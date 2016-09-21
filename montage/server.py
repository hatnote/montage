"""x Logging in
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

Because we're building on angular, most URLs return JSON, except for
login and complete_login, which give back redirects, and the root
page, which gives back the HTML basis.

# A bit of TBI design

We add privileged Users (with coordinator flag enabled). Coordinators
can create Campaigns, and see and interact only with Campaigns they've
created or been added to. Can Coordinators create other Coordinators?

"""
import sys
import os.path

import yaml

from clastic import Application, GET, POST

from clastic.static import StaticApplication
from clastic.middleware.cookie import SignedCookieMiddleware, NEVER
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mwoauth import ConsumerToken

from mw import (UserMiddleware,
                MessageMiddleware,
                DBSessionMiddleware)
from rdb import Base
from check_rdb import get_schema_errors

from juror_endpoints import (get_juror_round,
                             get_juror_rounds,
                             get_juror_campaign)
from admin_endpoints import (create_campaign,
                             edit_campaign,
                             create_round,
                             edit_round,
                             get_admin_index,
                             get_admin_round,
                             get_admin_campaign)

from public_endpoints import home, login, logout, complete_login


DEFAULT_DB_URL = 'sqlite:///tmp_montage.db'
CUR_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(CUR_PATH, 'static')


def create_app(env_name='prod'):
    # rendering is handled by MessageMiddleware
    routes = [('/', home),
              ('/login', login),
              ('/logout', logout),
              ('/complete_login', complete_login),
              GET('/admin/overview',
                  get_admin_index),
              POST('/admin/campaign',
                   create_campaign),
              GET('/admin/campaign/<campaign_id:int>/<camp_name?>',
                  get_admin_campaign),
              POST('/admin/campaign/<campaign_id:int>/<camp_name?>',
                   edit_campaign),
              POST('/admin/round',
                   create_round),
              GET('/admin/round/<round_id:int>/<round_name?>',
                  get_admin_round),
              POST('/admin/round/<round_id:int>/<round_name?>',
                   edit_round),
              GET('/juror/campaign',
                  get_juror_rounds),
              GET('/juror/campaign/<campaign_id:int>/<camp_name?>',
                  get_juror_campaign),
              GET('/juror/round',
                  get_juror_rounds),
              GET('/juror/round/<round_id:int>/<round_name?>',
                  get_juror_round)]

    config_file_name = 'config.%s.yaml' % env_name
    config = yaml.load(open(config_file_name))

    engine = create_engine(config.get('db_url', DEFAULT_DB_URL))
    session_type = sessionmaker()
    session_type.configure(bind=engine)

    # import pdb;pdb.set_trace()

    tmp_rdb_session = session_type()
    schema_errors = get_schema_errors(Base, tmp_rdb_session)
    if not schema_errors:
        print '++  schema validated ok'
    else:
        for err in schema_errors:
            print '!! ', err
        print '!!  recreate the database and update the code, then try again'
        sys.exit(2)

    engine.echo = config.get('db_echo', False)

    cookie_secret = config['cookie_secret']
    assert cookie_secret

    root_path = config.get('root_path', '/')

    scm_secure = env_name == 'prod'  # https only in prod
    scm_mw = SignedCookieMiddleware(secret_key=cookie_secret,
                                    path=root_path,
                                    http_only=True,
                                    secure=scm_secure)
    if not scm_secure:
        scm_mw.data_expiry = NEVER

    middlewares = [MessageMiddleware(),
                   scm_mw,
                   DBSessionMiddleware(session_type),
                   UserMiddleware()]

    consumer_token = ConsumerToken(config['oauth_consumer_token'],
                                   config['oauth_secret_token'])

    resources = {'config': config,
                 'consumer_token': consumer_token,
                 'root_path': root_path}

    app = Application(routes, resources, middlewares=middlewares)

    static_app = StaticApplication(STATIC_PATH)

    root_app = Application([('/', app),
                            ('/static/', static_app)])

    return root_app


if __name__ != '__main__':
    # generally imported for serving, ideally this would be side-effect free
    app = create_app(env_name="prod")
else:
    app = create_app(env_name="dev")
    app.serve()
