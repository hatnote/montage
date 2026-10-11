#!/usr/bin/env python3
"""Read-only analysis for the entries.file_id backfill (hatnote/montage#513).

For every entries row without a file_id, this script looks at the Commons
replica and decides which tier the row falls in. It writes NOTHING to any
database: the Montage connection is opened read-only, and the script has no
UPDATE, INSERT or DELETE statement. Output is a per-row TSV (ids, category,
flags and evidence; no names, no user names) and a summary of counts.

Categories (see .claude/features/file-id-backfill-513/ for the reasoning):
  tier1             one upload entry under the name, one version, same
                    timestamp (and sha1 when the log has one), uploaded before
                    the row's first import, nothing moved/deleted/hidden
  tier2a            several versions, uploads and versions match one-to-one,
                    all versions before the first import, all by the first
                    uploader or by bots
  tier2b            as tier2a, but other people uploaded versions too
  changed_after     versions match, but some came after the first import
  deleted_settled   whole file still deleted, deleted after the last date
                    jurors could see the row (stays NULL)
  deleted_mixed     whole file still deleted, but deleted before that date
  deleted_no_row    no file row (deleted before the 2025 migration), only
                    archive entries
  moved_away        no live file under the name, a move away from it
  name_reused       a whole-file deletion followed by a later upload
  restored          a whole-file deletion and restore, file live, no
                    re-upload after the deletion
  version_hidden    a version hidden, suppressed or deleted while the file
                    stays live
  moved_in          versions without an upload entry under this title
                    (moved here, or their log entry is hidden)
  upload_after_import  the only uploads are newer than the row's first import
  not_found         no file row, no archive entry, no move
  other             anything not covered above

Usage (Toolforge, buildservice shell):
  launcher python analyze_file_id.py --db DB --every 200 --out DIR

--every K takes the rows whose id is a multiple of K (a fixed, reproducible
sample); --every 1 takes all rows. --after-id resumes after a given id.
"""
from __future__ import print_function

import os
import re
import sys
import time
import json
import argparse
import datetime
import collections

try:
    import resource
except ImportError:  # not on Windows
    resource = None

VERSION = 'analyze_file_id v1'
TOOLSDB_HOST = 'tools.db.svc.wikimedia.cloud'
COMMONS_DB_HOST = os.environ.get('MONTAGE_COMMONS_DB_HOST',
                                 'commonswiki.analytics.db.svc.wikimedia.cloud')
DEFAULTS_FILE = '~/replica.my.cnf'

CATEGORIES = ('tier1', 'tier2a', 'tier2b', 'changed_after', 'deleted_settled',
              'deleted_mixed', 'deleted_no_row', 'moved_away', 'name_reused',
              'restored', 'version_hidden', 'moved_in', 'upload_after_import',
              'not_found', 'other')

# ---------------------------------------------------------------------------
# Queries (all SELECT)
# ---------------------------------------------------------------------------

ENTRIES_QUERY = '''
    SELECT id, name, upload_date, width, height, create_date
    FROM entries FORCE INDEX (PRIMARY)
    WHERE id > %s AND file_id IS NULL AND MOD(id, %s) = 0
    ORDER BY id
    LIMIT %s
'''

# The last moment jurors could look at a row: the end of its latest round,
# or now while a round is still open.
LAST_SEEN_QUERY = '''
    SELECT re.entry_id,
           MAX(CASE WHEN r.status IN ('active', 'paused') THEN UTC_TIMESTAMP()
                    ELSE COALESCE(r.close_date, r.deadline_date, r.create_date) END),
           COUNT(DISTINCT re.round_id)
    FROM round_entries re
    JOIN rounds r ON r.id = re.round_id
    WHERE re.entry_id IN ({ids})
    GROUP BY re.entry_id
'''

FILES_QUERY = '''
    SELECT file_id, file_name, file_deleted, file_latest
    FROM file WHERE file_name IN ({names})
'''

VERSIONS_QUERY = '''
    SELECT fr_file, fr_id, fr_timestamp, fr_sha1, fr_width, fr_height,
           fr_deleted, fr_actor
    FROM filerevision WHERE fr_file IN ({ids})
'''

LOG_QUERY = '''
    SELECT log_title, log_type, log_action, log_timestamp, log_deleted,
           log_actor, log_params
    FROM logging_logindex
    WHERE log_namespace = 6 AND log_title IN ({names})
      AND log_type IN ('upload', 'delete', 'move', 'merge', 'import')
'''

ARCHIVE_QUERY = '''
    SELECT fa_name, fa_timestamp, fa_sha1, fa_deleted_timestamp, fa_archive_name
    FROM filearchive WHERE fa_name IN ({names})
'''

BOTS_QUERY = '''
    SELECT a.actor_id, a.actor_name,
           MAX(ug.ug_group IS NOT NULL), MAX(ufg.ufg_group IS NOT NULL)
    FROM actor a
    LEFT JOIN user_groups ug ON ug.ug_user = a.actor_user AND ug.ug_group = 'bot'
    LEFT JOIN user_former_groups ufg ON ufg.ufg_user = a.actor_user
         AND ufg.ufg_group = 'bot'
    WHERE a.actor_id IN ({ids})
    GROUP BY a.actor_id, a.actor_name
'''

# ---------------------------------------------------------------------------
# Small helpers (pure)
# ---------------------------------------------------------------------------

_SHA1_RE = re.compile(r's:8:"img_sha1";s:\d+:"([0-9a-z]*)"')
_TS_RE = re.compile(r's:13:"img_timestamp";s:14:"(\d{14})"')


def text(value):
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode('utf8')
    return value


def ts(value):
    """A MediaWiki timestamp string (YYYYMMDDHHMMSS) from a datetime or a
    replica value; None for anything unusable."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.year < 1900:
            return None
        return value.strftime('%Y%m%d%H%M%S')
    value = text(value)
    if isinstance(value, str) and len(value) == 14 and value.isdigit():
        return value
    return None


def replica_name(name):
    return text(name).replace(' ', '_')


def is_canonical(name):
    """True if the stored name is already how Commons spells the title."""
    n = replica_name(name)
    if not n or n != n.strip('_') or '__' in n:
        return False
    if n.lower().startswith(('file:', 'image:')):
        return False
    return n[0] == n[0].upper()


def parse_upload_params(params):
    """(sha1, timestamp) from an upload log entry's serialized params; either
    may be None (entries before mid-2013 have no params)."""
    params = text(params) or ''
    sha1 = _SHA1_RE.search(params)
    stamp = _TS_RE.search(params)
    return (sha1.group(1) if sha1 else None, stamp.group(1) if stamp else None)


# ---------------------------------------------------------------------------
# Classification (pure; this is the rule, and the tests exercise it)
# ---------------------------------------------------------------------------

def classify(row, file_row, versions, logs, archive, bots):
    """Decide one entries row.

    row:      {id, name, upload_date, width, height, first_seen, last_seen}
              (first_seen/last_seen as MediaWiki timestamps)
    file_row: {file_id, file_deleted, file_latest} or None
    versions: [{fr_id, ts, sha1, width, height, deleted, actor}] of file_row
    logs:     [{type, action, ts, deleted, actor, sha1, img_ts}] for the title
    archive:  [{ts, sha1, deleted_ts, archive_name}] for the name
    bots:     {actor_id: True/False}

    Returns (category, flags, evidence) where flags is a sorted list of
    strings and evidence a dict of small values for the TSV.
    """
    flags = set()
    first_seen, last_seen = row['first_seen'], row['last_seen']
    uploads = sorted((l for l in logs if l['type'] == 'upload'), key=lambda l: l['ts'])
    deletes = sorted((l for l in logs if l['type'] == 'delete'
                      and l['action'] in ('delete', 'restore')), key=lambda l: l['ts'])
    moves = [l for l in logs if l['type'] == 'move']
    if any(l['type'] in ('merge', 'import') for l in logs):
        flags.add('merge_or_import')
    if any(l['deleted'] for l in logs):
        flags.add('log_hidden')
    if any(l['deleted'] & 8 for l in logs):
        flags.add('log_suppressed')
    if not is_canonical(row['name']):
        flags.add('name_not_canonical')
    if uploads and not any(u['sha1'] for u in uploads):
        flags.add('ts_only')
    if any(l['type'] == 'delete' and l['action'] == 'delete_redir' for l in logs):
        flags.add('redirect_deleted')
    if not last_seen:
        flags.add('no_rounds')
    evidence = {'n_uploads': len(uploads), 'n_versions': len(versions),
                'n_archive': len(archive), 'file_id': file_row and file_row['file_id']}

    # -- no live file ------------------------------------------------------
    if file_row is None:
        if moves:
            return 'moved_away', sorted(flags), evidence
        if archive:
            return 'deleted_no_row', sorted(flags), evidence
        return 'not_found', sorted(flags), evidence
    if file_row['file_deleted']:
        if file_row['file_deleted'] & 2:
            flags.add('file_suppressed')
        last_delete = max((d['ts'] for d in deletes if d['action'] == 'delete'),
                          default=None)
        evidence['deleted_ts'] = last_delete
        if last_delete and last_seen and last_delete > last_seen:
            return 'deleted_settled', sorted(flags), evidence
        return 'deleted_mixed', sorted(flags), evidence

    # -- live file -----------------------------------------------------------
    whole_deletes = [d for d in deletes if d['action'] == 'delete']
    restores = [d for d in deletes if d['action'] == 'restore']
    if any(v['deleted'] for v in versions):
        flags.add('version_hidden')
    if any(v['deleted'] & 8 for v in versions):
        flags.add('version_suppressed')
    upload_ts = set(u['img_ts'] or u['ts'] for u in uploads)
    version_ts = set(v['ts'] for v in versions)
    versions_without_upload = [v for v in versions if v['ts'] not in upload_ts]
    uploads_without_version = [u for u in uploads if (u['img_ts'] or u['ts']) not in version_ts]
    if versions_without_upload:
        flags.add('version_without_upload')
    if uploads_without_version:
        flags.add('upload_without_version')
    sha1_mismatch = False
    by_ts = {v['ts']: v for v in versions}
    for u in uploads:
        v = by_ts.get(u['img_ts'] or u['ts'])
        if v is not None and u['sha1'] and u['sha1'] != v['sha1']:
            sha1_mismatch = True
    if sha1_mismatch:
        flags.add('sha1_mismatch')

    # Montage cross-checks (counted, not deciding)
    if row['upload_date'] and row['upload_date'] in version_ts:
        flags.add('date_matches_version')
    at_import = [v for v in versions if first_seen and v['ts'] <= first_seen]
    if at_import:
        cur = max(at_import, key=lambda v: v['ts'])
        if row['width'] and (row['width'], row['height']) == (cur['width'], cur['height']):
            flags.add('size_matches_at_import')

    last_upload_ts = max(version_ts) if version_ts else None
    first_upload_ts = min(version_ts) if version_ts else None
    evidence['first_version_ts'] = first_upload_ts
    evidence['last_version_ts'] = last_upload_ts

    if whole_deletes:
        if any(u['ts'] > whole_deletes[-1]['ts'] for u in uploads):
            return 'name_reused', sorted(flags), evidence
        if restores:
            return 'restored', sorted(flags), evidence
        return 'other', sorted(flags), evidence
    if versions_without_upload or moves:
        return 'moved_in', sorted(flags), evidence
    if 'version_hidden' in flags or uploads_without_version:
        return 'version_hidden', sorted(flags), evidence
    if sha1_mismatch or 'log_hidden' in flags or 'merge_or_import' in flags:
        return 'other', sorted(flags), evidence
    if not versions or not uploads:
        return 'other', sorted(flags), evidence
    if first_seen and first_upload_ts > first_seen:
        return 'upload_after_import', sorted(flags), evidence
    if first_seen and last_upload_ts > first_seen:
        return 'changed_after', sorted(flags), evidence

    # every version predates the first import, uploads and versions match
    if len(uploads) == 1 and len(versions) == 1 and uploads[0]['action'] == 'upload':
        return 'tier1', sorted(flags), evidence
    first_actor = uploads[0]['actor']
    others = set(v['actor'] for v in versions
                 if v['actor'] != first_actor and not bots.get(v['actor']))
    bot_actors = sorted(set(v['actor'] for v in versions
                            if v['actor'] != first_actor and bots.get(v['actor'])))
    evidence['bots'] = bot_actors
    if others:
        return 'tier2b', sorted(flags), evidence
    return 'tier2a', sorted(flags), evidence


# ---------------------------------------------------------------------------
# Database access
# ---------------------------------------------------------------------------

def _in(n):
    return ', '.join(['%s'] * n)


class Montage(object):
    def __init__(self, connection):
        self.c = connection
        cur = self.c.cursor()
        try:
            # belt and braces: this connection cannot write
            cur.execute('SET SESSION TRANSACTION READ ONLY')
        finally:
            cur.close()

    def entries(self, after_id, every, limit):
        cur = self.c.cursor()
        try:
            cur.execute(ENTRIES_QUERY, (after_id, every, limit))
            rows = cur.fetchall()
        finally:
            cur.close()
        self.c.commit()
        return [{'id': r[0], 'name': text(r[1]), 'upload_date': ts(r[2]),
                 'width': r[3], 'height': r[4], 'first_seen': ts(r[5])} for r in rows]

    def last_seen(self, ids):
        if not ids:
            return {}
        cur = self.c.cursor()
        try:
            cur.execute(LAST_SEEN_QUERY.format(ids=_in(len(ids))), tuple(ids))
            rows = cur.fetchall()
        finally:
            cur.close()
        self.c.commit()
        return {r[0]: (ts(r[1]), r[2]) for r in rows}


class Replica(object):
    def __init__(self, connection):
        self.c = connection
        self.bot_cache = {}
        self.bot_names = {}
        self.bots_ok = True

    def _fetch(self, query, params):
        if not params:
            return []
        cur = self.c.cursor()
        try:
            cur.execute(query, tuple(params))
            return cur.fetchall()
        finally:
            cur.close()

    def lookup(self, names):
        names = sorted(set(names))
        enc = [n.encode('utf8') for n in names]
        files = {}
        for r in self._fetch(FILES_QUERY.format(names=_in(len(enc))), enc):
            files[text(r[1])] = {'file_id': int(r[0]), 'file_deleted': int(r[2]),
                                 'file_latest': int(r[3])}
        ids = sorted(f['file_id'] for f in files.values())
        versions = collections.defaultdict(list)
        for r in self._fetch(VERSIONS_QUERY.format(ids=_in(len(ids))), ids):
            versions[int(r[0])].append({'fr_id': int(r[1]), 'ts': ts(r[2]),
                                        'sha1': text(r[3]), 'width': r[4],
                                        'height': r[5], 'deleted': int(r[6]),
                                        'actor': r[7]})
        logs = collections.defaultdict(list)
        for r in self._fetch(LOG_QUERY.format(names=_in(len(enc))), enc):
            sha1, img_ts = (None, None)
            if text(r[1]) == 'upload':
                sha1, img_ts = parse_upload_params(r[6])
            logs[text(r[0])].append({'type': text(r[1]), 'action': text(r[2]),
                                     'ts': ts(r[3]), 'deleted': int(r[4]),
                                     'actor': int(r[5]) if r[5] is not None else None,
                                     'sha1': sha1, 'img_ts': img_ts})
        archive = collections.defaultdict(list)
        for r in self._fetch(ARCHIVE_QUERY.format(names=_in(len(enc))), enc):
            archive[text(r[0])].append({'ts': ts(r[1]), 'sha1': text(r[2]),
                                        'deleted_ts': ts(r[3]),
                                        'archive_name': text(r[4])})
        actors = set()
        for vs in versions.values():
            actors.update(v['actor'] for v in vs if v['actor'] is not None)
        for ls in logs.values():
            actors.update(l['actor'] for l in ls if l['actor'] is not None)
        self._load_bots(actors)
        self.c.commit()
        return files, versions, logs, archive

    def _load_bots(self, actors):
        if not self.bots_ok:
            return
        todo = sorted(a for a in actors if a not in self.bot_cache)
        try:
            self._load_bot_chunks(todo)
        except Exception as e:  # e.g. a view missing on the replica
            self.bots_ok = False
            print('warning: bot lookup failed, every other uploader counts as'
                  ' human from here on: %s' % e, file=sys.stderr, flush=True)

    def _load_bot_chunks(self, todo):
        for start in range(0, len(todo), 500):
            chunk = todo[start:start + 500]
            for r in self._fetch(BOTS_QUERY.format(ids=_in(len(chunk))), chunk):
                is_bot = bool(r[2]) or bool(r[3])
                self.bot_cache[int(r[0])] = is_bot
                if is_bot:  # bot account names are public and not personal
                    self.bot_names[int(r[0])] = text(r[1])
            for a in chunk:
                self.bot_cache.setdefault(a, False)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def peak_rss_mb():
    if resource is None:
        return -1
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024


def say(out, line):
    print(line, file=out, flush=True)


def analyze(montage, replica, out_dir, every=200, after_id=0, batch_size=500,
            max_batches=None, sleep=0.2, out=sys.stdout):
    os.makedirs(out_dir, exist_ok=True)
    rows_path = os.path.join(out_dir, 'rows.tsv')
    new_file = not os.path.exists(rows_path)
    counts = collections.Counter()
    by_year = collections.Counter()
    flag_counts = collections.Counter()
    bot_counts = collections.Counter()
    started = time.time()
    batches = 0
    with open(rows_path, 'a', encoding='utf-8') as tsv:
        if new_file:
            tsv.write('#%s every=%s\n' % (VERSION, every))
            tsv.write('id\tcategory\tflags\tfile_id\tn_uploads\tn_versions\t'
                      'n_archive\tfirst_seen\tlast_seen\tn_rounds\tevidence\n')
        while max_batches is None or batches < max_batches:
            t0 = time.time()
            rows = montage.entries(after_id, every, batch_size)
            if not rows:
                break
            seen = montage.last_seen([r['id'] for r in rows])
            t1 = time.time()
            files, versions, logs, archive = replica.lookup(
                replica_name(r['name']) for r in rows)
            t2 = time.time()
            for r in rows:
                r['last_seen'], n_rounds = seen.get(r['id'], (None, 0))
                name = replica_name(r['name'])
                f = files.get(name)
                cat, flags, ev = classify(
                    r, f, versions.get(f['file_id'], []) if f else [],
                    logs.get(name, []), archive.get(name, []), replica.bot_cache)
                counts[cat] += 1
                by_year[(cat, (r['first_seen'] or '????')[:4])] += 1
                flag_counts.update((cat, fl) for fl in flags)
                if cat in ('tier2a', 'tier2b'):
                    bot_counts.update(replica.bot_names.get(a, str(a))
                                      for a in ev.get('bots', []))
                tsv.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (
                    r['id'], cat, ','.join(flags), ev.get('file_id') or '',
                    ev['n_uploads'], ev['n_versions'], ev['n_archive'],
                    r['first_seen'] or '', r['last_seen'] or '', n_rounds,
                    json.dumps({k: v for k, v in ev.items()
                                if k not in ('file_id', 'n_uploads', 'n_versions',
                                             'n_archive')}, sort_keys=True)))
            tsv.flush()
            after_id = rows[-1]['id']
            batches += 1
            say(out, 'batch %d: %d rows, last id %d, montage %.1fs, replica %.1fs'
                % (batches, len(rows), after_id, t1 - t0, t2 - t1))
            if sleep:
                time.sleep(sleep)
    summary = {
        'version': VERSION, 'every': every, 'last_id': after_id, 'batches': batches,
        'rows': sum(counts.values()), 'seconds': round(time.time() - started, 1),
        'peak_rss_mb': peak_rss_mb(),
        'categories': {c: counts[c] for c in CATEGORIES if counts[c]},
        'by_first_import_year': {'%s %s' % k: v for k, v in sorted(by_year.items())},
        'flags': {'%s %s' % k: v for k, v in sorted(flag_counts.items())},
        'bots_in_tier2': dict(bot_counts.most_common()),
        'bot_lookup_ok': replica.bots_ok,
    }
    with open(os.path.join(out_dir, 'summary-%d.json' % after_id), 'w',
              encoding='utf-8') as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    say(out, json.dumps(summary, indent=1, sort_keys=True))
    return summary


def _connect(host, db, defaults_file):
    defaults_file = os.path.expanduser(defaults_file)
    if not os.path.isfile(defaults_file):
        raise SystemExit('defaults file %s not found (pass --defaults-file)' % defaults_file)
    os.environ.setdefault('USER', 'montage')  # pymysql needs it in containers
    import pymysql
    return pymysql.connect(host=host, db=db, charset='utf8mb4',
                           read_default_file=defaults_file, autocommit=False)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--db', required=True, help="Montage's database name")
    p.add_argument('--host', default=TOOLSDB_HOST)
    p.add_argument('--defaults-file', default=DEFAULTS_FILE)
    p.add_argument('--out', required=True, help='output folder (rows.tsv, summaries)')
    p.add_argument('--every', type=int, default=200,
                   help='rows whose id is a multiple of this (1 = all)')
    p.add_argument('--after-id', type=int, default=0)
    p.add_argument('--batch-size', type=int, default=500)
    p.add_argument('--max-batches', type=int)
    p.add_argument('--sleep', type=float, default=0.2)
    args = p.parse_args(argv)
    if not 1 <= args.batch_size <= 500:
        p.exit(2, '--batch-size must be 1-500\n')
    montage = Montage(_connect(args.host, args.db, args.defaults_file))
    replica = Replica(_connect(COMMONS_DB_HOST, 'commonswiki_p', args.defaults_file))
    analyze(montage, replica, args.out, args.every, args.after_id, args.batch_size,
            args.max_batches, args.sleep)
    return 0


if __name__ == '__main__':
    sys.exit(main())
