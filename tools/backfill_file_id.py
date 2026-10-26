#!/usr/bin/env python3
"""Reviewed, staged backfill of entries.file_id (hatnote/montage#660, #513).

Run in rounds, safest first (see ROUNDS). Each round is run, evaluated and
verified before the next one is applied: a round after the first will not
--execute without the previous round's journal, which must belong to the same
database. Each round is rehearsed on an exact copy of the database before the
same decisions file is applied to the real one; the file carries only entry
ids, file_ids and create dates (no names), so it is what moves between the two.

Subcommands. Only `apply` and `rollback` write to a database, and neither
writes unless it is given --execute together with --confirm-db <the --db name>.

  decide    rows.tsv (from tools/analyze_file_id.py, run with --every 1) ->
            decisions.tsv of one round. Pure file-to-file, no database. Rows
            of other rounds are held. Refuses a sampled rows.tsv.

  apply     decisions.tsv -> UPDATE entries SET file_id = ... for the rows
            decided "set". Dry run by default: it reads, counts, and writes
            nothing. With --execute it writes in batches, only to rows whose
            file_id IS NULL, and records every write in a journal first. A row
            is held, not written, when its create_date differs from the one the
            analysis saw (another row under that id), when its file_id is
            already on another entries row, or when a lower id in the same file
            gets the same file_id (--allow-duplicates writes those).

  verify    read-only: counts how many rows of a decisions file hold the
            decided value, are still NULL, or hold something else.

  rollback  journal -> restores each journalled row to its old value, but
            only where file_id still equals what apply wrote, and only on the
            database the journal was written on.

The writer never recomputes a decision and never looks at Commons: it applies
the reviewed file. A rerun is safe (rows already set are skipped), and an
interrupted --execute is resumed by running it again. Nothing detects an
analysis that was resumed with a different --every after its first header
line; run the analysis once, with --every 1.

Usage (Toolforge, buildservice shell), for round N, first on the copy, then on
the real database with the same decisions file but its OWN journal:
  python backfill_file_id.py decide --round 1 --rows rows.tsv --out decisions-1.tsv
  python backfill_file_id.py apply --db COPY --decisions decisions-1.tsv \\
      --journal copy-journal-1.tsv                  # dry run: counts only
  python backfill_file_id.py apply --db COPY --decisions decisions-1.tsv \\
      --journal copy-journal-1.tsv --execute --confirm-db COPY
  python backfill_file_id.py verify --db COPY --decisions decisions-1.tsv
  python backfill_file_id.py rollback --db COPY --journal copy-journal-1.tsv \\
      --execute --confirm-db COPY
Round 2 and later add --previous-journal <this database's journal of round N-1>
to apply --execute.
"""
from __future__ import print_function

import os
import re
import sys
import json
import time
import uuid
import hashlib
import sqlite3
import argparse
import datetime
import collections

RULESET_VERSION = 'file-id-backfill ruleset v3 (hatnote/montage#660)'
TOOLSDB_HOST = 'tools.db.svc.wikimedia.cloud'
DEFAULTS_FILE = '~/replica.my.cnf'

# analysis category -> decision, in rounds, safest first. A round is run,
# evaluated and verified before the next one is applied. "set": the row's
# file_id identifies its image (#660, "Proposed as certain: set"). "null":
# certain that no file_id can be set. Everything else is "hold": left NULL,
# listed for later.
ROUNDS = {
    # one upload, never changed, nothing moved or deleted
    1: ('tier1',),
    # several versions before the first import, by the uploader or a bot; the
    # same for names moved in or used again before the first import
    2: ('tier2a', 'reused_tier1', 'reused_tier2a',
        'moved_in_tier1', 'moved_in_tier2a'),
    # other people's versions, or versions added after the first import
    3: ('tier2b', 'reused_tier2b', 'moved_in_tier2b', 'changed_after'),
    # #660 open item 6: the row gets the file_id of the file it was moved to
    4: ('moved_away_tier1', 'moved_away_tier2a', 'moved_away_tier2b',
        'moved_away_changed_after'),
}
MOVED_AWAY = frozenset(ROUNDS[4])
NULL = frozenset(('deleted_settled', 'deleted_no_row'))

DECISIONS = ('set', 'null', 'hold')
DECISION_COLUMNS = ('id', 'decision', 'file_id', 'create_date', 'category', 'flags',
                    'rule')
JOURNAL_COLUMNS = ('run_id', 'time', 'id', 'old', 'new')
# MariaDB's eq_range_index_dive_limit is 200: an IN list of 200 or more values
# on file_id makes the optimizer read the whole table (#513). Stay below.
LOOKUP_CHUNK = 199


class BackfillError(Exception):
    pass


def say(out, line):
    print(line, file=out)
    out.flush()


# ---------------------------------------------------------------------------
# decide
# ---------------------------------------------------------------------------

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def decide_row(category, round_no):
    """(decision, rule) for one analysis category in one round. A category
    that belongs to another round is held here."""
    if category in ROUNDS[round_no]:
        return 'set', 'set:%s' % category
    if category in NULL:
        return 'null', 'null:%s' % category
    if any(category in c for c in ROUNDS.values()):
        return 'hold', 'hold:other_round:%s' % category
    return 'hold', 'hold:%s' % category


def header_value(path, key):
    """The value of `key=...` in a '#' header line of a decisions file or
    journal, or None."""
    with open(path, encoding='utf-8') as f:
        for line in f:
            if not line.startswith('#'):
                break
            for word in line[1:].split():
                if word.startswith(key + '='):
                    return word.split('=', 1)[1]
    return None


def _parse_file_id(value, row_id):
    try:
        file_id = int(value)
    except (TypeError, ValueError):
        raise BackfillError('row %s: file_id %r is not an integer' % (row_id, value))
    if file_id <= 0:
        raise BackfillError('row %s: file_id %d is not positive' % (row_id, file_id))
    return file_id


def norm_ts(value):
    """A 14-digit YYYYMMDDHHMMSS string from a datetime or a timestamp string,
    or '' for anything unusable (the same shape the analysis stores)."""
    if value is None:
        return ''
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y%m%d%H%M%S') if value.year >= 1900 else ''
    digits = re.sub(r'\D', '', str(value))
    return digits if len(digits) == 14 and digits[:4] >= '1900' else ''


def read_rows(path):
    """Yield (id, category, flags, file_id_column, first_seen, evidence) from
    rows.tsv."""
    with open(path, encoding='utf-8') as f:
        header = None
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            cols = line.split('\t')
            if header is None:
                header = cols
                for needed in ('id', 'category', 'flags', 'file_id', 'first_seen',
                               'evidence'):
                    if needed not in header:
                        raise BackfillError('%s: no %r column' % (path, needed))
                continue
            rec = dict(zip(header, cols))
            yield (int(rec['id']), rec['category'], rec['flags'], rec['file_id'],
                   rec['first_seen'], json.loads(rec['evidence'] or '{}'))


def rows_every(path):
    """The values of every `every=N` in the '#' header lines of rows.tsv."""
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                out.extend(int(m) for m in re.findall(r'\bevery=(\d+)', line))
    return out


def decide(rows_path, out_path, round_no, allow_sample=False):
    """Write the decisions.tsv of one round from rows.tsv; return
    ({decision: count}, {rule: count}, coverage)."""
    if round_no not in ROUNDS:
        raise BackfillError('round must be one of %s' % sorted(ROUNDS))
    every = rows_every(rows_path)
    if not every:
        raise BackfillError('%s has no "every=" header: cannot tell whether the '
                            'analysis covered every row' % rows_path)
    sample = any(e != 1 for e in every)
    if sample and not allow_sample:
        raise BackfillError('%s is a sample (every=%s), not the full analysis; run '
                            'the analysis with --every 1 (or pass --allow-sample '
                            'to test; such a file cannot be applied with --execute)'
                            % (rows_path, ','.join(str(e) for e in sorted(set(every)))))
    seen = set()
    counts = collections.Counter()
    by_rule = collections.Counter()
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write('#%s\n' % RULESET_VERSION)
        out.write('#round=%d sample=%s rows_sha256=%s\n'
                  % (round_no, 'true' if sample else 'false', sha256_of(rows_path)))
        out.write('\t'.join(DECISION_COLUMNS) + '\n')
        for row_id, category, flags, file_id, first_seen, evidence in read_rows(rows_path):
            if row_id in seen:
                raise BackfillError('%s: row id %d occurs twice' % (rows_path, row_id))
            seen.add(row_id)
            decision, rule = decide_row(category, round_no)
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
                row_id, decision, fid, first_seen, category, flags, rule)) + '\n')
    coverage = {'rows': len(seen), 'min_id': min(seen) if seen else None,
                'max_id': max(seen) if seen else None, 'sample': sample}
    return counts, by_rule, coverage


# ---------------------------------------------------------------------------
# reading a decision file
# ---------------------------------------------------------------------------

def read_decision_records(path):
    """(records, round_no, sha256, sample) of a decisions.tsv, validated.
    records are dicts with id, decision, file_id (int or None), create_date.
    Raises BackfillError on anything the writer must not trust: a missing
    round, a row that does not follow from its category in that round."""
    round_no = int(header_value(path, 'round') or 0)
    if round_no not in ROUNDS:
        raise BackfillError('%s: no valid #round= header' % path)
    records = []
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
            if (rec['decision'], rec['rule']) != decide_row(rec['category'], round_no):
                raise BackfillError('%s line %d: %s / %s is not what round %d decides '
                                    'for category %r' % (path, n, rec['decision'],
                                                         rec['rule'], round_no,
                                                         rec['category']))
            file_id = None
            if rec['decision'] == 'set':
                file_id = _parse_file_id(rec['file_id'], row_id)
            elif rec['file_id']:
                raise BackfillError('%s line %d: file_id on a %s row'
                                    % (path, n, rec['decision']))
            records.append({'id': row_id, 'decision': rec['decision'],
                            'file_id': file_id, 'create_date': rec['create_date']})
    if header is None:
        raise BackfillError('%s: no header' % path)
    sample = header_value(path, 'sample') == 'true'
    return records, round_no, sha256_of(path), sample


def read_decisions(path):
    """All (id, decision, file_id) of a decisions.tsv, validated; also the
    file's sha256."""
    records, _, sha, _ = read_decision_records(path)
    return [(r['id'], r['decision'], r['file_id']) for r in records], sha


# ---------------------------------------------------------------------------
# database access (sqlite3 in tests, pymysql on Toolforge)
# ---------------------------------------------------------------------------

def _ph(conn):
    return '?' if isinstance(conn, sqlite3.Connection) else '%s'


def _in(conn, n):
    return ','.join([_ph(conn)] * n)


def _select_rows(conn, ids):
    """{id: (file_id, normalised create_date)} of the entries rows that exist."""
    cur = conn.cursor()
    cur.execute('SELECT id, file_id, create_date FROM entries WHERE id IN (%s)'
                % _in(conn, len(ids)), list(ids))
    return {r[0]: (r[1], norm_ts(r[2])) for r in cur.fetchall()}


def _select_file_ids(conn, ids):
    return {i: v[0] for i, v in _select_rows(conn, ids).items()}


def _select_holders(conn, file_ids):
    """{file_id: set of entries ids that hold it}."""
    holders = collections.defaultdict(set)
    file_ids = sorted(set(file_ids))
    for chunk in _chunks(file_ids, LOOKUP_CHUNK):
        cur = conn.cursor()
        cur.execute('SELECT id, file_id FROM entries WHERE file_id IN (%s)'
                    % _in(conn, len(chunk)), list(chunk))
        for row_id, file_id in cur.fetchall():
            holders[file_id].add(row_id)
    return holders


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def describe_target(conn, target, out):
    cur = conn.cursor()
    cur.execute('SELECT MAX(id), COUNT(*) FROM entries')
    max_id, total = cur.fetchone()
    conn.rollback()
    say(out, 'target %s: entries max id %s, %s rows' % (target, max_id, total))


# ---------------------------------------------------------------------------
# journal
# ---------------------------------------------------------------------------

def _trim_torn_tail(path):
    """Cut a journal back to its last complete line (a killed run can leave a
    half-written one; its UPDATE never ran, because the journal is flushed
    before the UPDATE)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return
    with open(path, 'rb') as f:
        data = f.read()
    if data.endswith(b'\n'):
        return
    keep = data.rfind(b'\n') + 1
    with open(path, 'r+b') as f:
        f.truncate(keep)


def read_journal(path, err=sys.stderr):
    """(decisions_sha256, entries) of a journal; entries are
    (run_id, id, old, new) with old None for NULL. A half-written last line
    is ignored with a warning; any other malformed line is an error."""
    sha = None
    entries = []
    if not os.path.exists(path):
        return sha, entries
    with open(path, encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')
    last = lines.pop()          # '' when the file ends with a newline
    if last:
        print('warning: %s ends in a half-written line, ignored' % path, file=err)
    for n, line in enumerate(lines, 1):
        if not line:
            continue
        if line.startswith('#'):
            if 'decisions_sha256=' in line:
                sha = line.split('decisions_sha256=', 1)[1].split()[0]
            continue
        cols = line.split('\t')
        if cols[0] == JOURNAL_COLUMNS[0]:
            continue
        try:
            if len(cols) != 5:
                raise ValueError('%d columns' % len(cols))
            run_id, _, row_id, old, new = cols
            entries.append((run_id, int(row_id), int(old) if old else None, int(new)))
        except ValueError as e:
            raise BackfillError('%s line %d is malformed (%s): %r' % (path, n, e, line))
    return sha, entries


def check_journal_header(path, sha, round_no, target):
    """Refuse to continue a journal written for another decisions file, round
    or database; a journal with a header and no entries counts too."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return
    mine = (sha, str(round_no), target)
    theirs = (header_value(path, 'decisions_sha256'), header_value(path, 'round'),
              header_value(path, 'target'))
    if mine != theirs:
        raise BackfillError('journal %s was written for decisions %s, round %s, '
                            'database %s; this run is decisions %s, round %s, database '
                            '%s. Use a new journal.' % ((path,) + theirs + mine))


class Journal(object):
    """Write-ahead log: entries are flushed to disk before the UPDATE they
    describe, so a crash can leave an entry for a write that did not happen
    (rollback skips it: the column does not hold the journalled value) but
    never a write without an entry."""

    def __init__(self, path, decisions_sha, run_id, round_no, target):
        self.run_id = run_id
        _trim_torn_tail(path)
        check_journal_header(path, decisions_sha, round_no, target)
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self.f = open(path, 'a', encoding='utf-8')
        if new:
            self.f.write('#%s\n#round=%d target=%s decisions_sha256=%s\n'
                         % (RULESET_VERSION, round_no, target, decisions_sha))
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

def check_previous_round(round_no, previous_journal, target):
    """A round after the first only writes when the previous round's journal
    is given: it exists, belongs to round-1 and to this same database, and
    holds writes. That is a reminder to evaluate and verify that round first,
    not proof that anyone did."""
    if round_no == 1:
        return
    if not previous_journal:
        raise BackfillError('round %d needs --previous-journal, this database\'s '
                            'journal of round %d' % (round_no, round_no - 1))
    if not os.path.exists(previous_journal):
        raise BackfillError('%s does not exist' % previous_journal)
    if header_value(previous_journal, 'round') != str(round_no - 1):
        raise BackfillError('%s is not the journal of round %d'
                            % (previous_journal, round_no - 1))
    if header_value(previous_journal, 'target') != target:
        raise BackfillError('%s was written on database %s, not %s'
                            % (previous_journal, header_value(previous_journal, 'target'),
                               target))
    if not read_journal(previous_journal)[1]:
        raise BackfillError('%s has no entries: round %d was not applied'
                            % (previous_journal, round_no - 1))


def apply_decisions(conn, decisions_path, journal_path, execute=False, batch_size=1000,
                    max_batches=None, sleep=0.2, out=sys.stdout, previous_journal=None,
                    target='unknown', allow_duplicates=False):
    """Apply the "set" rows of a decisions file. Returns a Counter.

    Counters: to_set (written, or would be written on a dry run), already_same
    (file_id already holds the decided value), conflict (file_id holds a
    different value: left alone), missing (no entries row with that id),
    identity_mismatch (create_date differs from the one the analysis saw: held),
    file_id_elsewhere (the file_id is already on another entries row: held),
    duplicate_in_file (a lower id in this file gets the same file_id: held),
    raced (was NULL when read, not when written), not_set (null / hold rows,
    not touched), unprocessed (left over after --max-batches).

    A rerun, or the resume of an interrupted run, needs no memory of what was
    done: rows already written read as already_same. The journal is only for
    rollback. --max-batches counts batches that had something to write."""
    records, round_no, sha, sample = read_decision_records(decisions_path)
    if execute and sample:
        raise BackfillError('%s was decided from a sampled analysis; it cannot be '
                            'applied with --execute' % decisions_path)
    if execute:
        check_previous_round(round_no, previous_journal, target)
    check_journal_header(journal_path, sha, round_no, target)
    counts = collections.Counter()
    todo = []
    lowest = {}
    for rec in records:
        if rec['decision'] != 'set':
            counts['not_set'] += 1
            continue
        todo.append(rec)
        if rec['file_id'] not in lowest or rec['id'] < lowest[rec['file_id']]:
            lowest[rec['file_id']] = rec['id']
    journal = Journal(journal_path, sha, uuid.uuid4().hex[:12], round_no, target) \
        if execute else None
    describe_target(conn, target, out)
    started = time.time()
    batches = 0
    done = 0
    ph = _ph(conn)
    try:
        for chunk in _chunks(todo, batch_size):
            if max_batches is not None and batches >= max_batches:
                break
            current = _select_rows(conn, [r['id'] for r in chunk])
            holders = _select_holders(conn, [r['file_id'] for r in chunk])
            writes = []
            for rec in chunk:
                row_id, file_id = rec['id'], rec['file_id']
                if row_id not in current:
                    counts['missing'] += 1
                    continue
                value, create_date = current[row_id]
                if rec['create_date'] and create_date != rec['create_date']:
                    counts['identity_mismatch'] += 1
                elif value is not None:
                    counts['already_same' if value == file_id else 'conflict'] += 1
                elif not allow_duplicates and holders.get(file_id, set()) - {row_id}:
                    counts['file_id_elsewhere'] += 1
                elif not allow_duplicates and lowest[file_id] != row_id:
                    counts['duplicate_in_file'] += 1
                else:
                    writes.append((row_id, file_id))
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
            else:
                counts['to_set'] += len(writes)
            conn.commit()       # also ends the read snapshot of a dry run
            if writes:
                batches += 1
            done += len(chunk)
            say(out, 'batch %d: %d of %d rows, last id %d, %.0fs elapsed' % (
                batches, done, len(todo), chunk[-1]['id'], time.time() - started))
            if execute and writes and sleep:
                time.sleep(sleep)
    finally:
        if done < len(todo):
            counts['unprocessed'] = len(todo) - done
        say(out, ('EXECUTED' if execute else 'DRY RUN (nothing written)') + ': '
            + json.dumps(dict(sorted(counts.items()))))
        if journal:
            journal.close()
    return counts


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def verify(conn, decisions_path, batch_size=1000, out=sys.stdout, target='unknown'):
    """Read-only check of a database against a decisions file: counts only.

    For "set" rows: has_value (file_id equals the decided value), still_null,
    other_value (holds something else), missing (no such entries row),
    identity_mismatch (create_date differs from the analysis), and
    shared_file_id (has_value, but another entries row holds the same
    file_id). For null / hold rows: not_touched (file_id still NULL) and
    has_file_id (not NULL: set by an import or an earlier round).
    entries_with_duplicate_file_id counts every row of the table that shares
    its file_id with another."""
    records, _, _, _ = read_decision_records(decisions_path)
    counts = collections.Counter()
    describe_target(conn, target, out)
    for chunk in _chunks(records, batch_size):
        current = _select_rows(conn, [r['id'] for r in chunk])
        holders = _select_holders(conn, [r['file_id'] for r in chunk
                                         if r['file_id'] is not None])
        for rec in chunk:
            row_id = rec['id']
            if rec['decision'] == 'set':
                if row_id not in current:
                    counts['missing'] += 1
                    continue
                value, create_date = current[row_id]
                if rec['create_date'] and create_date != rec['create_date']:
                    counts['identity_mismatch'] += 1
                elif value is None:
                    counts['still_null'] += 1
                elif value != rec['file_id']:
                    counts['other_value'] += 1
                elif holders.get(value, set()) - {row_id}:
                    counts['has_value'] += 1
                    counts['shared_file_id'] += 1
                else:
                    counts['has_value'] += 1
            elif current.get(row_id, (None,))[0] is None:
                counts['not_touched'] += 1
            else:
                counts['has_file_id'] += 1
        conn.commit()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) - COUNT(DISTINCT file_id) FROM entries '
                'WHERE file_id IS NOT NULL')
    counts['entries_with_duplicate_file_id'] = int(cur.fetchone()[0])
    conn.commit()
    say(out, 'VERIFY (read-only): ' + json.dumps(dict(sorted(counts.items()))))
    return counts


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------

def rollback(conn, journal_path, execute=False, batch_size=1000, sleep=0.2,
             out=sys.stdout, target='unknown'):
    """Restore every journalled row to its old value, where file_id still
    equals the journalled new value. Counters: restored, already_old (the
    column already holds the old value: the write never happened, or this
    rollback already ran), changed_since (it holds something else: left
    alone)."""
    _, entries = read_journal(journal_path)
    if not entries:
        raise BackfillError('journal %s has no entries' % journal_path)
    written_on = header_value(journal_path, 'target')
    if written_on != target:
        raise BackfillError('journal %s was written on database %s, not %s'
                            % (journal_path, written_on, target))
    counts = collections.Counter()
    ph = _ph(conn)
    describe_target(conn, target, out)
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
            value = current.get(row_id)
            if row_id in current and value == old:
                counts['already_old'] += 1
            elif value != new:
                counts['changed_since'] += 1
            elif not execute:
                counts['restored'] += 1
            else:
                cur.execute('UPDATE entries SET file_id = %s WHERE id = %s '
                            'AND file_id = %s' % (ph, ph, ph), (old, row_id, new))
                counts['restored' if cur.rowcount == 1 else 'changed_since'] += 1
        conn.commit()
        if execute and sleep:
            time.sleep(sleep)
    say(out, ('EXECUTED' if execute else 'DRY RUN (nothing written)') + ': '
        + json.dumps(dict(sorted(counts.items()))))
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
                           read_default_file=defaults_file, autocommit=False,
                           connect_timeout=30, read_timeout=300, write_timeout=300)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = p.add_subparsers(dest='command', required=True)

    d = sub.add_parser('decide', help='rows.tsv -> decisions.tsv (no database)')
    d.add_argument('--rows', required=True)
    d.add_argument('--out', required=True)
    d.add_argument('--round', type=int, required=True, choices=sorted(ROUNDS),
                   help='1 = one upload, never changed (safest); 2 = several '
                        'versions by the uploader or bots; 3 = other people\'s '
                        'versions or versions after the import; 4 = moved-away '
                        'rows (#660 open item 6)')
    d.add_argument('--allow-sample', action='store_true',
                   help='accept a sampled rows.tsv (for testing; the result cannot '
                        'be applied with --execute)')

    for name, help_ in (('apply', 'apply a decisions file (dry run unless --execute)'),
                        ('verify', 'read-only: compare the database with a decisions file'),
                        ('rollback', 'restore the values in a journal')):
        s = sub.add_parser(name, help=help_)
        s.add_argument('--db', required=True, help="Montage's database name")
        s.add_argument('--host', default=TOOLSDB_HOST)
        s.add_argument('--defaults-file', default=DEFAULTS_FILE)
        s.add_argument('--batch-size', type=int, default=1000)
        if name != 'verify':
            s.add_argument('--journal', required=True)
            s.add_argument('--execute', action='store_true',
                           help='write; without it nothing is written')
            s.add_argument('--confirm-db',
                           help='required with --execute: the --db name again')
            s.add_argument('--sleep', type=float, default=0.2)
        if name in ('apply', 'verify'):
            s.add_argument('--decisions', required=True)
        if name == 'apply':
            s.add_argument('--max-batches', type=int)
            s.add_argument('--previous-journal',
                           help='required to --execute a round after the first: '
                                'this database\'s journal of the round before')
            s.add_argument('--allow-duplicates', action='store_true',
                           help='also write rows whose file_id is already on '
                                'another entries row or another row of the file')

    args = p.parse_args(argv)
    try:
        if args.command == 'decide':
            counts, by_rule, coverage = decide(args.rows, args.out, args.round,
                                               args.allow_sample)
            print(json.dumps({'decisions': dict(counts), 'coverage': coverage,
                              'rules': dict(sorted(by_rule.items()))}, indent=1))
            return 0
        if not 1 <= args.batch_size <= 5000:
            p.exit(2, '--batch-size must be 1-5000\n')
        if getattr(args, 'execute', False) and args.confirm_db != args.db:
            raise BackfillError('--execute needs --confirm-db %s (the --db name '
                                'again, so a wrong database is noticed)' % args.db)
        target = '%s/%s' % (args.host, args.db)
        conn = _connect(args.host, args.db, args.defaults_file)
        if args.command == 'apply':
            apply_decisions(conn, args.decisions, args.journal, args.execute,
                            args.batch_size, args.max_batches, args.sleep,
                            previous_journal=args.previous_journal, target=target,
                            allow_duplicates=args.allow_duplicates)
        elif args.command == 'verify':
            verify(conn, args.decisions, args.batch_size, target=target)
        else:
            rollback(conn, args.journal, args.execute, args.batch_size, args.sleep,
                     target=target)
    except BackfillError as e:
        print('error: %s' % e, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
