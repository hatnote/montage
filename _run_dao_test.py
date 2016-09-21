
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
    org_dao.add_coordinator('Slaporte', campaign.id)

    coord_user = lookup_user(rdb_session, 'Yarl')
    coord_dao = CoordinatorDAO(rdb_session, coord_user)

    # the org_dao should be able to do this stuff, too
    rnd = coord_dao.create_round(name='Test Round 1',
                                 quorum=2,
                                 jurors=['Slaporte', 'MahmoudHashemi'],
                                 campaign=campaign)
    # returns successful, disqualified, total counts
    # coord_dao.add_entries_from_cat('Wiki Loves Monuments France 2015',
    #                               round_id=rnd.id)

    coord_dao.add_entries_from_csv_gist('https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/9181d59224cd3335a8f434ff4683c83023f7a3f9/wlm2015_fr_12k.csv', round_id=rnd.id)
    
    # coord_dao.edit_round(rnd.id, {'status': 'active'})

    coord_dao.activate_round(rnd.id)  # or something
    
    juror_user = lookup_user(rdb_session, 'Slaporte')
    juror_dao = JurorDAO(rdb_session, juror_user)
    tasks = juror_dao.get_next_task()
    
    task1 = tasks[0]
    
    juror_dao.apply_rating(task1.id, 0.8)

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
