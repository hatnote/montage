from __future__ import absolute_import
import unicodecsv
import io
import datetime

from collections import defaultdict

from clastic import GET, POST, Response
from clastic.errors import Forbidden
from boltons.strutils import slugify
from boltons.timeutils import isoparse

from .utils import (format_date,
                   get_threshold_map,
                   InvalidAction,
                   DoesNotExist,
                   NotImplementedResponse,
                   js_isoparse)

from .rdb import (CoordinatorDAO,
                 MaintainerDAO,
                 OrganizerDAO)

CATEGORY_METHOD = 'category'
ROUND_METHOD = 'round'
SELECTED_METHOD = 'selected'


# These are populated at the bottom of the module
ADMIN_API_ROUTES, ADMIN_UI_ROUTES = None, None


def get_admin_routes():
    """
    /role/(object/id/object/id/...)verb is the guiding principle
    """
    api = [GET('/admin', get_index),
           POST('/admin/add_series', add_series),
           POST('/admin/series/<series_id:int>/edit', edit_series),
           POST('/admin/add_organizer', add_organizer),
           POST('/admin/remove_organizer', remove_organizer),
           POST('/admin/add_campaign', create_campaign),
           GET('/admin/users', get_users),
           GET('/admin/user', get_user),
           GET('/admin/campaigns/', get_campaigns),
           GET('/admin/campaigns/all', get_all_campaigns),
           GET('/admin/campaign/<campaign_id:int>', get_campaign),
           POST('/admin/campaign/<campaign_id:int>/edit', edit_campaign),
           POST('/admin/campaign/<campaign_id:int>/cancel', cancel_campaign),
           POST('/admin/campaign/<campaign_id:int>/add_round',
                create_round),
           POST('/admin/campaign/<campaign_id:int>/add_coordinator',
                add_coordinator),
           POST('/admin/campaign/<campaign_id:int>/remove_coordinator',
                remove_coordinator),
           POST('/admin/campaign/<campaign_id:int>/finalize', finalize_campaign),
           POST('/admin/campaign/<campaign_id:int>/reopen', reopen_campaign),
           POST('/admin/campaign/<campaign_id:int>/publish', publish_report),
           POST('/admin/campaign/<campaign_id:int>/unpublish', unpublish_report),
           GET('/admin/campaign/<campaign_id:int>/audit', get_campaign_log),
           POST('/admin/round/<round_id:int>/import', import_entries),
           POST('/admin/round/<round_id:int>/activate', activate_round),
           POST('/admin/round/<round_id:int>/pause', pause_round),
           GET('/admin/round/<round_id:int>', get_round),
           POST('/admin/round/<round_id:int>/edit', edit_round),
           POST('/admin/round/<round_id:int>/cancel', cancel_round),
           GET('/admin/round/<round_id:int>/preview_results',
               get_round_results_preview),
           POST('/admin/round/<round_id:int>/advance', advance_round),
           GET('/admin/round/<round_id:int>/flags', get_flagged_entries),
           GET('/admin/round/<round_id:int>/disqualified',
               get_disqualified),
           POST('/admin/round/<round_id:int>/autodisqualify',
                autodisqualify),
           POST('/admin/round/<round_id:int>/<entry_id:int>/disqualify',
                disqualify_entry),
           POST('/admin/round/<round_id:int>/<entry_id:int>/requalify',
                requalify_entry),
           GET('/admin/round/<round_id:int>/preview_disqualification',
               preview_disqualification),
           GET('/admin/round/<round_id:int>/results', get_results),
           GET('/admin/round/<round_id:int>/results/download', download_results_csv),
           GET('/admin/round/<round_id:int>/entries', get_round_entries),
           GET('/admin/round/<round_id:int>/entries/download', download_round_entries_csv),
           GET('/admin/round/<round_id:int>/reviews', get_round_reviews),
           GET('/admin/campaign/<campaign_id:int>/report', get_campaign_report_raw)]
    ui = [GET('/admin/campaign/<campaign_id:int>/report', get_campaign_report,
              'report.html')]
    # TODO: arguably download URLs should go into "ui" as well,
    # anything that generates a response directly (or doesn't return json)
    return api, ui


def get_round_reviews(user_dao, round_id):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    entries = coord_dao.get_reviews_table(round_id)
    entry_infos = [e.to_details_dict() for e in entries]
    return {'data': entry_infos}


def get_round_entries(user_dao, round_id):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    entries = coord_dao.get_round_entries(round_id)
    entry_infos = [e.to_export_dict() for e in entries]
    return {'file_infos': entry_infos}


def download_round_entries_csv(user_dao, round_id):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.get_round(round_id)
    entries = coord_dao.get_round_entries(round_id)
    entry_infos = [e.to_export_dict() for e in entries]
    output_name = 'montage_entries-%s.csv' % slugify(rnd.name, ascii=True).decode('ascii')
    output = io.BytesIO()
    csv_fieldnames = sorted(entry_infos[0].keys())
    csv_writer = unicodecsv.DictWriter(output, fieldnames=csv_fieldnames)
    csv_writer.writeheader()
    csv_writer.writerows(entry_infos)
    ret = output.getvalue()
    resp = Response(ret, mimetype='text/csv')
    resp.mimetype_params['charset'] = 'utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename=%s' % (output_name,)
    return resp


def disqualify_entry(user_dao, round_id, entry_id, request_dict):
    if not request_dict:
        request_dict = {}
    reason = request_dict.get('reason')
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    coord_dao.disqualify(round_id, entry_id, reason)


def requalify_entry(user_dao, round_id, entry_id, request_dict):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    coord_dao.requalify(round_id, entry_id)


def add_series(user_dao, request_dict):
    org_dao = OrganizerDAO(user_dao)

    name = request_dict['name']
    description = request_dict['description']
    url = request_dict['url']
    status = request_dict.get('status')

    new_series = org_dao.create_series(name, description, url, status)
    return {'data': new_series}


def edit_series(user_dao, series_id, request_dict):
    org_dao = OrganizerDAO(user_dao)
    series_dict = {}
    name = request_dict.get('name')
    if name:
        series_dict['name'] = name
    description = request_dict.get('description')
    if description:
        series_dict['description'] = description
    url = request_dict.get('url')
    if url:
        series_dict['url'] = url
    status = request_dict.get('status')
    if status:
        series_dict['status'] = status

    new_series = org_dao.edit_series(series_id, series_dict)
    return {'data': new_series}


def publish_report(user_dao, campaign_id):
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    coord_dao.publish_report()


def unpublish_report(user_dao, campaign_id):
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    coord_dao.unpublish_report()


def make_admin_round_details(rnd, rnd_stats):
    # TODO: This should be depricated in favor of rnd.to_details_dict(), which
    # is similar except for the stats dict structure.
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
           'total_disqualified_entries': rnd_stats['total_disqualified_entries'],
           'campaign': rnd.campaign.to_info_dict(),
           'stats': rnd_stats,
           'jurors': [rj.to_details_dict() for rj in rnd.round_jurors],
           'is_closable': rnd.check_closability()}
    return ret


def get_users(user_dao, request_dict):
    """View the maintainers, organizers, and campaign coordinators"""

    org_dao = OrganizerDAO(user_dao)
    user_list = org_dao.get_user_list()

    return {'data': user_list}


# TODO: (clastic) some way to mark arguments as injected from the
# request_dict such that the signature can be expanded here. the goal
# being that create_campaign can be a standalone function without any
# special middleware dependencies, to achieve a level of testing
# between the dao and server tests.
def create_campaign(user_dao, request_dict):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name:
            type: string

    Response model: AdminCampaignDetails
    """
    org_dao = OrganizerDAO(user_dao)

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

    url = request_dict['url']

    series_id = request_dict.get('series_id', 1)

    coord_names = request_dict.get('coordinators')

    coords = [user_dao.user]  # Organizer is included as a coordinator by default
    for coord_name in coord_names:
        coord = org_dao.get_or_create_user(coord_name, 'coordinator')
        coords.append(coord)

    campaign = org_dao.create_campaign(name=name,
                                       open_date=open_date,
                                       close_date=close_date,
                                       series_id=series_id,
                                       url=url,
                                       coords=set(coords))
    # TODO: need completion info for each round
    data = campaign.to_details_dict()

    return {'data': data}


def get_campaign_report(user_dao, campaign_id):
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    summary = coord_dao.get_campaign_report()
    ctx = summary.summary
    ctx['use_ashes'] = True
    return ctx


def get_campaign_report_raw(user_dao, campaign_id):
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    summary = coord_dao.get_campaign_report()
    data = summary.summary
    return {'data': data}


def get_campaign_log(user_dao, campaign_id, request_dict):
    request_dict = request_dict or dict()
    limit = request_dict.get('limit', 100)
    offset = request_dict.get('offset', 0)
    round_id = request_dict.get('round_id')
    log_id = request_dict.get('id')
    action = request_dict.get('action')

    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    audit_logs = coord_dao.get_audit_log(limit=limit,
                                         offset=offset,
                                         round_id=round_id,
                                         log_id=log_id,
                                         action=action)
    ret = [a.to_info_dict() for a in audit_logs]
    return {'data': ret}


def import_entries(user_dao, round_id, request_dict):
    """
    Summary: Load entries into a round via one of four import methods

    Request model:
      - round_id (in path)
      - import_method:
        - gistcsv
        - category
        - round
        - selected
      - gist_url (if import_method=gistcsv)
      - category (if import_method=category)
      - threshold (if import_method=round)
      - file_names (if import_method=selected)

    Response model name:
      - data:
        - round_id
        - new_entry_count
        - new_round_entry_count
        - total_entries
        - status: success or failure
        - errors: description of the failure (if any)
        - warnings: possible problems to alert the user
          - empty import (no entries)
          - duplicate import (no new entries)
          - all disqualified
    """
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    import_method = request_dict['import_method']

    # loader warnings
    import_warnings = list()

    if import_method == 'csv' or import_method == 'gistcsv':
        if import_method == 'gistcsv':
            csv_url = request_dict['gist_url']
        else:
            csv_url = request_dict['csv_url']

        entries, warnings = coord_dao.add_entries_from_csv(round_id,
                                                           csv_url)
        params = {'csv_url': csv_url}
        if warnings:
            msg = u'unable to load {} files ({!r})'.format(len(warnings), warnings)
            import_warnings.append(msg)
    elif import_method == CATEGORY_METHOD:
        cat_name = request_dict['category']
        entries = coord_dao.add_entries_from_cat(round_id, cat_name)
        params = {'category': cat_name}
    elif import_method == ROUND_METHOD:
        threshold = request_dict['threshold']
        prev_round_id = request_dict['previous_round_id']
        entries = coord_dao.get_rating_advancing_group(prev_round_id, threshold)
        params = {'threshold': threshold,
                  'round_id': prev_round_id}
    elif import_method == SELECTED_METHOD:
        file_names = request_dict['file_names']
        entries, warnings = coord_dao.add_entries_by_name(round_id, file_names)
        if warnings:
            formatted_warnings = u'\n'.join([
                u'- {}'.format(warning) for warning in warnings
            ])
            msg = u'unable to load {} files:\n{}'.format(len(warnings), formatted_warnings)
            import_warnings.append({'import issues', msg})
        params = {'file_names': file_names}
    else:
        raise NotImplementedResponse()

    new_entry_stats = coord_dao.add_round_entries(round_id, entries,
                                                  method=import_method,
                                                  params=params)
    new_entry_stats['warnings'] = import_warnings

    if not entries:
        new_entry_stats['warnings'].append({'empty import':
                                            'no entries imported'})
    elif not new_entry_stats.get('new_entry_count'):
        new_entry_stats['warnings'].append({'duplicate import':
                                            'no new entries imported'})

    # automatically disqualify entries based on round config
    auto_dq = autodisqualify(user_dao, round_id, request_dict={})
    new_entry_stats['disqualified'] = auto_dq['data']
    if len(new_entry_stats['disqualified']) >= len(entries):
        new_entry_stats['warnings'].append({'all disqualified':
                  'all entries disqualified by round settings'})

    return {'data': new_entry_stats}


def activate_round(user_dao, round_id, request_dict):
    """
    Summary: Set the status of a round to active.

    Request model:
        round_id:
            type: int64
    """
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    coord_dao.activate_round(round_id)
    rnd = coord_dao.get_round(round_id)
    ret_data = rnd.get_count_map()
    ret_data['round_id'] = round_id
    return {'data': ret_data}


def pause_round(user_dao, round_id, request_dict):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    coord_dao.pause_round(round_id)
    return {'data': 'paused'}


def edit_campaign(user_dao, campaign_id, request_dict):
    """
    Summary: Change the settings for a campaign

    Request model:
        campaign_id
        request_dict

    """
    edit_dict = {}
    name = request_dict.get('name')
    if name:
        edit_dict['name'] = name

    is_archived = request_dict.get('is_archived')
    if is_archived is not None:
        edit_dict['is_archived'] = is_archived

    open_date = request_dict.get('open_date')
    if open_date:
        edit_dict['open_date'] = js_isoparse(open_date)
    close_date = request_dict.get('close_date')
    if close_date:
        edit_dict['close_date'] = js_isoparse(close_date)

    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    coord_dao.edit_campaign(edit_dict)
    return {'data': edit_dict}


def cancel_campaign(user_dao, campaign_id):
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    results = coord_dao.cancel_campaign()
    return {'data': results}



def _prepare_round_params(coord_dao, request_dict):
    rnd_dict = {}
    req_columns = ['jurors', 'name', 'vote_method', 'deadline_date']
    extra_columns = ['description', 'config', 'directions', 'show_stats']
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


def create_round(user_dao, campaign_id, request_dict):
    """
    Summary: Create a new round

    Request model:
        campaign_id
    """
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)

    rnd_params = _prepare_round_params(coord_dao, request_dict)
    rnd = coord_dao.create_round(**rnd_params)

    data = rnd.to_details_dict()
    data['progress'] = rnd.get_count_map()

    return {'data': data}


def edit_round(user_dao, round_id, request_dict):
    """
    Summary: Post a new campaign

    Request model:
        campaign_name

    Response model: AdminCampaignDetails
    """
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    new_val_map = coord_dao.edit_round(round_id, request_dict)
    return {'data': new_val_map}


def cancel_round(user_dao, round_id):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.cancel_round(round_id)
    stats = rnd.get_count_map()
    return {'data': stats}


def get_round_results_preview(user_dao, round_id):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.get_round(round_id)

    round_counts = rnd.get_count_map()
    is_closeable = rnd.check_closability()

    data = {'round': rnd.to_info_dict(),
            'counts': round_counts,
            'is_closeable': is_closeable}

    if rnd.vote_method in ('yesno', 'rating'):
        data['ratings'] = coord_dao.get_round_average_rating_map(round_id)
        try:
            data['thresholds'] = get_threshold_map(data['ratings'])
        except:
            # import pdb;pdb.post_mortem()
            raise
    elif rnd.vote_method == 'ranking':
        if not is_closeable:
            # TODO: What should this return for ranking rounds? The ranking
            # round is sorta an all-or-nothing deal, unlike the rating rounds
            # where you can take a peek at in-progress results
            # import pdb;pdb.set_trace()
            return {'status': 'failure',
                    'errors': ('cannot preview results of a ranking '
                               'round until all ballots are '
                               'submitted'),
                    'data': None}

        rankings = coord_dao.get_round_ranking_list(round_id)

        data['rankings'] = [r.to_dict() for r in rankings]

    else:
        raise NotImplementedResponse()

    return {'data': data}


def advance_round(user_dao, round_id, request_dict):
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
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.get_round(round_id)

    if rnd.vote_method not in ('rating', 'yesno'):
        raise NotImplementedResponse()  # see docstring above
    try:
        threshold = float(request_dict['threshold'])
    except KeyError:
        raise InvalidAction('unset threshold. set the threshold and try again.')
    _next_round_params = request_dict['next_round']
    nrp = _prepare_round_params(coord_dao, _next_round_params)

    if nrp['vote_method'] == 'ranking' \
       and len(nrp['jurors']) != nrp.get('quorum'):
        # TODO: log
        # (ranking round quorum must match juror count)
        nrp['quorum'] = len(nrp['jurors'])

    # TODO: inherit round config from previous round?
    adv_group = coord_dao.finalize_rating_round(round_id, threshold=threshold)

    next_rnd = coord_dao.create_round(**nrp)
    source = 'round(#%s)' % round_id
    params = {'round': round_id,
              'threshold': threshold}
    coord_dao.add_round_entries(next_rnd.id, adv_group,
                                method=ROUND_METHOD, params=params)

    # NOTE: disqualifications are not repeated, as they should have
    # been performed the first round.

    next_rnd_dict = next_rnd.to_details_dict()
    next_rnd_dict['progress'] = next_rnd.get_count_map()

    msg = ('%s advanced campaign %r (#%s) from %s round "%s" to %s round "%s"'
           % (user_dao.user.username, rnd.campaign.name, rnd.campaign.id,
              rnd.vote_method, round_id, next_rnd.vote_method, next_rnd.name))
    coord_dao.log_action('advance_round', campaign=rnd.campaign, message=msg)

    return {'data': next_rnd_dict}


def finalize_campaign(user_dao, campaign_id):
    # TODO: add some docs
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    last_rnd = coord_dao.campaign.active_round

    if not last_rnd:
        raise InvalidAction('no active rounds')

    if last_rnd.vote_method != 'ranking':
        raise InvalidAction('only ranking rounds can be finalized')

    campaign_summary = coord_dao.finalize_ranking_round(last_rnd.id)
    coord_dao.finalize_campaign()
    return campaign_summary


def reopen_campaign(user_dao, campaign_id):
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    coord_dao.reopen_campaign()


def get_index(user_dao, only_active=True):
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
    campaigns = user_dao.get_all_campaigns(only_active=only_active)
    data = []

    for campaign in campaigns:
        data.append(campaign.to_details_dict())

    return {'data': data}


def get_user(user_dao, only_active=True):
    """
    Summary: Get current login user details.
    """
    return {'data': []}


def get_all_campaigns(user_dao):
    return get_index(user_dao, only_active=False)


def get_campaigns(user_dao):
    campaigns = user_dao.get_all_campaigns()
    data = []

    # TODO: group by series
    for campaign in sorted(campaigns, key=lambda c: c.create_date, reverse=True):
        data.append(campaign.to_info_dict())

    return {'data': data}



def get_campaign(user_dao, campaign_id):
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
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    campaign = coord_dao.campaign
    if campaign is None:
        raise Forbidden('not a coordinator on this campaign')
    data = campaign.to_details_dict()
    return {'data': data}


def get_round(user_dao, round_id):
    """
    Summary: Get admin-level details for a round, identified by round ID.

    Request model:
        round_id

    Response model name: AdminRoundDetails

    Errors:
       403: User does not have permission to access requested round
       404: Round not found
    """
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.get_round(round_id)
    rnd_stats = rnd.get_count_map()
    # entries_info = user_dao.get_entry_info(round_id) # TODO
    # TODO: joinedload if this generates too many queries
    data = make_admin_round_details(rnd, rnd_stats)
    return {'data': data}


def get_results(user_dao, round_id, request_dict):
    # TODO: Docs
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    results_by_name = coord_dao.make_vote_table(round_id)
    return {'data': results_by_name}


def download_results_csv(user_dao, round_id, request_dict):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.get_round(round_id)
    now = datetime.datetime.now().isoformat()
    output_name = 'montage_results-%s-%s.csv' % (slugify(rnd.name, ascii=True).decode('ascii'), now)

    # TODO: Confirm round is finalized
    # raise DoesNotExist('round results not yet finalized')

    results_by_name = coord_dao.make_vote_table(round_id)

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
    resp.headers['Content-Disposition'] = 'attachment; filename=%s' % output_name
    return resp


def autodisqualify(user_dao, round_id, request_dict):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.get_round(round_id)

    if rnd.status != 'paused':
        raise InvalidAction('round must be paused to disqualify entries')

    dq_by_upload_date = request_dict.get('dq_by_upload_date')
    dq_by_resolution = request_dict.get('dq_by_resolution')
    dq_by_uploader = request_dict.get('dq_by_uploader')
    dq_by_filetype = request_dict.get('dq_by_filetype')

    round_entries = []

    if rnd.config.get('dq_by_upload_date') or dq_by_upload_date:
        dq_upload_date = coord_dao.autodisqualify_by_date(round_id)
        round_entries += dq_upload_date

    if rnd.config.get('dq_by_resolution') or dq_by_resolution:
        dq_resolution = coord_dao.autodisqualify_by_resolution(round_id)
        round_entries += dq_resolution

    if rnd.config.get('dq_by_uploader') or dq_by_uploader:
        dq_uploader = coord_dao.autodisqualify_by_uploader(round_id)
        round_entries += dq_uploader

    if rnd.config.get('dq_by_filetype') or dq_by_filetype:
        dq_filetype = coord_dao.autodisqualify_by_filetype(round_id)
        round_entries += dq_filetype

    data = [re.to_dq_details() for re in round_entries]

    return {'data': data}


def preview_disqualification(user_dao, round_id):
    # Let's you see what will get disqualified, without actually
    # disqualifying any entries
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    # TODO: explain each disqualification
    rnd = coord_dao.get_round(round_id)
    ret = {'config': rnd.config}

    by_upload_date = coord_dao.autodisqualify_by_date(round_id, preview=True)
    ret['by_upload_date'] = [re.entry.to_details_dict(with_uploader=True)
                             for re in by_upload_date]

    by_resolution = coord_dao.autodisqualify_by_resolution(round_id, preview=True)
    ret['by_resolution'] = [re.entry.to_details_dict(with_uploader=True)
                            for re in by_resolution]

    by_uploader = coord_dao.autodisqualify_by_uploader(round_id, preview=True)
    ret['by_uploader'] = [re.entry.to_details_dict(with_uploader=True)
                          for re in by_uploader]

    by_filetype = coord_dao.autodisqualify_by_filetype(round_id, preview=True)
    ret['by_filetype'] = [re.entry.to_details_dict(with_uploader=True)
                          for re in by_filetype]

    return {'data': ret}


def get_flagged_entries(user_dao, round_id):
    # TODO: include a limit?
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    flagged_entries = coord_dao.get_grouped_flags(round_id)
    ret = []
    for fe in flagged_entries:
        entry = fe.entry.to_details_dict()
        entry['flaggings'] = [f.to_details_dict()
                              for f
                              in fe.flaggings]
        ret.append(entry)
    return {'data': ret}


def get_disqualified(user_dao, round_id):
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    round_entries = coord_dao.get_disqualified(round_id)
    data = [re.to_dq_details() for re in round_entries]
    return {'data': data}


def add_coordinator(user_dao, campaign_id, request_dict):
    """
    Summary: -
        Add a new coordinator identified by Wikimedia username to a campaign
        identified by campaign ID

    Request model:
        username

    Response model:
        username
        last_active_date
        campaign_id

    Errors:
       403: User does not have permission to add coordinators

    """
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    new_user_name = request_dict.get('username')
    new_coord = coord_dao.add_coordinator(new_user_name)
    data = {'username': new_coord.username,
            'campaign_id': campaign_id,
            'last_active_date': format_date(new_coord.last_active_date)}
    return {'data': data}


def remove_coordinator(user_dao, campaign_id, request_dict):
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    username = request_dict.get('username')
    old_coord = coord_dao.remove_coordinator(username)
    data = {'username': username,
            'campaign_id': campaign_id,
            'last_active_date': format_date(old_coord.last_active_date)}
    return {'data': data}


# Endpoints restricted to maintainers

def add_organizer(user_dao, request_dict):
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
    maint_dao = MaintainerDAO(user_dao)
    new_user_name = request_dict.get('username')
    new_organizer = maint_dao.add_organizer(new_user_name)
    data = {'username': new_organizer.username,
            'last_active_date': format_date(new_organizer.last_active_date)}
    return {'data': data}


def remove_organizer(user_dao, request_dict):
    maint_dao = MaintainerDAO(user_dao)
    username = request_dict.get('username')
    old_organizer = maint_dao.remove_organizer(username)
    data = {'username': username,
            'last_active_date': format_date(old_organizer.last_active_date)}
    return {'data': data}


# Endpoints restricted to organizers




ADMIN_API_ROUTES, ADMIN_UI_ROUTES = get_admin_routes()


# - cancel round
# - update round
#   - no reassignment required: name, description, directions, display_settings
#   - reassignment required: quorum, active_jurors
#   - not updateable: id, open_date, close_date, vote_method, campaign_id/seq
