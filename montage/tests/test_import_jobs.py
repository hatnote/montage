"""Tests for background import jobs (hatnote/montage#621, origin #618).

The import endpoint queues an import_jobs row; montage.import_worker runs
it. Covers enqueue, the worker (claim, fenced commit, failure), the
Phase 1 stuck-job rule, the activation gate, import_state in admin
payloads, and the MONTAGE_IMPORT_MODE=sync rollback switch.

All file data is synthetic.
"""
import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from montage import admin_endpoints, import_worker, rdb
from montage.app import make_engine
from montage.rdb import ImportJob, User
from montage.tests.conftest import (run_import_jobs, SELECTED_FILE_INFO,
                                    TOOLFORGE_FILE_URL)
from montage.tests.test_import_entries import (COORD, db_query, new_round,
                                               import_category, mock_category,
                                               make_file_infos)
from montage.tests.test_web_basic import montage_app, api_client  # noqa: F401 (fixtures)

import responses as responses_lib


@pytest.fixture
def coord_client(api_client):
    api_client.fetch('maintainer: add organizer', '/admin/add_organizer',
                     {'username': COORD})
    return api_client


@pytest.fixture
def engine(montage_app):
    eng = make_engine(montage_app.resources['config'])
    yield eng
    eng.dispose()


def activate(client, round_id, **kw):
    return client.fetch('coordinator: activate round',
                        '/admin/round/%s/activate' % round_id,
                        {'post': True}, as_user=COORD, **kw)


def get_job(client, round_id, job_id, **kw):
    resp = client.fetch('coordinator: get import job',
                        '/admin/round/%s/import/%s' % (round_id, job_id),
                        as_user=COORD, **kw)
    return resp if kw.get('error_code') else resp['data']


def get_round(client, round_id):
    return client.fetch('coordinator: get round',
                        '/admin/round/%s' % round_id, as_user=COORD)['data']


def error_text(resp):
    return resp.get_data(as_text=True)


def round_entry_count(app, round_id):
    return len(db_query(app, 'SELECT id FROM round_entries WHERE round_id = :r',
                        r=round_id))


def seed_job(app, round_id, status, **kw):
    """Insert an import job row directly; returns its id."""
    eng = create_engine(app.resources['config']['db_url'])
    session = sessionmaker(bind=eng)()
    try:
        user = session.query(User).filter_by(username=COORD).one()
        job = ImportJob(round_id=round_id, user_id=user.id, status=status,
                        method='category', params={'category': 'Seeded'},
                        **kw)
        session.add(job)
        session.commit()
        return job.id
    finally:
        session.close()
        eng.dispose()


def set_job(app, job_id, **values):
    sets = ', '.join('%s = :%s' % (k, k) for k in values)
    eng = create_engine(app.resources['config']['db_url'])
    try:
        with eng.begin() as conn:
            conn.execute(text('UPDATE import_jobs SET %s WHERE id = :id'
                              % sets), id=job_id, **values)
    finally:
        eng.dispose()


def campaign_id_of(client, round_id):
    return get_round(client, round_id)['campaign']['id']


# ---------------------------------------------------------------------------
# Enqueue and worker
# ---------------------------------------------------------------------------

def test_enqueue_returns_queued_without_external_calls(
        montage_app, coord_client, mock_external_apis):
    """AC1: the request only records the job; no wikireplica/API call."""
    round_id = new_round(coord_client, 'enqueue')
    calls_before = len(mock_external_apis.calls)
    data = import_category(coord_client, round_id)['data']
    assert len(mock_external_apis.calls) == calls_before
    assert data['round_id'] == round_id
    assert data['job']['status'] == 'queued'
    assert data['job']['params_summary'] == {
        'category': 'Synthetic_test_category'}
    assert 'new_entry_count' not in data
    assert round_entry_count(montage_app, round_id) == 0

    jobs = coord_client.fetch('coordinator: list import jobs',
                              '/admin/round/%s/imports' % round_id,
                              as_user=COORD)['data']
    assert [j['id'] for j in jobs] == [data['job']['id']]


def test_worker_runs_job(montage_app, coord_client, mock_external_apis):
    """AC2: after the worker ran, the job succeeded with the imported rows
    and the audit log has add_round_entries."""
    round_id = new_round(coord_client, 'worker runs')
    job = import_category(coord_client, round_id)['data']['job']
    assert run_import_jobs(montage_app) == [(job['id'], 'succeeded')]

    details = get_job(coord_client, round_id, job['id'])
    assert details['status'] == 'succeeded'
    assert details['entry_count'] == 20
    assert details['new_round_entry_count'] == 20
    assert details['disqualified_count'] == 0
    assert details['error'] is None
    assert details['requested_by'] == COORD
    assert details['finish_date']
    assert round_entry_count(montage_app, round_id) == 20

    campaign_id = campaign_id_of(coord_client, round_id)
    audit = coord_client.fetch(
        'coordinator: audit log',
        '/admin/campaign/%s/audit?action=add_round_entries' % campaign_id,
        as_user=COORD)['data']
    assert audit
    enq = coord_client.fetch(
        'coordinator: audit log',
        '/admin/campaign/%s/audit?action=enqueue_import' % campaign_id,
        as_user=COORD)['data']
    assert len(enq) == 1

    state = get_round(coord_client, round_id)['import_state']
    assert state['status'] == 'succeeded'
    assert state['blocks_activation'] is False
    activate(coord_client, round_id)


def test_loader_failure_marks_job_failed(montage_app, coord_client,
                                         mock_external_apis):
    """AC3: a failing fetch leaves a failed job with a reason, no rows,
    an import_failed audit entry, and blocks activation."""
    round_id = new_round(coord_client, 'loader fails')
    job = import_category(coord_client, round_id)['data']['job']

    def boom(*a, **kw):
        raise RuntimeError('boom')

    with patch.object(import_worker, 'load_import_entries', boom):
        assert run_import_jobs(montage_app) == [(job['id'], 'failed')]

    details = get_job(coord_client, round_id, job['id'])
    assert details['status'] == 'failed'
    assert 'boom' in details['error']
    assert round_entry_count(montage_app, round_id) == 0
    assert db_query(montage_app,
                    'SELECT id FROM round_sources WHERE round_id = :r',
                    r=round_id) == []
    campaign_id = campaign_id_of(coord_client, round_id)
    audit = coord_client.fetch(
        'coordinator: audit log',
        '/admin/campaign/%s/audit?action=import_failed' % campaign_id,
        as_user=COORD)['data']
    assert len(audit) == 1

    state = get_round(coord_client, round_id)['import_state']
    assert state['blocks_activation'] is True
    assert state['blocked_reason'] == 'import_failed'
    resp = activate(coord_client, round_id, error_code=400)
    assert 'last import failed' in error_text(resp)


def test_failure_after_inserts_rolls_back_in_worker(
        montage_app, coord_client, mock_external_apis):
    """AC3b: an error after the inserts rolls the whole import back."""
    infos = make_file_infos('wrollback', 220)
    round_id = new_round(coord_client, 'worker rollback')
    mock_category(mock_external_apis, infos)
    job = import_category(coord_client, round_id)['data']['job']

    def boom(*a, **kw):
        raise RuntimeError('fail after inserting')

    with patch.object(admin_endpoints, 'autodisqualify', boom):
        assert run_import_jobs(montage_app) == [(job['id'], 'failed')]

    assert db_query(montage_app,
                    "SELECT id FROM entries WHERE name LIKE 'wrollback%'") == []
    assert round_entry_count(montage_app, round_id) == 0
    assert db_query(montage_app,
                    'SELECT id FROM round_sources WHERE round_id = :r',
                    r=round_id) == []
    assert 'fail after inserting' in get_job(coord_client, round_id,
                                             job['id'])['error']


def test_error_text_hides_sql():
    exc = OperationalError('INSERT INTO entries VALUES (...) huge dump',
                           {'p': 1}, Exception('database is locked'))
    assert import_worker._error_text(exc) == 'Exception: database is locked'
    assert import_worker._error_text(rdb.InvalidAction('nope')) == 'nope'
    assert len(import_worker._error_text(ValueError('x' * 5000))) == \
        rdb.IMPORT_ERROR_MAX


def test_second_enqueue_rejected(montage_app, coord_client,
                                 mock_external_apis):
    """AC8: one queued/running job per round."""
    round_id = new_round(coord_client, 'second enqueue')
    import_category(coord_client, round_id)
    resp = import_category(coord_client, round_id, error_code=400)
    assert 'already queued or running' in error_text(resp)
    run_import_jobs(montage_app)
    import_category(coord_client, round_id)  # 200 again


def test_enqueue_requires_paused_round(montage_app, coord_client,
                                       mock_external_apis):
    round_id = new_round(coord_client, 'enqueue active')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    activate(coord_client, round_id)
    resp = import_category(coord_client, round_id, error_code=400)
    assert 'must be paused' in error_text(resp)


def test_activate_blocked_while_queued_and_running(
        montage_app, coord_client, mock_external_apis):
    """AC4"""
    round_id = new_round(coord_client, 'gate')
    job = import_category(coord_client, round_id)['data']['job']
    resp = activate(coord_client, round_id, error_code=400)
    assert 'still queued' in error_text(resp)

    set_job(montage_app, job['id'], status='running')
    resp = activate(coord_client, round_id, error_code=400)
    assert 'still running' in error_text(resp)
    assert get_round(coord_client, round_id)['import_state'][
        'blocked_reason'] == 'import_running'

    set_job(montage_app, job['id'], status='queued')
    run_import_jobs(montage_app)
    activate(coord_client, round_id)


def test_rerun_is_idempotent(montage_app, coord_client, mock_external_apis):
    """AC7: the same import again adds no round entries."""
    round_id = new_round(coord_client, 'rerun')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    job2 = import_category(coord_client, round_id)['data']['job']
    assert run_import_jobs(montage_app) == [(job2['id'], 'succeeded')]

    details = get_job(coord_client, round_id, job2['id'])
    assert details['new_round_entry_count'] == 0
    assert {'duplicate import': 'no new entries imported'} in \
        details['warnings']
    assert round_entry_count(montage_app, round_id) == 20


def test_selected_import_warning_is_dict(montage_app, coord_client,
                                         mock_external_apis):
    """The 'import issues' warning is a dict (was a set literal)."""
    mock_external_apis.replace(responses_lib.POST, TOOLFORGE_FILE_URL,
                               json={'file_infos': [SELECTED_FILE_INFO],
                                     'no_info': ['Missing.jpg']},
                               status=200)
    round_id = new_round(coord_client, 'selected warning')
    job = coord_client.fetch(
        'coordinator: import selected', '/admin/round/%s/import' % round_id,
        {'import_method': 'selected',
         'file_names': [SELECTED_FILE_INFO['img_name'], 'Missing.jpg']},
        as_user=COORD)['data']['job']
    assert job['params_summary'] == {'file_count': 2}
    run_import_jobs(montage_app)
    warnings = get_job(coord_client, round_id, job['id'])['warnings']
    issues = [w for w in warnings if 'import issues' in w]
    assert len(issues) == 1
    assert 'Missing.jpg' in issues[0]['import issues']


@pytest.mark.parametrize('body', [
    {'import_method': 'category'},
    {'import_method': 'category', 'category': ''},
    {'import_method': 'csv'},
    {'import_method': 'gistcsv', 'csv_url': 'https://example.org/x.csv'},
    {'import_method': 'selected', 'file_names': []},
    {'import_method': 'selected', 'file_names': 'Not_a_list.jpg'},
    {'category': 'No_method'},
])
def test_import_missing_key_is_400(montage_app, coord_client, body):
    round_id = new_round(coord_client, 'missing key')
    coord_client.fetch('coordinator: bad import',
                       '/admin/round/%s/import' % round_id, body,
                       as_user=COORD, error_code=400)
    assert db_query(montage_app, 'SELECT id FROM import_jobs') == []


# ---------------------------------------------------------------------------
# Worker internals: CAS claim, fencing, stuck-job rule, loop
# ---------------------------------------------------------------------------

def test_claim_cas_single_winner(montage_app, coord_client, engine):
    """AC5: claim_next_job's UPDATE only wins while the job is still
    queued. Another worker claims job 1 between our SELECT and our UPDATE;
    we must not take it over, and move on to job 2. (Sequential on SQLite;
    the row lock gives the same on MariaDB.)"""
    from sqlalchemy import event
    round_a = new_round(coord_client, 'cas a')
    round_b = new_round(coord_client, 'cas b')
    job_1 = seed_job(montage_app, round_a, 'queued')
    job_2 = seed_job(montage_app, round_b, 'queued')
    raced = []

    def other_worker_claims_first(conn, cursor, statement, params, context,
                                  executemany):
        if statement.lstrip().upper().startswith('UPDATE IMPORT_JOBS') \
                and not raced:
            raced.append(1)
            set_job(montage_app, job_1, status='running',
                    claim_token='other-worker')

    event.listen(engine, 'before_cursor_execute', other_worker_claims_first)
    try:
        claim = import_worker.claim_next_job(engine, 'w')
    finally:
        event.remove(engine, 'before_cursor_execute',
                     other_worker_claims_first)

    assert raced
    assert claim.id == job_2
    row_1 = db_query(montage_app, 'SELECT * FROM import_jobs WHERE id = :i',
                     i=job_1)[0]
    assert row_1['claim_token'] == 'other-worker'
    assert row_1['attempts'] == 0
    assert import_worker.claim_next_job(engine, 'w') is None


def test_claim_next_job(montage_app, coord_client, engine):
    round_id = new_round(coord_client, 'claim')
    job_id = seed_job(montage_app, round_id, 'queued')
    claim = import_worker.claim_next_job(engine, 'worker-a')
    assert claim.id == job_id
    assert claim.params == {'category': 'Seeded'}
    row = db_query(montage_app, 'SELECT * FROM import_jobs WHERE id = :i',
                   i=job_id)[0]
    assert row['status'] == 'running'
    assert row['claimed_by'] == 'worker-a'
    assert row['claim_token'] == claim.token
    assert row['attempts'] == 1
    assert row['start_date'] is not None
    assert import_worker.claim_next_job(engine, 'worker-b') is None


def test_fenced_commit_rejected_after_token_change(
        montage_app, coord_client, engine, mock_external_apis):
    """AC6b: a worker whose claim token changed cannot mark the job
    succeeded; its import is rolled back."""
    round_id = new_round(coord_client, 'fence')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')
    set_job(montage_app, job['id'], claim_token='someone-else')
    assert import_worker.process_job(engine, claim) == 'lost'
    assert round_entry_count(montage_app, round_id) == 0
    assert get_job(coord_client, round_id, job['id'])['status'] == 'running'


def job_row(app, job_id):
    return db_query(app, 'SELECT * FROM import_jobs WHERE id = :i',
                    i=job_id)[0]


def import_failed_audit(client, round_id):
    return client.fetch(
        'coordinator: audit log',
        '/admin/campaign/%s/audit?action=import_failed'
        % campaign_id_of(client, round_id), as_user=COORD)['data']


def test_stale_requeue_then_fail(montage_app, coord_client, engine):
    """AC6: a running job whose heartbeat is older than STALE_AFTER is
    requeued while attempts < MAX_ATTEMPTS, then failed; jobs with a
    fresh heartbeat (another live worker's) and queued jobs are left
    alone."""
    now = datetime.datetime(2026, 10, 1, 12, 0, 0)
    old_beat = now - import_worker.STALE_AFTER - datetime.timedelta(minutes=5)
    fresh_beat = now - datetime.timedelta(minutes=1)
    round_a = new_round(coord_client, 'stale a')
    round_b = new_round(coord_client, 'stale b')
    round_c = new_round(coord_client, 'stale c')
    stale = seed_job(montage_app, round_a, 'running', attempts=1,
                     claimed_by='dead-pod:1', claim_token='t-dead',
                     start_date=old_beat, heartbeat_date=old_beat)
    alive = seed_job(montage_app, round_b, 'running', attempts=1,
                     claimed_by='live-pod:1', claim_token='t-live',
                     start_date=old_beat, heartbeat_date=fresh_beat)
    queued = seed_job(montage_app, round_c, 'queued')

    assert import_worker.recover_stale_jobs(engine, now=now) == ([stale], [])
    row = job_row(montage_app, stale)
    assert row['status'] == 'queued'
    assert row['attempts'] == 1
    assert (row['claimed_by'], row['claim_token'], row['start_date'],
            row['heartbeat_date']) == (None, None, None, None)
    assert job_row(montage_app, alive)['status'] == 'running'
    assert job_row(montage_app, alive)['claim_token'] == 't-live'
    assert job_row(montage_app, queued)['status'] == 'queued'

    # second attempt dies too: claimed again (attempts 2), heartbeat stops
    claim = import_worker.claim_next_job(engine, 'w2')
    assert claim.id == stale
    set_job(montage_app, stale, heartbeat_date=old_beat)
    assert import_worker.recover_stale_jobs(engine, now=now) == ([], [stale])
    details = get_job(coord_client, round_a, stale)
    assert details['status'] == 'failed'
    assert details['error'] == import_worker.STALE_ERROR % 2
    assert 'stopped responding' in details['error']
    assert len(import_failed_audit(coord_client, round_a)) == 1
    assert job_row(montage_app, alive)['status'] == 'running'
    # nothing left to do
    assert import_worker.recover_stale_jobs(engine, now=now) == ([], [])


def test_stale_job_is_rerun_after_requeue(montage_app, coord_client, engine,
                                          mock_external_apis):
    """A worker killed mid-import (no release, no heartbeat) leaves a
    running job; once stale it is requeued and the next run imports it."""
    round_id = new_round(coord_client, 'rerun stale')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'killed-worker')
    long_ago = claim.start_date - import_worker.STALE_AFTER * 2
    set_job(montage_app, claim.id, heartbeat_date=long_ago)
    assert run_import_jobs(montage_app) == [(job['id'], 'succeeded')]
    assert job_row(montage_app, job['id'])['attempts'] == 2
    assert round_entry_count(montage_app, round_id) == 20


def test_worker_loop_survives_db_error(montage_app, coord_client, engine,
                                       mock_external_apis):
    round_id = new_round(coord_client, 'loop')
    job = import_category(coord_client, round_id)['data']['job']
    calls = []
    real_claim = import_worker.claim_next_job

    def flaky_claim(*a, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError('SELECT 1', {}, Exception('gone away'))
        return real_claim(*a, **kw)

    with patch.object(import_worker, 'claim_next_job', flaky_claim):
        assert import_worker.run_loop_iteration(engine, 'w') is False
        assert import_worker.run_loop_iteration(engine, 'w') is True
    assert get_job(coord_client, round_id, job['id'])['status'] == 'succeeded'


# ---------------------------------------------------------------------------
# Gate and import_state with seeded rows
# ---------------------------------------------------------------------------

def test_failed_job_on_round_with_entries_reports_import_failed(
        montage_app, coord_client, mock_external_apis):
    round_id = new_round(coord_client, 'failed with entries')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    job_id = seed_job(montage_app, round_id, 'failed', error='seeded')
    resp = activate(coord_client, round_id, error_code=400)
    assert 'failed (job #%s)' % job_id in error_text(resp)


def test_older_active_job_blocks_behind_newer_success(
        montage_app, coord_client, mock_external_apis):
    round_id = new_round(coord_client, 'any active')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    queued = seed_job(montage_app, round_id, 'queued')
    seed_job(montage_app, round_id, 'succeeded')  # newer, latest
    state = get_round(coord_client, round_id)['import_state']
    assert state['blocked_reason'] == 'import_queued'
    assert state['job']['id'] == queued
    activate(coord_client, round_id, error_code=400)


def test_failed_job_does_not_decorate_active_round(
        montage_app, coord_client, mock_external_apis):
    round_id = new_round(coord_client, 'active round')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    activate(coord_client, round_id)
    seed_job(montage_app, round_id, 'failed', error='seeded')
    state = get_round(coord_client, round_id)['import_state']
    assert state['status'] == 'failed'
    assert state['blocks_activation'] is False
    assert state['blocked_reason'] is None


def test_job_from_other_round_is_404(montage_app, coord_client):
    round_a = new_round(coord_client, 'other a')
    round_b = new_round(coord_client, 'other b')
    job_id = seed_job(montage_app, round_a, 'queued')
    get_job(coord_client, round_b, job_id, error_code=404)


def test_import_state_in_admin_payloads(montage_app, coord_client):
    round_id = new_round(coord_client, 'payloads')
    campaign_id = campaign_id_of(coord_client, round_id)
    keys = {'status', 'blocks_activation', 'blocked_reason', 'job'}

    state = get_round(coord_client, round_id)['import_state']
    assert set(state) == keys
    assert state['status'] == 'none' and state['job'] is None

    job_id = seed_job(montage_app, round_id, 'queued')
    campaign = coord_client.fetch('coordinator: campaign',
                                  '/admin/campaign/%s' % campaign_id,
                                  as_user=COORD)['data']
    rnd = [r for r in campaign['rounds'] if r['id'] == round_id][0]
    assert set(rnd['import_state']) == keys
    assert rnd['import_state']['job']['id'] == job_id
    assert rnd['import_state']['blocked_reason'] == 'import_queued'

    for url in ('/admin', '/admin/campaigns/all'):
        campaigns = coord_client.fetch('coordinator: index', url,
                                       as_user=COORD)['data']
        mine = [c for c in campaigns if c['id'] == campaign_id][0]
        rnd = [r for r in mine['rounds'] if r['id'] == round_id][0]
        assert rnd['import_state']['status'] == 'queued'


def test_import_state_in_active_round_payload(montage_app, coord_client,
                                              mock_external_apis):
    round_id = new_round(coord_client, 'active payload')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    activate(coord_client, round_id)
    campaign = coord_client.fetch(
        'coordinator: campaign',
        '/admin/campaign/%s' % campaign_id_of(coord_client, round_id),
        as_user=COORD)['data']
    assert campaign['active_round']['import_state']['status'] == 'succeeded'


def test_import_state_not_in_juror_payload(montage_app, coord_client,
                                           mock_external_apis):
    round_id = new_round(coord_client, 'juror payload')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    activate(coord_client, round_id)
    campaign_id = campaign_id_of(coord_client, round_id)
    data = coord_client.fetch('juror: campaign',
                              '/juror/campaign/%s' % campaign_id,
                              as_user='Slaporte')['data']
    for rnd in data['rounds']:
        assert 'import_state' not in rnd
    assert data['active_round'] is not None
    assert 'import_state' not in data['active_round']


# ---------------------------------------------------------------------------
# Sync rollback mode
# ---------------------------------------------------------------------------

@pytest.fixture
def sync_mode(montage_app):
    montage_app.resources['config']['import_mode'] = 'sync'


def test_sync_import_records_succeeded_job(montage_app, coord_client,
                                           mock_external_apis, sync_mode):
    round_id = new_round(coord_client, 'sync job')
    data = import_category(coord_client, round_id)['data']
    assert data['new_round_entry_count'] == 20
    assert data['entry_count'] == 20
    assert 'warnings' in data and 'disqualified' in data
    assert data['job']['status'] == 'succeeded'
    assert data['job']['new_round_entry_count'] == 20
    jobs = coord_client.fetch('coordinator: list import jobs',
                              '/admin/round/%s/imports' % round_id,
                              as_user=COORD)['data']
    assert [j['id'] for j in jobs] == [data['job']['id']]
    activate(coord_client, round_id)


def test_failed_sync_import_leaves_no_job(montage_app, coord_client,
                                          mock_external_apis, sync_mode):
    round_id = new_round(coord_client, 'sync fail')

    def boom(*a, **kw):
        raise RuntimeError('fail after inserting')

    mock_category(mock_external_apis, make_file_infos('syncfail', 30))
    with patch.object(admin_endpoints, 'autodisqualify', boom):
        import_category(coord_client, round_id, error_code=500)
    assert db_query(montage_app,
                    'SELECT id FROM import_jobs WHERE round_id = :r',
                    r=round_id) == []
    assert db_query(montage_app,
                    "SELECT id FROM entries WHERE name LIKE 'syncfail%'") == []
    assert round_entry_count(montage_app, round_id) == 0
    assert db_query(montage_app,
                    'SELECT id FROM round_sources WHERE round_id = :r',
                    r=round_id) == []


def test_sync_import_refused_while_job_queued(montage_app, coord_client,
                                              mock_external_apis):
    round_id = new_round(coord_client, 'sync refused')
    import_category(coord_client, round_id)  # worker mode: queued
    montage_app.resources['config']['import_mode'] = 'sync'
    resp = import_category(coord_client, round_id, error_code=400)
    assert 'already queued or running' in error_text(resp)
    assert round_entry_count(montage_app, round_id) == 0


def test_get_import_mode_validates():
    from montage.utils import get_import_mode
    assert get_import_mode({}) == 'sync'
    assert get_import_mode({'import_mode': 'worker'}) == 'worker'
    with pytest.raises(ValueError):
        get_import_mode({'import_mode': 'wroker'})


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_schema_check_reports_missing_import_jobs(tmpdir):
    """AC11: the startup schema check names a missing import_jobs table."""
    from montage.check_rdb import get_schema_errors
    eng = create_engine('sqlite:///%s/schema.db' % tmpdir)
    try:
        rdb.Base.metadata.create_all(eng)
        session = sessionmaker(bind=eng)()
        assert get_schema_errors(rdb.Base, session) == []
        session.close()
        rdb.import_jobs_t.drop(eng)
        session = sessionmaker(bind=eng)()
        errors = get_schema_errors(rdb.Base, session)
        session.close()
        assert len(errors) == 1 and 'import_jobs' in errors[0]
    finally:
        eng.dispose()


def test_long_json_column_roundtrip(montage_app, coord_client):
    from sqlalchemy.dialects import mysql
    from sqlalchemy.schema import CreateTable
    ddl = str(CreateTable(rdb.import_jobs_t).compile(dialect=mysql.dialect()))
    for col in ('params', 'warnings', 'flags'):
        assert '%s MEDIUMTEXT' % col in ddl
    assert 'error TEXT' in ddl
    assert 'TIMESTAMP' not in ddl

    round_id = new_round(coord_client, 'long json')
    names = ['File_%06d_%s.jpg' % (i, 'x' * 60) for i in range(1000)]
    job_id = seed_job(montage_app, round_id, 'queued')
    eng = create_engine(montage_app.resources['config']['db_url'])
    session = sessionmaker(bind=eng)()
    try:
        job = session.query(ImportJob).get(job_id)
        job.params = {'file_names': names}
        session.commit()
        session.expire_all()
        assert session.query(ImportJob).get(job_id).params == {
            'file_names': names}
    finally:
        session.close()
        eng.dispose()
    assert len(''.join(names)) > 70000


def test_round_sources_params_is_long_text():
    """round_sources.params is MEDIUMTEXT on MySQL, matching
    tools/migrate_round_sources_params.sql; dq_params stays TEXT."""
    import os
    from sqlalchemy.dialects import mysql
    from sqlalchemy.schema import CreateTable
    ddl = str(CreateTable(rdb.RoundSource.__table__).compile(
        dialect=mysql.dialect()))
    assert 'params MEDIUMTEXT' in ddl
    assert 'dq_params TEXT' in ddl
    tools = os.path.join(os.path.dirname(rdb.__file__), '..', 'tools')
    with open(os.path.join(tools, 'migrate_round_sources_params.sql')) as f:
        assert 'MODIFY params MEDIUMTEXT' in f.read()
    with open(os.path.join(tools, 'revert_round_sources_params.sql')) as f:
        assert 'MODIFY params TEXT' in f.read()


# ---------------------------------------------------------------------------
# PR check follow-ups: sweeps, fenced failure, timeouts, sync lock order
# ---------------------------------------------------------------------------

def test_main_has_no_startup_sweep_and_exits_on_shutdown(
        montage_app, coord_client, monkeypatch):
    """Multi-replica safety: a starting worker leaves other workers' running
    jobs (fresh heartbeat) alone, and main() returns 0 once a shutdown is
    requested."""
    round_id = new_round(coord_client, 'second replica')
    now = import_worker._utcnow()
    other = seed_job(montage_app, round_id, 'running', attempts=1,
                     claim_token='other-replica', start_date=now,
                     heartbeat_date=now)
    config = dict(montage_app.resources['config'])
    monkeypatch.setattr(import_worker, 'load_env_config', lambda: config)
    monkeypatch.setattr(import_worker, 'install_signal_handlers',
                        lambda: None)
    real_iteration = import_worker.run_loop_iteration
    iterations = []

    def one_iteration_then_sigterm(*a, **kw):
        iterations.append(real_iteration(*a, **kw))
        # what the SIGTERM handler does outside a job: only set the flag
        import_worker._on_shutdown_signal(15, None)
        return iterations[-1]

    monkeypatch.setattr(import_worker, 'run_loop_iteration',
                        one_iteration_then_sigterm)
    assert import_worker.main(['--poll-interval', '0']) == 0
    assert iterations == [False]
    row = job_row(montage_app, other)
    assert (row['status'], row['claim_token']) == ('running',
                                                   'other-replica')


def test_loop_iteration_recovers_stale_jobs(montage_app, coord_client,
                                            engine):
    """Every loop iteration runs stale recovery."""
    round_id = new_round(coord_client, 'loop recovery')
    long_ago = import_worker._utcnow() - datetime.timedelta(minutes=30)
    old = seed_job(montage_app, round_id, 'running', attempts=2,
                   claim_token='t', start_date=long_ago,
                   heartbeat_date=long_ago)
    assert import_worker.run_loop_iteration(engine, 'w') is False
    details = get_job(coord_client, round_id, old)
    assert details['status'] == 'failed'
    assert details['error'] == import_worker.STALE_ERROR % 2


def test_failure_after_recovery_is_fenced(montage_app, coord_client, engine,
                                          mock_external_apis):
    """M7: once stale recovery failed the job (claim token cleared), the
    worker's own failure must not overwrite it or log a second
    import_failed."""
    round_id = new_round(coord_client, 'fenced failure')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')
    long_ago = claim.start_date - datetime.timedelta(minutes=30)
    set_job(montage_app, job['id'], attempts=2, heartbeat_date=long_ago)
    assert import_worker.recover_stale_jobs(engine) == ([], [job['id']])

    def boom(*a, **kw):
        raise RuntimeError('late failure')

    with patch.object(import_worker, 'load_import_entries', boom):
        assert import_worker.process_job(engine, claim) == 'failed'
    details = get_job(coord_client, round_id, job['id'])
    assert details['error'] == import_worker.STALE_ERROR % 2
    assert len(import_failed_audit(coord_client, round_id)) == 1


def test_failed_rollback_still_marks_job_failed(montage_app, coord_client,
                                                engine, mock_external_apis):
    round_id = new_round(coord_client, 'rollback raises')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')
    from sqlalchemy.orm import Session

    real_rollback = Session.rollback
    raised = []

    def broken_rollback(self):
        # the import session's rollback raises, as on a dead connection
        # (whose transaction the server rolls back anyway)
        real_rollback(self)
        if not raised:
            raised.append(1)
            raise OperationalError('ROLLBACK', {},
                                   Exception('connection lost'))

    def boom(*a, **kw):
        raise RuntimeError('import broke')

    with patch.object(admin_endpoints, 'autodisqualify', boom), \
            patch.object(Session, 'rollback', broken_rollback):
        assert import_worker.process_job(engine, claim) == 'failed'
    assert raised
    details = get_job(coord_client, round_id, job['id'])
    assert details['status'] == 'failed'
    assert 'import broke' in details['error']


def test_hung_fetch_times_out_and_worker_moves_on(montage_app, coord_client,
                                                  mock_external_apis):
    """A fetch that times out fails its job with a readable reason; the
    next job still runs."""
    import requests
    from montage.tests.conftest import GSHEET_CSV_URL_RE
    mock_external_apis.replace(
        responses_lib.GET, GSHEET_CSV_URL_RE,
        body=requests.exceptions.ReadTimeout('Read timed out.'))
    round_a = new_round(coord_client, 'hung csv')
    round_b = new_round(coord_client, 'after hung csv')
    job_a = coord_client.fetch(
        'coordinator: import csv', '/admin/round/%s/import' % round_a,
        {'import_method': 'csv',
         'csv_url': 'https://docs.google.com/spreadsheets/d/x/edit'},
        as_user=COORD)['data']['job']
    job_b = import_category(coord_client, round_b)['data']['job']
    assert run_import_jobs(montage_app) == [(job_a['id'], 'failed'),
                                            (job_b['id'], 'succeeded')]
    error = get_job(coord_client, round_a, job_a['id'])['error']
    assert error.startswith('timed out while fetching the files to import')


def test_http_helpers_default_timeout():
    from montage import utils
    with patch.object(utils.requests, 'get') as get, \
            patch.object(utils.requests, 'post') as post:
        utils.requests_get('https://example.org/a')
        utils.requests_post('https://example.org/b', data={})
        utils.requests_get('https://example.org/c', timeout=3)
    assert get.call_args_list[0][1]['timeout'] == utils.DEFAULT_HTTP_TIMEOUT
    assert post.call_args_list[0][1]['timeout'] == utils.DEFAULT_HTTP_TIMEOUT
    assert get.call_args_list[1][1]['timeout'] == 3


def test_wikireplica_connection_has_timeouts():
    from montage import labs

    class FakeCursor(object):
        def execute(self, query, params):
            pass

        def fetchall(self):
            return [{'img_name': b'A.jpg'}]

    class FakeConnection(object):
        def cursor(self, cursor_type):
            return FakeCursor()

    with patch.object(labs.pymysql, 'connect',
                      return_value=FakeConnection()) as connect, \
         patch.object(labs, 'replica_credentials',
                      return_value={'read_default_file': '/x/replica.my.cnf'}):
        assert labs.fetchall_from_commonswiki('SELECT 1', ()) == [
            {'img_name': 'A.jpg'}]
    kw = connect.call_args[1]
    assert kw['read_default_file'] == '/x/replica.my.cnf'
    assert kw['connect_timeout'] == labs.CONNECT_TIMEOUT
    assert kw['read_timeout'] == labs.READ_TIMEOUT >= 30 * 60
    assert kw['write_timeout'] == labs.WRITE_TIMEOUT


def test_error_text_for_fetch_failures():
    import pymysql
    import requests
    assert import_worker._error_text(
        requests.exceptions.ConnectTimeout('x')).startswith('timed out')
    assert import_worker._error_text(
        requests.exceptions.ConnectionError('x')).startswith(
            'could not fetch')
    assert import_worker._error_text(
        pymysql.err.OperationalError(2013, 'Lost connection')).startswith(
            'the Commons database query failed or timed out')


def test_sync_import_takes_no_lock_before_fetch(montage_app, coord_client,
                                                mock_external_apis,
                                                sync_mode):
    """Blocker from the PR check: in sync mode the request must not hold a
    round lock / locking read on import_jobs across the fetch."""
    from sqlalchemy.orm import Query
    events = []
    real_wfu = Query.with_for_update
    real_load = rdb.load_import_entries

    def recording_wfu(self, *a, **kw):
        events.append('lock')
        return real_wfu(self, *a, **kw)

    def recording_load(*a, **kw):
        ret = real_load(*a, **kw)
        events.append('fetched')
        return ret

    round_id = new_round(coord_client, 'sync locks')
    with patch.object(Query, 'with_for_update', recording_wfu), \
            patch.object(rdb, 'load_import_entries', recording_load):
        import_category(coord_client, round_id)
    assert 'fetched' in events
    assert 'lock' not in events[:events.index('fetched')]


# ---------------------------------------------------------------------------
# Phase 2: heartbeat, shutdown release, skipped jobs, lock errors
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_worker_shutdown():
    import_worker._shutdown.update(requested=False, interruptible=False)
    yield
    import_worker._shutdown.update(requested=False, interruptible=False)


def test_heartbeat_updates_and_max_runtime(montage_app, coord_client, engine,
                                           mock_external_apis):
    """A tick refreshes heartbeat_date (fenced); after MAX_RUNTIME it fails
    the job instead, and the worker's later commit is rejected."""
    round_id = new_round(coord_client, 'heartbeat')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')
    later = claim.start_date + datetime.timedelta(minutes=10)
    assert import_worker.heartbeat_tick(engine, claim, now=later) == 'ok'
    assert job_row(montage_app, job['id'])['heartbeat_date'] is not None
    assert get_job(coord_client, round_id, job['id'])['heartbeat_date'] == \
        later.isoformat()

    # a fresh heartbeat keeps stale recovery away
    assert import_worker.recover_stale_jobs(
        engine, now=later + datetime.timedelta(minutes=1)) == ([], [])

    # fenced: another token's tick changes nothing
    other = claim._replace(token='not-ours')
    assert import_worker.heartbeat_tick(
        engine, other, now=later + datetime.timedelta(minutes=1)) == 'lost'
    assert get_job(coord_client, round_id, job['id'])['heartbeat_date'] == \
        later.isoformat()

    too_late = claim.start_date + import_worker.MAX_RUNTIME \
        + datetime.timedelta(seconds=1)
    assert import_worker.heartbeat_tick(engine, claim, now=too_late) == \
        'expired'
    details = get_job(coord_client, round_id, job['id'])
    assert details['status'] == 'failed'
    assert details['error'] == import_worker.MAX_RUNTIME_ERROR
    assert len(import_failed_audit(coord_client, round_id)) == 1
    assert import_worker.heartbeat_tick(engine, claim, now=too_late) == 'lost'

    # the (slow) worker finishes afterwards: its commit is fenced off
    assert import_worker.process_job(engine, claim) == 'lost'
    assert round_entry_count(montage_app, round_id) == 0
    assert get_job(coord_client, round_id, job['id'])['status'] == 'failed'


def test_heartbeat_thread_runs_and_stops_before_final_update(
        montage_app, coord_client, engine, mock_external_apis):
    """process_job keeps the job's heartbeat fresh while it fetches, and
    stops and joins the heartbeat thread before the fenced success
    UPDATE."""
    import threading
    import time as time_mod
    from sqlalchemy import event
    round_id = new_round(coord_client, 'heartbeat thread')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')
    events = []
    real_tick = import_worker.heartbeat_tick
    real_load = import_worker.load_import_entries
    real_stop = import_worker.Heartbeat.stop

    def recording_tick(*a, **kw):
        events.append('tick')
        return real_tick(*a, **kw)

    def slow_load(*a, **kw):
        time_mod.sleep(0.5)
        return real_load(*a, **kw)

    def recording_stop(self):
        events.append('stop')
        return real_stop(self)

    def on_execute(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith('UPDATE IMPORT_JOBS') \
                and 'succeeded' in repr(params):
            events.append('final update')

    event.listen(engine, 'before_cursor_execute', on_execute)
    try:
        with patch.object(import_worker, 'heartbeat_tick', recording_tick), \
                patch.object(import_worker, 'load_import_entries',
                             slow_load), \
                patch.object(import_worker.Heartbeat, 'stop',
                             recording_stop):
            assert import_worker.process_job(
                engine, claim, heartbeat_interval=0.05) == 'succeeded'
    finally:
        event.remove(engine, 'before_cursor_execute', on_execute)

    assert 'tick' in events
    final = events.index('final update')
    assert 'stop' in events[:final]
    assert 'tick' not in events[final:]
    assert not [t for t in threading.enumerate()
                if t.name == 'heartbeat-job-%s' % job['id']]
    assert round_entry_count(montage_app, round_id) == 20


def test_release_job_does_not_use_an_attempt(montage_app, coord_client,
                                             engine):
    round_id = new_round(coord_client, 'release')
    job_id = seed_job(montage_app, round_id, 'queued', attempts=0)
    claim = import_worker.claim_next_job(engine, 'w')
    assert job_row(montage_app, job_id)['attempts'] == 1
    assert import_worker.release_job(engine, claim) is True
    row = job_row(montage_app, job_id)
    assert row['status'] == 'queued'
    assert row['attempts'] == 0
    assert (row['claimed_by'], row['claim_token'], row['start_date'],
            row['heartbeat_date']) == (None, None, None, None)
    # fenced: a second release (token gone) does nothing
    assert import_worker.release_job(engine, claim) is False
    assert job_row(montage_app, job_id)['attempts'] == 0


def test_sigterm_during_fetch_releases_job(montage_app, coord_client, engine,
                                           mock_external_apis):
    """A real SIGTERM while the worker fetches: the handler interrupts it,
    the job goes back to 'queued' with its attempt returned, and the next
    run imports it."""
    import os
    import signal
    import time as time_mod
    round_id = new_round(coord_client, 'sigterm fetch')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')

    def fetch_then_get_killed(*a, **kw):
        os.kill(os.getpid(), signal.SIGTERM)
        time_mod.sleep(10)  # interrupted by the handler

    old_term = signal.getsignal(signal.SIGTERM)
    old_int = signal.getsignal(signal.SIGINT)
    started = time_mod.monotonic()
    try:
        import_worker.install_signal_handlers()
        with patch.object(import_worker, 'load_import_entries',
                          fetch_then_get_killed), \
                pytest.raises(import_worker.WorkerShutdown):
            import_worker.process_job(engine, claim, heartbeat_interval=0.05)
    finally:
        signal.signal(signal.SIGTERM, old_term)
        signal.signal(signal.SIGINT, old_int)
    assert time_mod.monotonic() - started < 5

    row = job_row(montage_app, job['id'])
    assert (row['status'], row['attempts'], row['claim_token']) == (
        'queued', 0, None)
    assert import_failed_audit(coord_client, round_id) == []

    import_worker._shutdown.update(requested=False)  # a new worker
    assert run_import_jobs(montage_app) == [(job['id'], 'succeeded')]
    assert job_row(montage_app, job['id'])['attempts'] == 1


def test_shutdown_during_import_rolls_back_and_releases(
        montage_app, coord_client, engine, mock_external_apis):
    """Interrupted after the inserts: nothing of the import is committed
    and the job is released, not failed."""
    round_id = new_round(coord_client, 'shutdown import')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')

    def interrupted(*a, **kw):
        import_worker._on_shutdown_signal(15, None)
        raise AssertionError('handler should have raised')

    with patch.object(admin_endpoints, 'autodisqualify', interrupted), \
            pytest.raises(import_worker.WorkerShutdown):
        import_worker.process_job(engine, claim)
    assert job_row(montage_app, job['id'])['status'] == 'queued'
    assert job_row(montage_app, job['id'])['attempts'] == 0
    assert round_entry_count(montage_app, round_id) == 0
    assert db_query(montage_app,
                    'SELECT id FROM round_sources WHERE round_id = :r',
                    r=round_id) == []


def test_error_during_shutdown_releases_instead_of_failing(
        montage_app, coord_client, engine, mock_external_apis):
    """If the interrupt surfaces as another exception (e.g. a rollback on
    the interrupted connection failing), the job is still released."""
    round_id = new_round(coord_client, 'shutdown side effect')
    job = import_category(coord_client, round_id)['data']['job']
    claim = import_worker.claim_next_job(engine, 'w')

    def broken(*a, **kw):
        import_worker._shutdown['requested'] = True
        raise RuntimeError('connection in a bad state')

    with patch.object(import_worker, 'load_import_entries', broken), \
            pytest.raises(import_worker.WorkerShutdown):
        import_worker.process_job(engine, claim)
    assert job_row(montage_app, job['id'])['status'] == 'queued'
    assert import_failed_audit(coord_client, round_id) == []


def test_shutdown_signal_raises_only_when_interruptible():
    import_worker._on_shutdown_signal(15, None)  # between jobs: flag only
    assert import_worker._shutdown['requested'] is True
    with pytest.raises(import_worker.WorkerShutdown):
        with import_worker._interruptible():  # already requested
            pass
    import_worker._shutdown['requested'] = False
    with pytest.raises(import_worker.WorkerShutdown):
        with import_worker._interruptible():
            import_worker._on_shutdown_signal(15, None)
    assert import_worker._shutdown['interruptible'] is False


def test_cancelled_rounds_queued_job_skipped_without_fetch(
        montage_app, coord_client, mock_external_apis):
    round_id = new_round(coord_client, 'cancelled before import')
    job = import_category(coord_client, round_id)['data']['job']
    coord_client.fetch('coordinator: cancel round',
                       '/admin/round/%s/cancel' % round_id, {'post': True},
                       as_user=COORD)
    calls_before = len(mock_external_apis.calls)
    assert run_import_jobs(montage_app) == [(job['id'], 'failed')]
    assert len(mock_external_apis.calls) == calls_before
    details = get_job(coord_client, round_id, job['id'])
    assert details['error'] == 'import skipped: the round is cancelled, not' \
        ' paused'
    # a cancelled round is not blocked or badged by it
    assert get_round(coord_client, round_id)['import_state'][
        'blocks_activation'] is False


def mysql_lock_error(code=1213):
    import pymysql
    msg = {1205: 'Lock wait timeout exceeded; try restarting transaction',
           1213: 'Deadlock found when trying to get lock; try restarting'
                 ' transaction'}[code]
    return OperationalError('SELECT ...', {},
                            pymysql.err.OperationalError(code, msg))


def test_worker_loop_logs_lock_error_and_continues(
        montage_app, coord_client, engine, mock_external_apis, caplog):
    round_id = new_round(coord_client, 'worker deadlock')
    job = import_category(coord_client, round_id)['data']['job']
    calls = []
    real_claim = import_worker.claim_next_job

    def deadlocked_once(*a, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise mysql_lock_error(1213)
        return real_claim(*a, **kw)

    with patch.object(import_worker, 'claim_next_job', deadlocked_once):
        assert import_worker.run_loop_iteration(engine, 'w') is False
        assert 'database busy' in caplog.text
        assert import_worker.run_loop_iteration(engine, 'w') is True
    assert get_job(coord_client, round_id, job['id'])['status'] == 'succeeded'


def test_error_text_for_lock_errors():
    for code in (1205, 1213):
        text = import_worker._error_text(mysql_lock_error(code))
        assert text.startswith(import_worker.LOCK_ERROR)
        assert 'SELECT' not in text
    assert not rdb.is_lock_error(OperationalError(
        'SELECT 1', {}, Exception('gone away')))
    assert not rdb.is_lock_error(RuntimeError('1213'))


# ---------------------------------------------------------------------------
# Phase 2: Retry and Dismiss
# ---------------------------------------------------------------------------

def retry(client, round_id, job_id, **kw):
    return client.fetch('coordinator: retry import',
                        '/admin/round/%s/import/%s/retry' % (round_id, job_id),
                        {'post': True}, as_user=COORD, **kw)


def dismiss(client, round_id, job_id, **kw):
    return client.fetch('coordinator: dismiss import',
                        '/admin/round/%s/import/%s/dismiss'
                        % (round_id, job_id),
                        {'post': True}, as_user=COORD, **kw)


def failed_category_job(app, client, round_id):
    job = import_category(client, round_id)['data']['job']

    def boom(*a, **kw):
        raise RuntimeError('boom')

    with patch.object(import_worker, 'load_import_entries', boom):
        assert run_import_jobs(app) == [(job['id'], 'failed')]
    return job


def test_dismiss_failed_import_unblocks_gate(montage_app, coord_client,
                                             mock_external_apis):
    """A dismissed failed import no longer blocks activation; the round
    keeps the entries an earlier import added."""
    round_id = new_round(coord_client, 'dismiss')
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    job = failed_category_job(montage_app, coord_client, round_id)
    activate(coord_client, round_id, error_code=400)

    data = dismiss(coord_client, round_id, job['id'])['data']
    assert data['job']['id'] == job['id']
    assert data['job']['dismissed'] is True
    assert data['import_state']['status'] == 'failed'
    assert data['import_state']['blocks_activation'] is False
    state = get_round(coord_client, round_id)['import_state']
    assert state['blocks_activation'] is False
    assert state['job']['dismissed'] is True
    audit = coord_client.fetch(
        'coordinator: audit log',
        '/admin/campaign/%s/audit?action=dismiss_import'
        % campaign_id_of(coord_client, round_id), as_user=COORD)['data']
    assert len(audit) == 1

    activate(coord_client, round_id)


def test_dismiss_on_empty_round_still_cannot_activate(
        montage_app, coord_client, mock_external_apis):
    """AC3 [P2]: dismissing does not make an empty round activatable."""
    round_id = new_round(coord_client, 'dismiss empty')
    job = failed_category_job(montage_app, coord_client, round_id)
    dismiss(coord_client, round_id, job['id'])
    resp = activate(coord_client, round_id, error_code=400)
    assert 'empty round' in error_text(resp)


def test_dismiss_refused_unless_failed_and_undismissed(
        montage_app, coord_client, mock_external_apis):
    round_id = new_round(coord_client, 'dismiss refused')
    queued = seed_job(montage_app, round_id, 'queued')
    resp = dismiss(coord_client, round_id, queued, error_code=400)
    assert 'only a failed import can be dismissed' in error_text(resp)
    failed = seed_job(montage_app, round_id, 'failed', error='seeded')
    dismiss(coord_client, round_id, failed)
    resp = dismiss(coord_client, round_id, failed, error_code=400)
    assert 'already dismissed' in error_text(resp)
    other_round = new_round(coord_client, 'dismiss other')
    dismiss(coord_client, other_round, failed, error_code=404)


def test_retry_failed_import_enqueues_same_import(montage_app, coord_client,
                                                  mock_external_apis):
    round_id = new_round(coord_client, 'retry')
    job = failed_category_job(montage_app, coord_client, round_id)
    resp = activate(coord_client, round_id, error_code=400)
    assert 'Retry the import' in error_text(resp)

    data = retry(coord_client, round_id, job['id'])['data']
    new_job = data['job']
    assert new_job['id'] != job['id']
    assert new_job['status'] == 'queued'
    assert new_job['method'] == 'category'
    assert new_job['params_summary'] == job['params_summary']
    details = get_job(coord_client, round_id, new_job['id'])
    assert details['params'] == {'category': 'Synthetic_test_category'}
    assert details['retry_of'] == job['id']
    assert 'claimed_by' not in details

    # a second retry while the first one is queued is refused
    retry(coord_client, round_id, job['id'], error_code=400)

    assert run_import_jobs(montage_app) == [(new_job['id'], 'succeeded')]
    assert round_entry_count(montage_app, round_id) == 20
    assert get_job(coord_client, round_id, job['id'])['status'] == 'failed'
    state = get_round(coord_client, round_id)['import_state']
    assert state['job']['id'] == new_job['id']
    assert state['blocks_activation'] is False
    activate(coord_client, round_id)


def test_retry_refused_unless_failed(montage_app, coord_client,
                                     mock_external_apis):
    round_id = new_round(coord_client, 'retry refused')
    job = import_category(coord_client, round_id)['data']['job']
    resp = retry(coord_client, round_id, job['id'], error_code=400)
    assert 'only a failed import can be retried' in error_text(resp)
    retry(coord_client, round_id, 999999, error_code=404)


def test_retry_in_sync_mode_runs_in_request(montage_app, coord_client,
                                            mock_external_apis):
    round_id = new_round(coord_client, 'retry sync')
    job = failed_category_job(montage_app, coord_client, round_id)
    montage_app.resources['config']['import_mode'] = 'sync'
    try:
        data = retry(coord_client, round_id, job['id'])['data']
    finally:
        montage_app.resources['config']['import_mode'] = 'worker'
    assert data['new_round_entry_count'] == 20
    assert data['job']['status'] == 'succeeded'
    assert get_job(coord_client, round_id,
                   data['job']['id'])['retry_of'] == job['id']


# ---------------------------------------------------------------------------
# Phase 2: MySQL lock errors (1205 / 1213) -> retryable 400
# ---------------------------------------------------------------------------

def raise_lock_error(code):
    def raiser(*a, **kw):
        raise mysql_lock_error(code)
    return raiser


@pytest.mark.parametrize('code', [1205, 1213])
def test_enqueue_lock_error_is_busy_400(montage_app, coord_client,
                                        mock_external_apis, code):
    round_id = new_round(coord_client, 'enqueue lock %s' % code)
    with patch.object(rdb.CoordinatorDAO, '_lock_round',
                      raise_lock_error(code)):
        resp = import_category(coord_client, round_id, error_code=400)
    assert 'the server is busy, please retry' in error_text(resp)
    assert 'queue the import' in error_text(resp)
    assert db_query(montage_app, 'SELECT id FROM import_jobs'
                    ' WHERE round_id = :r', r=round_id) == []
    # nothing left behind: the retry works
    assert import_category(coord_client, round_id)['data']['job'][
        'status'] == 'queued'


@pytest.mark.parametrize('code', [1205, 1213])
def test_activate_lock_error_is_busy_400(montage_app, coord_client,
                                         mock_external_apis, code):
    round_id = new_round(coord_client, 'activate lock %s' % code)
    import_category(coord_client, round_id)
    run_import_jobs(montage_app)
    # during the locked re-check
    with patch.object(rdb.CoordinatorDAO, '_get_active_import_job_locked',
                      raise_lock_error(code)):
        resp = activate(coord_client, round_id, error_code=400)
    assert 'the server is busy, please retry' in error_text(resp)
    # during task creation, after the round row was changed in memory
    with patch.object(rdb, 'create_initial_tasks', raise_lock_error(code)):
        resp = activate(coord_client, round_id, error_code=400)
    assert 'activate the round' in error_text(resp)
    assert get_round(coord_client, round_id)['status'] == 'paused'
    activate(coord_client, round_id)
    assert get_round(coord_client, round_id)['status'] == 'active'


def test_other_operational_errors_still_500(montage_app, coord_client):
    round_id = new_round(coord_client, 'enqueue gone away')

    def gone_away(*a, **kw):
        raise OperationalError('SELECT 1', {}, Exception(2006, 'gone away'))

    with patch.object(rdb.CoordinatorDAO, '_lock_round', gone_away):
        import_category(coord_client, round_id, error_code=500)
