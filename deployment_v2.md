# Montage Deployment

These are instructions for deploying Montage on Toolforge.

## Deploying on Toolforge from scratch
These instructions is only first time when setuping project on Toolforge

##### 1. Get thee OAuth credentials.
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
toolforge webservice node18 shell -m 2G
cd $HOME/www/python/src/frontend
npm install
npm run toolforge:build
exit
```
This will build the vue prod bundle and put in backend's `template` and `static` directory.

##### 5. Create your database
* Get the user name of database (`cat ~/replica.my.cnf`)
* Open up MariaDB with `sql local`
* Create a [Toolforge user database](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database#User_databases) (`create database <user>__<db name>;`), and remember the name for the config

##### 6. Set up the montage config
* Make a copy of `config.default.yaml` for your environment
   * You may need to update `USER_ENV_MAP` in `montage/utils.py` if you need to add a new environment
* Add the `oauth_consumer_token` and `oauth_secret_token` 
* Add a `cookie_secret: <your randome secret>`
* Add the `db_url` with your user database name, and the password from `~/.replica.my.cnf`
    * The format is: `mysql://<user>:<password>@tools.labsdb/<db name>?charset=utf8`
* Add `api_log_path: /data/project/<project>/logs/montage_api.log`
* Add `replay_log_path: /data/project/<project>/logs/montage_replay.log`
* Add `labs_db: True`
* Add `db_echo: False`
* Add `root_path: '/'`
 

##### 7. Creating a virtual environment
```bash
toolforge webservice python3.9 shell
python3 -m venv $HOME/www/python/venv
source $HOME/www/python/venv/bin/activate
pip install --upgrade pip wheel
pip install -r $HOME/www/python/src/requirements.txt
exit
```

##### 8. Start the backend service
```bash
toolforge webservice python3.9 start
```

##### 9. Testing of deployment
* Visit /meta to see the API. Example: https://montage-beta.toolforge.org/meta/


---


## Deploying new changes

If montage is already deployed then you just need following to deploy new changes.

##### 1. Check the instance usage
Login to the tool webapp. Make sure, you are maintainer on the webapp instance. Use the audit log endpoint to check that the instance isn't in active use. Example: https://montage-beta.toolforge.org/v1/logs/audit

This will tell latest usage of instance by audit `create_date`. You can continue if instance is not being used.

##### 2. SSH to Toolforge and then inside tool
```bash
ssh <shell-username>@login.toolforge.org
become montage-beta
```
Here, we are using `montage-beta` instance but it can be `montage` or `montage-dev` as well.

##### 3. Get new changes from remote
```bash
cd $HOME/www/python/src
git pull
```

##### 4. Make the frontend build
```bash
toolforge webservice node18 shell -m 2G
cd $HOME/www/python/src/frontend
npm install
npm run toolforge:build
exit
```

##### 5. (Optional) Install python packages
If you added new python packages in changes then you have to install them in pod.
```bash
toolforge webservice python3.9 shell
source $HOME/www/python/venv/bin/activate
pip install -r $HOME/www/python/src/requirements.txt
exit
```

##### 8. Restart the backend service
```bash
toolforge webservice python3.9 restart
```

##### 9. Testing of deployment
* Visit /meta to see the API. Example: https://montage-beta.toolforge.org/meta/