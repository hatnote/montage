import urllib
import urllib2
import cookielib
import json

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
    # load home
    resp = fetch('http://localhost:5000/').read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    # login as a maintainer
    resp = fetch('http://localhost:5000/complete_login').read()
    resp_dict = json.loads(resp)
    assert resp_dict['cookie']['username'] == 'Slaporte'

    # add an organizer
    data = {'username': 'Slaporte'}
    resp = fetch('http://localhost:5000/admin/add_organizer', data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    # create a campaign
    data = {'campaign_name': 'Another Test Campaign'}
    resp = fetch('http://localhost:5000/admin/new/campaign', data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'
    
    new_campaign_id = resp_dict['data']['id']

    # add a coordinator to this new camapign
    data = {'username': 'MahmoudHashemi'}
    resp = fetch('http://localhost:5000/admin/add_coordinator/campaign/%s' % new_campaign_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    # get the coordinator's index
    resp = fetch('http://localhost:5000/admin').read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    campaign_id = resp_dict['data'][-1]['id']

    # get coordinator's view of the first campaign    
    resp = fetch('http://localhost:5000/admin/campaign/%s' % campaign_id).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    # add a round to that campaign
    data = {'round_name': 'Another test round', 
            'quorum': 2, 
            'jurors': 'Slaporte,MahmoudHashemi'} # Comma separated, is this the usual way?
    resp = fetch('http://localhost:5000/admin/campaign/%s/new/round' % campaign_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    round_id = resp_dict['data']['id']

    # import the initial set of images to the round
    data = {'import_method': 'gistcsv',
        'gist_url': 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/9181d59224cd3335a8f434ff4683c83023f7a3f9/wlm2015_fr_12k.csv'}
    resp = fetch('http://localhost:5000/admin/round/%s/import' % round_id, data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    # active the round
    resp = fetch('http://localhost:5000/admin/round/%s/activate' % round_id, {'post': True}).read()
    resp_dict = json.loads(resp)
    # TODO: check results?

    # get the juror's index
    resp = fetch('http://localhost:5000/juror').read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    round_id = resp_dict['data'][-1]['id']

    # get the juror's view of the last round
    resp = fetch('http://localhost:5000/juror/round/%s' % round_id).read()
    resp_dict = json.loads(resp)
    # TODO: Check results

    # get the juror's next task
    # (optional count and offset params)
    resp = fetch('http://localhost:5000/juror/round/%s/tasks' % round_id).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    entry_id = resp_dict['data'][0]['round_entry_id']
    task_id = resp_dict['data'][0]['id']

    # submit the juror's rating
    data = {'entry_id': entry_id,
            'task_id': task_id,
            'rating': '0.8'}
    resp = fetch('http://localhost:5000/juror/submit/rating', data).read()
    resp_dict = json.loads(resp)
    assert resp_dict['status'] == 'success'

    import pdb;pdb.set_trace()

if __name__ == '__main__':
    main()
