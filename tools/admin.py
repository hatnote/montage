# -*- coding: utf-8 -*-
"""
TODO:

* Separate acting user from target user.
  * e.g., create_campaign creates a campaign with hardcoded slaporte as coordinator

# TODO: active users
# TODO: Remove organizer
# TODO: Remove coordinator

"""

from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import random
import datetime
from pprint import pprint
from collections import defaultdict

from unicodecsv import DictReader
from sqlalchemy.orm import joinedload
from face import Command, face_middleware, UsageError, ERROR

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

import montage.rdb
from montage.rdb import (make_rdb_session,
                         UserDAO,
                         PublicDAO,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         reassign_rating_tasks,
                         lookup_user)
from montage.utils import get_threshold_map


RANKING_MAX = 40


def warn(msg, force=False):
    if not force:
        confirmed = input('??  %s. Type yes to confirm: ' % msg)

        if not confirmed == 'yes':
            print(('-- you typed %r, aborting' % confirmed))
            sys.exit(0)

    return


def main():
    """
    The main entrypoint, setting up a face application, with middleware, common flags, and subcommands.
    """
    cmd = Command(name='montage-admin', func=None, doc="CLI tools for administrating Montage.")

    # middleware
    cmd.add(_admin_dao_mw)
    cmd.add(_rdb_session_mw)

    cmd.add('--username', missing=ERROR)
    cmd.add('--debug', parse_as=True, doc='get extra output, enable debug console before db commit')
    cmd.add('--force', parse_as=True, doc='skip some confirmations, use with caution')
    cmd.add('--campaign-id', parse_as=int, missing=ERROR)
    cmd.add('--round-id', parse_as=int, missing=ERROR)
    cmd.add('--csv-path', missing=ERROR)
    cmd.add('--url', missing=ERROR)

    cmd.add(add_organizer)  # , posargs={'count': 1, 'name': 'username'})  # TODO: figure out if we want posarg/flag overriding

    ser_cmd = Command(name='series', func=None, doc='tools for administrating Montage series')
    ser_cmd.add(add_series, name='add')

    cmd.add(ser_cmd)

    cmp_cmd = Command(name='campaign', func=None, doc='tools for administrating Montage campaigns')
    cmp_cmd.add(list_campaigns, name='list')
    cmp_cmd.add(create_campaign, name='create')
    cmp_cmd.add(add_coordinator, name='add-coordinator')
    cmp_cmd.add(cancel_campaign, name='cancel')
    cmp_cmd.add(backfill_series)

    cmd.add(cmp_cmd)

    rnd_cmd = Command(name='round', func=None, doc='tools for administrating Montage rounds')
    rnd_cmd.add(create_round, name='create')
    rnd_cmd.add(import_gist, name='import-gist')
    rnd_cmd.add(activate_round, name='activate')
    rnd_cmd.add(pause_round, name='pause')
    rnd_cmd.add(advance_round, name='advance')
    rnd_cmd.add(edit_round_quorum, name='edit-quorum')
    rnd_cmd.add(check_round_dupes, name='check-dupes')
    rnd_cmd.add(apply_round_ratings, name='apply-ratings')
    rnd_cmd.add(retask_duplicate_ratings, name='retask-dupes')
    rnd_cmd.add(shuffle_round_assignments, name='shuffle-tasks')
    rnd_cmd.add(cancel_round, name='cancel')
    rnd_cmd.add(unfinalize_rating_round, name='unfinalize-rating-round')

    cmd.add(rnd_cmd)

    cmd.add(rdb_console)
    cmd.prepare()
    return cmd.run()


def add_series(org_dao):
    name = _input('New series name: ')
    if not name:
        return
    desc = _input('New series description: ')
    url = _input('New series URL: ')
    if url:
        assert url.startswith('http'), 'url expected to start with http'

    series = org_dao.create_series(name, desc, url)

    print(('Created new series "%s" (#%s)' % (series.name, series.id)))
    return



def _input(prompt, blank=None):
    # TODO: if blank is MISSING, be more insistent, with message about
    # ctrld/ctrlc to exit
    try:
        ret = input(prompt).strip() or blank
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)
    return ret


def backfill_series(org_dao, user_dao, maint_dao, public_dao):
    cur_series = 'Unofficial'
    cur_camp_id = 0
    all_series = public_dao.get_all_series()

    print('Choose from the following series to browse and backfill:')
    for i, s in enumerate(all_series):
        print(('  %s - %s (#%s)' % (i + 1, s.name, s.id)))
    idx = _input('[%s] > ' % cur_series)
    if idx:
        idx = int(idx)
        assert idx > 0
        cur_series = all_series[idx - 1].name

    while 1:
        print('---')
        campaign = maint_dao.get_campaign_by_series(cur_series, cur_camp_id)
        if campaign is None:
            print(('no campaigns of series "%s" remaining' % cur_series))
            break
        cur_camp_id = campaign.id

        print(('\nCampaign "%s" (#%s) from series: %s (#%s)\n'
              % (campaign.name, campaign.id, campaign.series.name, campaign.series.id)))
        print('Choose from the following (or leave blank to skip):')
        for i, s in enumerate(all_series):
            print(('  %s - %s (#%s)' % (i + 1, s.name, s.id)))

        idx = _input('> ')
        if not idx:
            continue
        idx = int(idx)
        assert idx > 0
        new_series = all_series[idx - 1]
        campaign.series = new_series
        public_dao.rdb_session.commit()

        #if new_series == campaign.series:
        #    continue
    return


def create_round(user_dao, campaign_id, advance=False, debug=False):
    'interactively create a round in the specified campaign'
    # TODO: this looks messy below, campaign was semi-undefined and
    # the comment about rdb_session rollback may not be true.
    coord_dao = CoordinatorDAO.from_campaign(user_dao, campaign_id)
    rnd_name = input('?? Round name: ')
    if not rnd_name:
        print('-- round name required, aborting')
        sys.exit(0)
    juror_names_str = input('?? Juror names (comma separated): ')
    juror_names = [j.strip() for j in juror_names_str.split(',')]
    vote_method = input('?? Vote method (rating, yesno, or ranking): ')
    if vote_method not in ['rating', 'yesno', 'ranking']:
        print('-- vote method must be rating, yesno, or ranking, aborting')
        sys.exit(0)
    if vote_method != 'ranking':
        quorum = input('?? Voting quorum: ')
    else:
        quorum = len(juror_names)
    deadline_date_str = input('?? Deadline date: ')
    deadline_date = datetime.datetime.strptime(deadline_date_str, '%Y-%m-%d')
    description = input('?? Description: ')
    directions = input('?? Directions: ')
    if not advance:
        category_name = input('?? Category: ')
    rnd = coord_dao.create_round(name=rnd_name,
                                 quorum=quorum,
                                 vote_method=vote_method,
                                 deadline_date=deadline_date,
                                 jurors=juror_names,
                                 directions=directions,
                                 description=description)

    pprint(rnd.to_info_dict())
    print(('++ round %s (%r) created in campaign %s'
           % (rnd.id, rnd.name, campaign_id)))

    campaign = user_dao.get_campaign(campaign_id)

    if not advance:
        entries = coord_dao.add_entries_from_cat(rnd.id, category_name)
        source = category_name
        # GIST_URL = 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'
        # entries = maint_dao.add_entries_from_csv_gist(rnd, GIST_URL)
        # source = GIST_URL
        print(('++ prepared %s entries from %r' %
               (len(entries), source)))
        coord_dao.add_round_entries(rnd.id, entries)
    else:
        final_rnds = [r for r in campaign.rounds if r.status == 'finalized']
        last_successful_rnd = final_rnds[-1]
        advancing_group = coord_dao.get_rating_advancing_group(last_successful_rnd)
        entries = advancing_group
        if vote_method == 'ranking' and len(entries) > RANKING_MAX:
            print(('-- %s is too many entries for ranking round, aborting'
                   % len(entries)))
            raise UsageError('too many entries for ranking round')

        source = 'round(#%s)' % last_successful_rnd.id
        coord_dao.add_round_entries(rnd.id, advancing_group, source)
    print(('++ added entries from %s to round %s (%r)'
           % (source, rnd.id, rnd.name)))

    return rnd


def cancel_campaign(user_dao, org_dao, campaign_id, force=False):
    "cancel the specified campaign"
    campaign = user_dao.get_campaign(campaign_id)
    msg = ('this will cancel campaign %s (%r) and %s rounds, including tasks.'
           % (campaign_id, campaign.name, len(campaign.rounds)))

    warn(msg, force)

    org_dao.cancel_campaign(campaign)

    print(('++ cancelled campaign %s (%r) and %s rounds'
           % (campaign_id, campaign.name, len(campaign.rounds))))



def pause_round(maint_dao, round_id):
    'pause a round to make edits and perform other maintenance'
    rnd = maint_dao.get_round(round_id)

    maint_dao.pause_round(rnd)
    maint_dao.rdb_session.commit()

    print(('++ paused round %s (%r)' % (rnd.id, rnd.name)))

    return rnd


def remove_coordinator(maint_dao, campaign_id, username):
    # TODO: the campaign_coords table should have an is_active column
    raise NotImplementedError('cannot remove coordinators for now')


def retask_duplicate_ratings(maint_dao, round_id):
    'reassign all ratings that were duplicated'
    from montage.rdb import User, Rating, Round, RoundJuror, Task, RoundEntry

    print(('scanning round %s for duplicate tasks and juror eligibility' % round_id))

    session = maint_dao.rdb_session
    rnd = session.query(Round).get(round_id)

    cur_jurors = session.query(User)\
                        .join(RoundJuror)\
                        .filter_by(round=rnd, is_active=True)\
                        .all()

    cur_tasks = session.query(Task)\
                       .filter_by(cancel_date=None)\
                       .options(joinedload('round_entry'))\
                       .join(RoundEntry)\
                       .filter_by(round=rnd,
                                  dq_user_id=None)\
                       .all()

    elig_map = defaultdict(lambda: list(cur_jurors))
    dup_map = defaultdict(list)
    # only complete_date because that indicates that's the only
    # indicator we have that the user has seen the entry
    # comp_tasks = [t for t in cur_tasks if t.complete_date]
    for task in cur_tasks:
        try:
            elig_map[task.round_entry].remove(task.user)
        except ValueError:
            pass
        dup_map[(task.round_entry_id, task.user_id)].append(task)
    dup_items = [(k, v) for k, v in dup_map.items() if len(v) > 1]
    print(('found %s duplicate tasks out of %s tasks total' % (len(dup_items), len(cur_tasks))))
    print('starting retaskification')
    reassign_count = 0
    revert_count = 0
    for _, dup_tasks in dup_items:
        for i, task in enumerate(reversed(dup_tasks)):
            if i == 0:
                continue  # leave the most recent one alone
            reassign_count += 1
            new_j = random.choice(elig_map[task.round_entry])
            print(task, 'is being assigned from', task.user, 'to', new_j)
            task.user = new_j
            elig_map[task.round_entry].remove(task.user)
            # the following line makes this safer, but slower
            # also note that sqlalchemy doesn't support limit with its delete
            if task.complete_date:
                revert_count += 1
                assert session.query(Rating).filter_by(task_id=task.id).count() == 1
                session.query(Rating).filter_by(task_id=task.id).delete()
                task.complete_date = None

    print(('reassigned %s tasks and reverted %s ratings for round %s'
           % (reassign_count, revert_count, round_id)))

    return


def apply_round_ratings(maint_dao, rdb_session, round_id, csv_path):
    "apply ratings to a round based on an input file"
    from montage.rdb import Round, User, Entry, RoundEntry, Task, Rating

    print('applying ratings from %s to round #%s' % (csv_path, round_id))

    rnd = rdb_session.query(Round).get(round_id)

    dr = DictReader(open(csv_path, 'rb'))

    usernames = dr.fieldnames[1:]
    username_map = {}
    for username in usernames:
        user = rdb_session.query(User).filter_by(username=username).one()
        username_map[username] = user

    now = datetime.datetime.utcnow()

    new_tasks = []
    new_ratings = []
    del_ratings_count = 0

    for orig_entry_dict in dr:
        entry_dict = dict(orig_entry_dict)
        entry_name = entry_dict.pop('entry')
        _, _, entry_name = entry_name.rpartition('File:')
        entry_name = entry_name.strip()
        entry = rdb_session.query(Entry).filter_by(name=entry_name).one()
        round_entry = (rdb_session.query(RoundEntry)
                       .filter_by(round=rnd, entry=entry)
                       .one())

        old_tasks = (rdb_session.query(Task)
                     .filter_by(round_entry=round_entry)
                     .all())
        # cancel old tasks, delete associated ratings
        for t in old_tasks:
            t.complete_date = None
            t.cancel_date = now

            del_count = rdb_session.query(Rating).filter_by(task_id=t.id).delete()
            del_ratings_count += del_count

        # create new tasks, apply associated ratings
        for username, rv in entry_dict.items():
            if not rv.strip():
                continue
            rating_val = float(rv)
            user = username_map[username]
            new_task = Task(user=user, round_entry=round_entry)
            new_task.complete_date = now
            new_tasks.append(new_task)
            new_rating = Rating(value=rating_val, user=user, task=new_task,
                                round_entry=round_entry)
            new_ratings.append(new_rating)
            rdb_session.add(new_rating)

    print('deleted %s old tasks, created %s new ratings' % (del_ratings_count,
                                                            len(new_ratings)))

    return


def show_round_thresholds(user_dao, round_id):
    'get the threshold map (based on average ratings) for a specified round'
    # TODO: may not work (had nameerrors before porting)
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    avg_ratings_map = coord_dao.get_round_average_rating_map(round_id)
    thresh_map = get_threshold_map(avg_ratings_map)
    print('-- Round threshold map for round %s (%r) ...' % round_id)
    pprint(thresh_map)


def shuffle_round_assignments(user_dao, round_id):
    'randomly reassign all the rating tasks in a round'
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    rnd = coord_dao.get_round(round_id)
    new_jurors = rnd.jurors
    stats = reassign_rating_tasks(user_dao.rdb_session,
                                  rnd, new_jurors,
                                  reassign_all=True)
    print('++ reassignment stats: ')
    pprint(stats)


def check_round_dupes(user_dao, round_id):
    """check for double-assigned tasks or ratings in a specified round"""
    dupe_tasks_query = '''
    SELECT users.username, ratings.value, tasks.id, entries.name
    FROM tasks
    JOIN ratings
    ON tasks.id = ratings.task_id
    JOIN round_entries
    ON tasks.round_entry_id = round_entries.id
    JOIN entries
    ON round_entries.entry_id = entries.id
    JOIN users
    ON tasks.user_id = users.id
    WHERE round_entries.round_id = :round_id
    AND round_entries.dq_user_id IS NULL'''

    dupe_ratings_query = '''
    SELECT users.username, ratings.value, entries.name
    FROM ratings
    JOIN round_entries
    ON ratings.round_entry_id = round_entries.id
    JOIN entries
    ON round_entries.entry_id = entries.id
    JOIN users
    ON ratings.user_id = users.id
    WHERE round_entries.round_id = :round_id
    AND round_entries.dq_user_id IS NULL'''

    dupe_tasks = user_dao.rdb_session.execute(dupe_tasks_query,
                                              {'round_id': round_id}).fetchall()
    dupe_ratings = user_dao.rdb_session.execute(dupe_ratings_query,
                                                {'round_id': round_id}).fetchall()

    if len(dupe_tasks) - len(dupe_ratings):
        print(('-- found %s double-assigned tasks'
               % len(dupe_tasks)))

    if dupe_ratings:
        print(('-- found %s double-assigned ratings'
               % len(dupe_ratings)))

    return


def import_gist(user_dao, round_id, url):
    "import round entries from a csv list"
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    entries, warnings = coord_dao.add_entries_from_csv(round_id, url)
    stats = coord_dao.add_round_entries(round_id, entries,
                                        method='gistcsv',
                                        params={'gist_url': url})
    print('++ added entries to round %s: %r' % (round_id, stats))


def edit_round_quorum(maint_dao, round_id):
    "change the quorum of a given round, assigning and reassigning tasks as need be"
    rnd = maint_dao.get_round(round_id)
    old_quorum = rnd.quorum
    if rnd.status != 'paused':
        print('-- round must be paused to edit quorum, aborting')
        return
    print(('!! new quorum cannot be lower than current quorum: %s' % old_quorum))
    print(('!! new quorum cannot be higher than the number of jurors: %s' % len(rnd.jurors)))
    new_quorum = int(input('?? New quorum: '))
    new_juror_stats = maint_dao.modify_quorum(rnd, new_quorum)

    maint_dao.rdb_session.commit()

    print(('++ changed quorum in round %s (%s) from %s (old quorum) to %s (new quorum)'
           % (rnd.id, rnd.name, old_quorum, new_quorum)))
    print(('++ reassigned %s tasks, with mean load of %s tasks per juror'
           % (new_juror_stats['reassigned_task_count'], new_juror_stats['task_count_mean'])))

    return new_juror_stats


def advance_round(user_dao, round_id, debug):
    "finalize the specified round and start the next"
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    avg_ratings_map = coord_dao.get_round_average_rating_map(round_id)
    threshold_map = get_threshold_map(avg_ratings_map)
    print('-- Round threshold map...')
    pprint(threshold_map)
    threshold = input('?? Include at least how many images: ')
    threshold = int(threshold)
    if not threshold:
        print('-- no threshold provided, aborting')
        sys.exit(0)
    cur_thresh = [t for t, c in sorted(threshold_map.items()) \
                  if c >= threshold][-1]
    coord_dao.finalize_rating_round(round_id, cur_thresh)
    campaign_id = coord_dao.campaign.id
    print(('++ ready to import %s entries to the next round in campaign %s...'
           % (threshold_map[cur_thresh], campaign_id)))
    next_round = create_round(user_dao, campaign_id, advance=True, debug=debug)
    return


def activate_round(user_dao, round_id):
    'activate a round to start or resume voting'
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    coord_dao.activate_round(round_id)
    print('++ activated round %s' % round_id)


def cancel_round(user_dao, round_id, force):
    """set a round as cancelled, cancel related tasks, and remove it from
    the campaign's active rounds."""

    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    msg = 'this will cancel round %s and its tasks' % (round_id,)

    warn(msg, force)

    rnd = coord_dao.cancel_round(round_id)
    stats = rnd.get_count_map()

    print(('++ cancelled round %s (%s), with %s tasks'
           % (round_id, rnd.name, stats['total_cancelled_tasks'])))
    return


def unfinalize_rating_round(user_dao, round_id, force):
    """Unfinalize a rating round to allow voting to continue."""
    coord_dao = CoordinatorDAO.from_round(user_dao, round_id)
    msg = 'this will unfinalize round %s and allow voting to continue' % (round_id,)

    warn(msg, force)

    rnd = coord_dao.unfinalize_rating_round(round_id)
    print(('++ unfinalized round %s (%s), voting can now continue'
           % (round_id, rnd.name)))
    return rnd

def list_campaigns(user_dao):
    "list details about all campaigns"
    # TODO: flags for names-only, w/details, machine-readable
    campaigns = user_dao.get_all_campaigns()
    pprint([c.to_details_dict() for c in campaigns])


def add_organizer(maint_dao, username):
    "Add a top-level organizer to the system, capable of creating campaigns and adding coordinators."
    maint_dao.add_organizer(username)
    print('++ added %s as organizer' % username)


def add_coordinator(user_dao, org_dao, campaign_id, username):
    "add specified user as coordinator of a given campaign"
    camp = user_dao.get_campaign(campaign_id)
    org_dao.add_coordinator(campaign_id, username=username)
    print(('++ added %r as coordinator for campaign %s (%r)'
           % (username, campaign_id, camp.name)))
    return


class Rollback(SystemExit):
    pass


def rdb_console(command_, maint_dao, user_dao, org_dao, rdb_session):
    "Load a developer console for interacting with database objects."
    local_scope = {}
    for m in dir(montage.rdb):
        local_scope[m] = getattr(montage.rdb, m)

    def rollback():
        raise Rollback()

    local_scope['pprint'] = pprint
    local_scope['session'] = rdb_session
    local_scope['rollback'] = rollback

    banner = ('rdb console:'
              '\n  Use "session.query(...)" to interact with the db.'
              '\n  Use "import pdb;pdb.pm()" to debug exceptions.'
              '\n  Commit and exit with "exit()" or pressing ctrl-d.'
              '\n  Rollback and exit with "rollback()".\n')
    # import pdb;pdb.set_trace()
    import code
    code.interact(banner=banner, local=local_scope)
    return


def create_campaign(org_dao):
    "interactively create a campaign"
    camp_name = input('?? Campaign name: ')
    if not camp_name:
        print('-- campaign name required, aborting')
        sys.exit(0)
    open_date_str = input('?? Open date: ')
    open_date = datetime.datetime.strptime(open_date_str, '%Y-%m-%d')
    close_date_str = input('?? Close date: ')
    close_date = datetime.datetime.strptime(close_date_str, '%Y-%m-%d')
    campaign = org_dao.create_campaign(name=camp_name,
                                       open_date=open_date,
                                       close_date=close_date)
    pprint(campaign.to_info_dict())
    print(('++ campaign %s (%r) created with %r as coordinator'
           % (campaign.id, campaign.name, org_dao.user.username)))
    return


@face_middleware(provides=['rdb_session'])
def _rdb_session_mw(next_, debug):
    rdb_session = make_rdb_session(echo=debug)

    try:
        ret = next_(rdb_session=rdb_session)
    except Exception as e:
        if debug:
            print(('!! %s: %s' % (e.__class__.__name__, e)))
            print(".. pre-rollback debug console, about to undo changes to db."
                  " When debuggig is complete, press 'c' to rollback changes"
                  " and resume exiting.")
            import pdb;pdb.post_mortem()
        rdb_session.rollback()
        if not isinstance(e, Rollback):
            raise
    else:
        if debug:
            print("== pre-commit debug console. about to persist changes to db,"
                  " press 'c' to continue or 'q' to quit.")
            import pdb;pdb.set_trace()
        rdb_session.commit()
    finally:
        rdb_session.close()

    return ret



@face_middleware(provides=['user_dao', 'maint_dao', 'org_dao', 'public_dao'])
def _admin_dao_mw(next_, rdb_session):
    # TODO: autolookup from login.wmflabs username
    user = lookup_user(rdb_session, 'Slaporte')
    user_dao = UserDAO(rdb_session, user)
    maint_dao = MaintainerDAO(user_dao)
    org_dao = OrganizerDAO(user_dao)
    public_dao = PublicDAO(user_dao.rdb_session)
    return next_(user_dao=user_dao, maint_dao=maint_dao, org_dao=org_dao, public_dao=public_dao)



if __name__ == '__main__':
    sys.exit(main())
