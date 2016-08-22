
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
* Metadata (creation date/location)
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

    # update_date?


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    admins = relationship('CampaignAdmin')

    create_date = Column(DateTime, server_default=func.now())


class CampaignAdmin(Base):
    __tablename__ = 'campaign_admins'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), primary_key=True)

    user = relationship('User', back_populates='admined_campaigns')
    campaign = relationship('Campaign', back_populates='admins')

    def __init__(self, user=None, campaign=None):
        self.user = user
        self.campaign = campaign


"""
class RoundJurors(Base):
    __tablename__ = 'round_jurors'
    # per-round role

    # possible roles:

    # user fk
    # round fk


class Round(Base):
    __tablename__ = 'Rounds'

    id = Column(Integer, primary_key=True)
"""


def main():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # echo="debug" also prints results of selects, etc.
    engine = create_engine('sqlite:///tmp_montage.db', echo=True)
    Base.metadata.create_all(engine)

    session_type = sessionmaker()
    session_type.configure(bind=engine)
    session = session_type()

    user = User()
    campaign = Campaign()
    user.campaigns.append(campaign)

    session.add(user)
    session.commit()
    import pdb;pdb.set_trace()

    return


if __name__ == '__main__':
    main()


"""
* Rest of the tables (rounds, ratings, etc.)
* Indexes
* db session management, engine creation, and schema creation separation
* prod db pw management
* add simple_serdes for E-Z APIs
"""
