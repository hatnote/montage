# -*- coding: utf-8 -*-
import os
import sys
import argparse

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from montage.rdb import (make_rdb_session,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         lookup_user)


def add_organizer(maint_dao, new_org_name, debug=False):
    org_user = maint_dao.add_organizer(new_org_name)
    print '.. added %s as organizer' % new_org_name
    if debug:
        import pdb; pdb.set_trace()
    return


def cancel_round(maint_dao, rnd_id, debug):
    rnd = maint_dao.get_round(rnd_id)
    ret = maint_dao.cancel_round(rnd)
    stats = rnd.get_count_map()
    print ('.. cancelled round %s (%s), with %s tasks'
           % (rnd.id, rnd.name, stats['total_cancelled_tasks']))
    if debug:
        import pdb; pdb.set_trace()
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Admin CLI tools for montage')
    parser.add_argument('--organizer', help='add an organizer', type=str)
    parser.add_argument('--cancel_round', 
                        help=('set a round as cancelled, cancel related tasks'
                              ' and remove it from the campaign\'s active'
                              ' rounds'), type=int)
    parser.add_argument('--debug', action='store_true')
    
    args = parser.parse_args()

    rdb_session = make_rdb_session(echo=args.debug)

    maint = lookup_user(rdb_session, 'Slaporte')
    maint_dao = MaintainerDAO(rdb_session, maint)

    if args.organizer:
        new_org = args.organizer
        add_organizer(maint_dao, new_org, args.debug)

    if args.cancel_round:
        rnd_id = args.cancel_round
        cancel_round(maint_dao, rnd_id, args.debug)
