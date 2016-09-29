
from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify
from boltons.timeutils import isoparse

from utils import format_date, get_threshold_map, InvalidAction, DoesNotExist

from rdb import (CoordinatorDAO,
                 MaintainerDAO,
                 OrganizerDAO)


def get_admin_routes():
    ret = [GET('/admin', get_index),
           POST('/admin/new/campaign', create_campaign),
           GET('/admin/campaign/<campaign_id:int>', get_campaign),
           POST('/admin/campaign/<campaign_id:int>/edit', edit_campaign),
           POST('/admin/campaign/<campaign_id:int>/new/round', create_round),
           POST('/admin/round/<round_id:int>/import', import_entries),
           POST('/admin/round/<round_id:int>/activate', activate_round),
           POST('/admin/round/<round_id:int>/pause', pause_round),
           GET('/admin/round/<round_id:int>', get_round),
           POST('/admin/round/<round_id:int>/edit', edit_round),
           POST('/admin/round/<round_id:int>/edit_jurors', modify_jurors),
           GET('/admin/round/<round_id:int>/preview_results',
               get_round_results_preview),
           POST('/admin/round/<round_id:int>/finalize',
                finalize_round),
           POST('/admin/add_organizer', add_organizer),
           POST('/admin/add_coordinator/campaign/<campaign_id:int>',
                add_coordinator),
           GET('/admin/audit_logs', get_audit_logs)]
    return ret


def make_admin_round_details(rnd, rnd_stats):
    """
    Same as juror, but with: quorum, total_entries, jurors
    """
    ret = {'id': rnd.id,
           'name': rnd.name,
           'directions': rnd.directions,
           'canonical_url_name': slugify(rnd.name, '-'),
           'vote_method': rnd.vote_method,
           'open_date': format_date(rnd.open_date),
           'close_date': format_date(rnd.close_date),
           'deadline_date': format_date(rnd.deadline_date),
           'status': rnd.status,
           'quorum': rnd.quorum,
           'total_entries': len(rnd.entries),
           'total_tasks': rnd_stats['total_tasks'],
           'total_open_tasks': rnd_stats['total_open_tasks'],
           'percent_tasks_open': rnd_stats['percent_tasks_open'],
           'campaign': rnd.campaign.to_info_dict(),
           'jurors': [rj.to_details_dict() for rj in rnd.round_jurors]}
    # TODO: add total num of entries, total num of uploaders, round source info
    return ret


def create_campaign(user, rdb_session, request_dict):
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

    new_camp_name = request_dict.get('name')
    open_date = request_dict.get('open_date')
    close_date = request_dict.get('close_date')
    coord_names = request_dict.get('coordinators') or []

    coords = []
    for coord_name in coord_names:
        coord = org_dao.get_or_create_user(coord_name, 'coordinator')
        coords.append(coord)

    campaign = org_dao.create_campaign(name=new_camp_name,
                                       open_date=open_date,
                                       close_date=close_date,
                                       coords=coords)
    # TODO: need completion info for each round
    data = campaign.to_details_dict()

    return {'data': data}


def import_entries(rdb_session, user, round_id, request_dict):
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

    import_method = request_dict.get('import_method')

    if import_method == 'gistcsv':
        gist_url = request_dict.get('gist_url')
        entries = coord_dao.add_entries_from_csv_gist(rnd, gist_url)
        source = 'gistcsv(%s)' % gist_url
    elif import_method == 'category':
        cat_name = request_dict.get('category')
        entries = coord_dao.add_entries_from_cat(rnd, cat_name)
        source = 'category(%s)' % cat_name
    else:
        raise NotImplementedError()

    new_entries = coord_dao.add_round_entries(rnd, entries, source=source)

    data = {'round_id': rnd.id,
            'new_entry_count': len(entries),
            'new_round_entry_count': len(new_entries),
            'total_entries': len(rnd.entries)}
    return {'data': data}


def activate_round(rdb_session, user, round_id, request_dict):
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
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    coord_dao.activate_round(rnd)

    ret_data = coord_dao.get_round_task_counts(rnd)
    ret_data['round_id'] = round_id
    return {'data': ret_data}

def pause_round(rdb_session, user, round_id, request_dict):
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)
    if not rnd:
        raise DoesNotExist()

    coord_dao.pause_round(rnd)

    return {'data': rnd}


def edit_campaign(rdb_session, user, campaign_id, request_dict):
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
        if request_dict.get(column_name):
            campaign_dict[column_name] = request_dict.get(column_name)

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = coord_dao.edit_campaign(campaign_id, campaign_dict)
    return {'data': campaign_dict}


def create_round(rdb_session, user, campaign_id, request_dict):
    """
    Summary: Post a new round

    Request model:
        campaign_id:
            type: int64

    Response model: AdminCampaignDetails
    """
    coord_dao = CoordinatorDAO(rdb_session, user)
    campaign = coord_dao.get_campaign(campaign_id)

    rnd_dict = {}
    req_columns = ['jurors', 'name', 'vote_method', 'deadline_date']
    valid_vote_methods = ['ranking', 'rating', 'yesno']

    for column in req_columns:
        val = request_dict.get(column)
        if not val:
            raise InvalidAction('%s is required to create a round' % val)
        if column is 'vote_method' and val not in valid_vote_methods:
            raise InvalidAction('%s is an invalid vote method' % val)
        if column is 'deadline_date':
            val = isoparse(val)
        if column is 'jurors':
            juror_names = val
        rnd_dict[column] = val

    default_quorum = len(rnd_dict['jurors'])
    rnd_dict['quorum'] = request_dict.get('quorum', default_quorum)
    rnd_dict['campaign'] = campaign
    rnd_dict['jurors'] = []

    for juror_name in juror_names:
        juror = coord_dao.get_or_create_user(juror_name, 'juror')

        rnd_dict['jurors'].append(juror)

    rnd = coord_dao.create_round(**rnd_dict)

    data = rnd.to_details_dict()
    data['progress'] = coord_dao.get_round_task_counts(rnd)

    return {'data': data}


def edit_round(rdb_session, user, round_id, request_dict):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    column_names = ['name', 'description', 'directions', 'config']
    # Use specific methods to edit other columns:
    #  - status: activate_round, pause_round
    #  - quorum: [requires reallocation]
    #  - active_jurors: [requires reallocation]

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    new_val_map = {}

    for column_name in column_names:
        # val = request_dict.pop(column_name, None)  # see note below
        val = request_dict.get(column_name)
        if val is not None:
            setattr(rnd, column_name, val)
            new_val_map[column_name] = val

    # can't do this yet because stuff like su_to is hanging out in there.
    # if request_dict:
    #     raise InvalidAction('unable to modify round attributes: %r'
    #                         % request_dict.keys())

    return {'data': new_val_map}


def modify_jurors(rdb_session, user, round_id, request_dict):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    rnd_dict = {}
    new_jurors = request_dict.get('new_jurors')

    if not new_jurors:
        raise InvalidAction()

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    # TODO: Check if the number of jurors is valid (eg more than quorum)?

    if not rnd:
        raise DoesNotExist()

    if rnd.status != 'paused':
        raise InvalidAction('round must be paused to edit jurors')

    rnd = coord_dao.modify_jurors(rnd, new_jurors)

    return {'data': rnd_dict}


def get_round_results_preview(rdb_session, user, round_id):
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    round_counts = coord_dao.get_round_task_counts(rnd)
    is_closeable = round_counts['total_open_tasks'] == 0

    rating_map = coord_dao.get_round_average_rating_map(rnd)
    thresh_map = get_threshold_map(rating_map)

    return {'data': {'round': rnd.to_info_dict(),
                     'counts': round_counts,
                     'ratings': rating_map,
                     'thresholds': thresh_map,
                     'is_closeable': is_closeable}}


def finalize_round(rdb_session, user, round_id, request_dict):
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    if rnd.voting_method in ('rating', 'yesno'):
        threshold = request_dict['threshold']
        coord_dao.finalize_rating_round(rnd, threshold=threshold)
    else:
        raise NotImplementedError()
    return {}


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
    rnd_stats = coord_dao.get_round_task_counts(rnd)
    if rnd is None:
        raise Forbidden('not a coordinator for this round')
    # entries_info = user_dao.get_entry_info(round_id) # TODO

    # TODO: joinedload if this generates too many queries
    data = make_admin_round_details(rnd, rnd_stats)
    return {'data': data}


def get_audit_logs(rdb_session, user, request_dict):
    if not user.is_maintainer:
        raise Forbidden('not allowed to view the audit log')

    limit = request_dict.get('limit', 10)
    offset = request_dict.get('offset', 0)

    main_dao = MaintainerDAO(rdb_session, user)
    audit_logs = main_dao.get_audit_log(limit=limit, offset=offset)
    data = [l.to_info_dict() for l in audit_logs]

    return {'data': data}


def add_organizer(rdb_session, user, request_dict):
    """
    Summary: Add a new organizer identified by Wikimedia username

    Request mode:
        username:
            type: string

    Response model:
        username:
            type: string
        last_active_date:
            type: date-time

    Errors:
       403: User does not have permission to add organizers
    """
    if not user.is_maintainer:
        raise Forbidden('not allowed to add organizers')

    maint_dao = MaintainerDAO(rdb_session, user)
    new_user_name = request_dict.get('username')
    new_organizer = maint_dao.add_organizer(new_user_name)
    data = {'username': new_organizer.username,
            'last_active_date': format_date(new_organizer.last_active_date)}
    return {'data': data}


def add_coordinator(rdb_session, user, campaign_id, request_dict):
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
        last_active_date:
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
    new_user_name = request_dict.get('username')
    campaign = org_dao.get_campaign(campaign_id)
    new_coord = org_dao.add_coordinator(campaign, new_user_name)
    data = {'username': new_coord.username,
            'campaign_id': campaign_id,
            'last_active_date': format_date(new_coord.last_active_date)}
    return {'data': data}


ADMIN_ROUTES = get_admin_routes()


# - cancel round
# - update round
#   - no reassignment required: name, description, directions, display_settings
#   - reassignment required: quorum, active_jurors
#   - not updateable: id, open_date, close_date, vote_method, campaign_id/seq
