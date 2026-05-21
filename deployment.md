# Montage Deployment

Instructions for deploying Montage on Toolforge using the buildservice.

---

## Fresh install

#### 1. Register OAuth credentials

[Register your app](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose) on Meta-Wiki. Save the consumer token and secret token — you will need them in step 3.

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
toolforge envvars create MONTAGE_OAUTH_CONSUMER_TOKEN
toolforge envvars create MONTAGE_OAUTH_SECRET_TOKEN
toolforge envvars create MONTAGE_COOKIE_SECRET  # generate with: openssl rand -hex 32
toolforge envvars create MONTAGE_DB_URL         # mysql+pymysql://<user>:<pass>@tools.db.svc.wikimedia.cloud/<db>?charset=utf8mb4
toolforge envvars create MONTAGE_SUPERUSERS     # comma-separated Wikimedia usernames, e.g. YourUsername
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
launcher python tools/create_schema.py
exit
```

If upgrading an existing deployment, run the migration SQL instead (on the bastion):

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < tools/migrate_prod_db.sql
```

#### 7. Start the service

```bash
toolforge webservice buildservice start --mount all
```

`--mount all` is required — Montage writes logs to NFS (`/data/project/<toolname>/`), so shared
storage must be mounted.

#### 8. Verify

Visit `/meta` to confirm the service is running. Example: https://montage-beta.toolforge.org/meta/

The response should show a recent restart time. Add your Wikimedia username to `MONTAGE_SUPERUSERS` if you need admin access.

---

## Deploying new changes

#### 1. Check for active usage

Check the audit log to confirm the instance is not in active use before deploying:
https://montage-beta.toolforge.org/v1/logs/audit

#### 2. SSH into the tool account

```bash
ssh <shell-username>@login.toolforge.org
become montage-beta
```

#### 3. Rebuild the image

```bash
toolforge build start https://github.com/hatnote/montage.git --ref <branch>
toolforge build logs  # wait for completion
```

#### 4. Restart the service

```bash
toolforge webservice buildservice restart --mount all
```

#### 5. Verify

Visit `/meta` and confirm the restart time is recent.

---

## Debugging

#### Viewing logs

```bash
tail -50 /data/project/<project>/montage_api.log
```

#### Running Python commands

Use the buildservice shell — prefix Python with `launcher`:

```bash
toolforge webservice buildservice shell
launcher python -c "import montage.app"
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
toolforge webservice buildservice restart
```

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
