
import random
import datetime
from pprint import pprint

from montage.rdb import (make_rdb_session,
                         JurorDAO,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         lookup_user)

from montage.utils import PermissionDenied, get_threshold_map, load_env_config

random.seed('badidea')

GIST_URL = 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'

config = load_env_config()

def cross_complete(rdb_session, rnd):
    juror1, juror2 = rnd.jurors[0], rnd.jurors[1]
    juror1_dao = JurorDAO(rdb_session, juror1)
    task = juror1_dao.get_tasks_from_round(rnd, num=1)[0]

    juror2_dao = JurorDAO(rdb_session, juror2)
    juror2_dao.apply_rating(task, 0.2)

    return


def rate_round_tasks(rdb_session, rnd, limit_per=None):
    for juror in rnd.jurors:
        print '.. voting for %s' % juror.username
        juror_dao = JurorDAO(rdb_session, juror)
        tasks = juror_dao.get_tasks_from_round(rnd)

        count = 0
        while tasks:
            if limit_per and count > limit_per:
                break
            task = tasks.pop()
            vote = random.choice([0.0, 0.25, 0.5, 0.75, 1.0])
            juror_dao.apply_rating(task, vote)
            tasks = juror_dao.get_tasks_from_round(rnd)
            count += 1

    return


def main():
    rdb_session = make_rdb_session()

    # TODO: startup should add maintainers as users
    mahm_user = lookup_user(rdb_session, 'MahmoudHashemi')  # maintainer

    maint_dao = MaintainerDAO(rdb_session, mahm_user)
    org_user = maint_dao.add_organizer('LilyOfTheWest')
    org_dao = OrganizerDAO(rdb_session, org_user)

    # should automatically add the creator as coordinator
    campaign = org_dao.create_campaign(name='Basic test campaign',
                                       open_date=datetime.datetime(2015, 9, 10),
                                       close_date=datetime.datetime(2015, 10, 1))

    mahm_user = org_dao.add_coordinator(campaign, username='MahmoudHashemi')
    slap_user = org_dao.add_coordinator(campaign, 'Slaporte')
    leila_user = org_dao.add_coordinator(campaign, 'LilyOfTheWest')
    import pdb;pdb.set_trace()
    coord_dao = CoordinatorDAO(rdb_session, yarl_user)

    juror_usernames = ['Slaporte', 'MahmoudHashemi', 'Yarl', 'Erwmat']

    rnd = coord_dao.create_round(name='Test Round 1',
                                 quorum=3,
                                 vote_method='rating',
                                 deadline_date=datetime.datetime(2015, 10, 15),
                                 jurors=juror_usernames,
                                 campaign=campaign)
    # returns successful, disqualified, total counts
    # coord_dao.add_entries_from_cat(rnd, 'Wiki Loves Monuments France 2015')


    if config.get('labs_db'):
        entries = coord_dao.add_entries_from_cat(rnd, 'Images_from_Wiki_Loves_Monuments_2015_in_Pakistan')
    else:
        entries = coord_dao.add_entries_from_csv_gist(rnd, GIST_URL)

    coord_dao.add_round_entries(rnd, entries)

    coord_dao.autodisqualify_by_date(rnd)
    coord_dao.autodisqualify_by_resolution(rnd)
    coord_dao.autodisqualify_by_uploader(rnd)

    #coord_dao.disqualify_entry(entry)

    coord_dao.activate_round(rnd)

    try:
        cross_complete(rdb_session, rnd)
    except PermissionDenied:
        pass
    else:
        raise ValueError('expected permission denied on cross complete')

    rate_round_tasks(rdb_session, rnd, limit_per=20)

    coord_dao.cancel_round(rnd)

    # # should fail, quorum must be <= # of jurors
    # coord_dao.reassign(active_jurors=['Slaporte'])

    rnd = coord_dao.create_round(name='Test Round 1.1',
                                 quorum=2,
                                 vote_method='rating',
                                 deadline_date=datetime.datetime(2015, 10, 15),
                                 jurors=juror_usernames,
                                 campaign=campaign)
    entries = coord_dao.add_entries_from_csv_gist(rnd, GIST_URL)
    coord_dao.add_round_entries(rnd, entries)
    coord_dao.activate_round(rnd)

    rate_round_tasks(rdb_session, rnd, limit_per=50)

    coord_dao.modify_jurors(rnd, [slap_user, yarl_user])

    # some read tasks

    rate_round_tasks(rdb_session, rnd)

    avg_ratings_map = coord_dao.get_round_average_rating_map(rnd)
    threshold_map = get_threshold_map(avg_ratings_map)

    # let at least 100 through
    cur_thresh = [t for t, c in sorted(threshold_map.items()) if c >= 100][-1]

    adv_group = coord_dao.get_rating_advancing_group(rnd, cur_thresh)
    coord_dao.finalize_rating_round(rnd, cur_thresh)
    campaign = coord_dao.get_campaign(campaign.id)

    assert campaign.active_round is None

    #
    # Time for Round 2
    #

    rnd2 = coord_dao.create_round(campaign,
                                  name='Test Round 2',
                                  vote_method='rating',
                                  quorum=2,
                                  jurors=juror_usernames,
                                  deadline_date=datetime.datetime(2015, 11, 1))
    final_rnds = [r for r in campaign.rounds if r.status == 'finalized']
    last_successful_rnd = final_rnds[-1]  # TODO: these are ordered by date?
    advancing_group = coord_dao.get_rating_advancing_group(last_successful_rnd)

    source = 'round(#%s)' % last_successful_rnd.id
    coord_dao.add_round_entries(rnd2, advancing_group, source)
    coord_dao.activate_round(rnd2)

    rate_round_tasks(rdb_session, rnd2, limit_per=20)
    coord_dao.pause_round(rnd2)
    coord_dao.activate_round(rnd2)
    rate_round_tasks(rdb_session, rnd2)
    avg_ratings_map = coord_dao.get_round_average_rating_map(rnd2)
    threshold_map = get_threshold_map(avg_ratings_map)
    if config.get('labs_db'):
        # Assumign the category stays the same
        assert threshold_map == ROUND_2_CAT_THRESH
    else:
        assert threshold_map == ROUND_2_THRESH
    #
    #
    #

    # # close campaign
    # # download audit logs

    rdb_session.commit()
    pprint(threshold_map)

    import pdb;pdb.set_trace()


ROUND_2_THRESH = {0.0: 128, 0.125: 124, 0.25: 109, 0.375: 99,
                  0.5: 81, 0.625: 59, 0.75: 33, 0.875: 14, 1.0: 3}

ROUND_2_CAT_THRESH = {0.25: 109, 0.5: 81, 0.625: 59, 1.0: 3, 0.0: 128,
                     0.125: 124, 0.375: 99, 0.75: 33, 0.875: 14}

if __name__ == '__main__':
    main()
