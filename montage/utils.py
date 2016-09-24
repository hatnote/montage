
import sys
import json
import getpass
import os.path
import datetime
from urllib import urlencode
from urllib2 import urlopen

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from check_rdb import get_schema_errors


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

USER_ENV_MAP = {'tools.montage-dev': 'devlabs',
                'tools.montage': 'prod'}
DEFAULT_ENV_NAME = 'dev'


def get_mw_userid(username):
    # Look up the central/global userid based on the username
    # See also: https://commons.wikimedia.org//w/api.php?action=query&format=json&list=globalallusers&meta=&agufrom=Yarl
    api_url = 'https://commons.wikimedia.org/w/api.php?'
    params = {'action': 'query',
              'list': 'users',
              'usprop': 'centralids',
              'ususers': username,
              'format': 'json'}
    resp = urlopen(api_url + urlencode(params))
    data = json.loads(resp.read())
    user_id = data['query']['users'][0].get('centralids', {}).get('CentralAuth')
    if not user_id:
        raise RuntimeError('user %s does not exist' % username)
    return user_id


def get_env_name():
    username = getpass.getuser()
    return USER_ENV_MAP.get(username, DEFAULT_ENV_NAME)


def load_env_config(env_name=None):
    if not env_name:
        env_name = get_env_name()

    config_file_name = 'config.%s.yaml' % env_name
    config_file_path = os.path.join(PROJ_PATH, config_file_name)

    # print '==  loading config file: %s' % (config_file_path,)

    config = yaml.load(open(config_file_path))

    return config


def check_schema(db_url, base_type, echo=False, autoexit=False):
    engine = create_engine(db_url, echo=echo)
    session_type = sessionmaker()
    session_type.configure(bind=engine)

    # import pdb;pdb.set_trace()

    tmp_rdb_session = session_type()
    schema_errors = get_schema_errors(base_type, tmp_rdb_session)
    if not schema_errors:
        print '++  schema validated ok'
    else:
        for err in schema_errors:
            print '!! ', err
        print '!!  recreate the database and update the code, then try again'
        if autoexit:
            sys.exit(2)
    return schema_errors


def fmt_date(date):
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return date
