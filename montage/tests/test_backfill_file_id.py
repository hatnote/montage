# -*- coding: utf-8 -*-
"""tools/backfill_file_id.py (hatnote/montage#660): decide, apply and rollback,
on a throwaway SQLite database with the columns of `entries` that matter."""
import io
import os
import json
import sqlite3
import importlib.util

import pytest

_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'backfill_file_id.py')
_spec = importlib.util.spec_from_file_location('backfill_file_id', _PATH)
bf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bf)

ROWS_HEADER = ('id\tcategory\tflags\tfile_id\tn_uploads\tn_versions\tn_archive\t'
               'first_seen\tlast_seen\tn_rounds\tevidence\n')


def rows_tsv(tmp_path, rows):
    """rows: (id, category, file_id, evidence dict)"""
    path = str(tmp_path / 'rows.tsv')
    with open(path, 'w') as f:
        f.write('#analyze_file_id v4 every=1\n' + ROWS_HEADER)
        for row_id, cat, file_id, ev in rows:
            f.write('%s\t%s\t\t%s\t1\t1\t0\t20200101000000\t20200201000000\t1\t%s\n'
                    % (row_id, cat, file_id, json.dumps(ev)))
    return path


@pytest.fixture
def conn():
    c = sqlite3.connect(':memory:')
    c.execute('CREATE TABLE entries (id INTEGER PRIMARY KEY, name TEXT, '
              'create_date TIMESTAMP, file_id BIGINT NULL)')
    c.executemany('INSERT INTO entries (id, name, create_date, file_id) '
                  'VALUES (?, ?, ?, ?)',
                  [(i, 'F%d.jpg' % i, '2020-01-01 00:00:00', None)
                   for i in range(1, 11)])
    c.commit()
    return c


def file_ids(conn):
    return dict(conn.execute('SELECT id, file_id FROM entries').fetchall())


def decided(tmp_path, rows, round_no=1, name='decisions.tsv', **kw):
    out = str(tmp_path / name)
    bf.decide(rows_tsv(tmp_path, rows), out, round_no, **kw)
    return out


# round 1 sets tier1 only; the others are set in later rounds
SAMPLE = [
    (1, 'tier1', 101, {}),
    (2, 'tier1', 102, {}),
    (3, 'tier1', 103, {}),
    (4, 'deleted_settled', '', {}),
    (5, 'deleted_mixed', 105, {}),
    (6, 'moved_away_tier1', '', {'moved_to_file_id': 106}),
    (7, 'restored', 107, {}),
]


# --- decide ----------------------------------------------------------------

def test_decide_rules(tmp_path):
    out = decided(tmp_path, SAMPLE)
    decisions, _ = bf.read_decisions(out)
    assert decisions == [(1, 'set', 101), (2, 'set', 102), (3, 'set', 103),
                         (4, 'null', None), (5, 'hold', None),
                         (6, 'hold', None), (7, 'hold', None)]


def test_rounds_are_disjoint_and_safest_first():
    assert bf.ROUNDS[1] == ('tier1',)
    cats = [c for r in sorted(bf.ROUNDS) for c in bf.ROUNDS[r]]
    assert len(cats) == len(set(cats))
    assert not set(cats) & bf.NULL


def test_decide_each_category_is_set_in_exactly_one_round(tmp_path):
    rows = [(i, c, 100 + i, {'moved_to_file_id': 100 + i})
            for i, c in enumerate(sorted(c for r in bf.ROUNDS.values() for c in r), 1)]
    sets = {}
    for r in bf.ROUNDS:
        out = decided(tmp_path, rows, round_no=r, name='d%d.tsv' % r)
        for row_id, decision, _ in bf.read_decisions(out)[0]:
            if decision == 'set':
                assert row_id not in sets
                sets[row_id] = r
    assert len(sets) == len(rows)


def test_decide_round_4_uses_moved_to_file_id(tmp_path):
    out = decided(tmp_path, SAMPLE, round_no=4)
    decisions, _ = bf.read_decisions(out)
    assert (6, 'set', 106) in decisions
    assert (1, 'hold', None) in decisions


def test_decide_other_round_rows_are_held(tmp_path):
    rows = [(1, 'tier1', 101, {}), (2, 'tier2a', 102, {}), (3, 'tier2b', 103, {})]
    decisions, _ = bf.read_decisions(decided(tmp_path, rows, round_no=2))
    assert decisions == [(1, 'hold', None), (2, 'set', 102), (3, 'hold', None)]


def test_decide_invalid_round(tmp_path):
    with pytest.raises(bf.BackfillError, match='round'):
        decided(tmp_path, SAMPLE, round_no=9)


def test_decide_unknown_category_is_held(tmp_path):
    out = decided(tmp_path, [(1, 'something_new', 101, {})])
    assert bf.read_decisions(out)[0] == [(1, 'hold', None)]


def test_decide_set_without_file_id_fails(tmp_path):
    with pytest.raises(bf.BackfillError, match='no file_id'):
        decided(tmp_path, [(1, 'tier1', '', {})])


def test_decide_bad_file_id_fails(tmp_path):
    with pytest.raises(bf.BackfillError):
        decided(tmp_path, [(1, 'tier1', 'abc', {})])
    with pytest.raises(bf.BackfillError):
        decided(tmp_path, [(1, 'tier1', 0, {})])


def test_decide_duplicate_id_fails(tmp_path):
    with pytest.raises(bf.BackfillError, match='twice'):
        decided(tmp_path, [(1, 'tier1', 101, {}), (1, 'tier1', 101, {})])


def test_decisions_file_has_no_names(tmp_path):
    out = decided(tmp_path, SAMPLE)
    assert '.jpg' not in open(out).read()


def test_read_decisions_rejects_tampering(tmp_path):
    out = decided(tmp_path, SAMPLE)
    text = open(out).read()
    for bad in (text.replace('\tset\t101', '\tdelete\t101'),
                text + '1\tset\t999\ttier1\t\tset:tier1\n',     # duplicate id
                text.replace('\tnull\t\t', '\tnull\t77\t')):   # file_id on a null row
        open(out, 'w').write(bad)
        with pytest.raises(bf.BackfillError):
            bf.read_decisions(out)


# --- apply -----------------------------------------------------------------

def run_apply(conn, tmp_path, decisions, execute, **kw):
    return bf.apply_decisions(conn, decisions, str(tmp_path / 'journal.tsv'),
                              execute=execute, sleep=0, out=io.StringIO(), **kw)


def test_dry_run_writes_nothing(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    counts = run_apply(conn, tmp_path, out, execute=False)
    assert counts['to_set'] == 3 and counts['not_set'] == 4
    assert set(file_ids(conn).values()) == {None}
    assert not os.path.exists(str(tmp_path / 'journal.tsv'))


def test_execute_sets_only_set_rows(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['to_set'] == 3
    ids = file_ids(conn)
    assert (ids[1], ids[2], ids[3]) == (101, 102, 103)
    assert all(ids[i] is None for i in (4, 5, 6, 7, 8, 9, 10))


def test_batches(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    counts = run_apply(conn, tmp_path, out, execute=True, batch_size=1)
    assert counts['to_set'] == 3
    assert file_ids(conn)[3] == 103


def test_idempotent(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['to_set'] == 0 and counts['already_same'] == 3


def test_never_overwrites_existing_file_id(conn, tmp_path):
    conn.execute('UPDATE entries SET file_id = 555 WHERE id = 1')
    conn.execute('UPDATE entries SET file_id = 102 WHERE id = 2')
    conn.commit()
    out = decided(tmp_path, SAMPLE)
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['conflict'] == 1 and counts['already_same'] == 1
    assert counts['to_set'] == 1
    assert file_ids(conn)[1] == 555


def test_missing_row_is_counted(conn, tmp_path):
    out = decided(tmp_path, [(99, 'tier1', 199, {}), (1, 'tier1', 101, {})])
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['missing'] == 1 and counts['to_set'] == 1


def test_max_batches_then_resume(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    counts = run_apply(conn, tmp_path, out, execute=True, batch_size=2, max_batches=1)
    assert counts['to_set'] == 2 and counts['unprocessed'] == 1
    counts = run_apply(conn, tmp_path, out, execute=True, batch_size=2)
    assert counts['to_set'] == 1 and counts['already_same'] == 2
    assert file_ids(conn)[3] == 103


def test_journal_of_a_different_decisions_file_is_refused(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    other = decided(tmp_path, SAMPLE + [(8, 'tier1', 108, {})])
    with pytest.raises(bf.BackfillError, match='Use a new journal'):
        run_apply(conn, tmp_path, other, execute=True)
    assert file_ids(conn)[8] is None


def test_journal_content(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    sha, entries = bf.read_journal(str(tmp_path / 'journal.tsv'))
    assert sha == bf.sha256_of(out)
    assert [(i, old, new) for _, i, old, new in entries] == [
        (1, None, 101), (2, None, 102), (3, None, 103)]


# --- rounds: the second round waits for the first ---------------------------

ROUND_ROWS = [(1, 'tier1', 101, {}), (2, 'tier1', 102, {}), (3, 'tier2a', 103, {})]


def apply_round(conn, tmp_path, n, previous=None, execute=True):
    out = decided(tmp_path, ROUND_ROWS, round_no=n, name='decisions-%d.tsv' % n)
    return bf.apply_decisions(conn, out, str(tmp_path / ('journal-%d.tsv' % n)),
                              execute=execute, sleep=0, out=io.StringIO(),
                              previous_journal=previous)


def test_round_2_needs_previous_journal(conn, tmp_path):
    with pytest.raises(bf.BackfillError, match='--previous-journal'):
        apply_round(conn, tmp_path, 2)
    assert file_ids(conn)[3] is None


def test_round_2_refuses_wrong_or_empty_previous_journal(conn, tmp_path):
    with pytest.raises(bf.BackfillError, match='does not exist'):
        apply_round(conn, tmp_path, 2, previous=str(tmp_path / 'nope.tsv'))
    apply_round(conn, tmp_path, 1)
    # the journal of round 1 is not the journal of round 2's predecessor 2
    with pytest.raises(bf.BackfillError, match='not the journal of round 3'):
        apply_round(conn, tmp_path, 4, previous=str(tmp_path / 'journal-1.tsv'))


def test_round_2_after_round_1(conn, tmp_path):
    apply_round(conn, tmp_path, 1)
    assert file_ids(conn)[3] is None
    counts = apply_round(conn, tmp_path, 2, previous=str(tmp_path / 'journal-1.tsv'))
    assert counts['to_set'] == 1 and file_ids(conn)[3] == 103
    assert file_ids(conn)[1] == 101


def test_round_2_dry_run_needs_no_previous_journal(conn, tmp_path):
    assert apply_round(conn, tmp_path, 2, execute=False)['to_set'] == 1


def test_rounds_roll_back_separately(conn, tmp_path):
    apply_round(conn, tmp_path, 1)
    apply_round(conn, tmp_path, 2, previous=str(tmp_path / 'journal-1.tsv'))
    bf.rollback(conn, str(tmp_path / 'journal-2.tsv'), execute=True, sleep=0,
                out=io.StringIO())
    ids = file_ids(conn)
    assert ids[3] is None and ids[1] == 101 and ids[2] == 102


# --- verify ----------------------------------------------------------------

def test_verify_counts_and_is_read_only(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    conn.execute('UPDATE entries SET file_id = 777 WHERE id = 2')
    conn.execute('UPDATE entries SET file_id = 555 WHERE id = 5')   # a hold row
    conn.execute('DELETE FROM entries WHERE id = 3')
    conn.commit()
    before = file_ids(conn)
    counts = bf.verify(conn, out, out=io.StringIO())
    assert counts['has_value'] == 1 and counts['other_value'] == 1
    assert counts['missing'] == 1
    assert counts['has_file_id'] == 1 and counts['not_touched'] == 3
    assert file_ids(conn) == before


def test_verify_before_apply(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    assert bf.verify(conn, out, out=io.StringIO())['still_null'] == 3


# --- rollback --------------------------------------------------------------

def run_rollback(conn, tmp_path, execute):
    return bf.rollback(conn, str(tmp_path / 'journal.tsv'), execute=execute,
                       sleep=0, out=io.StringIO())


def test_rollback_restores_exactly(conn, tmp_path):
    conn.execute('UPDATE entries SET file_id = 900 WHERE id = 9')   # not ours
    conn.commit()
    before = file_ids(conn)
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    assert run_rollback(conn, tmp_path, execute=True)['restored'] == 3
    assert file_ids(conn) == before


def test_rollback_dry_run_writes_nothing(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    counts = run_rollback(conn, tmp_path, execute=False)
    assert counts['restored'] == 3
    assert file_ids(conn)[1] == 101


def test_rollback_leaves_rows_changed_since(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    conn.execute('UPDATE entries SET file_id = 777 WHERE id = 2')
    conn.commit()
    counts = run_rollback(conn, tmp_path, execute=True)
    assert counts['restored'] == 2 and counts['changed_since'] == 1
    assert file_ids(conn)[2] == 777 and file_ids(conn)[1] is None


def test_rollback_is_idempotent(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    run_rollback(conn, tmp_path, execute=True)
    counts = run_rollback(conn, tmp_path, execute=True)
    assert counts['restored'] == 0 and counts['already_old'] == 3


def test_rollback_without_journal_fails(conn, tmp_path):
    with pytest.raises(bf.BackfillError):
        run_rollback(conn, tmp_path, execute=True)


# --- command line ----------------------------------------------------------

def test_cli_decide(tmp_path, capsys):
    rows = rows_tsv(tmp_path, SAMPLE)
    out = str(tmp_path / 'd.tsv')
    assert bf.main(['decide', '--round', '1', '--rows', rows, '--out', out]) == 0
    assert json.loads(capsys.readouterr().out)['decisions'] == {
        'set': 3, 'null': 1, 'hold': 3}


# --- findings of pr-check (A-F) --------------------------------------------

def jpath(tmp_path, name='journal.tsv'):
    return str(tmp_path / name)


# A. a killed run leaves a half-written journal line

def test_torn_journal_tail_is_ignored_and_trimmed(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    with open(jpath(tmp_path), 'a') as f:
        f.write('abc\t2026-10-26T00:00:00Z\t9\t\t10')     # no newline: torn
    assert len(bf.read_journal(jpath(tmp_path), err=io.StringIO())[1]) == 3
    # resume appends cleanly (the torn line is cut first), then rollback works
    run_apply(conn, tmp_path, out, execute=True)
    assert len(bf.read_journal(jpath(tmp_path))[1]) == 3
    assert run_rollback(conn, tmp_path, execute=True)['restored'] == 3


def test_rollback_with_torn_tail_does_not_crash(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    with open(jpath(tmp_path), 'a') as f:
        f.write('abc\tt\t9\t')
    assert run_rollback(conn, tmp_path, execute=True)['restored'] == 3


def test_malformed_journal_line_is_a_clean_error(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    text = open(jpath(tmp_path)).read()
    open(jpath(tmp_path), 'w').write(text + 'garbage line\n')
    with pytest.raises(bf.BackfillError, match='malformed'):
        bf.read_journal(jpath(tmp_path))


# B. a journal belongs to one database

def apply_on(conn, tmp_path, target, n=1, journal='journal.tsv', previous=None,
             execute=True, rows=ROUND_ROWS):
    out = decided(tmp_path, rows, round_no=n, name='decisions-%d.tsv' % n)
    return bf.apply_decisions(conn, out, jpath(tmp_path, journal), execute=execute,
                              sleep=0, out=io.StringIO(), previous_journal=previous,
                              target=target)


def test_previous_journal_of_another_database_is_refused(conn, tmp_path):
    apply_on(conn, tmp_path, 'host/copy', n=1, journal='copy-1.tsv')
    with pytest.raises(bf.BackfillError, match='written on database host/copy'):
        apply_on(conn, tmp_path, 'host/prod', n=2, journal='prod-2.tsv',
                 previous=jpath(tmp_path, 'copy-1.tsv'))
    assert file_ids(conn)[3] is None


def test_same_journal_path_on_another_database_is_refused(conn, tmp_path):
    apply_on(conn, tmp_path, 'host/copy', n=1)
    with pytest.raises(bf.BackfillError, match='Use a new journal'):
        apply_on(conn, tmp_path, 'host/prod', n=1)


def test_rollback_on_another_database_is_refused(conn, tmp_path):
    apply_on(conn, tmp_path, 'host/copy', n=1)
    with pytest.raises(bf.BackfillError, match='written on database host/copy'):
        bf.rollback(conn, jpath(tmp_path), execute=True, sleep=0, out=io.StringIO(),
                    target='host/prod')
    assert file_ids(conn)[1] == 101


def test_header_only_journal_still_binds_to_its_decisions(conn, tmp_path):
    # a journal whose run found nothing to write has a header and no entries
    apply_on(conn, tmp_path, 'host/copy', n=1, rows=[(1, 'tier2a', 101, {})])
    assert bf.read_journal(jpath(tmp_path))[1] == []
    with pytest.raises(bf.BackfillError, match='Use a new journal'):
        apply_on(conn, tmp_path, 'host/copy', n=1)


def test_dry_run_names_the_target(conn, tmp_path):
    out = io.StringIO()
    decisions = decided(tmp_path, SAMPLE)
    bf.apply_decisions(conn, decisions, jpath(tmp_path), execute=False, sleep=0,
                       out=out, target='host/copy')
    assert 'target host/copy: entries max id 10, 10 rows' in out.getvalue()


def test_cli_execute_needs_confirm_db(tmp_path, capsys):
    argv = ['apply', '--db', 'prod', '--decisions', 'd.tsv', '--journal', 'j.tsv',
            '--execute']
    assert bf.main(argv) == 1
    assert '--confirm-db prod' in capsys.readouterr().err
    assert bf.main(argv + ['--confirm-db', 'copy']) == 1


# C. the round gate looks at every row, not just the header

def test_row_that_does_not_belong_to_the_round_is_refused(tmp_path):
    out = decided(tmp_path, [(1, 'tier1', 101, {}), (7, 'tier2b', 107, {})])
    text = open(out).read()
    assert '7\thold\t\t' in text
    open(out, 'w').write(text.replace('7\thold\t\t', '7\tset\t107\t'))
    with pytest.raises(bf.BackfillError, match='not what round 1 decides'):
        bf.read_decisions(out)


def test_hand_edited_round_header_is_refused(conn, tmp_path):
    out = decided(tmp_path, [(1, 'tier1', 101, {}), (2, 'tier2a', 102, {})], round_no=2)
    text = open(out).read().replace('#round=2', '#round=1')
    open(out, 'w').write(text)
    with pytest.raises(bf.BackfillError):
        bf.read_decisions(out)


# D. duplicate file_ids

def test_file_id_already_on_another_row_is_held(conn, tmp_path):
    conn.execute('UPDATE entries SET file_id = 101 WHERE id = 9')
    conn.commit()
    out = decided(tmp_path, SAMPLE)
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['file_id_elsewhere'] == 1 and counts['to_set'] == 2
    assert file_ids(conn)[1] is None


def test_allow_duplicates_writes_them(conn, tmp_path):
    conn.execute('UPDATE entries SET file_id = 101 WHERE id = 9')
    conn.commit()
    out = decided(tmp_path, SAMPLE)
    counts = bf.apply_decisions(conn, out, jpath(tmp_path), execute=True, sleep=0,
                                out=io.StringIO(), allow_duplicates=True)
    assert counts['to_set'] == 3 and file_ids(conn)[1] == 101


def test_same_file_id_twice_in_file_writes_only_the_lowest_id(conn, tmp_path):
    rows = [(1, 'tier1', 101, {}), (2, 'tier1', 101, {}), (3, 'tier1', 103, {})]
    out = decided(tmp_path, rows)
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['duplicate_in_file'] == 1 and counts['to_set'] == 2
    assert file_ids(conn)[2] is None
    # a rerun keeps holding it
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['file_id_elsewhere'] == 1 and counts['to_set'] == 0


def test_duplicate_in_file_across_batches(conn, tmp_path):
    rows = [(1, 'tier1', 101, {}), (2, 'tier1', 101, {})]
    out = decided(tmp_path, rows)
    counts = run_apply(conn, tmp_path, out, execute=True, batch_size=1)
    assert counts['to_set'] == 1 and file_ids(conn)[2] is None


def test_verify_reports_shared_file_ids(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    conn.execute('UPDATE entries SET file_id = 101 WHERE id = 9')
    conn.commit()
    counts = bf.verify(conn, out, out=io.StringIO())
    assert counts['shared_file_id'] == 1
    assert counts['entries_with_duplicate_file_id'] == 1


# E. a sampled analysis is not the full one

def sampled_rows(tmp_path, every):
    path = rows_tsv(tmp_path, SAMPLE)
    text = open(path).read().replace('every=1', 'every=%d' % every, 1)
    open(path, 'w').write(text)
    return path


def test_decide_refuses_a_sample(tmp_path):
    with pytest.raises(bf.BackfillError, match='sample'):
        bf.decide(sampled_rows(tmp_path, 200), str(tmp_path / 'd.tsv'), 1)


def test_decide_refuses_rows_without_every_header(tmp_path):
    path = rows_tsv(tmp_path, SAMPLE)
    open(path, 'w').write(open(path).read().replace('#analyze_file_id v4 every=1\n', ''))
    with pytest.raises(bf.BackfillError, match='every='):
        bf.decide(path, str(tmp_path / 'd.tsv'), 1)


def test_sample_decisions_cannot_be_executed(conn, tmp_path):
    out = str(tmp_path / 'd.tsv')
    _, _, coverage = bf.decide(sampled_rows(tmp_path, 200), out, 1, allow_sample=True)
    assert coverage['sample'] is True
    assert run_apply(conn, tmp_path, out, execute=False)['to_set'] == 3
    with pytest.raises(bf.BackfillError, match='sampled'):
        run_apply(conn, tmp_path, out, execute=True)


def test_decide_reports_coverage(tmp_path):
    _, _, coverage = bf.decide(rows_tsv(tmp_path, SAMPLE), str(tmp_path / 'd.tsv'), 1)
    assert coverage == {'rows': 7, 'min_id': 1, 'max_id': 7, 'sample': False}


# F. an id must still be the same row

def test_row_with_another_create_date_is_held(conn, tmp_path):
    conn.execute("UPDATE entries SET create_date = '2024-05-05 05:05:05' WHERE id = 2")
    conn.commit()
    out = decided(tmp_path, SAMPLE)
    counts = run_apply(conn, tmp_path, out, execute=True)
    assert counts['identity_mismatch'] == 1 and counts['to_set'] == 2
    assert file_ids(conn)[2] is None
    assert bf.verify(conn, out, out=io.StringIO())['identity_mismatch'] == 1


def test_row_without_a_create_date_in_the_analysis_is_not_checked(conn, tmp_path):
    path = rows_tsv(tmp_path, [(1, 'tier1', 101, {})])
    text = open(path).read().replace('20200101000000', '', 1)
    open(path, 'w').write(text)
    out = str(tmp_path / 'd.tsv')
    bf.decide(path, out, 1)
    assert run_apply(conn, tmp_path, out, execute=True)['to_set'] == 1


def test_norm_ts():
    import datetime
    assert bf.norm_ts(datetime.datetime(2020, 1, 2, 3, 4, 5)) == '20200102030405'
    assert bf.norm_ts('2020-01-02 03:04:05') == '20200102030405'
    assert bf.norm_ts(None) == '' and bf.norm_ts('0000-00-00 00:00:00') == ''


# should-fix

def test_max_batches_advances_across_runs(conn, tmp_path):
    rows = [(i, 'tier1', 100 + i, {}) for i in range(1, 7)]
    out = decided(tmp_path, rows)
    total = 0
    for _ in range(3):
        counts = run_apply(conn, tmp_path, out, execute=True, batch_size=2,
                           max_batches=1)
        total += counts['to_set']
    assert total == 6 and all(v is not None for i, v in file_ids(conn).items() if i <= 6)
