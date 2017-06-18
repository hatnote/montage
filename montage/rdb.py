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

from utils import (format_date,
                   to_unicode,
                   json_serial,
                   get_mw_userid,
                   weighted_choice,
                   PermissionDenied, InvalidAction)
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

    tasks = relationship('Task', back_populates='user')
    ratings = relationship('Rating', back_populates='user')
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
    campaign_coords = relationship('CampaignCoord')
    coords = association_proxy('campaign_coords', 'user',
                               creator=lambda user: CampaignCoord(coord=user))

    @property
    def active_round(self):
        return first([r for r in self.rounds
                      if r.status in ('active', 'paused')], None)

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
        task_count = rdb_session.query(Task)\
                                .filter(Task.round_entry.has(round_id=self.id),
                                        Task.cancel_date == None)\
                                .count()
        open_task_count = rdb_session.query(Task)\
                                     .filter(Task.round_entry.has(round_id=self.id),
                                             Task.complete_date == None,
                                             Task.cancel_date == None)\
                                     .count()
        cancelled_task_count = rdb_session.query(Task)\
                                     .filter(Task.round_entry.has(round_id=self.id),
                                             Task.cancel_date != None)\
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
        if self.entries and self.status == 'active' or self.status == 'paused':
            open_tasks = rdb_session.query(Task)\
                                    .options(joinedload('round_entry'))\
                                    .filter(Task.round_entry.has(round_id=self.id),
                                            Task.complete_date == None,
                                            Task.cancel_date == None)\
                                    .first()
            return not open_tasks
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
        task_count = rdb_session.query(Task)\
                                .filter(Task.round_entry.has(round_id=self.round_id),
                                        Task.user_id == self.user_id,
                                        Task.cancel_date == None)\
                                .count()
        open_task_count = rdb_session.query(Task)\
                                     .filter(Task.round_entry.has(round_id=self.round_id),
                                             Task.user_id == self.user_id,
                                             Task.complete_date == None,
                                             Task.cancel_date == None)\
                                     .count()
        cancelled_task_count = rdb_session.query(Task)\
                                     .filter(Task.round_entry.has(round_id=self.round_id),
                                             Task.user_id == self.user_id,
                                             Task.complete_date == None,
                                             Task.cancel_date != None)\
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
    tasks = relationship('Task', back_populates='round_entry')
    rating = relationship('Rating', back_populates='round_entry')
    ranking = relationship('Ranking', back_populates='round_entry')

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


class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    value = Column(Float)

    user = relationship('User')
    task = relationship('Task', back_populates='rating')
    user = relationship('User', back_populates='ratings')
    round_entry = relationship('RoundEntry', back_populates='rating')

    entry = association_proxy('round_entry', 'entry',
                              creator=lambda e: RoundEntry(entry=e))

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    def __init__(self, **kw):
        self.flags = kw.pop('flags', {})
        super(Rating, self).__init__(**kw)

    def to_info_dict(self):
        info = {'id': self.id,
                'task_id': self.task.id,
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


class Ranking(Base):
    __tablename__ = 'rankings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    value = Column(Integer)

    user = relationship('User')
    task = relationship('Task')
    round_entry = relationship('RoundEntry', back_populates='ranking')

    entry = association_proxy('round_entry', 'entry',
                              creator=lambda e: RoundEntry(entry=e))

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    def __init__(self, **kw):
        self.flags = kw.pop('flags', {})
        super(Ranking, self).__init__(**kw)

    def to_info_dict(self):
        info = {'id': self.id,
                'task_id': self.task.id,
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


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    user = relationship('User', back_populates='tasks')
    rating = relationship('Rating')
    round_entry = relationship('RoundEntry', back_populates='tasks')

    create_date = Column(TIMESTAMP, server_default=func.now())
    complete_date = Column(DateTime)
    cancel_date = Column(DateTime)

    entry = association_proxy('round_entry', 'entry',
                              creator=lambda e: RoundEntry(entry=e))

    def to_info_dict(self):
        ret = {'id': self.id,
               'round_entry_id': self.round_entry_id}
        return ret

    def to_details_dict(self):
        ret = self.to_info_dict()
        ret['entry'] = self.entry.to_details_dict()
        return ret


tasks_t = Task.__table__


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

    create_date = Column(TIMESTAMP, server_default=func.now())

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

    # Read methods
    def get_campaign(self, campaign_id):
        campaign = self.query(Campaign)\
                       .filter(
                           Campaign.coords.any(username=self.user.username))\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        return campaign

    def get_all_campaigns(self):
        campaigns = self.query(Campaign)\
                        .filter(
                            Campaign.coords.any(username=self.user.username))\
                        .all()
        return campaigns

    def get_round(self, round_id):
        round = self.query(Round)\
                    .filter(
                        Round.campaign.has(
                            Campaign.coords.any(username=self.user.username)))\
                    .filter_by(id=round_id)\
                    .one_or_none()
        return round

    def get_campaign_rounds(self, campaign, with_cancelled=False):
        q = self.query(Round).filter_by(campaign=campaign)
        if not with_cancelled:
            q.filter(Round.status != 'cancelled')
        q.order_by(Round.create_date)
        return q.all()

    def get_active_jurors(self, rnd):
        rjs = (self.query(RoundJuror)
               .filter_by(is_active=True,
                          round_id=rnd.id)
               .options(joinedload('user'))
               .all())
        users = [rj.user for rj in rjs]
        return users

    def get_round_task_counts(self, rnd):
        # the fact that these are identical for two DAOs shows it
        # should be on the Round model or somewhere else shared
        re_count = self.query(RoundEntry).filter_by(round_id=rnd.id).count()
        total_tasks = self.query(Task)\
                          .filter(Task.round_entry.has(round_id=rnd.id),
                                  Task.cancel_date == None)\
                          .count()
        total_open_tasks = self.query(Task)\
                               .filter(Task.round_entry.has(round_id=rnd.id),
                                       Task.user_id == self.user.id,
                                       Task.complete_date == None,
                                       Task.cancel_date == None)\
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
    def edit_campaign(self, campaign_id, campaign_dict):
        ret = self.rdb_session.query(Campaign)\
                              .filter_by(id=campaign_id)\
                              .update(campaign_dict)

        return ret

    def cancel_campaign(self, campaign):
        cancel_date = datetime.datetime.utcnow()
        campaign_id = campaign.id
        rounds = (self.query(Round)
                      .filter(Round.campaign_id == campaign_id)
                      .all())
        campaign.status = 'cancelled'
        for round in rounds:
            self.cancel_round(round)
        msg = '%s cancelled campaign "%s" and %s rounds' %\
              (self.user.username, campaign.name, len(rounds))
        self.log_action('cancel_campaign', campaign=campaign, message=msg)
        self.rdb_session.commit()

    def create_round(self, campaign, name, description, directions, quorum,
                     vote_method, jurors, deadline_date, config=None):

        if campaign.active_round:
            raise InvalidAction('can only create one active/paused round at a'
                                ' time. cancel or complete your existing'
                                ' rounds before trying again')
        config = config or {}
        jurors = [self.get_or_create_user(j, 'juror', campaign=campaign)
                  for j in jurors]

        for (k, v) in DEFAULT_ROUND_CONFIG.items():
            config[k] = config.get(k, v)

        full_config = dict(DEFAULT_ROUND_CONFIG)
        full_config.update(config)

        rnd = Round(name=name,
                    description=description,
                    directions=directions,
                    campaign=campaign,
                    campaign_seq=len(campaign.rounds),
                    status='paused',
                    quorum=quorum,
                    deadline_date=deadline_date,
                    vote_method=vote_method,
                    jurors=jurors,
                    config=full_config)

        self.rdb_session.add(rnd)

        j_names = [j.username for j in jurors]
        msg = ('%s created %s round "%s" (#%s) with jurors %r for'
               ' campaign "%s"' % (self.user.username, vote_method,
                                   rnd.name, rnd.id, j_names, campaign.name))
        self.log_action('create_round', round=rnd, message=msg)

        return rnd

    def autodisqualify_by_date(self, rnd, preview=False):
        campaign = rnd.campaign
        min_date = campaign.open_date
        max_date = campaign.close_date

        if (not min_date or not max_date):
            round_entries = []
            
            if not preview:
                msg = ('%s disqualified 0 entries by date due to missing, '
                       'campaign open or close date' % (self.user.username,))
                self.log_action('autodisqualify_by_date', round=rnd, message=msg)

            return round_entries

        round_entries = self.query(RoundEntry)\
                            .join(Entry)\
                            .filter(RoundEntry.round_id == rnd.id)\
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

            for task in round_entry.tasks:
                task.cancel_date = cancel_date

        msg = ('%s disqualified %s entries outside of date range %s - %s'
               % (self.user.username, len(round_entries), min_date, max_date))
        self.log_action('autodisqualify_by_date', round=rnd, message=msg)

        return round_entries

    def autodisqualify_by_resolution(self, rnd, preview=False):
        # TODO: get from config
        min_res = rnd.config.get('min_resolution', DEFAULT_MIN_RESOLUTION)

        round_entries = self.query(RoundEntry)\
                            .join(Entry)\
                            .filter(RoundEntry.round_id == rnd.id)\
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

            for task in r_ent.tasks:
                task.cancel_date = cancel_date

        msg = ('%s disqualified %s entries smaller than %s megapixels'
               % (self.user.username, len(round_entries), min_res_str))
        self.log_action('autodisqualify_by_resolution', round=rnd, message=msg)

        return round_entries

    def autodisqualify_by_filetype(self, rnd, preview=False):
        allowed_filetypes = rnd.config.get('allowed_filetypes')
        round_entries = self.query(RoundEntry)\
                            .join(Entry)\
                            .filter(RoundEntry.round_id == rnd.id)\
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

            for task in r_ent.tasks:
                task.cancel_date = cancel_date

        msg = ('%s disqualified %s entries by filetype not in %s'
               % (self.user.username, len(round_entries), allowed_filetypes))
        self.log_action('autodisqualify_by_filetype', round=rnd, message=msg)

        return round_entries

    def autodisqualify_by_uploader(self, rnd, preview=False):
        dq_group = {}
        dq_usernames = [j.username for j in rnd.jurors]

        for username in dq_usernames:
            dq_group[username] = 'juror'

        if rnd.config.get('dq_coords'):
            coord_usernames = [c.username for c in rnd.campaign.coords]
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
                            .filter(RoundEntry.round_id == rnd.id)\
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

            for task in round_entry.tasks:
                task.cancel_date = cancel_date

        msg = ('%s disqualified %s entries based on upload user'
               % (self.user.username, len(round_entries)))
        self.log_action('autodisqualify_by_uploader', round=rnd, message=msg)

        return round_entries

    def pause_round(self, rnd):
        rnd.status = 'paused'

        msg = '%s paused round "%s"' % (self.user.username, rnd.name)
        self.log_action('pause_round', round=rnd, message=msg)

        return rnd

    def activate_round(self, rnd):
        if not rnd.entries:
            raise InvalidAction('can not activate empty round, try importing'
                                ' entries first')

        if rnd.status != 'paused':
            raise InvalidAction('can only activate round in a paused state,'
                                ' not %r' % (rnd.status,))

        if not rnd.open_date:
            tasks = create_initial_tasks(self.rdb_session, rnd)
            rnd.open_date = datetime.datetime.utcnow()

            msg = ('%s opened round %s with %s tasks'
                   % (self.user.username, rnd.name, len(tasks)))
            self.log_action('open_round', round=rnd, message=msg)

        rnd.status = 'active'

        msg = '%s activated round "%s"' % (self.user.username, rnd.name)
        self.log_action('activate_round', round=rnd, message=msg)

        return

    def add_entries_from_cat(self, rnd, cat_name):
        entries = load_category(cat_name)

        entries, new_entry_count = self.add_entries(rnd, entries)

        msg = ('%s loaded %s entries from category (%s), %s new entries added'
               % (self.user.username, len(entries), cat_name, new_entry_count))
        self.log_action('add_entries', message=msg, round=rnd)

        return entries

    def add_entries_from_csv_gist(self, rnd, gist_url):
        # NOTE: this no longer creates RoundEntries, use
        # add_round_entries to do this.

        entries = get_entries_from_gist_csv(gist_url)

        entries, new_entry_count = self.add_entries(rnd, entries)

        msg = ('%s loaded %s entries from csv gist (%r), %s new entries added'
               % (self.user.username, len(entries), gist_url, new_entry_count))
        self.log_action('add_entries', message=msg, round=rnd)

        return entries

    def add_entries(self, rnd, entries):
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

    def add_round_entries(self, rnd, entries, source=''):
        if rnd.status != 'paused':
            raise InvalidAction('round must be paused to add new entries')
        existing_names = set(self.rdb_session.query(Entry.name).
                             join(RoundEntry).
                             filter_by(round=rnd).
                             all())
        new_entries = [e for e
                       in unique_iter(entries, key=lambda e: e.name)
                       if e.name not in existing_names]

        rnd.entries.extend(new_entries)

        msg = ('%s added %s round entries, %s new'
               % (self.user.username, len(entries), len(new_entries)))
        if source:
            msg += ' (from %s)' % (source,)
        self.log_action('add_round_entries', message=msg, round=rnd)

        return new_entries

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

    def cancel_round(self, rnd):
        tasks = self.query(Task)\
                    .filter(Task.round_entry.has(round_id=rnd.id))\
                    .all()
        cancel_date = datetime.datetime.utcnow()

        rnd.status = 'cancelled'
        rnd.close_date = cancel_date

        for task in tasks:
            task.cancel_date = cancel_date

        msg = '%s cancelled round "%s" and %s open tasks' %\
              (self.user.username, rnd.name, len(tasks))
        self.log_action('cancel_round', round=rnd, message=msg)
        self.rdb_session.commit()

        return rnd

    def finalize_rating_round(self, rnd, threshold):
        assert rnd.vote_method in ('rating', 'yesno')
        # TODO: assert all tasks complete

        rnd.close_date = datetime.datetime.utcnow()
        rnd.status = 'finalized'
        rnd.config['final_threshold'] = threshold

        advance_count = len(self.get_rating_advancing_group(rnd, threshold))

        msg = ('%s finalized rating round "%s" at threshold %s,'
               ' with %s entries advancing'
               % (self.user.username, rnd.name, threshold, advance_count))
        self.log_action('finalize_round', round=rnd, message=msg)

        return advance_count

    def finalize_ranking_round(self, rnd):
        assert rnd.vote_method == 'ranking'

        # TODO: Ranking method?

        rnd.close_date = datetime.datetime.utcnow()
        rnd.status = 'finalized'
        # rnd.config['ranking_method'] = method
        
        summary = self.build_campaign_report(rnd.campaign)

        result_summary = RoundResultsSummary(round_id=rnd.id,
                                             campaign_id=rnd.campaign.id,
                                             summary=summary)
        self.rdb_session.add(result_summary)
        self.rdb_session.commit()
        msg = ('%s finalized round "%s" (#%s) and created round results summary %s' % 
               (self.user.username, rnd.name, rnd.id, result_summary.id))
        self.log_action('finalize_ranking_round', round=rnd, message=msg)
        self.rdb_session.commit()
        return result_summary

    def get_campaign_report(self, campaign):
        campaign_id = campaign.id
        summary = self.query(RoundResultsSummary)\
                      .filter(
                          RoundResultsSummary.campaign.has(
                            Campaign.coords.any(username=self.user.username)))\
                      .filter_by(campaign_id=campaign_id)\
                      .one_or_none()
        return summary

    def get_rating_advancing_group(self, rnd, threshold=None):
        assert rnd.vote_method in ('rating', 'yesno')

        if threshold is None:
            threshold = rnd.config.get('final_threshold')
        if threshold is None:
            raise ValueError('expected threshold or finalized round')

        assert 0.0 <= threshold <= 1.0

        avg = func.avg(Rating.value).label('average')

        results = self.query(RoundEntry, Rating, avg)\
                      .options(joinedload('entry'))\
                      .filter_by(dq_user_id=None, round_id=rnd.id)\
                      .join(Rating)\
                      .group_by(Rating.round_entry_id)\
                      .having(avg >= threshold)\
                      .all()

        entries = [res[0].entry for res in results]

        return entries

    def get_round_average_rating_map(self, rnd):
        results = self.query(Rating, func.avg(Rating.value).label('average'))\
                      .join(RoundEntry)\
                      .filter(Rating.round_entry.has(round_id=rnd.id))\
                      .group_by(Rating.round_entry_id)\
                      .all()

        # thresh_counts = get_threshold_map(r[1] for r in ratings)
        rating_ctr = Counter([r[1] for r in results])

        return dict(rating_ctr)

    def get_round_ranking_list(self, rnd, notation):
        res = (self.query(Ranking)
               .options(joinedload('round_entry'))
               .filter(Ranking.round_entry.has(round_id=rnd.id))
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

            r_by_val = bucketize(rankings, lambda r: r.value)
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
        results = self.query(Rating)\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .join(Task, Rating.task_id == Task.id)\
                      .filter(RoundEntry.round_id == rnd.id,
                              RoundEntry.dq_user_id == None,
                              Task.cancel_date == None)\
                      .all()
        return results

    def get_all_rankings(self, rnd):
        results = self.query(Ranking)\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .join(Task, Ranking.task_id == Task.id)\
                      .filter(RoundEntry.round_id == rnd.id,
                              RoundEntry.dq_user_id == None,
                              Task.cancel_date == None)\
                      .all()
        return results

    def get_all_tasks(self, rnd):
        results = self.query(Task, Entry)\
                      .options(joinedload('user'))\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(RoundEntry.round_id == rnd.id,
                              RoundEntry.dq_user_id == None,
                              Task.cancel_date == None)\
                      .all()
        return results

    def get_disqualified(self, rnd):
        results = self.query(RoundEntry)\
                      .options(joinedload('entry'))\
                      .filter_by(round_id=rnd.id)\
                      .filter(RoundEntry.dq_user_id != None)\
                      .all()

        return results

    def modify_jurors(self, rnd, new_jurors):
        # NOTE: this does not add or remove tasks. Contrast this with
        # changing the quorum, which would remove tasks, but carries the
        # issue of possibly having to reweight or discard completed ratings.

        # TODO: check to make sure only certain round actions can happen
        # when paused, others only when active, basically none when the
        # round is complete or cancelled.
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
        old_jurors = self.get_active_jurors(rnd)
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

    def modify_quorum(self, rnd, new_quorum, strategy=None):
        # This only supports increasing the quorum. Decreaseing the
        # quorum would require handling some completed tasks (eg,
        # whose vote do you discard? Randomly choose?)

        # TODO: Support decreasing the quorum.

        old_quorum = rnd.quorum

        if not new_quorum:
            raise InvalidAction('must specify new quorum')
        
        if new_quorum <= old_quorum:
            raise NotImplemented('currently we do not support decreasing' +
                                 'the quorum, currently quourum is %r, got %r')

        jurors = self.get_active_jurors(rnd)
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
            ret.extend([Task(user=juror, round_entry=re)
                        for re in round_entries])
        return ret

    def create_ranking_round(self, campaign, name, jurors, deadline_date):
        # TODO: there might be some cases where they want to jump straight to the final round?
        # TODO: directions, other round params?
        assert campaign.active_round is None
        final_rnds = [r for r in campaign.rounds if r.status == 'finalized']
        prev_finalized_rnd = final_rnds[-1]  # TODO: these are ordered by date?
        assert prev_finalized_rnd.vote_method != 'ranking'

        advancing_group = self.get_rating_advancing_group(prev_finalized_rnd)

        assert 1 < len(advancing_group) <= 40  # TODO: configurable max

        rnd = self.create_round(campaign,
                                name=name,
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
                         if r.status != 'cancelled']  # TODO: switch to == 'finalized'

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

        ranking_list = self.get_round_ranking_list(final_rnd)

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


class OrganizerDAO(CoordinatorDAO):
    def add_coordinator(self, campaign, username):
        user = self.get_or_create_user(username, 'coordinator',
                                       campaign=campaign)
        if user in campaign.coords:
            raise InvalidAction('user is already a coordinator')
        campaign.coords.append(user)
        self.rdb_session.add(user)
        self.rdb_session.commit()

        msg = ('%s added %s as a coordinator of campaign "%s"'
               % (self.user.username, user.username, campaign.name))
        self.log_action('add_coordinator', campaign_id=campaign.id,
                        message=msg)
        return user

    def create_campaign(self, name, open_date, close_date, coords=None):
        # TODO: Check if campaign with this name already exists?
        if not coords:
            coords = [self.user]

        campaign = Campaign(name=name,
                            open_date=open_date,
                            close_date=close_date,
                            status='active',
                            coords=coords)

        self.rdb_session.add(campaign)

        msg = '%s created campaign "%s"' % (self.user.username, campaign.name)
        self.log_action('create_campaign', campaign=campaign, message=msg)

        return campaign

    # Read methods
    def get_all_campaigns(self):
        campaigns = self.query(Campaign)\
                        .all()
        return campaigns

    def get_campaign(self, campaign_id):
        campaign = self.query(Campaign)\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        return campaign

    def get_round(self, round_id):
        round = self.query(Round)\
                    .filter_by(id=round_id)\
                    .one_or_none()
        return round


class MaintainerDAO(OrganizerDAO):
    def get_audit_log(self, limit=100, offset=0):
        audit_logs = self.query(AuditLogEntry)\
                         .order_by(AuditLogEntry.create_date.desc())\
                         .limit(limit)\
                         .offset(offset)\
                         .all()
        return audit_logs

    def add_organizer(self, username):
        user = self.get_or_create_user(username, 'organizer')
        if user.is_organizer:
            pass
        else:
            user.is_organizer = True
            self.rdb_session.add(user)
            self.rdb_session.commit()
        return user

    def get_active_users(self):
        users = (self.rdb_session.query(User)
                 .filter(User.last_active_date != None)
                 .order_by(User.last_active_date.desc())
                 .all())
        return list(users)


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


class JurorDAO(UserDAO):
    """A Data Access Object for the Juror's view"""
    # Read methods
    def get_all_rounds(self):
        rounds = self.query(Round)\
                     .filter(Round.jurors.any(username=self.user.username))\
                     .all()
        return rounds

    def get_campaign(self, campaign_id):
        campaign = self.query(Campaign)\
                       .filter(Campaign.rounds.any(
                           Round.jurors.any(username=self.user.username)))\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        return campaign

    def get_round(self, round_id):
        round = self.query(Round)\
                    .filter(
                        Round.jurors.any(username=self.user.username),
                        Round.id == round_id)\
                    .one_or_none()
        return round

    def get_task(self, task_id):
        task = self.query(Task)\
                   .filter_by(id=task_id)\
                   .filter(Task.user == self.user)\
                   .one_or_none()
        return task

    def get_tasks(self, num=1, offset=0):
        tasks = self.query(Task)\
                    .filter(Task.user == self.user,
                            Task.complete_date == None,
                            Task.cancel_date == None)\
                    .limit(num)\
                    .offset(offset)\
                    .all()
        return tasks

    def get_total_tasks(self):
        task_count = self.query(Task)\
                         .filter(Task.user == self.user,
                                 Task.complete_date == None,
                                 Task.cancel_date == None)\
                         .count()
        return task_count

    def get_tasks_by_id(self, task_ids):
        if isinstance(task_ids, int):
            task_ids = [task_ids]

        ret = (self.query(Task)
               .options(joinedload('round_entry'))
               .filter(Task.id.in_(task_ids),
                       Task.user == self.user)
               .all())
        return ret

    def get_tasks_from_round(self, rnd, num=1, offset=0):
        tasks = self.query(Task)\
                    .filter(Task.user == self.user,
                            Task.complete_date == None,
                            Task.cancel_date == None,
                            Task.round_entry.has(round_id=rnd.id))\
                    .limit(num)\
                    .offset(offset)\
                    .all()
        return tasks

    def get_ratings_from_round(self, rnd, num, offset=0):
        # all the filter fields but cancel_date are actually on Rating
        # already
        ratings = self.query(Rating)\
                      .join(Task)\
                      .options(joinedload('round_entry'))\
                      .filter(Task.user == self.user,
                              Task.complete_date != None,
                              Task.cancel_date == None,
                              Task.round_entry.has(round_id=rnd.id))\
                      .limit(num)\
                      .offset(offset)\
                      .all()
        return ratings

    def get_rankings_from_round(self, rnd):
        rankings = self.query(Ranking)\
                       .filter(Ranking.user == self.user,
                               Ranking.round_entry.has(round_id=rnd.id))\
                       .join(Task)\
                       .options(joinedload('round_entry'))\
                       .filter(Task.cancel_date == None)\
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
        total_tasks = self.query(Task)\
                          .filter(Task.user_id == self.user.id,
                                  Task.cancel_date == None)\
                          .count()
        total_open_tasks = self.query(Task)\
                               .filter(Task.user_id == self.user.id,
                                       Task.complete_date == None,
                                       Task.cancel_date == None)\
                               .count()
        return self._build_round_stats(re_count, total_tasks, total_open_tasks)

    def get_round_task_counts(self, rnd):
        re_count = self.query(RoundEntry).filter_by(round_id=rnd.id).count()
        total_tasks = self.query(Task)\
                          .filter(Task.round_entry.has(round_id=rnd.id),
                                  Task.user_id == self.user.id,
                                  Task.cancel_date == None)
        total_tasks = total_tasks.count()
        total_open_tasks = self.query(Task)\
                               .filter(Task.round_entry.has(round_id=rnd.id),
                                       Task.user_id == self.user.id,
                                       Task.complete_date == None,
                                       Task.cancel_date == None)\
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
                [rounds_t.c.id, func.count(tasks_t.c.id).label(task_count)],
            ).select_from(
                user_rounds_join.outerjoin(
                    round_entries_t,
                    onclause=(rounds_t.c.id == round_entries_t.c.round_id),
                ).outerjoin(
                    tasks_t,
                    onclause=(round_entries_t.c.id == tasks_t.c.round_entry_id)
                )
            ).where(
                (tasks_t.c.user_id.in_([self.user.id, None])) & where
            ).group_by(
                rounds_t.c.id
            ).order_by(
                asc("id")
            )

        rounds_all_tasks_query = tasks_query(tasks_t.c.cancel_date == None)
        rounds_all_tasks = self.rdb_session.execute(rounds_all_tasks_query)
        rounds_open_tasks_query = tasks_query(
            (tasks_t.c.cancel_date == None) &
            (tasks_t.c.complete_date == None))
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

    def apply_rating(self, task, value, review=''):
        if not task.user == self.user:
            # belt and suspenders until server test covers the cross
            # complete case
            raise PermissionDenied()
        now = datetime.datetime.utcnow()
        rating = Rating(user_id=self.user.id,
                        task_id=task.id,
                        round_entry_id=task.round_entry_id,
                        value=value)
        review_stripped = review.strip()
        if len(review_stripped) > 8192:
            raise ValueError('review must be less than 8192 characters, not %r'
                             % len(review_stripped))
        if review_stripped:
            rating['flags']['review'] = review_stripped
        self.rdb_session.add(rating)
        task.complete_date = now
        return

    def edit_rating(self, task, value):
        if not task.user == self.user:
            raise PermissionDenied()
        now = datetime.datetime.utcnow()
        rating = self.rdb_session.query(Rating)\
                                 .filter_by(task_id=task.id)\
                                 .first()
        rating.value = value
        task.complete_date = now
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
            task = r_dict['task']
            ranking = Ranking(user_id=self.user.id,
                              task_id=task.id,
                              round_entry_id=task.round_entry.id,
                              value=r_dict['value'])
            review = r_dict.get('review') or ''
            if review:
                ranking.flags['review'] = review

            self.rdb_session.add(ranking)
            task.complete_date = now
        return

    def edit_ranking(self, ballot):
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
            task = r_dict['task']
            ranking = self.rdb_session.query(Ranking)\
                                      .filter_by(task_id=task.id)\
                                      .first()
            review = r_dict.get('review') or ''
            ranking.value = r_dict['value']
            if review:
                ranking.flags['review'] = review

            task.complete_date = now
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
    shuffled_entries = rdb_session.query(RoundEntry)\
                                  .filter(RoundEntry.round_id == rnd.id,
                                          RoundEntry.dq_user_id == None)\
                                  .order_by(rand_func).all()

    for juror in jurors:
        for entry in shuffled_entries:
            task = Task(user=juror, round_entry=entry)
            ret.append(task)

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
    shuffled_entries = rdb_session.query(RoundEntry)\
                                  .filter(RoundEntry.round_id == rnd.id,
                                          RoundEntry.dq_user_id == None)\
                                  .order_by(rand_func).all()

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
        task = Task(user=juror, round_entry=entry)
        ret.append(task)
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

    tasks_to_cancel = []
    if removed_jurors:
        removed_juror_ids = [j.id for j in removed_jurors]
        tasks_to_cancel = (session.query(Task)
                           .filter_by(complete_date=None,
                                      cancel_date=None)
                           .filter(Task.user_id.in_(removed_juror_ids))
                           .join(RoundEntry)
                           .filter_by(round=rnd).all())
        for task in tasks_to_cancel:
            task.cancel_date = now

    added_tasks = []
    if added_jurors:
        added_tasks = create_ranking_tasks(session, rnd, jurors=added_jurors)

    ret = {'reassigned_task_count': len(tasks_to_cancel) + len(added_tasks),
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

    cur_tasks = session.query(Task)\
                       .options(joinedload('round_entry'))\
                       .join(RoundEntry)\
                       .filter_by(round=rnd)\
                       .all()

    incomp_tasks = []
    reassg_tasks = []

    elig_map = defaultdict(lambda: list(new_jurors))
    work_map = defaultdict(list)

    # only complete_date because that indicates that's the only
    # indicator we have that the user has seen the entry
    comp_tasks = [t for t in cur_tasks if t.complete_date]
    for task in comp_tasks:
        try:
            elig_map[task.round_entry].remove(task.user)
        except ValueError:
            pass

    incomp_tasks = [t for t in cur_tasks
                    if not t.complete_date and not t.cancel_date]

    for task in incomp_tasks:
        work_map[task.user].append(task)

    target_work_map = dict([(j, []) for j in new_jurors])
    target_workload = int(len(incomp_tasks) / float(len(new_jurors))) + 1
    for user, user_tasks in work_map.items():
        if reassign_all or user not in new_jurors:
            reassg_tasks.extend(user_tasks)
            continue

        reassg_tasks.extend(user_tasks[target_workload:])
        target_work_map[user] = user_tasks[:target_workload]
        for task in target_work_map[user]:
            try:
                elig_map[task.round_entry].remove(user)
            except ValueError:
                pass

    # and now the distribution of tasks begins

    # future optimization note: totally new jurors are easy, as we can
    # skip eligibility checks

    # assuming initial task randomization remains sufficient here

    reassg_queue = list(reassg_tasks)

    def choose_eligible(eligible_users):
        # TODO: cache?
        wcp = [(target_workload - len(w), u)
               for u, w in target_work_map.items()
               if u in eligible_users]
        wcp = [(p[0] if p[0] > 0 else 0.0001, p[1]) for p in wcp]

        return weighted_choice(wcp)

    while reassg_queue:
        task = reassg_queue.pop()
        task.user = choose_eligible(elig_map[task.round_entry])

        # try:  # consider uncommenting this try/except if there are issues
        elig_map[task.round_entry].remove(task.user)
        # except ValueError:
        #    pass

        target_work_map[task.user].append(task)

    task_count_map = dict([(u, len(t)) for u, t in target_work_map.items()])

    return {'incomplete_task_count': len(incomp_tasks),
            'reassigned_task_count': len(reassg_tasks),
            'task_count_map': task_count_map,
            'task_count_mean': mean(task_count_map.values())}


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
