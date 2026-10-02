# Montage Deployment (Wikimedia Toolforge)

This guide is **specific to the Wikimedia Toolforge environment**: it assumes the Toolforge
Kubernetes buildservice, the `toolforge` CLI, Toolforge tool accounts, and Toolforge-managed
NFS and databases. Every step and prerequisite below is Toolforge-specific — deploying Montage
on a generic or self-hosted server is out of scope here.

<!-- TODO (later): separate the prerequisites into "Wikimedia Toolforge-specific" vs
     "any server" once a non-Toolforge deployment path is documented. -->

---

## Fresh install

#### 1. Register OAuth 2.0 credentials

[Register an OAuth 2.0 client](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose) on Meta-Wiki: choose **OAuth 2.0**, set the **callback (redirect) URI** to `https://<tool>.toolforge.org/complete_login` (e.g. `https://montage-beta.toolforge.org/complete_login`), and grant the **basic** scope. Save the **client ID** and **client secret** — you will need them in step 3. Each tool account needs its own client, because the callback URI differs per environment.

#### 2. SSH into the tool account

```bash
ssh <shell-username>@login.toolforge.org
become montage-beta
```

Replace `montage-beta` with `montage` or `montage-dev` as appropriate.

#### 3. Set environment variables (one-time)

Toolforge stores these as Kubernetes Secrets, injected into every pod on start. Use the
**interactive prompt** for secret values — never pass them as command-line arguments (they
would appear in `~/.bash_history` on the shared bastion).

```bash
toolforge envvars create MONTAGE_ENV            # enter: devlabs / beta / prod
toolforge envvars create MONTAGE_OAUTH_CLIENT_ID      # OAuth 2.0 client ID from Special:OAuthConsumerRegistration
toolforge envvars create MONTAGE_OAUTH_CLIENT_SECRET  # OAuth 2.0 client secret
toolforge envvars create MONTAGE_OAUTH_REDIRECT_URI   # e.g. https://montage-beta.toolforge.org/complete_login
toolforge envvars create MONTAGE_COOKIE_SECRET  # generate with: openssl rand -hex 32
toolforge envvars create MONTAGE_DB_URL         # mysql+pymysql://<user>:<pass>@tools.db.svc.wikimedia.cloud/<db>?charset=utf8mb4
toolforge envvars create MONTAGE_SUPERUSERS     # OPTIONAL — enables su-impersonation only, NOT admin access (see "Maintainer vs superuser" below)
toolforge envvars create MONTAGE_API_LOG_PATH   # e.g. /data/project/montage-beta/montage_api.log
toolforge envvars create MONTAGE_REPLAY_LOG_PATH
```

Optional env vars (all have sensible defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `MONTAGE_DB_ECHO` | `false` | Log all SQL queries |
| `MONTAGE_DEBUG` | `false` | Enable debug mode |
| `MONTAGE_ROOT_PATH` | `/` | URL root path |
| `MONTAGE_LABS_DB` | `true` | Enable Wikireplica queries |
| `MONTAGE_FEEL_LOG_PATH` | _(none)_ | Path for feel log |
| `MONTAGE_COMMONS_LINKS_DB_HOST` | `links.commonswiki.analytics.db.svc.wikimedia.cloud` | Wikireplica host for the Commons links tables (categorylinks, linktarget, page), on their own cluster since 2026-09-08 ([Wikitech](https://wikitech.wikimedia.org/wiki/News/2026_Commons_links_tables_database_split)) |
| `MONTAGE_IMPORT_MODE` | `sync` | `worker`: imports are queued and run by the `import-worker` job (step 7b); `sync`: imports run inside the request (old behaviour, rollback switch). Any other value (a typo, wrong case, empty) stops the web app from starting; `tools/deploy.sh` checks it before restarting anything |

#### 4. Create the database

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud
```

```sql
CREATE DATABASE `<user>__<db name>` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;
EXIT;
```

The `<user>` prefix must match the username in `~/replica.my.cnf`. See [Toolforge user databases](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database#User_databases).

The `MONTAGE_DB_URL` you set in step 3 should use this database name.

#### 5. Build the container image

```bash
toolforge build start https://github.com/hatnote/montage.git --ref <branch>
```

This builds the Python app and Vue frontend together into a single container image. Monitor progress:

```bash
toolforge build logs
```

Wait until the build completes successfully before continuing.

#### 6. Initialise the database schema

Run inside the buildservice shell (uses the same image as the webservice):

```bash
toolforge webservice buildservice shell
export USER=montage          # required — see note
launcher python tools/create_schema.py
exit
```

> **Why `export USER=montage`:** the buildservice **shell** does not run the app entrypoint, so
> `USER` is unset and the container has no passwd entry. `pymysql` calls `getpass.getuser()` at
> import time and raises `OSError: No username set in the environment`, which aborts any script
> that imports `montage.rdb`/`labs`. The running webservice avoids this because `app.py` does
> `os.environ.setdefault('USER', …)` before importing pymysql — but that only runs via the
> Procfile (`gunicorn app:app`), not in an interactive shell. Set `USER` manually there.

If upgrading an existing deployment, run the migration SQL instead (on the bastion):

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < tools/migrate_prod_db.sql
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < tools/migrate_import_jobs.sql
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < tools/migrate_round_sources_params.sql
```

`tools/migrate_import_jobs.sql` adds the `import_jobs` table (background imports,
hatnote/montage#621). Run it **before** deploying code that has it: the web app and the import
worker exit at startup if a model table is missing. Both migrations are idempotent. Fresh
installs get the table from `create_schema.py`. To undo: deploy code without the `ImportJob`
model, delete the `import-worker` job, then run `tools/revert_import_jobs.sql`.

`tools/migrate_round_sources_params.sql` widens `round_sources.params` to `MEDIUMTEXT`, so a long
file-list import no longer hits the 64 KB `TEXT` limit. The schema check does not compare column
types, so it can run before or after the deploy; run it when no import is running (the `ALTER`
copies the table). `tools/revert_round_sources_params.sql` undoes it (read its warning first).

#### 7. Start the service

```bash
toolforge webservice buildservice start --mount all
```

`--mount all` is required — Montage writes logs to NFS (`/data/project/<toolname>/`), so shared
storage must be mounted.

#### 7b. Start the import worker

Imports of a category, CSV or file list run in a background worker (hatnote/montage#621), a
Toolforge [continuous job](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Running_jobs)
using the same [buildservice image](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images)
(Procfile entry `import-worker`):

```bash
toolforge jobs run import-worker \
    --image tool-<tool>/tool-<tool>:latest \
    --command import-worker \
    --continuous --mount all --mem 1Gi --emails onfailure
toolforge envvars create MONTAGE_IMPORT_MODE    # enter: worker
toolforge envvars show MONTAGE_IMPORT_MODE      # must print exactly: worker
toolforge webservice buildservice restart --mount all
```

The web app refuses to start if `MONTAGE_IMPORT_MODE` is anything but `sync` or `worker`.
`tools/deploy.sh` checks the value before it restarts anything, but a manual
`webservice ... restart` like the one above does not, so check the value first.

- Keep one replica (the default). More are correct for the job rows (claims and every job
  update are fenced, and recovery goes by heartbeat, not by worker start), but overlapping
  imports contend for database locks and can collide on the same file names and fail (the
  coordinator retries).
- A running job's heartbeat is refreshed every 30 s. A job whose worker died without a heartbeat
  for 5 minutes (OOM, SIGKILL) is put back in the queue once; on the second time it is marked
  failed ("the import worker stopped responding"). A job running longer than 60 minutes is
  marked failed by the worker's heartbeat thread, and nothing of that import is kept (the worker
  skips the import if the time ran out during the fetch, and its final commit is refused
  otherwise). This limit is soft: a fetch or import already under way is not cut short, so the
  worker stays busy until it ends.
- On SIGTERM (`toolforge jobs restart`, a deploy, pod eviction) the worker rolls back and puts its
  running job back in the queue without counting the attempt; the next worker runs it again.
- `--mount all`: same reason as the webservice. Wikireplica credentials come from the
  `TOOL_REPLICA_USER` / `TOOL_REPLICA_PASSWORD` envvars Toolforge provides, else
  `$TOOL_DATA_DIR/replica.my.cnf`, else `~/replica.my.cnf` (in a job pod `HOME` is `/`, so `~`
  is not the tool's home).
- Check it started: `toolforge jobs logs import-worker` should show `schema validated ok` and
  `import worker ... starting`.
- Until `MONTAGE_IMPORT_MODE=worker` is set, imports keep running inside the request (`sync`).
- A failed import shows its reason on the round page, with **Retry import** (same source again)
  and **Dismiss** (unblocks activation with the files the round already has; a round with no
  files still cannot be activated). A queued import of a cancelled round is
  skipped without fetching anything.

Checked on montage-dev (worker mode): the worker finds the wikireplica credentials in its job
pod, and `toolforge jobs restart` picks up the new `:latest` image.

**To verify on montage-beta before production** (unverified so far): memory use of a large
(~21.5k file) category import fits `--mem 1Gi` (measured off Toolforge: a 120k-file import
peaked at about 1 GiB, so treat about 100k files as the ceiling); `launcher` passes SIGTERM on
to Python (the worker log shows `released back to the queue` after a restart during an import) and the
rollback fits the pod's termination grace period (otherwise the job is requeued after 5 minutes
instead); `toolforge jobs list` prints the job name `import-worker` (deploy.sh looks for it).

#### 8. Verify

Confirm the service is running:

- `https://<tool>.toolforge.org/meta/` — should show a recent start time.
- `https://<tool>.toolforge.org/v1/health` — should report `db: ok`, `status: healthy` (verifies database connectivity, not just that the app booted).

#### Maintainer vs superuser (important)

**Maintainer (admin) access is hardcoded in code, not configured.** The `MAINTAINERS` list in
`montage/rdb.py` is the source of truth for who is an admin (`User.is_maintainer` checks
membership in it). It is identical on every deployment (dev/beta/prod) and is **not** read from
config or env vars. To grant or revoke maintainer access you must edit that list in `rdb.py` and
redeploy — setting `MONTAGE_SUPERUSERS` does **not** do it. `ensure_series()` also indexes
`MAINTAINERS[0]`, so the list must never be empty.

**`MONTAGE_SUPERUSERS` is a separate, optional feature.** It enables *impersonation*: a listed
user may pass `su_to=<username>` to act as another user (for support/debugging), gated on a valid
signed cookie (`montage/mw/__init__.py`). Legacy YAML config called this `superuser` (singular);
the env var is `MONTAGE_SUPERUSERS` (comma-separated). Leave it unset to disable impersonation
entirely — it has no effect on who is an admin.

---

## Deploying new changes

#### 1. Check for active usage

Before a deploy that restarts or stops the service, confirm nobody is mid-vote.

The audit log records **admin** actions (round activate/finalize) but **not** juror voting:
https://montage-beta.toolforge.org/v1/logs/audit

For juror voting, query the database directly (works on any deploy model). Get the `<db name>`
from `config.<env>.yaml` (`db_url`) or `toolforge envvars`, then:

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> -e "SELECT UTC_TIMESTAMP() AS now_utc, (SELECT COUNT(*) FROM votes WHERE modified_date >= UTC_TIMESTAMP() - INTERVAL 15 MINUTE) AS votes_15m, (SELECT MAX(modified_date) FROM votes) AS last_vote_utc, (SELECT COUNT(*) FROM rounds WHERE status='active') AS active_rounds\\G"
```

`votes.modified_date` is stored in UTC and stamped when a juror casts or edits a vote. If
`active_rounds` is `0`, nothing is open for voting; if `votes_15m` is `0` and `last_vote_utc`
is well in the past, it is safe to restart. A juror mid-round loses no data — each vote is
committed on submission — they simply resume once the service is back.

#### 2. SSH into the tool account

```bash
ssh <shell-username>@login.toolforge.org
become montage-beta
```

#### 3. One-time setup (first deploy only)

Clone the repo so the deploy script is available on the bastion:

```bash
git clone --branch tools/buildservice https://github.com/hatnote/montage.git ~/www/python/src
```

If the repo is already cloned, make sure the branch tracks the right remote:

```bash
git -C ~/www/python/src fetch origin
git -C ~/www/python/src checkout -b tools/buildservice origin/tools/buildservice
```

#### 4. Run the deploy script

```bash
bash ~/www/python/src/tools/deploy.sh --ref <branch>
```

The script will: pull the latest version of itself, start the build, wait for
completion, verify the SHA and port, warn if the running image already matches,
check the database schema and `MONTAGE_IMPORT_MODE` inside the new image (a one-off
`schema-check` job running `tools/check_schema.py`; it aborts before any restart if a migration
is missing or the import mode is not `sync` or `worker`), restart the service, restart the
`import-worker` job (or print the command to create it), and smoke-test `/meta/`.

Run any new migration SQL **before** the deploy script (see step 6 of the fresh install).

---

## Switching an existing legacy webservice to the buildservice

If a tool is still running the old `python3.11`/`python3.13` NFS webservice — check with
`toolforge webservice status` — the deploy script cannot be used yet: it issues a `restart`,
which only applies to an already-running buildservice. Do the one-time switch manually:

```bash
whoami                                   # MUST be tools.<intended-tool> before any mutating command

# Ensure env vars are set (Fresh install step 3) and the image is built (Fresh install step 5),
# then swap the webservice type:
toolforge webservice stop
toolforge webservice buildservice start --mount all
```

`--mount all` is required; starting without it fails with
`ERROR: --mount not explicitly specified on a build service based tool`.

The legacy webservice reads its config from a YAML file on NFS, whereas the buildservice reads it
from `toolforge envvars`. A tool that worked on the legacy service can therefore still fail on the
buildservice if the `MONTAGE_*` env vars (Fresh install step 3) are not set — and its database may
need migrating (see "Startup crash: missing column" below).

---

## Debugging

#### Confirming which commit was built

Before restarting, verify the build used the expected commit and port:

```bash
toolforge build logs 2>&1 | grep -E "RESULT_SHA|gunicorn"
```

The `[step-clone]` line should show the expected `RESULT_SHA=<sha>` and the
`[step-build]` line should show `gunicorn --bind=0.0.0.0:8000`. If the SHA is wrong,
trigger a new build before restarting.

#### Diagnosing "no healthy upstream"

This means the pod never passed the Toolforge startup probe, which checks port 8000. Most
common cause: the running image binds to the wrong port. Use the build log check above to
confirm the built image uses port 8000, then restart.

#### Startup crash: `missing column ... from database`

If the pod logs (`toolforge webservice buildservice logs`) show:

```
!!  Model <class 'montage.rdb.Entry'> missing column file_id from database ...
!!  recreate the database and update the code, then try again
```

the database schema is behind the code (common when a tool has been off the buildservice for a
while). Run the migration — do **not** "recreate the database", which would wipe existing data:

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < tools/migrate_prod_db.sql
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < tools/migrate_round_sources_params.sql
toolforge webservice buildservice restart --mount all
```

The same applies to a missing table, e.g.
`!!  Model <class 'montage.rdb.ImportJob'> table import_jobs missing from database ...`: run
`tools/migrate_import_jobs.sql`, then restart the webservice and the `import-worker` job.

`tools/create_schema.py` only creates *missing tables* (`CREATE TABLE IF NOT EXISTS`); it does
**not** `ALTER` existing tables, so it will not add a missing column. Use the migration SQL for
schema changes to an existing database.

#### Viewing logs

Montage writes several log files to NFS (`/data/project/<project>/`). These are only
available because the service is started with `--mount all`; the files persist across restarts.

**Legacy (pre-buildservice) request log:** the old uWSGI webservice logs *every* request —
method, path, status, timing — to `/data/project/<project>/uwsgi.log` (e.g.
`/data/project/montage/uwsgi.log`). Health-check pings show up as frequent identical `GET /`
lines; ignore those and `robots.txt` when gauging real activity. Under the buildservice this is
replaced by `montage_api.log` (below) plus gunicorn stdout via `toolforge webservice buildservice logs`.

| Log file | Set via | What it captures |
|----------|---------|-----------------|
| `montage_api.log` | `MONTAGE_API_LOG_PATH` | Every API request — method, path, user, timing, result |
| `montage_api.exc.log` | _(derived — same path with `.exc` suffix)_ | Full tracebacks for 5xx errors |
| `montage_replay.log` | `MONTAGE_REPLAY_LOG_PATH` | Raw request replay data (optional; used for debugging) |
| `montage_feel.log` | `MONTAGE_FEEL_LOG_PATH` | Juror experience events (optional) |

Tail the API log (most useful starting point):

```bash
tail -50 /data/project/<project>/montage_api.log
```

For 5xx tracebacks:

```bash
tail -50 /data/project/<project>/montage_api.exc.log
```

**Gunicorn / pod stdout** (replaces the old `uwsgi.log`): gunicorn writes its own startup
messages and unhandled errors to stdout, which Kubernetes captures. To view it:

```bash
toolforge webservice buildservice logs
```

This is ephemeral — it reflects the current pod's output since the last restart and is not
written to a file.

**Import worker:** one line per claimed, finished and failed import job, with full tracebacks
for failures:

```bash
toolforge jobs logs import-worker        # add -f to follow
```

#### Imports stay queued

A round shows "Import queued" and cannot be activated:

1. Is the worker running? `toolforge jobs list`, `toolforge jobs show import-worker`. If it is
   missing, create it (fresh install step 7b).
2. Its log: `toolforge jobs logs import-worker` (schema errors, database errors, crashes).
3. Is `MONTAGE_IMPORT_MODE` what you expect? `toolforge envvars show MONTAGE_IMPORT_MODE`
   (unset means `sync`).
4. The jobs themselves (read-only):

   ```sql
   SELECT id, round_id, status, method, attempts, claimed_by, create_date, start_date,
          finish_date, LEFT(error, 200) AS error
   FROM import_jobs ORDER BY id DESC LIMIT 20;
   ```

**Hung worker** (one job stays "Import running", every other import stays queued, the worker
log shows nothing new): fetches have timeouts (HTTP: 15 s connect / 10 min per read; wikireplica:
10 s connect, 45 min per query, overridable with `MONTAGE_LABS_CONNECT_TIMEOUT` /
`MONTAGE_LABS_READ_TIMEOUT` in seconds; keep the connect timeout well under gunicorn's 30 s,
because in `sync` mode the fetch runs inside the web request), after which the job is marked failed with the reason
and the worker moves on; after 60 minutes the job is marked failed (the limit is soft, see step
7b: a stuck fetch keeps the worker busy). If the worker is
stuck anyway, restart it: `toolforge jobs restart import-worker`. The job goes back to the queue
and runs again (if the old pod is killed without a clean shutdown, after 5 minutes without a
heartbeat; the second time it is marked failed). The coordinator can retry or dismiss a failed
import on the round page.

**Rolling back to synchronous imports:** set `MONTAGE_IMPORT_MODE` to `sync`, restart the
webservice, delete the worker (`toolforge jobs delete import-worker`), and fail the jobs nobody
will run any more, otherwise their rounds can never be activated:

```sql
UPDATE import_jobs
SET status = 'failed', error = 'background import disabled; retry the import',
    finish_date = UTC_TIMESTAMP(), claim_token = NULL
WHERE status IN ('queued', 'running');
```

#### Running Python commands

Use the buildservice shell — prefix Python with `launcher`. Set `USER` first (the shell skips
the app entrypoint that normally sets it — see the note under "Initialise the database schema"),
and import the top-level `app` module (which sets `USER` and builds the real WSGI app) rather than
`montage.app` directly:

```bash
toolforge webservice buildservice shell
export USER=montage
launcher python -c "import app; print('app build OK')"   # exercises full startup: config, cookie guard, OAuth
launcher python tools/create_schema.py
exit
```

#### Restarting the service

```bash
toolforge webservice buildservice restart --mount all
```

#### Inspecting the database

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name>
```

```sql
SELECT COUNT(*) FROM entries;
DESCRIBE entries;
```

#### Updating environment variables

```bash
toolforge envvars create MONTAGE_SUPERUSERS  # overwrites existing value
toolforge envvars show MONTAGE_SUPERUSERS    # check one variable by name
toolforge webservice buildservice restart --mount all
```

Look at variables one at a time with `toolforge envvars show <NAME>`. Don't use
`toolforge envvars list`: it prints every value, the OAuth secret, cookie secret and database
password included, onto the shared bastion terminal.

---

## Multi-environment setup

Each tool account (`montage-dev`, `montage-beta`, `montage`) builds from its own branch and
has its own `toolforge envvars` configuration. The build command is the only thing that
differs:

| Account | Branch | URL |
|---------|--------|-----|
| `montage-dev` | `master` (or feature branch for testing) | https://montage-dev.toolforge.org |
| `montage-beta` | `master` | https://montage-beta.toolforge.org |
| `montage` | release tag | https://montage.toolforge.org |

---

## Notes

**`--forwarded-allow-ips=*` in the Procfile**: this tells Gunicorn to trust
`X-Forwarded-For` headers from any IP. This is safe on Toolforge because pods are not
directly reachable from the internet — traffic arrives exclusively through the
HAProxy → nginx-ingress chain. Do not copy the Procfile verbatim to other deployment
environments without understanding this dependency.

**Secrets are never in git or config files**: all credentials are stored as `toolforge envvars`
(Kubernetes Secrets). The config YAML files in the repo contain only non-secret defaults and
should never hold real credentials.
