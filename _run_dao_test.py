
from montage.rdb import (make_rdb_session,
                         JurorDAO,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         lookup_user)
from montage.utils import PermissionDenied

import random

random.seed('badidea')

def main():
    rdb_session = make_rdb_session()

    cur_user = 'MahmoudHashemi'  # maintainer
    user_obj = lookup_user(rdb_session, cur_user)

    maint_dao = MaintainerDAO(rdb_session, user_obj)
    maint_dao.add_organizer('LilyOfTheWest')

    org_user = lookup_user(rdb_session, 'LilyOfTheWest')
    org_dao = OrganizerDAO(rdb_session, org_user)

    # should automatically add the creator as coordinator
    campaign = org_dao.create_campaign(name='Test Campaign 2016')

    org_dao.add_coordinator('Yarl', campaign.id)
    org_dao.add_coordinator('Slaporte', campaign.id)

    coord_user = lookup_user(rdb_session, 'Yarl')
    coord_dao = CoordinatorDAO(rdb_session, coord_user)



    # the org_dao should be able to do this stuff, too
    rnd = coord_dao.create_round(name='Test Round',
                                 quorum=3,
                                 vote_method='rating',
                                 jurors=['Slaporte', 'MahmoudHashemi', 'Yarl'],
                                 campaign=campaign)
    # returns successful, disqualified, total counts
    # coord_dao.add_entries_from_cat('Wiki Loves Monuments France 2015',
    #                               round_id=rnd.id)

    gist_url = 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'

    coord_dao.add_entries_from_csv_gist(gist_url, round_id=rnd.id)

    # coord_dao.edit_round(rnd.id, {'status': 'active'})

    coord_dao.activate_round(rnd.id)  # or something

    def cross_complete(rdb_session, rnd):
        juror1, juror2 = rnd.jurors[0], rnd.jurors[1]
        juror1_dao = JurorDAO(rdb_session, juror1)
        task = juror1_dao.get_tasks_from_round(rnd.id, num=1)[0]

        juror2_dao = JurorDAO(rdb_session, juror2)
        juror2_dao.apply_rating(task.id, 0.2)

        return

    try:
        cross_complete(rdb_session, rnd)
    except PermissionDenied:
        pass
    else:
        raise ValueError('expected permission denied on cross complete')

    for juror in rnd.jurors:
        print '.. voting for %s' % juror.username
        juror_dao = JurorDAO(rdb_session, juror)
        tasks = juror_dao.get_tasks_from_round(rnd.id)

        while tasks:
            task = tasks.pop()
            vote = random.choice([0.0, 0.25, 0.5, 0.75, 1.0])
            juror_dao.apply_rating(task.id, vote)
            tasks = juror_dao.get_tasks_from_round(rnd.id)

    import pdb;pdb.set_trace()

    # coord_dao.reassign(active_jurors=['Slaporte'])

    # task2 = juror_dao.get_next_task()
    # juror_dao.apply_rating(task2.id, 0.4)

    # # a loop going over a bunch more ratings probably until
    # # get_next_task returns None

    # # coord_dao can do the following, too
    # # org_dao.cancel_round
    # org_dao.close_round(rnd.id)

    # # start new round
    # # close round
    # # close campaign
    # # download audit logs


if __name__ == '__main__':
    main()
