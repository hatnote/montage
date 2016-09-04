
import os.path

from montage.rdb import User, Campaign, Round, Base, create_initial_tasks
from montage.loaders import load_full_csv

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(CUR_PATH, 'test_data')


def make_rdb_session(db_url='sqlite:///tmp_montage.db', echo=True):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # echo="debug" also prints results of selects, etc.
    engine = create_engine(db_url, echo=echo)
    Base.metadata.create_all(engine)

    session_type = sessionmaker()
    session_type.configure(bind=engine)
    session = session_type()
    return session


def make_fake_data(debug=True, echo=True):
    rdb_session = make_rdb_session(echo=echo)
    coord = User(username='Leila')
    juror1 = User(username='Slaporte')
    juror2 = User(username='MahmoudHashemi')
    juror3 = User(username='Yuvi')

    campaign = Campaign(name='Test Campaign 2016')
    rdb_session.add(campaign)

    campaign.coords.append(coord)
    round = Round(name='Test Round 1', quorum=2)
    campaign.rounds.append(round)
    round.jurors.append(juror1)
    round.jurors.append(juror2)
    round.jurors.append(juror3)

    CSV_PATH = DATA_PATH + '/wlm2015_fr_12k.csv'

    with open(CSV_PATH) as f:
        entries = load_full_csv(f)

    for entry in entries:
        round.entries.append(entry)
    rdb_session.commit()

    tasks = create_initial_tasks(rdb_session, round)
    rdb_session.add_all(tasks)

    rdb_session.commit()
    if debug:
        import pdb;pdb.set_trace()
    return


def main():
    make_fake_data(True, False)
    return


if __name__ == '__main__':
    main()
