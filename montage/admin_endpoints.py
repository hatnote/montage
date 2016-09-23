from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from utils import fmt_date

from rdb import (Campaign,
                 CoordinatorDAO,
                 MaintainerDAO,
                 OrganizerDAO)



def make_admin_campaign_info(campaign):
    ret = {'id': campaign.id,
           'name': campaign.name,
           'canonical_url_name': slugify(campaign.name)}
    return ret


def make_admin_campaign_details(campaign):
    ret = {'id': campaign.id,
           'name': campaign.name,
           'canonical_url_name': slugify(campaign.name),
           'rounds': [make_admin_round_info(rnd) for rnd in campaign.rounds],
           'coordinators': [make_campaign_coordinator_info(c) 
                            for c in campaign.coords]}
    return ret


def make_admin_round_info(rnd):
    ret = {'id': rnd.id,
           'name': rnd.name,
           'directions': rnd.directions,
           'canonical_url_name': slugify(rnd.name, '-'),
           'vote_method': rnd.vote_method,
           'open_date': fmt_date(rnd.open_date),
           'close_date': fmt_date(rnd.close_date),
           'status': rnd.status,
           'quorum': rnd.quorum,
           'jurors': [make_round_juror_details(j) for j in rnd.round_jurors]}
    return ret


def make_admin_round_details(rnd):
    ret = {'id': rnd.id,
           'name': rnd.name,
           'directions': rnd.directions,
           'canonical_url_name': slugify(rnd.name, '-'),
           'vote_method': rnd.vote_method,
           'open_date': fmt_date(rnd.open_date),
           'close_date': fmt_date(rnd.close_date),
           'status': rnd.status,
           'quorum': rnd.quorum,
           'campaign': make_admin_campaign_info(rnd.campaign),
           'jurors': [make_round_juror_details(j) for j in rnd.round_jurors]}
    # TODO: add total num of entries, total num of uploaders, round source info
    return ret


def make_round_juror_details(round_juror):
    ret = {'id': round_juror.user.id,
           'username': round_juror.user.username,
           'is_active': round_juror.is_active}
    return ret


def make_campaign_coordinator_info(coordinator):
    ret = {'username': coordinator.username}
    return ret


def create_campaign(user, rdb_session, request):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    if not user.is_maintainer:  # TODO: check if user is an organizer too
        raise Forbidden('not allowed to create campaigns')

    org_dao = OrganizerDAO(rdb_session, user)
    new_camp_name = request.form.get('campaign_name')
    campaign = org_dao.create_campaign(name=new_camp_name)
    data = make_admin_campaign_details(campaign)
    return {'data': data}


def import_entries(rdb_session, user, round_id, request):
    """
    Summary: Load entries into a new round identified by a round ID.

    Request model:
        round_id:
            type: int64
        import_method:
            type: string
        import_url:
            type: string

    Response model name: EntryImportDetails
    Response model:
        round_id:
            type: int64
        total_entries:
            type: int64
    """

    if not user.is_maintainer:  # TODO: check if user is an organizer or coord
        raise Forbidden('not allowed to import entries')

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)
    # TODO: Confirm if round exists
    import_method = request.form.get('import_method')
    if import_method == 'gistcsv':
        gist_url = request.form.get('gist_url')
        rnd = coord_dao.add_entries_from_csv_gist(gist_url, round_id)
    else:
        # TODO: Support category based input via labs
        #       (other import methods too?)
        pass
    data = {'round_id': rnd.id,
            'total_entries': len(rnd.entries)}
    return {'data': data}

def activate_round(rdb_session, user, round_id, request):
    """
    Summary: Set the status of a round to active.

    Request model:
        round_id:
            type: int64

    Response model name: RoundActivationDetails
    Response model:
        round_id:
            type: int64
        status:
            type: string
    """
    if not user.is_maintainer:  # TODO: check if user is an organizer or coord
        raise Forbidden('not allowed to activate round')
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    tasks = coord_dao.activate_round(round_id)
    # TODO: Confirm round exists?
    data = {'round_id': round_id,
            'total_tasks': len(tasks)}
    return {'data': data}


def edit_campaign(user_dao, campaign_id, request_dict):
    """
    Summary: Change the settings for a round identified by a round ID.

    Request model:
        campaign_id:
            type: int64

    Response model: AdminCampaignDetails
    """
    pass


def create_round(rdb_session, user, campaign_id, request):
    """
    Summary: Post a new round

    Request model:
        campaign_id:
            type: int64

    Response model: AdminCampaignDetails
    """
    if not user.is_maintainer:  # TODO: check if user is an organizer or coord
        raise Forbidden('not allowed to create rounds')
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = coord_dao.get_campaign(campaign_id)
    # TODO: Confirm if campaign exists
    new_round_name = request.form.get('round_name')
    jurors = request.form.get('jurors').split(',')
    if not jurors:
        raise Exception('jurors are required to create a round')
    default_quorum = len(jurors) 
    quorum = request.form.get('quorum', default_quorum)
    rnd = coord_dao.create_round(name=new_round_name,
                                 quorum=quorum,
                                 jurors=jurors,
                                 campaign=campaign)
    data = make_admin_round_details(rnd)
    return {'data': data}


def edit_round(user_dao, round_id, request_dict):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    pass


def get_index(rdb_session, user):
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
        data.append(make_admin_campaign_details(campaign))
    return {'data': data}


def get_campaign(rdb_session, user, campaign_id):
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
        canonical_url_name:
            type: string
        rounds:
            type: array
            items:
                type: AdminRoundInfo
        coordinators:
            type: array
            items:
                type: CoordDetails

    Errors:
       403: User does not have permission to access requested campaign
       404: Campaign not found
    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = coord_dao.get_campaign(campaign_id)
    if campaign is None:
        raise Forbidden('not a coordinator on this campaign')
    data = make_admin_campaign_details(campaign)
    return {'data': data}


def get_round(rdb_session, user, round_id):
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
        directions:
            type: string
        canonical_url_name:
            type: string
        vote_method:
            type: string
        open_date:
            type: date-time
        close_date:
            type: date-time
        status:
            type: string
        quorum:
            type: int64
        campaign:
            type: CampaignInfo
        jurors:
            type: array
            items:
                type: UserDetails

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
    data = make_admin_round_details(rnd)
    return {'data': data}


def add_organizer(rdb_session, user, request):
    """
    Summary: Add a new organizer identified by Wikimedia username

    Request mode:
        username:
            type: string

    Response model:
        username:
            type: string
        last_login_date:
            type: date-time

    Errors:
       403: User does not have permission to add organizers
    """
    if not user.is_maintainer:
        raise Forbidden('not allowed to add organizers')

    maint_dao = MaintainerDAO(rdb_session, user)
    new_user_name = request.form.get('username')
    new_organizer = maint_dao.add_organizer(new_user_name)
    data = {'username': new_organizer.username,
            'last_login_date': fmt_date(new_organizer.last_login_date)}
    return {'data': data}


def add_coordinator(rdb_session, user, campaign_id, request):
    """
    Summary: -
        Add a new coordinator identified by Wikimedia username to a campaign
        identified by campaign ID

    Request mode:
        username:
            type: string

    Response model:
        username:
            type: string
        last_login_date:
            type: date-time
        campaign_id:
            type: int64

    Errors:
       403: User does not have permission to add coordinators

    """
    if not user.is_maintainer:  # TODO: Check if organizer too
        raise Forbidden('not allowed to add coordinators')
    # TODO: verify campaign id?
    org_dao = OrganizerDAO(rdb_session, user)
    new_user_name = request.form.get('username')
    new_coord = org_dao.add_coordinator(new_user_name, campaign_id)
    data = {'username': new_coord.username,
            'campaign_id': campaign_id,
            'last_login_date': fmt_date(new_coord.last_login_date)}
    return {'data': data}


admin_routes = [GET('/admin', get_index),
                POST('/admin/new/campaign', create_campaign),
                GET('/admin/campaign/<campaign_id:int>/<camp_name?>',
                    get_campaign),
                POST('/admin/campaign/<campaign_id:int>/<camp_name?>',
                     edit_campaign),
                POST('/admin/campaign/<campaign_id:int>/new/round',
                     create_round),
                POST('/admin/round/<round_id:int>/import', import_entries),
                POST('/admin/round/<round_id:int>/activate', activate_round),
                GET('/admin/round/<round_id:int>/<round_name?>',
                    get_round),
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
