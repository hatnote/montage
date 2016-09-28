
from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import JurorDAO
from utils import format_date, PermissionDenied


def get_juror_routes():
    ret = [GET('/juror', get_index),
           GET('/juror/campaign/<campaign_id:int>', get_campaign),
           GET('/juror/round/<round_id:int>', get_round),
           GET('/juror/tasks', get_tasks),
           GET('/juror/round/<round_id:int>/tasks', get_tasks_from_round),
           POST('/juror/submit/rating', submit_rating)]
    # TODO: submission for rank style votes
    # TODO: bulk rating submission
    return ret


def make_juror_round_details(rnd, rnd_stats):
    if rnd_stats['total_tasks']:
        percent_tasks_open = (float(rnd_stats['total_open_tasks']) / rnd_stats['total_tasks'])*100
    else:
        percent_tasks_open = 0
    ret = {'id': rnd.id,
           'directions': rnd.directions,
           'name': rnd.name,
           'vote_method': rnd.vote_method,
           'open_date': format_date(rnd.open_date),
           'close_date': format_date(rnd.close_date),
           'status': rnd.status,
           'canonical_url_name': slugify(rnd.name, '-'),
           'total_tasks': rnd_stats['total_tasks'],
           'total_open_tasks': rnd_stats['total_open_tasks'],
           'percent_tasks_open': percent_tasks_open,
           'campaign': rnd.campaign.to_info_dict()}
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
        rnd_stats = juror_dao.get_round_task_counts(rnd)
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
    data = campaign.to_details_dict()
    rounds = []
    for rnd in campaign.rounds:
        rnd_stats = juror_dao.get_round_task_counts(rnd)
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
    rnd_stats = juror_dao.get_round_task_counts(rnd)
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
        data.append(task.to_details_dict())

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
    rnd = juror_dao.get_round(round_id)
    if not rnd:
        raise PermissionDenied()
    tasks = juror_dao.get_tasks_from_round(rnd=rnd,
                                           num=count,
                                           offset=offset)
    data = []

    for task in tasks:
        data.append(task.to_details_dict())

    return {'data': data}


def submit_rating(rdb_session, user, request_dict):
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
    task_id = request_dict.get('task_id')
    rating = request_dict.get('rating')
    task = juror_dao.get_task(task_id)

    juror_dao.apply_rating(task, rating)
    # What should this return?
    return {'data': {'task_id': task_id, 'rating': rating}}


JUROR_ROUTES = get_juror_routes()
