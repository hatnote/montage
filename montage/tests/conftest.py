# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os

import pytest
from sqlalchemy import create_engine
from boltons.fileutils import mkdir_p

from montage import utils
from montage.app import create_app, STATIC_PATH
from montage.rdb import Base
from montage.tests.test_web_basic import MontageTestClient


@pytest.fixture
def montage_app(tmpdir):
    config = utils.load_env_config(env_name='devtest')
    config['db_url'] = config['db_url'].replace('///', '///' + str(tmpdir) + '/')
    engine = create_engine(config['db_url'])
    Base.metadata.create_all(engine)

    index_path = STATIC_PATH + '/index.html'
    if not os.path.exists(index_path):
        mkdir_p(STATIC_PATH)
        with open(index_path, 'w') as f:
            f.write('<html><body>just for tests</body></html>')

    return create_app('devtest', config=config)


@pytest.fixture
def api_client(montage_app):
    client = MontageTestClient(montage_app, base_path='/v1')
    client.set_session_cookie(montage_app.resources['config']['dev_local_cookie_value'])
    return client
