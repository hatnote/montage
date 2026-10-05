# -*- coding: utf-8 -*-
"""The import check (hatnote/montage#510): classification, the same-name
rule, check files. Commons lookups are stand-ins; all data is synthetic,
except the е/ё pair from #645 (public Commons file names and ids)."""
import csv
import io
import json
import os
import time
import datetime

import pytest
import responses as responses_lib

from montage import import_check
from montage.import_check import (run_check, counts, blocking_rows, importable,
                                  raise_if_blocked, import_warnings, summarize,
                                  upload_csv, save, load, same_name_keys)
from montage.loaders import parse_source_rows
from montage.utils import (ImportCheckBlocked, ImportCheckExpired,
                           ImportSourceInvalid)

CAMPAIGN = 7
VOLOCHEK = u'Церковь_Богоявления,_Вышний_Волочек.jpg'
VOLOCHYOK = u'Церковь_Богоявления,_Вышний_Волочёк.jpg'


def info(name, file_id, **kw):
    rec = {'img_name': name, 'img_width': 3000, 'img_height': 2000,
           'img_major_mime': 'image', 'img_minor_mime': 'jpeg',
           'img_user': 1, 'img_user_text': 'Uploader',
           'img_timestamp': '20260910120000',
           'rec_img_timestamp': '20260910120000', 'rec_img_user': 1,
           'rec_img_text': 'Uploader', 'oi_archive_name': None,
           'file_id': file_id}
    rec.update(kw)
    return rec


class FakeCommons(object):
    """Stands in for the wikireplica lookups (local mode)."""
    def __init__(self, files):
        self.by_name = {f['img_name']: f for f in files}
        self.by_id = {f['file_id']: f for f in files}
        self.calls = []

    def names(self, names, source='local'):
        self.calls.append(('names', sorted(set(names))))
        return {n: self.by_name[n] for n in names if n in self.by_name}

    def ids(self, ids):
        self.calls.append(('ids', sorted(set(ids))))
        return {i: self.by_id[i] for i in ids if i in self.by_id}

    def category(self, name, source='local'):
        self.calls.append(('category', name))
        return sorted(self.by_name.values(), key=lambda f: f['img_name'].encode('utf8'))


@pytest.fixture
def commons(monkeypatch):
    fake = FakeCommons([])

    def install(files):
        fake.__init__(files)
        return fake
    monkeypatch.setattr(import_check, 'lookup_by_names', fake.names)
    monkeypatch.setattr(import_check, 'lookup_by_ids', fake.ids)
    monkeypatch.setattr(import_check, 'category_records', fake.category)
    return install


def csv_check(monkeypatch, text, method='csv'):
    monkeypatch.setattr(import_check, 'fetch_source_text', lambda url: text)
    return run_check({'import_method': method, 'csv_url': 'https://example.org/x.csv'},
                     CAMPAIGN, source='local')


def statuses(result):
    return [(r['row'], r['status']) for r in result['rows']]


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def test_classify_every_status(monkeypatch, commons):
    commons([info('A.jpg', 1), info('B_new.jpg', 2), info('C.jpg', 3)])
    result = csv_check(monkeypatch, 'filename,file_id\n'
                       'A.jpg,1\n'          # 2 ok
                       'B old.jpg,2\n'      # 3 renamed
                       'C.jpg,\n'           # 4 ok by name
                       'Gone.jpg,\n'        # 5 unknown name
                       'X.jpg,99\n'         # 6 unknown file_id
                       'Y.jpg,1.2E+3\n'     # 7 malformed
                       'File:A.jpg,\n'      # 8 duplicate (same name)
                       ',3\n')              # 9 duplicate (id only)
    assert statuses(result) == [(2, 'ok'), (3, 'renamed'), (4, 'ok'),
                                (5, 'unknown_name'), (6, 'unknown_file_id'),
                                (7, 'malformed_file_id'), (8, 'duplicate'),
                                (9, 'duplicate')]
    renamed = result['rows'][1]
    assert renamed['commons_name'] == 'B_new.jpg' and renamed['file_id'] == 2
    assert u'B_old.jpg → B_new.jpg' in renamed['reason']
    assert result['rows'][7]['reason'] == 'the same file as row 4'
    assert [r['commons_name'] for r in importable(result)] == ['A.jpg', 'B_new.jpg', 'C.jpg']
    assert [r['row'] for r in blocking_rows(result)] == [6, 7]
    assert counts(result)['duplicate'] == 2


def test_old_name_and_its_file_id_are_one_file(monkeypatch, commons):
    commons([info('New.jpg', 5)])
    result = csv_check(monkeypatch, 'filename,file_id\nNew.jpg,\nOld.jpg,5\n')
    assert statuses(result) == [(2, 'ok'), (3, 'duplicate')]


def test_no_name_with_a_known_file_id_is_ok(monkeypatch, commons):
    commons([info('A.jpg', 1)])
    result = csv_check(monkeypatch, 'filename,file_id\n,1\n')
    assert statuses(result) == [(2, 'ok')]
    assert result['rows'][0]['reason'] == 'no name given; Commons name used'


def test_full_csv_metadata_is_ignored(monkeypatch, commons):
    """#509: Commons' metadata wins over the CSV's."""
    commons([info('A.jpg', 1, img_width=4000)])
    result = csv_check(monkeypatch, 'img_name,img_width,img_user_text\nA.jpg,1,Someone\n')
    assert importable(result)[0]['commons']['img_width'] == 4000
    assert result['columns']['ignored'] == ['img_width', 'img_user_text']


def test_blocking_per_method(monkeypatch, commons):
    commons([info('A.jpg', 1)])
    result = csv_check(monkeypatch, 'filename,file_id\nA.jpg,77\n')
    assert result['rows'][0]['status'] == 'unknown_file_id'
    with pytest.raises(ImportCheckBlocked) as exc:
        raise_if_blocked(result)
    assert exc.value.detail.startswith('1 rows block this import (1 unknown file id)')
    assert 'row 2: file_id 77 is not on Commons' in exc.value.detail


def test_unknown_names_do_not_block(monkeypatch, commons):
    commons([info('A.jpg', 1)])
    result = csv_check(monkeypatch, 'A.jpg\nGone.jpg\n')
    raise_if_blocked(result)
    warnings = import_warnings(result)
    assert list(warnings[0]) == ['import issues']
    assert 'Gone.jpg' in warnings[0]['import issues']


def test_blocked_detail_lists_ten_rows_count_first(monkeypatch, commons):
    commons([])
    result = csv_check(monkeypatch, 'filename,file_id\n' +
                       ''.join('F%d.jpg,%d\n' % (i, 500 + i) for i in range(30)))
    with pytest.raises(ImportCheckBlocked) as exc:
        raise_if_blocked(result)
    assert exc.value.detail.startswith('30 rows block this import')
    assert '... and 20 more' in exc.value.detail


def test_lookups_are_batched_not_per_row(monkeypatch, commons):
    fake = commons([info('A.jpg', 1), info('B.jpg', 2)])
    csv_check(monkeypatch, 'filename,file_id\nA.jpg,1\nB.jpg,\nC.jpg,\n')
    assert fake.calls == [('ids', [1]), ('names', ['B.jpg', 'C.jpg'])]


def test_file_list_rows_are_lines(commons):
    commons([info('A_b.jpg', 1)])
    result = run_check({'import_method': 'selected',
                        'file_names': ['File:A b.jpg', '', 'Gone.jpg']},
                       CAMPAIGN, source='local')
    assert statuses(result) == [(1, 'ok'), (3, 'unknown_name')]
    assert result['source'] == {'file_names': ['File:A b.jpg', 'Gone.jpg']}


def test_missing_source_is_import_source_invalid():
    for request in [{'import_method': 'selected'},
                    {'import_method': 'nonsense'},
                    {'import_method': 'csv'},
                    {'import_method': 'category', 'category': '  '}]:
        with pytest.raises(ImportSourceInvalid):
            run_check(request, CAMPAIGN, source='local')


# ---------------------------------------------------------------------------
# dev (remote): no lookup by file_id; compared by name
# ---------------------------------------------------------------------------

def test_remote_compares_file_ids_by_name(monkeypatch, commons):
    fake = commons([info('A.jpg', 1), info('B.jpg', 2)])
    monkeypatch.setattr(import_check, 'fetch_source_text',
                        lambda url: 'filename,file_id\nA.jpg,1\nB.jpg,3\n')
    result = run_check({'import_method': 'csv', 'csv_url': 'x'}, CAMPAIGN, source='remote')
    assert statuses(result) == [(2, 'ok'), (3, 'unknown_file_id')]
    assert result['rows'][1]['reason'].startswith('dev: compared by name only')
    assert [c[0] for c in fake.calls] == ['names']  # never by id


# ---------------------------------------------------------------------------
# The gist fix: a gist is looked up where the instance looks up (no POST to
# production's utils endpoint from beta/prod)
# ---------------------------------------------------------------------------

def test_gist_local_makes_no_remote_lookup(monkeypatch):
    from montage import labs
    monkeypatch.setattr(labs, 'get_files_info_by_names',
                        lambda names: {'A.jpg': info('A.jpg', 1)})
    monkeypatch.setattr('montage.loaders.get_files_info_by_names',
                        labs.get_files_info_by_names)
    with responses_lib.RequestsMock() as rsps:
        rsps.add(responses_lib.GET, 'https://gist.githubusercontent.com/u/abc/raw',
                 body='filename\nA.jpg\n', status=200)
        result = run_check({'import_method': 'gistcsv',
                            'gist_url': 'https://gist.github.com/u/abc'},
                           CAMPAIGN, source='local')
        assert len(rsps.calls) == 1  # the gist itself, no utils POST
    assert statuses(result) == [(2, 'ok')]


# ---------------------------------------------------------------------------
# Same name (#645): names the database treats as equal
# ---------------------------------------------------------------------------

def test_same_name_pair_blocks_a_list_import(monkeypatch, commons):
    commons([info(VOLOCHEK, 149673020), info(VOLOCHYOK, 149673022),
             info('Other.jpg', 3)])
    result = csv_check(monkeypatch, u'filename,file_id\n"%s",149673020\n"%s",\nOther.jpg,\n'
                       % (VOLOCHEK, VOLOCHYOK))
    assert statuses(result) == [(2, 'same_name'), (3, 'same_name'), (4, 'ok')]
    assert result['rows'][0]['group'] == result['rows'][1]['group'] == 1
    assert VOLOCHYOK in result['rows'][0]['reason']
    assert [r['row'] for r in blocking_rows(result)] == [2, 3]
    groups = summarize(result, 'x' * 32)['same_name_groups']
    assert [[m['commons_name'] for m in g] for g in groups] == [[VOLOCHEK, VOLOCHYOK]]


@pytest.mark.parametrize('pair', [('Photo.jpg', 'Photo.JPG'),
                                  (u'Église.jpg', u'Eglise.jpg'),
                                  (u'Йошкар.jpg', u'Иошкар.jpg')])
def test_same_name_case_and_accents(monkeypatch, commons, pair):
    commons([info(pair[0], 1), info(pair[1], 2)])
    result = csv_check(monkeypatch, 'filename\n%s\n%s\n' % pair)
    assert [s for _, s in statuses(result)] == ['same_name', 'same_name']


def test_same_name_in_a_category_keeps_the_first(commons):
    commons([info(VOLOCHYOK, 149673022), info(VOLOCHEK, 149673020), info('A.jpg', 1)])
    result = run_check({'import_method': 'category', 'category': 'Cat'},
                       CAMPAIGN, source='local')
    by_name = {r['commons_name']: r['status'] for r in result['rows']}
    # binary order: е (U+0435) sorts before ё (U+0451)
    assert by_name == {VOLOCHEK: 'ok', VOLOCHYOK: 'same_name', 'A.jpg': 'ok'}
    assert blocking_rows(result) == []
    warning = import_warnings(result)[-1]['same name']
    assert VOLOCHEK in warning and VOLOCHYOK in warning


def test_same_name_switch_off(monkeypatch, commons):
    monkeypatch.setattr(import_check, 'SAME_NAME_CHECK', False)
    commons([info(VOLOCHEK, 1), info(VOLOCHYOK, 2)])
    result = csv_check(monkeypatch, u'filename\n"%s"\n"%s"\n' % (VOLOCHEK, VOLOCHYOK))
    assert [s for _, s in statuses(result)] == ['ok', 'ok']


def test_test_only_key_does_not_cover_expansions():
    """Documented gap of the SQLite stand-in (MariaDB's own keys are used
    in production): ß/ss are not grouped."""
    keys = same_name_keys([u'Straße.jpg', u'Strasse.jpg'])
    assert keys[u'Straße.jpg'] != keys[u'Strasse.jpg']


def test_same_name_keys_ask_mariadb(monkeypatch):
    """On MariaDB the keys come from WEIGHT_STRING, batched, no table."""
    sent = []

    class Result(object):
        def __init__(self, n):
            self.n = n

        def fetchone(self):
            return [b'k' for _ in range(self.n)]

    class Session(object):
        def get_bind(self):
            class Bind(object):
                class dialect(object):
                    name = 'mysql'
            return Bind()

        def execute(self, statement, params):
            sent.append((str(statement), params))
            return Result(len(params))

    monkeypatch.setattr(import_check, 'SAME_NAME_CHUNK_SIZE', 2)
    keys = same_name_keys(['c.jpg', 'a.jpg', 'b.jpg'], Session())
    assert set(keys) == {'a.jpg', 'b.jpg', 'c.jpg'}
    assert [len(p) for _, p in sent] == [2, 1]
    sql = sent[0][0]
    assert sql.startswith('SELECT WEIGHT_STRING(CONVERT(:n0 USING utf8mb4)'
                          ' COLLATE utf8mb4_unicode_ci) AS w0')
    assert 'FROM' not in sql


# ---------------------------------------------------------------------------
# Summary and download
# ---------------------------------------------------------------------------

def test_summary_caps_issues(monkeypatch, commons):
    monkeypatch.setattr(import_check, 'ISSUES_SHOWN', 3)
    commons([])
    result = csv_check(monkeypatch, ''.join('G%d.jpg\n' % i for i in range(5)))
    summary = summarize(result, 't' * 32)
    assert len(summary['issues']) == 3 and summary['issues_total'] == 5
    assert summary['issues_truncated'] and not summary['blocking']
    assert summary['importable_count'] == 0 and summary['total_rows'] == 5
    assert 'commons' not in summary['issues'][0]
    assert summary['expires_at'] > summary['checked_at']


def test_download_is_an_upload_file_that_passes_unchanged(monkeypatch, commons):
    commons([info('A.jpg', 1), info('New.jpg', 2), info('=SUM(A1).jpg', 3)])
    first = csv_check(monkeypatch, 'img_name,file_id,img_width\n'
                      'A.jpg,1,5\nOld.jpg,2,5\nA.jpg,,5\nGone.jpg,,5\n=SUM(A1).jpg,,5\n')
    data = upload_csv(first).decode('utf8')
    assert list(csv.reader(io.StringIO(data))) == [
        ['filename', 'file_id'], ['A.jpg', '1'], ['New.jpg', '2'], ["'=SUM(A1).jpg", '3']]
    second = csv_check(monkeypatch, data)
    assert [s for _, s in statuses(second)] == ['ok', 'ok', 'ok']
    assert upload_csv(second) == upload_csv(first)


# ---------------------------------------------------------------------------
# Check files
# ---------------------------------------------------------------------------

@pytest.fixture
def config(tmpdir):
    return {'import_check_path': str(tmpdir.join('checks'))}


def _result(campaign_id=CAMPAIGN, method='csv', checked_at=None):
    now = checked_at or datetime.datetime.now(datetime.timezone.utc)
    return {'format': 1, 'checked_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'campaign_id': campaign_id, 'import_method': method,
            'source': {'csv_url': 'x'}, 'lookup': 'local',
            'columns': {}, 'rows': []}


def test_save_and_load(config):
    token = save(_result(), config)
    assert len(token) == 32
    folder = config['import_check_path']
    assert os.stat(folder).st_mode & 0o777 == 0o700
    path = os.path.join(folder, token + '.json')
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert os.listdir(folder) == [token + '.json']  # no temp file left
    assert load(token, config, CAMPAIGN, 'gistcsv')['campaign_id'] == CAMPAIGN


def test_load_refuses_bad_tokens(config):
    token = save(_result(), config)
    old = save(_result(checked_at=datetime.datetime.now(datetime.timezone.utc)
                       - datetime.timedelta(days=8)), config)
    for bad, args in [('../x', (CAMPAIGN,)),
                      ('../' + token[3:], (CAMPAIGN,)),
                      ('A' * 32, (CAMPAIGN,)),
                      (None, (CAMPAIGN,)),
                      (old, (CAMPAIGN,)),
                      (token, (CAMPAIGN + 1,)),
                      (token, (CAMPAIGN, 'category'))]:
        with pytest.raises(ImportCheckExpired):
            load(bad, config, *args)


def test_save_cleans_up_old_files(config, tmpdir):
    keep = save(_result(), config)
    stale = save(_result(), config)
    folder = config['import_check_path']
    week_ago = time.time() - 8 * 24 * 3600
    os.utime(os.path.join(folder, stale + '.json'), (week_ago, week_ago))
    other = os.path.join(folder, 'notes.txt')
    open(other, 'w').close()
    os.utime(other, (week_ago, week_ago))
    newest = save(_result(), config)
    assert sorted(os.listdir(folder)) == sorted([keep + '.json', newest + '.json', 'notes.txt'])


def test_check_file_has_no_montage_user(monkeypatch, commons, config):
    commons([info('A.jpg', 1, img_user_text='CommonsUploader')])
    token = save(csv_check(monkeypatch, 'A.jpg\n'), config)
    with open(os.path.join(config['import_check_path'], token + '.json')) as f:
        raw = f.read()
    stored = json.loads(raw)
    assert set(stored) == {'format', 'checked_at', 'campaign_id', 'import_method',
                           'source', 'lookup', 'columns', 'rows'}
    assert 'CommonsUploader' in raw  # Commons data is kept (approved)
    assert 'Yarl' not in raw and 'Slaporte' not in raw


def test_check_dir_required_on_deployed_instances(monkeypatch):
    monkeypatch.delenv('MONTAGE_IMPORT_CHECK_PATH', raising=False)
    for env in ('beta', 'prod', 'devlabs'):
        assert 'MONTAGE_IMPORT_CHECK_PATH' in import_check.check_dir_problem({}, env)
        assert import_check.check_dir_problem({'import_check_path': '/x'}, env) is None
    assert import_check.check_dir_problem({}, 'dev') is None
    monkeypatch.setenv('MONTAGE_IMPORT_CHECK_PATH', '/y')
    assert import_check.check_dir_problem({}, 'prod') is None


def test_header_less_list_with_comma_names(monkeypatch, commons):
    """A gist that lists the #645 pair one per line, unquoted: the commas
    stay in the names and the pair is found."""
    commons([info(VOLOCHEK, 149673020), info(VOLOCHYOK, 149673022)])
    result = csv_check(monkeypatch, u'%s\n%s\n' % (VOLOCHEK.replace('_', ' '), VOLOCHYOK))
    assert [(r['row'], r['commons_name'], r['status']) for r in result['rows']] == [
        (1, VOLOCHEK, 'same_name'), (2, VOLOCHYOK, 'same_name')]


# ---------------------------------------------------------------------------
# Endpoints: check, download, import by token
# ---------------------------------------------------------------------------

from montage.tests.test_web_basic import montage_app, api_client  # noqa: E402,F401
from montage.tests.test_import_entries import (  # noqa: E402,F401
    COORD, coord_client, new_round, db_query, entry_ids, round_rows)


def _campaign_of(client, round_id):
    return client.fetch('coordinator: get round', '/admin/round/%s' % round_id,
                        as_user=COORD)['data']['campaign']['id']


@pytest.fixture
def local_commons(monkeypatch, commons):
    """Endpoint tests run as 'dev'; look Commons up 'locally' (stand-in)
    so lookups by file_id happen, as on Toolforge."""
    monkeypatch.setattr(import_check, 'lookup_source', lambda: 'local')
    return commons


def _source(monkeypatch, text):
    monkeypatch.setattr(import_check, 'fetch_source_text', lambda url: text)


def _check(client, campaign_id, error_code=None, **request):
    request.setdefault('import_method', 'csv')
    request.setdefault('csv_url', 'https://example.org/list.csv')
    kw = {'error_code': error_code} if error_code else {}
    return client.fetch('coordinator: check import source',
                        '/admin/campaign/%s/import/check' % campaign_id,
                        request, as_user=COORD, **kw)


def _import(client, round_id, token, method='csv', error_code=None):
    data = {'import_method': method}
    if token:
        data['check_token'] = token
    kw = {'error_code': error_code} if error_code else {}
    return client.fetch('coordinator: import', '/admin/round/%s/import' % round_id,
                        data, as_user=COORD, **kw)


def _body(resp):
    return resp.get_data(as_text=True)


def test_check_endpoint_writes_no_rows(montage_app, coord_client, local_commons,
                                       monkeypatch):
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'filename,File ID\nA.jpg,x\nGone.jpg,\n')
    round_id = new_round(coord_client, 'chk')
    data = _check(coord_client, _campaign_of(coord_client, round_id))['data']
    assert len(data['token']) == 32
    assert data['counts']['ok'] == 1 and data['counts']['unknown_name'] == 1
    assert data['columns']['ignored'] == ['File ID']
    assert not data['blocking'] and data['importable_count'] == 1
    assert [i['row'] for i in data['issues']] == [3]
    assert db_query(montage_app, 'SELECT id FROM entries') == []
    assert db_query(montage_app, 'SELECT id FROM round_sources') == []


def test_check_and_download_need_a_coordinator(montage_app, coord_client,
                                               local_commons, monkeypatch):
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'A.jpg\n')
    round_id = new_round(coord_client, 'perm')
    campaign_id = _campaign_of(coord_client, round_id)
    token = _check(coord_client, campaign_id)['data']['token']
    coord_client.fetch('maintainer: add organizer', '/admin/add_organizer',
                       {'username': 'Outsider'})
    coord_client.fetch('outsider: check', '/admin/campaign/%s/import/check' % campaign_id,
                       {'import_method': 'csv', 'csv_url': 'x'}, as_user='Outsider',
                       error_code=403)
    coord_client.fetch('outsider: download',
                       '/admin/campaign/%s/import/check/%s/download' % (campaign_id, token),
                       as_user='Outsider', error_code=403)


def test_download(montage_app, coord_client, local_commons, monkeypatch):
    local_commons([info('A.jpg', 1), info('B_new.jpg', 2)])
    _source(monkeypatch, 'filename,file_id\nA.jpg,1\nB old.jpg,2\nGone.jpg,\n')
    round_id = new_round(coord_client, 'dl')
    campaign_id = _campaign_of(coord_client, round_id)
    token = _check(coord_client, campaign_id)['data']['token']
    resp = coord_client.fetch('coordinator: download check',
                              '/admin/campaign/%s/import/check/%s/download'
                              % (campaign_id, token), as_user=COORD)
    assert resp.headers['Content-Disposition'].startswith(
        'attachment; filename=montage_import-%s-' % campaign_id)
    assert _body(resp) == 'filename,file_id\nA.jpg,1\nB_new.jpg,2\n'


def test_import_without_a_token_is_refused(montage_app, coord_client):
    round_id = new_round(coord_client, 'notoken')
    for method in ('csv', 'gistcsv', 'category', 'selected'):
        resp = _import(coord_client, round_id, None, method, error_code=400)
        assert 'import_check_required' in _body(resp)
    assert db_query(montage_app, 'SELECT id FROM round_sources') == []


def test_import_takes_the_checked_list_without_lookups(montage_app, coord_client,
                                                      local_commons, monkeypatch):
    """#509 + #510: a full CSV with stale metadata imports Commons' data and
    file_ids; the import fetches nothing and asks Commons nothing."""
    local_commons([info('A.jpg', 1, img_width=4000), info('B_new.jpg', 2)])
    _source(monkeypatch, 'img_name,file_id,img_width,img_user_text\n'
                         'A.jpg,,10,Stale\nB old.jpg,2,10,Stale\n')
    round_id = new_round(coord_client, 'bytoken')
    token = _check(coord_client, _campaign_of(coord_client, round_id))['data']['token']

    def boom(*a, **kw):
        raise AssertionError('looked something up during the import')
    for name in ('fetch_source_text', 'lookup_by_names', 'lookup_by_ids',
                 'category_records'):
        monkeypatch.setattr(import_check, name, boom)
    from montage import labs
    monkeypatch.setattr(labs, '_connect', boom)
    with responses_lib.RequestsMock():  # any HTTP request fails
        data = _import(coord_client, round_id, token)['data']

    assert data['new_round_entry_count'] == 2
    assert ['renamed'] in [list(w) for w in data['warnings']]
    assert all(len(w) == 1 for w in data['warnings'])  # one-key dicts
    rows = round_rows(montage_app, round_id)
    assert [(r['name'], r['file_id'], r['width'], r['upload_user_text'])
            for r in rows] == [('A.jpg', 1, 4000, 'Uploader'),
                               ('B_new.jpg', 2, 3000, 'Uploader')]
    assert rows[0]['source_params']['csv_url'] == 'https://example.org/list.csv'


def test_check_token_is_stored_in_the_round_source(montage_app, coord_client,
                                                   local_commons, monkeypatch):
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'A.jpg\n')
    round_id = new_round(coord_client, 'param')
    token = _check(coord_client, _campaign_of(coord_client, round_id))['data']['token']
    _import(coord_client, round_id, token)
    params = db_query(montage_app, 'SELECT params FROM round_sources WHERE round_id = :r',
                      r=round_id)
    assert json.loads(params[0]['params']) == {
        'csv_url': 'https://example.org/list.csv', 'check_token': token}


def test_blocked_check_writes_nothing_and_retry_uses_the_same_round(
        montage_app, coord_client, local_commons, monkeypatch):
    files = [info('F%03d.jpg' % i, 1000 + i) for i in range(100)]
    local_commons(files)
    rows = ''.join('F%03d.jpg,%d\n' % (i, 1000 + i) for i in range(100))
    _source(monkeypatch, 'filename,file_id\n' + rows.replace(',1050\n', ',9999\n'))
    round_id = new_round(coord_client, 'blocked')
    campaign_id = _campaign_of(coord_client, round_id)
    check = _check(coord_client, campaign_id)['data']
    assert check['blocking'] and check['counts']['unknown_file_id'] == 1

    resp = _import(coord_client, round_id, check['token'], error_code=400)
    assert 'import_check_blocked' in _body(resp)
    assert 'row 52: file_id 9999 is not on Commons' in _body(resp)
    assert db_query(montage_app, 'SELECT id FROM entries') == []
    assert round_rows(montage_app, round_id) == []

    # the coordinator fixes the source, checks again, imports into the
    # round that already exists (the form does not create a second one)
    _source(monkeypatch, 'filename,file_id\n' + rows)
    check = _check(coord_client, campaign_id)['data']
    data = _import(coord_client, round_id, check['token'])['data']
    assert data['new_round_entry_count'] == 100
    rounds = coord_client.fetch('coordinator: campaign', '/admin/campaign/%s' % campaign_id,
                                as_user=COORD)['data']['rounds']
    assert len(rounds) == 1


def test_bad_tokens_via_the_endpoint(montage_app, coord_client, local_commons,
                                     monkeypatch):
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'A.jpg\n')
    round_a = new_round(coord_client, 'tok a')
    round_b = new_round(coord_client, 'tok b')
    token_b = _check(coord_client, _campaign_of(coord_client, round_b))['data']['token']
    for token, method in [('../../etc/passwd', 'csv'), ('x' * 32, 'csv'),
                          (token_b, 'csv'),  # another campaign
                          ]:
        resp = _import(coord_client, round_a, token, method, error_code=400)
        assert 'import_check_expired' in _body(resp)
    resp = _import(coord_client, round_b, token_b, 'category', error_code=400)
    assert 'import_check_expired' in _body(resp)
    assert db_query(montage_app, 'SELECT id FROM round_sources') == []


def test_import_after_seven_days_is_refused(montage_app, coord_client,
                                            local_commons, monkeypatch, tmpdir):
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'A.jpg\n')
    round_id = new_round(coord_client, 'old check')
    token = _check(coord_client, _campaign_of(coord_client, round_id))['data']['token']
    later = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=8)
    monkeypatch.setattr(import_check, '_utcnow', lambda: later)
    resp = _import(coord_client, round_id, token, error_code=400)
    assert 'import_check_expired' in _body(resp) and '7 days' in _body(resp)


def test_renamed_file_already_in_montage_keeps_its_row(montage_app, coord_client,
                                                       local_commons, monkeypatch):
    """Review fix 1: a file Montage already has (found by file_id) keeps its
    row and stored name; only a file new to Montage gets Commons' name."""
    local_commons([info('Old_name.jpg', 5)])
    _source(monkeypatch, 'Old_name.jpg\n')
    round_a = new_round(coord_client, 'ren a')
    _import(coord_client, round_a, _check(coord_client, _campaign_of(coord_client, round_a))['data']['token'])
    ids = entry_ids(montage_app, 'Old_name')

    local_commons([info('New_name.jpg', 5)])
    _source(monkeypatch, 'filename,file_id\nOld name.jpg,5\n')
    round_b = new_round(coord_client, 'ren b')
    check = _check(coord_client, _campaign_of(coord_client, round_b))['data']
    assert check['counts']['renamed'] == 1
    data = _import(coord_client, round_b, check['token'])['data']
    assert data['new_round_entry_count'] == 1
    assert entry_ids(montage_app, 'Old_name') == ids
    assert entry_ids(montage_app, 'New_name') == {}


def test_category_same_name_pair_keeps_the_first(montage_app, coord_client,
                                                 local_commons):
    local_commons([info(VOLOCHEK, 149673020), info(VOLOCHYOK, 149673022)])
    round_id = new_round(coord_client, 'cat pair')
    check = _check(coord_client, _campaign_of(coord_client, round_id),
                   import_method='category', category='Cat')['data']
    assert not check['blocking'] and check['importable_count'] == 1
    data = _import(coord_client, round_id, check['token'], 'category')['data']
    assert data['new_round_entry_count'] == 1
    same = [w['same name'] for w in data['warnings'] if 'same name' in w]
    assert len(same) == 1 and VOLOCHEK in same[0] and VOLOCHYOK in same[0]


def test_app_refuses_to_start_without_a_check_folder(monkeypatch):
    from montage.app import create_app
    monkeypatch.delenv('MONTAGE_IMPORT_CHECK_PATH', raising=False)
    with pytest.raises(ValueError) as exc:
        create_app('prod', config={'__file__': 'test', '__env__': 'prod',
                                   'db_url': 'sqlite://'})
    assert 'MONTAGE_IMPORT_CHECK_PATH' in str(exc.value)
