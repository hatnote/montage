
from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from utils import fmt_date, InvalidAction

from rdb import (CoordinatorDAO,
                 MaintainerDAO,
                 OrganizerDAO)


def make_admin_round_details(rnd, rnd_stats):
    if rnd_stats['total_tasks']:
        percent_tasks_open = (float(rnd_stats['total_open_tasks']) / rnd_stats['total_tasks'])*100
    else:
        percent_tasks_open = 0
    ret = {'id': rnd.id,
           'name': rnd.name,
           'directions': rnd.directions,
           'canonical_url_name': slugify(rnd.name, '-'),
           'vote_method': rnd.vote_method,
           'open_date': fmt_date(rnd.open_date),
           'close_date': fmt_date(rnd.close_date),
           'status': rnd.status,
           'quorum': rnd.quorum,
           'total_entries': len(rnd.entries),
           'total_tasks': rnd_stats['total_tasks'],
           'total_open_tasks': rnd_stats['total_open_tasks'],
           'percent_tasks_open': percent_tasks_open,
           'campaign': rnd.campaign.to_info_dict(),
           'jurors': [rj.to_details_dict() for rj in rnd.round_jurors]}
    # TODO: add total num of entries, total num of uploaders, round source info
    return ret


def create_campaign(user, rdb_session, request):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    if not user.is_maintainer or not user.is_organizer:
        raise Forbidden('must be a designated organizer to create campaigns')

    org_dao = OrganizerDAO(rdb_session, user)

    new_camp_name = request.form.get('name')
    open_date = request.form.get('open_date')
    close_date = request.form.get('close_date')

    campaign = org_dao.create_campaign(name=new_camp_name,
                                       open_date=open_date,
                                       close_date=close_date)
    # TODO: need completion info for each round
    data = campaign.to_details_dict()

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


def edit_campaign(rdb_session, user, campaign_id, request):
    """
    Summary: Change the settings for a round identified by a round ID.

    Request model:
        campaign_id:
            type: int64

    Response model: AdminCampaignDetails
    """
    campaign_dict = {}
    column_names = ['name', 'open_date', 'close_date']

    for column_name in column_names:
        if request.form.get(column_name):
            campaign_dict[column_name] = request.form.get(column_name)

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = coord_dao.edit_campaign(campaign_id, campaign_dict)
    return {'data': campaign_dict}


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

    rnd_dict = {}
    req_columns = ['jurors', 'name', 'vote_method']
    valid_vote_methods = ['ranking', 'rating', 'yesno']

    for column in req_columns:
        val = request.form.get(column)
        if not val:
            raise InvalidAction('%s is required to create a round' % val)
            # TODO: raise http error
        if column is 'jurors':
            val = val.split(',')
        if column is 'vote_method' and val not in valid_vote_methods:
            raise InvalidAction('%s is an invalid vote method' % val)
            # TODO: raise http error
        rnd_dict[column] = val

    default_quorum = len(rnd_dict['jurors'])
    rnd_dict['quorum'] = request.form.get('quorum', default_quorum)
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd_dict['campaign'] = coord_dao.get_campaign(campaign_id)
    # TODO: Confirm if campaign exists
    rnd = coord_dao.create_round(**rnd_dict)
    rnd_stats = coord_dao.get_round_task_counts(rnd.id)
    data = make_admin_round_details(rnd, rnd_stats)
    return {'data': data}


def edit_round(rdb_session, user, round_id, request):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    rnd_dict = {}
    column_names = ['name', 'description', 'directions', 'config_json']
    # Use specific methods to edit other columns:
    #  - status: activate_round, pause_round
    #  - quorum: [requires reallocation]
    #  - active_jurors: [requires reallocation]

    for column_name in column_names:
        if request.form.get(column_name):
            rnd_dict[column_name] = request.form.get(column_name)

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.edit_round(round_id, rnd_dict)
    return {'data': rnd_dict}


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
        data.append(campaign.to_details_dict())

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
    data = campaign.to_details_dict()
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
        total_entries:
            type: int64
        total_tasks:
            type: int64
        total_open_tasks:
            type: int64
        percent_open_tasks:
            type: float
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
    rnd_stats = coord_dao.get_round_task_counts(round_id)
    if rnd is None:
        raise Forbidden('not a coordinator for this round')
    # entries_info = user_dao.get_entry_info(round_id) # TODO

    # TODO: joinedload if this generates too many queries
    data = make_admin_round_details(rnd, rnd_stats)
    return {'data': data}


def get_audit_logs(rdb_session, user, request):
    if not user.is_maintainer:
        raise Forbidden('not allowed to view the audit log')

    limit = request.args.get('limit', 10)
    offset = request.args.get('offset', 0)

    main_dao = MaintainerDAO(rdb_session, user)
    audit_logs = main_dao.get_audit_log(limit=limit, offset=offset)
    data = [l.to_info_dict() for l in audit_logs]

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
                GET('/admin/campaign/<campaign_id:int>', get_campaign),
                POST('/admin/campaign/<campaign_id:int>/edit', edit_campaign),
                POST('/admin/campaign/<campaign_id:int>/new/round', create_round),
                POST('/admin/round/<round_id:int>/import', import_entries),
                POST('/admin/round/<round_id:int>/activate', activate_round),
                GET('/admin/round/<round_id:int>', get_round),
                POST('/admin/round/<round_id:int>/edit', edit_round),
                POST('/admin/add_organizer', add_organizer),
                POST('/admin/add_coordinator/campaign/<campaign_id:int>',
                     add_coordinator),
                GET('/admin/audit_logs', get_audit_logs)]



# - cancel round
# - update round
#   - no reassignment required: name, description, directions, display_settings
#   - reassignment required: quorum, active_jurors
#   - not updateable: id, open_date, close_date, vote_method, campaign_id/seq
