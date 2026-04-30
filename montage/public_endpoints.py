# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import datetime
from typing import Any, Callable

from clastic import redirect, render_basic, Response
from clastic.errors import BadRequest
from mwoauth import Handshaker, RequestToken
from markdown import Markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from chert import hypertext as html_utils
from sqlalchemy import text

from .mw import public
from .rdb import User, PublicDAO
from .labs import get_files, get_file_info

from .utils import get_env_name, DoesNotExist, InvalidAction


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = os.path.join(CUR_PATH, 'docs')

WIKI_OAUTH_URL = "https://meta.wikimedia.org/w/index.php"

MD_EXTENSIONS = ['markdown.extensions.def_list',
                 'markdown.extensions.footnotes',
                 'markdown.extensions.fenced_code',
                 'markdown.extensions.tables',
                 CodeHiliteExtension(pygments_style='emacs')]

env_name = get_env_name()


def get_public_routes() -> tuple[list[Any], list[Any]]:
    ui = [('/', home),
          ('/login', login),
          ('/logout', logout),
          ('/complete_login', complete_login),
          ('/campaign/<campaign_id:int>', get_report, 'report.html'),
          ('/docs/<path*>', get_doc, render_basic)]
    api = [('/campaign', get_all_reports),
           ('/series/<series_id?int>', get_series),
           ('/series', get_series),
           ('/entry/<entry_name:str>', get_entry_info),
           ('/raise', raise_error),
           ('/utils/category', get_file_info_by_category),
           ('/utils/file', get_files_info_by_name),
           ('/health', get_health)]
    return api, ui


@public
def raise_error() -> None:
    raise RuntimeError('testing')


@public
def get_health(rdb_session: Any) -> dict[str, str]:
    """Basic health check to verify database connectivity."""
    try:
        rdb_session.execute(text('SELECT 1'))
        return {'status': 'healthy', 'db': 'ok'}
    except Exception as e:
        return {'status': 'unhealthy', 'db': str(e)}


@public
def get_doc(ashes_renderer: Callable, path: list[str]) -> Response:
    if not path:
        path = ['index']
    render = ashes_renderer('docs/base.html')
    doc_rel_path = '/'.join(path)
    doc_path = os.path.join(DOCS_PATH, f'{doc_rel_path}.md')
    doc_path = os.path.normpath(doc_path)
    
    if not doc_path.startswith(DOCS_PATH):
        raise BadRequest('invalid doc path: %r' % doc_path)
    
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            doc_md = f.read()
    except OSError:
        raise BadRequest('could not open doc: %r' % doc_rel_path)

    lines = doc_md.splitlines()
    if not lines:
        raise BadRequest('empty doc: %r' % doc_rel_path)
    
    title_line, body_md = lines[0], '\n'.join(lines[1:])
    _, sep, title = title_line.partition('#')
    if not sep or not title:
        raise BadRequest('bad doc title. expected "# Title", not: %r'
                         % title_line)

    md_converter = Markdown(extensions=MD_EXTENSIONS)
    body_html = md_converter.convert(body_md)

    html_tree = html_utils.html_text_to_tree(body_html)
    html_utils.retarget_links(html_tree)
    html_utils.add_toc(html_tree)
    body_html = html_utils.html_tree_to_text(html_tree)

    return render({'title': title.strip(), 'body': body_html})


@public
def get_file_info_by_category(request_dict: dict[str, Any]) -> dict[str, list[Any]]:
    try:
        category_name = request_dict['name']
    except Exception:
        raise InvalidAction('missing name=category_name query parameter')
    files = get_files(category_name)
    return {'file_infos': files}


@public
def get_files_info_by_name(request_dict: dict[str, Any]) -> dict[str, list[Any]]:
    try:
        file_names = request_dict['names']
    except Exception:
        raise InvalidAction('must provide a list of names')
    files = []
    no_info = []
    for file_name in file_names:
        file_info = get_file_info(file_name)
        if not file_info:
            no_info.append(file_name)
        else:
            files.append(file_info)
    return {'file_infos': files,
            'no_info': no_info}


@public
def home(cookie: dict[str, Any], request: Any) -> dict[str, Any]:
    headers = dict([(k, v) for k, v in
                    request.environ.items() if k.startswith('HTTP_')])
    return {'cookie': dict(cookie),
            'headers': headers}


@public
def login(request: Any, consumer_token: Any, cookie: dict[str, Any], root_path: str) -> Response:
    handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

    redirect_url, request_token = handshaker.initiate()

    cookie['request_token_key'] = request_token.key
    cookie['request_token_secret'] = request_token.secret

    cookie['return_to_url'] = request.args.get('next', root_path)
    return redirect(redirect_url)


@public
def logout(request: Any, cookie: dict[str, Any], root_path: str) -> Response:
    cookie.pop('userid', None)
    cookie.pop('username', None)

    if env_name == 'dev':
        return redirect('http://localhost:5173')

    return_to_url = request.args.get('next', root_path)
    return redirect(return_to_url)


@public
def complete_login(request: Any, consumer_token: Any, cookie: dict[str, Any], rdb_session: Any, root_path: str, api_log: Any, config: dict[str, Any]) -> Response:
    # Standardised debug impersonation: only allowed in dev and if explicitly enabled
    is_dev = env_name == 'dev'
    allow_impersonation = config.get('allow_impersonation', False)
    
    if is_dev and allow_impersonation:
        identity = {'sub': 6024474,
                    'username': 'Slaporte'}
    else:
        handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

        with api_log.debug('load_login_cookie') as act:
            try:
                rt_key = cookie['request_token_key']
                rt_secret = cookie['request_token_secret']
            except KeyError:
                act.failure('clearing stale cookie, redirecting to {}', root_path)
                cookie.set_expires()
                return redirect(root_path)

        req_token = RequestToken(rt_key, rt_secret)

        access_token = handshaker.complete(req_token,
                                           request.query_string)
        identity = handshaker.identify(access_token)

    userid = identity['sub']
    username = identity['username']
    user = rdb_session.query(User).filter(User.id == userid).first()
    now = datetime.datetime.utcnow()
    if user is None:
        user = User(id=userid, username=username, last_active_date=now)
        rdb_session.add(user)
    else:
        user.last_active_date = now

    cookie['userid'] = identity['sub']
    cookie['username'] = identity['username']

    return_to_url = cookie.get('return_to_url')
    
    if not (is_dev and allow_impersonation):
        cookie.pop('request_token_key', None)
        cookie.pop('request_token_secret', None)
        cookie.pop('return_to_url', None)
    else:
        return_to_url = '/'

    if env_name == 'dev':
        return_to_url = 'http://localhost:5173'

    return redirect(return_to_url)


@public
def get_series(rdb_session: Any, series_id: int | None = None) -> dict[str, list[Any]]:
    dao = PublicDAO(rdb_session)
    if series_id:
        series = dao.get_series(series_id)
    else:
        series = dao.get_all_series()
    return {'data': [s.to_details_dict() for s in series]}


@public
def get_entry_info(rdb_session: Any, entry_name: str) -> dict[str, Any]:
    dao = PublicDAO(rdb_session)
    ret = dao.get_public_entry_info(entry_name)
    return {'data': ret}


@public
def get_report(rdb_session: Any, campaign_id: int) -> dict[str, Any]:
    dao = PublicDAO(rdb_session)
    report = dao.get_report(campaign_id)
    if not report:
        raise DoesNotExist('no report for this campaign')
    ctx = report.summary
    ctx['use_ashes'] = True
    return ctx


@public
def get_all_reports(rdb_session: Any) -> dict[str, list[Any]]:
    dao = PublicDAO(rdb_session)
    reports = dao.get_all_reports()
    return {'data': [r.to_dict() for r in reports]}


PUBLIC_API_ROUTES, PUBLIC_UI_ROUTES = get_public_routes()
