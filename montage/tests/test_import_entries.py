"""Tests for importing entries into a round (hatnote/montage#618).

add_entries / add_round_entries switched from one ORM INSERT per row to
multi-row INSERTs. These tests pin down that the database ends up exactly
as it did with the per-row implementation, across chunk boundaries,
re-imports, shared entries, odd filenames, reuploads, disqualification,
rollback on failure and task creation on activation.

All file data is synthetic.
"""
import datetime
import json
import zlib
from unittest.mock import patch

import pytest
import responses as responses_lib
from sqlalchemy import create_engine, text

from montage import admin_endpoints, rdb
from montage.rdb import (CoordinatorDAO, Entry, RoundEntry, IMPORT_CHUNK_SIZE,
                         PAUSED_STATUS, InvalidAction, chunked, to_unicode,
                         unique_iter)
from montage.tests.conftest import TOOLFORGE_CATEGORY_URL
from montage.tests.test_web_basic import montage_app, api_client  # noqa: F401 (fixtures)

COORD = 'Yarl'
OPEN_DATE = datetime.datetime(2015, 1, 1)

# Filenames that have tripped up SQL and encoding before: non-ASCII, quotes,
# percent signs (pymysql's executemany uses %-formatting), emoji (utf8mb4).
ODD_NAMES = [u'Храм_Спаса_на_Крови.jpg',
             u'Église_Saint-Épvre_Nancy.jpg',
             u"O'Brien's_\"quoted\"_bridge.jpg",
             u'100%_monument_%s_%(x)s.jpg',
             u'Monument_🏛_emoji.jpg',
             u'name with spaces.jpg']


# ---------------------------------------------------------------------------
# The per-row implementation from before #618, kept as the reference for the
# parity test. Verbatim from origin/master at 9bbe646.
# ---------------------------------------------------------------------------

def _legacy_add_entries(self, rnd, entries):
    seen_lower = {}
    deduped = []
    for e in entries:
        key = to_unicode(e.name).lower()
        if key not in seen_lower:
            seen_lower[key] = e.name
            deduped.append(e)
    entries = deduped

    entry_chunks = chunked(entries, IMPORT_CHUNK_SIZE)
    ret = []
    new_entry_count = 0

    for entry_chunk in entry_chunks:
        entry_names = [to_unicode(e.name) for e in entry_chunk]
        db_entries = self.get_entry_name_map(entry_names)

        for entry in entry_chunk:
            db_entry = db_entries.get(to_unicode(entry.name))
            if db_entry:
                entry = db_entry
            else:
                new_entry_count += 1
                self.rdb_session.add(entry)

            ret.append(entry)

    return ret, new_entry_count


def _legacy_add_round_entries(self, round_id, entries, method, params):
    rnd = self.user_dao.get_round(round_id)
    if rnd.status != PAUSED_STATUS:
        raise InvalidAction('round must be paused to add new entries')
    existing_names = (self.rdb_session.query(Entry.name)
                      .join(RoundEntry)
                      .filter_by(round=rnd)
                      .all())
    existing_names = set([n[0] for n in existing_names])
    new_entries = [e for e
                   in unique_iter(entries, key=lambda e: e.name)
                   if e.name not in existing_names]
    if not new_entries:
        return dict()
    round_source = self.get_or_create_round_source(round_id, method, params)
    self.rdb_session.flush()
    for new_entry in new_entries:
        new_round_entry = RoundEntry(entry_id=new_entry.id,
                                     round_id=round_id,
                                     round_source_id=round_source.id)
        self.rdb_session.add(new_round_entry)
    msg = ('%s added %s round entries, %s new'
           % (self.user.username, len(entries), len(new_entries)))
    if method:
        msg += ' (from %s)' % (method,)
    self.log_action('add_round_entries', message=msg, round=rnd)
    new_entry_stats = {'round_id': rnd.id,
                       'new_entry_count': len(entries),
                       'new_round_entry_count': len(new_entries),
                       'total_entries': len(rnd.entries)}
    return new_entry_stats


def _use_legacy_import():
    return [patch.object(CoordinatorDAO, 'add_entries', _legacy_add_entries),
            patch.object(CoordinatorDAO, 'add_round_entries',
                         _legacy_add_round_entries)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_file_infos(prefix, n, start=0, odd_names=False):
    """n synthetic file infos in the labs.py output shape, with variety:
    reuploads, missing file_id, low resolution, out-of-range upload dates,
    a disallowed filetype and a file uploaded by the coordinator."""
    base = datetime.datetime(2015, 9, 6)
    infos = []
    names = ['%s_%05d.jpg' % (prefix, i) for i in range(start, start + n)]
    if odd_names:
        names += [u'%s_%s' % (prefix, name) for name in ODD_NAMES]
    for i, name in enumerate(names):
        ts = (base + datetime.timedelta(minutes=i)).strftime('%Y%m%d%H%M%S')
        info = {'img_name': name,
                'img_major_mime': 'image',
                'img_minor_mime': 'jpeg',
                'img_width': '3264',
                'img_height': '2448',
                'img_user': str(5000000 + i % 17),
                'img_user_text': 'Uploader_%d' % (i % 17),
                'img_timestamp': ts,
                'oi_archive_name': '',
                'file_id': 100000 + start + i}
        if i % 7 == 3:  # reupload: carries flags, including a datetime
            info['oi_archive_name'] = '20160101000000!' + name
            info['rec_img_timestamp'] = '20160101000000'
            info['rec_img_user'] = '6000001'
            info['rec_img_text'] = 'Reuploader'
        if i % 5 == 4:  # CSV-style entry without a file_id
            info['file_id'] = None
        if i % 11 == 6:  # below the 2 MP minimum
            info['img_width'], info['img_height'] = '800', '600'
        if i % 13 == 9:  # uploaded after the campaign closed
            info['img_timestamp'] = '20170301120000'
        if i % 19 == 12:  # not an allowed filetype
            info['img_minor_mime'] = 'x-unknown'
        if i % 23 == 15:  # uploaded by a coordinator (dq_coords)
            info['img_user_text'] = COORD
        infos.append(info)
    return infos


def mock_category(mock_external_apis, file_infos):
    mock_external_apis.replace(responses_lib.POST, TOOLFORGE_CATEGORY_URL,
                               json={'file_infos': file_infos, 'no_info': []},
                               status=200)


def new_round(api_client, name, config=None, quorum=None, open_date=OPEN_DATE,
              close_date='2016-01-01T00:00:00'):
    """A paused round in a fresh campaign; returns the round id."""
    series_id = api_client.fetch('get default series', '/series')['data'][0]['id']
    campaign_id = api_client.fetch(
        'organizer: create campaign', '/admin/add_campaign',
        {'name': name,
         'coordinators': [COORD],
         'open_date': open_date.isoformat(),
         'close_date': close_date,
         'url': 'http://hatnote.com',
         'series_id': series_id},
        as_user=COORD)['data']['id']
    rnd = {'name': name + ' round 1',
           'vote_method': 'yesno',
           'deadline_date': '2016-10-15T00:00:00',
           'jurors': ['Slaporte', 'MahmoudHashemi', 'Effeietsanders']}
    if config is not None:
        rnd['config'] = config
    if quorum is not None:
        rnd['quorum'] = quorum
    return api_client.fetch('coordinator: create round',
                            '/admin/campaign/%s/add_round' % campaign_id,
                            rnd, as_user=COORD)['data']['id']


def import_category(api_client, round_id, **kw):
    return api_client.fetch_checked_import('coordinator: import category',
                                           round_id,
                                           {'import_method': 'category',
                                            'category': 'Synthetic_test_category'},
                                           as_user=COORD, **kw)


def _load_json(raw):
    return json.loads(raw) if raw else {}


def db_query(app, sql, **params):
    engine = create_engine(app.resources['config']['db_url'])
    try:
        with engine.connect() as conn:
            return [dict(row) for row in conn.execute(text(sql), **params)]
    finally:
        engine.dispose()


def round_rows(app, round_id, strip_prefix=''):
    """The round's entries as plain dicts, ids and timestamps dropped,
    JSON decoded (NULL and '{}' both read back as {} in the app)."""
    rows = db_query(app, '''
        SELECT e.*, re.dq_reason, re.dq_user_id, re.flags AS re_flags,
               rs.method AS source_method, rs.params AS source_params
        FROM round_entries re
        JOIN entries e ON e.id = re.entry_id
        LEFT JOIN round_sources rs ON rs.id = re.round_source_id
        WHERE re.round_id = :round_id''', round_id=round_id)
    ret = []
    for row in rows:
        row.pop('id')
        row.pop('create_date')
        row['flags'] = _load_json(row['flags'])
        row['re_flags'] = _load_json(row['re_flags'])
        row['source_params'] = _load_json(row['source_params'])
        # random per check (#510); stored, see test_check_token_is_stored...
        row['source_params'].pop('check_token', None)
        row['name'] = row['name'][len(strip_prefix):]
        if row['flags'].get('archive_name'):
            row['flags']['archive_name'] = row['flags']['archive_name'].replace(strip_prefix, '')
        ret.append(row)
    return sorted(ret, key=lambda r: r['name'])


def entry_ids(app, prefix):
    rows = db_query(app, "SELECT id, name FROM entries WHERE name LIKE :p",
                    p=prefix + '%')
    return {r['name']: r['id'] for r in rows}


def summarize_response(data, strip_prefix=''):
    data = dict(data)
    data.pop('round_id', None)
    dq = data.pop('disqualified', [])
    data['disqualified'] = sorted(
        (d['entry']['name'][len(strip_prefix):], d['dq_reason']) for d in dq)
    return data


@pytest.fixture
def coord_client(api_client):
    api_client.fetch('maintainer: add organizer', '/admin/add_organizer',
                     {'username': COORD})
    return api_client


# ---------------------------------------------------------------------------
# Parity with the per-row implementation
# ---------------------------------------------------------------------------

def _run_scenario(client, mock_external_apis, prefix):
    """Seed part of the files through one round, then import the full set
    (new + already-known entries, three chunks, odd names) into another."""
    seed = make_file_infos(prefix, 150, start=100)
    full = make_file_infos(prefix, 2 * IMPORT_CHUNK_SIZE + 37, odd_names=True)
    seed_round = new_round(client, prefix + ' seed')
    mock_category(mock_external_apis, seed)
    import_category(client, seed_round)

    main_round = new_round(client, prefix + ' main')
    mock_category(mock_external_apis, full)
    first = import_category(client, main_round)['data']
    again = import_category(client, main_round)['data']
    return main_round, first, again


def test_import_matches_per_row_implementation(montage_app, coord_client,
                                               mock_external_apis):
    patches = _use_legacy_import()
    for p in patches:
        p.start()
    try:
        old_round, old_first, old_again = _run_scenario(
            coord_client, mock_external_apis, 'old')
    finally:
        for p in patches:
            p.stop()
    new_round_id, new_first, new_again = _run_scenario(
        coord_client, mock_external_apis, 'new')

    assert summarize_response(new_first, 'new') == summarize_response(old_first, 'old')
    assert summarize_response(new_again, 'new') == summarize_response(old_again, 'old')

    old_rows = round_rows(montage_app, old_round, strip_prefix='old')
    new_rows = round_rows(montage_app, new_round_id, strip_prefix='new')
    assert len(new_rows) == 2 * IMPORT_CHUNK_SIZE + 37 + len(ODD_NAMES)
    for old, new in zip(old_rows, new_rows):
        assert new == old
    assert len(new_rows) == len(old_rows)

    # sanity: the scenario exercised what it claims to
    assert any(r['flags'].get('reupload') for r in new_rows)
    assert any(r['file_id'] is None for r in new_rows)
    assert any(r['dq_reason'] for r in new_rows)
    assert any(u'Храм' in r['name'] for r in new_rows)


# ---------------------------------------------------------------------------
# Counts, chunk boundaries, duplicates
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('n', [1, IMPORT_CHUNK_SIZE - 1, IMPORT_CHUNK_SIZE,
                               IMPORT_CHUNK_SIZE + 1, 2 * IMPORT_CHUNK_SIZE + 1])
def test_chunk_boundaries(n, montage_app, coord_client, mock_external_apis):
    prefix = 'chunk%d' % n
    infos = make_file_infos(prefix, n)
    round_id = new_round(coord_client, prefix)
    mock_category(mock_external_apis, infos)

    data = import_category(coord_client, round_id)['data']

    assert data['new_round_entry_count'] == n
    assert data['total_entries'] == n
    names = [r['name'] for r in round_rows(montage_app, round_id)]
    assert sorted(names) == sorted(i['img_name'] for i in infos)
    assert len(entry_ids(montage_app, prefix)) == n


def test_empty_category(montage_app, coord_client, mock_external_apis):
    round_id = new_round(coord_client, 'empty')
    mock_category(mock_external_apis, [])

    data = import_category(coord_client, round_id)['data']

    assert {'empty import': 'no entries imported'} in data['warnings']
    assert round_rows(montage_app, round_id) == []


def test_duplicate_and_case_variant_names(montage_app, coord_client,
                                          mock_external_apis):
    infos = make_file_infos('dup', 3)
    exact = dict(infos[0])
    case_variant = dict(infos[1], img_name=infos[1]['img_name'].upper())
    round_id = new_round(coord_client, 'dup')
    mock_category(mock_external_apis, infos + [exact, case_variant])

    data = import_category(coord_client, round_id)['data']

    assert data['new_round_entry_count'] == 3
    names = sorted(r['name'] for r in round_rows(montage_app, round_id))
    assert names == sorted(i['img_name'] for i in infos)


def test_reimport_adds_only_new_files(montage_app, coord_client,
                                      mock_external_apis):
    first = make_file_infos('re', 250)
    more = make_file_infos('re', 60, start=250)
    round_id = new_round(coord_client, 're')
    mock_category(mock_external_apis, first)
    import_category(coord_client, round_id)
    ids_before = entry_ids(montage_app, 're')

    mock_category(mock_external_apis, first + more)
    data = import_category(coord_client, round_id)['data']

    assert data['new_round_entry_count'] == 60
    assert data['total_entries'] == 310
    ids_after = entry_ids(montage_app, 're')
    assert len(ids_after) == 310
    # existing entries keep their rows
    assert {k: ids_after[k] for k in ids_before} == ids_before


def test_entries_shared_between_campaigns(montage_app, coord_client,
                                          mock_external_apis):
    infos = make_file_infos('shared', 230)
    round_a = new_round(coord_client, 'shared a')
    round_b = new_round(coord_client, 'shared b')
    mock_category(mock_external_apis, infos)

    import_category(coord_client, round_a)
    ids_a = entry_ids(montage_app, 'shared')
    data_b = import_category(coord_client, round_b)['data']

    assert data_b['new_round_entry_count'] == 230
    assert entry_ids(montage_app, 'shared') == ids_a  # no new entry rows
    rows_b = db_query(montage_app,
                      'SELECT entry_id FROM round_entries WHERE round_id = :r',
                      r=round_b)
    assert sorted(r['entry_id'] for r in rows_b) == sorted(ids_a.values())


# ---------------------------------------------------------------------------
# Failure and follow-on behaviour
# ---------------------------------------------------------------------------

def test_failed_import_leaves_nothing_behind(montage_app, coord_client,
                                             mock_external_apis):
    """An error after the inserts must roll them back (the batched insert
    runs in the request's transaction like the ORM inserts did)."""
    infos = make_file_infos('rollback', 220)
    round_id = new_round(coord_client, 'rollback')
    mock_category(mock_external_apis, infos)

    def boom(*a, **kw):
        raise RuntimeError('fail after inserting')

    with patch.object(admin_endpoints, 'autodisqualify', boom):
        import_category(coord_client, round_id, error_code=500)

    assert entry_ids(montage_app, 'rollback') == {}
    assert round_rows(montage_app, round_id) == []
    assert db_query(montage_app,
                    'SELECT id FROM round_sources WHERE round_id = :r',
                    r=round_id) == []


def test_activation_assigns_tasks_for_imported_entries(montage_app, coord_client,
                                                       mock_external_apis):
    infos = make_file_infos('tasks', 240)
    round_id = new_round(coord_client, 'tasks', quorum=2)
    mock_category(mock_external_apis, infos)
    import_category(coord_client, round_id)

    coord_client.fetch('coordinator: activate round',
                       '/admin/round/%s/activate' % round_id,
                       {'post': True}, as_user=COORD)

    eligible = [r for r in round_rows(montage_app, round_id) if not r['dq_reason']]
    votes = db_query(montage_app, '''
        SELECT v.round_entry_id FROM votes v
        JOIN round_entries re ON re.id = v.round_entry_id
        WHERE re.round_id = :r''', r=round_id)
    assert len(eligible) > 0
    assert len(votes) == 2 * len(eligible)


def test_total_entries_correct_when_round_entries_already_loaded(
        montage_app, coord_client, mock_external_apis):
    """add_round_entries inserts outside the session; a round whose
    round_entries were loaded earlier in the request must not report a
    stale count."""
    infos = make_file_infos('stale', 120)
    round_id = new_round(coord_client, 'stale')
    mock_category(mock_external_apis, infos[:20])
    import_category(coord_client, round_id)

    real_get_or_create = CoordinatorDAO.get_or_create_round_source

    def load_entries_then_get_source(self, round_id, *a, **kw):
        # runs right before the batched insert in add_round_entries
        source = real_get_or_create(self, round_id, *a, **kw)
        assert len(self.user_dao.get_round(round_id).round_entries) == 20
        return source

    mock_category(mock_external_apis, infos)
    with patch.object(CoordinatorDAO, 'get_or_create_round_source',
                      load_entries_then_get_source):
        data = import_category(coord_client, round_id)['data']

    assert data['total_entries'] == 120


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------

def test_mysql_driver_batches_the_inserts():
    """pymysql only turns executemany into multi-row INSERTs when the
    statement matches its INSERT ... VALUES pattern."""
    from pymysql.cursors import RE_INSERT_VALUES
    from sqlalchemy.dialects.mysql import pymysql as mysql_pymysql

    dialect = mysql_pymysql.dialect()
    for table, keys in ((rdb.entries_t, rdb._ENTRY_INSERT_COLS),
                        (rdb.round_entries_t,
                         ['entry_id', 'round_id', 'round_source_id'])):
        sql = str(table.insert().compile(dialect=dialect, column_keys=keys))
        assert RE_INSERT_VALUES.match(sql), sql


# ---------------------------------------------------------------------------
# Lookup by file_id (#513, #654); since #510 in every campaign, not only in
# campaigns opened from 2026-06-01 (the former FILE_ID_LOOKUP_CUTOFF)
# ---------------------------------------------------------------------------

AFTER_CUTOFF = datetime.datetime(2026, 6, 1) + datetime.timedelta(days=30)


def with_file_ids(infos):
    """The same files, all with a file_id (as wikireplica imports give);
    a missing one is derived from the name, so it is stable and unique."""
    return [dict(info, file_id=info['file_id']
                 or 10 ** 7 + zlib.crc32(info['img_name'].encode('utf8')))
            for info in infos]


def new_round_after_cutoff(api_client, name):
    return new_round(api_client, name, open_date=AFTER_CUTOFF,
                     close_date='2026-12-31T00:00:00')


def _no_name_lookup(*a, **kw):
    raise AssertionError('looked up entries by name')


def _no_file_id_lookup(*a, **kw):
    raise AssertionError('looked up entries by file_id')


def test_file_id_lookup_after_cutoff(montage_app, coord_client,
                                     mock_external_apis, monkeypatch):
    first = with_file_ids(make_file_infos('fid', IMPORT_CHUNK_SIZE + 50))
    more = with_file_ids(make_file_infos('fid', 30, start=500))
    round_id = new_round_after_cutoff(coord_client, 'fid')
    # production's indexes on entries: file_id yes, name no
    monkeypatch.setattr(rdb, '_entries_indexes', lambda session: (
        {'PRIMARY', 'ix_entries_file_id'}, {'id', 'file_id'}))
    monkeypatch.setattr(CoordinatorDAO, 'get_entry_name_map', _no_name_lookup)

    mock_category(mock_external_apis, first)
    data = import_category(coord_client, round_id)['data']
    assert data['new_round_entry_count'] == len(first)
    ids_before = entry_ids(montage_app, 'fid')
    assert len(ids_before) == len(first)

    mock_category(mock_external_apis, first + more)
    data = import_category(coord_client, round_id)['data']
    assert data['new_round_entry_count'] == 30
    ids_after = entry_ids(montage_app, 'fid')
    assert len(ids_after) == len(first) + 30
    assert {k: ids_after[k] for k in ids_before} == ids_before

    # a second campaign after the cutoff reuses the same rows
    other = new_round_after_cutoff(coord_client, 'fid other')
    data = import_category(coord_client, other)['data']
    assert data['new_round_entry_count'] == len(first) + 30
    assert entry_ids(montage_app, 'fid') == ids_after


def test_file_id_lookup_in_old_campaigns_too(montage_app, coord_client,
                                            mock_external_apis, monkeypatch):
    """#510: checked imports match by file_id whatever the campaign's open
    date; #654 did so only from 2026-06-01."""
    infos = with_file_ids(make_file_infos('old', 40))
    round_id = new_round(coord_client, 'old')  # opens in 2015
    monkeypatch.setattr(rdb, '_entries_indexes', lambda session: (
        {'PRIMARY', 'ix_entries_file_id'}, {'id', 'file_id'}))
    monkeypatch.setattr(CoordinatorDAO, 'get_entry_name_map', _no_name_lookup)
    mock_category(mock_external_apis, infos)
    import_category(coord_client, round_id)
    assert len(entry_ids(montage_app, 'old')) == 40


def test_name_lookup_when_a_file_id_is_missing(montage_app, coord_client,
                                               mock_external_apis,
                                               monkeypatch):
    infos = make_file_infos('nofid', 40)  # some have file_id None
    assert any(info['file_id'] is None for info in infos)
    round_id = new_round_after_cutoff(coord_client, 'nofid')
    monkeypatch.setattr(CoordinatorDAO, 'get_entry_file_id_map',
                        _no_file_id_lookup)
    mock_category(mock_external_apis, infos)
    import_category(coord_client, round_id)
    assert len(entry_ids(montage_app, 'nofid')) == 40


def test_file_id_lookup_keeps_the_row_of_a_renamed_file(montage_app,
                                                        coord_client,
                                                        mock_external_apis):
    infos = with_file_ids(make_file_infos('ren', 3))
    round_a = new_round_after_cutoff(coord_client, 'ren a')
    mock_category(mock_external_apis, infos)
    import_category(coord_client, round_a)
    ids = entry_ids(montage_app, 'ren')

    renamed = [dict(infos[0], img_name='ren_renamed.jpg')] + infos[1:]
    round_b = new_round_after_cutoff(coord_client, 'ren b')
    mock_category(mock_external_apis, renamed)
    data = import_category(coord_client, round_b)['data']
    assert data['new_round_entry_count'] == 3
    assert entry_ids(montage_app, 'ren') == ids  # no row for the new name


def test_file_id_lookup_keeps_the_row_of_a_file_without_file_id(
        montage_app, coord_client, mock_external_apis):
    # imported before the cutoff, so stored without a file_id
    infos = with_file_ids(make_file_infos('pre', 5))
    old_round = new_round(coord_client, 'pre old')
    mock_category(mock_external_apis,
                  [dict(info, file_id=None) for info in infos])
    import_category(coord_client, old_round)
    ids = entry_ids(montage_app, 'pre')

    # the same files after the cutoff, now with a file_id: where entries.name
    # is indexed (here unique, as on beta) they keep their rows
    new = new_round_after_cutoff(coord_client, 'pre new')
    mock_category(mock_external_apis, infos)
    data = import_category(coord_client, new)['data']
    assert data['new_round_entry_count'] == 5
    assert entry_ids(montage_app, 'pre') == ids


def test_entries_indexes_works_with_the_apps_connect_listener():
    """The app runs SET NAMES on every new connection (app.py); reflecting
    on the engine then hit a closed connection on montage-dev."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    engine = create_engine('sqlite://')
    rdb.Base.metadata.create_all(engine)

    def like_set_names(connection, branch):
        connection.execute('PRAGMA foreign_keys = ON')  # no rows, like SET NAMES

    event.listen(engine, 'engine_connect', like_set_names)
    session = sessionmaker(bind=engine)()
    session.query(Entry.id).first()
    rdb._ENTRIES_INDEX_CACHE.clear()
    names, first_columns = rdb._entries_indexes(session)
    assert 'name' in first_columns
    session.query(Entry.id).first()  # the session is still usable


def test_entries_indexes_reads_the_database():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine('sqlite://')
    rdb.Base.metadata.create_all(engine)
    names, first_columns = rdb._entries_indexes(sessionmaker(bind=engine)())
    assert 'name' in first_columns          # the model's unique index
    assert 'ix_entries_file_id' not in names  # only migrate_prod_db.sql adds it


def test_file_id_lookups_stay_below_the_index_dive_limit(
        montage_app, coord_client, mock_external_apis, monkeypatch):
    """MariaDB stops using ix_entries_file_id for IN lists of 200 values or
    more (eq_range_index_dive_limit); see rdb.FILE_ID_LOOKUP_CHUNK_SIZE."""
    assert rdb.FILE_ID_LOOKUP_CHUNK_SIZE < 200
    sizes = []
    real_lookup = CoordinatorDAO.get_entry_file_id_map

    def recording_lookup(self, file_ids):
        sizes.append(len(file_ids))
        return real_lookup(self, file_ids)

    monkeypatch.setattr(CoordinatorDAO, 'get_entry_file_id_map',
                        recording_lookup)
    infos = with_file_ids(make_file_infos('dive', 450))
    round_id = new_round_after_cutoff(coord_client, 'dive')
    mock_category(mock_external_apis, infos)
    import_category(coord_client, round_id)

    assert len(entry_ids(montage_app, 'dive')) == 450
    assert sizes and max(sizes) <= rdb.FILE_ID_LOOKUP_CHUNK_SIZE
