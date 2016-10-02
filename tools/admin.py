# -*- coding: utf-8 -*-
import os
import sys
import argparse
from pprint import pprint

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from montage.rdb import (make_rdb_session,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         lookup_user)

def warn(msg, force=False):
    if not force:
        confirmed = raw_input('??  %s. Type yes to confirm: ' % msg)
        if not confirmed == 'yes':
            print '-- you typed %r, aborting' % confirmed
            sys.exit(0)
    return



def add_organizer(maint_dao, new_org_name, debug=False):
    org_user = maint_dao.add_organizer(new_org_name)
    print '++ added %s as organizer' % new_org_name
    if debug:
        import pdb; pdb.set_trace()
    return

def cancel_campaign(maint_dao, camp_id, debug, force=False):
    campaign = maint_dao.get_campaign(camp_id)
    msg = ('this will cancel campaign %s (%s) and %s rounds, including tasks.'
           % (camp_id, campaign.name, len(campaign.rounds)))
    warn(msg, force)
    maint_dao.cancel_campaign(campaign)
    print ('++ cancelled campaign %s (%s) and %s rounds' 
           % (camp_id, campaign.name, len(campaign.rounds)))
    pass


def cancel_round(maint_dao, rnd_id, debug, force=False):
    rnd = maint_dao.get_round(rnd_id)
    msg = ('this will cancel round %s (%s) and its tasks'
           % (rnd_id, rnd.name))
    warn(msg, force)
    ret = maint_dao.cancel_round(rnd)
    stats = rnd.get_count_map()
    print ('++ cancelled round %s (%s), with %s tasks'
           % (rnd.id, rnd.name, stats['total_cancelled_tasks']))
    if debug:
        import pdb; pdb.set_trace()
    return


def add_coordinator(maint_dao, camp_id, username, debug):
    camp = maint_dao.get_campaign(camp_id)
    import pdb;pdb.set_trace()
    maint_dao.add_coordinator(camp, username=username)
    print ('++ added %s as coordinator for campaign %s (%s)'
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Admin CLI tools for montage')
    parser.add_argument('--add_organizer', 
                        help='add an organizer by username', 
                        type=str)
    parser.add_argument('--list',
                        help='list all campaigns and rounds',
                        action='store_true')
    parser.add_argument('--cancel-round', 
                        help=('set a round as cancelled, cancel related tasks'
                              ' and remove it from the campaign\'s active'
                              ' rounds'), type=int)
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

    #if args.remove_coordinator:
    #    username = args.remove_coordinator
    #    camp_id = args.campaign
    #    remove_coordinator(maint_dao, camp_id, username, args.debug)
