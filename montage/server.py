"""
 - Logging in
 - Health check
 - Admins
  - See a list of campaigns
  - Save edits to a campaign
  - See a list of rounds per campaign
  - Save edits to a round
  - Import photos for a round
  - Close out a round
  - Export the output from a round
  - Send notifications to admins (?)
 - Jurors
  - See a list of campaigns and rounds
  - See the next vote
  - Submit a vote
  - Skip a vote
  - Expoert their own votes (?)
  - Change a vote for an open round (?)
"""

import yaml

from clastic import Application, Middleware, redirect
from clastic.render import render_basic
from clastic.middleware.cookie import SignedCookieMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mwoauth import ConsumerToken, Handshaker, RequestToken

from rdb import get_campaign, get_all_campaigns, get_round

WIKI_OAUTH_URL = "https://meta.wikimedia.org/w/index.php"


def home(cookie):
    return {'test': True, 'cookie': dict(cookie)}


def login(request, consumer_token, cookie):
    handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

    redirect_url, request_token = handshaker.initiate()

    cookie['request_token_key'] = request_token.key
    cookie['request_token_secret'] = request_token.secret

    # TODO: / will break on labs path right?
    cookie['return_to_url'] = request.args.get('next', '/')
    return redirect(redirect_url)


# TODO: redirecter middleware for auth stuff


def complete_login(request, consumer_token, cookie):
    handshaker = Handshaker(WIKI_OAUTH_URL, consumer_token)

    req_token = RequestToken(cookie['request_token_key'],
                             cookie['request_token_secret'])

    access_token = handshaker.complete(req_token,
                                       request.query_string)
    cookie['access_token_key'] = access_token.key
    cookie['access_token_secret'] = access_token.secret
    identity = handshaker.identify(access_token)

    # wiki_uid = identity['sub']
    # user = g.conn.session.query(User).filter(User.wiki_uid == wiki_uid).first()
    # if user is None:
    #    user = User(username=identity['username'], wiki_uid=wiki_uid)
    #    g.conn.session.add(user)
    #    g.conn.session.commit()

    cookie['wiki_userid'] = identity['sub']
    cookie['wiki_username'] = identity['username']

    return_to_url = cookie.get('return_to_url')
    del cookie['request_token_key']
    del cookie['request_token_secret']
    return redirect(return_to_url)


def list_campaigns(request, rdb_session):
    user = request.values.get('user')
    campaigns = get_all_campaigns(rdb_session, user)
    return {'campaigns': [c.to_dict() for c in campaigns]}


def get_campaign_admin(request, rdb_session, campaign):
    user = request.values.get('user')
    campaign = get_campaign(rdb_session, user, id=campaign)
    return campaign.to_dict()


def get_round_admin(request, rdb_session, round, campaign=None):
    user = request.values.get('user')
    round = get_round(rdb_session, user, id=round)
    return round.to_dict()


def preview_selection(rdb_session, round, campaign=None):
    return


class UserMiddleware(Middleware):
    provides = ('user',)


class DBSessionMiddleware(Middleware):
    provides = ('rdb_session',)

    def __init__(self, session_type):
        self.session_type = session_type

    def request(self, next):
        return next(rdb_session=self.session_type())


def create_app():
    routes = [('/', home, render_basic),
              ('/admin', list_campaigns, render_basic),
              ('/admin/<campaign>', get_campaign_admin, render_basic),
              ('/admin/<campaign>/<round>', get_round_admin, render_basic),
              ('/admin/<campaign>/<round>/preview',
               preview_selection,
               render_basic),
              ('/login', login, render_basic),
              ('/complete_login', complete_login, render_basic)]

    engine = create_engine('sqlite:///tmp_montage.db', echo=True)
    session_type = sessionmaker()
    session_type.configure(bind=engine)

    config = yaml.load(open('config.dev.yaml'))
    cookie_secret = config['cookie_secret']
    assert cookie_secret

    middlewares = [SignedCookieMiddleware(secret_key=cookie_secret),
                   DBSessionMiddleware(session_type)]

    consumer_token = ConsumerToken(config['oauth_consumer_token'],
                                   config['oauth_secret_token'])

    resources = {'config': config, 'consumer_token': consumer_token}

    app = Application(routes, resources, middlewares=middlewares)
    return app


if __name__ == '__main__':
    app = create_app()
    app.serve()
