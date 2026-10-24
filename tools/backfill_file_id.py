#!/usr/bin/env python3
"""Reviewed backfill of entries.file_id (hatnote/montage#660, follow-up to #513).

Three steps, each its own subcommand. Only `apply` and `rollback` write to a
database, and `apply` writes nothing unless it is given --execute.

  decide    rows.tsv (from tools/analyze_file_id.py) -> decisions.tsv.
            Pure file-to-file, no database. The ruleset below maps each
            analysis category to set / null / hold. decisions.tsv holds ids,
            file_ids and categories only (no names), and is what gets reviewed.

  apply     decisions.tsv -> UPDATE entries SET file_id = ... for the rows
            decided "set". Dry run by default: it reads, counts, and writes
            nothing. With --execute it writes in batches, only to rows whose
            file_id IS NULL, and records every write in a journal first.

  rollback  journal -> restores each journalled row to its old value, but
            only where file_id still equals what apply wrote.

The writer never recomputes a decision and never looks at Commons: it applies
the reviewed file. A rerun is safe (rows already set are skipped), and an
interrupted --execute resumes from the journal.

Usage (Toolforge, buildservice shell), in this order:
  python backfill_file_id.py decide --rows rows.tsv --out decisions.tsv
  python backfill_file_id.py apply --db DB --decisions decisions.tsv \\
      --journal journal.tsv                      # dry run: counts only
  python backfill_file_id.py apply --db DB --decisions decisions.tsv \\
      --journal journal.tsv --execute            # writes
  python backfill_file_id.py rollback --db DB --journal journal.tsv --execute
"""
from __future__ import print_function

import os
import sys
import json
import time
import uuid
import hashlib
import sqlite3
import argparse
import datetime
import collections

RULESET_VERSION = 'file-id-backfill ruleset v1 (hatnote/montage#660)'
TOOLSDB_HOST = 'tools.db.svc.wikimedia.cloud'
DEFAULTS_FILE = '~/replica.my.cnf'

# analysis category -> decision. "set": the row's file_id identifies its
# image (#660, "Proposed as certain: set"). "null": certain that no file_id
# can be set. Everything else is "hold": left NULL, listed for later.
SET = frozenset((
    'tier1', 'tier2a', 'tier2b', 'changed_after',
    'reused_tier1', 'reused_tier2a', 'reused_tier2b',
    'moved_in_tier1', 'moved_in_tier2a', 'moved_in_tier2b',
))
NULL = frozenset(('deleted_settled', 'deleted_no_row'))
# Open item 6 in #660: the row gets the file_id of the file it was moved to.
# Held back unless decide is run with --include-moved-away.
MOVED_AWAY = frozenset((
    'moved_away_tier1', 'moved_away_tier2a', 'moved_away_tier2b',
    'moved_away_changed_after',
))

DECISIONS = ('set', 'null', 'hold')
DECISION_COLUMNS = ('id', 'decision', 'file_id', 'category', 'flags', 'rule')
JOURNAL_COLUMNS = ('run_id', 'time', 'id', 'old', 'new')


class BackfillError(Exception):
    pass


# ---------------------------------------------------------------------------
# decide
# ---------------------------------------------------------------------------

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def decide_row(category, include_moved_away=False):
    """(decision, rule) for one analysis category."""
    if category in SET:
        return 'set', 'set:%s' % category
    if category in NULL:
        return 'null', 'null:%s' % category
    if category in MOVED_AWAY and include_moved_away:
        return 'set', 'set:%s' % category
    return 'hold', 'hold:%s' % category


def _parse_file_id(value, row_id):
    try:
        file_id = int(value)
    except (TypeError, ValueError):
        raise BackfillError('row %s: file_id %r is not an integer' % (row_id, value))
    if file_id <= 0:
        raise BackfillError('row %s: file_id %d is not positive' % (row_id, file_id))
    return file_id


def read_rows(path):
    """Yield (id, category, flags, file_id_column, evidence) from rows.tsv."""
    with open(path, encoding='utf-8') as f:
        header = None
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            cols = line.split('\t')
            if header is None:
                header = cols
                for needed in ('id', 'category', 'flags', 'file_id', 'evidence'):
                    if needed not in header:
                        raise BackfillError('%s: no %r column' % (path, needed))
                continue
            rec = dict(zip(header, cols))
            yield (int(rec['id']), rec['category'], rec['flags'], rec['file_id'],
                   json.loads(rec['evidence'] or '{}'))


def decide(rows_path, out_path, include_moved_away=False):
    """Write decisions.tsv from rows.tsv; return {decision: count}."""
    seen = set()
    counts = collections.Counter()
    by_rule = collections.Counter()
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write('#%s\n' % RULESET_VERSION)
        out.write('#rows_sha256=%s include_moved_away=%s\n'
                  % (sha256_of(rows_path), bool(include_moved_away)))
        out.write('\t'.join(DECISION_COLUMNS) + '\n')
        for row_id, category, flags, file_id, evidence in read_rows(rows_path):
            if row_id in seen:
                raise BackfillError('%s: row id %d occurs twice' % (rows_path, row_id))
            seen.add(row_id)
            decision, rule = decide_row(category, include_moved_away)
            fid = ''
            if decision == 'set':
                if category in MOVED_AWAY:
                    file_id = evidence.get('moved_to_file_id') or ''
                if not file_id:
                    raise BackfillError('row %d (%s): decided "set" but the analysis '
                                        'gives no file_id' % (row_id, category))
                fid = _parse_file_id(file_id, row_id)
            counts[decision] += 1
            by_rule[rule] += 1
            out.write('\t'.join(str(x) for x in (
                row_id, decision, fid, category, flags, rule)) + '\n')
    return counts, by_rule


# ---------------------------------------------------------------------------
# reading a decision file
# ---------------------------------------------------------------------------

def read_decisions(path):
    """All (id, decision, file_id) of a decisions.tsv, validated; also the
    file's sha256. Raises BackfillError on anything the writer must not trust."""
    out = []
    seen = set()
    header = None
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            cols = line.split('\t')
            if header is None:
                if tuple(cols) != DECISION_COLUMNS:
                    raise BackfillError('%s: unexpected header %r' % (path, cols))
                header = cols
                continue
            if len(cols) != len(DECISION_COLUMNS):
                raise BackfillError('%s line %d: %d columns' % (path, n, len(cols)))
            rec = dict(zip(header, cols))
            row_id = int(rec['id'])
            if row_id in seen:
                raise BackfillError('%s line %d: id %d occurs twice' % (path, n, row_id))
            seen.add(row_id)
            if rec['decision'] not in DECISIONS:
                raise BackfillError('%s line %d: decision %r' % (path, n, rec['decision']))
            file_id = None
            if rec['decision'] == 'set':
                file_id = _parse_file_id(rec['file_id'], row_id)
            elif rec['file_id']:
                raise BackfillError('%s line %d: file_id on a %s row'
                                    % (path, n, rec['decision']))
            out.append((row_id, rec['decision'], file_id))
    if header is None:
        raise BackfillError('%s: no header' % path)
    return out, sha256_of(path)


# ---------------------------------------------------------------------------
# database access (sqlite3 in tests, pymysql on Toolforge)
# ---------------------------------------------------------------------------

def _ph(conn):
    return '?' if isinstance(conn, sqlite3.Connection) else '%s'


def _in(conn, n):
    return ','.join([_ph(conn)] * n)


def _select_file_ids(conn, ids):
    cur = conn.cursor()
    cur.execute('SELECT id, file_id FROM entries WHERE id IN (%s)' % _in(conn, len(ids)),
                list(ids))
    return dict(cur.fetchall())


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ---------------------------------------------------------------------------
# journal
# ---------------------------------------------------------------------------

def read_journal(path):
    """(decisions_sha256, entries) of a journal; entries are
    (run_id, id, old, new) with old None for NULL."""
    sha = None
    entries = []
    if not os.path.exists(path):
        return sha, entries
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
            if line.startswith('#decisions_sha256='):
                sha = line.split('=', 1)[1]
                continue
            if line.startswith('#') or line.startswith(JOURNAL_COLUMNS[0] + '\t'):
                continue
            run_id, _, row_id, old, new = line.split('\t')
            entries.append((run_id, int(row_id), int(old) if old else None, int(new)))
    return sha, entries


class Journal(object):
    """Write-ahead log: entries are flushed to disk before the UPDATE they
    describe, so a crash can leave an entry for a write that did not happen
    (rollback skips it: the column does not hold the journalled value) but
    never a write without an entry."""

    def __init__(self, path, decisions_sha, run_id):
        self.run_id = run_id
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self.f = open(path, 'a', encoding='utf-8')
        if new:
            self.f.write('#%s\n#decisions_sha256=%s\n' % (RULESET_VERSION, decisions_sha))
            self.f.write('\t'.join(JOURNAL_COLUMNS) + '\n')
        self.f.write('#run %s started %s\n' % (run_id, _now()))
        self.f.flush()

    def write(self, rows):
        now = _now()
        for row_id, old, new in rows:
            self.f.write('%s\t%s\t%d\t%s\t%d\n' % (
                self.run_id, now, row_id, '' if old is None else old, new))
        self.f.flush()
        os.fsync(self.f.fileno())

    def close(self):
        self.f.close()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

def apply_decisions(conn, decisions_path, journal_path, execute=False, batch_size=1000,
                    max_batches=None, sleep=0.2, out=sys.stdout):
    """Apply the "set" rows of a decisions file. Returns a Counter.

    Counters: to_set (written, or would be written on a dry run), already_same
    (file_id already holds the decided value), conflict (file_id holds a
    different value: left alone), missing (no entries row with that id),
    raced (was NULL when read, not when written), not_set (null / hold rows,
    not touched), unprocessed (left over after --max-batches).

    A rerun, or the resume of an interrupted run, needs no memory of what was
    done: rows already written read as already_same. The journal is only for
    rollback."""
    decisions, sha = read_decisions(decisions_path)
    journal_sha, entries = read_journal(journal_path)
    if entries and journal_sha != sha:
        raise BackfillError('journal %s belongs to a different decisions file '
                            '(sha256 %s, this one %s); use a new journal'
                            % (journal_path, journal_sha, sha))
    counts = collections.Counter()
    todo = []
    for row_id, decision, file_id in decisions:
        if decision != 'set':
            counts['not_set'] += 1
        else:
            todo.append((row_id, file_id))
    journal = Journal(journal_path, sha, uuid.uuid4().hex[:12]) if execute else None
    started = time.time()
    batches = 0
    ph = _ph(conn)
    try:
        for chunk in _chunks(todo, batch_size):
            if max_batches is not None and batches >= max_batches:
                break
            current = _select_file_ids(conn, [r for r, _ in chunk])
            writes = []
            for row_id, file_id in chunk:
                if row_id not in current:
                    counts['missing'] += 1
                elif current[row_id] is None:
                    writes.append((row_id, file_id))
                elif current[row_id] == file_id:
                    counts['already_same'] += 1
                else:
                    counts['conflict'] += 1
            if execute and writes:
                journal.write([(r, None, f) for r, f in writes])
                cur = conn.cursor()
                for row_id, file_id in writes:
                    cur.execute('UPDATE entries SET file_id = %s WHERE id = %s '
                                'AND file_id IS NULL' % (ph, ph), (file_id, row_id))
                    if cur.rowcount == 1:
                        counts['to_set'] += 1
                    else:
                        counts['raced'] += 1
                conn.commit()
            else:
                counts['to_set'] += len(writes)
            batches += 1
            print('batch %d: %d rows, last id %d, %.0fs elapsed' % (
                batches, len(chunk), chunk[-1][0], time.time() - started), file=out)
            if execute and sleep:
                time.sleep(sleep)
    finally:
        if journal:
            journal.close()
    if batches * batch_size < len(todo):
        counts['unprocessed'] = len(todo) - batches * batch_size
    print(('EXECUTED' if execute else 'DRY RUN (nothing written)') + ': '
          + json.dumps(dict(sorted(counts.items()))), file=out)
    return counts


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------

def rollback(conn, journal_path, execute=False, batch_size=1000, sleep=0.2,
             out=sys.stdout):
    """Restore every journalled row to its old value, where file_id still
    equals the journalled new value. Counters: restored, changed_since (the
    column no longer holds the journalled value: left alone)."""
    _, entries = read_journal(journal_path)
    if not entries:
        raise BackfillError('journal %s has no entries' % journal_path)
    counts = collections.Counter()
    ph = _ph(conn)
    # the last journalled value per row wins (a row can be journalled by a
    # run that crashed and again by its resume)
    last = {}
    for _, row_id, old, new in entries:
        last[row_id] = (old, new)
    items = sorted(last.items())
    for chunk in _chunks(items, batch_size):
        current = _select_file_ids(conn, [r for r, _ in chunk])
        cur = conn.cursor()
        for row_id, (old, new) in chunk:
            if current.get(row_id) != new:
                counts['changed_since'] += 1
            elif not execute:
                counts['restored'] += 1
            else:
                cur.execute('UPDATE entries SET file_id = %s WHERE id = %s '
                            'AND file_id = %s' % (ph, ph, ph), (old, row_id, new))
                counts['restored' if cur.rowcount == 1 else 'changed_since'] += 1
        if execute:
            conn.commit()
            if sleep:
                time.sleep(sleep)
    print(('EXECUTED' if execute else 'DRY RUN (nothing written)') + ': '
          + json.dumps(dict(sorted(counts.items()))), file=out)
    return counts


# ---------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------

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
    sub = p.add_subparsers(dest='command', required=True)

    d = sub.add_parser('decide', help='rows.tsv -> decisions.tsv (no database)')
    d.add_argument('--rows', required=True)
    d.add_argument('--out', required=True)
    d.add_argument('--include-moved-away', action='store_true',
                   help='also set moved-away rows to the moved file\'s file_id '
                        '(#660 open item 6; off by default)')

    for name, help_ in (('apply', 'apply a decisions file (dry run unless --execute)'),
                        ('rollback', 'restore the values in a journal')):
        s = sub.add_parser(name, help=help_)
        s.add_argument('--db', required=True, help="Montage's database name")
        s.add_argument('--host', default=TOOLSDB_HOST)
        s.add_argument('--defaults-file', default=DEFAULTS_FILE)
        s.add_argument('--journal', required=True)
        s.add_argument('--execute', action='store_true',
                       help='write; without it nothing is written')
        s.add_argument('--batch-size', type=int, default=1000)
        s.add_argument('--sleep', type=float, default=0.2)
        if name == 'apply':
            s.add_argument('--decisions', required=True)
            s.add_argument('--max-batches', type=int)

    args = p.parse_args(argv)
    try:
        if args.command == 'decide':
            counts, by_rule = decide(args.rows, args.out, args.include_moved_away)
            print(json.dumps({'decisions': dict(counts), 'rules': dict(sorted(by_rule.items()))},
                             indent=1))
            return 0
        if not 1 <= args.batch_size <= 5000:
            p.exit(2, '--batch-size must be 1-5000\n')
        conn = _connect(args.host, args.db, args.defaults_file)
        if args.command == 'apply':
            apply_decisions(conn, args.decisions, args.journal, args.execute,
                            args.batch_size, args.max_batches, args.sleep)
        else:
            rollback(conn, args.journal, args.execute, args.batch_size, args.sleep)
    except BackfillError as e:
        print('error: %s' % e, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
