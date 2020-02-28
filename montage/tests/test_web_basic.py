# -*- coding: utf-8 -*-

from __future__ import print_function

import json
import urllib

import pytest
from werkzeug.test import Client
from lithoxyl import DEBUG, INFO
from clastic.middleware.cookie import JSONCookie

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
            # TODO: careful, werkzeug's pretty liberal with "data",
            # will take a dictionary and do weird stuff to it, turn it
            # into a formencoded mess.
            if not isinstance(data, (bytes, unicode)):
                data = json.dumps(data)
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
        as_user = kw.pop('as_user', None)
        print('>>', action, 'as', role, end='')
        print((' (%s)' % as_user) if as_user else '')
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


@pytest.fixture
def montage_app(tmpdir):
    config = utils.load_env_config(env_name='devtest')
    config['db_url'] = config['db_url'].replace('///', '///' + str(tmpdir) + '/')
    db_url = config['db_url']
    _create_schema(db_url=db_url)

    app = create_app('devtest', config=config)
    return app


@pytest.fixture
def base_client(montage_app):
    client = MontageTestClient(montage_app)

    # TODO
    cookie = JSONCookie({'userid': 6024474, 'username': 'Slaporte'},
                        secret_key=montage_app.resources['config']['cookie_secret'])
    cookie_data = cookie.serialize()
    client.set_session_cookie(cookie_data)

    return client


@pytest.fixture
def api_client(montage_app):
    api_client = MontageTestClient(montage_app, base_path='/v1/')  # TODO
    api_client.set_session_cookie(montage_app.resources['config']['dev_local_cookie_value'])
    return api_client


def test_home_client(base_client, api_client):
    fetch = base_client.fetch

    fetch('organizer: home', '/')

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


    resp = fetch('maintainer: add organizer',
                 '/admin/add_organizer',
                 {'username': 'Yarl'})

    resp = fetch('maintainer: add another organizer, to be removed later',
                 '/admin/add_organizer',
                 {'username': 'Slaporte (WMF)'})

    resp = fetch('maintainer: remove organizer',
                 '/admin/remove_organizer',
                 {'username': 'Slaporte (WMF)'})

    resp = fetch('get default series', '/series')
    series_id = resp['data'][0]['id']

    data = {'name': 'Another Test Campaign 2017 - again',
            'coordinators': [u'LilyOfTheWest',
                             u'Slaporte',
                             u'Yarl'],
            'close_date': '2015-10-01 17:00:00',
            'url': 'http://hatnote.com',
            'series_id': series_id}
    resp = fetch('organizer: create campaign',
                 '/admin/add_campaign',
                 data,
                 as_user='Yarl')

    resp = fetch('coordinator: get admin view (list of all campaigns/rounds)',
                 '/admin', as_user='LilyOfTheWest')

    campaign_id = resp['data'][-1]['id']

    resp = fetch('coordinator: get campaign detail view',
                 '/admin/campaign/%s' % campaign_id,
                 as_user='LilyOfTheWest')

    data = {'name': 'A demo campaign 2016',
            'open_date': "2015-09-01 17:00:00",  # UTC times,
            'close_date': None}
    resp = fetch('coordinator: edit campaign',
                 '/admin/campaign/%s/edit' % campaign_id,
                 data, as_user='Yarl')

    resp = fetch('add frontend error log',
                 '/logs/feel',
                 {'error': 'TypologyError', 'stack': 'some text\nstack\netc.'},
                 as_user='LilyOfTheWest')
    resp = fetch('get frontend error log',
                 '/logs/feel',
                 as_user='LilyOfTheWest')

    # note: you can also add coordinators when the round is created
    resp = fetch('coordinator: add coordinator to campaign',
                 '/admin/campaign/%s/add_coordinator' % campaign_id,
                 {'username': 'Effeietsanders'},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: remove coordinator',
                 '/admin/campaign/%s/remove_coordinator' % campaign_id,
                 {'username': 'Effeietsanders'},
                 as_user='LilyOfTheWest')

    # for date inputs (like deadline_date below), the default format
    # is %Y-%m-%d %H:%M:%S  (aka ISO8601)
    # Add a round to a campaign
    rnd_data = {'name': 'Test yes/no round ნ',
                'vote_method': 'yesno',
                'quorum': 3,
                'deadline_date': "2016-10-15T00:00:00",
                'jurors': [u'Slaporte',
                           u'MahmoudHashemi',
                           u'Effeietsanders',
                           u'Jean-Frédéric',
                           u'LilyOfTheWest'],
                # a round will have these config settings by default
                'config': {'show_link': True,
                           'show_filename': True,
                           'show_resolution': True,
                           'dq_by_upload_date': True,
                           'dq_by_resolution': False,
                           'dq_by_uploader': True,
                           'min_resolution': 2000000,  # 2 megapixels
                           'dq_coords': True,
                           'dq_organizers': True,
                           'dq_maintainers': True}}

    resp = fetch('coordinator: add round to a campaign',
                 '/admin/campaign/%s/add_round' % campaign_id,
                 rnd_data,
                 as_user='LilyOfTheWest')

    round_id = resp['data']['id']

    resp = fetch('coordinator: get round details',
                 '/admin/round/%s' % round_id,
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: edit round details',
                 '/admin/round/%s/edit' % round_id,
                 {'directions': 'these are new directions'},
                 as_user='LilyOfTheWest')

    rnd = fetch('coordinator: get round config',
                '/admin/round/%s' % round_id,
                as_user='LilyOfTheWest')
    config = rnd['data']['config']
    config['show_filename'] = False
    resp = fetch('coordinator: edit round config',
                 '/admin/round/%s/edit' % round_id,
                 {'config': config},
                 as_user='LilyOfTheWest')

    data = {'import_method': 'category',
            'category': 'Images_from_Wiki_Loves_Monuments_2015_in_Albania'}
    resp = fetch('coordinator: import entries from a category',
                 '/admin/round/%s/import' % round_id,
                 data, as_user='LilyOfTheWest')

    resp = fetch('coordinator: activate a round',
                 '/admin/round/%s/activate' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')
    """
    # Cancel a round
    # - as coordinator
    resp = fetch('coordinator: cancel a round',
                 '/admin/round/%s/cancel' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')
    """

    resp = fetch('coordinator: pause a round',
                 '/admin/round/%s/pause' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')




    gsheet_url = 'https://docs.google.com/spreadsheets/d/1WzHFg_bhvNthRMwNmxnk010KJ8fwuyCrby29MvHUzH8/edit#gid=550467819'
    resp = fetch('coordinator: import more entries from different gsheet csv into an existing round',
                 '/admin/round/%s/import' % round_id,
                 {'import_method': 'csv', 'csv_url': gsheet_url},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: import files selected by name',
                 '/admin/round/%s/import' % round_id,
                 {'import_method': 'selected', 'file_names': ['Reynisfjara, Suðurland, Islandia, 2014-08-17, DD 164.JPG']},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: preview disqualifications',
                 '/admin/round/%s/preview_disqualification' % round_id,
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: disqualify by resolution',
                 '/admin/round/%s/autodisqualify' % round_id,
                 {'dq_by_resolution': True},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: view disqualified entries',
                 '/admin/round/%s/disqualified' % round_id,
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: reactivate the round',
                 '/admin/round/%s/activate' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')
