# -*- coding: utf-8 -*-
"""Background import worker (hatnote/montage#621, origin #618).

Runs the imports queued by ``POST /admin/round/<id>/import`` (see
``CoordinatorDAO.enqueue_import``), outside any web request. On Toolforge
it is a continuous job (Procfile entry ``import-worker``); locally
``./dev-servers.sh`` runs it, or ``python -m montage.import_worker --once``.

For each job:

1. claim it with a compare-and-set UPDATE (``status='queued'`` ->
   ``'running'`` plus a fresh claim token), committed on its own;
2. start a heartbeat thread that refreshes ``heartbeat_date`` every
   HEARTBEAT_INTERVAL seconds and fails the job after MAX_RUNTIME;
3. skip the job if its round is no longer paused (e.g. cancelled), else
   fetch the files (wikireplica / Toolforge API / CSV) with no database
   transaction open;
4. run the import (``admin_endpoints.run_import``) in ONE transaction. The
   heartbeat thread is stopped and joined, then the transaction's last
   statement marks the job succeeded, fenced on the claim token. If that
   UPDATE matches no row (the claim was lost), the import is rolled back;
5. on any error: roll back, then mark the job failed (fenced) and write an
   ``import_failed`` audit log entry in a separate transaction.

Every UPDATE of a claimed job is fenced with ``id AND status='running' AND
claim_token``, so a worker that lost its claim cannot change the job.

Recovery (safe with more than one replica): each loop,
``recover_stale_jobs`` takes ``running`` jobs whose heartbeat is older than
STALE_AFTER (their worker died, e.g. OOM or SIGKILL) and requeues them once
(``attempts < MAX_ATTEMPTS``) or else marks them failed. On SIGTERM (a
deploy or pod eviction) the worker rolls back and releases its job back to
``queued`` without using up an attempt, then exits.
"""
import os
# pymysql evaluates a default username at import time, which fails in
# Toolforge buildservice containers without USER; same as ../app.py.
# Must come before any import that reaches pymysql (montage.rdb).
os.environ.setdefault('USER', 'montage')

import sys
import time
import uuid
import signal
import socket
import logging
import argparse
import datetime
import threading
from contextlib import contextmanager
from collections import namedtuple

import requests
from sqlalchemy import and_, select, func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

try:
    from pymysql.err import MySQLError as WikireplicaError
except ImportError:  # pragma: no cover
    WikireplicaError = ()

from .rdb import (Base,
                  Round,
                  User,
                  UserDAO,
                  import_jobs_t,
                  import_result_values,
                  is_lock_error,
                  load_import_entries,
                  PAUSED_STATUS,
                  IMPORT_QUEUED,
                  IMPORT_RUNNING,
                  IMPORT_SUCCEEDED,
                  IMPORT_FAILED,
                  IMPORT_ERROR_MAX)
from .utils import (MontageError,
                    InvalidAction,
                    load_env_config,
                    check_schema)
from .app import make_engine, DEFAULT_DB_URL
from .admin_endpoints import run_import


log = logging.getLogger('montage.import_worker')

DEFAULT_POLL = 5  # seconds between polls when the queue is empty
HEARTBEAT_INTERVAL = 30  # seconds
STALE_AFTER = datetime.timedelta(minutes=5)  # no heartbeat for this long
MAX_ATTEMPTS = 2  # a stale job is requeued once, then failed
MAX_RUNTIME = datetime.timedelta(minutes=60)
HEARTBEAT_JOIN_TIMEOUT = 60  # seconds to wait for a heartbeat in progress
# On shutdown the pod has a short grace period (Kubernetes default 30 s):
# don't wait long for a heartbeat in progress. Releasing is fenced, so a
# late heartbeat cannot undo it.
SHUTDOWN_JOIN_TIMEOUT = 2

MAX_RUNTIME_ERROR = ('import exceeded the maximum runtime of %d minutes'
                     % (MAX_RUNTIME.total_seconds() // 60))
STALE_ERROR = ('the import worker stopped responding (%d attempts; e.g. it'
               ' ran out of memory or was killed)')
LOCK_ERROR = ('the database was busy (lock wait timeout or deadlock);'
              ' retry the import')

_rounds_c = Round.__table__.c

# Plain values only: the import session must never hold the job as an ORM
# object, or a flush could write the job row without the claim-token fence.
# flags: the job's flags when claimed (e.g. retry_of), kept on success.
Claim = namedtuple('Claim', 'id token round_id user_id method params'
                   ' start_date flags', defaults=(None, None))

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
    elif is_lock_error(exc):
        text = '%s (%s: %s)' % (LOCK_ERROR, type(exc.orig).__name__,
                                exc.orig)
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


# ---------------------------------------------------------------------------
# Shutdown (SIGTERM / SIGINT)
# ---------------------------------------------------------------------------

class WorkerShutdown(BaseException):
    """Raised in the main thread by the signal handler while a job runs
    (BaseException, so the worker's `except Exception` blocks let it
    through)."""


# 'interruptible' is True only while it is safe to abandon the current
# work (the fetch and the import before its final fenced UPDATE). The
# signal handler raises only then; otherwise it only sets 'requested'
# and the loop exits after the current step.
_shutdown = {'requested': False, 'interruptible': False}


def _on_shutdown_signal(signum, frame):
    _shutdown['requested'] = True
    if _shutdown['interruptible']:
        _shutdown['interruptible'] = False
        raise WorkerShutdown('received signal %s' % signum)


@contextmanager
def _interruptible():
    if _shutdown['requested']:
        raise WorkerShutdown('shutdown requested')
    _shutdown['interruptible'] = True
    try:
        yield
    finally:
        _shutdown['interruptible'] = False


def install_signal_handlers():
    signal.signal(signal.SIGTERM, _on_shutdown_signal)
    signal.signal(signal.SIGINT, _on_shutdown_signal)


# ---------------------------------------------------------------------------
# Claim, heartbeat, release
# ---------------------------------------------------------------------------

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
                select([_c.round_id, _c.user_id, _c.method, _c.params,
                        _c.flags])
                .where(_c.id == job_id)).first()
            session.commit()
            return Claim(id=job_id,
                         token=token,
                         round_id=row.round_id,
                         user_id=row.user_id,
                         method=row.method,
                         params=dict(row.params or {}),
                         start_date=now,
                         flags=dict(row.flags or {}))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def heartbeat_tick(engine, claim, now=None):
    """One heartbeat of a claimed job, in its own transaction.

    Returns 'ok' (heartbeat_date refreshed), 'expired' (the job ran longer
    than MAX_RUNTIME and was marked failed), or 'lost' (the fenced UPDATE
    matched no row: the job was failed, requeued or reclaimed meanwhile).
    Database errors propagate (the caller logs them and tries again)."""
    now = now or _utcnow()
    expired = (claim.start_date is not None
               and now - claim.start_date > MAX_RUNTIME)
    if expired:
        values = {'status': IMPORT_FAILED,
                  'error': MAX_RUNTIME_ERROR,
                  'finish_date': now,
                  'claim_token': None}
    else:
        values = {'heartbeat_date': now}
    session = sessionmaker(bind=engine)()
    try:
        res = session.execute(
            import_jobs_t.update().where(_fenced(claim)).values(**values))
        if res.rowcount != 1:
            session.rollback()
            log.warning('job #%s: claim lost (heartbeat matched no row)',
                        claim.id)
            return 'lost'
        if expired:
            _log_import_failed(session, claim.id, claim.round_id,
                               claim.user_id, MAX_RUNTIME_ERROR)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    if expired:
        log.warning('job #%s (round %s): marked failed: %s',
                    claim.id, claim.round_id, MAX_RUNTIME_ERROR)
        return 'expired'
    return 'ok'


class Heartbeat(object):
    """Daemon thread calling heartbeat_tick every `interval` seconds until
    stopped, or until the claim is lost or expired. Errors are logged and
    retried at the next tick (on SQLite the import transaction holds the
    write lock, so heartbeats during the write phase fail with 'database
    is locked'; MariaDB has row locks and is not affected)."""

    def __init__(self, engine, claim, interval=HEARTBEAT_INTERVAL):
        self.engine = engine
        self.claim = claim
        self.interval = interval
        self.result = None
        self._stopped = False
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name='heartbeat-job-%s' % claim.id)
        self._thread.daemon = True

    def start(self):
        self._thread.start()
        return self

    def _run(self):
        while not self._stop_event.wait(self.interval):
            try:
                result = heartbeat_tick(self.engine, self.claim)
            except Exception:
                log.exception('job #%s: heartbeat failed; retrying',
                              self.claim.id)
                continue
            if result != 'ok':
                self.result = result
                return

    def stop(self, timeout=HEARTBEAT_JOIN_TIMEOUT):
        """Stop and join (at most `timeout` seconds). Joins only on the
        first call; later calls return at once. After it returns no
        heartbeat UPDATE is in flight, unless the join timed out (logged)."""
        self._stop_event.set()
        if self._stopped:
            return
        self._stopped = True
        if self._thread.is_alive():
            self._thread.join(timeout)
            if self._thread.is_alive():
                log.warning('job #%s: heartbeat thread did not stop within'
                            ' %ss', self.claim.id, timeout)


def release_job(engine, claim):
    """Put a claimed job back to 'queued' (fenced) without using up an
    attempt; used on shutdown. Returns True if the job was released. On
    failure the job stays 'running' and recover_stale_jobs requeues it
    once its heartbeat is stale."""
    session = sessionmaker(bind=engine)()
    try:
        res = session.execute(
            import_jobs_t.update()
            .where(_fenced(claim))
            .values(status=IMPORT_QUEUED,
                    attempts=_c.attempts - 1,
                    claimed_by=None,
                    claim_token=None,
                    start_date=None,
                    heartbeat_date=None))
        released = res.rowcount == 1
        session.commit()
        if released:
            log.warning('job #%s (round %s): released back to the queue',
                        claim.id, claim.round_id)
        else:
            log.warning('job #%s: not released (claim already lost)',
                        claim.id)
        return released
    except Exception:
        session.rollback()
        log.exception('job #%s: could not release the job', claim.id)
        return False
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
        # the job stays 'running'; its heartbeat stops with this attempt,
        # so recover_stale_jobs picks it up after STALE_AFTER
        log.exception('could not mark import job #%s failed', claim.id)
        return False
    finally:
        session.close()


def _check_round_paused(engine, claim):
    """Skip jobs whose round is no longer paused (e.g. cancelled while
    the job was queued) before the slow fetch."""
    with engine.connect() as conn:
        status = conn.execute(select([_rounds_c.status])
                              .where(_rounds_c.id == claim.round_id)).scalar()
    if status != PAUSED_STATUS:
        raise InvalidAction('import skipped: the round is %s, not paused'
                            % (status or 'missing',))
    return


def _discard_session(session, claim):
    # After an interrupt the connection may be mid-protocol: drop it
    # instead of rolling back on it. The server rolls back the open
    # transaction when the connection closes.
    try:
        session.invalidate()
    except Exception:
        log.exception('job #%s: discarding the session failed', claim.id)


def process_job(engine, claim, heartbeat_interval=None):
    """Run a claimed job. Returns 'succeeded', 'failed' or 'lost'. Raises
    WorkerShutdown after releasing the job if a shutdown interrupted it."""
    start = time.time()
    log.info('job #%s: starting %s import into round %s',
             claim.id, claim.method, claim.round_id)
    session = None
    heartbeat = None
    try:
        if heartbeat_interval:
            heartbeat = Heartbeat(engine, claim, heartbeat_interval).start()
        with _interruptible():
            _check_round_paused(engine, claim)
            # fetch with no transaction open: the slow, external part
            loaded = load_import_entries(claim.method, claim.params)

            # The fetch can take long: if the claim expired (MAX_RUNTIME)
            # or was lost (requeued, reclaimed) meanwhile, don't start a
            # write transaction whose commit is fenced off anyway; it would
            # hold locks against the run that now owns the job.
            if heartbeat is not None and heartbeat.result is not None:
                log.warning('job #%s: claim %s during the fetch; not'
                            ' importing', claim.id, heartbeat.result)
                return 'lost'

            session = sessionmaker(bind=engine)()
            user = session.query(User).get(claim.user_id)
            if user is None:
                raise RuntimeError('user %s who requested the import does'
                                   ' not exist' % (claim.user_id,))
            user_dao = UserDAO(session, user)
            stats = run_import(user_dao, claim.round_id, claim.method,
                               claim.params, loaded=loaded)
            session.flush()

        # No interrupts from here on, and no heartbeat UPDATE racing ours
        if heartbeat is not None:
            heartbeat.stop()
        # LAST statement of the import transaction, fenced on the claim.
        # Merge flags (the UPDATE replaces the column): keep retry_of etc.
        now = _utcnow()
        values = import_result_values(stats)
        values['flags'] = dict(claim.flags or {}, **values['flags'])
        res = session.execute(
            import_jobs_t.update()
            .where(_fenced(claim))
            .values(status=IMPORT_SUCCEEDED,
                    finish_date=now,
                    heartbeat_date=now,
                    **values))
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
    except WorkerShutdown:
        log.warning('job #%s: shutdown requested after %.1fs; rolling back',
                    claim.id, time.time() - start)
        if session is not None:
            _discard_session(session, claim)
            session = None
        if heartbeat is not None:
            heartbeat.stop(timeout=SHUTDOWN_JOIN_TIMEOUT)
        release_job(engine, claim)
        raise
    except Exception as e:
        if _shutdown['requested']:
            # most likely a side effect of the interrupt (e.g. a rollback
            # on the interrupted connection failing): release, don't fail
            log.warning('job #%s: %s: %s during shutdown; rolling back',
                        claim.id, type(e).__name__, e)
            if session is not None:
                _discard_session(session, claim)
                session = None
            if heartbeat is not None:
                heartbeat.stop(timeout=SHUTDOWN_JOIN_TIMEOUT)
            release_job(engine, claim)
            raise WorkerShutdown('shutdown requested') from e
        log.exception('job #%s: import failed after %.1fs',
                      claim.id, time.time() - start)
        if session is not None:
            try:
                session.rollback()
            except Exception:
                # e.g. the connection is gone; record the failure anyway
                log.exception('job #%s: rollback failed', claim.id)
        if heartbeat is not None:
            heartbeat.stop()
        _mark_failed(engine, claim, _error_text(e))
        return 'failed'
    finally:
        if heartbeat is not None:
            heartbeat.stop()
        if session is not None:
            try:
                session.close()
            except Exception:
                log.exception('job #%s: closing the session failed',
                              claim.id)


# ---------------------------------------------------------------------------
# Stale-job recovery
# ---------------------------------------------------------------------------

def recover_stale_jobs(engine, now=None):
    """Requeue or fail 'running' jobs whose heartbeat is older than
    STALE_AFTER (their worker died without releasing them). A job with
    attempts < MAX_ATTEMPTS goes back to 'queued' (the import is one
    transaction, so nothing of it was committed and a rerun is safe);
    otherwise it is marked failed. Each UPDATE re-checks the stale
    condition and the claim token, so this is safe with several workers.
    Returns (requeued_ids, failed_ids)."""
    now = now or _utcnow()
    cutoff = now - STALE_AFTER
    last_sign_of_life = func.coalesce(_c.heartbeat_date, _c.start_date,
                                      _c.create_date)
    stale = and_(_c.status == IMPORT_RUNNING, last_sign_of_life < cutoff)

    session = sessionmaker(bind=engine)()
    requeued, failed = [], []
    try:
        rows = session.execute(
            select([_c.id, _c.round_id, _c.user_id, _c.attempts,
                    _c.claim_token])
            .where(stale).order_by(_c.id)).fetchall()
        for row in rows:
            # explicit IS NULL: a running row without a token (manual SQL,
            # legacy) must still be recoverable
            if row.claim_token is None:
                same_token = _c.claim_token.is_(None)
            else:
                same_token = _c.claim_token == row.claim_token
            fence = and_(_c.id == row.id, stale, same_token)
            if (row.attempts or 0) < MAX_ATTEMPTS:
                res = session.execute(
                    import_jobs_t.update().where(fence)
                    .values(status=IMPORT_QUEUED,
                            claimed_by=None,
                            claim_token=None,
                            start_date=None,
                            heartbeat_date=None))
                if res.rowcount == 1:
                    requeued.append(row.id)
                    log.warning('job #%s (round %s): no heartbeat since %s;'
                                ' requeued (attempt %s of %s used)',
                                row.id, row.round_id, cutoff,
                                row.attempts, MAX_ATTEMPTS)
                continue
            error = STALE_ERROR % (row.attempts,)
            res = session.execute(
                import_jobs_t.update().where(fence)
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
    return requeued, failed


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------

def run_once(engine, worker_id=None, heartbeat_interval=None):
    """Stale recovery, then claim and process jobs until the queue is
    empty. Returns [(job_id, outcome), ...]. For tests and manual runs."""
    recover_stale_jobs(engine)
    outcomes = []
    while True:
        claim = claim_next_job(engine, worker_id)
        if claim is None:
            break
        outcomes.append((claim.id, process_job(engine, claim,
                                               heartbeat_interval)))
    return outcomes


def run_loop_iteration(engine, worker_id=None, heartbeat_interval=None):
    """One poll of the worker loop: stale recovery, then claim and process
    at most one job. Never raises an Exception; a transient error (a lost
    database connection, a lock wait timeout or deadlock) is logged and
    the loop continues. WorkerShutdown propagates. Returns True if a job
    was processed."""
    try:
        recover_stale_jobs(engine)
        claim = claim_next_job(engine, worker_id)
        if claim is None:
            return False
        process_job(engine, claim, heartbeat_interval)
        return True
    except Exception as e:
        if is_lock_error(e):
            log.warning('import worker: database busy (%s: %s); retrying at'
                        ' the next poll', type(e.orig).__name__, e.orig)
        else:
            log.exception('import worker loop error; continuing')
        return False


def main(argv=None):
    prs = argparse.ArgumentParser(
        description='Run queued Montage import jobs (hatnote/montage#621).')
    prs.add_argument('--once', action='store_true',
                     help='process the queued jobs, then exit')
    prs.add_argument('--poll-interval', type=float, default=DEFAULT_POLL,
                     help='seconds to wait when the queue is empty'
                     ' (default %(default)s)')
    prs.add_argument('--heartbeat-interval', type=float,
                     default=HEARTBEAT_INTERVAL,
                     help='seconds between heartbeats of a running job;'
                     ' 0 disables them (default %(default)s)')
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
    heartbeat_interval = args.heartbeat_interval or None
    log.info('import worker %s starting (env %s)', worker_id,
             config.get('__env__'))

    if args.once:
        for job_id, outcome in run_once(engine, worker_id,
                                        heartbeat_interval):
            log.info('job #%s: %s', job_id, outcome)
        return 0

    install_signal_handlers()
    try:
        while not _shutdown['requested']:
            if not run_loop_iteration(engine, worker_id,
                                      heartbeat_interval):
                with _interruptible():
                    time.sleep(args.poll_interval)
    except WorkerShutdown:
        pass
    log.info('import worker %s: shutdown requested; exiting', worker_id)
    return 0


if __name__ == '__main__':
    sys.exit(main())
