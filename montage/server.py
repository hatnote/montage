"""
 - Logging in
 - Health check
 - Coordinators
  x See a list of campaigns
  - Save edits to a campaign
  x See a list of rounds per campaign
  - Save edits to a round
  - Import photos for a round
  - Close out a round
  - Export the output from a round
  - Send notifications to coordinators & jurors (?)
 - Jurors
  - See a list of campaigns and rounds
  - See the next vote
  - Submit a vote
  - Skip a vote
  - Expoert their own votes (?)
  - Change a vote for an open round (?)

Practical design:

Because we're building on react, most URLs return JSON, except for
login and complete_login, which give back redirects, and the root
page, which gives back the HTML basis.

"""
import datetime

import yaml

from clastic import Application, redirect
from clastic.render import render_basic
from clastic.middleware.cookie import SignedCookieMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mwoauth import ConsumerToken, Handshaker, RequestToken

from mw import public, UserMiddleware, DBSessionMiddleware
from rdb import get_all_campaigns, get_round, User, get_campaign_name

WIKI_OAUTH_URL = "https://meta.wikimedia.org/w/index.php"
DEFAULT_DB_URL = 'sqlite:///tmp_montage.db'


@public
def home(cookie, user):
    user_dict = user.to_dict() if user else user
    return {'user': user_dict, 'cookie': dict(cookie)}


@public
def login(request, consumer_token, cookie, root_path):
    handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

    redirect_url, request_token = handshaker.initiate()

    cookie['request_token_key'] = request_token.key
    cookie['request_token_secret'] = request_token.secret

    # TODO: / will break on labs path right?
    cookie['return_to_url'] = request.args.get('next', root_path)
    return redirect(redirect_url)


@public
def logout(request, cookie, root_path):
    cookie.pop('userid', None)
    cookie.pop('username', None)

    return_to_url = request.args.get('next', root_path)

    return redirect(return_to_url)


@public
def complete_login(request, consumer_token, cookie, rdb_session):
    handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

    req_token = RequestToken(cookie['request_token_key'],
                             cookie['request_token_secret'])

    access_token = handshaker.complete(req_token,
                                       request.query_string)
    identity = handshaker.identify(access_token)

    userid = identity['sub']
    username = identity['username']
    user = rdb_session.query(User).filter(User.id == userid).first()
    now = datetime.datetime.utcnow()
    if user is None:
        user = User(id=userid, username=username, last_login_date=now)
        rdb_session.add(user)
    else:
        user.last_login_date = now

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
    del cookie['request_token_key']
    del cookie['request_token_secret']
    del cookie['return_to_url']
    return redirect(return_to_url)


def list_campaigns(rdb_session, user):
    campaigns = get_all_campaigns(rdb_session, user)
    return {'campaigns': [c.to_dict() for c in campaigns]}


def show_campaign_config(rdb_session, user, campaign):
    campaign = get_campaign_config(rdb_session, user, id=campaign)
    return campaign


def show_round_config(rdb_session, user, round):
    round = get_round(rdb_session, user, id=round)
    return round.to_dict()


def campaign_redirect(request, rdb_session, campaign):
    user = request.values.get('user')
    name = get_campaign_name(rdb_session, campaign)
    name = name.replace(' ', '-')
    new_path = '/admin/%s/%s?user=%s' % (campaign, name, user)
    # TODO: remove user here once we have oauth sessions
    return redirect(new_path)


def create_app(env_name='prod'):
    routes = [('/', home, render_basic),
              ('/admin', list_campaigns, render_basic),
              ('/admin/<campaign>', campaign_redirect, render_basic),
              ('/admin/<campaign>/<name>', show_campaign_config, render_basic),
              ('/admin/<campaign>/<name>/<round>', show_round_config, render_basic),
              ('/login', login, render_basic),
              ('/logout', logout, render_basic),
              ('/complete_login', complete_login, render_basic)]

    config_file_name = 'config.%s.yaml' % env_name
    config = yaml.load(open(config_file_name))

    engine = create_engine(config.get('db_url', DEFAULT_DB_URL),
                           echo=config.get('db_echo', False))
    session_type = sessionmaker()
    session_type.configure(bind=engine)

    cookie_secret = config['cookie_secret']
    assert cookie_secret

    root_path = config.get('root_path', '/')

    scm_secure = env_name == 'prod'  # https only in prod
    scm_mw = SignedCookieMiddleware(secret_key=cookie_secret,
                                    path=root_path,
                                    http_only=True,
                                    secure=scm_secure)

    middlewares = [scm_mw,
                   DBSessionMiddleware(session_type),
                   UserMiddleware()]

    consumer_token = ConsumerToken(config['oauth_consumer_token'],
                                   config['oauth_secret_token'])

    resources = {'config': config,
                 'consumer_token': consumer_token,
                 'root_path': root_path}

    app = Application(routes, resources, middlewares=middlewares)
    return app


if __name__ == '__main__':
    app = create_app(env_name="dev")
    app.serve()
