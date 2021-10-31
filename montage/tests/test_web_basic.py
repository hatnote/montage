# -*- coding: utf-8 -*-

from __future__ import print_function

from __future__ import absolute_import
import os
import json
import six.moves.urllib.parse, six.moves.urllib.error
from pprint import pprint

import pytest
from werkzeug.test import Client
from lithoxyl import DEBUG, INFO
from clastic.middleware.cookie import JSONCookie
from boltons.fileutils import mkdir_p
from glom import glom, T

from montage import utils
from montage.log import script_log
from montage.app import create_app, STATIC_PATH
from montage.utils import unicode


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
            url_su_to = six.moves.urllib.parse.quote_plus(su_to.encode('utf8'))
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
            raise TypeError('unexpected kwargs: %r' % list(kw.keys()))

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

    index_path = STATIC_PATH + '/index.html'
    if not os.path.exists(index_path):
        mkdir_p(STATIC_PATH)
        with open(index_path, 'w') as f:
            f.write('<html><body>just for tests</body></html>')

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
    api_client = MontageTestClient(montage_app, base_path='/v1')  # TODO
    api_client.set_session_cookie(montage_app.resources['config']['dev_local_cookie_value'])
    return api_client


def test_home_client(base_client, api_client):

    resp = base_client.fetch('organizer: home', '/')
    #resp = base_client.fetch('public: login', '/login')

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

    resp = fetch('organizer: list users',
                 '/admin/users')

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
    rnd_data = {'name': 'Test yes/no round',
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

    discarded_round_id = resp['data']['id']

    resp = fetch('coordinator: cancel round',
                 '/admin/round/%s/cancel' % discarded_round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: re-add round to a campaign',
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


    resp = fetch('coordinator: pause round',
                 '/admin/round/%s/pause' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: edit jurors in a round',
                 '/admin/round/%s/edit' % round_id,
                 data={'new_jurors': [u'Slaporte',
                                      u'MahmoudHashemi',
                                      u'Effeietsanders',
                                      u'Jean-Frédéric',
                                      u'Jimbo Wales']},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: raise quorum value',
                 '/admin/round/%s/edit' % round_id,
                 {'quorum': 4},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: try to reduce quorum (not supported)',
                 '/admin/round/%s/edit' % round_id,
                 {'quorum': 1},
                 as_user='LilyOfTheWest',
                 error_code=400)

    resp = fetch('coordinator: reactivate our round',
                 '/admin/round/%s/activate' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')


    resp = fetch('juror: get votes stats for yes/no round',
                 '/juror/round/%s/votes-stats' % round_id,
                 as_user='Slaporte')
    assert 'yes' in resp['stats']
    assert 'no' in resp['stats']

    resp = fetch('maintainer: view audit logs', '/logs/audit')

    # Jury endpoints
    # --------------

    resp = fetch('juror: get the juror overview',
                 '/juror', as_user='Slaporte')

    # TODO: Jurors only see a list of rounds at this point, so there
    # is no need to get the detailed view of campaign.

    # Get a detailed view of a campaign
    resp = fetch('juror: get campaign details',
                 '/juror/campaign/%s' % campaign_id,
                 as_user='Jimbo Wales')

    resp = fetch('juror: get round details',
                 '/juror/round/%s' % round_id,
                 as_user='Jimbo Wales')

    resp = fetch("juror: get juror's open tasks",
                 '/juror/round/%s/tasks' % round_id,
                 as_user='Jimbo Wales')

    # note: will return a default of 15 tasks, but you can request
    # more or fewer with the count parameter, or can skip tasks with
    # an offset paramter

    # entry_id = resp['data']['tasks'][0]['round_entry_id']
    tasks = resp['data']['tasks']
    vote_id = tasks[0]['id']

    resp = fetch('juror: submit a single rating task',
                 '/juror/round/%s/tasks/submit' % round_id,
                 {'ratings': [{'vote_id': vote_id, 'value': 1.0}]},
                 as_user='Jimbo Wales')

    skip_vote_id = tasks[1]['id']
    resp = fetch('juror: skip a rating',
                 '/juror/round/%s/tasks/skip' % round_id,
                 {'vote_id': skip_vote_id},
                 as_user='Jimbo Wales')

    entry_id = tasks[-1]['entry']['id']
    resp = fetch('juror: mark an entry as favorite',
                 '/juror/round/%s/%s/fave' % (round_id, entry_id),
                 {'post': True},
                 as_user='Jimbo Wales')

    resp = fetch("juror: get list of own faves",
                 '/juror/faves', as_user='Jimbo Wales')

    resp = fetch('juror: unfave a favorite',
                 '/juror/round/%s/%s/unfave' % (round_id, entry_id),
                 {'post': True}, as_user='Jimbo Wales')

    resp = fetch('juror: flag an entry',
                 '/juror/round/%s/%s/flag' % (round_id, entry_id),
                 {'reason': 'I really do not like this photo, I am sorry.'},
                 as_user='Jimbo Wales')

    resp = fetch('coordinator: get list of flagged files',
                 '/admin/round/%s/flags' % (round_id),
                 as_user='LilyOfTheWest')

    entry_id = resp['data'][0]['id']
    resp = fetch('coordinator: pause round for manual disqualification',
                 '/admin/round/%s/pause' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: disqualify particular file',
                 '/admin/round/%s/%s/disqualify' % (round_id, entry_id),
                 {'post': True},
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: requalify (undisqualify) particular file',
                 '/admin/round/%s/%s/requalify' % (round_id, entry_id),
                 {'post': True},                 as_user='LilyOfTheWest')


    resp = fetch('coordinator: reactivate the round to continue',
                 '/admin/round/%s/activate' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')

    # Attempt to submit or get tasks while the round is paused

    # Pause the round
    resp = fetch('coordinator: pause round for submission-during-paused test',
                 '/admin/round/%s/pause' % round_id,
                 {'post': True},
                 as_user='LilyOfTheWest')

    vote_id = tasks[-1]['id']

    resp = fetch('juror: submit rating during paused round',
                 '/juror/round/%s/tasks/submit' % round_id,
                 {'ratings': [{'vote_id': vote_id, 'value': 1.0}]},
                 as_user='Jimbo Wales',
                 error_code=400)

    resp = fetch('juror: attempt to get more tasks from paused round',
                 '/juror/round/%s/tasks' % round_id,
                 as_user='Jimbo Wales',
                 error_code=400)

    resp = fetch('coordinator: reactivate round',
                 '/admin/round/%s/activate' % round_id,
                 {'post': True}, as_user='LilyOfTheWest')

    resp = fetch('juror: confirm getting more tasks works again',
                 '/juror/round/%s/tasks' % round_id,
                 as_user='Jimbo Wales')

    rating_dicts = []

    for vote in resp['data']['tasks']:
        val = float(vote['id'] % 2)  # deterministic but arbitrary
        rating_dicts.append({'vote_id': vote['id'], 'value': val})
    data = {'ratings': rating_dicts}

    resp = fetch('juror: submit rating tasks',
                 '/juror/round/%s/tasks/submit' % round_id,
                 data, as_user='Jimbo Wales')

    resp = fetch('juror: get list of past ratings',
                 '/juror/round/%s/votes' % round_id,
                 as_user='Jimbo Wales')
    recent_rating = resp['data'][-1]

    # Adjust a recent rating
    # - as juror
    vote_id = recent_rating['id']
    new_val = float((recent_rating['id'] + 1) % 2)
    resp = fetch('juror: edit a recent rating',
                 '/juror/round/%s/tasks/submit' % recent_rating['round_id'],
                 {'ratings': [{'vote_id': vote_id, 'value': new_val}]},
                 as_user='Jimbo Wales')

    # Admin endpoints (part 2)
    # --------------- --------

    # Get a preview of results from a round
    # - as coordinator
    resp = fetch('coordinator: get a preview of results from a round',
                 '/admin/round/%s/preview_results' % round_id,
                 as_user='LilyOfTheWest')

    # submit all remaining tasks for the round

    submit_ratings(api_client, round_id)

    resp = fetch('coordinator: preview round results in prep for closing',
                 '/admin/round/%s/preview_results' % round_id,
                 as_user='LilyOfTheWest')

    rnd_data = {'name': 'Test advance to rating round',
                'vote_method': 'rating',
                'quorum': 3,
                'deadline_date': "2016-10-20T00:00:00",
                'jurors': [u'Slaporte',
                           u'Effeietsanders',
                           u'Jean-Frédéric',
                           u'LilyOfTheWest']}

    resp = fetch('coordinator: close round, loading results into a new round',
                 '/admin/round/%s/advance' % round_id,
                 {'next_round': rnd_data, 'threshold': 0.5},
                 as_user='LilyOfTheWest')

    rnd_2_id = resp['data']['id']

    # TODO: test getting a csv of final round results needs more instrumentation
    print('>> downloading results')
    resp = api_client.fetch_url('/v1/admin/round/%s/results/download?su_to=LilyOfTheWest' % round_id)
    resp_data = resp.get_data()
    assert len(resp_data) > 100
    assert resp_data.count(',') > 10

    resp = fetch('coordinator: activate new round',
                 '/admin/round/%s/activate' % rnd_2_id,
                 {'post': True}, as_user='LilyOfTheWest')

    submit_ratings(api_client, rnd_2_id)

    resp = fetch('juror: get votes stats for rating round',
                 '/juror/round/%s/votes-stats' % rnd_2_id,
                 as_user='Slaporte')
    assert '1' in resp['stats']
    assert '5' in resp['stats']

    resp = fetch('juror: view own ratings for round 3',
                 '/juror/round/%s/ratings' % rnd_2_id,
                 as_user='Slaporte')

    resp = fetch('coordinator: preview results from second round',
                 '/admin/round/%s/preview_results' % rnd_2_id,
                 as_user='LilyOfTheWest')

    thresh_map = resp['data']['thresholds']  # TODO
    cur_thresh = [t for t, c in sorted(thresh_map.items()) if 0 < c <= 20][-1]

    rnd_data = {'name': 'Test advance to ranking round',
                'vote_method': 'ranking',
                'directions': 'Final round, rank the images, best to worst.',
                # note the lack of quorum. quorum is same as juror count
                'deadline_date': "2016-10-25T00:00:00",
                'jurors': [u'Slaporte',
                           u'Effeietsanders',
                           u'Jean-Frédéric',
                           u'MahmoudHashemi']}
    resp = fetch('coordinator: advance to round 3',
                 '/admin/round/%s/advance' % rnd_2_id,
                 {'next_round': rnd_data, 'threshold': cur_thresh},
                 as_user='LilyOfTheWest')
    rnd_3_id = resp['data']['id']

    resp = fetch('coordinator: activate round 3 to make assignments',
                 '/admin/round/%s/activate' % rnd_3_id,
                 {'post': True}, as_user='LilyOfTheWest')
    resp = fetch('coordinator: pause round 3 for edits',
                 '/admin/round/%s/pause' % rnd_3_id,
                 {'post': True}, as_user='LilyOfTheWest')

    # adding jimbo
    data = {'new_jurors': [u'Slaporte',
                           u'MahmoudHashemi',
                           u'Effeietsanders',
                           u'Jean-Frédéric',
                           u'Jimbo Wales']}
    resp = fetch('coordinator: add new juror jimbo to round 3',
                 '/admin/round/%s/edit' % rnd_3_id,
                 data, as_user='LilyOfTheWest')

    # edit without changing the jurors, but with changing the description
    data = {'directions': 'great new directions',
            'new_jurors': [u'Slaporte',
                           u'MahmoudHashemi',
                           u'Effeietsanders',
                           u'Jean-Frédéric',
                           u'Jimbo Wales']}

    resp = fetch('coordinator: change round 3 directions',
                 '/admin/round/%s/edit' % rnd_3_id,
                 data, as_user='LilyOfTheWest')

    resp = fetch('coordinator: reactivate round 3',
                 '/admin/round/%s/activate' % rnd_3_id,
                 {'post': True}, as_user='LilyOfTheWest')

    resp = fetch('coordinator: pause round 3 to remove jurors',
                      '/admin/round/%s/pause' % rnd_3_id,
                      {'post': True}, as_user='LilyOfTheWest')

    # remove jf and eff
    data = {'new_jurors': [u'Slaporte',
                           u'MahmoudHashemi',
                           u'Jimbo Wales']}
    resp = fetch('coordinator: remove JF and EFF from round 3 jurors',
                 '/admin/round/%s/edit' % rnd_3_id,
                 data, as_user='LilyOfTheWest')

    resp = fetch('coordinator: reactivate round 3',
                 '/admin/round/%s/activate' % rnd_3_id,
                 {'post': True}, as_user='LilyOfTheWest')

    resp = fetch('coordinator: pause round 3 to readd a juror',
                 '/admin/round/%s/pause' % rnd_3_id,
                 {'post': True}, as_user='LilyOfTheWest')

    # readd jf
    data = {'new_jurors': [u'Slaporte',
                           u'MahmoudHashemi',
                           u'Jean-Frédéric',
                           u'Jimbo Wales']}
    resp = fetch('coordinator: readd JF as juror',
                 '/admin/round/%s/edit' % rnd_3_id,
                 data, as_user='LilyOfTheWest')

    resp = fetch('coordinator: reactivate round 3 after readding JF as juror',
                 '/admin/round/%s/activate' % rnd_3_id,
                 {'post': True}, as_user='LilyOfTheWest')

    # cancel campaign -- warning, this cancels everything (campaign, rounds, and tasks)

    #resp = fetch('coordinator: cancel campaign',
    #             '/admin/campaign/%s/cancel' % campaign_id,
    #             {'post': True}, as_user='LilyOfTheWest')
    #import pdb;pdb.set_trace()

    # submit the remaining ratings

    submit_ratings(api_client, rnd_3_id)

    resp = fetch('coordinator: preview round 3 results',
                 '/admin/round/%s/preview_results' % rnd_3_id,
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: read round 3 reviews',
                 '/admin/round/%s/reviews' % rnd_3_id,
                 as_user='LilyOfTheWest')

    ### ARCHIVING (2020-09)
    data = {'is_archived': True}
    resp = fetch('coordinator: archive campaign',
                 '/admin/campaign/%s/edit' % campaign_id,
                 data, as_user='Yarl')

    resp = fetch('coordinator: see active campaigns, check archived hidden',
                 '/admin',
                 as_user='Yarl')
    assert len(resp['data']) == 0

    resp = fetch('juror: check archived campaign rounds hidden',
                 '/juror', as_user='Slaporte')
    assert len(resp['data']) == 0

    resp = fetch('coordinator: see all campaigns, check archived shown',
                 '/admin/campaigns/all',
                 as_user='Yarl')
    assert len(resp['data']) == 1
    assert resp['data'][0]['is_archived'] is True

    data = {'is_archived': False}
    resp = fetch('coordinator: unarchive campaign',
                 '/admin/campaign/%s/edit' % campaign_id,
                 data, as_user='Yarl')

    resp = fetch('coordinator: see active campaigns, check archived shown again',
                 '/admin',
                 as_user='Yarl')
    assert len(resp['data']) == 1
    assert glom(resp, 'data.0.is_archived') is False

    resp = fetch('juror: check archived campaign rounds shown',
                 '/juror', as_user='Slaporte')
    assert len(resp['data']) > 1  # 4 rounds at time of writing
    assert glom(resp, 'data.0.campaign.is_archived') is False


    ### END ARCHIVING (2020-09)

    resp = fetch('coordinator: finalize campaign',
                 '/admin/campaign/%s/finalize' % campaign_id,
                 {'post': True}, as_user='LilyOfTheWest')

    # view the final campaign report (note: fetch_url, as this is an html page)
    resp = base_client.fetch('coordinator: view final report',
                             '/admin/campaign/%s/report' % campaign_id,
                             as_user='LilyOfTheWest')  # , content_type='text/html')

    resp = fetch('coordinator: view round 3 entries',
                 '/admin/round/%s/entries' % rnd_3_id,
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: download round 3 entries',
                 '/admin/round/%s/entries/download' % rnd_3_id,
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: view round 3 results',
                 '/admin/round/%s/results' % rnd_3_id,
                 as_user='LilyOfTheWest')

    resp = fetch('juror: view own rankings for round 3',
                 '/juror/round/%s/rankings' % rnd_3_id,
                 as_user='Jimbo Wales')

    resp = fetch('coordinator: make campaign results public (publish report)',
                 '/admin/campaign/%s/publish' % campaign_id,
                 {'post': True}, as_user='LilyOfTheWest')

    resp = fetch('coordinator: unpublish campaign results',
                 '/admin/campaign/%s/unpublish' % campaign_id,
                 {'post': True}, as_user='LilyOfTheWest')

    resp = fetch('coordinator: republish campaign results',
                 '/admin/campaign/%s/publish' % campaign_id,
                 {'post': True}, as_user='LilyOfTheWest')

    pprint(resp['data'])

    resp = fetch('coordinator: see the audit log with full campaign history',
                 '/admin/campaign/%s/audit' % campaign_id,
                 as_user='LilyOfTheWest')

    pprint(resp['data'])


    # maintainer stuff
    resp = fetch('maintainer: see active users',
                 '/maintainer/active_users')

    resp = fetch('maintainer: see api logs',
                 '/logs/api')

    resp = fetch('maintainer: see api exec logs',
                 '/logs/api_exc')

    resp = base_client.fetch('public: view docs', '/docs')

    resp = base_client.fetch('public: view report', '/campaign/1')
    #resp = base_client.fetch('public: logout', '/logout')

def test_multiple_jurors(api_client):
    # This is copied from above. What's the best way to break up the tests into
    # various stages? Should I use a pytest.fixture?
    fetch = api_client.fetch

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

    # for date inputs (like deadline_date below), the default format
    # is %Y-%m-%d %H:%M:%S  (aka ISO8601)
    # Add a round to a campaign
    rnd_data = {'name': 'Test yes/no round',
                'vote_method': 'yesno',
                'quorum': 1,
                'deadline_date': "2016-10-15T00:00:00",
                'jurors': [u'Haylad',
                           u'Slaporte',
                           u'Haylad']}  # Testing duplicate usres

    resp = fetch('coordinator: add round to a campaign',
                 '/admin/campaign/%s/add_round' % campaign_id,
                 rnd_data,
                 as_user='LilyOfTheWest')


@script_log.wrap('critical', verbose=True)
def submit_ratings(client, round_id, coord_user='Yarl'):
    """
    A reminder of our key players:

      * Maintainer: Slaporte
      * Organizer: Yarl
      * Coordinators: LilyOfTheWest, Slaporte, Yarl, Effeietsanders
      * Jurors: (coordinators) + "Jean-Frédéric" + "Jimbo Wales"
    """
    fetch = client.fetch
    r_dict = fetch('coordinator: get round details/jurors for submit_ratings',
                   '/admin/round/%s' % round_id,
                   as_user=coord_user)['data']
    if not r_dict['status'] == 'active':
        raise RuntimeError('round must be active to submit ratings')
    j_dicts = r_dict['jurors']

    per_fetch = 100  # max value

    for j_dict in j_dicts:
        j_username = j_dict['username']
        for i in xrange(100):  # don't go on forever
            t_dicts = fetch('juror: fetch open tasks',
                            '/juror/round/%s/tasks?count=%s'
                            % (round_id, per_fetch), log_level=DEBUG,
                            as_user=j_username)['data']['tasks']
            if len(t_dicts) < per_fetch:
                print('!! last batch: %r' % ([t['id'] for t in t_dicts]))
            if not t_dicts:
                break  # right?
            ratings = []
            for i, t_dict in enumerate(t_dicts):
                vote_id = t_dict['id']
                review = None
                rating_dict = {'vote_id': vote_id}

                # arb scoring
                if r_dict['vote_method'] == 'yesno':
                    value = len(j_username + t_dict['entry']['name']) % 2
                    if value == 1:
                        review = '%s likes this' % j_username
                elif r_dict['vote_method'] == 'rating':
                    value = len(j_username + t_dict['entry']['name']) % 5 * 0.25
                    entry_id = t_dict['entry']['id']
                    if value == 1:
                        review = '%s thinks this is great' % j_username
                    '''
                    # Note: only if you want some extra faves for testing
                    if value == 1.0:
                        review = '%s loves this' % j_username
                        data = {'post': True}
                        resp = fetch('juror: submit fave',
                                     '/juror/round/%s/%s/fave' %
                                     (round_id, entry_id),
                                     data, as_user=j_username)
                    '''
                    '''
                    # Note: only if you want some extra flags for testing
                    if value <0.25:
                        resp = fetch('juror: flag an entry',
                                     '/juror/round/%s/%s/flag' % (round_id, entry_id),
                                     {'reason': 'not cool'},
                                     as_user=j_username)
                    '''
                elif r_dict['vote_method'] == 'ranking':
                    value = (i + len(j_username)) % len(t_dicts)
                    if value == 0:
                        review = '%s thinks this should win' % j_username
                else:
                    raise NotImplementedError()

                rating_dict['value'] = value
                if review:
                    print(review)
                    rating_dict['review'] = review

                ratings.append(rating_dict)

            data = {'ratings': ratings}
            t_resp = fetch('juror: submit ratings and reviews',
                           '/juror/round/%s/tasks/submit' % round_id,
                           data=data, as_user=j_username, log_level=DEBUG)
        else:
            raise RuntimeError('task list did not terminate')

    return

    # get all the jurors that have open tasks in a round
    # get juror's tasks
    # submit random valid votes until there are no more tasks
