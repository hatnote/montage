# Relational database models for Montage
from sqlalchemy import (Column,
                        String,
                        Integer,
                        Float,
                        Boolean,
                        DateTime,
                        ForeignKey)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

from sqlalchemy.ext.declarative import declarative_base

from simple_serdes import DictableBase

Base = declarative_base()

"""
Column ordering and groupings:
* ID
* Data
* Metadata (creation date)
* 1-n relationships
* n-n relationships
"""


class User(Base, DictableBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    last_login_date = Column(DateTime)

    create_date = Column(DateTime, server_default=func.now())

    coordinated_campaigns = relationship('CampaignCoord', back_populates='user')
    campaigns = association_proxy('coordinated_campaigns', 'campaign',
                                  creator=lambda c: CampaignCoord(campaign=c))

    jurored_rounds = relationship('RoundJurors', back_populates='user')
    rounds = association_proxy('jurored_rounds', 'round',
                               creator=lambda r: RoundJurors(round=r))
    votes = relationship('Vote', back_populates='user')
    # update_date?


class Campaign(Base, DictableBase):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    open_date = Column(DateTime)
    close_date = Column(DateTime)

    create_date = Column(DateTime, server_default=func.now())

    rounds = relationship('Round', back_populates='campaign')
    campaign_coords = relationship('CampaignCoord')
    coords = association_proxy('campaign_coords', 'user',
                               creator=lambda u: CampaignCoord(user=u))
    entries_submitted = relationship('CampaignEntry')
    entries = association_proxy('entries_submitted', 'entry',
                                creator=lambda e: CampaignEntry(entry=e))


class CampaignCoord(Base):
    __tablename__ = 'campaign_coords'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), primary_key=True)

    user = relationship('User', back_populates='coordinated_campaigns')
    campaign = relationship('Campaign', back_populates='campaign_coords')

    def __init__(self, user=None, campaign=None):
        self.user = user
        self.campaign = campaign


class Round(Base, DictableBase):
    __tablename__ = 'rounds'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    open_date = Column(DateTime)
    close_date = Column(DateTime)
    status = Column(String)
    vote_method = Column(String)
    quorum = Column(Integer)
    # Should we just have some settings in json?
    show_link = Column(Boolean)
    show_filename = Column(Boolean)
    show_resolution = Column(Boolean)

    create_date = Column(DateTime, server_default=func.now())

    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    campaign = relationship('Campaign', back_populates='rounds')
    round_jurors = relationship('RoundJurors')
    jurors = association_proxy('round_jurors', 'user',
                              creator=lambda u: RoundJuror(user=u))
    votes = relationship('Vote', back_populates='round')


class RoundJurors(Base):
    __tablename__ = 'round_jurors'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), primary_key=True)

    user = relationship('User', back_populates='jurored_rounds')
    round = relationship('Round', back_populates='round_jurors')

    def __init__(self, user=None, round=None):
        self.user = user
        self.round = round


class Entry(Base):
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    timestamp = Column(DateTime)
    url = Column(String)
    description_url = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    license = Column(String)
    author = Column(String)
    uploader = Column(String)

    create_date = Column(DateTime, server_default=func.now())

    campaigns = relationship('CampaignEntry')
    votes = relationship('Vote', back_populates='entry')


class CampaignEntry(Base):
    __tablename__ = 'campaign_entries'

    entry_id = Column(Integer, ForeignKey('entries.id'), primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), primary_key=True)

    entry = relationship('Entry', back_populates='campaigns')
    campaign = relationship('Campaign', back_populates='entries_submitted')

    def __init__(self, entry=None, campaign=None):
        self.entry = entry
        self.campaign = campaign


class Vote(Base):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    entry_id = Column(Integer, ForeignKey('entries.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    old_task_id = Column(Integer)
    vote = Column(Float)
    is_canceled = Column(Boolean)

    create_date = Column(DateTime, server_default=func.now())

    user = relationship('User', back_populates='votes')
    round = relationship('Round', back_populates='votes')
    entry = relationship('Entry', back_populates='votes')


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    entry_id = Column(Integer, ForeignKey('entries.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))


class UserDAO(object):
    """The Data Acccess Object wraps the rdb_session and active user
    model, providing a layer for model manipulation through
    expressively-named methods.

    As the DAO expands, it will likely break up into multiple DAOs for
    different areas of the schema.

    # TODO: name? true that user is bound in, but UserDAO doesn't ring
    totally true.
    # TODO: will blow up a bit if user is None

    # TODO: rather than query(Model), this should do user.models and
    filter from there, I'm thinking.
    """
    def __init__(self, rdb_session, user):
        self.rdb_session = rdb_session
        self.user = user

    def query(self, *a, **kw):
        "a call-through to the underlying session.query"
        return self.rdb_session.query(*a, **kw)

    def get_campaign_config(self, campaign_id=None):
        campaign = self.query(Campaign)\
                       .filter(Campaign.coords.any(id=self.user.id))\
                       .filter_by(id=campaign_id)\
                       .one()
        ret = campaign.to_dict()
        ret['rounds'] = [r.to_dict() for r in campaign.rounds]

        return ret

    def get_campaign_overview(self, campaign_id):
        # TODO: campaign_id wasn't referenced?
        campaign = self.query(Campaign)\
                       .filter(Campaign.rounds.any(Round.jurors.any(id=self.user.id))).all()
        return campaign

    def get_campaign_name(self, campaign_id):
        campaign = self.query(Campaign).filter_by(id=campaign_id).one()
        return campaign.name

    def get_round(self, round_id):
        round = self.query(Round)\
                    .filter(Round.campaign.has(Campaign.coords.any(id=self.user.id)),
                            Round.id == round_id)\
                    .one()
        return round

    def get_all_campaigns(self):
        campaigns = self.query(Campaign)\
                        .filter(Campaign.coords.any(username=self.user.username))\
                        .all()
        return campaigns

    def get_all_rounds(self):
        rounds = self.query(Round)\
                     .filter(Round.jurors.any(username=self.user.username))\
                     .group_by(Round.campaign_id)\
                     .all()
        ret = [r.to_dict() for r in rounds]
        return ret



def make_rdb_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # echo="debug" also prints results of selects, etc.
    engine = create_engine('sqlite:///tmp_montage.db', echo=True)
    Base.metadata.create_all(engine)

    session_type = sessionmaker()
    session_type.configure(bind=engine)
    session = session_type()
    return session


def make_fake_data():
    rdb_session = make_rdb_session()
    first_user = User(username='Slaporte')
    second_user = User(username='Mahmoud')
    juror = User(username='Slaporte')
    campaign = Campaign(name='test campaign')
    round = Round(name='test round')
    campaign.rounds.append(round)
    first_user.campaigns.append(campaign)
    second_user.campaigns.append(campaign)
    juror.rounds.append(round)
    rdb_session.add(first_user)
    rdb_session.add(second_user)
    rdb_session.add(juror)
    rdb_session.commit()


def main():
    make_fake_data()
    import pdb;pdb.set_trace()

    return


if __name__ == '__main__':
    main()


"""
* Indexes
* db session management, engine creation, and schema creation separation
* prod db pw management
* add simple_serdes for E-Z APIs
* revision_id - verify if we must use the upload timestamp
"""
