from __future__ import absolute_import
from __future__ import print_function
import sys
import os.path
import logging

from clastic import Application, StaticFileRoute, MetaApplication

from clastic.static import StaticApplication
from clastic.middleware import HTTPCacheMiddleware
from clastic.middleware.cookie import SignedCookieMiddleware, NEVER
from clastic.render import AshesRenderFactory, render_basic

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from mwoauth import ConsumerToken

from .mw import (UserMiddleware,
                UserIPMiddleware,
                TimingMiddleware,
                LoggingMiddleware,
                ReplayLogMiddleware,
                DBSessionMiddleware,
                MessageMiddleware,
                SQLProfilerMiddleware)
from .rdb import Base, bootstrap_maintainers, ensure_series
from .utils import get_env_name, load_env_config
from .check_rdb import get_schema_errors, ping_connection

from .meta_endpoints import META_API_ROUTES, META_UI_ROUTES
from .juror_endpoints import JUROR_API_ROUTES, JUROR_UI_ROUTES
from .admin_endpoints import ADMIN_API_ROUTES, ADMIN_UI_ROUTES
from .public_endpoints import PUBLIC_API_ROUTES, PUBLIC_UI_ROUTES

import sentry_sdk

from .clastic_sentry import SentryMiddleware
from .cors import CORSMiddleware


DEFAULT_DB_URL = 'sqlite:///tmp_montage.db'
CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)
STATIC_PATH = os.path.join(CUR_PATH, 'static')
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'templates')


def set_mysql_session_charset_and_collation(connection, branch):
    # https://dev.mysql.com/doc/refman/8.0/en/set-names.html
    connection.execute("SET NAMES 'utf8mb4' COLLATE 'utf8mb4_unicode_ci'")
    return


def create_app(env_name='prod', config=None):
    # rendering is handled by MessageMiddleware
    ui_routes = (PUBLIC_UI_ROUTES + JUROR_UI_ROUTES
                 + ADMIN_UI_ROUTES + META_UI_ROUTES)
    api_routes = (PUBLIC_API_ROUTES + JUROR_API_ROUTES
                 + ADMIN_API_ROUTES + META_API_ROUTES)
    print('==  creating WSGI app using env name: %s' % (env_name,))

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

    if config is None:
        config = load_env_config(env_name=env_name)
    print('==  loaded config file: %s' % (config['__file__'],))

    engine = create_engine(config.get('db_url', DEFAULT_DB_URL), pool_recycle=60)
    session_type = sessionmaker()
    session_type.configure(bind=engine)
    tmp_rdb_session = session_type()

    schema_errors = get_schema_errors(Base, tmp_rdb_session)
    if not schema_errors:
        print('++  schema validated ok')
    else:
        for err in schema_errors:
            print('!! ', err)
        print('!!  recreate the database and update the code, then try again')
        sys.exit(2)

    # create maintainer users if they don't exist yet
    musers = bootstrap_maintainers(tmp_rdb_session)
    if musers:
        print('++ created new users for maintainers: %r' % (musers,))

    new_series = ensure_series(tmp_rdb_session)
    if new_series:
        print('++ created new series: %r' % new_series)

    tmp_rdb_session.commit()

    engine.echo = config.get('db_echo', False)

    if not config.get('db_disable_ping'):
        event.listen(engine, 'engine_connect', ping_connection)

    renderer = AshesRenderFactory(TEMPLATES_PATH)

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

    def get_engine():
        db_url = config.get('db_url', DEFAULT_DB_URL)
        engine = create_engine(db_url, pool_recycle=60)
        engine.echo = config.get('db_echo', False)
        if not config.get('db_disable_ping'):
            event.listen(engine, 'engine_connect', ping_connection)

        if 'mysql' in db_url:
            event.listen(engine, 'engine_connect', set_mysql_session_charset_and_collation)

        return engine

    blank_session_type = sessionmaker()

    middlewares = [TimingMiddleware(),
                   UserIPMiddleware(),
                   SQLProfilerMiddleware(),
                   scm_mw,
                   DBSessionMiddleware(blank_session_type, get_engine),
                   UserMiddleware()]
    api_log_path = config.get('api_log_path', 'montage_api.log')
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
                 'root_path': root_path,
                 'ashes_renderer': renderer,
                }

    debug_errors = bool(os.getenv('MONTAGE_PDB', False)) or config['__env__'] == 'devtest'
    api_app = Application(api_routes, resources,
                          middlewares=[MessageMiddleware(debug_errors=debug_errors)] + middlewares,
                          render_factory=render_basic)
    

    ui_app = Application(ui_routes, resources,
                         middlewares=[MessageMiddleware(debug_errors=debug_errors, use_ashes=True)] + middlewares,
                         render_factory=renderer)

    static_app = StaticApplication(STATIC_PATH)

    root_mws = [HTTPCacheMiddleware(use_etags=True)]

    if env_name == 'dev':
        root_mws.append(
            CORSMiddleware(
                allow_origins=[
                    'http://localhost:5173',
                ],
                allow_methods=['GET', 'POST', 'OPTIONS'],
                allow_headers=['Content-Type'],
                allow_credentials=True,
                max_age=3600
            )
        )
    if not debug_errors:
        # don't need sentry if you've got pdb, etc.
        sentry_sdk.init(environment=config['__env__'],
                        max_request_body_size='medium',
                        dsn="https://5738a89dcd5e4b599f7a801fd63bc217@sentry.io/3532775")
        root_mws.append(SentryMiddleware())

    root_app = Application([StaticFileRoute('/', STATIC_PATH + '/index.html'),
                            StaticFileRoute('/a/', STATIC_PATH + '/a/index.html'),
                            ('/', static_app),
                            ('/', ui_app),
                            ('/v1/', api_app),
                            ('/meta', MetaApplication())],
                           resources={'config': config},
                           middlewares=root_mws)


    return root_app
