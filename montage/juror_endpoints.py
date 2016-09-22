
from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import JurorDAO


def get_juror_index(rdb_session, user):
    """
    Summary: Get juror-level index of all campaigns and rounds.

    Response model name: JurorCampaignIndex
    Response model:
        campaigns:
            type: array
            items:
                type: JurorCampaignDetails

    Errors:
       403: User does not have permission to access any rounds
    """
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    rounds = juror_dao.get_all_rounds()
    if len(rounds) == 0:
        raise Forbidden('not a juror for any rounds')
    info = [rnd.to_dict() for rnd in rounds]
    return info


def get_juror_campaign(rdb_session, user, campaign_id):
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
        url_name:
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
    info = {'id': campaign.id,
            'name': campaign.name,
            'rounds': [],
            'coords': [u.username for u in campaign.coords]}
    for rnd in campaign.rounds:
        info['rounds'].append(get_juror_round(rdb_session, user, rnd.id))

    info['canonical_url_name'] = slugify(info['name'], '-')
    return info


def get_juror_round(rdb_session, user, round_id):
    """
    Summary: Get juror-level details for a round, identified by round ID.

    Request model:
        round_id:
            type: int64

    Response model name: JurorCampaignDetails
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
    if rnd is None:
        raise Forbidden('not a juror for this round')
    info = rnd.to_dict()
    return info


def get_tasks(rdb_session, user, round_id, request):
    # TODO: get task from within a round
    # TODO: Check permissions
    count = request.values.get('count', 3)
    offset = request.values.get('offset', 0)
    juror_dao = JurorDAO(rdb_session, user)
    tasks = juror_dao.get_next_task(num=count, offset=offset)
    return tasks

def submit_vote(rdb_session, user, request):
    # TODO: Check permissions
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    # TODO: Confirm if task is open and valid
    task_id = request.form.get('task_id')
    rating = request.form.get('rating')
    ret = juror_dao.apply_rating(task_id, rating)
    return ret # what should return?


juror_routes = [GET('/juror', get_juror_index),
                GET('/juror/campaign/<campaign_id:int>', get_juror_campaign),
                GET('/juror/round/<round_id:int>', get_juror_round),
                GET('/juror/round/<round_id:int>/tasks', get_tasks),
                POST('/juror/submit/rating', submit_vote)]
