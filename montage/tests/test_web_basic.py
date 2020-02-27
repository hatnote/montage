
from __future__ import print_function

import json
import urllib

from werkzeug.test import Client
from lithoxyl import DEBUG, INFO

from montage import utils
from montage.log import script_log
from montage.app import create_app


class ClasticTestClient(Client):
    def __init__(self, app):
        super(ClasticTestClient, self).__init__(app, app.response_type)


# TODO: could use clastic to route-match based on URL to determine
# "role" of current route being tested
class MontageTestClient(object):
    def __init__(self, app, default_role='public', base_path=''):
        self.default_role = default_role
        self.base_path = base_path
        self._test_client = ClasticTestClient(app)
        # TODO: default user?

    def set_session_cookie(self, val):
        self._test_client.set_cookie('', 'clastic_cookie', value=val)

    def get_session_cookie(self):
        # https://github.com/pallets/werkzeug/issues/1060
        # (This is a travesty, I can't believe they closed the issue
        # with this as the recommended pattern)
        for cookie in self._test_client.cookie_jar:
            pass

    def fetch_url(self, url, data=None, act=None, **kw):
        # hyperlinkify url
        su_to = kw.get('su_to')
        if su_to:
            url_su_to = urllib.quote_plus(su_to.encode('utf8'))
            if '?' in url:
                url += '&su_to=' + url_su_to
            else:
                url += '?su_to=' + url_su_to
        if act:
            act['url'] = url
        c = self._test_client
        if data is None:
            res = c.get(url)
        else:
            res = c.post(url, data=data,
                         content_type=kw.get('content_type', 'application/json'))

        if res.status_code != 200:
            error_code = kw.get('error_code')
            if error_code and error_code == res.status_code:
                return res
            print('!! ', res.get_data())
            print()
            import pdb;pdb.set_trace()
            raise AssertionError('got error code %s when fetching %s' % (res.status_code, url))
        return res

    def fetch(self, role_action, url, data=None, **kw):
        if not url.startswith('/'):
            raise ValueError('expected url starting with "/", not: %r' % url)
        role, sep, action = role_action.partition(':')
        role, action = (role, action) if sep else (self.default_role, role)
        print('>>', action, 'as', role)
        as_user = kw.pop('as_user', None)
        if as_user:
            print('(%s)' % as_user)
        else:
            print()
        url = self.base_path + url if self.base_path else url

        log_level = kw.pop('log_level', INFO)
        error_code = kw.pop('error_code', None)
        if kw:
            raise TypeError('unexpected kwargs: %r' % kw.keys())

        with script_log.action(log_level, 'fetch_url') as act:
            resp = self.fetch_url(url,
                                  data=data,
                                  su_to=as_user,
                                  error_code=error_code,
                                  act=act)
        # TODO: the following should be replaced with an internal
        # assert (along with the coupled status code check in
        # fetch_url)
        if error_code and resp is True:
            return True
        if not resp.content_type.startswith('application/json'):
            return resp
        data = resp.get_data()
        data_dict = json.loads(data)
        try:
            assert data_dict['status'] == 'success'
        except AssertionError:
            print('!! did not successfully load %s' % url)
            print('  got: ', data_dict)
            import pdb;pdb.set_trace()
            raise
        return data_dict


def _create_schema(db_url, echo=True):
    from sqlalchemy import create_engine
    from montage.rdb import Base

    engine = create_engine(db_url, echo=echo)
    Base.metadata.create_all(engine)

    return


def test_home_client():
    config = utils.load_env_config(env_name='devtest')
    db_url = config.get('db_url')
    _create_schema(db_url=db_url)

    app = create_app('devtest')

    client = MontageTestClient(app)
    from clastic.middleware.cookie import JSONCookie
    cookie = JSONCookie({'userid': 6024474, 'username': 'Slaporte'}, secret_key=config['cookie_secret'])
    cookie_data = cookie.serialize()

    client.set_session_cookie(cookie_data)
    fetch = client.fetch

    fetch('organizer: home', '/')

    api_client = MontageTestClient(app, base_path='/v1/')  # TODO
    api_client.set_session_cookie(config['dev_local_cookie_value'])
    fetch = api_client.fetch

    resp = fetch('organizer: create a new series',
                 '/admin/add_series',
                 {'name': 'test series',
                  'description': 'test',
                  'url': 'test'})

    resp = fetch('get list of all series', '/series')

    most_recent_series = resp['data'][-1]['id']
    resp = fetch('organizer: cancel most recent series',
                 '/admin/series/%s/edit' % most_recent_series,
                 {'status': 'cancelled'})
