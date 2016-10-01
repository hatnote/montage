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

from lithoxyl import DEBUG

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


def fetch(url, data=None):
    if not data:
        req = urllib2.Request(url)
    else:
        data_bytes = json.dumps(data)
        req = urllib2.Request(url, data_bytes,
                              {'Content-Type': 'application/json'})
    return opener.open(req)


@script_log.wrap('info', inject_as='act')
def fetch_json(url, data=None, act=None, **kw):
    act.level = kw.get('log_level', act.level)
    su_to = kw.get('su_to')
    if su_to:
        url_su_to = urllib.quote_plus(su_to.encode('utf8'))
        if '?' in url:
            url += '&su_to=' + url_su_to
        else:
            url += '?su_to=' + url_su_to
    act['url'] = url
    res = fetch(url, data=data)
    data_dict = json.load(res)
    if kw.get('assert_success', True):
        try:
            assert data_dict['status'] == 'success'
            # print '.. loaded %s' % url
        except AssertionError:
            print '!! did not successfully load %s' % url
            import pdb;pdb.set_trace()
    return data_dict


def full_run(url_base, remote):
    # Admin endpoints
    # ---------------

    # Get the home page
    # - as maintainer
    resp = fetch(url_base).read()

    # Login - TODO: this approach does not work
    # - as maintainer
    # resp = fetch(url_base + '/complete_login').read()

    # Add an organizer
    # - as maintainer
    data = {'username': 'Yarl'}
    resp = fetch_json(url_base + '/admin/add_organizer', data)

    # Create a campaign
    # - as organizer
    data = {'name': 'Another Test Campaign 2016',
            'coordinators': [u'LilyOfTheWest',
                             u'Slaporte',
                             u'Yarl']}
    resp = fetch_json(url_base + '/admin/add_campaign', data,
                      su_to='Yarl')

    # Get an admin view with a list of all campaigns and rounds
    # - as coordinator
    resp = fetch_json(url_base + '/admin', su_to='LilyOfTheWest')

    campaign_id = resp['data'][-1]['id']

    # Get a detailed view of a campaign
    # - as coordinator
    resp = fetch_json(url_base + '/admin/campaign/%s' % campaign_id,
                      su_to='LilyOfTheWest')

    # Edit a campaign
    # - as organizer
    data = {'name': 'A demo campaign 2016',
            'open_date': "2015-09-01 17:00:00",  # UTC times,
            'close_date': "2015-09-30 20:00:00"}
    resp = fetch_json(url_base + '/admin/campaign/%s/edit' % campaign_id,
                      data, su_to='Yarl')

    # Add a coordinator to a camapign
    # - as organizer
    # note: you can also add coordinators when the round is created
    data = {'username': 'Effeietsanders'}
    resp = fetch_json(url_base + '/admin/campaign/%s/add_coordinator' % campaign_id,
                      data, su_to='Yarl')

    # for date inputs (like deadline_date below), the default format
    # is %Y-%m-%d %H:%M:%S

    # Add a round to a campaign
    # - as coordinator
    data = {'name': 'Test yes/no round',
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


    resp = fetch_json(url_base + '/admin/campaign/%s/add_round' % campaign_id,
                      data, su_to='LilyOfTheWest')

    round_id = resp['data']['id']

    # Get detailed view of a round
    # - as coordinator
    resp = fetch_json(url_base + '/admin/round/%s' % round_id,
                      su_to='LilyOfTheWest')

    # Edit a round
    # - as coordinator
    data = {'directions': 'these are new directions'}
    resp = fetch_json(url_base + '/admin/round/%s/edit' % round_id,
                      data, su_to='LilyOfTheWest')

    # Import entries to a round from a gistcsv
    # - as coordinator
    gist_url = 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'
    data = {'import_method': 'gistcsv',
            'gist_url': gist_url}
    resp = fetch_json(url_base + '/admin/round/%s/import' % round_id,
                      data, su_to='LilyOfTheWest')

    """
    # Import entries to a round from a category
    # - as coordinator
    data = {'import_method': 'category',
            'category': 'Images_from_Wiki_Loves_Monuments_2015_in_Pakistan'}
    resp = fetch_json(url_base + '/admin/round/%s/import' % round_id,
                      data, su_to='LilyOfTheWest')
    """

    # Activate a round
    # - as coordinator
    data = {'post': True}
    resp = fetch_json(url_base + '/admin/round/%s/activate' % round_id,
                      data, su_to='LilyOfTheWest')

    # Pause a round
    # - as coordinator
    data = {'post': True}
    resp = fetch_json(url_base + '/admin/round/%s/pause' % round_id,
                      data, su_to='LilyOfTheWest')

    # Edit jurors in a round
    # - as coordinator
    data = {'new_jurors': [u'Slaporte',
                           u'MahmoudHashemi',
                           u'Effeietsanders',
                           u'Jean-Frédéric',
                           u'Jimbo Wales']}

    resp = fetch_json(url_base + '/admin/round/%s/edit_jurors' % round_id,
                      data, su_to='LilyOfTheWest')


    # Reactivate a round
    # - as coordinator
    data = {'post': True}
    resp = fetch_json(url_base + '/admin/round/%s/activate' % round_id,
                      data, su_to='LilyOfTheWest')

    # Get the audit logs
    # - as maintainer
    resp = fetch_json(url_base + '/admin/audit_logs')

    # Jury endpoints
    # --------------

    # Get the jury index
    # - as juror
    resp = fetch_json(url_base + '/juror', su_to='Jimbo Wales')

    round_id = resp['data'][-1]['id']

    """
    # TODO: Jurors only see a list of rounds at this point, so there
    # is no need to get the detailed view of  campaign.

    # Get a detailed view of a campaign
    resp = fetch_json(url_base + '/juror/campaign/' + campaign_id,
                      su_to='Jimbo Wales')
    """

    # Get a detailed view of a round
    # - as juror
    resp = fetch_json(url_base + '/juror/round/%s' % round_id,
                      su_to='Jimbo Wales')

    # Get the open tasks in a round
    # - as juror
    resp = fetch_json(url_base + '/juror/round/%s/tasks' % round_id,
                      su_to='Jimbo Wales')

    # note: will return a default of 15 tasks, but you can request
    # more or fewer with the count parameter, or can skip tasks with
    # an offset paramter

    # entry_id = resp['data']['tasks'][0]['round_entry_id']
    task_id = resp['data']['tasks'][0]['id']

    # Submit a single rating task
    # - as juror
    data = {'ratings': [{'task_id': task_id, 'value': 1.0}]}
    resp = fetch_json(url_base + '/juror/round/%s/tasks/submit' % round_id,
                      data, su_to='Jimbo Wales')
    import pdb;pdb.set_trace()
    # Get more tasks
    # - as juror
    resp = fetch_json(url_base + '/juror/round/%s/tasks' % round_id,
                      su_to='Jimbo Wales')

    rating_dicts = []
    for task in resp['data']['tasks']:
        val = float(task['id'] % 2)  # deterministic but arbitrary
        rating_dicts.append({'task_id': task['id'], 'value': val})
    data = {'ratings': rating_dicts}

    resp = fetch_json(url_base + '/juror/round/%s/tasks/submit' % round_id,
                      data, su_to='Jimbo Wales')

    # Admin endpoints (part 2)
    # --------------- --------

    # Get a preview of results from a round
    # - as coordinator
    resp = fetch_json(url_base + '/admin/round/%s/preview_results' % round_id,
                      su_to='LilyOfTheWest')

    # submit all remaining tasks for the round

    submit_ratings(url_base, round_id)

    # TODO:
    #
    # close out the round the round
    # load the results of this round into the next

    resp = fetch_json(url_base + '/admin/round/%s/preview_results' % round_id,
                      su_to='LilyOfTheWest')
    pprint(resp['data'])
    print cookies

    import pdb;pdb.set_trace()


@script_log.wrap('critical', verbose=True)
def submit_ratings(url_base, round_id):
    """
    A reminder of our key players:

      * Maintainer: Slaporte
      * Organizer: Yarl
      * Coordinators: LilyOfTheWest, Slaporte, Yarl, Effeietsanders
      * Jurors: (coordinators) + "Jean-Frédéric" + "Jimbo Wales"
    """
    r_dict = fetch_json(url_base + '/admin/round/%s' % round_id,
                        su_to='Yarl')['data']
    j_dicts = r_dict['jurors']

    per_fetch = 100  # max value

    for j_dict in j_dicts:
        j_username = j_dict['username']
        for i in xrange(100):  # don't go on forever
            t_dicts = fetch_json(url_base + '/juror/round/%s/tasks?count=%s'
                                 % (round_id, per_fetch), log_level=DEBUG,
                                 su_to=j_username)['data']['tasks']
            if not t_dicts:
                break  # right?
            ratings = []
            for t_dict in t_dicts:
                task_id = t_dict['id']

                # arb scoring
                if r_dict['vote_method'] == 'yesno':
                    value = len(j_username + t_dict['entry']['name']) % 2
                elif r_dict['vote_method'] == 'rating':
                    value = len(j_username + t_dict['entry']['name']) % 2
                else:
                    raise NotImplementedError()
                ratings.append({'task_id': task_id, "value": value})

            data = {'ratings': ratings}
            t_resp = fetch_json(url_base + '/juror/round/%s/tasks/submit' % round_id,
                                data=data, su_to=j_username, log_level=DEBUG)

    return

    # get all the jurors that have open tasks in a round
    # get juror's tasks
    # submit random valid votes until there are no more tasks


def main():
    config = utils.load_env_config()

    prs = argparse.ArgumentParser('test the montage server endpoints')
    add_arg = prs.add_argument
    add_arg('--remote', action="store_true", default=False)

    args = prs.parse_args()

    if args.remote:
        url_base = 'https://tools.wmflabs.org/montage-dev'
    else:
        url_base = 'http://localhost:5000'

    parsed_url = urlparse.urlparse(url_base)

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

    full_run(url_base, remote=args.remote)


if __name__ == '__main__':
    main()
