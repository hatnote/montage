
from __future__ import absolute_import
import json
import datetime

from clastic import render_basic, GET, POST
from clastic.errors import Forbidden
from boltons.strutils import indent
from boltons.jsonutils import reverse_iter_lines

from .rdb import MaintainerDAO

DEFAULT_LINE_COUNT = 500

# These are populated at the bottom of the module
META_API_ROUTES, META_UI_ROUTES = None, None


def get_meta_routes():
    api = [GET('/maintainer/active_users', get_active_users),
           GET('/logs/audit', get_audit_logs),
           GET('/logs/api', get_api_log_tail, render_basic),
           GET('/logs/api_exc', get_api_exc_log_tail, render_basic),
           GET('/logs/feel', get_frontend_error_log, render_basic),
           POST('/logs/feel', post_frontend_error_log, render_basic)]
    ui = []
    return api, ui


def get_active_users(user_dao):
    maint_dao = MaintainerDAO(user_dao)
    users = maint_dao.get_active_users()
    data = []
    for user in users:
        ud = user.to_details_dict()
        data.append(ud)
    return {'data': data}


def get_audit_logs(user_dao, request):
    """
    Available filters (as query parameters):

    - limit (default 10)
    - offset (default 0)
    - campaign_id
    - round_id
    - action
    """
    limit = request.values.get('limit', 10)
    offset = request.values.get('offset', 0)
    log_campaign_id = request.values.get('campaign_id')
    round_id = request.values.get('round_id')
    log_id = request.values.get('id')
    action = request.values.get('action')

    maint_dao = MaintainerDAO(user_dao)

    audit_logs = maint_dao.get_audit_log(limit=limit,
                                         offset=offset,
                                         campaign_id=log_campaign_id,
                                         round_id=round_id,
                                         log_id=log_id,
                                         action=action)
    data = [l.to_info_dict() for l in audit_logs]
    return {'data': data}


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
    request_dict = request_dict or dict()
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
    err_str = json.dumps(request_dict, sort_keys=True, indent=2)
    err_str = indent(err_str, '  ')
    with open(feel_path, 'a') as feel_file:
        feel_file.write('Begin error at %s:\n\n' % now_str)
        feel_file.write('  + Username: ' + username + '\n')
        feel_file.write(err_str)
        feel_file.write('\n\nEnd error at %s\n\n' % now_str)

    return


def get_frontend_error_log(config, request_dict):
    # TODO
    request_dict = request_dict or dict()
    count = int(request_dict.get('count', DEFAULT_LINE_COUNT))
    feel_path = config.get('feel_log_path', None)
    if not feel_path:
        return ['(no front-end error log configured)']

    return _get_tail_from_path(feel_path, count=count)


META_API_ROUTES, META_UI_ROUTES = get_meta_routes()
