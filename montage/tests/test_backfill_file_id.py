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
    c.execute('CREATE TABLE entries (id INTEGER PRIMARY KEY, name TEXT, file_id BIGINT NULL)')
    c.executemany('INSERT INTO entries (id, name, file_id) VALUES (?, ?, ?)',
                  [(i, 'F%d.jpg' % i, None) for i in range(1, 11)])
    c.commit()
    return c


def file_ids(conn):
    return dict(conn.execute('SELECT id, file_id FROM entries').fetchall())


def decided(tmp_path, rows, **kw):
    out = str(tmp_path / 'decisions.tsv')
    bf.decide(rows_tsv(tmp_path, rows), out, **kw)
    return out


SAMPLE = [
    (1, 'tier1', 101, {}),
    (2, 'tier2a', 102, {}),
    (3, 'changed_after', 103, {}),
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


def test_decide_moved_away_only_when_asked(tmp_path):
    out = decided(tmp_path, SAMPLE, include_moved_away=True)
    decisions, _ = bf.read_decisions(out)
    assert (6, 'set', 106) in decisions


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
    with pytest.raises(bf.BackfillError, match='different decisions file'):
        run_apply(conn, tmp_path, other, execute=True)
    assert file_ids(conn)[8] is None


def test_journal_content(conn, tmp_path):
    out = decided(tmp_path, SAMPLE)
    run_apply(conn, tmp_path, out, execute=True)
    sha, entries = bf.read_journal(str(tmp_path / 'journal.tsv'))
    assert sha == bf.sha256_of(out)
    assert [(i, old, new) for _, i, old, new in entries] == [
        (1, None, 101), (2, None, 102), (3, None, 103)]


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
    assert counts['restored'] == 0 and counts['changed_since'] == 3


def test_rollback_without_journal_fails(conn, tmp_path):
    with pytest.raises(bf.BackfillError):
        run_rollback(conn, tmp_path, execute=True)


# --- command line ----------------------------------------------------------

def test_cli_decide(tmp_path, capsys):
    rows = rows_tsv(tmp_path, SAMPLE)
    out = str(tmp_path / 'd.tsv')
    assert bf.main(['decide', '--rows', rows, '--out', out]) == 0
    assert json.loads(capsys.readouterr().out)['decisions'] == {
        'set': 3, 'null': 1, 'hold': 3}
