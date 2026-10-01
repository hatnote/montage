# -*- coding: utf-8 -*-
"""Background import worker (hatnote/montage#621, origin #618).

Runs the imports queued by ``POST /admin/round/<id>/import`` (see
``CoordinatorDAO.enqueue_import``), outside any web request. On Toolforge
it is a continuous job (Procfile entry ``import-worker``); locally
``./dev-servers.sh`` runs it, or ``python -m montage.import_worker --once``.

For each job:

1. claim it with a compare-and-set UPDATE (``status='queued'`` ->
   ``'running'`` plus a fresh claim token), committed on its own;
2. fetch the files (wikireplica / Toolforge API / CSV) with no database
   transaction open;
3. run the import (``admin_endpoints.run_import``) in ONE transaction whose
   last statement marks the job succeeded, fenced on the claim token. If
   that UPDATE matches no row (the claim was lost), the whole transaction
   is rolled back;
4. on any error: roll back, then mark the job failed (fenced) and write an
   ``import_failed`` audit log entry in a separate transaction. No retry.

Phase 1 stuck-job rule (run EXACTLY ONE replica): at startup every
``running`` job is marked failed (its worker was killed and its
transaction rolled back); every loop, ``running`` jobs started more than
MAX_RUNTIME ago are marked failed. Heartbeats, requeueing and SIGTERM
handling are Phase 2.
"""
import os
# pymysql evaluates a default username at import time, which fails in
# Toolforge buildservice containers without USER; same as ../app.py.
# Must come before any import that reaches pymysql (montage.rdb).
os.environ.setdefault('USER', 'montage')

import sys
import time
import uuid
import socket
import logging
import argparse
import datetime
from collections import namedtuple

import requests
from sqlalchemy import and_, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

try:
    from pymysql.err import MySQLError as WikireplicaError
except ImportError:  # pragma: no cover
    WikireplicaError = ()

from .rdb import (Base,
                  User,
                  UserDAO,
                  import_jobs_t,
                  import_result_values,
                  load_import_entries,
                  IMPORT_QUEUED,
                  IMPORT_RUNNING,
                  IMPORT_SUCCEEDED,
                  IMPORT_FAILED,
                  IMPORT_ERROR_MAX)
from .utils import MontageError, load_env_config, check_schema
from .app import make_engine, DEFAULT_DB_URL
from .admin_endpoints import run_import


log = logging.getLogger('montage.import_worker')

MAX_RUNTIME = datetime.timedelta(minutes=60)
DEFAULT_POLL = 5  # seconds between polls when the queue is empty

INTERRUPTED_ERROR = ('import interrupted by a worker restart; cancel this'
                     ' round and create it again')
MAX_RUNTIME_ERROR = ('import exceeded the maximum runtime of %d minutes;'
                     ' cancel this round and create it again'
                     % (MAX_RUNTIME.total_seconds() // 60))

# Plain values only: the import session must never hold the job as an ORM
# object, or a flush could write the job row without the claim-token fence.
Claim = namedtuple('Claim', 'id token round_id user_id method params')

_c = import_jobs_t.c


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def default_worker_id():
    return '%s:%s' % (socket.gethostname(), os.getpid())


def _error_text(exc):
    """The error shown to coordinators: MontageError messages verbatim,
    database errors reduced to the driver message (no SQL / parameter
    dump), anything else as 'Type: message'. Full tracebacks go to the
    worker log only."""
    if isinstance(exc, MontageError):
        text = str(exc)
    elif isinstance(exc, DBAPIError) and exc.orig is not None:
        text = '%s: %s' % (type(exc.orig).__name__, exc.orig)
    elif isinstance(exc, requests.exceptions.Timeout):
        text = ('timed out while fetching the files to import (%s: %s)'
                % (type(exc).__name__, exc))
    elif isinstance(exc, requests.exceptions.RequestException):
        text = ('could not fetch the files to import (%s: %s)'
                % (type(exc).__name__, exc))
    elif isinstance(exc, WikireplicaError):
        # raw pymysql errors only come from labs.py (the app database is
        # reached through SQLAlchemy, whose errors are DBAPIError)
        text = ('the Commons database query failed or timed out (%s: %s)'
                % (type(exc).__name__, exc))
    else:
        text = '%s: %s' % (type(exc).__name__, exc)
    return text[:IMPORT_ERROR_MAX]


def _fenced(claim):
    return and_(_c.id == claim.id,
                _c.status == IMPORT_RUNNING,
                _c.claim_token == claim.token)


def _log_import_failed(session, job_id, round_id, user_id, error):
    user = session.query(User).get(user_id) if user_id else None
    msg = 'import job #%s failed: %s' % (job_id, error)
    UserDAO(session, user).log_action('import_failed',
                                      round_id=round_id,
                                      role='import_worker',
                                      message=msg)
    return


def claim_next_job(engine, worker_id=None):
    """Claim the oldest queued job; return a Claim, or None if the queue
    is empty. Safe with several workers: the UPDATE only matches while the
    job is still queued, and rowcount tells who won (MySQL reports matched
    rows: SQLAlchemy's mysql dialects set CLIENT.FOUND_ROWS)."""
    worker_id = worker_id or default_worker_id()
    session = sessionmaker(bind=engine)()
    lost = set()
    try:
        while True:
            q = select([_c.id]).where(_c.status == IMPORT_QUEUED)
            if lost:
                q = q.where(~_c.id.in_(sorted(lost)))
            q = q.order_by(_c.id).limit(1)
            job_id = session.execute(q).scalar()
            if job_id is None:
                session.rollback()
                return None

            token = uuid.uuid4().hex
            now = _utcnow()
            res = session.execute(
                import_jobs_t.update()
                .where(and_(_c.id == job_id, _c.status == IMPORT_QUEUED))
                .values(status=IMPORT_RUNNING,
                        claimed_by=worker_id,
                        claim_token=token,
                        start_date=now,
                        heartbeat_date=now,
                        attempts=_c.attempts + 1))
            if res.rowcount != 1:
                # another worker got there first
                session.rollback()
                lost.add(job_id)
                continue

            row = session.execute(
                select([_c.round_id, _c.user_id, _c.method, _c.params])
                .where(_c.id == job_id)).first()
            session.commit()
            return Claim(id=job_id,
                         token=token,
                         round_id=row.round_id,
                         user_id=row.user_id,
                         method=row.method,
                         params=dict(row.params or {}))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _mark_failed(engine, claim, error):
    """Mark a claimed job failed (fenced) plus an audit log entry, in a
    transaction of its own. Returns True if the job was marked."""
    session = sessionmaker(bind=engine)()
    try:
        res = session.execute(
            import_jobs_t.update()
            .where(_fenced(claim))
            .values(status=IMPORT_FAILED,
                    error=error,
                    finish_date=_utcnow(),
                    claim_token=None))
        marked = res.rowcount == 1
        if marked:
            _log_import_failed(session, claim.id, claim.round_id,
                               claim.user_id, error)
        session.commit()
        return marked
    except Exception:
        session.rollback()
        # the job stays 'running' until the next worker start or the
        # max-runtime sweep marks it failed
        log.exception('could not mark import job #%s failed', claim.id)
        return False
    finally:
        session.close()


def process_job(engine, claim):
    """Run a claimed job. Returns 'succeeded', 'failed' or 'lost'."""
    start = time.time()
    log.info('job #%s: starting %s import into round %s',
             claim.id, claim.method, claim.round_id)
    session = None
    try:
        # fetch with no transaction open: this is the slow, external part
        loaded = load_import_entries(claim.method, claim.params)

        session = sessionmaker(bind=engine)()
        user = session.query(User).get(claim.user_id)
        if user is None:
            raise RuntimeError('user %s who requested the import does not'
                               ' exist' % (claim.user_id,))
        user_dao = UserDAO(session, user)
        stats = run_import(user_dao, claim.round_id, claim.method,
                           claim.params, loaded=loaded)
        session.flush()

        # LAST statement of the import transaction, fenced on the claim
        now = _utcnow()
        res = session.execute(
            import_jobs_t.update()
            .where(_fenced(claim))
            .values(status=IMPORT_SUCCEEDED,
                    finish_date=now,
                    heartbeat_date=now,
                    **import_result_values(stats)))
        if res.rowcount != 1:
            session.rollback()
            log.warning('job #%s: claim lost before commit (job was failed'
                        ' or reclaimed meanwhile); import rolled back',
                        claim.id)
            return 'lost'
        session.commit()
        log.info('job #%s: succeeded in %.1fs: %s files, %s added to round'
                 ' %s, %s disqualified', claim.id, time.time() - start,
                 stats.get('entry_count'),
                 stats.get('new_round_entry_count', 0), claim.round_id,
                 len(stats.get('disqualified') or []))
        return 'succeeded'
    except Exception as e:
        log.exception('job #%s: import failed after %.1fs',
                      claim.id, time.time() - start)
        if session is not None:
            try:
                session.rollback()
            except Exception:
                # e.g. the connection is gone; record the failure anyway
                log.exception('job #%s: rollback failed', claim.id)
        _mark_failed(engine, claim, _error_text(e))
        return 'failed'
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                log.exception('job #%s: closing the session failed',
                              claim.id)


def fail_interrupted_jobs(engine, now=None, at_startup=False):
    """Phase 1 stuck-job rule. at_startup: fail EVERY running job (only
    correct with exactly one worker replica). Otherwise: fail running jobs
    whose start_date is older than MAX_RUNTIME. Returns the failed job
    ids."""
    now = now or _utcnow()
    if at_startup:
        cond = _c.status == IMPORT_RUNNING
        error = INTERRUPTED_ERROR
    else:
        cond = and_(_c.status == IMPORT_RUNNING,
                    _c.start_date < now - MAX_RUNTIME)
        error = MAX_RUNTIME_ERROR

    session = sessionmaker(bind=engine)()
    failed = []
    try:
        rows = session.execute(
            select([_c.id, _c.round_id, _c.user_id]).where(cond)
            .order_by(_c.id)).fetchall()
        for row in rows:
            res = session.execute(
                import_jobs_t.update()
                .where(and_(_c.id == row.id, cond))
                .values(status=IMPORT_FAILED,
                        error=error,
                        finish_date=now,
                        claim_token=None))
            if res.rowcount != 1:
                continue
            _log_import_failed(session, row.id, row.round_id, row.user_id,
                               error)
            failed.append(row.id)
            log.warning('job #%s (round %s): marked failed: %s',
                        row.id, row.round_id, error)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return failed


def run_once(engine, worker_id=None):
    """Max-runtime sweep, then claim and process jobs until the queue is
    empty. Returns [(job_id, outcome), ...]. For tests and manual runs;
    does not run the startup sweep."""
    fail_interrupted_jobs(engine)
    outcomes = []
    while True:
        claim = claim_next_job(engine, worker_id)
        if claim is None:
            break
        outcomes.append((claim.id, process_job(engine, claim)))
    return outcomes


def run_loop_iteration(engine, worker_id=None):
    """One poll of the worker loop: sweep, then claim and process at most
    one job. Never raises; a transient error (e.g. a lost database
    connection) is logged and the loop continues. Returns True if a job
    was processed."""
    try:
        fail_interrupted_jobs(engine)
        claim = claim_next_job(engine, worker_id)
        if claim is None:
            return False
        process_job(engine, claim)
        return True
    except Exception:
        log.exception('import worker loop error; continuing')
        return False


def main(argv=None):
    prs = argparse.ArgumentParser(
        description='Run queued Montage import jobs (hatnote/montage#621).')
    prs.add_argument('--once', action='store_true',
                     help='process the queued jobs, then exit (no startup'
                     ' sweep)')
    prs.add_argument('--poll-interval', type=float, default=DEFAULT_POLL,
                     help='seconds to wait when the queue is empty'
                     ' (default %(default)s)')
    args = prs.parse_args(argv)

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

    config = load_env_config()
    db_url = config.get('db_url', DEFAULT_DB_URL)
    # exits 2 if a model table/column is missing (e.g. import_jobs)
    check_schema(db_url, Base, autoexit=True)
    engine = make_engine(config)
    # db_echo would log every 5-second poll; the worker logs its own lines
    engine.echo = False
    worker_id = default_worker_id()
    log.info('import worker %s starting (env %s)', worker_id,
             config.get('__env__'))

    if args.once:
        for job_id, outcome in run_once(engine, worker_id):
            log.info('job #%s: %s', job_id, outcome)
        return 0

    failed = fail_interrupted_jobs(engine, at_startup=True)
    if failed:
        log.warning('marked %s interrupted job(s) failed at startup: %r',
                    len(failed), failed)
    while True:
        if not run_loop_iteration(engine, worker_id):
            time.sleep(args.poll_interval)


if __name__ == '__main__':
    sys.exit(main())
