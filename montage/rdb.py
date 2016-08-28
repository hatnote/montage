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


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    ca_user = Column(String)

    create_date = Column(DateTime, server_default=func.now())
    
    admined_campaigns = relationship('CampaignAdmin', back_populates='user')
    campaigns = association_proxy('admined_campaigns', 'campaign',
                                  creator=lambda c: CampaignAdmin(campaign=c))
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
    campaign_admins = relationship('CampaignAdmin')
    admins = association_proxy('campaign_admins', 'user',
                               creator=lambda u: CampaignAdmin(user=u))
    entries_submitted = relationship('CampaignEntry')
    entries = association_proxy('entries_submitted', 'entry',
                                creator=lambda e: CampaignEntry(entry=e))


class CampaignAdmin(Base):
    __tablename__ = 'campaign_admins'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), primary_key=True)

    user = relationship('User', back_populates='admined_campaigns')
    campaign = relationship('Campaign', back_populates='campaign_admins')

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
    jurors = relationship('RoundJurors')
    votes = relationship('Vote', back_populates='round')


class RoundJurors(Base):
    __tablename__ = 'round_jurors'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), primary_key=True)

    user = relationship('User', back_populates='jurored_rounds')
    round = relationship('Round', back_populates='jurors')

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


def get_campaign(session, user, id=None, name=None):
    # Should it support getting campaigns by name, for prettier URLs?
    campaign = session.query(Campaign)\
                      .filter(Campaign.admins.any(ca_user=user))\
                      .filter_by(id=id)\
                      .one()
    return campaign


def get_round(session, user, id):
    
    return


def get_all_campaigns(session, user):
    campaigns = session.query(Campaign)\
                       .filter(Campaign.admins.any(ca_user=user))\
                       .all()
    return campaigns


def main():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # echo="debug" also prints results of selects, etc.
    engine = create_engine('sqlite:///tmp_montage.db', echo=True)
    Base.metadata.create_all(engine)

    session_type = sessionmaker()
    session_type.configure(bind=engine)
    session = session_type()
    round = Round()
    campaign = Campaign(name='Test')
    another_campaign = Campaign(name='Another')
    user = User(ca_user='slaporte')
    user.rounds.append(round)
    user.campaigns.append(campaign)
    user.campaigns.append(another_campaign)
    another_user = User(ca_user='mahmoud')
    another_user.campaigns.append(another_campaign)
    session.add(user)
    session.add(another_user)
    session.commit()
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
