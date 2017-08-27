# -*- coding: utf-8 -*-

# Relational database models for Montage
import time
import random
import string
import datetime
import itertools
from collections import Counter, defaultdict
from math import ceil
from json import dumps

from pyvotecore.schulze_npr import SchulzeNPR
from sqlalchemy import (Text,
                        Column,
                        String,
                        Integer,
                        Float,
                        Boolean,
                        DateTime,
                        TIMESTAMP,
                        ForeignKey,
                        inspect)
from sqlalchemy.sql import func, asc
from sqlalchemy.orm import relationship, joinedload
from sqlalchemy.sql.expression import select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy

from boltons.strutils import slugify
from boltons.iterutils import chunked, first, unique_iter, bucketize
from boltons.statsutils import mean

from clastic.errors import Forbidden

from utils import (format_date,
                   to_unicode,
                   json_serial,
                   get_mw_userid,
                   weighted_choice,
                   PermissionDenied, InvalidAction,
                   DoesNotExist)
from imgutils import make_mw_img_url
from loaders import get_entries_from_gist_csv, load_category
from simple_serdes import DictableBase, JSONEncodedDict

Base = declarative_base(cls=DictableBase)


ONE_MEGAPIXEL = 1e6
DEFAULT_MIN_RESOLUTION = 2 * ONE_MEGAPIXEL
IMPORT_CHUNK_SIZE = 200

DEFAULT_ALLOWED_FILETYPES = ['jpeg', 'png', 'gif']

# Some basic config settings
DEFAULT_ROUND_CONFIG = {'show_link': True,
                        'show_filename': True,
                        'show_resolution': True,
                        'dq_by_upload_date': True,
                        'dq_by_resolution': False,
                        'dq_by_uploader': False,
                        'dq_by_filetype': False,
                        'allowed_filetypes': DEFAULT_ALLOWED_FILETYPES,
                        'min_resolution': DEFAULT_MIN_RESOLUTION,
                        'dq_coords': True,
                        'dq_organizers': True,
                        'dq_maintainers': True}

# Status
ACTIVE_STATUS = 'active'
PAUSED_STATUS = 'paused'
CANCELLED_STATUS = 'cancelled'
FINALIZED_STATUS = 'finalized'
COMPLETED_STATUS = 'completed'

"""
Column ordering and groupings:
* ID
* Data
* Metadata (creation date)
* 1-n relationships
* n-n relationships
"""

"""
# Note on "flags"

The "flags" column, when present, is a string
column with serialized JSON data, used for incidental data that isn't
represented in columns (and thus can't be indexed/queried
directly). The hope is that this saves us a migration or two down the
line.

Also note that unless there is an __init__ that populates the field
with a dict, brand new flags-having objects will have None for the
flags attribute.
"""

MAINTAINERS = ['MahmoudHashemi', 'Slaporte', 'Yarl', 'LilyOfTheWest']


"""
class RDBSession(sessionmaker()):
    def __init__(self, *a, **kw):
        super(RDBSession, self).__init__(*a, **kw)
        self.dao_list = []
"""


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    username = Column(String(255))
    is_organizer = Column(Boolean, default=False)
    last_active_date = Column(DateTime)

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    created_by = Column(Integer, ForeignKey('users.id'))
    coordinated_campaigns = relationship('CampaignCoord', back_populates='user')
    campaigns = association_proxy('coordinated_campaigns', 'campaign',
                                  creator=lambda c: CampaignCoord(campaign=c))

    jurored_rounds = relationship('RoundJuror', back_populates='user')
    rounds = association_proxy('jurored_rounds', 'round',
                               creator=lambda r: RoundJuror(round=r))

    ratings = relationship('Vote', back_populates='user')
    # update_date?

    def __init__(self, **kw):
        self.flags = kw.pop('flags', {})
        super(User, self).__init__(**kw)

    @property
    def is_maintainer(self):
        return self.username in MAINTAINERS

    def to_info_dict(self):
        ret = {'id': self.id,
               'username': self.username,
               'is_organizer': self.is_organizer,
               'is_maintainer': self.is_maintainer}
        return ret

    def to_details_dict(self):
        ret = self.to_info_dict()
        ret['last_active_date'] = self.last_active_date
        ret['created_by'] = self.created_by
        return ret


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))

    # open/close can be used to select/verify that images were
    # actually uploaded during the contest window
    open_date = Column(DateTime)
    close_date = Column(DateTime)
    status = Column(String(255))  # active, cancelled, finalized

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    rounds = relationship('Round', back_populates='campaign')
    campaign_coords = relationship('CampaignCoord',
                                   cascade="save-update, merge, delete, delete-orphan")
    coords = association_proxy('campaign_coords', 'user',
                               creator=lambda user: CampaignCoord(coord=user))

    @property
    def active_round(self):
        return first([r for r in self.rounds
                      if r.status in (ACTIVE_STATUS, PAUSED_STATUS)], None)

    def to_info_dict(self):
        ret = {'id': self.id,
               'name': self.name,
               'url_name': slugify(self.name, '-'),
               'open_date': format_date(self.open_date),
               'close_date': format_date(self.close_date)}
        return ret

    def to_details_dict(self, admin=None):  # TODO: with_admin?
        ret = self.to_info_dict()
        ret['rounds'] = [rnd.to_info_dict() for rnd in self.rounds]
        # should this exclude cancelled rounds?
        ret['coordinators'] = [user.to_info_dict() for user in self.coords]
        active_rnd = self.active_round
        ret['active_round'] = active_rnd.to_info_dict() if active_rnd else None
        return ret

campaigns_t = Campaign.__table__


class CampaignCoord(Base):  # Coordinator, not Coordinate
    __tablename__ = 'campaign_coords'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), primary_key=True)

    user = relationship('User', back_populates='coordinated_campaigns')
    campaign = relationship('Campaign', back_populates='campaign_coords')

    def __init__(self, campaign=None, coord=None):
        if campaign is not None:
            self.campaign = campaign
        self.user = coord


class Round(Base):
    """The "directions" field is for coordinators to communicate
    localized directions to jurors, whereas the "description" field is
    for coordinator comments (and not shown to jurors).
    """
    __tablename__ = 'rounds'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    description = Column(Text)
    directions = Column(Text)
    open_date = Column(DateTime)
    close_date = Column(DateTime)
    status = Column(String(255))  # active, paused, cancelled finalized
    vote_method = Column(String(255))
    quorum = Column(Integer)

    config = Column(JSONEncodedDict, default=DEFAULT_ROUND_CONFIG)
    deadline_date = Column(TIMESTAMP)

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    campaign_seq = Column(Integer)

    campaign = relationship('Campaign', back_populates='rounds')

    round_jurors = relationship('RoundJuror')
    jurors = association_proxy('round_jurors', 'user',
                               creator=lambda u: RoundJuror(user=u))

    round_entries = relationship('RoundEntry')
    entries = association_proxy('round_entries', 'entry',
                                creator=lambda e: RoundEntry(entry=e))

    def get_count_map(self):
        # TODO TODO TODO
        # when more info is needed, can get session with
        # inspect(self).session (might be None if not attached), only
        # disadvantage is that user is not available to do permissions
        # checking.
        rdb_session = inspect(self).session
        if not rdb_session:
            # TODO: just make a session
            raise RuntimeError('cannot get counts for detached Round')
        re_count = len(self.round_entries)
        task_count = rdb_session.query(Vote)\
                                .filter(Vote.round_entry.has(round_id=self.id),
                                        Vote.status != CANCELLED_STATUS)\
                                .count()
        open_task_count = rdb_session.query(Vote)\
                                     .filter(Vote.round_entry.has(round_id=self.id),
                                             Vote.status == ACTIVE_STATUS)\
                                     .count()
        cancelled_task_count = rdb_session.query(Vote)\
                                     .filter(Vote.round_entry.has(round_id=self.id),
                                             Vote.status == CANCELLED_STATUS)\
                                     .count()
        dq_entry_count = rdb_session.query(RoundEntry)\
                                    .filter_by(round_id=self.id)\
                                    .filter(RoundEntry.dq_reason != None)\
                                    .count()
        if task_count:
            percent_open = round((100.0 * open_task_count) / task_count, 3)
        else:
            percent_open = 0.0

        return {'total_round_entries': re_count,
                'total_tasks': task_count,
                'total_open_tasks': open_task_count,
                'percent_tasks_open': percent_open,
                'total_cancelled_tasks': cancelled_task_count,
                'total_disqualified_entries': dq_entry_count,
                'total_uploaders': len(self.get_uploaders())}

    def get_uploaders(self):
        # TODO: order by and maybe include count per?
        rdb_session = inspect(self).session
        query = (rdb_session
                 .query(Entry.upload_user_text)
                 .group_by(Entry.upload_user_id)
                 .join(RoundEntry)
                 .filter(RoundEntry.round == self,
                         RoundEntry.dq_user_id == None))
        return [x[0] for x in query.all()]

    def is_closeable(self):
        rdb_session = inspect(self).session

        if not rdb_session:
            # TODO: see above
            raise RuntimeError('cannot get counts for detached Round')
        '''
        open_tasks = rdb_session.query(Task)\
                                .filter(Task.round_entry.has(round_id=self.id),
                                        Task.complete_date == None,
                                        Task.cancel_date == None)\
                                .count()
        '''
        if self.entries and self.status == ACTIVE_STATUS or self.status == PAUSED_STATUS:
            active_votes = rdb_session.query(Vote)\
                                    .options(joinedload('round_entry'))\
                                    .filter(Vote.round_entry.has(round_id=self.id),
                                            Vote.status == ACTIVE_STATUS)\
                                    .first()
            return not active_votes
        return False


    def to_info_dict(self):
        ret = {'id': self.id,
               'name': self.name,
               'directions': self.directions,
               'canonical_url_name': slugify(self.name, '-'),
               'vote_method': self.vote_method,
               'open_date': format_date(self.open_date),
               'close_date': format_date(self.close_date),
               'deadline_date': format_date(self.deadline_date),
               'jurors': [rj.to_info_dict() for rj in self.round_jurors],
               'status': self.status,
               'config': self.config}
        return ret

    def to_details_dict(self):
        ret = self.to_info_dict()
        ret['quorum'] = self.quorum
        ret['total_round_entries'] = len(self.round_entries)
        ret['stats'] = self.get_count_map()
        ret['juror_details'] = [rj.to_details_dict() for rj in self.round_jurors],
        return ret

    def confirm_active(self):
        if self.status != ACTIVE_STATUS:
            raise InvalidAction('round %s is not active' % self.id)
        return True

rounds_t = Round.__table__


class RoundJuror(Base):
    __tablename__ = 'round_jurors'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), primary_key=True)
    is_active = Column(Boolean, default=True)
    flags = Column(JSONEncodedDict)

    user = relationship('User', back_populates='jurored_rounds')
    round = relationship('Round', back_populates='round_jurors')

    def __init__(self, round=None, user=None):
        if round is not None:
            # lesson: setting round to None would give an error about
            # trying to "blank-out primary key column"
            self.round = round
        if user is not None:
            self.user = user

    def get_count_map(self):
        rdb_session = inspect(self).session
        if not rdb_session:
            # TODO: just make a session
            raise RuntimeError('cannot get counts for detached Round')
        task_count = rdb_session.query(Vote)\
                                .filter(Vote.round_entry.has(round_id=self.round_id),
                                        Vote.status != CANCELLED_STATUS)\
                                .count()
        open_task_count = rdb_session.query(Vote)\
                                     .filter(Vote.round_entry.has(round_id=self.round_id),
                                             Vote.user_id == self.user_id,
                                             Vote.status == ACTIVE_STATUS)\
                                     .count()
        cancelled_task_count = rdb_session.query(Vote)\
                                     .filter(Vote.round_entry.has(round_id=self.round_id),
                                             Vote.user_id == self.user_id,
                                             Vote.status == CANCELLED_STATUS)\
                                     .count()
        if task_count:
            percent_open = round((100.0 * open_task_count) / task_count, 3)
        else:
            percent_open = 0.0

        return {'total_tasks': task_count,
                'total_open_tasks': open_task_count,
                'percent_tasks_open': percent_open,
                'total_cancelled_tasks': cancelled_task_count}

    def to_info_dict(self):
        ret = {'id': self.user.id,
               'username': self.user.username,
               'is_active': self.is_active}
        if self.flags:
            ret['flags'] = self.flags
        return ret

    def to_details_dict(self):
        ret = self.to_info_dict()
        ret['stats'] = self.get_count_map()
        return ret


round_jurors_t = RoundJuror.__table__


class Entry(Base):
    # if this is being kept generic for other types of media judging,
    # then I think a "duration" attribute makes sense -mh
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True)

    # page_id?
    name = Column(String(255), index=True, unique=True)
    mime_major = Column(String(255))
    mime_minor = Column(String(255))
    width = Column(Integer)
    height = Column(Integer)
    resolution = Column(Integer)
    # if we ever figure out how to get the monument ID
    subject_id = Column(String(255))
    upload_user_id = Column(Integer)
    upload_user_text = Column(String(255))
    upload_date = Column(DateTime)

    # TODO: img_sha1/page_touched for updates?
    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    entered_rounds = relationship('RoundEntry')
    rounds = association_proxy('entered_rounds', 'round',
                               creator=lambda r: RoundEntry(round=r))

    def to_info_dict(self):
        return {'id': self.id}

    def to_details_dict(self, **kw):
        with_uploader = kw.pop('with_uploader', None)
        ret = self.to_info_dict()
        ret.update({'upload_date': format_date(self.upload_date),
                    'mime_major': self.mime_major,
                    'mime_minor': self.mime_minor,
                    'name': self.name,
                    'height': self.height,
                    'width': self.width,
                    'url': make_mw_img_url(self.name),
                    'url_sm': make_mw_img_url(self.name, size='small'),
                    'url_med': make_mw_img_url(self.name, size='medium'),
                    'resolution': self.resolution})
        if with_uploader:
            ret['upload_user_text'] = self.upload_user_text
        return ret


class RoundEntry(Base):
    __tablename__ = 'round_entries'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('entries.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))

    dq_user_id = Column(Integer, ForeignKey('users.id'))
    dq_reason = Column(String(255))  # in case it's disqualified
    # examples: too low resolution, out of date range
    # TODO: dq_date?
    flags = Column(JSONEncodedDict)

    entry = relationship(Entry, back_populates='entered_rounds')
    round = relationship(Round, back_populates='round_entries')
    vote = relationship('Vote', back_populates='round_entry')

    def __init__(self, entry=None, round=None):
        if entry is not None:
            self.entry = entry
        if round is not None:
            self.round = round
        return

    def to_dq_details(self):
        ret = {'entry': self.entry.to_details_dict(),
               'dq_reason': self.dq_reason,
               'dq_user_id': self.dq_user_id}
        return ret


round_entries_t = RoundEntry.__table__


class RoundSource(Base):
    __tablename__ = 'round_sources'

    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    method = Column(String(255))
    params = Column(JSONEncodedDict)
    dq_params = Column(JSONEncodedDict)

    create_date = Column(TIMESTAMP, server_default=func.now())
    user = relationship('User')

    flags = Column(JSONEncodedDict)


class Flag(Base):
    __tablename__ = 'flags'

    id = Column(Integer, primary_key=True)
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    reason = Column(Text)

    create_date = Column(TIMESTAMP, server_default=func.now())
    user = relationship('User')

    flags = Column(JSONEncodedDict)


class Favorite(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('entries.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    status = Column(String(255))  # active, cancelled

    user = relationship('User')
    campaign = relationship('Campaign')

    create_date = Column(TIMESTAMP, server_default=func.now())
    modified_date = Column(DateTime)

    flags = Column(JSONEncodedDict)


class Vote(Base):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    value = Column(Float)
    status = Column(String(255))  # active, cancelled, complete

    user = relationship('User', back_populates='ratings')
    round_entry = relationship('RoundEntry', back_populates='vote')

    entry = association_proxy('round_entry', 'entry',
                              creator=lambda e: RoundEntry(entry=e))

    create_date = Column(TIMESTAMP, server_default=func.now())
    modified_date = Column(DateTime)

    flags = Column(JSONEncodedDict)

    def __init__(self, **kw):
        self.flags = kw.pop('flags', {})
        super(Vote, self).__init__(**kw)

    @property
    def ranking_value(self):
        return int(self.value)

    def to_info_dict(self):
        info = {'id': self.id,
                'name': self.entry.name,
                'user': self.user.username,
                'value': self.value,
                'round_id': self.round_entry.round_id}
        info['review'] = self.flags.get('review')  # TODO
        return info

    def to_details_dict(self):
        ret = self.to_info_dict()
        ret['entry'] = self.entry.to_details_dict()
        return ret


votes_t = Vote.__table__


class FinalEntryRanking(object):
    """This is just for organizing ranking information as calculated at
    the end of a ranking round.
    """
    def __init__(self, rank, entry, ranking_map, juror_review_map):
        self.rank = rank
        self.entry = entry
        self.ranking_map = ranking_map

        self.juror_ranking_map = {}

        for rank, jurors in ranking_map.items():
            for juror in jurors:
                self.juror_ranking_map[juror] = rank

        self.juror_review_map = juror_review_map

    def to_dict(self):
        return {'ranking': self.rank,
                'entry': self.entry.to_dict(),
                'ranking_map': self.ranking_map,
                'juror_review_map': self.juror_review_map,
                'juror_ranking_map': self.juror_ranking_map}

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s #%r %r>' % (cn, self.rank, self.entry)


class RoundResultsSummary(Base):
    """# Results modeling

    This is more like a persistent cache. Results could be recomputed from
    the ratings/rankings.

    ## Round results

    All have:

    * Total number in/out
    * Time created/closed
    * Created/closed by

    Style-specific:

    * Rating-based
        * Winning images (up to 50, sampled?)
        * Parameters (scale, threshold)
    * Ranking-based
        * ?

    """
    __tablename__ = 'results_summaries'

    id = Column(Integer, primary_key=True)

    round_id = Column(Integer, ForeignKey('rounds.id'))
    round = relationship('Round')
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    campaign = relationship('Campaign')

    summary = Column(JSONEncodedDict)
    status = Column(String(255))  # private, public
    language = Column(String(255))

    version = Column(String(255))

    create_date = Column(TIMESTAMP, server_default=func.now())
    modified_date = Column(DateTime)

'''
class CampaignResults(Base):
    """
    (Same as last round results?)

    On the frontend I'd like to see:

    * Ranked winners
    * Total number of entries
    * Total number of votes
    * Summary of each round (with jurors)
    * Organizers and coordinators
    * Dates

    """
    __tablename__ = 'campaign_results'

    id = Column(Integer, primary_key=True)

    campaign_id = Column(Integer, ForeignKey('campaign.id'))

    summary = Column(JSONEncodedDict)

    create_date = Column(TIMESTAMP, server_default=func.now())
'''


class AuditLogEntry(Base):
    __tablename__ = 'audit_log_entries'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'))
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    role = Column(String(255))
    action = Column(String(255))
    message = Column(Text)

    flags = Column(JSONEncodedDict)

    create_date = Column(TIMESTAMP, server_default=func.now())

    def to_info_dict(self):
        ret = {'id': self.id,
               'user_id': self.user_id,
               'campaign_id': self.campaign_id,
               'round_id': self.round_id,
               'round_entry_id': self.round_entry_id,
               'role': self.role,
               'action': self.action,
               'message': self.message,
               'create_date': format_date(self.create_date)}
        return ret


class UserDAO(object):
    """The Data Acccess Object wraps the rdb_session and active user
    model, providing a layer for model manipulation through
    expressively-named methods.

    As the DAO expands, it will likely break up into multiple DAOs for
    different areas of the schema.

    # TODO: will blow up a bit if user is None
    """
    def __init__(self, rdb_session, user):
        self.rdb_session = rdb_session
        self.user = user

    @property
    def role(self):
        cn_role = self.__class__.__name__.replace('DAO', '').lower()
        # allow overriding with _role attribute
        return getattr(self, '_role', cn_role)

    def query(self, *a, **kw):
        "a call-through to the underlying session.query"
        return self.rdb_session.query(*a, **kw)

    def get_campaign(self, campaign_id):
        campaign = self.query(Campaign)\
                       .filter(
                           Campaign.coords.any(username=self.user.username))\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        if not campaign:
            raise Forbidden('not a coordinator on campaign %s' % campaign_id)
        return campaign

    def get_all_campaigns(self):
        campaigns = self.query(Campaign)\
                        .filter(
                            Campaign.coords.any(username=self.user.username))\
                        .all()
        if len(campaigns) == 0:
            raise Forbidden('not a coordinator on any campaigns')
        return campaigns

    def get_round(self, round_id):
        rnd = self.query(Round)\
                  .filter(
                      Round.campaign.has(
                          Campaign.coords.any(username=self.user.username)))\
                  .filter_by(id=round_id)\
                  .one_or_none()
        if not rnd:
            raise Forbidden('not a coordinator for round %s' % round_id)
        return rnd

    def get_or_create_user(self, user, role, **kw):
        # kw is for including round/round_id/campaign/campaign_id
        # which is used in the audit log if the user is created
        if isinstance(user, User):
            return user
        elif not isinstance(user, basestring):
            raise TypeError('expected user or username, not %r' % user)
        username = user
        user = lookup_user(self.rdb_session, username=username)

        if not user:
            creator = self.user
            user_id = get_mw_userid(username)
            user = User(id=user_id,
                        username=username,
                        created_by=creator.id if creator else None)
            self.rdb_session.add(user)
            msg = ('%s created user %s while adding them as a %s'
                   % (creator.username if creator else '', username, role))
            self.log_action('create_user', message=msg, **kw)

        return user

    def log_action(self, action, **kw):
        # TODO: file logging here too
        user_id = self.user.id if self.user else None
        round_entry = kw.pop('round_entry', None)
        round_entry_id = kw.pop('round_entry_id',
                                round_entry.id if round_entry else None)

        rnd = kw.pop('round', None)
        round_id = kw.pop('round_id', rnd.id if rnd else None)

        if not round_id and round_entry_id:
            rnd = self.query(RoundEntry).get(round_entry_id).round
            round_id = rnd.id

        campaign = kw.pop('campaign', None)
        campaign_id = kw.pop('campaign_id', campaign.id if campaign else None)

        if round_id and not campaign_id:
            campaign = self.query(Round).get(round_id).campaign
            campaign_id = campaign.id

        cn_role = self.__class__.__name__.replace('DAO', '').lower()
        role = kw.pop('role', cn_role)

        message = kw.pop('message', None)
        flags = dict(kw.pop('flags', {}))

        ale = AuditLogEntry(user_id=user_id,
                            campaign_id=campaign_id,
                            round_id=round_id,
                            round_entry_id=round_entry_id,
                            role=role,
                            action=action,
                            message=message,
                            flags=flags)

        self.rdb_session.add(ale)
        return


class CoordinatorDAO(UserDAO):
    """A Data Access Object for the Coordinator's view"""

    # Some restrictions on editing round properties:
    # (these restrictions are enforced in the endpoint funcs)
    #
    #   - no reassignment required: name, description, directions,
    #     display_settings
    #   - reassignment required: quorum, active_jurors
    #   - not updateable: id, open_date, close_date, vote_method,
    #     campaign_id/seq

    def __init__(self, user_dao, campaign):
        if not type(campaign) is Campaign:
            InvalidAction('cannot load campaign')
        self.query = user_dao.query
        self.rdb_session = user_dao.rdb_session
        self.user_dao = user_dao
        self.user = user_dao.user
        self.get_or_create_user = user_dao.get_or_create_user
        self.campaign = campaign
        self.get_campaign = user_dao.get_campaign

    @classmethod
    def from_campaign(cls, user_dao, campaign_id):
        campaign = user_dao.get_campaign(campaign_id)
        return cls(user_dao, campaign)

    @classmethod
    def from_round(cls, user_dao, round_id):
        rnd = user_dao.get_round(round_id)
        campaign = rnd.campaign
        return cls(user_dao, campaign)

    # Read methods

    def get_campaign_rounds(self, campaign, with_cancelled=False):
        q = self.query(Round).filter_by(campaign=campaign)
        if not with_cancelled:
            q.filter(Round.status != CANCELLED_STATUS)
        q.order_by(Round.create_date)
        return q.all()

    def get_active_jurors(self, round_id):
        rjs = (self.query(RoundJuror)
               .filter_by(is_active=True,
                          round_id=round_id)
               .options(joinedload('user'))
               .all())
        users = [rj.user for rj in rjs]
        return users

    def get_round_task_counts(self, round_id):
        # the fact that these are identical for two DAOs shows it
        # should be on the Round model or somewhere else shared
        re_count = self.query(RoundEntry).filter_by(round_id=round_id).count()
        total_tasks = self.query(Vote)\
                          .filter(Vote.round_entry.has(round_id=round_id),
                                  Vote.user_id == self.user.id,
                                  Vote.status != CANCELLED_STATUS)\
                          .count()
        total_open_tasks = self.query(Vote)\
                               .filter(Vote.round_entry.has(round_id=round_id),
                                       Vote.user_id == self.user.id,
                                       Vote.status == ACTIVE_STATUS)\
                               .count()

        if total_tasks:
            percent_open = round((100.0 * total_open_tasks) / total_tasks, 3)
        else:
            percent_open = 0.0
        return {'total_round_entries': re_count,
                'total_tasks': total_tasks,
                'total_open_tasks': total_open_tasks,
                'percent_tasks_open': percent_open}

    def get_entry_name_map(self, filenames):
        entries = self.query(Entry)\
                      .filter(Entry.name.in_(filenames))\
                      .all()
        ret = {}
        for entry in entries:
            name = entry.name
            ret[name] = entry
        return ret

    # write methods
    def edit_campaign(self, campaign_dict):
        ret = self.query(Campaign)\
                  .filter_by(id=self.campaign.id)\
                  .update(campaign_dict)
        msg = ('%s edited these columns in campaign "%s" (#%s): %r'
               % (self.user.username, self.campaign.name, self.campaign.id,
                  campaign_dict.keys()))
        self.log_action('edit_campaign', campaign=self.campaign, message=msg)
        return ret

    def create_round(self, name, description, directions, quorum,
                     vote_method, jurors, deadline_date, config=None):
        if self.campaign.active_round:
            raise InvalidAction('can only create one active/paused round at a'
                                ' time. cancel or complete your existing'
                                ' rounds before trying again')
        config = config or {}
        jurors = [self.get_or_create_user(j, 'juror', campaign=self.campaign)
                  for j in jurors]

        for (k, v) in DEFAULT_ROUND_CONFIG.items():
            config[k] = config.get(k, v)

        full_config = dict(DEFAULT_ROUND_CONFIG)
        full_config.update(config)

        rnd = Round(name=name,
                    description=description,
                    directions=directions,
                    campaign=self.campaign,
                    campaign_seq=len(self.campaign.rounds),
                    status=PAUSED_STATUS,
                    quorum=quorum,
                    deadline_date=deadline_date,
                    vote_method=vote_method,
                    jurors=jurors,
                    config=full_config)

        self.rdb_session.add(rnd)

        j_names = [j.username for j in jurors]
        msg = ('%s created %s round "%s" (#%s) with jurors %r for'
               ' campaign "%s"' % (self.user.username, vote_method,
                                   rnd.name, rnd.id, j_names, self.campaign.name))
        self.log_action('create_round', round=rnd, message=msg)
        self.rdb_session.commit()
        return rnd

    def edit_round(self, round_id, round_dict):
        editable_columns = ['name', 'description', 'directions',
                            'config', 'new_jurors', 'deadline_date',
                            'quorum']
        rnd = self.get_round(round_id)
        # Use specific methods to edit other columns:
        #  - status: activate_round, pause_round
        #  - quorum: [requires reallocation]
        #  - active_jurors: [requires reallocation]
        must_be_paused = ['quorum', 'new_jurors']
        new_val_map = {}
        for column_name in editable_columns:
            # val = request_dict.pop(column_name, None)  # see note below
            val = round_dict.get(column_name)
            if val is not None and column_name not in must_be_paused:
                if column_name == 'deadline_date':
                    val = js_isoparse(val)
                setattr(rnd, column_name, val)
                new_val_map[column_name] = val
        # can't do this yet because stuff like su_to is hanging out in there.
        # if round_dict ...:
        #     raise InvalidAction('unable to modify round attributes: %r'
        #                         % request_dict.keys())
        new_juror_names = round_dict.get('new_jurors')
        cur_jurors = self.get_active_jurors(round_id)
        cur_juror_names = [u.username for u in cur_jurors]
        if new_juror_names and set(new_juror_names) != set(cur_juror_names):
            if rnd.status != PAUSED_STATUS:
                raise InvalidAction('round must be paused to edit jurors')
            else:
                new_juror_stats = self.modify_jurors(round_id, new_juror_names)
                new_val_map['new_jurors'] = new_juror_names
        new_quorum = round_dict.get('quorum')
        if new_quorum and new_quorum != rnd.quorum:
            if rnd.status != PAUSED_STATUS:
                raise InvalidAction('round must be paused to edit quorum')
            else:
                new_juror_stats = self.modify_quorum(round_id, new_quorum)
                new_val_map['quorum'] = new_quorum
        msg = ('%s edited these columns in round "%s" (#%s): %r'
               % (self.user.username, rnd.name, rnd.id, new_val_map.keys()))
        self.log_action('edit_round', round=rnd, message=msg)
        return new_val_map

    def autodisqualify_by_date(self, round_id, preview=False):
        rnd = self.get_round(round_id)
        min_date = self.campaign.open_date
        max_date = self.campaign.close_date

        if (not min_date or not max_date):
            round_entries = []

            if not preview:
                msg = ('%s disqualified 0 entries by date due to missing, '
                       'campaign open or close date' % (self.user.username,))
                self.log_action('autodisqualify_by_date', round=rnd, message=msg)

            return round_entries

        round_entries = self.query(RoundEntry)\
                            .join(Entry)\
                            .filter(RoundEntry.round_id == round_id)\
                            .filter((Entry.upload_date < min_date) |
                                    (Entry.upload_date > max_date))\
                            .all()

        if preview:
            return round_entries

        cancel_date = datetime.datetime.utcnow()

        for round_entry in round_entries:
            dq_reason = ('upload date %s is out of campaign date range %s - %s'
                         % (round_entry.entry.upload_date, min_date, max_date))
            round_entry.dq_reason = dq_reason
            round_entry.dq_user_id = self.user.id

            for vote in round_entry.votes:
                vote.status = CANCELLED_STATUS
                vote.modified_date = datetime.datetime.utcnow()

        msg = ('%s disqualified %s entries outside of date range %s - %s'
               % (self.user.username, len(round_entries), min_date, max_date))
        self.log_action('autodisqualify_by_date', round=rnd, message=msg)

        return round_entries

    def autodisqualify_by_resolution(self, round_id, preview=False):
        # TODO: get from config
        rnd = self.get_round(round_id)
        min_res = rnd.config.get('min_resolution', DEFAULT_MIN_RESOLUTION)
        round_entries = self.query(RoundEntry)\
                            .join(Entry)\
                            .filter(RoundEntry.round_id == round_id)\
                            .filter(Entry.resolution < min_res)\
                            .all()

        if preview:
            return round_entries

        min_res_str = round(min_res / ONE_MEGAPIXEL, 2)
        cancel_date = datetime.datetime.utcnow()

        for r_ent in round_entries:
            entry_res_str = round(r_ent.entry.resolution / ONE_MEGAPIXEL, 2)
            dq_reason = ('resolution %s is less than %s minimum '
                         % (entry_res_str, min_res_str))
            r_ent.dq_reason = dq_reason
            r_ent.dq_user_id = self.user.id

            for vote in r_ent.vote:
                vote.status = CANCELLED_STATUS
                vote.modified_date = datetime.datetime.utcnow()

        msg = ('%s disqualified %s entries smaller than %s megapixels'
               % (self.user.username, len(round_entries), min_res_str))
        self.log_action('autodisqualify_by_resolution', round=rnd, message=msg)

        return round_entries

    def autodisqualify_by_filetype(self, round_id, preview=False):
        rnd = self.get_round(round_id)
        allowed_filetypes = rnd.config.get('allowed_filetypes')
        round_entries = self.query(RoundEntry)\
                            .join(Entry)\
                            .filter(RoundEntry.round_id == round_id)\
                            .filter(~Entry.mime_minor.in_(allowed_filetypes))\
                            .all()

        if preview:
            return round_entries

        cancel_date = datetime.datetime.utcnow()

        for r_ent in round_entries:
            dq_reason = ('mime %s is not in %s' % (r_ent.entry.mime_minor,
                                                   allowed_filetypes))
            r_ent.dq_reason = dq_reason
            r_ent.dq_user_id = self.user.id

            for vote in r_ent.vote:
                vote.status = CANCELLED_STATUS
                vote.modified_date = datetime.datetime.utcnow()

        msg = ('%s disqualified %s entries by filetype not in %s'
               % (self.user.username, len(round_entries), allowed_filetypes))
        self.log_action('autodisqualify_by_filetype', round=rnd, message=msg)
        return round_entries

    def autodisqualify_by_uploader(self, round_id, preview=False):
        dq_group = {}
        rnd = self.get_round(round_id)
        dq_usernames = [j.username for j in rnd.jurors]

        for username in dq_usernames:
            dq_group[username] = 'juror'

        if rnd.config.get('dq_coords'):
            coord_usernames = [c.username for c in self.campaign.coords]
            dq_usernames += coord_usernames
            for username in coord_usernames:
                dq_group[username] = 'coordinator'

        if rnd.config.get('dq_organizers'):
            organizers = self.query(User)\
                             .filter_by(is_organizer=True)\
                             .all()
            organizer_usernames = [u.username for u in organizers]
            dq_usernames += organizer_usernames
            for username in organizer_usernames:
                dq_group[username] = 'organizer'

        if rnd.config.get('dq_maintainers'):
            dq_usernames += MAINTAINERS
            for username in MAINTAINERS:
                dq_group[username] = 'maintainer'

        dq_usernames = set(dq_usernames)

        round_entries = self.query(RoundEntry)\
                            .join(Entry)\
                            .filter(RoundEntry.round_id == round_id)\
                            .filter(Entry.upload_user_text.in_(dq_usernames))\
                            .all()

        if preview:
            return round_entries

        cancel_date = datetime.datetime.utcnow()

        for round_entry in round_entries:
            upload_user = round_entry.entry.upload_user_text
            dq_reason = 'upload user %s is %s'\
                        % (upload_user, dq_group[upload_user])
            round_entry.dq_reason = dq_reason
            round_entry.dq_user_id = self.user.id

            for vote in round_entry.votes:
                vote.status = CANCELLED_STATUS
                vote.modified_date = datetime.datetime.utcnow()

        msg = ('%s disqualified %s entries based on upload user'
               % (self.user.username, len(round_entries)))
        self.log_action('autodisqualify_by_uploader', round=rnd, message=msg)

        return round_entries

    def pause_round(self, round_id):
        rnd = self.user_dao.get_round(round_id)
        rnd.status = PAUSED_STATUS
        msg = '%s paused round "%s"' % (self.user.username, rnd.name)
        self.log_action('pause_round', round=rnd, message=msg)

        return rnd

    def activate_round(self, round_id):
        rnd = self.user_dao.get_round(round_id)
        if not rnd.entries:
            raise InvalidAction('can not activate empty round, try importing'
                                ' entries first')

        if rnd.status != PAUSED_STATUS:
            raise InvalidAction('can only activate round in a paused state,'
                                ' not %r' % (rnd.status,))

        tasks = create_initial_tasks(self.rdb_session, rnd)
        rnd.open_date = datetime.datetime.utcnow()

        msg = ('%s opened round %s with %s tasks'
               % (self.user.username, rnd.name, len(tasks)))
        self.log_action('open_round', round=rnd, message=msg)

        rnd.status = ACTIVE_STATUS

        msg = '%s activated round "%s"' % (self.user.username, rnd.name)
        self.log_action('activate_round', round=rnd, message=msg)

        return

    def add_entries_from_cat(self, round_id, cat_name):
        rnd = self.user_dao.get_round(round_id)
        entries = load_category(cat_name)
        params = {'category': cat_name}
        entries, new_entry_count = self.add_entries(rnd, entries)

        msg = ('%s loaded %s entries from category (%s), %s new entries added'
               % (self.user.username, len(entries), cat_name, new_entry_count))
        self.log_action('add_entries', message=msg, round=rnd)

        return entries

    def add_entries_from_csv_gist(self, round_id, gist_url):
        # NOTE: this no longer creates RoundEntries, use
        # add_round_entries to do this.
        rnd = self.user_dao.get_round(round_id)
        entries = get_entries_from_gist_csv(gist_url)
        entries, new_entry_count = self.add_entries(rnd, entries)

        msg = ('%s loaded %s entries from csv gist (%r), %s new entries added'
               % (self.user.username, len(entries), gist_url, new_entry_count))
        self.log_action('add_entries', message=msg, round=rnd)

        return entries

    def add_round_source(self, round_id, import_method, params, dq_params=None):
        round_source = RoundSource(round_id=round_id,
                                   method=import_method,
                                   params=params,
                                   dq_params=dq_params,
                                   user=self.user)
        self.rdb_session.add(round_source)
        return round_source


    def add_entries(self, rnd, entries):
        # TODO: you shouldn't be able to use this method to add
        # entries to anything other than the first round in a campaign
        entry_chunks = chunked(entries, IMPORT_CHUNK_SIZE)
        ret = []
        new_entry_count = 0

        for entry_chunk in entry_chunks:
            entry_names = [to_unicode(e.name) for e in entry_chunk]
            db_entries = self.get_entry_name_map(entry_names)

            for entry in entry_chunk:
                db_entry = db_entries.get(to_unicode(entry.name))
                if db_entry:
                    entry = db_entry
                else:
                    new_entry_count += 1
                    self.rdb_session.add(entry)

                ret.append(entry)

        return ret, new_entry_count

    def add_round_entries(self, round_id, entries, source, params):
        rnd = self.user_dao.get_round(round_id)
        if rnd.status != PAUSED_STATUS:
            raise InvalidAction('round must be paused to add new entries')
        existing_names = set(self.rdb_session.query(Entry.name).
                             join(RoundEntry).
                             filter_by(round=rnd).
                             all())
        try:
            new_entries = [e for e
                           in unique_iter(entries, key=lambda e: e.name)
                           if e.name not in existing_names]
        except Exception as e:
            import pdb;pdb.set_trace()

        rnd.entries.extend(new_entries)
        self.add_round_source(round_id, source, params)
        msg = ('%s added %s round entries, %s new'
               % (self.user.username, len(entries), len(new_entries)))
        if source:
            msg += ' (from %s)' % (source,)
        self.log_action('add_round_entries', message=msg, round=rnd)
        return new_entries

    def cancel_round(self, round_id):
        rnd = self.get_round(round_id)
        votes = self.query(Vote)\
                    .filter(Vote.round_entry.has(round_id=round_id),
                            Vote.status == 'active')\
                    .all()
        cancel_date = datetime.datetime.utcnow()
        rnd.status = CANCELLED_STATUS
        rnd.close_date = cancel_date

        for vote in votes:
            vote.status = CANCELLED_STATUS
            vote.modified_date = datetime.datetime.utcnow()

        msg = '%s cancelled round "%s" and %s votes' %\
              (self.user.username, rnd.name, len(votes))
        self.log_action('cancel_round', round=rnd, message=msg)
        return rnd

    def make_vote_table(self, round_id):
        rnd = self.get_round(round_id)
        if rnd.vote_method == 'ranking':
            all_ratings = self.get_all_rankings(round_id)
        else:
            all_ratings = self.get_all_ratings(round_id)
        all_tasks = self.get_all_tasks(round_id)

        results_by_name = defaultdict(dict)
        ratings_dict = {r.task_id: r.value for r in all_ratings}

        for (task, entry) in all_tasks:
            rating = ratings_dict.get(task.id, {})
            filename = entry.name
            username = task.user.username

            if task.complete_date:
                results_by_name[filename][username] = rating
            else:
                # tbv = to be voted
                # there should be no empty tasks in a fully finalized round
                results_by_name[filename][username] = 'tbv'

        return results_by_name

    def finalize_rating_round(self, round_id, threshold):
        rnd = self.get_round(round_id)
        assert rnd.vote_method in ('rating', 'yesno')
        # TODO: assert all tasks complete

        rnd.close_date = datetime.datetime.utcnow()
        rnd.status = FINALIZED_STATUS
        rnd.config['final_threshold'] = threshold

        advance_group = self.get_rating_advancing_group(round_id, threshold)

        msg = ('%s finalized rating round "%s" at threshold %s,'
               ' with %s entries advancing'
               % (self.user.username, rnd.name, threshold, len(advance_group)))
        self.log_action('finalize_round', round=rnd, message=msg)
        return advance_group

    def finalize_ranking_round(self, round_id):
        rnd = self.get_round(round_id)
        assert rnd.vote_method == 'ranking'

        # TODO: Ranking method?

        rnd.close_date = datetime.datetime.utcnow()
        rnd.status = FINALIZED_STATUS
        # rnd.config['ranking_method'] = method

        summary = self.build_campaign_report(rnd.campaign)

        result_summary = RoundResultsSummary(round_id=round_id,
                                             campaign_id=rnd.campaign.id,
                                             summary=summary)
        self.rdb_session.add(result_summary)
        msg = ('%s finalized round "%s" (#%s) and created round results summary %s' %
               (self.user.username, rnd.name, rnd.id, result_summary.id))
        self.log_action('finalize_ranking_round', round=rnd, message=msg)
        return result_summary

    def finalize_campaign(self):
        last_rnd = self.campaign.rounds[-1]
        self.campaign.status = FINALIZED_STATUS
        #self.campaign.close_date = datetime.datetime.utcnow() # TODO
        msg = ('%s finalized campaign %r (#%s) with %s round "%s"'
               % (self.user.username, self.campaign.name, self.campaign.id,
                  last_rnd.vote_method, last_rnd.name))
        self.log_action('finalize_campaign', campaign=self.campaign, message=msg)
        return self.campaign

    def get_campaign_report(self):
        if self.campaign.status != FINALIZED_STATUS:
            raise Forbidden('cannot open report for campaign %s' % self.campaign.id)
        summary = self.query(RoundResultsSummary)\
                      .filter(
                          RoundResultsSummary.campaign.has(
                              Campaign.coords.any(username=self.user.username)))\
                      .filter_by(campaign_id=self.campaign.id)\
                      .one_or_none()
        return summary

    def get_rating_advancing_group(self, round_id, threshold=None):
        #assert rnd.vote_method in ('rating', 'yesno')

        if threshold is None:
            rnd = self.get_round(round_id)
            threshold = rnd.config.get('final_threshold')
        if threshold is None:
            raise ValueError('expected threshold or finalized round')

        assert 0.0 <= threshold <= 1.0

        avg = func.avg(Vote.value).label('average')

        results = self.query(RoundEntry, Vote, avg)\
                      .options(joinedload('entry'))\
                      .filter_by(dq_user_id=None, round_id=round_id)\
                      .join(Vote)\
                      .group_by(Vote.round_entry_id)\
                      .having(avg >= threshold)\
                      .all()

        entries = [res[0].entry for res in results]

        return entries

    def get_round_average_rating_map(self, round_id):
        results = self.query(Vote, func.avg(Vote.value).label('average'))\
                      .join(RoundEntry)\
                      .filter(Vote.round_entry.has(round_id=round_id),
                              Vote.status == COMPLETED_STATUS)\
                      .group_by(Vote.round_entry_id)\
                      .all()

        # thresh_counts = get_threshold_map(r[1] for r in ratings)
        rating_ctr = Counter([r[1] for r in results])

        return dict(rating_ctr)

    def get_round_ranking_list(self, round_id, notation=None):
        res = (self.query(Vote)
               .options(joinedload('round_entry'))
               .filter(Vote.round_entry.has(round_id=round_id),
                       Vote.status == COMPLETED_STATUS)
               .all())
        all_inputs = []
        by_juror_id = bucketize(res, lambda r: r.user_id)
        entry_user_review_map = {}

        for ranking in res:
            user_id = ranking.user_id
            entry_id = ranking.round_entry.entry_id
            review = ranking.flags.get('review', '')
            username = self.query(User).get(user_id).username

            entry_user_review_map.setdefault(entry_id, {})[username] = review

        entry_rank_user_map = {}
        for user_id, rankings in by_juror_id.items():
            cur_ballot = []
            cur_input = {'count': 1, 'ballot': cur_ballot}

            r_by_val = bucketize(rankings, lambda r: r.ranking_value)
            lowest_rank = max(r_by_val.keys())
            for rank in range(0, lowest_rank + 1):
                ranking_objs = r_by_val.get(rank, [])
                cur_ballot.append([r.round_entry.entry_id
                                   for r in ranking_objs])
                for r in ranking_objs:
                    (entry_rank_user_map.setdefault(r.round_entry.entry_id, {})
                     .setdefault(rank, [])
                     .append(self.query(User).get(user_id).username))

            all_inputs.append(cur_input)

        # If the following line errors, you have a the wrong version
        # of python-vote-core. make sure you have the github version
        # installed, referenced in the requirements.txt.
        # # pip install -r requirements.txt
        notation_style = SchulzeNPR.BALLOT_NOTATION_GROUPING  # see note above
        snpr = SchulzeNPR(all_inputs, ballot_notation=notation_style)

        snpr_res = snpr.as_dict()

        ret = []

        for i, entry_id in enumerate(snpr_res['order']):
            entry = self.query(Entry).get(entry_id)
            ranking_map = entry_rank_user_map[entry_id]
            review_map = entry_user_review_map[entry_id]
            fer = FinalEntryRanking(i, entry, ranking_map, review_map)
            ret.append(fer)
        return ret

    def get_all_ratings(self, rnd):
        results = self.query(Vote)\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(RoundEntry.round_id == rnd.id,
                              RoundEntry.dq_user_id == None,
                              Vote.status == COMPLETED_STATUS)\
                      .all()
        return results

    # do we need this?
    def get_all_rankings(self, rnd):
        results = self.query(Vote)\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(RoundEntry.round_id == rnd.id,
                              RoundEntry.dq_user_id == None,
                              Vote.status == COMPLETED_STATUS)\
                      .all()
        return results

    def get_all_tasks(self, rnd):
        results = self.query(Vote, Entry)\
                      .options(joinedload('user'))\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(RoundEntry.round_id == rnd.id,
                              RoundEntry.dq_user_id == None,
                              Vote.status == ACTIVE_STATUS)\
                      .all()
        return results

    def get_disqualified(self, round_id):
        results = self.query(RoundEntry)\
                      .options(joinedload('entry'))\
                      .filter_by(round_id=round_id)\
                      .filter(RoundEntry.dq_user_id != None)\
                      .all()

        return results

    def modify_jurors(self, round_id, new_jurors):
        # NOTE: this does not add or remove tasks. Contrast this with
        # changing the quorum, which would remove tasks, but carries the
        # issue of possibly having to reweight or discard completed ratings.

        # TODO: check to make sure only certain round actions can happen
        # when paused, others only when active, basically none when the
        # round is complete or cancelled.
        rnd = self.get_round(round_id)

        if not getattr(new_jurors, 'username', None):
            new_jurors = [self.get_or_create_user(j, 'juror', round=rnd)
                          for j in new_jurors]

        if not new_jurors:
            raise InvalidAction('round requires at least one juror, got %r'
                                % (new_jurors,))

        if rnd.vote_method == 'ranking':
            rnd.quorum = len(new_jurors)
        elif rnd.quorum > len(new_jurors):
            raise InvalidAction('expected at least %s jurors to make quorum'
                                ' (%s) for round #%s'
                                % (len(new_jurors), rnd.quorum, rnd.id))
        new_juror_names = sorted([nj.username for nj in new_jurors])
        old_jurors = self.get_active_jurors(rnd.id)
        old_juror_names = sorted([oj.username for oj in old_jurors])
        if new_juror_names == old_juror_names:
            raise InvalidAction('new jurors must differ from current jurors')

        res = reassign_tasks(self.rdb_session, rnd, new_jurors)

        for juror in new_jurors:
            if juror not in rnd.jurors:
                rnd.jurors.append(juror)

        for round_juror in rnd.round_jurors:
            if round_juror.user.username in new_juror_names:
                round_juror.is_active = 1
            else:
                round_juror.is_active = 0

        msg = ('%s changed round #%s jurors (%r -> %r), reassigned %s tasks'
               ' (average juror task queue now at %s)'
               % (self.user.username, rnd.id, old_juror_names, new_juror_names,
                  res['reassigned_task_count'], res['task_count_mean']))

        self.log_action('modify_jurors', round=rnd, message=msg)
        return res

    def modify_quorum(self, round_id, new_quorum, strategy=None):
        # This only supports increasing the quorum. Decreaseing the
        # quorum would require handling some completed tasks (eg,
        # whose vote do you discard? Randomly choose?)

        # TODO: Support decreasing the quorum.
        rnd = self.get_round(round_id)

        old_quorum = rnd.quorum

        if not new_quorum:
            raise InvalidAction('must specify new quorum')

        if new_quorum <= old_quorum:
            raise NotImplementedError('currently we do not support quorum '
                                      'decreases. current quorum is %r, got %r'
                                      % (old_quorum, new_quorum))

        jurors = self.get_active_jurors(rnd.id)
        session = self.rdb_session

        rnd.quorum = new_quorum

        if rnd.vote_method == 'ranking':
            raise InvalidAction('no quorum for a ranking round')
        elif rnd.vote_method in ('yesno', 'rating'):
            new_tpe = new_quorum - old_quorum
            # I'm pretty sure this will fairly distribute tasks
            created_tasks = create_initial_rating_tasks(session, rnd,
                                                        tasks_per_entry=new_tpe)
            ret = reassign_rating_tasks(session, rnd, jurors,
                                        strategy=strategy, reassign_all=True)
        else:
            raise ValueError('invalid vote method: %r' % rnd.vote_method)

        msg = ('%s changed round #%s quorum (%r -> %r), reassigned %s tasks'
               ' (average juror task queue is now at %s)'
               % (self.user.username, rnd.id, old_quorum, new_quorum,
                  ret['reassigned_task_count'], ret['task_count_mean']))

        self.log_action('modify_quorum', round=rnd, message=msg)
        return ret

    def create_ranking_tasks(self, rnd, round_entries):
        jurors = rnd.jurors
        ret = []
        for juror in jurors:
            ret.extend([Vote(user=juror, round_entry=re, status=ACTIVE_STATUS)
                        for re in round_entries])
        return ret

    def create_ranking_round(self, campaign, name, jurors, deadline_date):
        # TODO: there might be some cases where they want to jump straight to the final round?
        # TODO: directions, other round params?
        assert campaign.active_round is None
        final_rnds = [r for r in campaign.rounds if r.status == FINALIZED_STATUS]
        prev_finalized_rnd = final_rnds[-1]  # TODO: these are ordered by date?
        assert prev_finalized_rnd.vote_method != 'ranking'

        advancing_group = self.get_rating_advancing_group(prev_finalized_rnd.id)

        assert 1 < len(advancing_group) <= 40  # TODO: configurable max

        rnd = self.create_round(name=name,
                                jurors=jurors,
                                quorum=len(jurors),
                                vote_method='ranking',
                                deadline_date=deadline_date)
        source = 'round(#%s)' % prev_finalized_rnd.id
        self.add_round_entries(rnd, advancing_group, source=source)

    def build_campaign_report(self, campaign):
        # TODO: must be a coordinator on the campaign
        # TODO: assert campaign is finalized

        ret = {}
        start_time = time.time()

        ret["campaign"] = campaign.to_info_dict()

        ret["rounds"] = [r.to_details_dict() for r in campaign.rounds
                         if r.status != CANCELLED_STATUS]  # TODO: switch to == FINALIZED_STATUS

        ret["coordinators"] = [cc.user.to_info_dict() for cc in
                               campaign.campaign_coords]

        rnds = self.get_campaign_rounds(campaign, with_cancelled=False)

        final_rnd = rnds[-1]

        assert final_rnd.vote_method == 'ranking'

        juror_alias_map = None

        def make_juror_alias_map(juror_ranking_map):
            jurors = juror_ranking_map.keys()
            random.shuffle(jurors)
            # TODO: gonna be in trouble for final rounds with greater
            # than 26 jurors (double letters)
            return dict([(juror, alias) for juror, alias
                         in zip(jurors, string.uppercase)])

        def alias_jurors(juror_ranking_map):
            ret = {}
            for k, v in juror_ranking_map.items():
                ret[juror_alias_map[k]] = v
            return ret

        ranking_list = self.get_round_ranking_list(final_rnd.id)

        ret['all_jurors'] = set(sum([[j['username'] for j in r['jurors']]
                                     for r in ret['rounds']], []))

        winners = []

        for fer in ranking_list:
            # TODO: get entry description from commons
            cur = {}
            cur['ranking'] = fer.rank
            cur['entry'] = fer.entry.to_dict()  # TODO (need desc, etc.)

            if not juror_alias_map:
                jrm = fer.juror_ranking_map
                # automatically alias by default
                if final_rnd.config.get('alias_jurors', True):
                    juror_alias_map = make_juror_alias_map(jrm)
                else:
                    # dummy map
                    juror_alias_map = dict([(k, k) for k in jrm])

            cur['juror_ranking_map'] = alias_jurors(fer.juror_ranking_map)
            cur['juror_review_map'] = alias_jurors(fer.juror_review_map)
            winners.append(cur)

        ret['winners'] = winners

        ret['render_date'] = datetime.datetime.utcnow()
        ret['render_duration'] = time.time() - start_time

        return ret


class OrganizerDAO(object):
    def __init__(self, user_dao):
        self.user = user_dao.user
        if not (self.user.is_maintainer or self.user.is_organizer):
            raise Forbidden('must have maintainer permissions')
        self.user_dao = user_dao
        self.query = user_dao.query
        self.rdb_session = user_dao.rdb_session
        self.get_or_create_user = user_dao.get_or_create_user
        self.log_action = user_dao.log_action

    def add_coordinator(self, campaign_id, username):
        campaign = self.user_dao.get_campaign(campaign_id)
        user = self.get_or_create_user(username, 'coordinator',
                                       campaign=campaign)
        if user in campaign.coords:
            raise InvalidAction('user is already a coordinator')
        campaign.coords.append(user)
        self.rdb_session.add(user)

        msg = ('%s added %s as a coordinator of campaign "%s"'
               % (self.user.username, user.username, campaign.name))
        self.log_action('add_coordinator', campaign_id=campaign.id,
                        message=msg, role='organizer')
        return user

    def remove_coordinator(self, campaign_id, username):
        campaign = self.user_dao.get_campaign(campaign_id)
        removed = None
        for user in campaign.coords:
            if user.username == username:
                campaign.coords.remove(user)
                removed = user
        if not removed:
            raise InvalidAction('user %s is not a coordinator' % username)
        msg = ('%s removed %s as a coordinator on campaign "%s" (#%s)'
               % (self.user.username, username, campaign.name, campaign.id))
        self.log_action('remove_coordinator', campaign=campaign, message=msg,
                        role='organizer')
        return removed

    def create_campaign(self, name, open_date, close_date, coords=None):
        # TODO: Check if campaign with this name already exists?
        if not coords:
            coords = [self.user]

        campaign = Campaign(name=name,
                            open_date=open_date,
                            close_date=close_date,
                            status=ACTIVE_STATUS,
                            coords=coords)
        self.rdb_session.add(campaign)
        self.rdb_session.flush()  # to get a campaign id
        msg = '%s created campaign "%s"' % (self.user.username, campaign.name)
        self.log_action('create_campaign', campaign=campaign, message=msg,
                        role='organizer')
        return campaign

    def cancel_campaign(self, campaign_id):
        cancel_date = datetime.datetime.utcnow()
        campaign = self.user_dao.get_campaign(campaign_id)
        rounds = (self.query(Round)
                      .filter(Round.campaign_id == campaign_id)
                      .all())
        campaign.status = CANCELLED_STATUS
        for round in rounds:
            self.cancel_round(round)
        msg = '%s cancelled campaign "%s" and %s rounds' %\
              (self.user.username, campaign.name, len(rounds))
        self.log_action('cancel_campaign', campaign=campaign, message=msg)


class MaintainerDAO(object):
    def __init__(self, user_dao):
        self.user = user_dao.user
        if not self.user.is_maintainer:
            raise Forbidden('must have Maintainer permission')
        self.user_dao = user_dao
        self.query = user_dao.query
        self.rdb_session = user_dao.rdb_session
        self.get_or_create_user = user_dao.get_or_create_user
        self.log_action = user_dao.log_action

    def get_audit_log(self, limit=100, offset=0):
        audit_logs = self.query(AuditLogEntry)\
                         .order_by(AuditLogEntry.create_date.desc())\
                         .limit(limit)\
                         .offset(offset)\
                         .all()
        return audit_logs

    def get_active_users(self):
        users = (self.rdb_session.query(User)
                 .filter(User.last_active_date != None)
                 .order_by(User.last_active_date.desc())
                 .all())
        return list(users)

    def add_organizer(self, username):
        user = self.get_or_create_user(username, 'organizer')
        if user.is_organizer:
            pass
        else:
            user.is_organizer = True
            self.rdb_session.add(user)
        msg = ('%s added %s as an organizer' % (self.user.username, username))
        self.log_action('add_organizer', message=msg, role='maintainer')
        return user

    def remove_organizer(self, username):
        user = lookup_user(self.rdb_session, username=username)
        if not user:
            raise InvalidAction('user %s is not an organizer' % username)
        user.is_organizer = False
        msg = ('%s removed %s as an organizer' % (self.user.username, username))
        self.log_action('remove_organizer', message=msg, role='maintianer')
        return user


def bootstrap_maintainers(rdb_session):
    # returns created users
    ret = []
    for username in MAINTAINERS:
        user = lookup_user(rdb_session, username=username)

        if not user:
            user_id = get_mw_userid(username)
            user = User(id=user_id,
                        username=username,
                        created_by=None)
            rdb_session.add(user)
            ret.append(user)
    return ret


class JurorDAO(object):
    """A Data Access Object for the Juror's view"""
    def __init__(self, user_dao):
        self.user = user_dao.user
        self.user_dao = user_dao
        self.query = user_dao.query
        self.rdb_session = user_dao.rdb_session
        self.get_or_create_user = user_dao.get_or_create_user
        self.log_action = user_dao.log_action

    # Read methods
    def get_campaign(self, campaign_id):
        if self.user.is_maintainer or self.user.is_organizer:
            return self.get_any_campaign(campaign_id)
        campaign = self.query(Campaign)\
                       .filter(Campaign.rounds.any(
                           Round.jurors.any(username=self.user.username)))\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        if not campaign:
            raise Forbidden('not a juror on campaign %s' % campaign_id)
        return campaign

    def get_any_campaign(self, campaign_id):
        campaign = (self.query(Campaign)
                    .filter_by(id=campaign_id)
                    .one_or_none())
        if not campaign:
            raise DoesNotExist('campaign %s does not exist' % campaign_id)
        return campaign

    def get_round(self, round_id):
        if self.user.is_maintainer or self.user.is_organizer:
            return self.get_any_round(round_id)
        rnd = self.query(Round)\
                  .filter(
                      Round.jurors.any(username=self.user.username),
                      Round.id == round_id)\
                  .one_or_none()
        if not rnd:
            raise Forbidden('not a juror for round %s' % round_id)
        return rnd

    def get_any_round(self, round_id):
        rnd = (self.query(Round)
               .filter_by(id=round_id)
               .one_or_none())

        if not rnd:
            raise DoesNotExist('round %s does not exist' % round_id)
        return rnd

    def confirm_active(self, round_id):
        rnd = self.get_round(round_id)
        return rnd.confirm_active()

    def get_round_task_counts(self, round_id):
        # the fact that these are identical for two DAOs shows it
        # should be on the Round model or somewhere else shared
        re_count = self.query(RoundEntry).filter_by(round_id=round_id).count()
        total_tasks = self.query(Vote)\
                          .filter(Vote.round_entry.has(round_id=round_id),
                                  Vote.user_id == self.user.id,
                                  Vote.status != CANCELLED_STATUS)\
                          .count()
        total_open_tasks = self.query(Vote)\
                               .filter(Vote.round_entry.has(round_id=round_id),
                                       Vote.user_id == self.user.id,
                                       Vote.status == ACTIVE_STATUS)\
                               .count()

        if total_tasks:
            percent_open = round((100.0 * total_open_tasks) / total_tasks, 3)
        else:
            percent_open = 0.0
        return {'total_round_entries': re_count,
                'total_tasks': total_tasks,
                'total_open_tasks': total_open_tasks,
                'percent_tasks_open': percent_open}

    def get_task(self, vote_id):
        task = self.query(Vote)\
                   .filter_by(id=vote_id)\
                   .filter(Vote.user == self.user)\
                   .one_or_none()
        return task

    def get_tasks(self, num=1, offset=0):
        tasks = self.query(Vote)\
                    .filter(Vote.user == self.user,
                            Vote.status == ACTIVE_STATUS)\
                    .limit(num)\
                    .offset(offset)\
                    .all()
        if not tasks:
            raise Forbidden('no assigned tasks')
        return tasks

    def get_total_tasks(self):
        task_count = self.query(Vote)\
                         .filter(Vote.user == self.user,
                                 Vote.status == ACTIVE_STATUS)\
                         .count()
        return task_count

    def get_tasks_by_id(self, task_ids):
        if isinstance(task_ids, int):
            task_ids = [task_ids]

        ret = (self.query(Vote)
               .options(joinedload('round_entry'))
               .filter(Vote.id.in_(task_ids),
                       Vote.user == self.user)
               .all())
        return ret

    def get_tasks_from_round(self, round_id, num=1, offset=0):
        tasks = self.query(Vote)\
                    .filter(Vote.user == self.user,
                            Vote.status == ACTIVE_STATUS,
                            Vote.round_entry.has(round_id=round_id))\
                    .limit(num)\
                    .offset(offset)\
                    .all()
        return tasks

    def get_ratings_from_round(self, round_id, num, offset=0):
        # all the filter fields but cancel_date are actually on Vote
        # already
        ratings = self.query(Vote)\
                      .options(joinedload('round_entry'))\
                      .filter(Vote.user == self.user,
                              Vote.status == COMPLETED_STATUS,
                              Vote.round_entry.has(round_id=round_id))\
                      .limit(num)\
                      .offset(offset)\
                      .all()
        if not ratings:
            raise Forbidden('no complete ratings')
        return ratings

    def get_rankings_from_round(self, round_id):
        rankings = self.query(Vote)\
                       .filter(Vote.user == self.user,
                               Vote.status == COMPLETED_STATUS,
                               Vote.round_entry.has(round_id=round_id))\
                       .options(joinedload('round_entry'))\
                       .all()
        return rankings

    def _build_round_stats(self,
                           re_count,
                           total_tasks,
                           total_open_tasks):
        if total_tasks:
            percent_open = round((100.0 * total_open_tasks) / total_tasks, 3)
        else:
            percent_open = 0.0
        return {'total_round_entries': re_count,
                'total_tasks': total_tasks,
                'total_open_tasks': total_open_tasks,
                'percent_tasks_open': percent_open}

    def get_task_counts(self):
        re_count = self.query(RoundEntry).count()
        total_tasks = self.query(Vote)\
                          .filter(Vote.user_id == self.user.id,
                                  Vote.status != CANCELLED_STATUS)\
                          .count()
        total_open_tasks = self.query(Vote)\
                               .filter(Vote.user_id == self.user.id,
                                       Vote.status == ACTIVE_STATUS)\
                               .count()
        return self._build_round_stats(re_count, total_tasks, total_open_tasks)

    def get_all_rounds_task_counts(self):
        entry_count = 'entry_count'
        task_count = 'task_count'
        campaign_id = '_campaign_id'
        campaign_name = '_campaign_name'
        campaign_open_date = '_campaign_open_date'
        campaign_close_date = '_campaign_close_date'

        user_rounds_join = rounds_t.join(
                round_jurors_t,
                onclause=((rounds_t.c.id == round_jurors_t.c.round_id)
                          & (round_jurors_t.c.user_id == self.user.id))
            )

        users_rounds_query = select(
            list(rounds_t.c) +
            [
                campaigns_t.c.id.label(campaign_id),
                campaigns_t.c.name.label(campaign_name),
                campaigns_t.c.open_date.label(campaign_open_date),
                campaigns_t.c.close_date.label(campaign_close_date),
            ] +
            [
                func.count(round_entries_t.c.id).label(entry_count),
            ]).select_from(
                user_rounds_join.join(
                    campaigns_t,
                    onclause=(campaigns_t.c.id == rounds_t.c.campaign_id),
                ).outerjoin(
                    round_entries_t,
                    onclause=(rounds_t.c.id == round_entries_t.c.round_id),
                ),
            ).group_by(
                rounds_t.c.id,
            ).order_by(
                campaign_id,
            )

        all_user_rounds = self.rdb_session.execute(
            users_rounds_query,
        )

        def tasks_query(where):
            return select(
                [rounds_t.c.id, func.count(votes_t.c.id).label(task_count)],
            ).select_from(
                user_rounds_join.outerjoin(
                    round_entries_t,
                    onclause=(rounds_t.c.id == round_entries_t.c.round_id),
                ).outerjoin(
                    votes_t,
                    onclause=(round_entries_t.c.id == votes_t.c.round_entry_id)
                )
            ).where(
                (votes_t.c.user_id.in_([self.user.id, None])) & where
            ).group_by(
                rounds_t.c.id
            ).order_by(
                asc("id")
            )

        rounds_all_tasks_query = tasks_query(votes_t.c.status != CANCELLED_STATUS)
        rounds_all_tasks = self.rdb_session.execute(rounds_all_tasks_query)
        rounds_open_tasks_query = tasks_query(votes_t.c.status == ACTIVE_STATUS)
        rounds_open_tasks = self.rdb_session.execute(rounds_open_tasks_query)

        rounds_to_total_tasks = {row['id']: row[task_count]
                                 for row in rounds_all_tasks}
        rounds_to_total_open_tasks = {row['id']: row[task_count]
                                      for row in rounds_open_tasks}
        results = []
        for row in all_user_rounds:
            round_kwargs = dict(row)

            re_count = round_kwargs.pop(entry_count)
            campaign = Campaign(id=round_kwargs.pop(campaign_id),
                                name=round_kwargs.pop(campaign_name),
                                open_date=round_kwargs.pop(campaign_open_date),
                                close_date=round_kwargs.pop(campaign_close_date))

            round = Round(**round_kwargs)
            round.campaign = campaign

            total_tasks = rounds_to_total_tasks.get(round.id, 0)
            total_open_tasks = rounds_to_total_open_tasks.get(round.id, 0)

            results.append(
                (round,
                 self._build_round_stats(
                     re_count, total_tasks, total_open_tasks)),
            )
        return results

    def apply_rating(self, vote, value, review=''):
        if not vote.user == self.user:
            # belt and suspenders until server test covers the cross
            # complete case
            raise PermissionDenied()
        now = datetime.datetime.utcnow()
        review_stripped = review.strip()
        if len(review_stripped) > 8192:
            raise ValueError('review must be less than 8192 characters, not %r'
                             % len(review_stripped))
        if review_stripped:
            vote['flags']['review'] = review_stripped
        vote.complete_date = now
        vote.status = COMPLETED_STATUS
        self.rdb_session.add(vote)
        return vote

    def edit_rating(self, task, value):
        if not task.user == self.user:
            raise PermissionDenied()
        now = datetime.datetime.utcnow()
        rating = self.rdb_session.query(Vote)\
                                 .filter_by(id=task.id)\
                                 .first()
        rating.value = value
        rating.modified_date = now
        rating.status = COMPLETED_STATUS
        return rating

    def apply_ranking(self, ballot):
        """ballot format:

        [{"task": <Task object>,
          "value": 0,
          "review": "The light dances across the image."},
        {...}]

        ballot can be in any order, with values representing
        ranks. ties are allowed.
        """
        now = datetime.datetime.utcnow()
        for r_dict in ballot:
            vote = r_dict['vote']
            review = r_dict.get('review') or ''
            vote.value = r_dict['value']
            if review:
                vote.flags['review'] = review

            vote.modified_date = now
            vote.status = COMPLETED_STATUS
            self.rdb_session.add(vote)
        return


def lookup_user(rdb_session, username):
    user = rdb_session.query(User).filter_by(username=username).one_or_none()
    return user


def create_initial_tasks(rdb_session, rnd):
    if rnd.vote_method in ('yesno', 'rating'):
        ret = create_initial_rating_tasks(rdb_session, rnd)
    elif rnd.vote_method == 'ranking':
        ret = create_ranking_tasks(rdb_session, rnd)
    else:
        raise ValueError('invalid round vote method: %r' % rnd.vote_method)
    return ret


def create_ranking_tasks(rdb_session, rnd, jurors=None):
    ret = []

    if jurors is None:
        jurors = [rj.user for rj in rnd.round_jurors if rj.is_active]
    if not jurors:
        raise InvalidAction('expected round with active jurors')

    rdb_type = rdb_session.bind.dialect.name

    if rdb_type == 'mysql':
        rand_func = func.rand()
    else:
        rand_func = func.random()

    # this does the shuffling in the database
    shuffled_entries = (rdb_session.query(RoundEntry)
                                   .filter(RoundEntry.round_id == rnd.id,
                                           RoundEntry.dq_user_id == None,
                                           RoundEntry.vote == None)
                                   .order_by(rand_func).all())
    if not shuffled_entries:
        return []

    for juror in jurors:
        for entry in shuffled_entries:
            vote = Vote(user=juror, round_entry=entry, status=ACTIVE_STATUS)
            ret.append(vote)

    return ret


def create_initial_rating_tasks(rdb_session, rnd, tasks_per_entry=None):
    # Creates a specified number of tasks per entry.

    ret = []

    if not tasks_per_entry:
        tasks_per_entry = rnd.quorum

    if tasks_per_entry > len(rnd.round_jurors):
        raise InvalidAction('quorum cannot be greater than the number of jurors')

    jurors = [rj.user for rj in rnd.round_jurors if rj.is_active]
    if not jurors:
        raise InvalidAction('expected round with active jurors')
    random.shuffle(jurors)

    rdb_type = rdb_session.bind.dialect.name

    if rdb_type == 'mysql':
        rand_func = func.rand()
    else:
        rand_func = func.random()

    # this does the shuffling in the database
    shuffled_entries = (rdb_session.query(RoundEntry)
                                   .filter(RoundEntry.round_id == rnd.id,
                                           RoundEntry.dq_user_id == None,
                                           RoundEntry.vote == None)
                                   .order_by(rand_func).all())
    if not shuffled_entries:
        return []
    # Note: It's only creating tasks for entries with no tasks. A
    # better approach would be to check if each entry meets the
    # quorum, and create tasks accordingly

    to_process = itertools.chain.from_iterable([shuffled_entries] * tasks_per_entry)
    # some pictures may get more than quorum votes
    # it's either that or some get less
    per_juror = int(ceil(len(shuffled_entries)
                         * (float(tasks_per_entry) / len(jurors))))

    juror_iters = itertools.chain.from_iterable([itertools.repeat(j, per_juror)
                                                 for j in jurors])

    pairs = itertools.izip_longest(to_process, juror_iters, fillvalue=None)

    for entry, juror in pairs:
        assert juror is not None, 'should never run out of jurors first'
        if entry is None:
            break

        # TODO: bulk_save_objects
        vote = Vote(user=juror, round_entry=entry, status=ACTIVE_STATUS)
        ret.append(vote)
    return ret


def reassign_tasks(session, rnd, new_jurors, strategy=None):
    if rnd.vote_method in ('yesno', 'rating'):
        ret = reassign_rating_tasks(session, rnd, new_jurors,
                                    strategy=strategy)
    elif rnd.vote_method == 'ranking':
        ret = reassign_ranking_tasks(session, rnd, new_jurors,
                                     strategy=strategy)
    else:
        raise ValueError('invalid round vote method: %r' % rnd.vote_method)
    return ret


def reassign_ranking_tasks(session, rnd, new_jurors, strategy=None):
    assert len(new_jurors) > 0

    old_jurors = session.query(User)\
                        .join(RoundJuror)\
                        .filter_by(round=rnd, is_active=True)\
                        .all()

    """
    For all removed jurors, cancel their tasks.
    For all added jurors, create their tasks.
    """
    old_juror_id_set = set([j.id for j in old_jurors])
    new_juror_id_set = set([j.id for j in new_jurors])
    if new_juror_id_set == old_juror_id_set:
        return
    removed_jurors = [j for j in old_jurors if j.id not in new_juror_id_set]
    added_jurors = [j for j in new_jurors if j.id not in old_juror_id_set]

    now = datetime.datetime.utcnow()

    votes_to_cancel = []
    if removed_jurors:
        removed_juror_ids = [j.id for j in removed_jurors]
        votes_to_cancel = (session.query(Vote)
                           .filter_by(status=ACTIVE_STATUS)
                           .filter(Vote.user_id.in_(removed_juror_ids))
                           .join(RoundEntry)
                           .filter_by(round=rnd).all())
        for vote in votes_to_cancel:
            vote.status = CANCELLED_STATUS
            vote.modified_date = now

    added_votes = []
    if added_jurors:
        added_votes = create_ranking_tasks(session, rnd, jurors=added_jurors)

    ret = {'reassigned_task_count': len(votes_to_cancel) + len(added_votes),
           'task_count_mean': -1}

    return ret


def reassign_rating_tasks(session, rnd, new_jurors, strategy=None,
                          reassign_all=False):
    """Different strategies for different outcomes:

    1. Try to balance toward everyone having cast roughly the same
       number of votes (fair)
    2. Try to balance toward the most even task queue length per user
       (fast)
    3. Balance toward the users that have been voting most (fastest)

    This function takes the second approach to get a reasonably fast,
    fair result.

    This function does not create or delete tasks. There must be
    enough new jurors to fulfill round quorum.

    Features:

    * No juror is assigned the same RoundEntry twice.
    * Looks at all Jurors who have ever submitted a Rating for the
      Round, meaning that a Juror can be added, removed, and added
      again without seeing duplicates.
    * Evens out work queues, so that workload can be redistributed.

    """
    # TODO: have this cancel tasks and create new ones.

    assert len(new_jurors) >= rnd.quorum

    cur_votes = session.query(Vote)\
                       .options(joinedload('round_entry'))\
                       .join(RoundEntry)\
                       .filter_by(round=rnd)\
                       .all()

    incomp_votes = []
    reassg_votes = []

    elig_map = defaultdict(lambda: list(new_jurors))
    work_map = defaultdict(list)

    comp_votes = [v for v in cur_votes if v.status == COMPLETED_STATUS]
    for vote in comp_votes:
        try:
            elig_map[vote.round_entry].remove(vote.user)
        except ValueError:
            pass

    incomp_votes = [v for v in cur_votes if v.status == ACTIVE_STATUS]

    for vote in incomp_votes:
        work_map[vote.user].append(vote)

    target_work_map = dict([(j, []) for j in new_jurors])
    target_workload = int(len(incomp_votes) / float(len(new_jurors))) + 1
    for user, user_votes in work_map.items():
        if reassign_all or user not in new_jurors:
            reassg_votes.extend(user_votes)
            continue

        reassg_votes.extend(user_votes[target_workload:])
        target_work_map[user] = user_votes[:target_workload]
        for vote in target_work_map[user]:
            try:
                elig_map[vote.round_entry].remove(user)
            except ValueError:
                pass

    # and now the distribution of tasks begins

    # future optimization note: totally new jurors are easy, as we can
    # skip eligibility checks

    # assuming initial task randomization remains sufficient here

    reassg_queue = list(reassg_votes)

    def choose_eligible(eligible_users):
        # TODO: cache?
        wcp = [(target_workload - len(w), u)
               for u, w in target_work_map.items()
               if u in eligible_users]
        wcp = [(p[0] if p[0] > 0 else 0.0001, p[1]) for p in wcp]

        return weighted_choice(wcp)

    while reassg_queue:
        vote = reassg_queue.pop()
        vote.user = choose_eligible(elig_map[vote.round_entry])

        # try:  # consider uncommenting this try/except if there are issues
        elig_map[vote.round_entry].remove(vote.user)
        # except ValueError:
        #    pass

        target_work_map[vote.user].append(vote)

    vote_count_map = dict([(u, len(t)) for u, t in target_work_map.items()])

    return {'incomplete_task_count': len(incomp_votes),
            'reassigned_task_count': len(reassg_votes),
            'task_count_map': vote_count_map,
            'task_count_mean': mean(vote_count_map.values())}


def make_rdb_session(echo=True):
    from utils import load_env_config
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    try:
        config = load_env_config()
    except Exception:
        print '!!  no db_url specified and could not load config file'
        raise
    else:
        db_url = config.get('db_url')

    engine = create_engine(db_url, echo=echo, encoding='utf8')

    session_type = sessionmaker()
    session_type.configure(bind=engine)
    session = session_type()

    return session


"""* Indexes
* db session management, engine creation, and schema creation separation
* prod db pw management
* add simple_serdes for E-Z APIs

TODO: what should the tallying for ratings look like? Get all the
ratings that form the quorum and average them? or median? (sum is the
same as average) what about when images have more than quorum ratings?

"""
