
import os.path
import argparse

from montage.rdb import User, Campaign, Round, Base, create_initial_tasks
from montage.loaders import load_full_csv

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(CUR_PATH, 'test_data')

DEFAULT_DB_URL = 'sqlite:///montage/tmp_montage.db'


def make_rdb_session(db_url=DEFAULT_DB_URL, echo=True):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # echo="debug" also prints results of selects, etc.
    engine = create_engine(db_url, echo=echo)
    Base.metadata.create_all(engine)

    session_type = sessionmaker()
    session_type.configure(bind=engine)
    session = session_type()
    return session


def populate_initial_data(db_url, debug=False, echo=True):
    rdb_session = make_rdb_session(db_url=db_url, echo=echo)
    coord = User(username='Leila')
    juror1 = User(username='Slaporte')
    juror2 = User(username='MahmoudHashemi')
    juror3 = User(username='Yarl')

    campaign = Campaign(name='Test Campaign 2016')
    rdb_session.add(campaign)
    round = Round(name='Test Round 1', quorum=2)
    rdb_session.add(round)

    campaign.coords.append(coord)

    round.jurors.append(juror1)
    round.jurors.append(juror2)
    round.jurors.append(juror3)

    CSV_PATH = DATA_PATH + '/wlm2015_ir_5.csv'

    with open(CSV_PATH) as f:
        entries = load_full_csv(f)

    for entry in entries:
        round.entries.append(entry)
    print ' + loaded %s entries' % len(entries)
    rdb_session.commit()

    tasks = create_initial_tasks(rdb_session, round)
    rdb_session.add_all(tasks)
    print ' + assigned %s tasks' % len(tasks)

    rdb_session.commit()
    if debug:
        import pdb;pdb.set_trace()
    return


def main():
    prs = argparse.ArgumentParser('create montage db and load initial data')
    add_arg = prs.add_argument
    add_arg('--db_url', default=DEFAULT_DB_URL)
    add_arg('--debug', action="store_true", default=False)
    add_arg('--verbose', action="store_true", default=False)

    args = prs.parse_args()

    try:
        populate_initial_data(echo=args.verbose,
                              debug=args.debug,
                              db_url=args.db_url)
    except Exception:
        if not args.debug:
            raise
        import pdb;pdb.post_mortem()

    return


if __name__ == '__main__':
    main()
