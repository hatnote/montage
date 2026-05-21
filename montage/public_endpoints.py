
from __future__ import absolute_import
import base64
import hashlib
import os
import datetime
import secrets
from urllib.parse import urlencode

import requests as http_requests
from clastic import redirect, render_basic
from clastic.errors import BadRequest
from markdown import Markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from chert import hypertext as html_utils

from .mw import public
from .rdb import User, PublicDAO
from .labs import get_files, get_file_info

from .utils import get_env_name, DoesNotExist, InvalidAction


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = CUR_PATH + '/docs'


def _safe_next(next_url, fallback):
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return next_url
    return fallback

_MW_BASE = 'https://meta.wikimedia.org/w'
_MW_OAUTH2_AUTHORIZE = _MW_BASE + '/rest.php/oauth2/authorize'
_MW_OAUTH2_TOKEN = _MW_BASE + '/rest.php/oauth2/access_token'
_MW_OAUTH2_PROFILE = _MW_BASE + '/rest.php/oauth2/resource/profile'
_MW_USER_AGENT = 'Montage/1.0 (Toolforge tool; https://github.com/hatnote/montage)'

MD_EXTENSIONS = ['markdown.extensions.def_list',
                 'markdown.extensions.footnotes',
                 'markdown.extensions.fenced_code',
                 'markdown.extensions.tables',
                 CodeHiliteExtension(pygments_style='emacs')]

env_name = get_env_name()

def get_public_routes():
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
           ('/campaign', get_all_reports),
           ('/raise', raise_error),
           ('/utils/category', get_file_info_by_category),
           ('/utils/file', get_files_info_by_name)]
    return api, ui


@public
def raise_error():
    raise RuntimeError('testing')


@public
def get_doc(ashes_renderer, path):
    if not path:
        path = ['index']
    render = ashes_renderer('docs/base.html')
    doc_rel_path = '/'.join(path)
    doc_path = DOCS_PATH + '/' + doc_rel_path + '.md'
    doc_path = os.path.normpath(doc_path)
    if not doc_path.startswith(DOCS_PATH):
        raise BadRequest('invalid doc path: %r' % doc_path)
    try:
        doc_md = open(doc_path, 'r').read()
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

    # TODO: cached version
    return render({'title': title, 'body': body_html})


@public
def get_file_info_by_category(request_dict):
    try:
        category_name = request_dict['name']
    except Exception:
        raise InvalidAction('missing name=category_name query parameter')
    files = get_files(category_name)
    return {'file_infos': files}


@public
def get_files_info_by_name(request_dict):
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
def home(cookie, request):
    headers = dict([(k, v) for k, v in
                    request.environ.items() if k.startswith('HTTP_')])
    return {'cookie': dict(cookie),
            'headers': headers}


@public
def login(request, oauth_config, cookie, root_path):
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode()
    state = secrets.token_urlsafe(32)

    cookie['oauth_state'] = state
    cookie['oauth_code_verifier'] = code_verifier
    cookie['return_to_url'] = _safe_next(request.args.get('next'), root_path)

    params = urlencode({
        'response_type': 'code',
        'client_id': oauth_config['client_id'],
        'redirect_uri': oauth_config['redirect_uri'],
        'scope': 'basic',
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    })
    return redirect(_MW_OAUTH2_AUTHORIZE + '?' + params)


@public
def logout(request, cookie, root_path):
    cookie.pop('userid', None)
    cookie.pop('username', None)

    if env_name == 'dev':
        return redirect('http://localhost:5173')

    return_to_url = _safe_next(request.args.get('next'), root_path)
    return redirect(return_to_url)


@public
def complete_login(request, oauth_config, cookie, rdb_session, root_path, api_log, config):
    if config.get('debug'):
        identity = {
            'sub': config.get('debug_userid', 0),
            'username': config.get('debug_username', '__montage_debug__'),
        }
    else:
        state = request.args.get('state', '')
        with api_log.debug('verify_oauth_state') as act:
            if not state or state != cookie.get('oauth_state'):
                act.failure('state mismatch, clearing cookie and redirecting to {}', root_path)
                cookie.set_expires()
                return redirect(root_path)

        code = request.args.get('code', '')
        code_verifier = cookie.get('oauth_code_verifier', '')

        try:
            token_resp = http_requests.post(
                _MW_OAUTH2_TOKEN,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': oauth_config['redirect_uri'],
                    'client_id': oauth_config['client_id'],
                    'client_secret': oauth_config['client_secret'],
                    'code_verifier': code_verifier,
                },
                headers={'User-Agent': _MW_USER_AGENT},
                timeout=10,
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()['access_token']

            profile_resp = http_requests.get(
                _MW_OAUTH2_PROFILE,
                headers={
                    'Authorization': 'Bearer ' + access_token,
                    'User-Agent': _MW_USER_AGENT,
                },
                timeout=10,
            )
            profile_resp.raise_for_status()
            identity = profile_resp.json()
        except Exception as e:
            with api_log.debug('oauth_exchange_failed') as act:
                act.failure('oauth exchange failed: {}', type(e).__name__)
            cookie.set_expires()
            return redirect(root_path)

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

    return_to_url = _safe_next(cookie.get('return_to_url'), root_path)
    for key in ('oauth_state', 'oauth_code_verifier', 'return_to_url'):
        cookie.pop(key, None)

    if env_name == 'dev':
        return_to_url = 'http://localhost:5173'

    return redirect(return_to_url)


@public
def get_series(rdb_session, series_id=None):
    dao = PublicDAO(rdb_session)
    if series_id:
        series = dao.get_series(series_id)
    else:
        series = dao.get_all_series()
    return {'data': [s.to_details_dict() for s in series]}

@public
def get_entry_info(rdb_session, entry_name):
    dao = PublicDAO(rdb_session)
    ret = dao.get_public_entry_info(entry_name)
    return {'data': ret}


@public
def get_report(rdb_session, campaign_id):
    dao = PublicDAO(rdb_session)
    report = dao.get_report(campaign_id)
    if not report:
        raise DoesNotExist('no report for this campaign')
    ctx = report.summary
    ctx['use_ashes'] = True
    return ctx


@public
def get_all_reports(rdb_session):
    dao = PublicDAO(rdb_session)
    reports = dao.get_all_reports()
    return {'data': [r.to_dict() for r in reports]}


PUBLIC_API_ROUTES, PUBLIC_UI_ROUTES = get_public_routes()
