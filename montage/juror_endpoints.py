
from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import JurorDAO
from utils import format_date, PermissionDenied, InvalidAction


def get_juror_routes():
    ret = [GET('/juror', get_index),
           GET('/juror/campaign/<campaign_id:int>', get_campaign),
           GET('/juror/round/<round_id:int>', get_round),
           GET('/juror/tasks', get_tasks),
           GET('/juror/round/<round_id:int>/tasks', get_tasks_from_round),
           POST('/juror/submit/rating', submit_rating),
           POST('/juror/bulk_submit/rating', bulk_submit_rating)]
    # TODO: submission for rank style votes
    # TODO: bulk rating submission
    return ret


def make_juror_round_details(rnd, rnd_stats):
    ret = {'id': rnd.id,
           'directions': rnd.directions,
           'name': rnd.name,
           'vote_method': rnd.vote_method,
           'open_date': format_date(rnd.open_date),
           'close_date': format_date(rnd.close_date),
           'deadline_date': format_date(rnd.deadline_date),
           'status': rnd.status,
           'canonical_url_name': slugify(rnd.name, '-'),
           'total_tasks': rnd_stats['total_tasks'],
           'total_open_tasks': rnd_stats['total_open_tasks'],
           'percent_tasks_open': rnd_stats['percent_tasks_open'],
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


VALID_RATINGS = (0.0, 0.25, 0.5, 0.75, 1.0)
VALID_YESNO = (0.0, 1.0)


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
    task_id = request_dict['task_id']
    rating = float(request_dict['rating'])
    task = juror_dao.get_task(task_id)
    rnd = task.round_entry.round
    if rnd.status != 'active':
        raise InvalidAction('round must be active to submit ratings.'
                            ' round is currently: %s' % rnd.status)
    if rnd.vote_method == 'rating':
        if rating not in VALID_RATINGS:
            raise InvalidAction('rating expected one of %s, not %r'
                                % (VALID_RATINGS, rating))
    elif rnd.vote_method == 'yesno':
        if rating not in VALID_YESNO:
            raise InvalidAction('rating expected one of %s, not %r'
                                % (VALID_YESNO, rating))
    if task.user != user:  # TODO: this should be handled by the dao get
        raise PermissionDenied()
    if not (task.complete_date or task.cancel_date):
        juror_dao.apply_rating(task, rating)

    # What should this return?
    return {'data': {'task_id': task_id, 'rating': rating}}

def bulk_submit_rating(rdb_session, user, request_dict):
    # TODO: Check permissions
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    ratings = request_dict.get('ratings')
    ret = []

    for rating in ratings:
        task_id = rating['task_id']
        rating_val = rating['rating']
        
        task = juror_dao.get_task(task_id)

        juror_dao.apply_rating(task, rating_val)

        ret.append({'task_id': task_id, 'rating': rating})

    return {'data': ret}

from itertools import groupby
MAX_RATINGS_SUBMIT = 100


def submit_ratings(rdb_session, user, request_dict):
    """message format:

    {"ratings": [{"task_id": 10, "value": 0.0}, {"task_id": 11, "value": 1.0}]}

    this function is used to submit ratings _and_ rankings. when
    submitting rankings does not support ranking ties at the moment
    """

    # TODO: can jurors change their vote?
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)

    r_dicts = request_dict['ratings']
    if len(r_dicts) > MAX_RATINGS_SUBMIT:
        raise InvalidAction('can submit up to 100 ratings at once, not %r'
                            % len(r_dicts))
    id_map = dict([(r['task_id'], r['value']) for r in r_dicts])
    if not len(id_map) == len(r_dicts):
        pass  # duplicate values

    tasks = juror_dao.get_tasks_by_id(id_map.keys())
    task_map = dict([(t.id, t) for t in tasks])
    round_id_set = set([t.round_entry.round_id for t in tasks])
    if not len(round_id_set) == 1:
        raise InvalidAction('can only submit ratings for one round at a time')
    rnd = juror_dao.get_round(list(round_id_set)[0])
    style = rnd.vote_method

    # validation
    if style == 'rating':
        invalid = [r not in VALID_RATINGS for r in id_map.values()]
        if invalid:
            raise InvalidAction('rating expected one of %s, not %r'
                                % (VALID_RATINGS, sorted(set(invalid))))
    elif style == 'yesno':
        invalid = [r not in VALID_YESNO for r in id_map.values()]
        if not all([r in VALID_YESNO for r in id_map.values()]):
            raise InvalidAction('yes/no rating expected one of %s, not %r'
                                % (VALID_YESNO, sorted(set(invalid))))
    elif style == 'ranking':
        invalid = [r for r in id_map.values() if r != int(r) or r < 0]
        if invalid:
            raise InvalidAction('ranking expects round numbers >= 0, not %r'
                                % (sorted(set(invalid))))
        ranks = sorted([int(v) for v in id_map.values()])
        if ranks != range(len(rnd.entries)):  # TODO: no support for ties yet
            raise InvalidAction('ranking expects contiguous unique numbers,'
                                ' 0 - %s, not %r' % (len(rnd.entries), ranks))

    if style in ('rating', 'yesno'):
        for t in tasks:
            juror_dao.apply_rating(t, id_map[t.id])
    elif style == 'ranking':
        # This part is designed to support ties ok though
        sorted_rs = sorted(r_dicts, key=lambda r: r['value'])
        sorted_rank_task_pairs = [(int(r['value']), task_map[r['task_id']])
                                  for r in sorted_rs]
        rank_items = [tuple(t) for r, t in
                      groupby(sorted_rank_task_pairs, key=lambda rt: rt[0])]
        #  rank_map = dict(rank_items)  # might be clearer

        juror_dao.apply_ranking(rank_items)

    return {}  # TODO?

JUROR_ROUTES = get_juror_routes()

# TODO: Cave -> key-value store
# TODO: flag RoundEntries (only applicable on ratings rounds?)
# TODO: entry ID lookup by filename (should also return uploader, etc.)
# TODO: manual disqualificatin for coordinators
