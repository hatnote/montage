# -*- coding: utf-8 -*-

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
  x See the next vote
  x Submit a vote
  x Skip a vote
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

import logging

from clastic import Application, StaticFileRoute, MetaApplication

from clastic.static import StaticApplication
from clastic.middleware.cookie import SignedCookieMiddleware, NEVER
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from mwoauth import ConsumerToken

from mw import (UserMiddleware,
                TimingMiddleware,
                LoggingMiddleware,
                MessageMiddleware,
                ReplayLogMiddleware,
                DBSessionMiddleware)
from rdb import Base, bootstrap_maintainers
from utils import get_env_name
from check_rdb import get_schema_errors, ping_connection

from meta_endpoints import META_ROUTES
from juror_endpoints import JUROR_ROUTES
from admin_endpoints import ADMIN_ROUTES
from public_endpoints import PUBLIC_ROUTES


DEFAULT_DB_URL = 'sqlite:///tmp_montage.db'
CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)
STATIC_PATH = os.path.join(CUR_PATH, 'static')


def create_app(env_name='prod'):
    # rendering is handled by MessageMiddleware
    routes = PUBLIC_ROUTES + JUROR_ROUTES + ADMIN_ROUTES + META_ROUTES

    print '==  creating WSGI app using env name: %s' % (env_name,)

    config_file_name = 'config.%s.yaml' % env_name
    config_file_path = os.path.join(PROJ_PATH, config_file_name)

    print '==  loading config file: %s' % (config_file_path,)

    config = yaml.load(open(config_file_path))

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

    # Recycle connections after 5 minutes, since MySQL is usually configed to kill
    # long running idle connections at some interval. 5 is perhaps too aggressive,
    # but eh. See http://docs.sqlalchemy.org/en/rel_1_0/core/pooling.html#setting-pool-recycle
    # for more details
    # FIXME: Make this configurable
    engine = create_engine(config.get('db_url', DEFAULT_DB_URL), pool_recycle=300)
    session_type = sessionmaker()
    session_type.configure(bind=engine)
    tmp_rdb_session = session_type()

    schema_errors = get_schema_errors(Base, tmp_rdb_session)
    if not schema_errors:
        print '++  schema validated ok'
    else:
        for err in schema_errors:
            print '!! ', err
        print '!!  recreate the database and update the code, then try again'
        sys.exit(2)

    # create maintainer users if they don't exist yet
    musers = bootstrap_maintainers(tmp_rdb_session)
    if musers:
        print '++ created new users for maintainers: %r' % (musers,)
    tmp_rdb_session.commit()

    engine.echo = config.get('db_echo', False)

    if not config.get('db_disable_ping'):
        event.listen(engine, 'engine_connect', ping_connection)

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
                   TimingMiddleware(),
                   scm_mw,
                   DBSessionMiddleware(session_type),
                   UserMiddleware()]
    api_log_path = config.get('api_log_path')
    if api_log_path:
        log_mw = LoggingMiddleware(api_log_path)
        middlewares.insert(0, log_mw)
        # hack
        config['api_exc_log_path'] = getattr(log_mw, 'exc_log_path', None)

    replay_log_path = config.get('replay_log_path')
    if replay_log_path:
        replay_log_mw = ReplayLogMiddleware(replay_log_path)
        middlewares.append(replay_log_mw)

    consumer_token = ConsumerToken(config['oauth_consumer_token'],
                                   config['oauth_secret_token'])

    resources = {'config': config,
                 'consumer_token': consumer_token,
                 'root_path': root_path}

    app = Application(routes, resources, middlewares=middlewares)

    static_app = StaticApplication(STATIC_PATH)

    root_app = Application([StaticFileRoute('/', STATIC_PATH + '/index.html'),
                            ('/', static_app),
                            ('/', app),
                            ('/meta', MetaApplication())])

    return root_app


env_name = get_env_name()
app = create_app(env_name=env_name)


if __name__ == '__main__':
    app.serve()
