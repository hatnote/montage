# -*- coding: utf-8 -*-

import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from montage.rdb import (Base, 
                         UserDAO,
                         CoordinatorDAO, 
                         Round, 
                         Campaign, 
                         User, 
                         CANCELLED_STATUS, 
                         ACTIVE_STATUS, 
                         FINALIZED_STATUS)

def test_get_campaign_rounds_dao():
    """
    Unit test for get_campaign_rounds logic.
    Verified fix for PR #500 / Issue #399.
    """
    # 1. Setup in-memory SQLite database
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 2. Populate with test data
    user = User(username='test_coord')
    session.add(user)
    
    campaign = Campaign(name='Test Campaign')
    session.add(campaign)
    session.flush()

    # We add rounds out of chronological order to verify ordering logic
    # Round 1: Finalized, earliest
    r1 = Round(name='Round 1', 
               status=FINALIZED_STATUS, 
               campaign=campaign, 
               create_date=datetime.datetime(2023, 1, 1))
    
    # Round 3: Cancelled, latest
    r3 = Round(name='Round 3', 
               status=CANCELLED_STATUS, 
               campaign=campaign, 
               create_date=datetime.datetime(2023, 1, 10))
    
    # Round 2: Active, middle
    r2 = Round(name='Round 2', 
               status=ACTIVE_STATUS, 
               campaign=campaign, 
               create_date=datetime.datetime(2023, 1, 5))
    
    session.add_all([r1, r2, r3])
    session.commit()

    # 3. Instantiate DAO
    user_dao = UserDAO(session, user)
    dao = CoordinatorDAO(user_dao, campaign)

    # 4. Assertions: Default behavior (with_cancelled=False)
    rounds = dao.get_campaign_rounds(campaign, with_cancelled=False)
    
    assert len(rounds) == 2, "Should return exactly 2 non-cancelled rounds"
    assert r3 not in rounds, "Cancelled round should be filtered out"
    
    # Check ordering (earliest first)
    assert rounds[0].id == r1.id
    assert rounds[1].id == r2.id
    assert rounds[0].create_date < rounds[1].create_date

    # 5. Assertions: Including cancelled rounds
    all_rounds = dao.get_campaign_rounds(campaign, with_cancelled=True)
    assert len(all_rounds) == 3, "Should return all 3 rounds when with_cancelled=True"
    assert r3 in all_rounds
    
    # Check ordering across all 3
    assert all_rounds[0].id == r1.id
    assert all_rounds[1].id == r2.id
    assert all_rounds[2].id == r3.id

    print("DAO get_campaign_rounds unit test passed successfully.")

if __name__ == "__main__":
    try:
        test_get_campaign_rounds_dao()
    except AssertionError as e:
        print(f"Test Failed: {e}")
        exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)
