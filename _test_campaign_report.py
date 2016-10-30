
from montage.rdb import *
from montage.rdb import make_rdb_session, CoordinatorDAO, User

def main():
    rdb_session = make_rdb_session(echo=False)

    user = rdb_session.query(User).first()
    cdao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = cdao.get_campaign(1)

    ctx = cdao.get_campaign_report(campaign)

    import pdb;pdb.set_trace()


if __name__ == '__main__':
    main()
