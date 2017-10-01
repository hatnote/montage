# Montage deployment instructions

These are basic instructions to deploy montage on Toolforge.

## 1. Set up the Toolforge project

 - Visit [toolsadmin](https://toolsadmin.wikimedia.org/tools/)

## 2. Set up the OAuth credentials.
 
 - [Register your app](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose)
 - Save your consumer token and secret token for later -- you will need these for the config (step 5).

## 3. In the Toolforge project, clone the montage repo

## 4. Create your database

 - Open up MariaDB with `sql local` (or `mysql --defaults-file=~/replica.my.cnf`)
 - Create a [Toolforge user database](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database#User_databases) (`create database <user>__<db name>;`), and remember the name for the config (step 5)

## 5. Set up montage config
 
 - Make a copy of `config.default.yaml` for your environment
   * You may need to update `USER_ENV_MAP` in `montage/utils.py` if you need to detect a new environment
 - Add the `oauth_consumer_token` and `oauth_secret_token` from step 2
 - Add a `cookie_secret: <your secret>`
 - Add the `db_url` with your user database name from step 4, and the password from `~/.replica.my.cnf`
    * The format is: `mysql://<user>:<password>@tools.labsdb/<db name>?charset=utf8`
 - Add `api_log_path: /data/project/<project>/logs/montage_api.log`
 - Add `replay_log_path: /data/project/<project>/logs/montage_replay.log`
 - Add `labs_db: True`
 - Add `db_echo: False`
 - Add `root_path: '/<project>/'`

## 6. Setting up Toolforge:

The project will look like this:

```
/data/projects/<project>/<montage repo, with app.py>
/data/projects/<project>/www/python/uwsgi.ini
/data/projects/<project>/www/python/src -> <montage repo, with app.py>
/data/projects/<project>/www/python/venv
```

 - Create `~/logs`
 - Create `~/www/python`
 - Enter the kubernetes (k8s) python2 shell with `webservice --backend=kubernetes python2 shell`. While in the k8s shell:
   * In `~/www/python`, create a virtualenv with `virtualenv venv`
   * In the virtualenv, install the Python requirements with `pip install -r ~/montage/requirements.txt`
   * Run `python montage/tools/create_schema.py` (you're done with the k8s shell for now)
 - Link `~/www/python/src` to the montage repo
   * Create `~/www/python/src/app.py`
 - Create `~/www/python/uwsgi.ini`
 - Add the venv to `.bash_profile` for ease of use -- `source ~/www/python/venv/bin/activate`

## 7. Build the front end

(it's probably easier to do this locally, and then move to labs)

In `montage/client`...

 - Install node dependencies with `npm install` 
 - Set your environment with `export NODE_ENV=<local,dev,beta,etc>` -- if you're creating a new env, create `montage/client/src/index_<env>.ejs`
 - Build the client with `npm run build`
 - Copy `montage/montage/static/dist` and `montage/montage/static/index.html` to your Toolforge project

## 8. Start the webservice 

 - Run `webservice --backend=kubernetes python2 start`
 - Investigate `~/uwsgi.log` for errors

## Testing
 
 - Visit /meta to see the API
 - **Full test**
   * Make sure your username is set as `superuser` in the remote version config
   * Log into the remote version of montage, open your cookies, and copy the value from your `clastic_cookie`
   * In the config for a local version of montage, add your `clastic_cookie` value to `dev_remote_cookie_value`
   * Run `python run_server_test.py --remote --url <url>`
