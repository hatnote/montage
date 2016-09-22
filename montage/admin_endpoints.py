from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import (Campaign,
                 CoordinatorDAO,
                 MaintainerDAO,
                 OrganizerDAO)


def create_campaign(user, rdb_session, request):
    if not user.is_maintainer:  # TODO: check if user is an organizer too
        raise Forbidden('not allowed to create campaigns')

    org_dao = OrganizerDAO(rdb_session, user)
    new_camp_name = request.form.get('campaign_name')
    ret = org_dao.create_campaign(name=new_camp_name)
    return ret


def import_entries(rdb_session, user, round_id, request):
    if not user.is_maintainer:  # TODO: check if user is an organizer or coord
        raise Forbidden('not allowed to import entries')

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)
    # TODO: Confirm if round exists
    import_method = request.form.get('import_method')
    if import_method == 'gistcsv':
        gist_url = request.form.get('gist_url')
        ret = coord_dao.add_entries_from_csv_gist(gist_url, round_id)
    else:
        # TODO: Support category based input via labs
        #       (other import methods too?)
        pass
    return ret

def activate_round(rdb_session, user, round_id, request):
    if not user.is_maintainer:  # TODO: check if user is an organizer or coord
        raise Forbidden('not allowed to activate round')
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    ret = coord_dao.activate_round(round_id)
    # TODO: Confirm round exists?
    return ret  # Should return stats on the number of tasks


def edit_campaign(user_dao, campaign_id, request_dict):
    pass


def create_round(rdb_session, user, campaign_id, request):
    if not user.is_maintainer:  # TODO: check if user is an organizer or coord
        raise Forbidden('not allowed to create rounds')
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = coord_dao.get_campaign(campaign_id)
    # TODO: Confirm if campaign exists
    new_round_name = request.form.get('round_name')
    qourum = request.form.get('qourum')
    jurors = request.form.get('jurors').split(',', '')
    ret = coord_dao.create_round(name=new_round_name,
                                 quorum=qourum,
                                 jurors=jurors,
                                 campaign=campaign)
    return ret


def edit_round(user_dao, round_id, request_dict):
    pass


def get_admin_index(rdb_session, user):
    """
    Summary: Get admin-level details for all campaigns.

    Response model name: AdminCampaignIndex
    Response model:
        campaigns:
            type: array
            items:
                type: AdminCampaignDetails

    Errors:
       403: User does not have permission to access any campaigns
    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaigns = coord_dao.get_all_campaigns()
    if len(campaigns) == 0:
        raise Forbidden('not a coordinator on any campaigns')
    data = []
    for campaign in campaigns:
        camp = get_admin_campaign(rdb_session, user, campaign.id)
        data.append(camp)
    return data


def get_admin_campaign(rdb_session, user, campaign_id):
    """
    Summary: Get admin-level details for a campaign, identified by campaign ID.

    Request model:
        campaign_id:
            type: int64

    Response model name: AdminCampaignDetails
    Response model:
        id:
            type: int64
        name:
            type: string
        rounds:
            type: array
            items:
                type: AdminRoundDetails
        coordinators:
            type: array
            items:
                type: CoordDetails
        url_name:
            type: string

    Errors:
       403: User does not have permission to access requested campaign
       404: Campaign not found
    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = coord_dao.get_campaign(campaign_id)
    if campaign is None:
        raise Forbidden('not a coordinator on this campaign')
    info = {'id': campaign.id,
            'name': campaign.name,
            'rounds': [],
            'coords': [u.username for u in campaign.coords]}
    for rnd in campaign.rounds:
        info['rounds'].append(get_admin_round(rdb_session, user, rnd.id))

    info['canonical_url_name'] = slugify(info['name'], '-')
    # TODO: Format output?
    return info


def get_admin_round(rdb_session, user, round_id):
    """
    Summary: Get admin-level details for a round, identified by round ID.

    Request model:
        round_id:
            type: int64

    Response model name: AdminRoundDetails
    Response model:
        id:
            type: int64
        name:
            type: string
        url_name:
            type: string
        vote_method:
            type: string
        status:
            type: string
        jurors:
            type: array
            items:
                type: UserDetails
        quorum:
            type: int64
        close_date:
            type: date-time
        campaign:
            type: CampaignInfo

    Errors:
       403: User does not have permission to access requested round
       404: Round not found
    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)
    if rnd is None:
        raise Forbidden('not a coordinator for this round')
    # entries_info = user_dao.get_entry_info(round_id) # TODO

    # TODO: joinedload if this generates too many queries
    jurors = [{'username': rj.user.username,
               'id': rj.user.id,
               'active': rj.is_active} for rj in rnd.round_jurors]

    info = {'id': rnd.id,
            'name': rnd.name,
            'voteMethod': rnd.vote_method,
            'status': rnd.status,
            'jurors': jurors,
            'quorum': rnd.quorum,
            'sourceInfo': {
                'entryCount': None,
                'uploadersCount': None,
                'roundSource': {'id': None,
                                'title': None}},
            'closeDate': rnd.close_date,
            'campaign': rnd.campaign_id}

    info['canonical_url_name'] = slugify(info['name'], '-')

    return info


def add_organizer(rdb_session, user, request):
    if not user.is_maintainer:
        raise Forbidden('not allowed to add organizers')

    maint_dao = MaintainerDAO(rdb_session, user)
    new_user_name = request.form.get('username')
    ret = maint_dao.add_organizer(new_user_name)
    return ret


def add_coordinator(rdb_session, user, campaign_id, request):
    if not user.is_maintainer:  # TODO: Check if organizer too
        raise Forbidden('not allowed to add coordinators')
    # TODO: verify campaign id?
    org_dao = OrganizerDAO(rdb_session, user)
    new_user_name = request.form.get('username')
    ret = org_dao.add_coordinator(new_user_name, campaign_id)
    return ret


admin_routes = [GET('/admin', get_admin_index),
                POST('/admin/new/campaign', create_campaign),
                GET('/admin/campaign/<campaign_id:int>/<camp_name?>',
                    get_admin_campaign),
                POST('/admin/campaign/<campaign_id:int>/<camp_name?>',
                     edit_campaign),
                POST('/admin/campaign/<campaign_id:int>/new/round',
                     create_round),
                POST('/admin/round/<round_id:int>/import', import_entries),
                POST('/admin/round/<round_id:int>/activate', activate_round),
                GET('/admin/round/<round_id:int>/<round_name?>',
                    get_admin_round),
                POST('/admin/round/<round_id:int>/<round_name?>',
                     edit_round),
                POST('/admin/add_organizer', add_organizer),
                POST('/admin/add_coordinator/campaign/<campaign_id:int>', 
                     add_coordinator)]



# - cancel round
# - update round
#   - no reassignment required: name, description, directions, display_settings
#   - reassignment required: quorum, active_jurors
#   - not updateable: id, open_date, close_date, vote_method, campaign_id/seq
