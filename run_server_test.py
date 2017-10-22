# -*- coding: utf-8 -*-

import sys
import json
import os.path
import urllib
import urllib2
import urlparse
import argparse
import cookielib
from pprint import pprint

from lithoxyl import DEBUG, INFO

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)
sys.path.append(PROJ_PATH)

from montage import utils
from montage.log import script_log


cookies = cookielib.LWPCookieJar()

handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPCookieProcessor(cookies)
]

opener = urllib2.build_opener(*handlers)


def fetch_raw(url, data=None, content_type='application/json'):
    if not data:
        req = urllib2.Request(url)
    else:
        data_bytes = json.dumps(data)
        req = urllib2.Request(url, data_bytes,
                              {'Content-Type': content_type})
    return opener.open(req)


def fetch_url(url, data=None, act=None, **kw):
    su_to = kw.get('su_to')
    if su_to:
        url_su_to = urllib.quote_plus(su_to.encode('utf8'))
        if '?' in url:
            url += '&su_to=' + url_su_to
        else:
            url += '?su_to=' + url_su_to
    if act:
        act['url'] = url
    try:
        res = fetch_raw(url, data=data,
                        content_type=kw.get('content_type', 'application/json'))
    except urllib2.HTTPError as he:
        error_code = kw.get('error_code')
        if error_code and error_code == he.getcode():
            return True
        print '!! ', he.read()
        print
        import pdb;pdb.set_trace()
        raise
    return res


"""
* role
* action
* url
* data
* username
* assert_error/success
* http method (whether or not data is passed)
"""

# TODO: could use clastic to route-match based on URL to determine
# "role" of current route being tested
class TestClient(object):
    def __init__(self, base_url, default_role='public'):
        self.base_url = base_url.rstrip('/')
        self.default_role = default_role
        # TODO: default user?

    def fetch(self, role_action, url, data=None, **kw):
        if not url.startswith('/'):
            raise ValueError('expected url starting with "/", not: %r' % url)
        role, sep, action = role_action.partition(':')
        role, action = (role, action) if sep else (self.default_role, role)
        print '>>', action, 'as', role,
        as_user = kw.pop('as_user', None)
        if as_user:
            print '(%s)' % as_user
        else:
            print

        log_level = kw.pop('log_level', INFO)
        error_code = kw.pop('error_code', None)
        if kw:
            raise TypeError('unexpected kwargs: %r' % kw.keys())

        with script_log.action(log_level, 'fetch_url') as act:
            resp = fetch_url(self.base_url + url,
                             data=data,
                             su_to=as_user,
                             error_code=error_code,
                             act=act)
        if error_code and resp is True:
            return True
        data_dict = json.load(resp)
        try:
            assert data_dict['status'] == 'success'
        except AssertionError:
            print '!! did not successfully load %s' % url
            print '  got: ', data_dict
            import pdb;pdb.set_trace()
        return data_dict


def full_run(base_url, remote):
    # Admin endpoints
    # ---------------

    # Get the home page
    # - as maintainer
    base_api_url = base_url + '/v1/'
    client = TestClient(base_url=base_api_url)  # TODO
    fetch = client.fetch

    resp = fetch_raw(base_url).read()

    # Login - TODO: this approach does not work
    # - as maintainer
    # resp = fetch_raw(base_url + '/complete_login').read()

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
    resp = fetch('organizer: edit campaign',
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

    # Import entries to a round from a gistcsv
    # - as coordinator
    """
    gist_url = 'https://gist.githubusercontent.com/slaporte/2074004d1fb76893b23f91fc2d4951a1/raw/26d49a976b6f5c13ecc0bee28747f9c1dce4a5ef/gistfile1.txt'
    resp = fetch('coordinator: import entries from gist csv',
                 '/admin/round/%s/import' % round_id,
                 {'import_method': 'gistcsv', 'gist_url': gist_url},
                 as_user='LilyOfTheWest')

    """
    data = {'import_method': 'category',
            'category': 'Images_from_Wiki_Loves_Monuments_2015_in_Albania'}
    resp = fetch('coordinator: import entries from a category',
                 '/admin/round/%s/import' % round_id,
                 data, as_user='LilyOfTheWest')

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

    gist_url = 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'
    resp = fetch('coordinator: import more entries from different gist csv into an existing round',
                 '/admin/round/%s/import' % round_id,
                 {'import_method': 'gistcsv', 'gist_url': gist_url},
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

    """
    # Try to activate a second round (will fail bc prev round not closed)

    data = {'name': 'Test second round',
            'vote_method': 'rating',
            'quorum': 4,
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
                       'dq_by_resolution': True,
                       'dq_by_uploader': True,
                       'dq_by_filetype': True,
                       'allowed_filetypes': ['jpeg', 'png', 'gif'],
                       'min_resolution': 2000000, #2 megapixels
                       'dq_coords': True,
                       'dq_organizers': True,
                       'dq_maintainers': True}}


    resp = fetch('coordinator: try to create second round',
                 '/admin/campaign/%s/add_round' % campaign_id,
                 data, as_user='LilyOfTheWest')

    secound_round_id = resp['data']['id']

    data = {'post': True}
    resp = fetch('coordinator: activate round (will fail)',
                 '/admin/round/%s/activate' % second_round_id,
                 data, as_user='LilyOfTheWest')

    import pdb;pdb.set_trace()
    """

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

    resp = fetch('maintainer: view audit logs', '/logs/audit')

    # Jury endpoints
    # --------------

    resp = fetch('juror: get the juror overview',
                 '/juror', as_user='Slaporte')

    """
    # TODO: Jurors only see a list of rounds at this point, so there
    # is no need to get the detailed view of campaign.

    # Get a detailed view of a campaign
    resp = fetch('juror: get campaign details',
                 '/juror/campaign/' + campaign_id,
                 as_user='Jimbo Wales')
    """
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

    submit_ratings(client, round_id)

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
    resp = fetch_raw(base_api_url + '/admin/round/%s/results/download?su_to=LilyOfTheWest' % round_id)
    resp_bytes = resp.read()
    assert len(resp_bytes) > 100
    assert resp_bytes.count(',') > 10

    resp = fetch('coordinator: activate new round',
                 '/admin/round/%s/activate' % rnd_2_id,
                 {'post': True}, as_user='LilyOfTheWest')

    submit_ratings(client, rnd_2_id)

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

    submit_ratings(client, rnd_3_id)

    resp = fetch('coordinator: preview round 3 results',
                 '/admin/round/%s/preview_results' % rnd_3_id,
                 as_user='LilyOfTheWest')

    resp = fetch('coordinator: finalize campaign',
                 '/admin/campaign/%s/finalize' % campaign_id,
                 {'post': True}, as_user='LilyOfTheWest')

    # view the final campaign report (note: fetch_url, as this is an html page)
    resp = fetch_url(base_url + '/admin/campaign/%s/report' % campaign_id,
                     as_user='LilyOfTheWest', content_type='text/html')

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
    import pdb;pdb.set_trace()


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
                print '!! last batch: %r' % ([t['id'] for t in t_dicts])
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
                    if value == 1.0:
                        review = '%s likes this' % j_username
                elif r_dict['vote_method'] == 'rating':
                    value = len(j_username + t_dict['entry']['name']) % 5 * 0.25
                    entry_id = t_dict['entry']['id']
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


def main():
    config = utils.load_env_config()

    prs = argparse.ArgumentParser('test the montage server endpoints')
    add_arg = prs.add_argument
    add_arg('--remote', type=str,
            help='run tests on a remote montage installation')
    add_arg('--remote_prod', action='store_true',
            help='run tests on https://tools.wmflabs.org/montage')
    add_arg('--remote_dev', action='store_true',
            help='run tests on https://tools.wmflabs.org/montage-dev')

    args = prs.parse_args()

    if args.remote:
        base_url = args.remote
    elif args.remote_prod:
        base_url = 'https://tools.wmflabs.org/montage'
    elif args.remote_dev:
        base_url = 'https://tools.wmflabs.org/montage-dev'
    else:
        base_url = 'http://localhost:5000'

    parsed_url = urlparse.urlparse(base_url)

    domain = parsed_url.netloc.partition(':')[0]
    if domain.startswith('localhost'):
        domain = 'localhost.local'
        ck_val = config['dev_local_cookie_value']
    else:
        ck_val = config['dev_remote_cookie_value']

    ck = cookielib.Cookie(version=0, name='clastic_cookie',
                          value=ck_val,
                          port=None, port_specified=False,
                          domain=domain, domain_specified=True,
                          domain_initial_dot=False,
                          path=parsed_url.path, path_specified=True,
                          secure=False, expires=None, discard=False,
                          comment=None, comment_url=None, rest={},
                          rfc2109=False)
    cookies.set_cookie(ck)

    full_run(base_url, remote=args.remote)


if __name__ == '__main__':
    main()
