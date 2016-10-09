# -*- coding: utf-8 -*-
import os
import sys
import argparse
from datetime import datetime
from pprint import pprint

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from montage.rdb import (make_rdb_session,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         lookup_user)

from montage.utils import get_threshold_map

GIST_URL = 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'
RANKING_MAX = 40


def warn(msg, force=False):
    if not force:
        confirmed = raw_input('??  %s. Type yes to confirm: ' % msg)

        if not confirmed == 'yes':
            print '-- you typed %r, aborting' % confirmed
            sys.exit(0)

    return


def create_campaign(maint_dao, username):
    coord_user = maint_dao.get_or_create_user(username, 'coordinator')
    camp_name = raw_input('?? Campaign name: ')

    if not camp_name:
        print '-- campaign name required, aborting'
        sys.exit(0)

    open_date_str = raw_input('?? Open date: ')
    open_date = datetime.strptime(open_date_str, '%Y-%m-%d')
    close_date_str = raw_input('?? Close date: ')
    close_date = datetime.strptime(close_date_str, '%Y-%m-%d')
    campaign = maint_dao.create_campaign(name=camp_name,
                                         open_date=open_date,
                                         close_date=close_date,
                                         coords=[coord_user])

    rdb_session.commit()

    pprint(campaign.to_info_dict())
    print ('++ campaign %s (%r) created with %r as coordinator' 
           % (campaign.id, campaign.name, coord_user.username))
    return campaign


def create_round(maint_dao, campaign_id, advance=False, debug=False):
    campaign = maint_dao.get_campaign(campaign_id)
    rnd_name = raw_input('?? Round name: ')

    if not rnd_name:
        print '-- round name required, aborting'
        sys.exit(0)

    juror_names_str = raw_input('?? Juror names (comma separated): ')
    juror_names = [j.strip() for j in juror_names_str.split(',')]
    vote_method = raw_input('?? Vote method (rating, yesno, or ranking): ')

    if vote_method not in ['rating', 'yesno', 'ranking']:
        print '-- vote method must be rating, yesno, or ranking, aborting'
        sys.exit(0)

    if vote_method != 'ranking':
        quorum = raw_input('?? Voting quorum: ')
    else:
        quorum = len(juror_names)

    deadline_date_str = raw_input('?? Deadline date: ')
    deadline_date = datetime.strptime(deadline_date_str, '%Y-%m-%d')
    description = raw_input('?? Description: ')
    directions = raw_input('?? Directions: ')

    if not advance:
        category_name = raw_input('?? Category: ')

    rnd = maint_dao.create_round(name=rnd_name,
                                 quorum=quorum,
                                 vote_method=vote_method,
                                 deadline_date=deadline_date,
                                 jurors=juror_names,
                                 directions=directions,
                                 description=description,
                                 campaign=campaign)

    pprint(rnd.to_info_dict())

    print ('++ round %s (%r) created in campaign %s (%r)' 
           % (rnd.id, rnd.name, campaign.id, campaign.name))

    if not advance:
        entries = maint_dao.add_entries_from_cat(rnd, category_name)
        source = category_name
        #entries = maint_dao.add_entries_from_csv_gist(rnd, GIST_URL)
        #source = GIST_URL
        print ('++ prepared %s entries from %r' %
               (len(entries), source))
        maint_dao.add_round_entries(rnd, entries)
    else:
        final_rnds = [r for r in campaign.rounds if r.status == 'finalized']
        last_successful_rnd = final_rnds[-1]
        advancing_group = maint_dao.get_rating_advancing_group(last_successful_rnd)
        entries = advancing_group
        if vote_method == 'ranking' and len(entries) > RANKING_MAX:
            print ('-- %s is too many entries for ranking round, aborting'
                   % len(entries))
            # TODO: does not actually roll back the round, since 
            # create_round commits on its own. Should individual dao methods
            # have an option to not commit?
            rdb_session.rollback()
            sys.exit(0)        

        source = 'round(#%s)' % last_successful_rnd.id
        maint_dao.add_round_entries(rnd, advancing_group, source)

    rdb_session.commit()

    print ('++ added entries from %s to round %s (%r)'
           % (source, rnd.id, rnd.name))

    if debug:
        import pdb;pdb.set_trace()
    return rnd


def add_organizer(maint_dao, new_org_name, debug=False):
    org_user = maint_dao.add_organizer(new_org_name)

    print '++ added %s as organizer' % new_org_name

    if debug:
        import pdb; pdb.set_trace()
    return


def cancel_campaign(maint_dao, camp_id, debug, force=False):
    campaign = maint_dao.get_campaign(camp_id)
    msg = ('this will cancel campaign %s (%r) and %s rounds, including tasks.'
           % (camp_id, campaign.name, len(campaign.rounds)))

    warn(msg, force)

    maint_dao.cancel_campaign(campaign)

    print ('++ cancelled campaign %s (%r) and %s rounds' 
           % (camp_id, campaign.name, len(campaign.rounds)))
    pass


def cancel_round(maint_dao, rnd_id, debug, force=False):
    rnd = maint_dao.get_round(rnd_id)
    msg = ('this will cancel round %s (%r) and its tasks'
           % (rnd_id, rnd.name))

    warn(msg, force)

    ret = maint_dao.cancel_round(rnd)
    stats = rnd.get_count_map()

    print ('++ cancelled round %s (%r), with %s tasks'
           % (rnd.id, rnd.name, stats['total_cancelled_tasks']))

    if debug:
        import pdb;pdb.set_trace()
    return


def activate_round(maint_dao, rnd_id, debug):
    rnd = maint_dao.get_round(rnd_id)
    
    maint_dao.activate_round(rnd)
    maint_dao.rdb_session.commit()
    
    print '++ activated round %s (%s)' % (rnd.id, rnd.name)

    if debug:
        import pdb;pdb.set_trace()
    return rnd


def pause_round(maint_dao, rnd_id, debug):
    rnd = maint_dao.get_round(rnd_id)
    
    maint_dao.pause_round(rnd)
    maint_dao.rdb_session.commit()

    print '++ paused round %s (%r)' % (rnd.id, rnd.name)
    
    if debug:
        import pdb;pdb.set_trace()
    return rnd


def add_coordinator(maint_dao, camp_id, username, debug):
    camp = maint_dao.get_campaign(camp_id)

    maint_dao.add_coordinator(camp, username=username)

    print ('++ added %r as coordinator for campaign %s (%r)'
           % (username, camp_id, camp.name))
    if debug:
        import pdb;pdb.set_trace()
    return


def remove_coordinator(maint_dao, camp_id, username, debug):
    # TODO: the campaign_coords table should have an is_active column
    raise NotImplementedError('cannot remove coordinators for now')
    '''
    camp = maint_dao.get_campaign(camp_id)
    user = maint_dao.get_or_create_user(username, 'coordinator',
                                        campaign=camp)
    print ('-- remvoed %s as coordinator from campaign %s (%s)'
           % (username, camp_id, camp.name))
    if debug:
        import pdb;pdb.set_trace()
    return
    '''


def advance_round(maint_dao, rnd_id, debug):
    rnd = maint_dao.get_round(rnd_id)
    # TODO: see if the round is open

    avg_ratings_map = maint_dao.get_round_average_rating_map(rnd)
    threshold_map = get_threshold_map(avg_ratings_map)

    print '-- Round threshold map...'
    pprint(threshold_map)

    threshold = raw_input('?? Include at least how many images: ')
    threshold = int(threshold)

    if not threshold:
        print '-- no threshold provided, aborting'
        sys.exit(0)

    cur_thresh = [t for t, c in sorted(threshold_map.items()) \
                  if c >= threshold][-1]

    maint_dao.finalize_rating_round(rnd, cur_thresh)

    camp_id = rnd.campaign.id

    print ('++ ready to import %s entries to the next round in %s (%r)...' 
           % (threshold_map[cur_thresh], camp_id, rnd.campaign.name))

    next_round = create_round(maint_dao, camp_id, advance=True, debug=debug)
  
    if debug:
        import pdb;pdb.set_trace()
    return next_round


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Admin CLI tools for montage')
    parser.add_argument('--add_organizer', 
                        help='add an organizer by username', 
                        type=str)
    parser.add_argument('--list',
                        help='list all campaigns and rounds',
                        action='store_true')
    parser.add_argument('--cancel-round', 
                        help=('set a round as cancelled, cancel related'
                              ' tasks and remove it from the campaign\'s'
                              ' active  rounds'), type=int)
    parser.add_argument('--cancel-campaign', 
                        help=('cancel a campaign by id, including all of its'
                              ' rounds and associated tasks'), type=int)
    parser.add_argument('--add-coordinator', 
                        help=('add a coordinator by username to a campaign'), 
                        type=str)
    #parser.add_argument('--remove-coordinator', 
    #                    help=('remove a coordinator by username from a '
    #                          'campaign (not implemented'), 
    #                    type=str)
    parser.add_argument('--create-campaign',
                        help=('create a new campaign with a  specified coordiantor'),
                        type=str)
    parser.add_argument('--create-round',
                        help=('create a new round in a specified campaign'),
                        type=int)
    parser.add_argument('--activate-round',
                        help=('activate a specified round to start voting'),
                        type=int)
    parser.add_argument('--pause-round',
                        help=('pause a specified round if you wish to make edits'),
                        type=int)
    parser.add_argument('--advance-round',
                        help=('finalize a specified round and start the next'),
                        type=int)
    parser.add_argument('--campaign', help='campaign id', type=int)
    parser.add_argument('--force', action='store_true', 
                        help='Use with caution when cancelling things')
    parser.add_argument('--debug', action='store_true')

    
    args = parser.parse_args()

    rdb_session = make_rdb_session(echo=args.debug)

    maint = lookup_user(rdb_session, 'Slaporte')
    maint_dao = MaintainerDAO(rdb_session, maint)

    if args.list:
        campaigns = maint_dao.get_all_campaigns()
        pprint([c.to_details_dict() for c in campaigns])

    if args.add_organizer:
        new_org = args.organizer
        add_organizer(maint_dao, new_org, args.debug)

    if args.cancel_round:
        rnd_id = args.cancel_round
        cancel_round(maint_dao, rnd_id, args.debug, args.force)

    if args.cancel_campaign:
        camp_id = args.cancel_campaign
        cancel_campaign(maint_dao, camp_id, args.debug, args.force)

    if args.add_coordinator:
        username = args.add_coordinator
        camp_id = args.campaign
        add_coordinator(maint_dao, camp_id, username, args.debug)

    if args.create_campaign:
        coord_name = args.create_campaign
        create_campaign(maint_dao, coord_name, debug=args.debug)
    
    if args.create_round:
        campaign_id = args.create_round
        create_round(maint_dao, campaign_id)

    if args.activate_round:
        rnd_id = args.activate_round
        activate_round(maint_dao, rnd_id, args.debug)

    if args.pause_round:
        rnd_id = args.pause_round
        pause_round(maint_dao, rnd_id, args.debug)

    if args.advance_round:
        rnd_id = args.advance_round
        advance_round(maint_dao, rnd_id, args.debug)

    #if args.remove_coordinator:
    #    username = args.remove_coordinator
    #    camp_id = args.campaign
    #    remove_coordinator(maint_dao, camp_id, username, args.debug)
