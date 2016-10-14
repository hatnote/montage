
import json
import datetime

from clastic import render_basic, GET, POST
from clastic.errors import Forbidden
from boltons.strutils import indent
from boltons.jsonutils import reverse_iter_lines


DEFAULT_LINE_COUNT = 500


def get_meta_routes():
    ret = [('/logs/api', get_api_log_tail, render_basic),
           ('/logs/api_exc', get_api_exc_log_tail, render_basic),
           GET('/logs/feel', get_frontend_error_log, render_basic),
           POST('/logs/feel', post_frontend_error_log, render_basic)]
    return ret


def get_api_log_tail(config, user, request_dict):
    if not user.is_maintainer:
        raise Forbidden()
    request_dict = request_dict or {}
    count = int(request_dict.get('count', DEFAULT_LINE_COUNT))

    log_path = config.get('api_log_path')
    if not log_path:
        return ['(no API log path configured)']

    lines = _get_tail_from_path(log_path, count=count)

    return lines


def get_api_exc_log_tail(config, user, request_dict):
    if not user.is_maintainer:
        raise Forbidden()
    request_dict = request_dict or {}
    count = int(request_dict.get('count', DEFAULT_LINE_COUNT))

    log_path = config.get('api_exc_log_path')
    if not log_path:
        return ['(no API exception log path configured)']
    lines = _get_tail_from_path(log_path, count=count)

    return lines


def _get_tail_from_path(path, count=DEFAULT_LINE_COUNT):
    log_path = open(path, 'rb')

    rliter = reverse_iter_lines(log_path)
    lines = []
    for i, line in enumerate(rliter):
        if i > count:
            break
        lines.append(line)
    lines.reverse()
    return lines


def post_frontend_error_log(user, config, request_dict):
    feel_path = config.get('feel_log_path', None)
    if not feel_path:
        return ['(no front-end error log configured)']
    now = datetime.datetime.utcnow()
    now_str = now.isoformat()

    username = user.username if user else '<nouser>'
    err_bytes = json.dumps(request_dict, sort_keys=True, indent=2)
    err_bytes = indent(err_bytes, '  ')
    with open(feel_path, 'ab') as feel_file:
        feel_file.write('Begin error at %s:\n\n' % now_str)
        feel_file.write('  + Username: ' + username + '\n')
        feel_file.write(err_bytes)
        feel_file.write('\n\nEnd error at %s\n\n' % now_str)

    return


def get_frontend_error_log(config, request_dict):
    # TODO
    count = int(request_dict.get('count', DEFAULT_LINE_COUNT))
    feel_path = config.get('feel_log_path', None)
    if not feel_path:
        return ['(no front-end error log configured)']

    return _get_tail_from_path(feel_path, count=count)


META_ROUTES = get_meta_routes()
