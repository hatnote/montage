
from itertools import groupby

from clastic import GET, POST
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import JurorDAO
from utils import format_date, PermissionDenied, InvalidAction

MAX_RATINGS_SUBMIT = 100
VALID_RATINGS = (0.0, 0.25, 0.5, 0.75, 1.0)
VALID_YESNO = (0.0, 1.0)


# these are set at the bottom of the module
JUROR_API_ROUTES, JUROR_UI_ROUTES = None, None


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
    api = [GET('/juror', get_index),
           GET('/juror/campaign/<campaign_id:int>', get_campaign),
           GET('/juror/round/<round_id:int>', get_round),
           GET('/juror/round/<round_id:int>/tasks', get_tasks_from_round),
           POST('/juror/round/<round_id:int>/tasks/submit', submit_ratings),
           POST('/juror/round/<round_id:int>/tasks/skip', skip_rating),
           GET('/juror/round/<round_id:int>/votes', get_votes_from_round),
           GET('/juror/round/<round_id:int>/ratings', get_ratings_from_round),
           GET('/juror/round/<round_id:int>/rankings', get_rankings_from_round),
           POST('/juror/round/<round_id:int>/<entry_id:int>/fave', submit_fave),
           POST('/juror/round/<round_id:int>/<entry_id:int>/unfave',
                remove_fave),
           POST('/juror/round/<round_id:int>/<entry_id:int>/flag', submit_flag),
           GET('/juror/faves', get_faves)]
    ui = []
    return api, ui


def make_juror_round_details(rnd, rnd_stats, ballot):
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
           'ballot': ballot,
           'campaign': rnd.campaign.to_info_dict()}
    return ret


# Endpoint functions

def get_index(user_dao):
    """
    Summary: Get juror-level index of all campaigns and rounds.
    """
    juror_dao = JurorDAO(user_dao)
    stats = [make_juror_round_details(rnd, rnd_stats, ballot)
             for rnd, rnd_stats, ballot
             in juror_dao.get_all_rounds_task_counts()]
    return stats


def get_campaign(user_dao, campaign_id):
    """
    Summary: Get juror-level list of rounds, identified by campaign ID.
    """
    juror_dao = JurorDAO(user_dao)
    campaign = juror_dao.get_campaign(campaign_id)
    data = campaign.to_details_dict()
    rounds = []
    for rnd in campaign.rounds:
        rnd_stats = user_dao.get_round_task_counts(rnd.id)
        ballot = juror_dao.get_ballot(rnd.id)
        rounds.append(make_juror_round_details(rnd, rnd_stats, ballot))
    data['rounds'] = rounds
    return {'data': data}


def get_round(user_dao, round_id):
    """
    Summary: Get juror-level details for a round, identified by round ID.
    """
    juror_dao = JurorDAO(user_dao)
    rnd = juror_dao.get_round(round_id)
    ballot = juror_dao.get_ballot(round_id)
    rnd_stats = juror_dao.get_round_task_counts(round_id)
    data = make_juror_round_details(rnd, rnd_stats, ballot)  # TODO: add to Round model
    return {'data': data}


def get_tasks_from_round(user_dao, round_id, request):
    count = request.values.get('count', 15)
    offset = request.values.get('offset', 0)
    # TODO: remove offset once it's removed from the client
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


def get_votes_from_round(user_dao, round_id, request, rnd=None):
    count = request.values.get('count', 15)
    offset = request.values.get('offset', 0)
    order_by = request.values.get('order_by', 'date')
    sort = request.values.get('sort', 'asc')
    juror_dao = JurorDAO(user_dao)
    if not rnd:
        rnd = juror_dao.get_round(round_id)
    if rnd.vote_method in ('yesno', 'rating'):
        ratings = juror_dao.get_ratings_from_round(round_id,
                                                   num=count,
                                                   offset=offset,
                                                   sort=sort,
                                                   order_by=order_by)
        data = [r.to_details_dict() for r in ratings]
    else:
        rankings = juror_dao.get_rankings_from_round(round_id)
        data = [r.to_details_dict() for r in rankings]
        data.sort(key=lambda x: x['value'])
    return {'data': data}


def get_ratings_from_round(user_dao, round_id, request):
    juror_dao = JurorDAO(user_dao)
    ret = get_votes_from_round(user_dao, round_id, request)
    return ret


def get_rankings_from_round(user_dao, round_id, request):
    juror_dao = JurorDAO(user_dao)
    rnd = juror_dao.get_round(round_id)
    if rnd.vote_method != 'ranking':
        return {'status': 'failure',
                'errors': 'round %s is not a ranking round' % round_id}
    ret = get_votes_from_round(user_dao, round_id, request, rnd=rnd)
    return ret


def get_faves(user_dao, request_dict):
    request_dict = request_dict or dict()

    juror_dao = JurorDAO(user_dao)
    limit = request_dict.get('limit', 10)
    offset = request_dict.get('offset', 0)
    sort = request_dict.get('sort', 'desc')
    faves = juror_dao.get_faves(sort, limit, offset)
    return {'data': [f.to_details_dict() for f in faves]}


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


def skip_rating(user_dao, round_id, request, request_dict):
    juror_dao = JurorDAO(user_dao)
    
    try:
        vote_id = request_dict['vote_id']
    except Exception as e:
        import pdb;pdb.set_trace()
        raise InvalidAction('must provide skip id')

    juror_dao.skip_voting(vote_id)
    next_tasks = get_tasks_from_round(user_dao, round_id, request)

    return next_tasks


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



JUROR_API_ROUTES, JUROR_UI_ROUTES = get_juror_routes()

# TODO: Cave -> key-value store
# TODO: flag RoundEntries (only applicable on ratings rounds?)
# TODO: entry ID lookup by filename (should also return uploader, etc.)
# TODO: manual disqualificatin for coordinators
