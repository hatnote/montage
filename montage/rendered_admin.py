
from admin_endpoints import (get_index,
                             get_campaign,
                             get_round,
                             get_flagged_entries,
                             get_disqualified,
                             get_round_entries,
                             get_results)


def get_rendered_routes():
    # all campaigns
    # -- create_campaign
    # -- campaign details
    # -- -- edit_campaign
    # -- -- create round
    # -- -- round details
    # -- -- -- edit round
    # -- -- -- disqualification
    # -- -- -- view flags
    # -- -- -- view juror stats
    # -- -- -- -- per juror tasks
    # -- -- results
    # -- -- -- download
    # -- -- entries
    # -- -- -- download

    routes = [('/m/admin', view_index, 'admin_index.html'),
              ('/m/admin/campaign/create',
               create_campaign, 'campaign_create.html'),
              ('/m/admin/campaign/<campaign_id:int>',
               view_campaign, 'campaign.html'),
              ('/m/admin/campaign/<campaign_id:int>/edit',
               edit_campaign, 'campaign_edit.html'),
              ('/m/admin/campaign/<campaign_id:int>/round/create',
               create_round, 'round_create.html'),
              ('/m/admin/campaign/<campaign_id:int>/round/<round_id:int>',
               view_round, 'round.html'),
              ('/m/admin/campaign/<campaign_id:int>/round/<round_id:int>/edit',
               edit_round, 'round_edit.html'),
              ('/m/admin/campaign/<campaign_id:int>/round/<round_id:int>/flags',
               view_flags, 'flags_view.html'),
              ('/m/admin/campaign/<campaign_id:int>/round/<round_id:int>/juror/<user_id:int>',
               view_juror, 'juror_view.html'),
              ('/m/admin/campaign/<campaign_id:int>/round/<round_id:int>/disqualified',
               view_disqualified, 'disqualified_view.html')
              ('/m/admin/campaign/<campaign_id:int>/round/<round_id:int>/entries',
               view_entries, 'entries_view.html')
,              ('/m/admin/campaign/<campaign_id:int>/round/<round_id:int>/results',
               view_results, 'results.html')]
    return routes


def view_index(user_dao):
    raw = get_index(user_dao)
    return raw['data']

def create_campaign(user_dao):
    pass

def view_campaign(user_dao, campaign_id):
    raw = get_campaign(user_dao, campaign_id)
    return raw['data']

def edit_campaign(user_dao, campaign_id):
    raw = get_campaign(user_dao, campaign_id)
    return raw['data']

def create_round(user_dao, campaign_id):
    raw = get_campaign(user_dao, campaign_id)
    return raw['data']

def view_round(user_dao, round_id):
    raw = get_round(user_dao, round_id)
    return raw['data']

def edit_round(user_dao, round_id):
    raw = get_round(user_dao, round_id)
    return raw['data']

def view_flags(user_dao, round_id):
    raw = get_flagged_entries(user_dao, round_id)
    return raw['data']

def view_jurors(user_dao, round_id, user_id):
    pass

def view_disqualified(user_dao, round_id):
    raw = get_disqualified(user_dao, round_id)
    return raw['data']

def view_entries(user_dao, round_id):
    raw = get_round_entries(user_dao, round_id)
    return raw['data']

def view_results(user_dao, round_id):
    raw = get_results(user_dao, round_id)
    return raw['data']
