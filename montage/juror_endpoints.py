
from itertools import groupby

from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import JurorDAO
from utils import format_date, PermissionDenied, InvalidAction

MAX_RATINGS_SUBMIT = 100
VALID_RATINGS = (0.0, 0.25, 0.5, 0.75, 1.0)
VALID_YESNO = (0.0, 1.0)


def get_juror_routes():
    """\
    The refactored routes for jurors, coming soon.

    * removed GET('/juror/round/<round_id:int>/tasks', get_tasks)
      because requests for tasks must be interpreted in the context of
      an active round. Specifically, ranking rounds must get and
      submit all tasks at once.

    * removed POST('/juror/bulk_submit/rating', bulk_submit_rating)
      and POST('/juror/submit/rating', submit_rating) in favor of the
      unified submission URL which includes the round_id
    """
    ret = [GET('/juror', get_index),
           GET('/juror/campaign/<campaign_id:int>', get_campaign),
           GET('/juror/round/<round_id:int>', get_round),
           GET('/juror/round/<round_id:int>/tasks', get_tasks_from_round),
           POST('/juror/round/<round_id:int>/tasks/submit', submit_ratings),
           GET('/juror/round/<round_id:int>/ratings', get_ratings_from_round),
           GET('/juror/round/<round_id:int>/rankings', get_rankings_from_round),
           POST('/juror/round/<round_id:int>/<entry_id:int>/fave', submit_fave),
           POST('/juror/round/<round_id:int>/<entry_id:int>/unfave',
                remove_fave),
           POST('/juror/round/<round_id:int>/<entry_id:int>/flag', submit_flag),
           GET('/juror/faves', get_faves)]
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
           'config': rnd.config,
           'total_tasks': rnd_stats['total_tasks'],
           'total_open_tasks': rnd_stats['total_open_tasks'],
           'percent_tasks_open': rnd_stats['percent_tasks_open'],
           'campaign': rnd.campaign.to_info_dict()}
    return ret


# Endpoint functions

def get_index(user_dao):
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
    juror_dao = JurorDAO(user_dao)
    stats = [make_juror_round_details(rnd, rnd_stats)
             for rnd, rnd_stats
             in juror_dao.get_all_rounds_task_counts()]
    return stats


def get_campaign(user_dao, campaign_id):
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
    juror_dao = JurorDAO(user_dao)
    campaign = juror_dao.get_campaign(campaign_id)
    data = campaign.to_details_dict()
    rounds = []
    for rnd in campaign.rounds:
        rnd_stats = user_dao.get_round_task_counts(rnd.id)
        rounds.append(make_juror_round_details(rnd, rnd_stats))
    data['rounds'] = rounds
    return {'data': data}


def get_round(user_dao, round_id):
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
    juror_dao = JurorDAO(user_dao)
    rnd = juror_dao.get_round(round_id)
    rnd_stats = juror_dao.get_round_task_counts(round_id)
    data = make_juror_round_details(rnd, rnd_stats)  # TODO: add to Round model
    return {'data': data}


def get_campaign_info(user_dao, campaign_id):
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
    juror_dao = JurorDAO(use_dao)
    campaign = juror_dao.get_campaign(campaign_id)
    ret = CampaignInfo(campaign)  # TODO: add as a method on the Round model?
    return {'data': ret}


def get_tasks(user_dao, request):
    """
    Summary: Get the next tasks for a juror.

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
    # TODO: this needs a round. a given user can be participating in
    # multiple campaigns at once.
    count = request.values.get('count', 15)
    offset = request.values.get('offset', 0)
    juror_dao = JurorDAO(user_dao)
    tasks = juror_dao.get_tasks(num=count, offset=offset)
    stats = juror_dao.get_task_counts()
    data = {'stats': stats,
            'tasks': []}
    for task in tasks:
        data['tasks'].append(task.to_details_dict())
    return {'data': data}


def get_tasks_from_round(user_dao, round_id, request):
    count = request.values.get('count', 15)
    offset = request.values.get('offset', 0)
    juror_dao = JurorDAO(user_dao)
    juror_dao.confirm_active(round_id)
    rnd = juror_dao.get_round(round_id)
    if rnd.vote_method == 'ranking':
        count = MAX_RATINGS_SUBMIT  # TODO: better constant
    tasks = juror_dao.get_tasks_from_round(round_id,
                                           num=count,
                                           offset=offset)
    stats = juror_dao.get_round_task_counts(round_id)
    data = {'stats': stats,
            'tasks': []}

    for task in tasks:
        data['tasks'].append(task.to_details_dict())

    return {'data': data}


def get_ratings_from_round(user_dao, round_id, request):
    count = request.values.get('count', 15)
    offset = request.values.get('offset', 0)
    juror_dao = JurorDAO(user_dao)
    ratings = juror_dao.get_ratings_from_round(round_id,
                                               num=count,
                                               offset=offset)
    data = [r.to_details_dict() for r in ratings]
    return {'data': data}


def get_rankings_from_round(user_dao, round_id):
    juror_dao = JurorDAO(user_dao)
    rankings = juror_dao.get_rankings_from_round(round_id)
    data = [r.to_details_dict() for r in rankings]
    data.sort(key=lambda x: x['value'])
    return {'data': data}


def get_faves(user_dao, request_dict):
    juror_dao = JurorDAO(user_dao)
    limit = request_dict.get('limit', 10)
    offset = request_dict.get('offset', 0)
    faves = juror_dao.get_favtes(limit, offset)
    return {'data': faves}


def submit_rating(user_dao, request_dict):
    # TODO: Check permissions
    juror_dao = JurorDAO(user_dao)
    vote_id = request_dict['vote_id']
    rating = float(request_dict['rating'])
    task = juror_dao.get_task(vote_id)
    rnd = task.round_entry.round
    rnd.confirm_active()
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
    if task.status == 'active':
        juror_dao.apply_rating(task, rating)

    # What should this return?
    return {'data': {'vote_id': vote_id, 'rating': rating}}


def submit_ratings(user_dao, request_dict):
    """message format:

    {"ratings": [{"vote_id": 10, "value": 0.0}, {"vote_id": 11, "value": 1.0}]}

    this function is used to submit ratings _and_ rankings. when
    submitting rankings does not support ranking ties at the moment
    """

    # TODO: can jurors change their vote?
    juror_dao = JurorDAO(user_dao)

    r_dicts = request_dict['ratings']

    if len(r_dicts) > MAX_RATINGS_SUBMIT:
        raise InvalidAction('can submit up to 100 ratings at once, not %r'
                            % len(r_dicts))
    elif not r_dicts:
        return {}  # submitting no ratings = immediate return

    for rd in r_dicts:
        review = rd.get('review') or ''
        review_stripped = review.strip()
        if len(review_stripped) > 8192:
            raise ValueError('review must be less than 8192 chars,'
                             ' not %r' % len(review_stripped))
    try:
        id_map = dict([(r['vote_id'], r['value']) for r in r_dicts])
    except KeyError as e:
        # fallback for old versions
        id_map = dict([(r['task_id'], r['value']) for r in r_dicts])
    if not len(id_map) == len(r_dicts):
        pass  # duplicate values

    tasks = juror_dao.get_tasks_by_id(id_map.keys())
    task_map = dict([(t.id, t) for t in tasks])
    round_id_set = set([t.round_entry.round_id for t in tasks])
    if not len(round_id_set) == 1:
        import pdb;pdb.set_trace()
        raise InvalidAction('can only submit ratings for one round at a time')

    round_id = list(round_id_set)[0]
    rnd = juror_dao.get_round(round_id)
    rnd.confirm_active()
    style = rnd.vote_method

    # validation
    if style == 'rating':
        invalid = [r for r in id_map.values() if r not in VALID_RATINGS]
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
            raise InvalidAction('ranking expects whole numbers >= 0, not %r'
                                % (sorted(set(invalid))))
        ranks = sorted([int(v) for v in id_map.values()])
        last_rank = max(ranks)
        len_rnd_entries = len(rnd.entries)
        max_ok_rank = len_rnd_entries - 1
        if last_rank > max_ok_rank:
            raise InvalidAction('ranking for round #%s expects ranks 0 - %s,'
                                ' not %s' % (rnd.id, max_ok_rank, last_rank))
        if len_rnd_entries != len(id_map):
            raise InvalidAction('must submit all rankings at once.'
                                ' (expected %s submissions, got %s.)'
                                % (len_rnd_entries, len(id_map)))

    if style in ('rating', 'yesno'):
        for t in tasks:
            val = id_map[t.id]
            juror_dao.edit_rating(t, val)
    elif style == 'ranking':
        # This part is designed to support ties ok though
        """
        [{"vote_id": 123,
          "value": 0,
          "review": "The light dances across the image."}]
        """
        ballot = []
        is_edit = False
        for rd in r_dicts:
            cur = dict(rd)
            vote_id = rd.get('vote_id')
            if not vote_id:
                vote_id = rd.get('task_id')  # fallback for old versions of the client
            cur['vote'] = task_map[vote_id]
            if cur['vote'].status == 'complete':
                is_edit = True
            elif is_edit:
                raise InvalidAction('all tasks must be complete or incomplete')
            ballot.append(cur)

        juror_dao.apply_ranking(ballot)

    return {}  # TODO?


def submit_fave(user_dao, round_id, entry_id):
    juror_dao = JurorDAO(user_dao)
    juror_dao.fave(round_id, entry_id)


def remove_fave(user_dao, round_id, entry_id):
    juror_dao = JurorDAO(user_dao)
    juror_dao.unfave(round_id, entry_id)


def submit_flag(user_dao, round_id, entry_id, request_dict):
    juror_dao = JurorDAO(user_dao)
    reason = request_dict.get('reason')
    juror_dao.flag(round_id, entry_id, reason)



JUROR_ROUTES = get_juror_routes()

# TODO: Cave -> key-value store
# TODO: flag RoundEntries (only applicable on ratings rounds?)
# TODO: entry ID lookup by filename (should also return uploader, etc.)
# TODO: manual disqualificatin for coordinators
