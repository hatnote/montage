# -*- coding: utf-8 -*-
"""DAO-free unit tests for the module-level task (re)assignment helpers
in montage.rdb, against an in-memory sqlite database.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from montage.rdb import (Base,
                         User,
                         Round,
                         Entry,
                         RoundEntry,
                         Vote,
                         reassign_rating_tasks,
                         ACTIVE_STATUS,
                         PAUSED_STATUS,
                         COMPLETED_STATUS,
                         CANCELLED_STATUS)


def make_session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_reassign_cancels_unfulfillable_task():
    """Regression: reassigning an active vote on an entry that every
    remaining juror has already completed used to crash with a
    ValueError from weighted_choice. The orphaned task is unfulfillable
    (coverage is already met), so it must be cancelled instead.
    """
    session = make_session()

    juror_a = User(id=1, username='JurorA')
    juror_b = User(id=2, username='JurorB')
    juror_c = User(id=3, username='JurorC')

    rnd = Round(name='test rating round',
                vote_method='rating',
                quorum=2,
                status=PAUSED_STATUS,
                jurors=[juror_a, juror_b, juror_c])
    entry = Entry(name='test entry.jpg')
    round_entry = RoundEntry(entry=entry, round=rnd)

    vote_a = Vote(user=juror_a, round_entry=round_entry,
                  status=COMPLETED_STATUS, value=0.8)
    vote_b = Vote(user=juror_b, round_entry=round_entry,
                  status=COMPLETED_STATUS, value=0.6)
    vote_c = Vote(user=juror_c, round_entry=round_entry,
                  status=ACTIVE_STATUS)

    session.add_all([rnd, round_entry, vote_a, vote_b, vote_c])
    session.flush()

    # juror C leaves; A and B have both already rated the entry, so C's
    # open task has no eligible juror and must be cancelled, not crash
    res = reassign_rating_tasks(session, rnd, [juror_a, juror_b])
    session.flush()

    assert res['cancelled_task_count'] == 1
    assert vote_c.status == CANCELLED_STATUS
    assert vote_c.modified_date is not None

    # completed votes are untouched and no new tasks appeared
    assert vote_a.status == COMPLETED_STATUS
    assert vote_b.status == COMPLETED_STATUS
    active_votes = session.query(Vote).filter_by(status=ACTIVE_STATUS).all()
    assert active_votes == []
