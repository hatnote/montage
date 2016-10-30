import unicodecsv
import io
import datetime

from collections import defaultdict

from clastic import GET, POST, Response
from clastic.errors import Forbidden
from boltons.strutils import slugify
from boltons.timeutils import isoparse

from utils import format_date, get_threshold_map, InvalidAction, DoesNotExist

from rdb import (CoordinatorDAO,
                 MaintainerDAO,
                 OrganizerDAO)


def get_admin_routes():
    """
    /role/(object/id/object/id/...)verb is the guiding principle
    """
    ret = [GET('/admin', get_index),
           POST('/admin/add_organizer', add_organizer),
           POST('/admin/add_campaign', create_campaign),  # was ../new/campaign
           GET('/admin/campaign/<campaign_id:int>', get_campaign),
           POST('/admin/campaign/<campaign_id:int>/edit', edit_campaign),
           POST('/admin/campaign/<campaign_id:int>/add_round',
                create_round),  # was ../new/round
           POST('/admin/campaign/<campaign_id:int>/add_coordinator',
                add_coordinator),  # was /admin/add_coordinator/campaign/...',
           POST('/admin/round/<round_id:int>/import', import_entries),
           POST('/admin/round/<round_id:int>/activate', activate_round),
           POST('/admin/round/<round_id:int>/pause', pause_round),
           GET('/admin/round/<round_id:int>', get_round),
           POST('/admin/round/<round_id:int>/edit', edit_round),
           POST('/admin/round/<round_id:int>/cancel', cancel_round),
           GET('/admin/round/<round_id:int>/preview_results',
               get_round_results_preview),
           POST('/admin/round/<round_id:int>/advance', advance_round),
           GET('/admin/round/<round_id:int>/disqualified',
               get_disqualified),
           POST('/admin/round/<round_id:int>/autodisqualify',
                autodisqualify),
           GET('/maintainer', get_maint_index),
           GET('/admin/round/<round_id:int>/results', get_results),
           GET('/admin/round/<round_id:int>/download', download_results_csv),
           GET('/maintainer/active_users', get_active_users),
           GET('/maintainer/campaign/<campaign_id:int>', get_maint_campaign),
           GET('/maintainer/round/<round_id:int>', get_maint_round),
           GET('/maintainer/round/<round_id:int>/results', get_results),
           GET('/maintainer/round/<round_id:int>/download', download_results_csv),
           # TODO: split out into round/campaign log endpoints
           GET('/maintainer/audit_logs', get_audit_logs)]
    return ret


def js_isoparse(date_str):
    try:
        ret = isoparse(date_str)
    except ValueError:
        # It may be a javascript Date object printed with toISOString()
        if date_str[-1] == 'Z':
            date_str = date_str[:-1]
        ret = isoparse(date_str)
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
           'config': rnd.config,
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


def get_active_users(user, rdb_session):
    if not (user.is_maintainer or user.is_organizer):
        raise Forbidden('must be a designated organizer to create campaigns')
    maint_dao = MaintainerDAO(rdb_session, user)
    users = maint_dao.get_active_users()
    data = []
    for user in users:
        ud = user.to_details_dict()
        ud['last_active_date'] = ud['last_active_date'].isoformat()
        data.append(ud)
    return {'data': data}


# TODO: (clastic) some way to mark arguments as injected from the
# request_dict such that the signature can be expanded here. the goal
# being that create_campaign can be a standalone function without any
# special middleware dependencies, to achieve a level of testing
# between the dao and server tests.
def create_campaign(user, rdb_session, request_dict):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    if not (user.is_maintainer or user.is_organizer):
        raise Forbidden('must be a designated organizer to create campaigns')

    org_dao = OrganizerDAO(rdb_session, user)

    name = request_dict.get('name')

    if not name:
        raise InvalidAction('name is required to create a campaign, got %r'
                            % name)
    now = datetime.datetime.utcnow().isoformat()
    open_date = request_dict.get('open_date', now)

    if open_date:
        open_date = js_isoparse(open_date)

    close_date = request_dict.get('close_date')

    if close_date:
        close_date = js_isoparse(close_date)

    coord_names = request_dict.get('coordinators')

    coords = [user]  # Organizer is included as a coordinator by default
    for coord_name in coord_names:
        coord = org_dao.get_or_create_user(coord_name, 'coordinator')
        coords.append(coord)

    campaign = org_dao.create_campaign(name=name,
                                       open_date=open_date,
                                       close_date=close_date,
                                       coords=set(coords))
    # TODO: need completion info for each round
    rdb_session.commit()
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
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)
    coords = rnd.campaign.coords

    if not user.is_maintainer and user not in coords:
        raise Forbidden('not allowed to import entries')

    import_method = request_dict.get('import_method')

    if import_method == 'gistcsv':
        gist_url = request_dict.get('gist_url')
        entries = coord_dao.add_entries_from_csv_gist(rnd, gist_url)
        source = 'gistcsv(%s)' % gist_url
    elif import_method == 'category':
        cat_name = request_dict.get('category')
        if not cat_name:
            raise InvalidAction('needs category name for import')
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

    return {'data': 'paused'}


def edit_campaign(rdb_session, user, campaign_id, request_dict):
    """
    Summary: Change the settings for a round identified by a round ID.

    Request model:
        campaign_id:
            type: int64

    Response model: AdminCampaignDetails
    """
    edit_dict = {}
    name = request_dict.get('name')
    if name:
        edit_dict['name'] = name
    open_date = request_dict.get('open_date')
    if open_date:
        edit_dict['open_date'] = js_isoparse(open_date)
    close_date = request_dict.get('close_date')
    if close_date:
        edit_dict['close_date'] = js_isoparse(close_date)

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    coord_dao.edit_campaign(campaign_id, edit_dict)

    rdb_session.commit()

    return {'data': edit_dict}


def _prepare_round_params(coord_dao, request_dict):
    rnd_dict = {}
    req_columns = ['jurors', 'name', 'vote_method', 'deadline_date']
    extra_columns = ['description', 'config', 'directions']
    valid_vote_methods = ['ranking', 'rating', 'yesno']

    for column in req_columns + extra_columns:
        val = request_dict.get(column)
        if not val and column in req_columns:
            raise InvalidAction('%s is required to create a round (got %r)'
                                % (column, val))
        if column is 'vote_method' and val not in valid_vote_methods:
            raise InvalidAction('%s is an invalid vote method' % val)
        if column is 'deadline_date':
            val = js_isoparse(val)
        if column is 'jurors':
            juror_names = val
        rnd_dict[column] = val

    default_quorum = len(rnd_dict['jurors'])
    rnd_dict['quorum'] = request_dict.get('quorum', default_quorum)
    rnd_dict['jurors'] = []

    for juror_name in juror_names:
        juror = coord_dao.get_or_create_user(juror_name, 'juror')

        rnd_dict['jurors'].append(juror)

    return rnd_dict


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

    rnd_params = _prepare_round_params(coord_dao, request_dict)
    rnd_params['campaign'] = campaign
    rnd = coord_dao.create_round(**rnd_params)

    rdb_session.commit()

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
    column_names = ['name', 'description', 'directions',
                    'config', 'new_jurors', 'deadline_date']
    # Use specific methods to edit other columns:
    #  - status: activate_round, pause_round
    #  - quorum: [requires reallocation]
    #  - active_jurors: [requires reallocation]

    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    if not rnd:
        raise DoesNotExist()

    new_val_map = {}

    for column_name in column_names:
        # val = request_dict.pop(column_name, None)  # see note below
        val = request_dict.get(column_name)
        if val is not None:
            if column_name == 'deadline_date':
                val = js_isoparse(val)
            setattr(rnd, column_name, val)
            new_val_map[column_name] = val

    # can't do this yet because stuff like su_to is hanging out in there.
    # if request_dict:
    #     raise InvalidAction('unable to modify round attributes: %r'
    #                         % request_dict.keys())

    new_juror_names = new_val_map.get('new_jurors')
    cur_jurors = coord_dao.get_active_jurors(rnd)
    cur_juror_names = [u.username for u in cur_jurors]

    if new_juror_names and set(new_juror_names) != set(cur_juror_names):
        if rnd.status != 'paused':
            raise InvalidAction('round must be paused to edit jurors')
        else:
            rnd = coord_dao.modify_jurors(rnd, new_val_map['new_jurors'])

    return {'data': new_val_map}


def cancel_round(rdb_session, user, round_id):
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    if not rnd:
        raise Forbidden('cannot access round')

    coord_dao.cancel_round(rnd)

    stats = rnd.get_count_map()
    return {'data': stats}


def get_round_results_preview(rdb_session, user, round_id):
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    round_counts = coord_dao.get_round_task_counts(rnd)
    is_closeable = round_counts['total_open_tasks'] == 0

    data = {'round': rnd.to_info_dict(),
            'counts': round_counts,
            'is_closeable': is_closeable}

    if rnd.vote_method in ('yesno', 'rating'):
        data['ratings'] = coord_dao.get_round_average_rating_map(rnd)
        data['thresholds'] = get_threshold_map(data['ratings'])
    elif rnd.vote_method == 'ranking':
        if not is_closeable:
            # TODO: should this sort of check apply to ratings as well?
            raise InvalidAction('round must be closeable to preview results')
        rankings = coord_dao.get_round_ranking_list(rnd)

        data['rankings'] = [r.to_dict() for r in rankings]

    else:
        raise NotImplementedError()

    return {'data': data}


def advance_round(rdb_session, user, round_id, request_dict):
    """Technical there are four possibilities.

    1. Advancing from yesno/rating to another yesno/rating
    2. Advancing from yesno/rating to ranking
    3. Advancing from ranking to yesno/rating
    4. Advancing from ranking to another ranking

    Especially for the first version of Montage, this function will
    only be written to cover the first two cases. This is because
    campaigns are designed to end with a single ranking round.

    typical advancements are: "yesno -> rating -> ranking" or
    "yesno -> rating -> yesno -> ranking"

    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    if not rnd:
        raise Forbidden('No permission to advance round %s, or round does not exist' % round_id)

    if rnd.vote_method not in ('rating', 'yesno'):
        raise NotImplementedError()  # see docstring above
    threshold = float(request_dict['threshold'])
    _next_round_params = request_dict['next_round']
    nrp = _prepare_round_params(coord_dao, _next_round_params)
    nrp['campaign'] = rnd.campaign

    if nrp['vote_method'] == 'ranking' \
       and len(nrp['jurors']) != nrp.get('quorum'):
        # TODO: log
        # (ranking round quorum must match juror count)
        nrp['quorum'] = len(nrp['jurors'])

    # TODO: inherit round config from previous round?
    coord_dao.finalize_rating_round(rnd, threshold=threshold)
    adv_group = coord_dao.get_rating_advancing_group(rnd, threshold)

    next_rnd = coord_dao.create_round(**nrp)
    source = 'round(#%s)' % rnd.id
    coord_dao.add_round_entries(next_rnd, adv_group, source=source)

    # NOTE: disqualifications are not repeated, as they should have
    # been performed the first round.

    next_rnd_dict = next_rnd.to_details_dict()
    next_rnd_dict['progress'] = coord_dao.get_round_task_counts(next_rnd)

    msg = ('%s advanced campaign %r (#%s) from %s round "%s" to %s round "%s"'
           % (user.username, rnd.campaign.name, rnd.campaign.id,
              rnd.vote_method, rnd.name, next_rnd.vote_method, next_rnd.name))
    coord_dao.log_action('advance_round', campaign=rnd.campaign, message=msg)

    return {'data': next_rnd_dict}


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
    user_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaigns = user_dao.get_all_campaigns()

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
    if rnd is None:
        raise Forbidden('not a coordinator for this round')

    rnd_stats = coord_dao.get_round_task_counts(rnd)
    # entries_info = user_dao.get_entry_info(round_id) # TODO

    # TODO: joinedload if this generates too many queries
    data = make_admin_round_details(rnd, rnd_stats)
    return {'data': data}


def make_vote_table(user_dao, rnd):
    if rnd.vote_method == 'ranking':
        all_ratings = user_dao.get_all_rankings(rnd)
    else:
        all_ratings = user_dao.get_all_ratings(rnd)
    all_tasks = user_dao.get_all_tasks(rnd)

    results_by_name = defaultdict(dict)
    ratings_dict = {r.task_id: r.value for r in all_ratings}

    for (task, entry) in all_tasks:
        rating = ratings_dict.get(task.id, {})
        filename = entry.name
        username = task.user.username

        if task.complete_date:
            results_by_name[filename][username] = rating
        else:
            # tbv = to be voted
            # there should be no empty tasks in a fully finalized round
            results_by_name[filename][username] = 'tbv'

    return results_by_name


def get_results(rdb_session, user, round_id, request_dict):
    # TODO: Quick hacky maintainer access
    # this should should be standardized throughout
    if user.is_maintainer:
        user_dao = MaintainerDAO(rdb_session=rdb_session, user=user)
        rnd = user_dao.get_round(round_id)
    else:
        user_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
        rnd = user_dao.get_round(round_id)

    if rnd is None:
        raise Forbidden('not a coordinator for this round')

    if not user.is_maintainer and rnd.status != 'finalized':
        raise DoesNotExist('round results not yet finalized')

    results_by_name = make_vote_table(user_dao, rnd)

    return {'data': results_by_name}


def download_results_csv(rdb_session, user, round_id, request_dict):
    if user.is_maintainer:
        user_dao = MaintainerDAO(rdb_session=rdb_session, user=user)
        rnd = user_dao.get_round(round_id)
    else:
        user_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
        rnd = user_dao.get_round(round_id)

    if rnd is None:
        raise Forbidden('not a coordinator for this round')

    if not user.is_maintainer and rnd.status != 'finalized':
        raise DoesNotExist('round results not yet finalized')

    results_by_name = make_vote_table(user_dao, rnd)

    output = io.BytesIO()
    csv_fieldnames = ['filename', 'average'] + [r.username for r in rnd.jurors]
    csv_writer = unicodecsv.DictWriter(output, fieldnames=csv_fieldnames,
                                       restval=None)
    # na means this entry wasn't assigned

    csv_writer.writeheader()

    for filename, ratings in results_by_name.items():
        csv_row = {'filename': filename}
        valid_ratings = [r for r in ratings.values() if type(r) is not str]
        if valid_ratings:
            # TODO: catch if there are more than a quorum of votes
            ratings['average'] = sum(valid_ratings) / len(valid_ratings)
        else:
            ratings['average'] = 'na'
        csv_row.update(ratings)
        csv_writer.writerow(csv_row)

    ret = output.getvalue()
    resp = Response(ret, mimetype='text/csv')
    resp.mimetype_params['charset'] = 'utf-8'
    resp.headers["Content-Disposition"] = "attachment; filename=montage_vote_report.csv"
    return resp


def autodisqualify(rdb_session, user, round_id, request_dict):
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    if rnd is None:
        raise Forbidden('not a coordinator for this round')

    if rnd.status != 'paused':
        raise InvalidAction('round must be paused to disqualify entries')

    dq_by_upload_date = request_dict.get('dq_by_upload_date')
    dq_by_resolution = request_dict.get('dq_by_resolution')
    dq_by_uploader = request_dict.get('dq_by_uploader')
    dq_by_filetype = request_dict.get('dq_by_filetype')

    round_entries = []

    if rnd.config.get('dq_by_upload_date') or dq_by_upload_date:
        dq_upload_date = coord_dao.autodisqualify_by_date(rnd)
        round_entries += dq_upload_date

    if rnd.config.get('dq_by_resolution') or dq_by_resolution:
        dq_resolution = coord_dao.autodisqualify_by_resolution(rnd)
        round_entries += dq_resolution

    if rnd.config.get('dq_by_uploader') or dq_by_uploader:
        dq_uploader = coord_dao.autodisqualify_by_uploader(rnd)
        round_entries += dq_uploader

    if rnd.config.get('dq_by_filetype') or dq_by_filetype:
        dq_filetype = coord_dao.autodisqualify_by_filetype(rnd)
        round_entries += dq_filetype

    data = [re.to_dq_details() for re in round_entries]

    return {'data': data}

def get_disqualified(rdb_session, user, round_id):
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)

    round_entries = coord_dao.get_disqualified(rnd)

    data = [re.to_dq_details() for re in round_entries]
    return {'data': data}

# Endpoints restricted to maintainers

def get_maint_index(rdb_session, user, request_dict):
    if not user.is_maintainer:
        raise Forbidden('You are not logged in as a maintainer')

    maint_dao = MaintainerDAO(rdb_session, user)
    campaigns = maint_dao.get_all_campaigns()

    data = []

    for campaign in campaigns:
        data.append(campaign.to_details_dict())

    return {'data': data}


def get_maint_campaign(rdb_session, user, campaign_id, request_dict):
    if not user.is_maintainer:
        raise Forbidden('You are not logged in as a maintainer')

    maint_dao = MaintainerDAO(rdb_session, user)
    campaign = maint_dao.get_campaign(campaign_id)
    if campaign is None:
        raise DoesNotExist('no campaigns available')

    data = campaign.to_details_dict()
    return {'data': data}


def get_maint_round(rdb_session, user, round_id, request_dict):
    if not user.is_maintainer:
        raise Forbidden('You are not logged in as a maintainer')

    maint_dao = MaintainerDAO(rdb_session, user)
    rnd = maint_dao.get_round(round_id)

    if rnd is None:
        raise DoesNotExist('no rounds available')
    # entries_info = user_dao.get_entry_info(round_id) # TODO

    rnd_stats = maint_dao.get_round_task_counts(rnd)

    data = make_admin_round_details(rnd, rnd_stats)
    return {'data': data}


def get_audit_logs(rdb_session, user, request):
    if not user.is_maintainer and not user.is_organizer:
        raise Forbidden('not allowed to view the audit log')

    limit = request.values.get('limit', 10)
    offset = request.values.get('offset', 0)

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
