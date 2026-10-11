# -*- coding: utf-8 -*-
"""tools/analyze_file_id.py (hatnote/montage#513): the classification rule,
with synthetic rows shaped like the replica cases seen on 2026-10-10."""
import io
import os
import json
import datetime
import importlib.util

_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'analyze_file_id.py')
_spec = importlib.util.spec_from_file_location('analyze_file_id', _PATH)
af = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(af)

UPLOADER, OTHER, BOT = 11, 22, 33
BOTS = {UPLOADER: False, OTHER: False, BOT: True}


def row(**kw):
    r = {'id': 1, 'name': 'Example.jpg', 'upload_date': '20200101120000',
         'width': 4000, 'height': 3000, 'first_seen': '20200915000000',
         'last_seen': '20201031000000'}
    r.update(kw)
    return r


def ver(stamp, sha1='a' * 31, actor=UPLOADER, deleted=0, width=4000, height=3000):
    return {'fr_id': int(stamp[-6:]), 'ts': stamp, 'sha1': sha1, 'width': width,
            'height': height, 'deleted': deleted, 'actor': actor}


def up(stamp, sha1='a' * 31, action='upload', actor=UPLOADER, deleted=0, params=True):
    return {'type': 'upload', 'action': action, 'ts': stamp, 'deleted': deleted,
            'actor': actor, 'sha1': sha1 if params else None,
            'img_ts': stamp if params else None}


def log(type_, action, stamp):
    return {'type': type_, 'action': action, 'ts': stamp, 'deleted': 0, 'actor': UPLOADER,
            'sha1': None, 'img_ts': None}


LIVE = {'file_id': 500, 'file_deleted': 0, 'file_latest': 1}


def decide(r, file_row, versions, logs, archive=(), page_logs=None):
    return af.classify(r, file_row, list(versions), list(logs), list(archive), BOTS,
                       page_logs)


# -- helpers ------------------------------------------------------------------

def test_parse_upload_params_new_and_old():
    params = ('a:3:{s:8:"img_sha1";s:31:"pbk7ynph3k98l3223guhep8eo86enie";'
              's:13:"img_timestamp";s:14:"20261007200602";s:17:"associated_rev_id";i:1;}')
    assert af.parse_upload_params(params.encode()) == (
        'pbk7ynph3k98l3223guhep8eo86enie', '20261007200602')
    assert af.parse_upload_params(b'') == (None, None)   # before mid-2013
    assert af.parse_upload_params(None) == (None, None)


def test_ts_and_canonical_names():
    assert af.ts(datetime.datetime(2020, 1, 2, 3, 4, 5)) == '20200102030405'
    assert af.ts(b'20200102030405') == '20200102030405'
    assert af.ts(None) is None and af.ts('0000') is None
    assert af.is_canonical('Ab c.jpg')
    assert not af.is_canonical('ab.jpg')
    assert not af.is_canonical('File:Ab.jpg')
    assert not af.is_canonical('Ab  c.jpg')


def test_every_query_is_a_select():
    queries = {k: v for k, v in vars(af).items() if k.endswith('_QUERY')}
    assert len(queries) == 9
    for name, sql in queries.items():
        assert sql.strip().upper().startswith('SELECT'), name
        for word in ('UPDATE ', 'INSERT ', 'DELETE ', 'REPLACE ', 'ALTER ', 'DROP '):
            assert word not in sql.upper(), (name, word)


# -- settled tiers ------------------------------------------------------------

def test_tier1_one_upload_one_version():
    cat, flags, _ = decide(row(), LIVE, [ver('20200101120000')], [up('20200101120000')])
    assert cat == 'tier1'
    assert 'date_matches_version' in flags and 'size_matches_at_import' in flags


def test_tier1_before_2013_is_marked_timestamp_only():
    cat, flags, _ = decide(row(upload_date='20110101120000'), LIVE,
                           [ver('20110101120000')], [up('20110101120000', params=False)])
    assert cat == 'tier1' and 'ts_only' in flags


def test_sha1_differs_from_log_is_not_tier1():
    cat, flags, _ = decide(row(), LIVE, [ver('20200101120000', sha1='b' * 31)],
                           [up('20200101120000')])
    assert cat == 'other' and 'sha1_mismatch' in flags


def test_upload_after_first_import():
    # the name showed something else (or nothing) when Montage imported it
    cat, _, _ = decide(row(first_seen='20190101000000'), LIVE,
                       [ver('20200101120000')], [up('20200101120000')])
    assert cat == 'upload_after_import'


def test_tier2a_uploader_and_bot_before_import():
    versions = [ver('20200101120000'), ver('20200102120000', 'c' * 31, actor=BOT),
                ver('20200103120000', 'd' * 31)]
    logs = [up('20200101120000'), up('20200102120000', 'c' * 31, 'overwrite', BOT),
            up('20200103120000', 'd' * 31, 'overwrite')]
    cat, _, ev = decide(row(), LIVE, versions, logs)
    assert cat == 'tier2a' and ev['bots'] == [BOT]


def test_tier2b_other_person_overwrote_before_import():
    versions = [ver('20200101120000'), ver('20200102120000', 'c' * 31, actor=OTHER)]
    logs = [up('20200101120000'), up('20200102120000', 'c' * 31, 'overwrite', OTHER)]
    assert decide(row(), LIVE, versions, logs)[0] == 'tier2b'


def test_new_version_after_first_import_says_who():
    versions = [ver('20200101120000'), ver('20201001120000', 'c' * 31, actor=BOT),
                ver('20201002120000', 'd' * 31, actor=OTHER)]
    logs = [up('20200101120000'), up('20201001120000', 'c' * 31, 'overwrite', BOT),
            up('20201002120000', 'd' * 31, 'overwrite', OTHER)]
    cat, flags, _ = decide(row(), LIVE, versions, logs)
    assert cat == 'changed_after'
    assert 'later_by_bot' in flags and 'later_by_other' in flags
    assert 'later_by_uploader' not in flags


def test_size_mismatch_is_flagged():
    _, flags, _ = decide(row(width=100), LIVE, [ver('20200101120000')],
                         [up('20200101120000')])
    assert 'size_mismatch_at_import' in flags and 'size_matches_at_import' not in flags


# -- whole file deleted (D1) ---------------------------------------------------

DELETED = {'file_id': 500, 'file_deleted': 1, 'file_latest': 0}


def test_still_deleted_after_last_seen_is_settled():
    logs = [up('20200101120000'), log('delete', 'delete', '20210101000000')]
    cat, _, ev = decide(row(), DELETED, [], logs)
    assert cat == 'deleted_settled' and ev['deleted_ts'] == '20210101000000'


def test_still_deleted_while_jurors_could_still_look_is_mixed():
    logs = [up('20200101120000'), log('delete', 'delete', '20201001000000')]
    assert decide(row(), DELETED, [], logs)[0] == 'deleted_mixed'


def test_suppressed_whole_file_is_flagged():
    logs = [up('20200101120000'), log('delete', 'delete', '20210101000000')]
    _, flags, _ = decide(row(), dict(DELETED, file_deleted=3), [], logs)
    assert 'file_suppressed' in flags


def test_deleted_before_migration_has_no_row():
    # the 2012 examples: archive only
    archive = [{'ts': '20120629044749', 'sha1': 'r' * 31,
                'deleted_ts': '20120629224925', 'archive_name': ''}]
    cat, _, _ = decide(row(), None, [], [up('20120629044749', params=False),
                                         log('delete', 'delete', '20120629224925')], archive)
    assert cat == 'deleted_no_row'


def test_name_reused_before_the_import_is_judged_by_the_current_file():
    # Bajo_cero.jpg: uploaded 2012, deleted 2012, new upload 2022, imported 2023
    logs = [up('20120629202534', params=False), log('delete', 'delete', '20120629224347'),
            up('20220909054242', 'n' * 31)]
    cat, flags, _ = decide(row(first_seen='20230101000000', last_seen='20230301000000',
                               upload_date='20220909054242'),
                           LIVE, [ver('20220909054242', 'n' * 31)], logs)
    assert cat == 'reused_tier1' and 'upload_without_version' in flags


def test_name_reused_after_the_import():
    # imported 2020, deleted 2021, another image uploaded under the name 2022
    logs = [up('20200101120000'), log('delete', 'delete', '20210101000000'),
            up('20220101000000', 'n' * 31)]
    cat, _, _ = decide(row(), LIVE, [ver('20220101000000', 'n' * 31)], logs)
    assert cat == 'name_reused'


def test_deleted_and_restored():
    logs = [up('20200101120000'), log('delete', 'delete', '20200201000000'),
            log('delete', 'restore', '20200301000000')]
    assert decide(row(), LIVE, [ver('20200101120000')], logs)[0] == 'restored'


# -- versions deleted or hidden while the file stays live (D2-D4) --------------

def test_hidden_version():
    # JRShibuya: the 2015 version hidden after a 2026 overwrite
    versions = [ver('20150823074021', deleted=1), ver('20200102120000', 'c' * 31)]
    logs = [up('20150823074021'), up('20200102120000', 'c' * 31, 'overwrite')]
    cat, flags, _ = decide(row(), LIVE, versions, logs)
    assert cat == 'version_hidden' and 'version_hidden' in flags


def test_suppressed_version_is_flagged():
    versions = [ver('20200101120000', deleted=9), ver('20200102120000', 'c' * 31)]
    logs = [up('20200101120000'), up('20200102120000', 'c' * 31, 'overwrite')]
    _, flags, _ = decide(row(), LIVE, versions, logs)
    assert 'version_suppressed' in flags


def test_old_version_deleted():
    # D2: an upload entry without its version (moved to the archive)
    logs = [up('20200101120000'), up('20200102120000', 'c' * 31, 'overwrite')]
    cat, flags, _ = decide(row(), LIVE, [ver('20200102120000', 'c' * 31)], logs)
    assert cat == 'version_hidden' and 'upload_without_version' in flags


# -- moves --------------------------------------------------------------------

def test_moved_away_no_file_under_the_name():
    # Villa_(2).jpg
    logs = [up('20251018123515'), log('move', 'move', '20261010185936')]
    assert decide(row(), None, [], logs)[0] == 'moved_away'


def test_moved_in_without_page_history():
    assert decide(row(), LIVE, [ver('20200101120000')], [])[0] == 'moved_in'


def test_moved_in_before_the_import_is_judged_by_the_page_history():
    page = [up('20200101120000'), log('move', 'move', '20200201000000')]
    cat, _, ev = decide(row(), LIVE, [ver('20200101120000')], [], page_logs=page)
    assert cat == 'moved_in_tier1' and ev['last_move_ts'] == '20200201000000'


def test_moved_in_after_the_import_stays_open():
    page = [up('20200101120000'), log('move', 'move', '20201001000000')]
    cat, flags, _ = decide(row(), LIVE, [ver('20200101120000')], [], page_logs=page)
    assert cat == 'moved_in' and 'page_history_read' in flags


def test_needs_page_history_only_for_versions_without_upload_here():
    assert af.needs_page_history(LIVE, [ver('20200101120000')], [])
    assert not af.needs_page_history(LIVE, [ver('20200101120000')], [up('20200101120000')])
    assert not af.needs_page_history(None, [], [])
    assert not af.needs_page_history(DELETED, [], [])


def test_not_found():
    assert decide(row(), None, [], [])[0] == 'not_found'


def test_hidden_log_entry_is_not_tier1():
    logs = [up('20200101120000', deleted=4)]
    cat, flags, _ = decide(row(), LIVE, [ver('20200101120000')], logs)
    assert cat == 'other' and 'log_hidden' in flags


def test_row_in_no_round_is_flagged():
    _, flags, _ = decide(row(last_seen=None), LIVE, [ver('20200101120000')],
                         [up('20200101120000')])
    assert 'no_rounds' in flags


# -- the run loop, with stand-ins for both databases ---------------------------

class FakeMontage(object):
    """Read-only stand-in: it has no method that could write."""
    def __init__(self, rows):
        self.rows = rows

    def entries(self, after_id, every, limit):
        return [r for r in self.rows if r['id'] > after_id and r['id'] % every == 0][:limit]

    def last_seen(self, ids):
        return {i: ('20201031000000', 2, 1 if i == 2 else 0) for i in ids}


class FakeReplica(object):
    bots_ok = True

    def page_history(self, names):
        return {}

    def __init__(self):
        self.bot_cache = dict(BOTS)
        self.bot_names = {BOT: 'ExampleBot'}

    def lookup(self, names):
        names = list(names)
        files = {n: dict(LIVE) for n in names if n != 'Gone.jpg'}
        versions = {500: [ver('20200101120000')]}
        logs = {n: [up('20200101120000')] for n in names}
        return files, versions, logs, {}


def test_analyze_writes_rows_and_summary(tmp_path):
    rows = [{'id': i, 'name': 'Gone.jpg' if i == 4 else 'F %d.jpg' % i,
             'upload_date': '20200101120000', 'width': 4000, 'height': 3000,
             'first_seen': '20200915000000'} for i in range(1, 9)]
    out = io.StringIO()
    summary = af.analyze(FakeMontage(rows), FakeReplica(), str(tmp_path), every=2,
                         batch_size=2, sleep=0, out=out)
    assert summary['rows'] == 4 and summary['batches'] == 2 and summary['last_id'] == 8
    assert summary['categories'] == {'tier1': 3, 'not_found': 1}
    assert summary['flags'].get('tier1 round_not_closed') == 1
    lines = (tmp_path / 'rows.tsv').read_text(encoding='utf-8').splitlines()
    assert lines[0].startswith('#analyze_file_id') and len(lines) == 2 + 4
    assert 'Gone' not in '\n'.join(lines)          # no names in the output
    inspect = (tmp_path / 'inspect.tsv').read_text(encoding='utf-8').splitlines()
    assert len(inspect) == 1 and inspect[0].split('\t')[1:3] == ['not_found', 'Gone.jpg']
    saved = json.loads((tmp_path / 'summary-8.json').read_text(encoding='utf-8'))
    assert saved['categories'] == summary['categories']


def test_analyze_resumes_after_id(tmp_path):
    rows = [{'id': i, 'name': 'F %d.jpg' % i, 'upload_date': '20200101120000',
             'width': 4000, 'height': 3000, 'first_seen': '20200915000000'}
            for i in range(1, 9)]
    summary = af.analyze(FakeMontage(rows), FakeReplica(), str(tmp_path), every=1,
                         after_id=5, batch_size=10, sleep=0, out=io.StringIO())
    assert summary['rows'] == 3 and summary['last_id'] == 8
