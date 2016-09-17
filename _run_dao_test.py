
from montage.rdb import (make_rdb_session,
                         JurorDAO,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         lookup_user)

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

    coord_user = lookup_user(rdb_session, 'Yarl')
    coord_dao = CoordinatorDAO(rdb_session, coord_user)

    # the org_dao should be able to do this stuff, too
    rnd = coord_dao.create_round(name='Test Round 1',
                                 quorum=2,
                                 jurors=['Slaporte', 'MahmoudHashemi'],
                                 campaign=campaign)
    # # returns successful, disqualified, total counts
    # # coord_dao.add_entries_from_cat('Wiki Loves Monuments France 2015',
    # #                               round_id=rnd.id)
    # coord_dao.add_entries_from_csv_url('http://commons.wikimedia.org/...',
    #                                    round_id=rnd.id)

    # coord_dao.activate_round(rnd.id)  # or something

    # juror_dao = JurorDAO(lookup_user('Slaporte'))
    # task1 = juror_dao.get_next_task()

    # juror_dao.apply_rating(task1.id, 0.8)

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
