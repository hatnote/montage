# -*- coding: utf-8 -*-

# Relational database models for Montage
import json
import time
import random
import string
import datetime
import itertools
from collections import Counter, defaultdict
from math import ceil

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
from sqlalchemy.sql import func, asc, distinct
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
                   get_mw_userid,
                   weighted_choice,
                   PermissionDenied, InvalidAction, NotImplementedResponse,
                   DoesNotExist,
                   get_env_name,
                   load_default_series,
                   js_isoparse)

from imgutils import make_mw_img_url
import loaders
from simple_serdes import DictableBase, JSONEncodedDict

Base = declarative_base(cls=DictableBase)

ONE_MEGAPIXEL = 1e6
DEFAULT_MIN_RESOLUTION = 2 * ONE_MEGAPIXEL
IMPORT_CHUNK_SIZE = 200

# By default, srounds will support all the file types allowed on
# Wikimedia Commons -- see: Commons:Project_scope/Allowable_file_types
DEFAULT_ALLOWED_FILETYPES = ['jpeg', 'png', 'gif', 'svg', 'tiff',
                             'xcf', 'webp']

# Some basic config settings
DEFAULT_ROUND_CONFIG = {'show_link': True,
                        'show_filename': True,
                        'show_resolution': True,
                        'dq_by_upload_date': True,
                        'dq_by_resolution': False,
                        'dq_by_uploader': False,
                        'dq_by_filetype': True,
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
PUBLISHED_STATUS = 'published'
PRIVATE_STATUS = 'private'

VALID_STATUS = [ACTIVE_STATUS, PAUSED_STATUS, CANCELLED_STATUS,
                FINALIZED_STATUS, COMPLETED_STATUS, PUBLISHED_STATUS,
                PRIVATE_STATUS]

ENV_NAME = get_env_name()

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

    username = Column(String(255), index=True)
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

    def to_dict(self):
        ret = super(User, self).to_dict()
        ret['is_organizer'] = ret.get('is_organizer') or self.is_maintainer
        return ret

    def to_info_dict(self):
        ret = {'id': self.id,
               'username': self.username,
               'is_organizer': self.is_organizer,
               'is_maintainer': self.is_maintainer}
        return ret

    def to_details_dict(self):
        ret = self.to_info_dict()
        ret['last_active_date'] = format_date(self.last_active_date)
        ret['created_by'] = self.created_by
        return ret


class Series(Base):
    __tablename__ = 'series'
    # defaults: wlm, unofficial
    id = Column(Integer, primary_key=True)

    name = Column(String(255), index=True)
    description = Column(Text)
    url = Column(Text)

    status = Column(String(255), index=True)  # active, cancelled
    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    campaigns = relationship('Campaign', back_populates='series')

    def to_details_dict(self):
        return {'id': self.id,
                'name': self.name,
                'url': self.url,
                'description': self.description,
                'status': self.status}


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey('series.id'), index=True)

    name = Column(String(255), index=True)
    # open/close can be used to select/verify that images were
    # actually uploaded during the contest window
    open_date = Column(DateTime)
    close_date = Column(DateTime)

    url = Column(Text)
    status = Column(String(255), index=True)  # active, cancelled, finalized
    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    rounds = relationship('Round', back_populates='campaign')
    series = relationship('Series')
    results_summary = relationship('RoundResultsSummary')
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
               'close_date': format_date(self.close_date),
               'status': self.status}
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
    name = Column(String(255), index=True)
    description = Column(Text)
    directions = Column(Text)
    open_date = Column(DateTime)
    close_date = Column(DateTime)
    # active, paused, cancelled, finalized
    status = Column(String(255), index=True)
    vote_method = Column(String(255))
    quorum = Column(Integer)

    config = Column(JSONEncodedDict, default=DEFAULT_ROUND_CONFIG)
    deadline_date = Column(TIMESTAMP)

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    campaign_id = Column(Integer, ForeignKey('campaigns.id'), index=True)
    campaign_seq = Column(Integer)

    campaign = relationship('Campaign', back_populates='rounds')

    round_jurors = relationship('RoundJuror')
    jurors = association_proxy('round_jurors', 'user',
                               creator=lambda u: RoundJuror(user=u))

    round_entries = relationship('RoundEntry')
    entries = association_proxy('round_entries', 'entry',
                                creator=lambda e: RoundEntry(entry=e))

    @property
    def show_stats(self):
        if self.config is None:
            return None
        return self.config.get('show_stats')

    @show_stats.setter
    def show_stats(self, value):
        if self.config is None:
            self.config = {}
        self.config['show_stats'] = value

    def check_closability(self):
        task_count = self._get_task_count()
        open_task_count = self._get_open_task_count()
        if open_task_count == 0 and task_count:
            return True
        return False

    def _get_rdb_session(self):
        rdb_session = inspect(self).session
        if not rdb_session:
            # TODO: just make a session
            raise RuntimeError('cannot get counts for detached Round')
        return rdb_session


    def _get_open_task_count(self, rdb_session=None):
        if not rdb_session:
            rdb_session = self._get_rdb_session()
        ret = (rdb_session.query(Vote)
                          .filter(Vote.round_entry.has(round_id=self.id),
                                  Vote.status == ACTIVE_STATUS)
                          .count())
        return ret

    def _get_task_count(self, rdb_session=None):
        if not rdb_session:
            rdb_session = self._get_rdb_session()
        ret = (rdb_session.query(Vote)
                          .filter(Vote.round_entry.has(round_id=self.id),
                                  Vote.status != CANCELLED_STATUS)
                          .count())
        return ret

    def get_count_map(self):
        # TODO TODO TODO
        # when more info is needed, can get session with
        # inspect(self).session (might be None if not attached), only
        # disadvantage is that user is not available to do permissions
        # checking.
        rdb_session = self._get_rdb_session()
        re_count = len(self.round_entries)

        open_task_count = self._get_open_task_count(rdb_session=rdb_session)
        task_count = self._get_task_count(rdb_session=rdb_session)
        cancelled_task_count = rdb_session.query(Vote)\
                                     .filter(Vote.round_entry.has(round_id=self.id),
                                             Vote.status == CANCELLED_STATUS)\
                                     .count()
        dq_entry_count = rdb_session.query(RoundEntry)\
                                    .filter_by(round_id=self.id)\
                                    .filter(RoundEntry.dq_reason != None)\
                                    .count()
        all_mimes = rdb_session.query(Entry.mime_minor)\
                                    .join(RoundEntry)\
                                    .distinct(Entry.mime_minor)\
                                    .filter_by(round_id=self.id)\
                                    .filter(RoundEntry.dq_reason == None)\
                                    .all()

        if task_count:
            percent_open = round((100.0 * open_task_count) / task_count, 3)
        else:
            percent_open = 0.0

        return {'total_round_entries': re_count,  # TODO: sync with total_entries
                'total_tasks': task_count,
                'total_open_tasks': open_task_count,
                'percent_tasks_open': percent_open,
                'total_cancelled_tasks': cancelled_task_count,
                'total_disqualified_entries': dq_entry_count,
                'total_uploaders': len(self.get_uploaders()),
                'all_mimes': all_mimes}

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
               'config': self.config,
               'show_stats': self.show_stats,
               'round_sources': []}
        return ret

    def to_details_dict(self):
        ret = self.to_info_dict()
        ret['is_closable'] = self.check_closability()
        ret['campaign'] = self.campaign.to_info_dict()
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

    @property
    def skip(self):
        skip = self.flags.get('skip')
        return skip

    def get_count_map(self):
        rdb_session = inspect(self).session
        if not rdb_session:
            # TODO: just make a session
            raise RuntimeError('cannot get counts for detached Round')
        task_count = rdb_session.query(Vote)\
                                .filter(Vote.round_entry.has(round_id=self.round_id),
                                        Vote.user_id == self.user_id,
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
    upload_user_id = Column(Integer, index=True)
    upload_user_text = Column(String(255), index=True)
    upload_date = Column(DateTime, index=True)

    # TODO: img_sha1/page_touched for updates?
    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    faves = relationship('Favorite')
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

    def to_export_dict(self):
        ret = {'img_name': self.name,
               'img_major_mime': self.mime_major,
               'img_minor_mime': self.mime_minor,
               'img_width': self.width,
               'img_height': self.height,
               'img_user': self.upload_user_id,
               'img_user_text': self.upload_user_text,
               'img_timestamp': format_date(self.upload_date)}
        return ret


class RoundEntry(Base):
    __tablename__ = 'round_entries'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('entries.id'), index=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), index=True)
    round_source_id = Column(Integer, ForeignKey('round_sources.id'), index=True)

    dq_user_id = Column(Integer, ForeignKey('users.id'), index=True)
    dq_reason = Column(String(255))  # in case it's disqualified
    # examples: too low resolution, out of date range
    # TODO: dq_date?
    flags = Column(JSONEncodedDict)

    entry = relationship(Entry, back_populates='entered_rounds')
    round = relationship(Round, back_populates='round_entries')
    votes = relationship('Vote', back_populates='round_entry')
    round_source = relationship('RoundSource')
    flaggings = relationship('Flag')

    def to_dq_details(self):
        ret = {'entry': self.entry.to_details_dict(),
               'dq_reason': self.dq_reason,
               'dq_user_id': self.dq_user_id}
        return ret

    def to_export_dict(self):
        entry = self.entry.to_export_dict()
        entry['source_method'] = self.round_source.method
        entry['source_params'] = json.dumps(self.round_source.params)
        return entry


round_entries_t = RoundEntry.__table__


class RoundSource(Base):
    __tablename__ = 'round_sources'

    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    method = Column(String(255), index=True)
    params = Column(JSONEncodedDict)
    dq_params = Column(JSONEncodedDict)

    create_date = Column(TIMESTAMP, server_default=func.now())
    user = relationship('User')

    flags = Column(JSONEncodedDict)


class Flag(Base):
    __tablename__ = 'flags'

    id = Column(Integer, primary_key=True)
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    reason = Column(Text)

    round_entry = relationship('RoundEntry', back_populates='flaggings')

    create_date = Column(TIMESTAMP, server_default=func.now())
    user = relationship('User')

    flags = Column(JSONEncodedDict)

    def to_details_dict(self):
        ret = {'round': self.round_entry.round.id,
               'entry_id': self.round_entry.entry.id,
               'entry_name': self.round_entry.entry.name,
               'user': self.user.username,
               'reason': self.reason,
               'date': format_date(self.create_date)}
        return ret


class Favorite(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('entries.id'), index=True)
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'), index=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    status = Column(String(255), index=True)  # active, cancelled

    user = relationship('User')
    campaign = relationship('Campaign')
    round_entry = relationship('RoundEntry')
    entry = relationship('Entry')

    create_date = Column(TIMESTAMP, server_default=func.now())
    modified_date = Column(DateTime)

    flags = Column(JSONEncodedDict)

    def to_details_dict(self):
        ret = self.entry.to_details_dict()
        ret['fave_date'] = format_date(self.create_date)
        if self.modified_date:
            ret['fave_date'] = format_date(self.modified_date)
        return ret


class Vote(Base):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'), index=True)

    value = Column(Float)
    status = Column(String(255), index=True)  # active, cancelled, complete

    user = relationship('User', back_populates='ratings')
    round_entry = relationship('RoundEntry', back_populates='votes')

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

    def check_fave(self):
        rdb_session = inspect(self).session
        # TODO: check, is this slow?
        faves = (rdb_session.query(Favorite)
                    .filter_by(entry_id=self.entry.id,
                               user_id=self.user.id,
                               status=ACTIVE_STATUS)
                    .all())
        return len(faves) > 0


    def to_info_dict(self):
        info = {'id': self.id,
                'name': self.entry.name,
                'user': self.user.username,
                'value': self.value,
                'date': format_date(self.modified_date),
                'round_id': self.round_entry.round_id,
                'is_fave': self.check_fave()}
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

    round_id = Column(Integer, ForeignKey('rounds.id'), index=True)
    round = relationship('Round')
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), index=True)
    campaign = relationship('Campaign', back_populates='results_summary')

    summary = Column(JSONEncodedDict)
    status = Column(String(255), index=True)  # private, public
    language = Column(String(255))

    version = Column(String(255))

    create_date = Column(TIMESTAMP, server_default=func.now())
    modified_date = Column(DateTime)

    def to_dict(self):
        ret = {'campaign_id': self.campaign_id,
               'campaign_name': self.campaign.name,
               'date': format_date(self.modified_date),
               'version': self.version}
        return ret


class AuditLogEntry(Base):
    __tablename__ = 'audit_log_entries'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), index=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), index=True)
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'), index=True)

    role = Column(String(255))
    action = Column(String(255))
    message = Column(Text)

    flags = Column(JSONEncodedDict)

    create_date = Column(TIMESTAMP, server_default=func.now(), index=True)

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


class PublicDAO(object):
    def __init__(self, rdb_session):
        self.rdb_session = rdb_session

    def query(self, *a, **kw):
        "a call-through to the underlying session.query"
        return self.rdb_session.query(*a, **kw)

    def get_series(self, series_id):
        series = (self.query(Series)
                  .filter_by(id=series_id)
                  .all())
        return series

    def get_all_series(self):
        series = (self.query(Series)
                  .filter_by(status=ACTIVE_STATUS)
                  .all())
        return series

    def get_report(self, campaign_id):
        summary = (self.query(RoundResultsSummary)
                   .filter_by(campaign_id=campaign_id,
                              status=PUBLISHED_STATUS)
                   .one_or_none())
        return summary

    def get_all_reports(self):
        reports = (self.query(RoundResultsSummary)
                   .filter_by(status=PUBLISHED_STATUS)
                   .all())
        return reports

    def _get_entry_by_name(self, entry_name):
        entry = (self.query(Entry)
                 .filter_by(name=entry_name)
                 .one_or_none())
        if not entry:
            raise DoesNotExist('no entry named %s' % entry_name)
        return entry

    def get_public_entry_info(self, entry_name):
        entry = self._get_entry_by_name(entry_name)
        ret = entry.to_details_dict()
        ret['campaigns'] = []
        round_entries = entry.entered_rounds
        for round_entry in round_entries:
            campaign_id = round_entry.round.campaign.id,
            disqualified = False
            results_published = False
            if campaign_id in [c['campaign_id'] for c in ret['campaigns']]:
                # Only need the first round in a campaign
                continue
            if round_entry.dq_reason:
                disqualified = True  # Should montage let people see
                                     # if their photo was dq'ed?
            summary = round_entry.round.campaign.results_summary
            if summary:
                summary = summary[0]
                results_published = True  # If it's published, you can
                                          # visit the campaign report
                                          # to see the results
                '''
                # TODO: show the ranking, if it's a winner?
                winners = [(e['entry']['name'],
                            e['ranking']) for e in results['winners']]
                '''
            re_info = {'campaign_id': campaign_id,
                       'campaign_name': round_entry.round.campaign.name,
                       'campaign_status': round_entry.round.campaign.status,
                       'campaign_results_published': results_published,
                       'disqualified': disqualified,
                       'source': round_entry.round_source.params}
            ret['campaigns'].append(re_info)
        return ret


class UserDAO(PublicDAO):
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

    def _get_any_campaign(self, campaign_id):
        campaign = (self.query(Campaign)
                        .filter_by(id=campaign_id)
                        .one_or_none())
        if not campaign:
            raise DoesNotExist('campaign %s does not exist' % campaign_id)
        return campaign

    def _get_every_campaign(self):
        campaigns = (self.query(Campaign)
                         .all())
        return campaigns

    def _get_any_round(self, round_id):
        rnd = (self.query(Round)
                   .filter_by(id=round_id)
                   .one_or_none())
        if not rnd:
            raise DoesNotExist('round %s does not exist' % round_id)
        return rnd

    def get_campaign(self, campaign_id):
        if self.user.is_maintainer:
            return self._get_any_campaign(campaign_id)
        campaign = self.query(Campaign)\
                       .filter(
                           Campaign.coords.any(username=self.user.username))\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        if not campaign:
            raise Forbidden('not a coordinator on campaign %s' % campaign_id)
        return campaign

    def get_all_campaigns(self):
        if self.user.is_maintainer:
            return self._get_every_campaign()
        campaigns = self.query(Campaign)\
                        .filter(
                            Campaign.coords.any(username=self.user.username))\
                        .all()
        user = self.user
        if not (campaigns or user.is_organizer or user.is_maintainer):
            raise Forbidden('not a coordinator on any campaigns')
        return campaigns

    def get_round(self, round_id):
        if self.user.is_maintainer:
            return self._get_any_round(round_id)
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
        if type(campaign) is not Campaign:
            raise InvalidAction('cannot load campaign')
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

    def get_round_entries(self, round_id):
        round_entries = (self.query(RoundEntry)
                         .filter_by(round_id=round_id,
                                    dq_reason=None)
                         .all())
        return round_entries

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

    def get_grouped_flags(self, round_id):
        flagged_entries = (self.query(RoundEntry)
                           .filter_by(round_id=round_id)
                           .join(RoundEntry.flaggings)
                           .group_by(RoundEntry)
                           .order_by(func.count(RoundEntry.flaggings).desc())
                           .all())
        return flagged_entries

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
                     vote_method, jurors, deadline_date, config=None, show_stats=None):
        if self.campaign.active_round:
            raise InvalidAction('can only create one active/paused round at a'
                                ' time. cancel or complete your existing'
                                ' rounds before trying again')
        config = config or {}
        jurors = [self.get_or_create_user(j, 'juror', campaign=self.campaign)
                  for j in set(jurors)]

        if type(deadline_date) is not datetime.datetime:
            deadline_date = js_isoparse(deadline_date)

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
        if show_stats is not None:
            rnd.show_stats = show_stats

        self.rdb_session.add(rnd)
        self.rdb_session.flush()
        j_names = [j.username for j in jurors]
        msg = ('%s created %s round "%s" (#%s) with jurors %r for'
               ' campaign "%s"' % (self.user.username, vote_method,
                                   rnd.name, rnd.id, j_names, self.campaign.name))
        self.log_action('create_round', round=rnd, message=msg)
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
        show_stats = round_dict.get('show_stats')
        if show_stats is not None:
            rnd.show_stats = show_stats

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

    def disqualify(self, round_id, entry_id, reason=None):
        rnd = self.get_round(round_id)
        if rnd.status != PAUSED_STATUS:
            raise InvalidAction('round must be paused to disqualify files')
        if not reason:
            reason = 'no reason specified'
        round_entry = (self.query(RoundEntry)
                       .filter_by(round_id=round_id)
                       .join(Entry)
                       .filter(Entry.id == entry_id,
                               RoundEntry.dq_reason == None)
                       .one_or_none())
        if not round_entry:
            raise InvalidAction('cannot disqualify this entry')
        cancel_date = datetime.datetime.utcnow()
        round_entry.dq_reason = ('specifically disqualified by %s (%s)'
                                 % (self.user.username, reason))
        round_entry.dq_user_id = self.user.id
        for vote in round_entry.votes:
            vote.status = CANCELLED_STATUS
            vote.modified_date = cancel_date
        msg = ('%s manually disqualified entry %s in round %s (%s)'
               % (self.user.username, entry_id, round_id, reason))
        self.log_action('disqualify', round_id=round_id, message=msg)
        return round_entry

    def requalify(self, round_id, entry_id, reason=None):
        rnd = self.get_round(round_id)
        requalify_date = datetime.datetime.utcnow()
        if rnd.status != PAUSED_STATUS:
            raise InvalidAction('round must be paused to requalify files')
        if not reason:
            reason = 'no reason specified'
        round_entry = (self.query(RoundEntry)
                       .filter_by(round_id=round_id)
                       .join(Entry)
                       .filter(Entry.id == entry_id,
                               RoundEntry.dq_reason != None)
                       .one_or_none())
        if not round_entry:
            raise InvalidAction('cannot requalify this entry')
        round_entry.dq_reason = None
        round_entry.dq_user_id = None
        for vote in round_entry.votes:
            vote.status = ACTIVE_STATUS
            vote.modified_date = requalify_date
        msg = ('%s manually requalified entry %s in round %s (%s)'
               % (self.user.username, entry_id, round_id, reason))
        self.log_action('requalify', round_id=round_id, message=msg)
        return round_entry

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

            for vote in r_ent.votes:
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

            for vote in r_ent.votes:
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
        if ENV_NAME == 'dev':
            source = 'remote'
        else:
            source = 'local'
        entries = loaders.load_category(cat_name, source=source)
        entries, new_entry_count = self.add_entries(rnd, entries)

        msg = ('%s loaded %s entries from category (%s), %s new entries added'
               % (self.user.username, len(entries), cat_name, new_entry_count))
        self.log_action('add_entries', message=msg, round=rnd)

        return entries

    def add_entries_by_name(self, round_id, file_names):
        rnd = self.user_dao.get_round(round_id)
        if ENV_NAME == 'dev':
            source = 'remote'
        else:
            source = 'local'
        entries = loaders.load_by_filename(file_names, source=source)
        entries, new_entry_count = self.add_entries(rnd, entries)

        msg = ('%s loaded %s entries from filenames, %s new entries added'
               % (self.user.username, len(entries), new_entry_count))
        self.log_action('add_entries', message=msg, round=rnd)

        return entries

    def add_entries_from_csv(self, round_id, csv_url):
        # NOTE: this no longer creates RoundEntries, use
        # add_round_entries to do this.
        rnd = self.user_dao.get_round(round_id)
        if ENV_NAME == 'dev':
            source = 'remote'
        else:
            source = 'local'
        try:
            entries, warnings = loaders.get_entries_from_csv(csv_url,
                                                             source=source)
        except ValueError as e:
            raise InvalidAction('unable to load csv "%s"' % csv_url)

        entries, new_entry_count = self.add_entries(rnd, entries)

        msg = ('%s loaded %s entries from csv (%r), %s new entries added'
               % (self.user.username, len(entries), csv_url, new_entry_count))
        self.log_action('add_entries', message=msg, round=rnd)

        return entries, warnings

    def get_round_sources(self, round_id, import_method):
        round_sources = (self.query(RoundSource)
                         .filter_by(round_id=round_id,
                                    method=import_method)
                         .all())
        return round_sources

    def get_or_create_round_source(self, round_id, import_method,
                                  params, dq_params=None):
        existing_sources = self.get_round_sources(round_id, import_method)
        if existing_sources:
            for existing_source in existing_sources:
                if existing_source.params == params:
                    return existing_source
        round_source = RoundSource(method=import_method,
                                   params=params,
                                   dq_params=dq_params,
                                   round_id=round_id,
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

    def add_round_entries(self, round_id, entries, method, params):
        rnd = self.user_dao.get_round(round_id)
        if rnd.status != PAUSED_STATUS:
            raise InvalidAction('round must be paused to add new entries')
        existing_names = (self.rdb_session.query(Entry.name)
                          .join(RoundEntry)
                          .filter_by(round=rnd)
                          .all())
        existing_names = set([n[0] for n in existing_names])
        new_entries = [e for e
                       in unique_iter(entries, key=lambda e: e.name)
                       if e.name not in existing_names]
        if not new_entries:
            return dict()
        round_source = self.get_or_create_round_source(round_id, method, params)
        self.rdb_session.flush()
        for new_entry in new_entries:
            new_round_entry = RoundEntry(entry_id=new_entry.id,
                                         round_id=round_id,
                                         round_source_id=round_source.id)
            self.rdb_session.add(new_round_entry)
        msg = ('%s added %s round entries, %s new'
               % (self.user.username, len(entries), len(new_entries)))
        if method:
            msg += ' (from %s)' % (method,)
        self.log_action('add_round_entries', message=msg, round=rnd)
        new_entry_stats = {'round_id': rnd.id,
                           'new_entry_count': len(entries),
                           'new_round_entry_count': len(new_entries),
                           'total_entries': len(rnd.entries)}
        return new_entry_stats

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

    def get_reviews_table(self, round_id):
        rnd = self.get_round(round_id)
        votes = self.get_all_reviews(round_id)
        return votes

    def make_vote_table(self, round_id):
        rnd = self.get_round(round_id)
        if rnd.vote_method == 'ranking':
            all_ratings = self.get_all_rankings(round_id)
        else:
            all_ratings = self.get_all_ratings(round_id)
        all_tasks = self.get_all_tasks(round_id)

        results_by_name = defaultdict(dict)
        ratings_dict = {r.id: r.value for r in all_ratings}

        for (task, entry) in all_tasks:
            rating = ratings_dict.get(task.id, {})
            filename = entry.name
            username = task.user.username

            if task.status == COMPLETED_STATUS:
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

        rnd.close_date = datetime.datetime.utcnow()
        rnd.status = FINALIZED_STATUS
        # rnd.config['ranking_method'] = method

        summary = self.build_campaign_report()

        result_summary = RoundResultsSummary(round_id=round_id,
                                             campaign_id=rnd.campaign.id,
                                             summary=summary)
        self.rdb_session.add(result_summary)
        self.rdb_session.flush()
        msg = ('%s finalized round "%s" (#%s) and created round results summary %s' %
               (self.user.username, rnd.name, rnd.id, result_summary.id))
        self.log_action('finalize_ranking_round', round=rnd, message=msg)
        return result_summary

    def finalize_campaign(self):
        last_rnd = self.campaign.rounds[-1] if len(self.campaign.rounds) > 0 else None
        self.campaign.status = FINALIZED_STATUS
        #self.campaign.close_date = datetime.datetime.utcnow() # TODO
        if last_rnd:
            msg = ('%s finalized campaign %r (#%s) with %s round "%s"'
                   % (self.user.username, self.campaign.name, self.campaign.id,
                      last_rnd.vote_method, last_rnd.name))
        else:
            msg = ('%s finalized campaign %r (#%s)'
                   % (self.user.username, self.campaign.name, self.campaign.id,))
        self.log_action('finalize_campaign', campaign=self.campaign, message=msg)
        return self.campaign

    def get_campaign_report(self):
        if self.campaign.status != FINALIZED_STATUS:
            raise Forbidden('cannot open report for campaign %s' % self.campaign.id)
        if self.user.is_maintainer:
            summary = (self.query(RoundResultsSummary)
                           .filter_by(campaign_id=self.campaign.id)
                           .one_or_none())
        else:
            summary = (self.query(RoundResultsSummary)
                           .filter(RoundResultsSummary.campaign.has(
                              Campaign.coords.any(username=self.user.username)))
                           .filter_by(campaign_id=self.campaign.id)
                           .one_or_none())
        return summary

    def get_audit_log(self, limit=100, offset=0,
                      round_id=None, log_id=None, action=None):
        audit_log_q = (self.query(AuditLogEntry)
                           .order_by(AuditLogEntry.create_date.desc())
                           .filter_by(campaign_id=self.campaign.id))
        if round_id:
            audit_log_q = audit_log_q.filter_by(round_id=round_id)
        if log_id:
            audit_log_q = audit_log_q.filter_by(id=log_id)
        if action:
            audit_log_q = audit_log_q.filter_by(action=action)
        audit_logs = audit_log_q.limit(limit).offset(offset).all()
        return audit_logs

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

    def get_all_ratings(self, round_id):
        results = self.query(Vote)\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(RoundEntry.round_id == round_id,
                              RoundEntry.dq_user_id == None,
                              Vote.status == COMPLETED_STATUS)\
                      .all()
        return results

    # do we need this?
    def get_all_rankings(self, round_id):
        results = self.query(Vote)\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(RoundEntry.round_id == round_id,
                              RoundEntry.dq_user_id == None,
                              Vote.status == COMPLETED_STATUS)\
                      .all()
        return results

    def get_all_reviews(self, round_id):
        results = (self.query(Vote)
                       .join(RoundEntry)
                       .join(Entry)
                       .filter(RoundEntry.round_id == round_id,
                               RoundEntry.dq_user_id == None,
                               Vote.status != CANCELLED_STATUS,
                               Vote.flags != {})
                       .all())
        results = [r for r in results if r.flags.get('review')]
        return results

    def get_all_tasks(self, round_id):
        results = self.query(Vote, Entry)\
                      .options(joinedload('user'))\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(RoundEntry.round_id == round_id,
                              RoundEntry.dq_user_id == None,
                              Vote.status != CANCELLED_STATUS)\
                      .all()
        return results

    def get_disqualified(self, round_id):
        results = self.query(RoundEntry)\
                      .options(joinedload('entry'))\
                      .filter_by(round_id=round_id)\
                      .filter(RoundEntry.dq_user_id != None)\
                      .all()

        return results

    def add_coordinator(self, username):
        user = self.get_or_create_user(username, 'coordinator',
                                       campaign=self.campaign)
        if user in self.campaign.coords:
            raise InvalidAction('user is already a coordinator')
        self.campaign.coords.append(user)
        self.rdb_session.add(user)

        msg = ('%s added %s as a coordinator of campaign "%s"'
               % (self.user.username, user.username, self.campaign.name))
        self.log_action('add_coordinator', campaign_id=self.campaign.id,
                        message=msg, role='organizer')
        return user

    def remove_coordinator(self, username):
        removed = None
        for user in self.campaign.coords:
            if user.username == username:
                self.campaign.coords.remove(user)
                removed = user
        if not removed:
            raise InvalidAction('user %s is not a coordinator' % username)
        msg = ('%s removed %s as a coordinator on campaign "%s" (#%s)'
               % (self.user.username, username, self.campaign.name, self.campaign.id))
        self.log_action('remove_coordinator', campaign=self.campaign, message=msg,
                        role='organizer')
        return removed

    def modify_jurors(self, round_id, new_jurors, force_balance=False):
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

        if len(new_jurors) == len(old_jurors) and not force_balance:
            added_juror = list(set(new_jurors) - set(old_jurors))[0]
            removed_juror = list(set(old_jurors) - set(new_jurors))[0]
            res = swap_tasks(self.rdb_session, rnd, added_juror, removed_juror)
        else:
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

        rnd = self.get_round(round_id)

        old_quorum = rnd.quorum

        if not new_quorum:
            raise InvalidAction('must specify new quorum')

        if new_quorum <= old_quorum:
            raise NotImplementedResponse('currently we do not support quorum '
                                         'decreases. current quorum is %r, got %r'
                                         % (old_quorum, new_quorum))

        jurors = self.get_active_jurors(rnd.id)
        session = self.rdb_session

        rnd_stats = rnd.to_details_dict()
        if not rnd_stats['stats']['total_tasks']:
            create_initial_tasks(session, rnd)

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

    def build_campaign_report(self):
        campaign = self.campaign
        # assert campaign.status is FINALIZED_STATUS

        ret = {}
        start_time = time.time()

        ret["campaign"] = campaign.to_info_dict()

        ret["rounds"] = [r.to_details_dict() for r in campaign.rounds
                         if r.status == FINALIZED_STATUS]

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

    def update_report(self, report_dict):
        report_dict['modified_date'] = datetime.datetime.utcnow()
        ret = (self.query(RoundResultsSummary)
               .filter_by(campaign_id=self.campaign.id)
               .update(report_dict))
        return ret

    def publish_report(self):
        report = {'status': PUBLISHED_STATUS}
        ret = self.update_report(report)
        return ret

    def unpublish_report(self):
        report = {'status': PRIVATE_STATUS}
        ret = self.update_report(report)
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

    def _get_campaigns_named(self, name):
        campaigns = (self.query(Campaign)
                     .filter_by(name=name)
                     .all())
        return campaigns

    def create_series(self, name, description, url, status=None):
        if not status or status not in VALID_STATUS:
            status = ACTIVE_STATUS
        new_series = Series(name=name,
                            description=description,
                            url=url,
                            status=status)
        self.rdb_session.add(new_series)
        self.rdb_session.flush()
        msg = '%s created series %s (%s)' % (self.user.username,
                                              new_series.name,
                                              new_series.id)
        self.log_action('create_series', message=msg, role='organizer')
        return new_series

    def edit_series(self, series_id, series_dict):
        series = (self.query(Series)
                  .filter_by(id=series_id)
                  .update(series_dict))
        msg = ('%s edited these columns in series %s: %r'
               % (self.user.username, series_id,
                  series_dict.keys()))
        self.log_action('edit_series', message=msg, role='organizer')
        return series

    def create_campaign(self, name, url, open_date, close_date, series_id, coords=None):
        other_campaigns = self._get_campaigns_named(name)

        if type(open_date) is not datetime.datetime:
            open_date = js_isoparse(open_date)

        if type(close_date) is not datetime.datetime:
            close_date = js_isoparse(close_date)

        if other_campaigns:
            raise InvalidAction('A campaign named %s already exists' % name)
        if not coords:
            coords = [self.user]

        campaign = Campaign(name=name,
                            open_date=open_date,
                            close_date=close_date,
                            status=ACTIVE_STATUS,
                            series_id=series_id,
                            url=url,
                            coords=coords)
        self.rdb_session.add(campaign)
        self.rdb_session.flush()  # to get a campaign id
        msg = '%s created campaign "%s"' % (self.user.username, campaign.name)
        self.log_action('create_campaign', campaign=campaign, message=msg,
                        role='organizer')
        return campaign

    def cancel_campaign(self, campaign_id):
        campaign = self.user_dao.get_campaign(campaign_id)
        coord_dao = CoordinatorDAO(self.user_dao, campaign)
        rounds = (self.query(Round)
                  .filter(Round.campaign_id == campaign_id)
                  .all())
        campaign.status = CANCELLED_STATUS
        for rnd in rounds:
            coord_dao.cancel_round(rnd.id)
        msg = '%s cancelled campaign "%s" and %s rounds' %\
              (self.user.username, campaign.name, len(rounds))
        self.log_action('cancel_campaign', campaign=campaign, message=msg)

    def get_user_list(self):
        all_camps = self.user_dao._get_every_campaign()
        orgs = (self.query(User)
                    .filter_by(is_organizer=True)
                    .all())
        ret = {'maintainers': [],
               'organizers': [o.to_details_dict() for o in orgs],
               'campaigns': []}

        for username in MAINTAINERS:
            user = (self.query(User)
                        .filter_by(username=username)
                        .one_or_none())
            if not user:
                continue
            ret['maintainers'].append(user.to_details_dict())

        for camp in all_camps:
            coords = [u.to_details_dict() for u in camp.coords]
            ret['campaigns'].append({'id': camp.id,
                                     'name': camp.name,
                                     'coorinators': coords})
        return ret


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

    def get_audit_log(self, limit=100, offset=0, campaign_id=None,
                      round_id=None, log_id=None, action=None):
        audit_log_q = (self.query(AuditLogEntry)
                           .order_by(AuditLogEntry.create_date.desc()))
        if campaign_id:
            audit_log_q = audit_log_q.filter_by(campaign_id=campaign_id)
        if round_id:
            audit_log_q = audit_log_q.filter_by(round_id=round_id)
        if log_id:
            audit_log_q = audit_log_q.filter_by(id=log_id)
        if action:
            audit_log_q = audit_log_q.filter_by(action=action)
        audit_logs = audit_log_q.limit(limit).offset(offset).all()
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
            raise InvalidAction('user %s is not present in the system' % username)
        user.is_organizer = False
        msg = ('%s removed %s as an organizer' % (self.user.username, username))
        self.log_action('remove_organizer', message=msg, role='maintianer')
        return user

    def get_campaign_by_series(self, series_name, start_id=0):
        series = lookup_series(self.rdb_session, series_name)
        if series is None:
            raise ValueError('unrecognized series name: %r' % series)
        qs = self.query(Campaign).filter_by(series=series)
        if start_id:
            qs = qs.filter(Campaign.id > start_id)
        qs = qs.order_by(Campaign.id)
        return qs.first()


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


def ensure_series(rdb_session):
    user = lookup_user(rdb_session, MAINTAINERS[0])
    user_dao = UserDAO(rdb_session, user)
    org_user = OrganizerDAO(user_dao)
    series = load_default_series()
    name = series['name']
    cur_series = lookup_series(rdb_session, name=name)
    ret = None
    if not cur_series:
        ret = org_user.create_series(name=series['name'],
                                     description=series['description'],
                                     url=series['url'],
                                     status=ACTIVE_STATUS)
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

    def _get_round_juror(self, round_id):
        round_juror = (self.query(RoundJuror)
                           .filter_by(user=self.user,
                                      round_id=round_id)
                           .one_or_none())
        return round_juror

    # Read methods
    def get_campaign(self, campaign_id):
        if self.user.is_maintainer:
            return self.user_dao._get_any_campaign(campaign_id)
        campaign = self.query(Campaign)\
                       .filter(Campaign.rounds.any(
                           Round.jurors.any(username=self.user.username)))\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        if not campaign:
            raise Forbidden('not a juror on campaign %s' % campaign_id)
        return campaign

    def get_round(self, round_id):
        if self.user.is_maintainer:
            return self.user_dao._get_any_round(round_id)
        rnd = self.query(Round)\
                  .filter(
                      Round.jurors.any(username=self.user.username),
                      Round.id == round_id)\
                  .one_or_none()
        if not rnd:
            raise Forbidden('not a juror for round %s' % round_id)
        return rnd

    def get_round_entry(self, round_id, entry_id):
        # Note, this doesn't check permissions. Are you really a juror
        # on this round?
        round_entry = (self.query(RoundEntry)
                       .filter_by(round_id=round_id,
                                  entry_id=entry_id)
                       .one_or_none())

        if not round_entry:
            raise DoesNotExist('round entry %s does not exist' % entry_id)
        return round_entry

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
        # TODO: remove offset once it's removed from the client
        task_query = (self.query(Vote)
                          .filter_by(user=self.user,
                                     status=ACTIVE_STATUS)
                          .filter(
                            Vote.round_entry.has(round_id=round_id))
                          .order_by(Vote.id))

        # Check if this round_juror has skipped any tasks
        round_juror = self._get_round_juror(round_id)
        skip = round_juror.skip

        if skip:
            tasks = (task_query.filter(Vote.id > skip)
                               .limit(num)
                               .offset(offset)
                               .all())
            if len(tasks) == num:
                return tasks
        else:
            tasks = []

        new_num = int(num) - len(tasks)
        tasks += task_query.limit(new_num).offset(offset).all()
        tasks = list(set(tasks))

        return tasks

    def get_faves(self, sort='desc', limit=10, offset=0):
        faves_query = (self.query(Favorite)
                            .filter_by(user=self.user,
                                        status=ACTIVE_STATUS))
        if sort == 'asc':
            faves_query = faves_query.order_by(
                            func.coalesce(Favorite.modified_date,
                            Favorite.create_date))
        else:
            faves_query = faves_query.order_by(
                            func.coalesce(Favorite.modified_date,
                            Favorite.create_date).desc())
        faves = faves_query.limit(limit).offset(0).all()
        return faves

    def get_ratings_from_round(self, round_id, num,
                               sort, order_by, offset=0):
        # all the filter fields but cancel_date are actually on Vote
        # already
        ratings_query = (self.query(Vote)\
                      .options(joinedload('round_entry'))
                      .filter(Vote.user == self.user,
                              Vote.status == COMPLETED_STATUS,
                              Vote.round_entry.has(round_id=round_id)))
        if order_by == 'value' and sort == 'desc':
            ratings_query = ratings_query.order_by(Vote.value.desc())
        elif order_by == 'value' and sort == 'asc':
            ratings_query = ratings_query.order_by(Vote.value)
        elif order_by == 'date' and sort == 'desc':
            ratings_query = ratings_query.order_by(Vote.modified_date.desc())
        else:
            ratings_query = ratings_query.order_by(Vote.modified_date)

        ratings = ratings_query.limit(num).offset(offset).all()

        if not ratings:
            raise Forbidden('no complete ratings')
        return ratings

    def get_rating_stats_from_round(self, round_id):
        ratings_query = (self.query(func.count(Vote.value).label('count'), Vote.value)\
                      .filter(Vote.user == self.user,
                              Vote.status == COMPLETED_STATUS,
                              Vote.round_entry.has(round_id=round_id))
                      .group_by(Vote.value))

        ratings = ratings_query.all()

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
        campaign_status = '_campaign_status'

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
                campaigns_t.c.status.label(campaign_status),
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
                                close_date=round_kwargs.pop(campaign_close_date),
                                status=round_kwargs.pop(campaign_status))

            round = Round(**round_kwargs)
            round.campaign = campaign

            total_tasks = rounds_to_total_tasks.get(round.id, 0)
            total_open_tasks = rounds_to_total_open_tasks.get(round.id, 0)

            results.append(
                (round,
                 self._build_round_stats(
                     re_count, total_tasks, total_open_tasks),
                 self.get_ballot(round.id)),
            )
        return results

    def get_ballot(self, round_id):
        results = (self.query(Vote, Vote.value)
                       .filter(Vote.round_entry.has(round_id=round_id),
                               Vote.status == COMPLETED_STATUS,
                               Vote.user == self.user)
                       .all())

        rating_ctr = Counter([r[1] for r in results])

        return dict(rating_ctr)

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

    def edit_rating(self, task, value, review=''):
        if not task.user == self.user:
            raise PermissionDenied()
        now = datetime.datetime.utcnow()
        rating = self.rdb_session.query(Vote)\
                                 .filter_by(id=task.id)\
                                 .first()
        rating.value = value
        if review:
            rating.flags['review'] = review
        rating.modified_date = now
        rating.status = COMPLETED_STATUS
        return rating

    def skip_voting(self, vote_id, round_id=None):
        vote = (self.query(Vote)
                    .filter_by(id=vote_id,
                               user=self.user)
                    .one_or_none())
        if not vote:
            return InvalidAction('vote %s does not exist for this user' % vote_id)
        if not round_id:
            round_id = vote.round_entry.round_id

        round_juror = self._get_round_juror(round_id)

        round_juror.flags['skip'] = vote_id
        self.rdb_session.add(round_juror)
        return

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

    def fave(self, round_id, entry_id):
        existing_fave = (self.query(Favorite)
                             .filter_by(entry_id=entry_id,
                                        user=self.user)
                             .first())  # there should be one
        if existing_fave:
            existing_fave.modified_date = datetime.datetime.utcnow()
            existing_fave.status = ACTIVE_STATUS
            return

        round_entry = self.get_round_entry(round_id, entry_id)
        fave = Favorite(entry_id=round_entry.entry.id,
                       round_entry_id = round_entry.id,
                       campaign_id=round_entry.round.campaign.id,
                       user=self.user,
                       status=ACTIVE_STATUS)
        self.rdb_session.add(fave)

    def unfave(self, round_id, entry_id):
        fave = (self.query(Favorite)
               .filter_by(entry_id=entry_id,
                          user=self.user)
               .filter(Favorite.round_entry.has(round_id=round_id))
               .one())
        fave.status = CANCELLED_STATUS
        fave.modified_date = datetime.datetime.utcnow()

    def flag(self, round_id, entry_id, reason=None):
        round_entry = self.get_round_entry(round_id, entry_id)
        flag = Flag(round_entry_id = round_entry.id,
                    user=self.user,
                    reason=reason)
        self.rdb_session.add(flag)


def lookup_user(rdb_session, username):
    user = rdb_session.query(User).filter_by(username=username).one_or_none()
    if user:
        return user
    user_id = get_mw_userid(username)
    user = rdb_session.query(User).filter_by(id=user_id).one_or_none()
    if not user:
        return user
    user.username = username  # update our local cache of the username
    return user


def lookup_series(rdb_session, name):
    series = (rdb_session.query(Series)
              .filter_by(name=name)
              .one_or_none())
    return series

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
                                           RoundEntry.votes == None)
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
                                           RoundEntry.votes == None)
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


def swap_tasks(session, rnd, new_juror, old_juror):
    # Transfer tasks from one juror to another

    votes_to_swap = (session.query(Vote)
                            .filter_by(status=ACTIVE_STATUS, user=old_juror)
                            .join(RoundEntry)
                            .filter_by(round=rnd).all())

    # TODO: should it check for files uploaded by the new juror?

    for vote in votes_to_swap:
        vote.user = new_juror

    session.flush()

    ret = {'reassigned_task_count': len(votes_to_swap),
           'task_count_mean': -1}

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
        elig_map[vote.round_entry].remove(vote.user)
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
