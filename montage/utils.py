# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
import sys
import bisect
import random
import getpass
import os.path
import datetime
from six.moves.urllib.parse import urlencode


import yaml
import requests
from clastic.errors import Forbidden, NotFound, BadRequest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from boltons.timeutils import isoparse

from .check_rdb import get_schema_errors
import six

try:
    unicode = unicode
    basestring = basestring
except NameError:
    unicode = str
    basestring = str


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

USER_ENV_MAP = {'tools.montage-dev': 'devlabs',
                'tools.montage': 'prod',
                'tools.montage-beta': 'beta'}
DEFAULT_ENV_NAME = 'dev'


class MontageError(Exception):
    "A base type for expected errors."


class PermissionDenied(MontageError, Forbidden):
    "Raised when users perform actions on the wrong resources"


class DoesNotExist(MontageError, NotFound):
    "Raised when users perform actions on nonexistent resources"


class InvalidAction(MontageError, BadRequest):
    "Raised when some user behavior would cause some other assumption to fail"


class NotImplementedResponse(MontageError, BadRequest, NotImplementedError):
    "Raised when a feature hasn't yet been implemented"


DEFAULT_SERIES = {'name': 'Unofficial',
                  'description': 'For unofficial campaigns, whether for testing or just for fun!',
                  'url': 'TODO add docs url'}  # TODO: status is always active


def to_unicode(obj):
    try:
        return unicode(obj)
    except UnicodeDecodeError:
        return unicode(obj, encoding='utf8')


def encode_dict_to_bytes(query):
    if hasattr(query, 'items'):
        query = list(query.items())

    for key, value in query:
        if isinstance(value, list):
            yield (encode_value_to_bytes(key), [encode_value_to_bytes(v) for v in value])
        yield (encode_value_to_bytes(key), encode_value_to_bytes(value))


def encode_value_to_bytes(value):
    if not isinstance(value, unicode):
        return str(value)
    return value.encode('utf8')


def get_mw_userid(username):
    # Look up the central/global userid based on the username
    api_url = 'https://commons.wikimedia.org/w/api.php?'
    params = {'action': 'query',
              'list': 'globalallusers',
              'agufrom': username,
              'format': 'json'}
    full_url = api_url + urlencode(list(encode_dict_to_bytes(params)))
    resp = requests.get(full_url)
    data = resp.json()
    user = data['query']['globalallusers'][0]
    if user['name'] == username:
        user_id = int(user['id'])
    else:
        raise DoesNotExist('user %s does not exist' % username)
    return user_id


def get_threshold_map(ratings_map):
    thresh_counts = {}
    # coerce some types
    ratings_map = dict([(float(k), int(v)) for k, v in ratings_map.items()])
    ratings_map[0.0] = ratings_map.get(0.0, 0)
    ratings_map[1.0] = ratings_map.get(1.0, 0)
    for rating in sorted(ratings_map.keys()):
        total_gte = sum([v for k, v in ratings_map.items() if k >= rating])
        rating_key = int(rating * 1000) / 1000.0
        thresh_counts[rating_key] = total_gte
    return thresh_counts


def get_env_name():
    username = getpass.getuser()
    return USER_ENV_MAP.get(username, DEFAULT_ENV_NAME)


DEVTEST_CONFIG = {'oauth_consumer_token': None,
                  'oauth_secret_token': None,
                  'cookie_secret': 'supertotallyrandomsecretcookiesecret8675309',
                  'api_log_path': 'montage_api.log',
                  'replay_log_path': 'montage_replay.log',
                  'feel_log_path': 'montage_feel.log',
                  'db_url': "sqlite:///tmp_montage.db",
                  'db_echo': False,
                  'debug': True,
                  'superusers': ['Slaporte', 'MahmoudHashemi'],
                  'dev_local_cookie_value': '"W7XGXxmUjl4kbkE0TWaFo4Oth50=?userid=NjAyNDQ3NA==&username=IlNsYXBvcnRlIg=="',
                  '__file__': 'devtest-builtin',
                  '__env__': 'devtest',
}


def load_env_config(env_name=None):
    if not env_name:
        env_name = get_env_name()
    elif env_name == 'devtest':
        return dict(DEVTEST_CONFIG)

    config_file_name = 'config.%s.yaml' % env_name
    config_file_path = os.path.join(PROJ_PATH, config_file_name)

    try:
        config = yaml.safe_load(open(config_file_path))
    except Exception:
        print('!! failed to load config file: %s' % (config_file_path,))
        raise

    config['__env__'] = env_name
    config['__file__'] = config_file_path
    return config


def load_default_series():
    return DEFAULT_SERIES


def check_schema(db_url, base_type, echo=False, autoexit=False):
    engine = create_engine(db_url, echo=echo)
    session_type = sessionmaker()
    session_type.configure(bind=engine)

    # import pdb;pdb.set_trace()

    tmp_rdb_session = session_type()
    schema_errors = get_schema_errors(base_type, tmp_rdb_session)
    if not schema_errors:
        print('++  schema validated ok')
    else:
        for err in schema_errors:
            print('!! ', err)
        print('!!  recreate the database and update the code, then try again')
        if autoexit:
            sys.exit(2)
    return schema_errors


def format_date(date):
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return date


def js_isoparse(date_str):
    try:
        ret = isoparse(date_str)
    except ValueError:
        # It may be a javascript Date object printed with toISOString()
        if date_str[-1] == 'Z':
            date_str = date_str[:-1]
        ret = isoparse(date_str)
    return ret


def json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        serial = obj.isoformat()
        return serial
    elif isinstance(obj, set):
        return list(obj)
    raise TypeError("type %s not serializable" % type(obj))


def parse_date(date):
    if date is None:
        return None
    return isoparse(date)


# The following is almost ready to go to boltons

def weighted_choice(weighted_choices):
    nsw_list, vals = process_weighted_choices(weighted_choices)
    if len(vals) == 1:
        return vals[0]
    return fast_weighted_choice(nsw_list, vals)


def process_weighted_choices(wcp):
    if not wcp:
        raise ValueError('expected weight-choice list or map, not %r' % wcp)
    if isinstance(wcp, dict):
        wcp = list(wcp.items())
    else:
        wcp = list(wcp)
    if any([p[0] < 0 for p in wcp]):
        raise ValueError('weight cannot be less than 0')
    total = float(sum([p[0] for p in wcp], 0.0))
    if not total:
        raise ValueError()
    norm_pairs = [(k / total, v) for k, v in wcp]
    norm_pairs.sort(key=lambda x: x[0], reverse=True)

    summed_pairs = []
    bound = 0.0
    for delta, val in norm_pairs:
        summed_pairs.append((bound, val))
        bound += delta

    summed_sorted_weights, vals = zip(*summed_pairs)
    return (summed_sorted_weights, vals)


def fast_weighted_choice(nsw, values):
    return values[bisect.bisect(nsw, random.random()) - 1]
