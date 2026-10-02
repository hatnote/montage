# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import

import os

import pytest
import responses
from pytest import raises

from montage.loaders import get_entries_from_gsheet, make_entry

from .conftest import (
    FIXTURE_FILE_INFOS,
    FIXTURE_FULL_CSV,
    FIXTURE_FILENAME_CSV,
    TOOLFORGE_FILE_URL,
    REUPLOAD_FILE_INFO,
)

RESULTS = 'https://docs.google.com/spreadsheets/d/1RDlpT23SV_JB1mIz0OA-iuc3MNdNVLbaK_LtWAC7vzg/edit?usp=sharing'
FILENAME_LIST = 'https://docs.google.com/spreadsheets/d/1Nqj-JsX3L5qLp5ITTAcAFYouglbs5OpnFwP6zSFpa0M/edit?usp=sharing'
GENERIC_CSV = 'https://docs.google.com/spreadsheets/d/1WzHFg_bhvNthRMwNmxnk010KJ8fwuyCrby29MvHUzH8/edit#gid=550467819'
FORBIDDEN_SHEET = 'https://docs.google.com/spreadsheets/d/1tza92brMKkZBTykw3iS6X9ij1D4_kvIYAiUlq1Yi7Fs/edit'

# Pre-compute the actual fetch URLs that loaders.py constructs from the
# doc IDs embedded in the spreadsheet URLs above.
_RESULTS_CSV_URL = 'https://docs.google.com/spreadsheets/d/1RDlpT23SV_JB1mIz0OA-iuc3MNdNVLbaK_LtWAC7vzg/gviz/tq?tqx=out:csv'
_FILENAME_CSV_URL = 'https://docs.google.com/spreadsheets/d/1Nqj-JsX3L5qLp5ITTAcAFYouglbs5OpnFwP6zSFpa0M/gviz/tq?tqx=out:csv'
_GENERIC_CSV_URL = 'https://docs.google.com/spreadsheets/d/1WzHFg_bhvNthRMwNmxnk010KJ8fwuyCrby29MvHUzH8/gviz/tq?tqx=out:csv'
_FORBIDDEN_CSV_URL = 'https://docs.google.com/spreadsheets/d/1tza92brMKkZBTykw3iS6X9ij1D4_kvIYAiUlq1Yi7Fs/gviz/tq?tqx=out:csv'


@responses.activate
def test_load_results():
    """Full CSV with all required columns -- entries created directly."""
    responses.add(
        responses.GET,
        _RESULTS_CSV_URL,
        body=FIXTURE_FULL_CSV,
        status=200,
        content_type='text/csv',
    )
    imgs, warnings = get_entries_from_gsheet(RESULTS, source='remote')
    assert len(imgs) == len(FIXTURE_FILE_INFOS)


@responses.activate
def test_load_filenames():
    """Partial CSV with only 'filename' column -- triggers Toolforge lookup."""
    responses.add(
        responses.GET,
        _FILENAME_CSV_URL,
        body=FIXTURE_FILENAME_CSV,
        status=200,
        content_type='text/csv',
    )
    # The filename-only CSV triggers load_partial_csv -> load_name_list
    # -> get_by_filename_remote -> POST to Toolforge /file endpoint.
    responses.add(
        responses.POST,
        TOOLFORGE_FILE_URL,
        json={'file_infos': FIXTURE_FILE_INFOS, 'no_info': []},
        status=200,
    )
    imgs, warnings = get_entries_from_gsheet(FILENAME_LIST, source='remote')
    assert len(imgs) == len(FIXTURE_FILE_INFOS)


@responses.activate
def test_load_csv():
    """Generic full CSV -- same path as test_load_results."""
    responses.add(
        responses.GET,
        _GENERIC_CSV_URL,
        body=FIXTURE_FULL_CSV,
        status=200,
        content_type='text/csv',
    )
    imgs, warnings = get_entries_from_gsheet(GENERIC_CSV, source='remote')
    assert len(imgs) == len(FIXTURE_FILE_INFOS)


@responses.activate
def test_no_persmission():
    """Non-CSV content-type signals a permission / sharing error."""
    responses.add(
        responses.GET,
        _FORBIDDEN_CSV_URL,
        body='<html><body>Sign in</body></html>',
        status=200,
        content_type='text/html',
    )
    with raises(ValueError):
        get_entries_from_gsheet(FORBIDDEN_SHEET, source='remote')


def test_make_entry_reupload():
    """make_entry() correctly handles a reuploaded file."""
    entry = make_entry(REUPLOAD_FILE_INFO)
    assert entry.flags['reupload'] is True
    assert entry.flags['reupload_user_id'] == '2222'
    assert entry.file_id == 2


# ---------------------------------------------------------------------------
# Category membership comes from the Commons links replica (x4) since
# 2026-09-08; file data from the main replica. The two are joined in code.
# ---------------------------------------------------------------------------

class _FakeCursor(object):
    def __init__(self, conn):
        self.conn = conn
        self.rows = None

    def execute(self, query, params):
        assert not self.conn.closed
        self.conn.queries += 1
        self.rows = self.conn.fetch(query, params, db_host=self.conn.db_host)

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class _FakeConnection(object):
    """Stands in for a pymysql connection; each query is answered by a
    fetchall_from_commonswiki-style function fetch(query, params, db_host)."""
    def __init__(self, db_host, fetch):
        self.db_host = db_host
        self.fetch = fetch
        self.queries = 0
        self.closed = False

    def cursor(self):
        return _FakeCursor(self)

    def close(self):
        self.closed = True


def _patch_replicas(monkeypatch, fetch):
    """Replace labs._connect with fake connections answered by fetch;
    returns the list of connections opened."""
    from montage import labs
    opened = []

    def connect(db_host):
        opened.append(_FakeConnection(db_host, fetch))
        return opened[-1]
    monkeypatch.setattr(labs, '_connect', connect)
    return opened


def _fake_replicas(links_rows, file_rows, calls):
    """A replica stand-in: category members from the
    links replica, file details from the main replica."""
    from montage import labs

    def fake(query, params, db_host=labs.COMMONS_DB_HOST):
        calls.append((db_host, query, params))
        if db_host == labs.COMMONS_LINKS_DB_HOST:
            assert 'categorylinks' in query and 'file AS file' not in query
            return [{'file_name': n} for n in links_rows]
        assert 'categorylinks' not in query and 'linktarget' not in query
        return [dict(file_rows[n]) for n in params if n in file_rows]
    return fake


def _file_row(name, file_id):
    return {'img_name': name, 'img_width': 3000, 'img_height': 2000,
            'img_major_mime': 'image', 'img_minor_mime': 'jpeg',
            'img_user': 1, 'img_user_text': 'Uploader',
            'img_timestamp': '20260910120000',
            'rec_img_timestamp': '20260910120000', 'rec_img_user': 1,
            'rec_img_text': 'Uploader', 'oi_archive_name': None,
            'file_id': file_id}


def test_get_files_reads_members_from_links_replica(monkeypatch):
    from montage import labs
    names = ['B_file.jpg', 'A_file.jpg', 'Café_ü.jpg', 'A_file.jpg']
    file_rows = {n: _file_row(n, i) for i, n in enumerate(set(names))}
    calls = []
    _patch_replicas(monkeypatch, _fake_replicas(names, file_rows, calls))

    result = labs.get_files('Images from Wiki Loves Monuments 2026 in Russia')

    assert calls[0][0] == labs.COMMONS_LINKS_DB_HOST
    assert calls[0][2] == ('Images_from_Wiki_Loves_Monuments_2026_in_Russia',)
    assert all(host == labs.COMMONS_DB_HOST for host, _, _ in calls[1:])
    # one row per file, duplicates collapsed, binary name order as before
    assert [r['img_name'] for r in result] == ['A_file.jpg', 'B_file.jpg', 'Café_ü.jpg']
    assert set(result[0]) == set(_file_row('x', 0))  # output keys unchanged


def test_get_files_looks_up_files_in_chunks(monkeypatch):
    from montage import labs
    monkeypatch.setattr(labs, 'FILE_LOOKUP_CHUNK_SIZE', 3)
    names = ['F%02d.jpg' % i for i in range(8)]
    file_rows = {n: _file_row(n, i) for i, n in enumerate(names)}
    calls = []
    _patch_replicas(monkeypatch, _fake_replicas(names, file_rows, calls))

    result = labs.get_files('Some category')

    lookups = [params for host, _, params in calls if host == labs.COMMONS_DB_HOST]
    assert [len(p) for p in lookups] == [3, 3, 2]
    assert [r['img_name'] for r in result] == names


def test_get_files_skips_members_without_a_file_row(monkeypatch):
    """A member with no live file row (deleted) is left out, as the old
    inner JOIN did."""
    from montage import labs
    names = ['Kept.jpg', 'Deleted.jpg']
    calls = []
    _patch_replicas(monkeypatch, _fake_replicas(names, {'Kept.jpg': _file_row('Kept.jpg', 1)}, calls))

    assert [r['img_name'] for r in labs.get_files('Cat')] == ['Kept.jpg']


def test_get_files_empty_category_makes_no_file_lookup(monkeypatch):
    from montage import labs
    calls = []
    _patch_replicas(monkeypatch, _fake_replicas([], {}, calls))

    assert labs.get_files('Empty category') == []
    assert [host for host, _, _ in calls] == [labs.COMMONS_LINKS_DB_HOST]


@pytest.mark.xfail(
    os.environ.get('TOOLFORGE') != '1',
    reason='Requires live wikireplicas (Toolforge); set TOOLFORGE=1 to run',
)
def test_get_files_sees_files_added_after_links_split():
    """On 2026-10-01 the stale main-replica copy of categorylinks had 5,005
    links for this category and the links replica 15,678. get_files must
    follow the links replica."""
    from montage.labs import get_category_file_names, get_files
    category = 'Images_from_Wiki_Loves_Monuments_2026_in_Russia'
    members = get_category_file_names(category)
    files = get_files(category)
    assert len(members) > 10000
    assert len(files) >= 0.99 * len(set(members))


# ---------------------------------------------------------------------------
# File-list imports look names up in batches, not one query per file
# (a 1000+ name list outlasted the 30 s request timeout on montage-beta).
# ---------------------------------------------------------------------------

def _fake_main_replica(existing, calls):
    from montage import labs

    def fake(query, params, db_host=labs.COMMONS_DB_HOST):
        assert db_host == labs.COMMONS_DB_HOST
        calls.append(params)
        return [_file_row(n, i) for i, n in enumerate(params) if n in existing]
    return fake


def test_load_by_filename_batches_lookups(monkeypatch):
    from montage import labs, loaders
    monkeypatch.setattr(labs, 'FILE_LOOKUP_CHUNK_SIZE', 4)
    names = ['File %02d.jpg' % i for i in range(10)]
    existing = {n.replace(' ', '_') for n in names}
    calls = []
    _patch_replicas(monkeypatch, _fake_main_replica(existing, calls))

    entries, warnings = loaders.load_by_filename(names, source='local')

    assert [len(c) for c in calls] == [4, 4, 2]  # 3 queries, not 10
    assert [e.name for e in entries] == [n.replace(' ', '_') for n in names]
    assert warnings == []


def test_load_by_filename_warns_per_missing_name_in_input_order(monkeypatch):
    from montage import labs, loaders
    calls = []
    _patch_replicas(monkeypatch, _fake_main_replica({'B.jpg'}, calls))

    entries, warnings = loaders.load_by_filename(['Z missing.jpg', 'B.jpg', 'A missing.jpg'],
                                                 source='local')

    assert [e.name for e in entries] == ['B.jpg']
    assert len(warnings) == 2
    assert '"Z missing.jpg"' in warnings[0] and '"A missing.jpg"' in warnings[1]


def test_load_name_list_local(monkeypatch):
    """CSV with only file names, local source: used to unpack the file info
    dict into (edict, warnings) and fail."""
    from io import StringIO
    from montage import labs, loaders
    calls = []
    _patch_replicas(monkeypatch, _fake_main_replica({'One.jpg', 'Two_words.jpg'}, calls))

    entries, warnings = loaders.load_name_list(
        StringIO('File:One.jpg\nTwo words.jpg\nGone.jpg\n'), source='local')

    assert [e.name for e in entries] == ['One.jpg', 'Two_words.jpg']
    assert len(calls) == 1
    assert len(warnings) == 1 and '"Gone.jpg"' in warnings[0]


def test_round_source_params_hold_large_file_lists():
    """A 'selected' import stores its whole file list in round_sources.params;
    1000+ names pass TEXT's 64 KB, so the column is MEDIUMTEXT on MySQL."""
    from sqlalchemy import create_engine
    from sqlalchemy.dialects import mysql
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.schema import CreateTable
    from montage.rdb import Base, RoundSource

    ddl = str(CreateTable(RoundSource.__table__).compile(dialect=mysql.dialect()))
    assert 'params MEDIUMTEXT' in ddl

    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    names = ['Wiki_Loves_Monuments_2026_in_Russia_photo_%05d.jpg' % i for i in range(2000)]
    session.add(RoundSource(method='selected', params={'file_names': names}))
    session.commit()
    stored = session.query(RoundSource).one().params
    assert stored['file_names'] == names
    assert len(str(stored)) > 64 * 1024


def test_get_files_order_is_binary_like_the_old_query(monkeypatch):
    """Uppercase sorts before lowercase, as the old ORDER BY on the binary
    file_name column did; a case-insensitive sort would differ."""
    from montage import labs
    names = ['b_lower.jpg', 'B_upper.jpg', 'a_lower.jpg', 'A_upper.jpg', 'Ö_umlaut.jpg']
    calls = []
    _patch_replicas(monkeypatch, _fake_replicas(names, {n: _file_row(n, i) for i, n in enumerate(names)}, calls))

    result = [r['img_name'] for r in labs.get_files('Cat')]

    assert result == ['A_upper.jpg', 'B_upper.jpg', 'a_lower.jpg', 'b_lower.jpg', 'Ö_umlaut.jpg']


def test_load_by_filename_duplicates_and_space_underscore_pairs(monkeypatch):
    """'A b.jpg' and 'A_b.jpg' are the same Commons file; both requests
    resolve, with one query."""
    from montage import labs, loaders
    calls = []
    _patch_replicas(monkeypatch, _fake_main_replica({'A_b.jpg'}, calls))

    entries, warnings = loaders.load_by_filename(['A b.jpg', 'A_b.jpg', 'A b.jpg'], source='local')

    assert [e.name for e in entries] == ['A_b.jpg'] * 3
    assert warnings == [] and len(calls) == 1 and calls[0] == ('A_b.jpg',)


# ---------------------------------------------------------------------------
# One replica connection per lookup (per database host), closed afterwards,
# not one per 500-name chunk (hatnote/montage#625).
# ---------------------------------------------------------------------------

def test_get_files_uses_one_connection_per_replica(monkeypatch):
    from montage import labs
    monkeypatch.setattr(labs, 'FILE_LOOKUP_CHUNK_SIZE', 3)
    names = ['F%02d.jpg' % i for i in range(8)]
    calls = []
    opened = _patch_replicas(monkeypatch, _fake_replicas(
        names, {n: _file_row(n, i) for i, n in enumerate(names)}, calls))

    assert len(labs.get_files('Some category')) == 8

    # links + main, although the main replica answered 3 chunk queries
    assert [c.db_host for c in opened] == [labs.COMMONS_LINKS_DB_HOST,
                                           labs.COMMONS_DB_HOST]
    assert [c.queries for c in opened] == [1, 3]
    assert all(c.closed for c in opened)


def test_get_files_info_by_names_uses_one_connection(monkeypatch):
    from montage import labs
    monkeypatch.setattr(labs, 'FILE_LOOKUP_CHUNK_SIZE', 4)
    names = ['File %02d.jpg' % i for i in range(10)]
    calls = []
    opened = _patch_replicas(monkeypatch, _fake_main_replica(
        {n.replace(' ', '_') for n in names}, calls))

    assert len(labs.get_files_info_by_names(names)) == 10

    assert [len(c) for c in calls] == [4, 4, 2]
    assert [(c.db_host, c.queries, c.closed) for c in opened] == [
        (labs.COMMONS_DB_HOST, 3, True)]


def test_replica_connection_is_closed_when_a_query_fails(monkeypatch):
    from montage import labs

    def failing(query, params, db_host=labs.COMMONS_DB_HOST):
        raise RuntimeError('replica went away')
    opened = _patch_replicas(monkeypatch, failing)

    with pytest.raises(RuntimeError):
        labs.get_files_info_by_names(['A.jpg'])
    with pytest.raises(RuntimeError):
        labs.fetchall_from_commonswiki('SELECT 1', ())

    assert len(opened) == 2 and all(c.closed for c in opened)
