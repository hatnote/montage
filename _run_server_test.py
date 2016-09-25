import sys
import os.path
import urllib
import urllib2
import urlparse
import cookielib
import json

import argparse

cookies = cookielib.LWPCookieJar()

handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPCookieProcessor(cookies)
]

opener = urllib2.build_opener(*handlers)

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from montage import utils


def fetch(url, data=None):
    if data:
        data = urllib.urlencode(data)
    req = urllib2.Request(url, data)
    return opener.open(req)


def fetch_json(*a, **kw):
    res = fetch(*a, **kw)
    data_dict = json.load(res)
    if kw.get('assert_success', True):
        assert data_dict['status'] == 'success'
    return data_dict


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

    # load home
    resp = fetch(url_base).read()

    print '.. loaded the home page'

    # login as a maintainer
    # resp = fetch(url_base + '/complete_login').read()
    # resp_dict = json.loads(resp)
    # assert resp_dict['cookie']['username'] == 'Slaporte'

    print '.. logged in'

    # add an organizer
    data = {'username': 'Slaporte'}
    resp_dict = fetch_json(url_base + '/admin/add_organizer', data)

    print '.. added %s as organizer' % data['username']

    # create a campaign
    data = {'name': 'Another Test Campaign'}
    resp_dict = fetch_json(url_base + '/admin/new/campaign', data)

    campaign_id = resp_dict['data']['id']

    print '.. created campaign no %s' % campaign_id

    # edit campaign
    data = {'name': 'Another Test Campaign - edited'}
    resp_dict = fetch_json(url_base + '/admin/campaign/%s/edit' % campaign_id, data)

    print '.. edited campaign no %s' % campaign_id

    # add a coordinator to this new camapign
    data = {'username': 'MahmoudHashemi'}
    resp_dict = fetch(url_base + '/admin/add_coordinator/campaign/%s' % campaign_id, data)

    print '.. added %s as coordinator for campaign no %s' % (data['username'], campaign_id)

    # get the coordinator's index
    resp_dict = fetch_json(url_base + '/admin')

    print '.. loaded the coordinators index'

    campaign_id = resp_dict['data'][-1]['id']

    # get coordinator's view of the first campaign
    resp_dict = fetch_json(url_base + '/admin/campaign/%s' % campaign_id)

    print '.. loaded the coordinator view of campaign no %s' % campaign_id

    # add a round to that campaign
    data = {'name': 'Another test round',
            'vote_method': 'rating',
            'quorum': 2,
            'jurors': 'Slaporte,MahmoudHashemi'} # Comma separated, is this the usual way?
    resp_dict = fetch_json(url_base + '/admin/campaign/%s/new/round' % campaign_id, data)

    round_id = resp_dict['data']['id']

    print '.. added round no %s to campaign no %s' % (round_id, campaign_id)

    # edit the round description
    data = {'directions': 'these are new directions'}
    resp_dict = fetch_json(url_base + '/admin/round/%s/edit' % round_id, data)

    print '.. edited the directions of round no %s' % round_id

    # import the initial set of images to the round
    data = {'import_method': 'gistcsv',
            'gist_url': 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/9181d59224cd3335a8f434ff4683c83023f7a3f9/wlm2015_fr_12k.csv'}
    resp_dict = fetch_json(url_base + '/admin/round/%s/import' % round_id, data)

    print '.. loaded %s entries into round no %s' % ('_', round_id)

    # active the round
    resp_dict = fetch_json(url_base + '/admin/round/%s/activate' % round_id, {'post': True})
    # TODO: check results?

    print '.. activated round no %s' % round_id

    # get the juror's index
    resp_dict = fetch_json(url_base + '/juror')

    round_id = resp_dict['data'][-1]['id']

    print '.. loaded the jurors index'

    # get the juror's view of the last round
    resp_dict = fetch_json(url_base + '/juror/round/%s' % round_id)

    print '.. loaded juror view of round no %s' % round_id

    # get the juror's next task
    # (optional count and offset params)
    resp_dict = fetch_json(url_base + '/juror/round/%s/tasks' % round_id)

    entry_id = resp_dict['data'][0]['round_entry_id']
    task_id = resp_dict['data'][0]['id']

    print '.. loaded task(s) from round no %s' % round_id

    # submit the juror's rating
    data = {'entry_id': entry_id,
            'task_id': task_id,
            'rating': '0.8'}
    resp_dict = fetch_json(url_base + '/juror/submit/rating', data)

    print '.. submitted rating on task no %s' % task_id

    # TODO:
    #
    # submit random results for all open tasks in a round
    # close out the round the round
    # load the results of this round into the next

    print cookies

    import pdb;pdb.set_trace()

if __name__ == '__main__':
    main()
