# -*- coding: utf-8 -*-

import sys
import json
import bisect
import random
import getpass
import os.path
import datetime
from urllib import urlencode
from urllib2 import urlopen
from collections import Counter

import yaml
from clastic.errors import Forbidden, NotFound, BadRequest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from boltons.timeutils import isoparse

from check_rdb import get_schema_errors


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

USER_ENV_MAP = {'tools.montage-dev': 'devlabs',
                'tools.montage': 'prod'}
DEFAULT_ENV_NAME = 'dev'


class PermissionDenied(Forbidden):
    "Raised when users perform actions on the wrong resources"


class DoesNotExist(NotFound):
    "Raised when users perform actions on nonexistent resources"


class InvalidAction(BadRequest):
    "Raised when some user behavior would cause some other assumption to fail"


def encode_dict_to_bytes(query):
    if hasattr(query, 'items'):
        query = query.items()
    for key, value in query:
        yield (encode_value_to_bytes(key), encode_value_to_bytes(value))


def encode_value_to_bytes(value):
    if not isinstance(value, unicode):
        return str(value)
    return value.encode('utf8')


def get_mw_userid(username):
    # Look up the central/global userid based on the username
    # See also: https://commons.wikimedia.org//w/api.php?action=query&format=json&list=globalallusers&meta=&agufrom=Yarl
    api_url = 'https://commons.wikimedia.org/w/api.php?'
    params = {'action': 'query',
              'list': 'users',
              'usprop': 'centralids',
              'ususers': username,
              'format': 'json'}
    resp = urlopen(api_url + urlencode(list(encode_dict_to_bytes(params))))
    data = json.loads(resp.read())
    user_id = data['query']['users'][0].get('centralids', {}).get('CentralAuth')
    if not user_id:
        raise DoesNotExist('user %s does not exist' % username)
    return user_id


def get_threshold_map(values):
    score_counts = Counter([v for v in values])
    thresh_counts = {}
    scores = [0] + list(score_counts)
    for score in scores:
        score = round(score, 3)
        total_gte = sum([v for k, v in score_counts.items() if k >= score])
        thresh_counts[score] = total_gte
    return thresh_counts


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


def format_date(date):
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return date


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
        wcp = wcp.items()
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
