# Montage Deployment

Instructions for deploying Montage on Toolforge.

---

## Fresh install

#### 1. Register OAuth credentials

[Register your app](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose) on Meta-Wiki. Save the consumer token and secret token — you will need them in step 6.

#### 2. SSH into the tool account

```bash
ssh <shell-username>@login.toolforge.org
become montage-beta
```

Replace `montage-beta` with `montage` or `montage-dev` as appropriate.

#### 3. Clone the repo

```bash
mkdir -p $HOME/www/python
cd $HOME/www/python
git clone https://github.com/hatnote/montage.git src
```

#### 4. Build the frontend

```bash
cd $HOME/www/python/src
bash tools/build_frontend.sh
```

This runs a Toolforge job (node20, 4Gi) and waits for it to finish. See `tools/build_frontend.sh` for documented workarounds.

#### 5. Create the database

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud
```

```sql
CREATE DATABASE `<user>__<db name>` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;
EXIT;
```

The `<user>` prefix must match the username in `~/replica.my.cnf`. See [Toolforge user databases](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database#User_databases).

#### 6. Set up the config file

```bash
cp $HOME/www/python/src/config.default.yaml $HOME/www/python/src/config.<env>.yaml
chmod 600 $HOME/www/python/src/config.<env>.yaml
```

Edit the file and set the following fields:

```yaml
# OAuth tokens from step 1
oauth_consumer_token: "<consumer token>"
oauth_secret_token: "<secret token>"

# Random secret for session cookies — use: openssl rand -hex 32
cookie_secret: "<random secret>"

# Database — credentials are in ~/replica.my.cnf
db_url: "mysql+pymysql://<user>:<password>@tools.db.svc.wikimedia.cloud/<user>__<db name>?charset=utf8mb4"

# Logs
api_log_path: /data/project/<project>/montage_api.log
replay_log_path: /data/project/<project>/montage_replay.log

# Required for Toolforge
labs_db: True
db_echo: False
root_path: '/'

# Add your Wikimedia username to get admin access
superuser: YourUsername
```

Note: if you need to add a new environment beyond dev/beta/prod, update `USER_ENV_MAP` in `montage/utils.py`.

#### 7. Create the virtual environment

Run inside the webservice shell — `python3 -m venv` with pip hangs in the pod, so bootstrap pip via curl instead:

```bash
toolforge webservice python3.13 shell
python3 -m venv ~/www/python/venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | ~/www/python/venv/bin/python3
~/www/python/venv/bin/pip install -r ~/www/python/src/requirements.txt
exit
```

#### 8. Initialise the database schema

```bash
source $HOME/www/python/venv/bin/activate
python3 $HOME/www/python/src/tools/create_schema.py
```

If this is an upgrade of an existing deployment (not a fresh install), run the migration SQL instead:

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < $HOME/www/python/src/tools/migrate_prod_db.sql
```

#### 9. Start the service

```bash
cd ~
toolforge webservice python3.13 start
```

#### 10. Verify

Visit `/meta` to confirm the service is running. Example: https://montage-beta.toolforge.org/meta/

The response should show a recent restart time.

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

#### 3. Pull and rebuild

```bash
cd $HOME/www/python/src
git pull && bash tools/build_frontend.sh
```

`build_frontend.sh` restores `package-lock.json` from git automatically, so this is safe to run on every deploy.

#### 4. Install new Python packages (if any)

Only needed if `requirements.txt` changed:

```bash
toolforge webservice python3.13 shell
~/www/python/venv/bin/pip install -r ~/www/python/src/requirements.txt
exit
```

#### 5. Restart the service

```bash
cd ~
toolforge webservice python3.13 restart
```

#### 6. Verify

Visit `/meta` and confirm the restart time is recent.

---

## Debugging

#### Viewing logs

```bash
tail -50 /data/project/<project>/uwsgi.log
tail -50 /data/project/<project>/montage_api.log
```

#### Running Python / pip commands

Always use the webservice shell — the bastion shell uses a different venv and pip installs there have no effect on the running service:

```bash
toolforge webservice python3.13 shell
pip install -r ~/www/python/src/requirements.txt
python3 -c "import montage.app"
exit
```

#### Restarting the service

Always run from `~`, not from inside the repo:

```bash
cd ~
toolforge webservice python3.13 restart
```

#### Rebuilding the venv from scratch

If the venv is broken (e.g. `pip` is missing, wrong Python version, or packages are corrupted):

```bash
rm -rf ~/www/python/venv
toolforge webservice python3.13 shell
python3 -m venv ~/www/python/venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | ~/www/python/venv/bin/python3
~/www/python/venv/bin/pip install -r ~/www/python/src/requirements.txt
exit
cd ~
toolforge webservice python3.13 restart
```

Note: always use `--without-pip` — `python3 -m venv` with pip hangs in the webservice shell pod.

#### Inspecting the database

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name>
```

```sql
SELECT COUNT(*) FROM entries;
DESCRIBE entries;
```

#### Inspecting a legacy SQLite database (dev only)

There is no `sqlite3` CLI on Toolforge — use Python:

```bash
python3 -c 'import sqlite3; c=sqlite3.connect("tmp_montage.db"); print(c.execute("SELECT COUNT(*) FROM entries").fetchone())'
```
