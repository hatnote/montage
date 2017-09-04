
import os
import datetime

from clastic import redirect, render_basic
from clastic.errors import BadRequest
from mwoauth import Handshaker, RequestToken
from markdown import Markdown
from markdown.extensions.codehilite import CodeHiliteExtension

from mw import public
from rdb import User, PublicDAO
from labs import get_files, get_file_info

from utils import load_env_config, DoesNotExist, InvalidAction

config = load_env_config()
DEBUG = config.get('debug', False)

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = CUR_PATH + '/docs'

WIKI_OAUTH_URL = "https://meta.wikimedia.org/w/index.php"

MD_EXTENSIONS = ['markdown.extensions.def_list',
                 'markdown.extensions.footnotes',
                 'markdown.extensions.fenced_code',
                 'markdown.extensions.tables',
                 CodeHiliteExtension(pygments_style='emacs')]


def get_public_routes():
    ret = [('/', home),
           ('/login', login),
           ('/logout', logout),
           ('/complete_login', complete_login),
           ('/series/<series_id?int>', get_series),
           ('/series', get_series),
           ('/campaign/<campaign_id:int>', get_report,
            'report.html'),
           ('/campaign', get_all_reports),
           ('/docs/<path*>', get_doc, render_basic),
           ('/utils/category', get_file_info_by_category),
           ('/utils/file', get_files_info_by_name)]
    return ret


@public
def get_doc(ashes_renderer, path):
    if not path:
        path = ['index']
    render = ashes_renderer('docs/base.html')
    doc_path = DOCS_PATH + '/' + '/'.join(path) + '.md'
    doc_path = os.path.normpath(doc_path)
    if not doc_path.startswith(DOCS_PATH):
        raise BadRequest('invalid doc path: %r' % doc_path)
    try:
        doc_md = open(doc_path, 'rb').read()
    except OSError:
        raise BadRequest('could not open doc: %r' % '/'.join(path))
    md_converter = Markdown(extensions=MD_EXTENSIONS)
    content = md_converter.convert(doc_md)
    # TODO: cached version
    return render({'content': content})


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
    for file_name in file_names:
        file_info = get_file_info(file_name)
        files.append(file_info)
    return {'file_infos': files}


@public
def home(cookie, request):
    headers = dict([(k, v) for k, v in
                    request.environ.items() if k.startswith('HTTP_')])
    return {'cookie': dict(cookie),
            'headers': headers}


@public
def login(request, consumer_token, cookie, root_path):
    handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

    redirect_url, request_token = handshaker.initiate()

    cookie['request_token_key'] = request_token.key
    cookie['request_token_secret'] = request_token.secret

    cookie['return_to_url'] = request.args.get('next', root_path)
    return redirect(redirect_url)


@public
def logout(request, cookie, root_path):
    cookie.pop('userid', None)
    cookie.pop('username', None)

    return_to_url = request.args.get('next', root_path)

    return redirect(return_to_url)


@public
def complete_login(request, consumer_token, cookie, rdb_session, root_path):
    # TODO: Remove or standardize the DEBUG option
    if DEBUG:
        identity = {'sub': 6024474,
                    'username': 'Slaporte'}
    else:
        handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

        try:
            rt_key = cookie['request_token_key']
            rt_secret = cookie['request_token_secret']
        except KeyError:
            # in some rare cases, stale cookies are left behind
            # and users have to click login again
            # TODO: clear cookie and redirect home instead
            # redirect(root_path)
            return BadRequest('Invalid cookie. Try clearing your cookies'
                              ' and logging in again.')

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

    # These would be useful when we have oauth beyond simple ID, but
    # they should be stored in the database along with expiration times.
    # ID tokens only last 100 seconds or so
    # cookie['access_token_key'] = access_token.key
    # cookie['access_token_secret'] = access_token.secret

    # identity['confirmed_email'] = True/False might be interesting
    # for contactability through the username. Might want to assert
    # that it is True.

    cookie['userid'] = identity['sub']
    cookie['username'] = identity['username']

    return_to_url = cookie.get('return_to_url')
    # TODO: Clean up
    if not DEBUG:
        del cookie['request_token_key']
        del cookie['request_token_secret']
        del cookie['return_to_url']
    else:
        return_to_url = '/'
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


PUBLIC_ROUTES = get_public_routes()
