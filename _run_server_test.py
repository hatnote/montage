import urllib
import urllib2
import cookielib
import json

import argparse

cookies = cookielib.LWPCookieJar()

handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPCookieProcessor(cookies)
]

opener = urllib2.build_opener(*handlers)


def fetch(url, data=None):
    if data:
        data = urllib.urlencode(data)
    req = urllib2.Request(url, data)
    return opener.open(req)


def main():
    prs = argparse.ArgumentParser('test the montage server endpoints')
    add_arg = prs.add_argument
    add_arg('--remote', action="store_true", default=False)

    args = prs.parse_args()

    if args.remote:
        url_base = 'https://tools.wmflabs.org/montage-dev'
    else:
        url_base = 'http://localhost:5000'

    # load home
    resp = fetch(url_base).read()

    print '.. loaded the home page'

    # login as a maintainer
    resp = fetch(url_base + '/complete_login').read()
    #resp_dict = json.loads(resp)
    #assert resp_dict['cookie']['username'] == 'Slaporte'

    print '.. logged in'

    # add an organizer
    data = {'username': 'Slaporte'}
    resp = fetch(url_base + '/admin/add_organizer', data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. added %s as organizer' % data['username']

    # create a campaign
    data = {'name': 'Another Test Campaign'}
    resp = fetch(url_base + '/admin/new/campaign', data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    campaign_id = resp_dict['data']['id']

    print '.. created campaign no %s' % campaign_id

    # edit campaign
    data = {'name': 'Another Test Campaign - edited'}
    resp = fetch(url_base + '/admin/campaign/%s/edit' % campaign_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. edited campaign no %s' % campaign_id

    # add a coordinator to this new camapign
    data = {'username': 'MahmoudHashemi'}
    resp = fetch(url_base + '/admin/add_coordinator/campaign/%s' % campaign_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. added %s as coordinator for campaign no %s' % (data['username'], campaign_id)

    # get the coordinator's index
    resp = fetch(url_base + '/admin').read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. loaded the coordinators index'

    campaign_id = resp_dict['data'][-1]['id']

    # get coordinator's view of the first campaign
    resp = fetch(url_base + '/admin/campaign/%s' % campaign_id).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. loaded the coordinator view of campaign no %s' % campaign_id

    # add a round to that campaign
    data = {'name': 'Another test round', 
            'vote_method': 'rating',
            'quorum': 2, 
            'jurors': 'Slaporte,MahmoudHashemi'} # Comma separated, is this the usual way?
    resp = fetch(url_base + '/admin/campaign/%s/new/round' % campaign_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    round_id = resp_dict['data']['id']

    print '.. added round no %s to campaign no %s' % (round_id, campaign_id)

    # edit the round description
    data = {'directions': 'these are new directions'}
    resp = fetch(url_base + '/admin/round/%s/edit' % round_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. edited the directions of round no %s' % round_id

    # import the initial set of images to the round
    data = {'import_method': 'gistcsv',
        'gist_url': 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/9181d59224cd3335a8f434ff4683c83023f7a3f9/wlm2015_fr_12k.csv'}
    resp = fetch(url_base + '/admin/round/%s/import' % round_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. loaded %s entries into round no %s' % ('_', round_id)

    # active the round
    resp = fetch(url_base + '/admin/round/%s/activate' % round_id, {'post': True}).read()
    resp_dict = json.loads(resp)
    # TODO: check results?

    print '.. activated round no %s' % round_id

    # get the juror's index
    resp = fetch(url_base + '/juror').read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    round_id = resp_dict['data'][-1]['id']

    print '.. loaded the jurors index'

    # get the juror's view of the last round
    resp = fetch(url_base + '/juror/round/%s' % round_id).read()
    resp_dict = json.loads(resp)

    print '.. loaded juror view of round no %s' % round_id

    # get the juror's next task
    # (optional count and offset params)
    resp = fetch(url_base + '/juror/round/%s/tasks' % round_id).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    entry_id = resp_dict['data'][0]['round_entry_id']
    task_id = resp_dict['data'][0]['id']

    print '.. loaded task(s) from round no %s' % round_id

    # submit the juror's rating
    data = {'entry_id': entry_id,
            'task_id': task_id,
            'rating': '0.8'}
    resp = fetch(url_base + '/juror/submit/rating', data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    print '.. submitted rating on task no %s' % task_id

    # TODO:
    #
    # submit random results for all open tasks in a round
    # close out the round the round
    # load the results of this round into the next

    import pdb;pdb.set_trace()

if __name__ == '__main__':
    main()
