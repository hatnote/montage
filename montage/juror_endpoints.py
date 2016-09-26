
from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import JurorDAO
from utils import fmt_date
from imgutils import make_mw_img_url


# API Spec

def make_juror_campaign_info(campaign):
    ret = {'id': campaign.id,
           'name': campaign.name,
           'canonical_url_name': slugify(campaign.name)}

    return ret


def make_juror_campaign_details(campaign):
    ret = {'id': campaign.id,
           'name': campaign.name,
           'canonical_url_name': slugify(campaign.name),
           'rounds': None,  # must get rnd_stats for each below
           'coordinators': [make_coord_details(coord) for coord in campaign.coords]}
    return ret

def make_juror_round_info(rnd):
    ret = {'id': rnd.id,
           'name': rnd.name,
           'canonical_url_name': slugify(rnd.name)}

    return ret

def make_juror_round_details(rnd, rnd_stats):
    if rnd_stats['total_tasks']:
        percent_tasks_open = (float(rnd_stats['total_open_tasks']) / rnd_stats['total_tasks'])*100
    else:
        percent_tasks_open = 0
    ret = {'id': rnd.id,
           'directions':  rnd.directions,
           'name': rnd.name,
           'vote_method': rnd.vote_method,
           'open_date': fmt_date(rnd.open_date),
           'close_date': fmt_date(rnd.close_date),
           'status': rnd.status,
           'canonical_url_name': slugify(rnd.name, '-'),
           'total_tasks': rnd_stats['total_tasks'],
           'total_open_tasks': rnd_stats['total_open_tasks'],
           'percent_tasks_open': percent_tasks_open,
           'campaign': make_juror_campaign_info(rnd.campaign)}
    return ret


def make_juror_task_details(task):
    ret = {'id': task.id,
           'round_entry_id': task.round_entry_id,
           'entry': make_entry_details(task.entry)}
    return ret


def make_entry_details(entry):
    ret = {'id': entry.id,
           'upload_date': fmt_date(entry.upload_date),
           'mime_major': entry.mime_major,
           'mime_minor': entry.mime_minor,
           'name': entry.name,
           'upload_user_text': entry.upload_user_text,  # TODO: only if allowed by round options
           'height': entry.height,
           'width': entry.width,
           'url': make_mw_img_url(entry.name),
           'resolution': entry.resolution}
    return ret


def make_coord_details(coord):
    ret = {'username': coord.username}
    return ret


# Endpoint functions

def get_index(rdb_session, user):
    """
    Summary: Get juror-level index of all campaigns and rounds.

    Response model name: JurorCampaignIndex
    Response model:
        campaigns:
            type: array
            items:
                type: JurorRoundDetails

    Errors:
       403: User does not have permission to access any rounds
    """
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    rounds = juror_dao.get_all_rounds()
    if len(rounds) == 0:
        raise Forbidden('not a juror for any rounds')
    data = []
    for rnd in rounds:
        rnd_stats = juror_dao.get_round_task_counts(rnd.id)
        rnd_details = make_juror_round_details(rnd, rnd_stats)
        data.append(rnd_details)
    return {'data': data}


def get_campaign(rdb_session, user, campaign_id):
    """
    Summary: Get juror-level list of rounds, identified by campaign ID.

    Request model:
        campaign_id:
            type: int64

    Response model name: JurorCampaignDetails
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
                type: JurorRoundDetails
        coordinators:
            type: array
            items:
                type: CoordDetails

    Errors:
       403: User does not have permission to access the requested campaign
       404: Campaign not found
    """
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    campaign = juror_dao.get_campaign(campaign_id)
    if campaign is None:
        raise Forbidden('not a juror for this campaign')
    data = make_juror_campaign_details(campaign)
    rounds = []
    for rnd in campaign.rounds:
        rnd_stats = juror_dao.get_round_task_counts(rnd.id)
        rounds.append(make_juror_round_details(rnd, rnd_stats))
    data['rounds'] = rounds
    return {'data': data}


def get_round(rdb_session, user, round_id):
    """
    Summary: Get juror-level details for a round, identified by round ID.

    Request model:
        round_id:
            type: int64

    Response model name: JurorRoundDetails
    Response model:
        id:
            type: int64
        name:
            type: string
        canonical_url_name:
            type: string
        directions:
            type: string
        vote_method:
            type: string
        status:
            type: string
        open_date:
            type: date-time
        close_date:
            type: date-time
        campaign:
            type: CampaignInfo

    Errors:
       403: User does not have permission to access requested round
       404: Round not found
    """
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    rnd = juror_dao.get_round(round_id)
    rnd_stats = juror_dao.get_round_task_counts(round_id)
    if rnd is None:
        raise Forbidden('not a juror for this round')
    data = make_juror_round_details(rnd, rnd_stats)
    return {'data': data}


def get_campaign_info(rdb_session, user, campaign_id):
    """
    Summary: Get juror-level info for a round, identified by campaign ID.

    Request model:
        campaign_id:
            type: int64

    Response model name: JurorCampaignInfo
    Response model:
        id:
            type: int64
        name:
            type: string
        canonical_url_name:
            type: string

    Errors:
       403: User does not have permission to access requested campaign
       404: Campaign not found
    """
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    campaign = juror_dao.get_campaign(campaign_id)
    if campaign is None:
        raise Forbidden('not a juror for this round')
    ret = CampaignInfo(campaign)
    return ret


def get_tasks(rdb_session, user, request):
    """
    Summary: Get the next tasks for a juror

    Request model:
        count:
            default: 3
            type: int64
        offeset:
            default: 0
            type: int64

    Response model name: JurorTaskDetails
    Response model:
        id:
            type: int64
        entry:
            type: EntryInfo

    Errors:
       403: User does not have permission to access any tasks
       404: Tasks not found
    """
    count = request.values.get('count', 15)
    offset = request.values.get('offset', 0)
    juror_dao = JurorDAO(rdb_session, user)
    tasks = juror_dao.get_tasks(num=count, offset=offset)
    data = []

    for task in tasks:
        data.append(make_juror_task_details(task))

    return {'data': data}


def get_tasks_from_round(rdb_session, user, round_id, request):
    """
    Summary: Get the next tasks for a juror

    Request model:
        round_id:
            type:int64
        count:
            default: 3
            type: int64
        offeset:
            default: 0
            type: int64

    Response model name: JurorTaskDetails

    Errors:
       403: User does not have permission to access any tasks in the requested round
       404: Round not found
    """
    # TODO: get task from within a round
    # TODO: Check permissions
    count = request.values.get('count', 15)
    offset = request.values.get('offset', 0)
    juror_dao = JurorDAO(rdb_session, user)
    tasks = juror_dao.get_tasks_from_round(round_id=round_id, num=count, offset=offset)
    data = []

    for task in tasks:
        data.append(make_juror_task_details(task))

    return {'data': data}


def submit_rating(rdb_session, user, request):
    """
    Summary: Post a rating-type vote for an entry

    Request model:
        task_id:
            type: int64
        rating:
            type: int64

    Response model name: JurorRatingResults
    Response model:
        task_id:
            type: int64
        rating:
            type: int64

    Errors:
       403: User cannot submit ratings
       404: Task not found
    """
    # TODO: Check permissions
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    # TODO: Confirm if task is open and valid
    task_id = request.form.get('task_id')
    rating = request.form.get('rating')
    result = juror_dao.apply_rating(task_id, rating)
    return {'data': {'task_id': task_id, 'rating': rating}}  # What should this return?


juror_routes = [GET('/juror', get_index),
                GET('/juror/campaign/<campaign_id:int>', get_campaign),
                GET('/juror/round/<round_id:int>', get_round),
                GET('/juror/tasks', get_tasks),
                GET('/juror/round/<round_id:int>/tasks', get_tasks_from_round),
                POST('/juror/submit/rating', submit_rating)]  # TODO: submission for rank style votes
