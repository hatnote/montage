# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
import bisect
import random
import getpass
import os.path
import datetime
from urllib.parse import urlencode
from typing import Any, Generator, Sequence, TypeVar, Union

import yaml
import requests
from clastic.errors import Forbidden, NotFound, BadRequest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from boltons.timeutils import isoparse

from .check_rdb import get_schema_errors

T = TypeVar('T')

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

USER_ENV_MAP = {'tools.montage-dev': 'devlabs',
                'tools.montage': 'prod',
                'tools.montage-beta': 'beta'}
DEFAULT_ENV_NAME = 'dev'
USER_AGENT = 'montage/25.0 (https://github.com/hatnote/montage; mahmoud@hatnote.com)'


def requests_get(url: str, **kwargs: Any) -> requests.Response:
    """Wrapper for requests.get that adds User-Agent header"""
    headers = kwargs.pop('headers', {})
    headers.setdefault('User-Agent', USER_AGENT)
    return requests.get(url, headers=headers, **kwargs)


def requests_post(url: str, **kwargs: Any) -> requests.Response:
    """Wrapper for requests.post that adds User-Agent header"""
    headers = kwargs.pop('headers', {})
    headers.setdefault('User-Agent', USER_AGENT)
    return requests.post(url, headers=headers, **kwargs)


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


def to_unicode(obj: Any) -> str:
    return str(obj)


def encode_dict_to_bytes(query: Union[dict, list]) -> Generator[tuple[bytes, Any], None, None]:
    if hasattr(query, 'items'):
        query = list(query.items())

    for key, value in query:
        if isinstance(value, list):
            yield (encode_value_to_bytes(key), [encode_value_to_bytes(v) for v in value])
        yield (encode_value_to_bytes(key), encode_value_to_bytes(value))


def encode_value_to_bytes(value: Any) -> bytes:
    if not isinstance(value, str):
        return str(value).encode('utf8')
    return value.encode('utf8')


def get_mw_userid(username: str) -> int:
    # Look up the central/global userid based on the username
    api_url = 'https://commons.wikimedia.org/w/api.php?'
    params = {'action': 'query',
              'list': 'globalallusers',
              'agufrom': username,
              'format': 'json'}
    full_url = api_url + urlencode(list(encode_dict_to_bytes(params)))
    resp = requests_get(full_url)
    data = resp.json()
    user = data['query']['globalallusers'][0]
    if user['name'] == username:
        user_id = int(user['id'])
    else:
        raise DoesNotExist('user %s does not exist' % username)
    return user_id


def get_threshold_map(ratings_map: dict[Union[str, float], Union[str, int]]) -> dict[float, int]:
    thresh_counts = {}
    # coerce some types
    typed_ratings_map = dict([(float(k), int(v)) for k, v in ratings_map.items()])
    typed_ratings_map[0.0] = typed_ratings_map.get(0.0, 0)
    typed_ratings_map[1.0] = typed_ratings_map.get(1.0, 0)
    for rating in sorted(typed_ratings_map.keys()):
        total_gte = sum([v for k, v in typed_ratings_map.items() if k >= rating])
        rating_key = int(rating * 1000) / 1000.0
        thresh_counts[rating_key] = total_gte
    return thresh_counts


def get_env_name() -> str:
    env = os.environ.get('MONTAGE_ENV')
    if env:
        return env
    try:
        username = getpass.getuser()
    except Exception:
        raise RuntimeError(
            'MONTAGE_ENV is not set and getpass.getuser() failed '
            '(LDAP is unavailable in container environments). '
            'Set MONTAGE_ENV via toolforge envvars.'
        )
    return USER_ENV_MAP.get(username, DEFAULT_ENV_NAME)


DEVTEST_CONFIG = {'oauth_client_id': None,
                  'oauth_client_secret': None,
                  'oauth_redirect_uri': None,
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


def _load_config_from_env(env_name):
    def _bool(key, default=False):
        val = os.environ.get(key)
        return val.lower() in ('1', 'true', 'yes') if val is not None else default

    required = {
        'oauth_client_id': 'MONTAGE_OAUTH_CLIENT_ID',
        'oauth_client_secret': 'MONTAGE_OAUTH_CLIENT_SECRET',  # pragma: allowlist secret
        'oauth_redirect_uri': 'MONTAGE_OAUTH_REDIRECT_URI',
        'cookie_secret': 'MONTAGE_COOKIE_SECRET',
        'db_url': 'MONTAGE_DB_URL',
    }
    config = {}
    missing = [envvar for key, envvar in required.items() if not os.environ.get(envvar)]
    if missing:
        raise ValueError(
            'Missing required environment variables: ' + ', '.join(missing)
        )
    for key, envvar in required.items():
        config[key] = os.environ[envvar]

    superusers_raw = os.environ.get('MONTAGE_SUPERUSERS', '')
    superusers = [u.strip() for u in superusers_raw.split(',') if u.strip()]
    config.update({
        'superusers': superusers,
        'db_echo': _bool('MONTAGE_DB_ECHO'),
        'debug': _bool('MONTAGE_DEBUG'),
    })
    if config['debug'] and env_name in ('prod', 'beta', 'devlabs'):
        raise ValueError(
            'MONTAGE_DEBUG=true is not permitted in env %r. '
            'Unset MONTAGE_DEBUG or change MONTAGE_ENV to dev.' % env_name
        )
    config.update({
        'labs_db': _bool('MONTAGE_LABS_DB', True),
        'root_path': os.environ.get('MONTAGE_ROOT_PATH', '/'),
        'api_log_path': os.environ.get('MONTAGE_API_LOG_PATH', 'montage_api.log'),
        'replay_log_path': os.environ.get('MONTAGE_REPLAY_LOG_PATH'),
        'feel_log_path': os.environ.get('MONTAGE_FEEL_LOG_PATH'),
        '__env__': env_name,
        '__file__': 'environment',
    })
    return config


def load_env_config(env_name: str | None = None) -> dict[str, Any]:
    if not env_name:
        env_name = get_env_name()
    elif env_name == 'devtest':
        return dict(DEVTEST_CONFIG)

    if os.environ.get('MONTAGE_OAUTH_CLIENT_ID'):
        return _load_config_from_env(env_name)

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


def load_default_series() -> dict[str, str]:
    return DEFAULT_SERIES


def check_schema(db_url: str, base_type: Any, echo: bool = False, autoexit: bool = False) -> list[str]:
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


def format_date(date: datetime.datetime | str | None) -> str | None:
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return date


def js_isoparse(date_str: str) -> datetime.datetime:
    try:
        ret = isoparse(date_str)
    except ValueError:
        # It may be a javascript Date object printed with toISOString()
        if date_str[-1] == 'Z':
            date_str = date_str[:-1]
        ret = isoparse(date_str)
    return ret


def json_serial(obj: Any) -> str | list[Any]:
    if isinstance(obj, (datetime.datetime, datetime.date)):
        serial = obj.isoformat()
        return serial
    elif isinstance(obj, set):
        return list(obj)
    raise TypeError("type %s not serializable" % type(obj))


def parse_date(date: str | None) -> datetime.datetime | None:
    if date is None:
        return None
    return isoparse(date)


# The following is almost ready to go to boltons

def weighted_choice(weighted_choices: Sequence[tuple[float, T]] | dict[float, T]) -> T:
    nsw_list, vals = process_weighted_choices(weighted_choices)
    if len(vals) == 1:
        return vals[0]
    return fast_weighted_choice(nsw_list, vals)


def process_weighted_choices(wcp: Sequence[tuple[float, T]] | dict[float, T]) -> tuple[Sequence[float], Sequence[T]]:
    if not wcp:
        raise ValueError('expected weight-choice list or map, not %r' % wcp)
    if isinstance(wcp, dict):
        wcp_list = list(wcp.items())
    else:
        wcp_list = list(wcp)
    if any([p[0] < 0 for p in wcp_list]):
        raise ValueError('weight cannot be less than 0')
    total = float(sum([p[0] for p in wcp_list], 0.0))
    if not total:
        raise ValueError()
    norm_pairs = [(k / total, v) for k, v in wcp_list]
    norm_pairs.sort(key=lambda x: x[0], reverse=True)

    summed_pairs = []
    bound = 0.0
    for delta, val in norm_pairs:
        summed_pairs.append((bound, val))
        bound += delta

    summed_sorted_weights, vals = zip(*summed_pairs)
    return (summed_sorted_weights, vals)


def fast_weighted_choice(nsw: Sequence[float], values: Sequence[T]) -> T:
    return values[bisect.bisect(nsw, random.random()) - 1]
