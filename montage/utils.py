
import json
import getpass
import datetime

from urllib import urlencode
from urllib2 import urlopen


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


def fmt_date(date):
    if isinstance(date, datetime.datetime):
        date =  date.isoformat()
    return date
