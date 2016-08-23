
# Relational database models for Montage

from sqlalchemy import (Column,
                        String,
                        Integer,
                        DateTime,
                        ForeignKey)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

from sqlalchemy.ext.declarative import declarative_base

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


class Campaign(Base):
    __tablename__ = 'campaigns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    
    create_date = Column(DateTime, server_default=func.now())

    admins = relationship('CampaignAdmin')
    entries_submitted = relationship('CampaignEntry')
    entries = association_proxy('entries_submitted', 'entry',
                                creator=lambda e: CampaignEntry(entry=e))


class CampaignAdmin(Base):
    __tablename__ = 'campaign_admins'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), primary_key=True)

    user = relationship('User', back_populates='admined_campaigns')
    campaign = relationship('Campaign', back_populates='admins')

    def __init__(self, user=None, campaign=None):
        self.user = user
        self.campaign = campaign


class Round(Base):
    __tablename__ = 'rounds'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    status = Column(String)
    vote_method = Column(String)
    quorum = Column(Integer)

    create_date = Column(DateTime, server_default=func.now())

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
    vote_updown = Column(Integer)
    vote_rating = Column(Integer)
    vote_ranking = Column(Integer)
    
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
    user = User()
    user.rounds.append(round)
    session.add(user)
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
