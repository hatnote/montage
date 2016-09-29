
from clastic import render_basic
from clastic.errors import Forbidden
from boltons.jsonutils import reverse_iter_lines


DEFAULT_LINE_COUNT = 500


def get_meta_routes():
    ret = [('/logs/api', get_api_log_tail, render_basic),
           ('/logs/api_exc', get_api_exc_log_tail, render_basic)]
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


META_ROUTES = get_meta_routes()
