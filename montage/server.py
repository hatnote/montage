"""
 x Logging in
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
  x See a list of campaigns and rounds
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
import os.path
import datetime

import yaml

from clastic import Application, SubApplication, redirect
from clastic.static import StaticApplication
from clastic.render import render_basic, render_json
from clastic.middleware.cookie import SignedCookieMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from boltons.strutils import slugify
from mwoauth import ConsumerToken, Handshaker, RequestToken

from mw import public, UserMiddleware, DBSessionMiddleware
from rdb import User


WIKI_OAUTH_URL = "https://meta.wikimedia.org/w/index.php"
DEFAULT_DB_URL = 'sqlite:///tmp_montage.db'
CUR_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(CUR_PATH, 'static')


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


def admin_camp_redirect(user_dao, campaign_id, correct_name=None):
    if not correct_name:
        correct_name = user_dao.get_campaign_name(campaign_id)
    correct_name = correct_name.replace(' ', '-')
    new_path = '/admin/campaign/%s/%s' % (campaign_id, correct_name)
    return redirect(new_path)


def admin_round_redirect(user_dao, round_id, correct_name=None):
    if not correct_name:
        correct_name = user_dao.get_round_name(round_id)
    correct_name = correct_name.replace(' ', '-')
    new_path = '/admin/round/%s/%s' % (round_id, correct_name)
    return redirect(new_path)


def admin_landing(user_dao):
    campaigns = user_dao.get_all_campaigns()
    data = []
    for campaign in campaigns:
        campaign_info = get_campaign_admin_info(user_dao, campaign.id)
        data.append(campaign_info)
    return {'data': data}


def get_campaign_admin_info(user_dao, campaign_id):
    campaign = user_dao.get_campaign_config(campaign_id)
    info = {'id': campaign.id,
            'name': campaign.name,
            'rounds': [],
            'coords': [u.username for u in campaign.coords]}
    for round in campaign.rounds:
        info['rounds'].append(get_round_admin_info(user_dao, round.id))
    return info


def get_round_admin_info(user_dao, round_id):
    round = user_dao.get_round_config(round_id)
    #entries_info = user_dao.get_entry_info(round_id) # TODO
    info = {'id': round.id,
            'name': round.name,
            'voteMethod': round.vote_method,
            'status': round.status,
            'jury': [u.username for u in round.jurors],
            'quorum': round.quorum,
            'sourceInfo': {
                'entryCount': None,
                'uploadersCount': None,
                'roundSource': 'round',
                'roundSource': {'id': None,
                                'title': None}},
            'endDate': round.close_date, # TODO: use clse_date or endDate?
            'campaign': round.campaign_id
    }
    return info


def admin_camp_dashboard(user_dao, campaign_id, camp_name):
    correct_name = user_dao.get_campaign_name(campaign_id)
    if camp_name != correct_name.replace(' ', '-'):
        return admin_camp_redirect(user_dao, campaign_id, correct_name)
    data = get_campaign_admin_info(user_dao, campaign_id)
    return {'data': data}


def admin_round_dashboard(user_dao, round_id, round_name):
    correct_name = user_dao.get_round_name(round_id)
    if round_name != correct_name.replace(' ', '-'):
        return admin_round_redirect(user_dao, round_id, correct_name)
    data = get_round_admin_info(user_dao, round_id)
    return {'data': data}


def juror_camp_redirect(user_dao, campaign_id, correct_name=None):
    if not correct_name:
        correct_name = user_dao.get_campaign_name(campaign_id)
    correct_name = correct_name.replace(' ', '-')
    new_path = '/campaign/%s/%s' % (campaign_id, correct_name)
    return redirect(new_path)


def juror_round_redirect(user_dao, round_id, correct_name=None):
    if not correct_name:
        correct_name = user_dao.get_round_name(round_id)
    correct_name = correct_name.replace(' ', '-')
    new_path = '/round/%s/%s' % (round_id, correct_name)
    return redirect(new_path)


def juror_landing(user_dao):
    # TODO: add top-level wrapper
    rounds = user_dao.get_all_rounds()
    return rounds


def juror_camp_dashboard(user_dao, campaign_id, camp_name):
    # TODO: add top-level wrapper
    correct_name = user_dao.get_campaign_name(campaign_id)
    if camp_name != correct_name.replace(' ', '-'):
        return juror_camp_redirect(user_dao, campaign_id, correct_name)
    campaign = user_dao.get_campaign(campaign_id)
    return campaign


def juror_round_dashboard(user_dao, round_id, round_name):
    # TODO: add top-level wrapper
    correct_name = user_dao.get_round_name(round_id)
    if round_name != correct_name.replace(' ', '-'):
        return juror_round_redirect(user_dao, round_id, correct_name)
    round = user_dao.get_round(round_id)
    return round.to_dict()


def create_app(env_name='prod'):
    routes = [('/', home, render_basic),
              ('/admin', admin_landing, render_json),
              ('/admin/campaign', admin_landing, render_json),
              ('/admin/campaign/<campaign_id>', admin_camp_redirect,
               render_json),
              ('/admin/campaign/<campaign_id>/<camp_name>',
               admin_camp_dashboard, render_json),
              ('/admin/round', admin_landing, render_json),
              ('/admin/round/<round_id>', admin_round_redirect,
               render_json),
              ('/admin/round/<round_id>/<round_name>', admin_round_dashboard,
               render_json),
              ('/campaign', juror_landing, render_basic),
              ('/campaign/<campaign_id>', juror_camp_redirect, render_basic),
              ('/campaign/<campaign_id>/<camp_name>', juror_camp_dashboard,
               render_basic),
              ('/round', juror_landing, render_basic),
              ('/round/<round_id>', juror_round_redirect, render_basic),
              ('/round/<round_id>/<round_name>', juror_round_dashboard,
               render_basic),
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

    static_app = StaticApplication(STATIC_PATH)
    app.add(('/static/', static_app))

    return app


if __name__ == '__main__':
    app = create_app(env_name="dev")
    app.serve(use_meta=False)
