# Montage Deployment

These are instructions for deploying Montage on Toolforge.

## Deploying on Toolforge from scratch
These instructions is only first time when setuping project on Toolforge

##### 1. Get the OAuth credentials.
[Register your app](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose) and save your consumer token and secret token for later.

##### 2. SSH to Toolforge and then inside tool
```bash
ssh <shell-username>@login.toolforge.org
become montage-beta
```
Here, we are using `montage-beta` instance but it can be `montage` or `montage-dev` as well.

##### 3. Clone the repo as src directory
```bash
mkdir -p $HOME/www/python
cd $HOME/www/python
git clone https://github.com/hatnote/montage.git src
```

##### 4. Make the frontend build
```bash
cd $HOME/www/python/src
bash tools/build_frontend.sh
```
This will build the Vue prod bundle and copy it into the backend's `static/` directory.
The script uses a Toolforge job (node20, 4Gi) and waits for it to finish.
See `tools/build_frontend.sh` for documented workarounds and known issues.

##### 5. Create your database
* Get the username and password from `cat ~/replica.my.cnf`
* Connect to MariaDB:
  ```bash
  mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud
  ```
* Create a [Toolforge user database](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database#User_databases) with `utf8mb4` charset, and remember the name for the config:
  ```sql
  CREATE DATABASE `<user>__<db name>` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;
  EXIT;
  ```

##### 6. Set up the montage config
* Make a copy of `config.default.yaml` for your environment
   * You may need to update `USER_ENV_MAP` in `montage/utils.py` if you need to add a new environment
* Add the `oauth_consumer_token` and `oauth_secret_token` 
* Add a `cookie_secret: <your random secret>`
* Add the `db_url` with your user database name, and the password from `~/.replica.my.cnf`
    * The format is: `mysql+pymysql://<user>:<password>@tools.db.svc.wikimedia.cloud/<db name>?charset=utf8mb4`
* Create the log directory: `mkdir -p /data/project/<project>/logs`
* Add `api_log_path: /data/project/<project>/logs/montage_api.log`
* Add `replay_log_path: /data/project/<project>/logs/montage_replay.log`
* Add `labs_db: True`
* Add `db_echo: False`
* Add `root_path: '/'`
 

##### 7. Creating a virtual environment
```bash
toolforge webservice python3.11 shell
python3 -m venv $HOME/www/python/venv
source $HOME/www/python/venv/bin/activate
pip install --upgrade pip wheel
pip install -r $HOME/www/python/src/requirements.txt
exit
```

##### 8. Initialise the database schema
```bash
cd $HOME/www/python/src
source $HOME/www/python/venv/bin/activate
python3 montage/create_schema.py
```

If this is an upgrade of an existing deployment (not a fresh install), run the migration SQL instead:
```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name> < tools/migrate_prod_db.sql
```

##### 9. Start the backend service
```bash
toolforge webservice python3.11 start
```

##### 10. Testing of deployment
* Visit /meta to see the API. Example: https://montage-beta.toolforge.org/meta/
* In the top section, you should see that the service was restarted in the last few seconds/minutes.


---


## Deploying new changes

If montage is already deployed then you just need following to deploy new changes.

##### 1. Check the instance usage
Login to the tool webapp. Make sure, you are maintainer on the webapp instance. Use the audit log endpoint to check that the instance isn't in active use. Example: https://montage-beta.toolforge.org/v1/logs/audit

This will tell latest usage of instance by audit `create_date`. You can continue if instance is not being used.

Sometimes, instance can in use, but there can be important bugfix and we can push anyways.

##### 2. SSH to Toolforge and then inside tool
```bash
ssh <shell-username>@login.toolforge.org
become montage-beta
```
Here, we are using `montage-beta` instance but it can be `montage` or `montage-dev` as well.

##### 3. Pull changes and rebuild the frontend
```bash
cd $HOME/www/python/src
git pull && bash tools/build_frontend.sh
```
The script restores `package-lock.json` from git automatically, so this command works cleanly on every deploy.

##### 5. (Optional) Install python packages
If you added new python packages in changes then you have to install them in pod.
```bash
toolforge webservice python3.11 shell
source $HOME/www/python/venv/bin/activate
pip install -r $HOME/www/python/src/requirements.txt
exit
```

##### 8. Restart the backend service
```bash
toolforge webservice python3.11 restart
```

##### 9. Testing of deployment
* Visit /meta to see the API. Example: https://montage-beta.toolforge.org/meta/
* In the top section, you should see that the service was restarted in the last few seconds/minutes.


---


## Debugging

##### Viewing logs

The uwsgi log is at:
```bash
tail -50 /data/project/montage-beta/uwsgi.log
```

Note: the log directory is `/data/project/<project>/logs/`, not inside `src/`.

##### Running Python / pip commands

Always run `pip install` and Python diagnostics inside the webservice shell, not the bastion shell. The two environments use different venvs:

```bash
toolforge webservice python3.13 shell
# venv is activated automatically
pip install -r ~/www/python/src/requirements.txt
python3 -c "import montage.app"
exit
```

Running `pip` on the bastion shell installs to a different venv and will not affect the running service.

##### Restarting the service

```bash
toolforge webservice python3.13 restart
```

##### Rebuilding the venv from scratch

If the venv is broken (e.g. `pip` is missing, wrong Python version, or packages are corrupted), wipe it and rebuild:

```bash
rm -rf ~/www/python/venv
toolforge webservice python3.13 shell
python3 -m venv ~/www/python/venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | ~/www/python/venv/bin/python3
~/www/python/venv/bin/pip install -r ~/www/python/src/requirements.txt
exit
toolforge webservice python3.13 restart
```

Note: `python3 -m venv` with pip hangs in the webservice shell pod. Always use `--without-pip` and bootstrap pip via curl as shown above.

##### Inspecting the MariaDB database

Always pass `-h tools.db.svc.wikimedia.cloud` explicitly — there is no local socket on the Toolforge bastion:

```bash
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db name>
```

Example queries:
```sql
SELECT COUNT(*) FROM entries;
DESCRIBE entries;
```

##### Inspecting the SQLite database (legacy / dev only)

Note: montage-beta originally used SQLite and the file (`tmp_montage.db`) may still exist alongside the MariaDB setup. It is no longer used by the running service once the config switches to `mysql+pymysql://`.

There is no `sqlite3` CLI on Toolforge. Use Python instead:

```bash
python3 -c 'import sqlite3; c=sqlite3.connect("/data/project/montage-beta/www/python/src/tmp_montage.db"); print(c.execute("SELECT COUNT(*) FROM entries").fetchone())'
```