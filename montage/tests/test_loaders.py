# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import

import os

import pytest
import responses
from pytest import raises

from montage.loaders import (make_entry, parse_source_rows, parse_name_list,
                             parse_file_id, normalise_name, fetch_source_text,
                             guard_cell, unguard_cell)
from montage.utils import ImportSourceInvalid

from .conftest import (
    FIXTURE_FILE_INFOS,
    FIXTURE_FULL_CSV,
    FIXTURE_FILENAME_CSV,
    REUPLOAD_FILE_INFO,
)

RESULTS = 'https://docs.google.com/spreadsheets/d/1RDlpT23SV_JB1mIz0OA-iuc3MNdNVLbaK_LtWAC7vzg/edit?usp=sharing'
FORBIDDEN_SHEET = 'https://docs.google.com/spreadsheets/d/1tza92brMKkZBTykw3iS6X9ij1D4_kvIYAiUlq1Yi7Fs/edit'

# Pre-compute the actual fetch URLs that loaders.py constructs from the
# doc IDs embedded in the spreadsheet URLs above.
_RESULTS_CSV_URL = 'https://docs.google.com/spreadsheets/d/1RDlpT23SV_JB1mIz0OA-iuc3MNdNVLbaK_LtWAC7vzg/gviz/tq?tqx=out:csv'
_FORBIDDEN_CSV_URL = 'https://docs.google.com/spreadsheets/d/1tza92brMKkZBTykw3iS6X9ij1D4_kvIYAiUlq1Yi7Fs/gviz/tq?tqx=out:csv'


# ---------------------------------------------------------------------------
# Fetching a source (hatnote/montage#510): no Commons lookup here
# ---------------------------------------------------------------------------

@responses.activate
def test_fetch_sheet_returns_its_csv_text():
    responses.add(responses.GET, _RESULTS_CSV_URL, body=FIXTURE_FULL_CSV,
                  status=200, content_type='text/csv')
    assert fetch_source_text(RESULTS) == FIXTURE_FULL_CSV
    assert len(responses.calls) == 1


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
    with raises(ImportSourceInvalid):
        fetch_source_text(FORBIDDEN_SHEET)


@responses.activate
def test_fetch_gist_rewrites_the_link_and_strips_the_bom():
    responses.add(responses.GET, 'https://gist.githubusercontent.com/u/abc/raw',
                  body=u'\ufefffilename\nA.jpg\n'.encode('utf8'), status=200)
    assert fetch_source_text('https://gist.github.com/u/abc') == 'filename\nA.jpg\n'


@responses.activate
def test_fetch_errors_are_import_source_invalid():
    responses.add(responses.GET, 'https://gist.githubusercontent.com/u/gone/raw',
                  body='Not Found', status=404)
    with raises(ImportSourceInvalid) as exc:
        fetch_source_text('https://gist.github.com/u/gone')
    assert '404' in exc.value.detail
    with raises(ImportSourceInvalid):  # unregistered: ConnectionError
        fetch_source_text('https://gist.github.com/u/unreachable')
    with raises(ImportSourceInvalid):
        fetch_source_text('https://docs.google.com/spreadsheets/nodoc')
    with raises(ImportSourceInvalid):
        fetch_source_text('  ')


# ---------------------------------------------------------------------------
# Parsing a source
# ---------------------------------------------------------------------------

def _names(rows):
    return [r['name'] for r in rows]


def test_parse_filename_csv():
    rows, columns = parse_source_rows(FIXTURE_FILENAME_CSV)
    assert _names(rows) == [i['img_name'] for i in FIXTURE_FILE_INFOS]
    assert [r['row'] for r in rows[:2]] == [2, 3]  # header is row 1
    assert columns == {'name': 'filename', 'file_id': None, 'ignored': []}


def test_parse_full_csv_reads_only_the_name_column():
    """#509: metadata columns are ignored; Commons supplies them."""
    rows, columns = parse_source_rows(FIXTURE_FULL_CSV)
    assert _names(rows) == [i['img_name'] for i in FIXTURE_FILE_INFOS]
    assert columns['name'] == 'img_name'
    assert 'img_width' in columns['ignored'] and 'img_name' not in columns['ignored']
    assert set(rows[0]) == {'row', 'name_as_written', 'file_id_as_written',
                            'name', 'file_id', 'malformed_file_id'}


def test_parse_headers_case_bom_and_preference():
    rows, columns = parse_source_rows(u'\ufeffFile_ID, FileName ,img_name,File ID\n'
                                      u'42,A b.jpg,Other.jpg,x\n')
    assert columns == {'name': 'filename', 'file_id': 'file_id',
                       'ignored': ['img_name', 'File ID']}
    assert rows[0]['name'] == 'A_b.jpg' and rows[0]['file_id'] == 42
    assert rows[0]['name_as_written'] == 'A b.jpg'


def test_parse_rejects_columns_without_a_name_column():
    with raises(ImportSourceInvalid) as exc:
        parse_source_rows('a,b\n1,2\n')
    assert 'no filename or img_name column' in exc.value.detail


def test_parse_header_less_lists():
    # a gist: commas in names survive, File: prefixes go, blank lines keep numbers
    rows, columns = parse_source_rows('Foo, bar.jpg\n\nFile:Baz qux.png\n')
    assert [(r['row'], r['name']) for r in rows] == [(1, 'Foo,_bar.jpg'),
                                                      (3, 'Baz_qux.png')]
    assert columns['name'] is None
    # a one-column Google Sheet export: quoted cells
    rows, _ = parse_source_rows('"Foo, bar.jpg"\n"Two.jpg"\n')
    assert _names(rows) == ['Foo,_bar.jpg', 'Two.jpg']
    # one column with an unknown header word: read as a name (as before)
    rows, _ = parse_source_rows('files\nOne.jpg\n')
    assert _names(rows) == ['Files', 'One.jpg']  # first letter canonical


def test_parse_file_id_cells():
    assert parse_file_id('149673020') == (149673020, False)
    assert parse_file_id(u' 12\xa0') == (12, False)
    assert parse_file_id('') == (None, False)
    assert parse_file_id('  ') == (None, False)
    for bad in ['1.49673E+08', '149,673,020', '12.0', 'abc', '0', '-5', '1 2']:
        assert parse_file_id(bad) == (None, True), bad


def test_parse_short_rows_and_malformed_ids():
    rows, _ = parse_source_rows('filename,file_id\nA.jpg\nB.jpg,1.2E+3\n,\n,7\n')
    assert [(r['row'], r['name'], r['file_id'], r['malformed_file_id'])
            for r in rows] == [(2, 'A.jpg', None, False),
                               (3, 'B.jpg', None, True),
                               (5, '', 7, False)]


def test_parse_name_list():
    rows = parse_name_list(['File:A b.jpg', '', '  ', 'C.jpg'])
    assert [(r['row'], r['name']) for r in rows] == [(1, 'A_b.jpg'), (4, 'C.jpg')]
    assert _names(parse_name_list('A.jpg\nB.jpg')) == ['A.jpg', 'B.jpg']
    with raises(ImportSourceInvalid):
        parse_name_list(None)


def test_formula_guard_round_trip():
    for name in ['=SUM(A1).jpg', '+1.jpg', '-x.jpg', '@me.jpg', "'s-Hertogenbosch.jpg",
                 "''x.jpg", 'Plain.jpg']:
        assert unguard_cell(guard_cell(name)) == name
        assert normalise_name(guard_cell(name)) == name
    assert guard_cell('=x.jpg') == "'=x.jpg"
    assert normalise_name("'s-Hertogenbosch.jpg") == "'s-Hertogenbosch.jpg"


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


def test_lookup_by_names_batches_lookups(monkeypatch):
    from montage import labs, loaders
    monkeypatch.setattr(labs, 'FILE_LOOKUP_CHUNK_SIZE', 4)
    names = ['File_%02d.jpg' % i for i in range(10)]
    calls = []
    _patch_replicas(monkeypatch, _fake_main_replica(set(names), calls))

    found = loaders.lookup_by_names(names + names[:3], source='local')

    assert [len(c) for c in calls] == [4, 4, 2]  # 3 queries, not 10
    assert sorted(found) == names


def test_lookup_by_names_remote_keys_by_normalised_name(mock_external_apis):
    from montage import loaders
    from .conftest import SELECTED_FILE_INFO
    name = normalise_name(SELECTED_FILE_INFO['img_name'])  # remote: spaces
    found = loaders.lookup_by_names([name, 'Not_there.jpg'], source='remote')
    assert list(found) == [name]


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


def _labs_hosts(env):
    """(COMMONS_DB_HOST, COMMONS_LINKS_DB_HOST) as a fresh interpreter
    computes them at import, with these MONTAGE_COMMONS_* variables."""
    import subprocess
    import sys
    run_env = dict(os.environ)
    run_env.pop('MONTAGE_COMMONS_DB_HOST', None)
    run_env.pop('MONTAGE_COMMONS_LINKS_DB_HOST', None)
    run_env.update(env)
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    out = subprocess.check_output(
        [sys.executable, '-c',
         'import montage.labs as l; print(l.COMMONS_DB_HOST); '
         'print(l.COMMONS_LINKS_DB_HOST)'],
        env=run_env, cwd=root)
    return tuple(out.decode('utf8').split())


def test_replica_hosts_default_to_the_analytics_replicas():
    assert _labs_hosts({}) == (
        'commonswiki.analytics.db.svc.wikimedia.cloud',
        'links.commonswiki.analytics.db.svc.wikimedia.cloud')


def test_replica_hosts_can_be_set_by_environment():
    assert _labs_hosts({'MONTAGE_COMMONS_DB_HOST': 'main.example',
                        'MONTAGE_COMMONS_LINKS_DB_HOST': 'links.example'}) == (
        'main.example', 'links.example')


# ---------------------------------------------------------------------------
# Lookup by file_id (hatnote/montage#510): same query as by name, other column
# ---------------------------------------------------------------------------

# _files_by_name's query as on master 939d890, copied verbatim: the shared
# query builder must not change the SQL that the name lookups send.
_MASTER_FILES_BY_NAME_SQL = '''
        SELECT DISTINCT {cols}
        FROM commonswiki_p.file AS file
        JOIN commonswiki_p.filerevision AS fr ON fr.fr_id = file.file_latest
          AND fr.fr_deleted = 0
        LEFT JOIN actor AS ci ON fr.fr_actor = ci.actor_id
        LEFT JOIN commonswiki_p.filetypes AS ft ON file.file_type = ft.ft_id
        {earliest_rev}
        WHERE file.file_name IN ({names})
          AND file.file_deleted = 0
    '''


def test_files_by_name_sql_unchanged():
    from montage import labs
    seen = []
    labs._files_by_name(lambda q, p: seen.append((q, p)) or [], ['A.jpg', 'B.jpg'])
    expected = _MASTER_FILES_BY_NAME_SQL.format(
        cols=', '.join(labs.FILE_COLS),
        earliest_rev=labs._EARLIEST_REVISION_SUBQUERY,
        names='%s, %s')
    assert seen == [(expected, ('A.jpg', 'B.jpg'))]


def _fake_main_replica_by_id(existing, calls):
    """existing: {file_id: name}; answers lookups by file_id."""
    from montage import labs

    def fake(query, params, db_host=labs.COMMONS_DB_HOST):
        assert db_host == labs.COMMONS_DB_HOST
        assert 'WHERE file.file_id IN (' in query
        assert 'file.file_deleted = 0' in query and 'fr.fr_deleted = 0' in query
        calls.append(params)
        return [_file_row(existing[i], i) for i in params if i in existing]
    return fake


def test_get_files_info_by_ids_batches_one_connection(monkeypatch):
    from montage import labs
    monkeypatch.setattr(labs, 'FILE_LOOKUP_CHUNK_SIZE', 3)
    existing = {i: 'F%02d.jpg' % i for i in range(1, 9)}
    calls = []
    opened = _patch_replicas(monkeypatch, _fake_main_replica_by_id(existing, calls))

    found = labs.get_files_info_by_ids(['8', 7, 6, 5, 4, 3, 2, 1, 1, 99])

    assert [len(c) for c in calls] == [3, 3, 3]  # 9 distinct ids, as ints
    assert all(isinstance(i, int) for c in calls for i in c)
    assert sorted(found) == list(range(1, 9))
    assert found[3]['img_name'] == 'F03.jpg'
    assert [(c.db_host, c.queries, c.closed) for c in opened] == [
        (labs.COMMONS_DB_HOST, 3, True)]


def test_get_files_info_by_ids_empty(monkeypatch):
    from montage import labs
    opened = _patch_replicas(monkeypatch, _fake_main_replica_by_id({}, []))
    assert labs.get_files_info_by_ids([]) == {}
    assert opened == []


@pytest.mark.xfail(
    os.environ.get('TOOLFORGE') != '1',
    reason='Requires live wikireplicas (Toolforge); set TOOLFORGE=1 to run',
)
def test_get_files_info_by_ids_live():
    """A file found by name is found again by its file_id, with the same
    details."""
    from montage.labs import get_files_info_by_names, get_files_info_by_ids
    name = 'Reynisfjara,_Suðurland,_Islandia,_2014-08-17,_DD_164.JPG'
    by_name = get_files_info_by_names([name])[name]
    by_id = get_files_info_by_ids([by_name['file_id']])
    assert by_id[by_name['file_id']] == by_name


def test_source_url_rewrites_only_gist_links():
    """#208: a plain CSV / text link got '/raw' appended and returned 404."""
    from montage.loaders import source_url
    assert source_url('https://gist.github.com/u/abc') == (
        'https://gist.githubusercontent.com/u/abc/raw', False)
    assert source_url('https://gist.githubusercontent.com/u/abc/raw/x.csv') == (
        'https://gist.githubusercontent.com/u/abc/raw/x.csv', False)
    assert source_url('https://wikimedia.be/public/wlh/list.txt') == (
        'https://wikimedia.be/public/wlh/list.txt', False)



# ---------------------------------------------------------------------------
# Review fixes (pr-check 2026-10-06): what the server fetches, and how much
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('url', [
    'http://example.org/list.csv',            # not https
    'https://127.0.0.1/list.csv',
    'https://169.254.169.254/latest/meta-data/',
    'https://[::1]/list.csv',
    'https://10.0.0.5/list.csv',
    'ftp://example.org/list.csv',
    'https:///nohost',
])
def test_fetch_refuses_non_public_or_non_https_links(url):
    with responses.RequestsMock() as rsps:  # nothing may be requested
        with raises(ImportSourceInvalid):
            fetch_source_text(url)
        assert len(rsps.calls) == 0


def test_fetch_follows_redirects_only_to_public_addresses(monkeypatch):
    from montage import loaders
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, 'https://example.org/a.csv', status=302,
                 headers={'Location': 'https://example.org/b.csv'})
        rsps.add(responses.GET, 'https://example.org/b.csv', body='A.jpg\n', status=200)
        assert fetch_source_text('https://example.org/a.csv') == 'A.jpg\n'
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, 'https://example.org/c.csv', status=302,
                 headers={'Location': 'https://169.254.169.254/secret'})
        with raises(ImportSourceInvalid):
            fetch_source_text('https://example.org/c.csv')
        assert len(rsps.calls) == 1
    with responses.RequestsMock() as rsps:
        for i in range(loaders.MAX_REDIRECTS + 1):
            rsps.add(responses.GET, 'https://example.org/r%d' % i, status=302,
                     headers={'Location': 'https://example.org/r%d' % (i + 1)})
        with raises(ImportSourceInvalid):
            fetch_source_text('https://example.org/r0')


def test_fetch_stops_at_the_size_cap(monkeypatch):
    from montage import loaders
    monkeypatch.setattr(loaders, 'MAX_SOURCE_BYTES', 1000)
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, 'https://example.org/big.csv', body='A.jpg\n' * 500, status=200)
        with raises(ImportSourceInvalid) as exc:
            fetch_source_text('https://example.org/big.csv')
    assert 'larger than' in exc.value.detail


def test_parse_stops_at_the_row_cap(monkeypatch):
    from montage import loaders
    monkeypatch.setattr(loaders, 'MAX_SOURCE_ROWS', 3)
    parse_source_rows('filename\nA.jpg\nB.jpg\nC.jpg\n')
    with raises(ImportSourceInvalid):
        parse_source_rows('filename\nA.jpg\nB.jpg\nC.jpg\nD.jpg\n')
    with raises(ImportSourceInvalid):
        parse_name_list(['A.jpg', 'B.jpg', 'C.jpg', 'D.jpg'])


def test_source_fields_must_be_text():
    from montage.loaders import category_records
    for bad in (['https://example.org/x.csv'], {'u': 1}, 5):
        with raises(ImportSourceInvalid):
            fetch_source_text(bad)
        with raises(ImportSourceInvalid):
            category_records(bad)
    with raises(ImportSourceInvalid):
        parse_name_list(5)


@pytest.mark.parametrize('written, canonical', [
    ('file:a b.jpg', 'A_b.jpg'),
    ('Image: Foo.jpg', 'Foo.jpg'),
    ('File:  two   spaces__and_.jpg', 'Two_spaces_and_.jpg'),
    ('_leading and trailing_ ', 'Leading_and_trailing'),
    (u'éclair.jpg', u'Éclair.jpg'),
    (b'Bytes.jpg', 'Bytes.jpg'),
])
def test_names_are_canonical_like_mediawiki(written, canonical):
    """MediaWiki file titles: File:/Image: prefix in any case, runs of
    spaces and underscores collapsed, no leading/trailing underscore,
    first letter upper case (Commons is first-letter case-sensitive)."""
    assert normalise_name(written) == canonical
    assert parse_name_list([written])[0]['name'] == canonical
