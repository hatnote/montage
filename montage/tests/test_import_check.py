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
    def __init__(self, files, other_ids=None):
        self.by_name = {f['img_name']: f for f in files}
        self.by_id = {f['file_id']: f for f in files}
        self.other_ids = other_ids or {}
        self.calls = []

    def names(self, names, source='local'):
        self.calls.append(('names', sorted(set(names))))
        return {n: self.by_name[n] for n in names if n in self.by_name}

    def ids(self, ids):
        self.calls.append(('ids', sorted(set(ids))))
        return {i: self.by_id[i] for i in ids if i in self.by_id}

    def others(self, numbers):
        self.calls.append(('other_ids', sorted(set(numbers))))
        return {n: self.other_ids[n] for n in numbers if n in self.other_ids}

    def category(self, name, source='local'):
        self.calls.append(('category', name))
        return sorted(self.by_name.values(), key=lambda f: f['img_name'].encode('utf8'))


@pytest.fixture
def commons(monkeypatch):
    fake = FakeCommons([])

    def install(files, other_ids=None):
        fake.__init__(files, other_ids)
        return fake
    monkeypatch.setattr(import_check, 'lookup_by_names', fake.names)
    monkeypatch.setattr(import_check, 'lookup_by_ids', fake.ids)
    monkeypatch.setattr(import_check, 'category_records', fake.category)
    monkeypatch.setattr(import_check, 'lookup_other_ids', fake.others)
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
    assert result['rows'][7]['reason'] == 'the same file as row 4; imported once'
    assert (result['rows'][7]['reason_code'], result['rows'][7]['reason_params']) == ('duplicate', ['4'])
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
    assert exc.value.detail.startswith('1 row blocks the import.')
    assert 'row 2: no file on Commons has file ID 77' in exc.value.detail


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
    assert exc.value.detail.startswith('30 rows block the import.')
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
            return self.row

    class Session(object):
        def get_bind(self):
            class Bind(object):
                class dialect(object):
                    name = 'mysql'
            return Bind()

        def execute(self, statement, params):
            sent.append((str(statement), params))
            result = Result(len(params))
            # a key per bound name, in column order (case-insensitive)
            result.row = [params['n%d' % j].lower().encode('utf8')
                          for j in range(len(params))]
            return result

    monkeypatch.setattr(import_check, 'SAME_NAME_CHUNK_SIZE', 2)
    keys = same_name_keys(['c.jpg', 'X.jpg', 'a.jpg', 'x.jpg'], Session())
    assert keys == {'X.jpg': b'x.jpg', 'a.jpg': b'a.jpg', 'c.jpg': b'c.jpg', 'x.jpg': b'x.jpg'}
    assert [len(p) for _, p in sent] == [2, 2]  # X.jpg and x.jpg in different chunks
    sql = sent[0][0]
    assert sql.startswith('SELECT WEIGHT_STRING(CONVERT(:n0 USING utf8mb4)'
                          ' COLLATE utf8mb4_unicode_ci) AS w0')
    assert 'FROM' not in sql


def _session(dialect):
    class Session(object):
        def get_bind(self):
            class Bind(object):
                pass
            Bind.dialect = type('Dialect', (), {'name': dialect})
            return Bind()

        def execute(self, statement, params):
            class Result(object):
                def fetchone(self):
                    return [None] * len(params)
            return Result()
    return Session()


def test_same_name_keys_never_approximate_silently(monkeypatch):
    """B4: the Python stand-in only for SQLite / no session in dev and
    tests; another dialect, or any deployed instance, fails loudly."""
    with pytest.raises(RuntimeError):
        same_name_keys(['a.jpg'], _session('postgresql'))
    with pytest.raises(RuntimeError):  # a NULL key from the database
        same_name_keys(['a.jpg'], _session('mariadb'))
    assert same_name_keys(['a.jpg'], _session('sqlite'))
    monkeypatch.setattr(import_check, 'ENV_NAME', 'prod')
    with pytest.raises(RuntimeError):
        same_name_keys(['a.jpg'], _session('sqlite'))
    with pytest.raises(RuntimeError):
        same_name_keys(['a.jpg'])


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



def test_download_pasted_into_the_file_list_passes_unchanged(monkeypatch, commons):
    """The download can be pasted into the file list box as the next
    source (the form sends the box's lines as file_names)."""
    commons([info('A.jpg', 1), info('New.jpg', 2), info(VOLOCHEK, 3)])
    first = csv_check(monkeypatch, 'filename,file_id\nA.jpg,1\nOld.jpg,2\n"%s",\nGone.jpg,\n' % VOLOCHEK)
    data = upload_csv(first).decode('utf8')
    second = run_check({'import_method': 'selected', 'file_names': data.split('\n')},
                       CAMPAIGN, source='local')
    assert [s for _, s in statuses(second)] == ['ok', 'ok', 'ok']
    assert second['columns']['file_id'] == 'file_id'
    assert upload_csv(second) == upload_csv(first)


def test_pasted_csv_by_file_id_only_finds_same_name_pairs(commons):
    """A list of file_ids alone (header file_id) is looked up by id; two
    files whose names the database treats as equal block it."""
    commons([info(VOLOCHEK, 149673020), info(VOLOCHYOK, 149673022)])
    result = run_check({'import_method': 'selected',
                        'file_names': ['file_id', '149673020', '149673022']},
                       CAMPAIGN, source='local')
    assert statuses(result) == [(2, 'same_name'), (3, 'same_name')]
    assert [r['commons_name'] for r in result['rows']] == [VOLOCHEK, VOLOCHYOK]


def test_file_list_of_bare_file_ids(commons):
    """Lines of digits only are file_ids (no header needed); they mix with
    names. Two ids whose Commons names the database treats as equal block."""
    commons([info(VOLOCHEK, 149673020), info(VOLOCHYOK, 149673022), info('A.jpg', 1)])
    result = run_check({'import_method': 'selected',
                        'file_names': [' 149673020 ', 'A.jpg', '149673022', '999']},
                       CAMPAIGN, source='local')
    assert statuses(result) == [(1, 'same_name'), (2, 'ok'), (3, 'same_name'),
                                (4, 'unknown_file_id')]
    assert result['rows'][0]['commons_name'] == VOLOCHEK


def test_bare_page_and_revision_ids_are_refused_with_a_reason(commons):
    """People find page IDs and revision IDs on Commons, not file_ids. A
    bare number that is one of those blocks, saying what it is and which
    file it points to, instead of 'not on Commons' or, worse, importing
    another file whose file_id happens to be that number."""
    commons([info('A.jpg', 1), info('B.jpg', 2)],
            other_ids={1: {'kind': 'page_id', 'name': 'A.jpg'},           # same file: fine
                       2: {'kind': 'page_id', 'name': 'Other.jpg'},       # ambiguous
                       1100000000: {'kind': 'revision_id', 'name': 'C.jpg'},
                       170000000: {'kind': 'page_id', 'name': 'D.jpg'}})
    result = run_check({'import_method': 'selected',
                        'file_names': ['1', '2', '1100000000', '170000000', '5', 'B.jpg']},
                       CAMPAIGN, source='local')
    assert statuses(result) == [(1, 'ok'), (2, 'ambiguous_id'), (3, 'revision_id'),
                                (4, 'page_id'), (5, 'unknown_file_id'), (6, 'ok')]
    reasons = {r['row']: r['reason'] for r in result['rows']}
    assert 'revision ID' in reasons[3] and 'C.jpg' in reasons[3]
    assert 'page ID' in reasons[4] and 'D.jpg' in reasons[4]
    assert 'B.jpg' in reasons[2] and 'Other.jpg' in reasons[2]
    assert [r['row'] for r in blocking_rows(result)] == [2, 3, 4, 5]


def test_named_rows_are_not_looked_up_as_page_ids(commons):
    """A row with a name confirms its file_id; only bare numbers are
    checked against page and revision IDs."""
    fake = commons([info('A.jpg', 1)], other_ids={1: {'kind': 'page_id', 'name': 'X.jpg'}})
    result = run_check({'import_method': 'selected', 'file_names': ['A.jpg']},
                       CAMPAIGN, source='local')
    assert statuses(result) == [(1, 'ok')]
    assert not any(c[0] == 'other_ids' for c in fake.calls)


def test_rows_carry_a_reason_code_and_params_for_translation(commons):
    """The frontend shows montage-round-check-reason-<code> with the params;
    the English reason stays for API users."""
    commons([info('A.jpg', 1), info('New.jpg', 2), info(VOLOCHEK, 3), info(VOLOCHYOK, 4)],
            other_ids={1100000000: {'kind': 'revision_id', 'name': 'C.jpg'}})
    result = run_check({'import_method': 'selected', 'file_names': [
        'A.jpg', 'A.jpg', 'Gone.jpg', '99', '1100000000', VOLOCHEK, VOLOCHYOK]},
        CAMPAIGN, source='local')
    codes = [(r['row'], r['reason_code'], r['reason_params']) for r in result['rows']]
    assert codes == [
        (1, None, []),
        (2, 'duplicate', ['1']),
        (3, 'unknown-name', ['Gone.jpg']),
        (4, 'unknown-file-id', ['99']),
        (5, 'revision-id', ['1100000000', 'C.jpg']),
        (6, 'same-name', [VOLOCHYOK, '7']),
        (7, 'same-name', [VOLOCHEK, '6'])]
    issue = summarize(result, 't' * 32)['issues'][0]
    assert issue['reason_code'] == 'duplicate' and issue['reason_params'] == ['1']


def test_source_errors_carry_a_reason_code():
    """Source errors reach the client with reason_code / reason_params."""
    from montage.utils import ImportSourceInvalid
    err = ImportSourceInvalid('x', reason_code='https-only', reason_params=['http://a'])
    assert err.to_dict()['reason_code'] == 'https-only'
    assert err.to_dict()['reason_params'] == ['http://a']
    assert err.to_dict()['error_type'] == 'import_source_invalid'

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


def test_save_cleans_up_only_old_check_files(config, tmpdir):
    keep = save(_result(), config)
    stale = save(_result(), config)
    folder = config['import_check_path']
    week_ago = time.time() - 8 * 24 * 3600
    for name in (stale + '.json', 'notes.txt', 'export.json', '.tmp-x1.json'):
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            open(path, 'w').close()
        os.utime(path, (week_ago, week_ago))
    newest = save(_result(), config)
    assert sorted(os.listdir(folder)) == sorted(
        [keep + '.json', newest + '.json', 'notes.txt', 'export.json'])


def test_save_does_not_change_an_existing_folder(tmpdir):
    folder = tmpdir.mkdir('shared')
    os.chmod(str(folder), 0o755)
    save(_result(), {'import_check_path': str(folder)})
    assert os.stat(str(folder)).st_mode & 0o777 == 0o755


def test_save_keeps_at_most_max_check_files(config, monkeypatch):
    monkeypatch.setattr(import_check, 'MAX_CHECK_FILES', 3)
    tokens = []
    for i in range(5):
        tokens.append(save(_result(), config))
        path = os.path.join(config['import_check_path'], tokens[-1] + '.json')
        recent = time.time() - 3600 + i  # within 7 days, oldest first
        os.utime(path, (recent, recent))
    left = sorted(os.listdir(config['import_check_path']))
    assert left == sorted(t + '.json' for t in tokens[-3:])


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


def test_check_dir_required_outside_dev(monkeypatch, tmpdir):
    monkeypatch.delenv('MONTAGE_IMPORT_CHECK_PATH', raising=False)
    good = str(tmpdir.mkdir('checks'))
    for env in ('beta', 'prod', 'devlabs', 'staging'):
        assert 'MONTAGE_IMPORT_CHECK_PATH' in import_check.check_dir_problem({}, env)
        assert import_check.check_dir_problem({'import_check_path': good}, env) is None
    for env in ('dev', 'devtest'):
        assert import_check.check_dir_problem({}, env) is None
    monkeypatch.setenv('MONTAGE_IMPORT_CHECK_PATH', good)
    assert import_check.check_dir_problem({}, 'prod') is None


def test_check_dir_must_be_a_folder_of_its_own(tmpdir):
    """B1: a typo such as the tool's home must not start the app (its
    cleanup would delete files there)."""
    home = tmpdir.mkdir('home')
    home.join('replica.my.cnf').write('x')
    for path, why in [('relative/checks', 'absolute'),
                      (str(home), 'other files'),
                      (str(tmpdir.join('missing', 'deeper')), 'does not exist')]:
        problem = import_check.check_dir_problem({'import_check_path': path}, 'prod')
        assert problem and why in problem, (path, problem)
    # a folder that does not exist yet, in an existing parent, is fine
    assert import_check.check_dir_problem(
        {'import_check_path': str(home.join('import_checks'))}, 'prod') is None


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


def test_round_source_records_a_check_fingerprint_not_the_token(
        montage_app, coord_client, local_commons, monkeypatch):
    """B10: round_sources.params is shown on the public /entry page, so the
    token itself is not stored; a second check of the same source reuses
    the round source."""
    import hashlib
    local_commons([info('A.jpg', 1), info('B.jpg', 2)])
    _source(monkeypatch, 'A.jpg\n')
    round_id = new_round(coord_client, 'param')
    campaign_id = _campaign_of(coord_client, round_id)
    token = _check(coord_client, campaign_id)['data']['token']
    _import(coord_client, round_id, token)
    _source(monkeypatch, 'A.jpg\nB.jpg\n')
    _import(coord_client, round_id, _check(coord_client, campaign_id)['data']['token'])
    params = db_query(montage_app, 'SELECT params FROM round_sources WHERE round_id = :r',
                      r=round_id)
    assert len(params) == 1
    assert json.loads(params[0]['params']) == {
        'csv_url': 'https://example.org/list.csv',
        'check_id': hashlib.sha256(token.encode('ascii')).hexdigest()[:12]}
    page = coord_client.fetch('public: entry', '/entry/A.jpg')
    assert token not in json.dumps(page)


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
    assert 'row 52: no file on Commons has file ID 9999' in _body(resp)
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


def _after(monkeypatch, **delta):
    later = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(**delta)
    monkeypatch.setattr(import_check, '_utcnow', lambda: later)


def test_a_check_is_valid_for_one_hour(montage_app, coord_client, local_commons,
                                       monkeypatch, tmpdir):
    """Files are renamed and deleted on Commons all the time: a check is
    used within the hour or done again."""
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'A.jpg\n')
    round_id = new_round(coord_client, 'old check')
    data = _check(coord_client, _campaign_of(coord_client, round_id))['data']
    assert (import_check._parse_iso(data['expires_at'])
            - import_check._parse_iso(data['checked_at'])) == datetime.timedelta(hours=1)
    _after(monkeypatch, minutes=61)
    resp = _import(coord_client, round_id, data['token'], error_code=400)
    assert 'import_check_expired' in _body(resp) and '1 hour' in _body(resp)
    _after(monkeypatch, minutes=59)
    assert _import(coord_client, round_id, data['token'])['data']['new_round_entry_count'] == 1


def test_downloads_work_until_the_file_is_deleted(montage_app, coord_client,
                                                  local_commons, monkeypatch):
    """The upload file and the issues report stay available for the file's
    lifetime (at most 7 days), also after the check can no longer be
    imported."""
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'A.jpg\nGone.jpg\n')
    round_id = new_round(coord_client, 'downloads')
    campaign_id = _campaign_of(coord_client, round_id)
    token = _check(coord_client, campaign_id)['data']['token']
    url = '/admin/campaign/%s/import/check/%s/' % (campaign_id, token)
    _after(monkeypatch, days=2)
    for kind in ('download', 'issues'):
        coord_client.fetch('coordinator: ' + kind, url + kind, as_user=COORD)
    _after(monkeypatch, days=8)
    resp = coord_client.fetch('coordinator: download', url + 'download', as_user=COORD,
                              error_code=400)
    assert 'import_check_expired' in _body(resp)


def test_every_use_of_the_folder_cleans_up(config):
    """Files are deleted after at most 7 days whenever the folder is used:
    a check, an import, a download, or the app starting."""
    stale, fresh = save(_result(), config), save(_result(), config)
    folder = config['import_check_path']
    week_ago = time.time() - 8 * 24 * 3600
    os.utime(os.path.join(folder, stale + '.json'), (week_ago, week_ago))
    with pytest.raises(ImportCheckExpired):
        load('x' * 32, config, CAMPAIGN)  # a failed load cleans up too
    assert os.listdir(folder) == [fresh + '.json']
    os.utime(os.path.join(folder, fresh + '.json'), (week_ago, week_ago))
    import_check.cleanup(config)  # what the app runs at start
    assert os.listdir(folder) == []


def test_app_start_cleans_up_the_check_folder(tmpdir):
    from montage.app import create_app
    from montage import utils
    folder = tmpdir.mkdir('checks')
    old = folder.join('A' * 32 + '.json')
    old.write('{}')
    week_ago = time.time() - 8 * 24 * 3600
    os.utime(str(old), (week_ago, week_ago))
    config = utils.load_env_config(env_name='devtest')
    config['db_url'] = 'sqlite:///' + str(tmpdir.join('app.db'))
    config['import_check_path'] = str(folder)
    from montage.tests.test_web_basic import _create_schema
    _create_schema(config['db_url'], echo=False)
    create_app('devtest', config=config)
    assert folder.listdir() == []


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


def test_name_taken_by_another_file_in_montage_is_left_out(montage_app, coord_client,
                                                          local_commons, monkeypatch):
    """Where entries.name has a unique index (beta, fresh installs), a new
    file whose name the database treats as equal to an existing row of
    another file cannot be stored: the save failed with IntegrityError 1062
    (beta, 2026-10-10). The check now finds it: a category leaves it out,
    a list blocks. Here: the same name, a different file (re-uploaded)."""
    local_commons([info('Photo.jpg', 1)])
    _source(monkeypatch, 'filename,file_id\nPhoto.jpg,1\n')
    round_a = new_round(coord_client, 'taken a')
    token = _check(coord_client, _campaign_of(coord_client, round_a))['data']['token']
    _import(coord_client, round_a, token)

    local_commons([info('Photo.jpg', 2), info('Other.jpg', 3)])
    round_b = new_round(coord_client, 'taken b')
    check = _check(coord_client, _campaign_of(coord_client, round_b),
                   import_method='category', category='Cat')['data']
    assert check['counts']['same_name_existing'] == 1
    assert not check['blocking'] and check['importable_count'] == 1
    issue = check['issues'][0]
    assert issue['reason_code'] == 'same-name-existing-category'
    assert issue['reason_params'] == ['Photo.jpg']
    data = _import(coord_client, round_b, check['token'], 'category')['data']
    assert data['new_round_entry_count'] == 1

    _source(monkeypatch, 'filename,file_id\nPhoto.jpg,2\nOther.jpg,3\n')
    check = _check(coord_client, _campaign_of(coord_client, round_b))['data']
    assert check['blocking'] and check['counts']['same_name_existing'] == 1
    assert check['issues'][0]['reason_code'] == 'same-name-existing'


def test_name_taken_check_follows_the_database_comparison(commons, monkeypatch):
    """The existing rows are those the database matches (on MariaDB: case,
    accents, е/ё); the same file (same file_id) or an old row of exactly
    this name without a file_id is reused, not a clash."""
    commons([info(u'Ленина_71А.jpg', 10), info('Same.jpg', 11), info('Legacy.jpg', 12),
             info('Free.jpg', 13)])
    monkeypatch.setattr(import_check, '_name_must_be_unique', lambda session: True)
    monkeypatch.setattr(import_check, '_existing_entries', lambda session, names: [
        (u'Ленина_71а.jpg', 9), ('same.jpg', 11), ('Legacy.jpg', None)])
    monkeypatch.setattr(import_check, 'same_name_keys',
                        lambda names, session=None: {n: n.lower() for n in names})
    result = run_check({'import_method': 'selected', 'file_names': [
        u'Ленина_71А.jpg', 'Same.jpg', 'Legacy.jpg', 'Free.jpg']},
        CAMPAIGN, source='local', rdb_session=object())
    assert statuses(result) == [(1, 'same_name_existing'), (2, 'ok'), (3, 'ok'), (4, 'ok')]
    assert result['rows'][0]['reason_params'] == [u'Ленина_71а.jpg']
    assert [r['row'] for r in blocking_rows(result)] == [1]


def test_name_taken_check_is_skipped_without_a_unique_index(commons, monkeypatch):
    """Production has no index on entries.name (#650): both rows are stored,
    and looking names up there would scan the whole table."""
    commons([info('A.jpg', 1)])
    monkeypatch.setattr(import_check, '_name_must_be_unique', lambda session: False)
    monkeypatch.setattr(import_check, '_existing_entries', lambda session, names: 1 / 0)
    monkeypatch.setattr(import_check, 'same_name_keys',
                        lambda names, session=None: {n: n for n in names})
    result = run_check({'import_method': 'selected', 'file_names': ['A.jpg']},
                       CAMPAIGN, source='local', rdb_session=object())
    assert statuses(result) == [(1, 'ok')]


def test_empty_import_is_not_reported_as_all_disqualified(montage_app, coord_client,
                                                         local_commons, monkeypatch):
    """#208: an import that brought no files also warned 'all entries
    disqualified by round settings' (0 >= 0)."""
    local_commons([])
    _source(monkeypatch, 'Gone.jpg\n')
    round_id = new_round(coord_client, 'empty')
    token = _check(coord_client, _campaign_of(coord_client, round_id))['data']['token']
    warnings = _import(coord_client, round_id, token)['data']['warnings']
    keys = [k for w in warnings for k in w]
    assert 'empty import' in keys and 'all disqualified' not in keys


def test_app_refuses_to_start_without_a_check_folder(monkeypatch):
    from montage.app import create_app
    monkeypatch.delenv('MONTAGE_IMPORT_CHECK_PATH', raising=False)
    with pytest.raises(ValueError) as exc:
        create_app('prod', config={'__file__': 'test', '__env__': 'prod',
                                   'db_url': 'sqlite://'})
    assert 'MONTAGE_IMPORT_CHECK_PATH' in str(exc.value)


# ---------------------------------------------------------------------------
# #447: a first round is created together with its import, or not at all
# ---------------------------------------------------------------------------

def _new_campaign(client, name):
    series_id = client.fetch('get default series', '/series')['data'][0]['id']
    return client.fetch('organizer: create campaign', '/admin/add_campaign',
                        {'name': name, 'coordinators': [COORD],
                         'open_date': '2015-01-01T00:00:00',
                         'close_date': '2016-01-01T00:00:00',
                         'url': 'http://hatnote.com', 'series_id': series_id},
                        as_user=COORD)['data']['id']


def _add_round(client, campaign_id, import_request=None, error_code=None):
    rnd = {'name': 'Round 1', 'vote_method': 'yesno',
           'deadline_date': '2016-10-15T00:00:00',
           'jurors': ['Slaporte', 'MahmoudHashemi', 'Effeietsanders']}
    if import_request is not None:
        rnd['import'] = import_request
    kw = {'error_code': error_code} if error_code else {}
    return client.fetch('coordinator: create round',
                        '/admin/campaign/%s/add_round' % campaign_id,
                        rnd, as_user=COORD, **kw)


def _rounds(client, campaign_id):
    return client.fetch('coordinator: campaign', '/admin/campaign/%s' % campaign_id,
                        as_user=COORD)['data']['rounds']


def test_create_round_with_its_import(montage_app, coord_client, local_commons,
                                      monkeypatch):
    local_commons([info('A.jpg', 1), info('B.jpg', 2)])
    _source(monkeypatch, 'A.jpg\nB.jpg\nGone.jpg\n')
    campaign_id = _new_campaign(coord_client, 'atomic ok')
    token = _check(coord_client, campaign_id)['data']['token']

    data = _add_round(coord_client, campaign_id,
                      {'import_method': 'csv', 'check_token': token})['data']

    assert data['import']['new_round_entry_count'] == 2
    assert any('import issues' in w for w in data['import']['warnings'])
    assert len(_rounds(coord_client, campaign_id)) == 1
    assert len(round_rows(montage_app, data['id'])) == 2


@pytest.mark.parametrize('case', ['no files', 'blocked', 'unknown token'])
def test_create_round_with_a_failing_import_creates_no_round(
        montage_app, coord_client, local_commons, monkeypatch, case):
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, {'no files': 'Gone.jpg\n',
                          'blocked': 'filename,file_id\nA.jpg,99\n',
                          'unknown token': 'A.jpg\n'}[case])
    campaign_id = _new_campaign(coord_client, 'atomic ' + case)
    token = _check(coord_client, campaign_id)['data']['token']
    if case == 'unknown token':
        token = 'x' * 32

    resp = _add_round(coord_client, campaign_id,
                      {'import_method': 'csv', 'check_token': token}, error_code=400)

    expected = {'no files': 'import_empty', 'blocked': 'import_check_blocked',
                'unknown token': 'import_check_expired'}[case]
    assert expected in _body(resp)
    assert _rounds(coord_client, campaign_id) == []
    assert db_query(montage_app, 'SELECT id FROM round_sources') == []
    # nothing blocks the next attempt (#447: "one active round at a time")
    assert _add_round(coord_client, campaign_id)['data']['id']


def test_create_round_without_import_is_unchanged(montage_app, coord_client):
    campaign_id = _new_campaign(coord_client, 'plain')
    data = _add_round(coord_client, campaign_id)['data']
    assert 'import' not in data and len(_rounds(coord_client, campaign_id)) == 1


def test_create_round_accepts_only_checked_import_methods(montage_app, coord_client):
    """B12: add_round's import goes through the check; import_method
    'round' (advance) would reach a KeyError (500)."""
    campaign_id = _new_campaign(coord_client, 'advance')
    resp = _add_round(coord_client, campaign_id,
                      {'import_method': 'round', 'check_token': 'x'}, error_code=400)
    assert 'import_method' in _body(resp)
    assert _rounds(coord_client, campaign_id) == []


def test_create_round_rolls_back_after_rows_were_written(montage_app, coord_client,
                                                         local_commons, monkeypatch):
    """B12: a failure after the entries and round entries were inserted
    leaves nothing behind either."""
    from montage import admin_endpoints
    from montage.utils import InvalidAction
    local_commons([info('Wr_A.jpg', 1), info('Wr_B.jpg', 2)])
    _source(monkeypatch, 'Wr_A.jpg\nWr_B.jpg\n')
    campaign_id = _new_campaign(coord_client, 'late failure')
    token = _check(coord_client, campaign_id)['data']['token']

    def late_failure(*a, **kw):
        raise InvalidAction('failed after the inserts')
    monkeypatch.setattr(admin_endpoints, 'autodisqualify', late_failure)
    _add_round(coord_client, campaign_id, {'import_method': 'csv', 'check_token': token},
               error_code=400)
    monkeypatch.undo()
    assert _rounds(coord_client, campaign_id) == []
    assert entry_ids(montage_app, 'Wr_') == {}
    assert db_query(montage_app, 'SELECT id FROM round_entries') == []
    assert db_query(montage_app, 'SELECT id FROM round_sources') == []
    assert db_query(montage_app, "SELECT id FROM audit_log_entries WHERE action = 'add_round_entries'") == []


def test_issues_report_download(montage_app, coord_client, local_commons, monkeypatch):
    """B13: every row that is not ok, also beyond the 1000 shown in the
    form, as a CSV report (the upload file leaves them out)."""
    local_commons([info('A.jpg', 1)])
    _source(monkeypatch, 'filename,file_id\nA.jpg,1\n=Gone.jpg,\nX.jpg,99\n')
    round_id = new_round(coord_client, 'issues')
    campaign_id = _campaign_of(coord_client, round_id)
    token = _check(coord_client, campaign_id)['data']['token']
    resp = coord_client.fetch('coordinator: issues report',
                              '/admin/campaign/%s/import/check/%s/issues' % (campaign_id, token),
                              as_user=COORD)
    assert resp.headers['Content-Disposition'].startswith(
        'attachment; filename=montage_import_issues-%s-' % campaign_id)
    rows = list(csv.reader(io.StringIO(_body(resp))))
    assert rows[0] == ['row', 'name', 'file_id', 'commons_name', 'status', 'reason']
    assert [(r[0], r[1], r[4]) for r in rows[1:]] == [
        ('3', "'=Gone.jpg", 'unknown_name'), ('4', 'X.jpg', 'unknown_file_id')]
