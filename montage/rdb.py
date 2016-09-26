# -*- coding: utf-8 -*-

# Relational database models for Montage
import json
import random
import itertools
from datetime import datetime
from math import ceil
from collections import Counter

from sqlalchemy import (Column,
                        String,
                        Integer,
                        Float,
                        Boolean,
                        DateTime,
                        TIMESTAMP,
                        Text,
                        ForeignKey)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy

from boltons.iterutils import chunked

from simple_serdes import DictableBase, JSONEncodedDict
from utils import get_mw_userid, PermissionDenied, DoesNotExist, InvalidAction

from loaders import get_csv_from_gist

Base = declarative_base(cls=DictableBase)


# Some basic display settings for now
DEFAULT_ROUND_CONFIG = json.dumps({'show_link': True,
                                   'show_filename': True,
                                   'show_resolution': True})

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

MAINTAINERS = ['MahmoudHashemi', 'Slaporte', 'Yarl']


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(255))

    last_login_date = Column(DateTime)
    create_date = Column(TIMESTAMP, server_default=func.now())
    is_organizer = Column(Boolean, default=False)

    flags = Column(JSONEncodedDict)

    created_by = Column(Integer, ForeignKey('users.id'))
    coordinated_campaigns = relationship('CampaignCoord', back_populates='user')
    campaigns = association_proxy('coordinated_campaigns', 'campaign',
                                  creator=lambda c: CampaignCoord(campaign=c))

    jurored_rounds = relationship('RoundJuror', back_populates='user')
    rounds = association_proxy('jurored_rounds', 'round',
                               creator=lambda r: RoundJuror(round=r))

    tasks = relationship('Task', back_populates='user')
    # update_date?

    def __init__(self, **kw):
        self.flags = kw.pop('flags', {})
        super(User, self).__init__(**kw)

    @property
    def is_maintainer(self):
        return self.username in MAINTAINERS


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))

    # open/close can be used to select/verify that images were
    # actually uploaded during the contest window
    open_date = Column(DateTime)
    close_date = Column(DateTime)

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    rounds = relationship('Round', back_populates='campaign')
    campaign_coords = relationship('CampaignCoord')
    coords = association_proxy('campaign_coords', 'user',
                               creator=lambda user: CampaignCoord(coord=user))


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
    status = Column(String(255))
    vote_method = Column(String(255))
    quorum = Column(Integer)
    # Should we just have some settings in json? yes. -mh
    config_json = Column(Text, default=DEFAULT_ROUND_CONFIG)

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)

    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    # increments for higher rounds within the same campaign
    # doesn't need to be in the db prolly
    campaign_seq = Column(Integer, default=1)
    campaign = relationship('Campaign', back_populates='rounds')

    round_jurors = relationship('RoundJuror')
    jurors = association_proxy('round_jurors', 'user',
                               creator=lambda u: RoundJuror(user=u))

    round_entries = relationship('RoundEntry')
    entries = association_proxy('round_entries', 'entry',
                                creator=lambda e: RoundEntry(entry=e))


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


class RoundEntry(Base):
    __tablename__ = 'round_entries'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('entries.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))

    dq_user_id = Column(Integer, ForeignKey('users.id'))
    dq_reason = Column(String(255))  # in case it's disqualified
    # examples: too low resolution, out of date range
    flags = Column(JSONEncodedDict)

    entry = relationship(Entry, back_populates='entered_rounds')
    round = relationship(Round, back_populates='round_entries')
    task = relationship('Task', back_populates='round_entry')
    rating = relationship('Rating', back_populates='round_entry')
    ranking = relationship('Ranking', back_populates='round_entry')

    def __init__(self, entry=None, round=None):
        if entry is not None:
            self.entry = entry
        if round is not None:
            self.round = round
        return


class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    value = Column(Float)

    round_entry = relationship('RoundEntry', back_populates='rating')

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)


class Ranking(Base):
    __tablename__ = 'rankings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    value = Column(Integer)

    round_entry = relationship('RoundEntry', back_populates='ranking')

    create_date = Column(TIMESTAMP, server_default=func.now())
    flags = Column(JSONEncodedDict)


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    round_entry_id = Column(Integer, ForeignKey('round_entries.id'))

    user = relationship('User', back_populates='tasks')
    round_entry = relationship('RoundEntry', back_populates='task')

    create_date = Column(TIMESTAMP, server_default=func.now())
    complete_date = Column(DateTime)
    cancel_date = Column(DateTime)

    entry = association_proxy('round_entry', 'entry',
                              creator=lambda e: RoundEntry(entry=e))


class ResultsSummary(Base):
    """# Results modeling

    This is more like a persistent cache. Results could be recomputed from
    the ratings/rankings.

    ## Campaign results

    (Same as last round results?)

    * Ranked winners
    * Total number of entries
    * Total number of votes
    * Credits (organizers, coordinators, jurors)

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

    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))

    summary = Column(JSONEncodedDict)

    create_date = Column(TIMESTAMP, server_default=func.now())


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

    def query(self, *a, **kw):
        "a call-through to the underlying session.query"
        return self.rdb_session.query(*a, **kw)

    def get_campaign_name(self, campaign_id):
        # TODO: check user permissions?
        campaign = self.query(Campaign).filter_by(Round.id == campaign_id).one()
        return campaign.name

    def get_round_name(self, round_id):
        # TODO: check user permissions?
        round = self.query(Round).filter_by(Round.id == round_id).one()
        return round.name

    def log_action(self, action, **kw):
        # TODO: file logging here too
        user_id = self.user.id
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
    def check_is_coord(self):
        pass

    def edit_campaign(self, campaign_id, campaign_dict):
        # TODO: confirm permissions in this query
        ret = self.rdb_session.query(Campaign)\
                              .filter_by(id=campaign_id)\
                              .update(campaign_dict)
        self.rdb_session.commit()

        return ret

    def create_round(self,
                     name,
                     quorum,
                     vote_method,
                     jurors,
                     campaign=None,
                     campaign_id=None):
        if not campaign and campaign_id:
            raise DoesNotExist('missing campaign object or campaign_id')

        if not campaign and campaign_id:
            campaign = self.get_camapign(campaign_id)

        if not campaign:
            raise DoesNotExist('campaign does not exist')

        rnd_jurors = []

        for juror_name in jurors:
            juror = self.add_juror(juror_name)
            rnd_jurors.append(juror)

        # TODO: campaign_seq, ie the rounds position within the campaign

        rnd = Round(name=name,
                    campaign=campaign,
                    quorum=quorum,
                    vote_method=vote_method,
                    jurors=rnd_jurors)

        self.rdb_session.add(rnd)
        self.rdb_session.commit()

        return rnd

    def edit_round(self, round_id, round_dict):
        # TODO: Confirm if dict keys are columns?

        # Some restrictions on editing round properties:
        # (these restrictions are enforced in the endpoint funcs)
        #
        #   - no reassignment required: name, description, directions,
        #     display_settings
        #   - reassignment required: quorum, active_jurors
        #   - not updateable: id, open_date, close_date, vote_method,
        #     campaign_id/seq
        ret = self.rdb_session.query(Round)\
                              .filter_by(id=round_id)\
                              .update(round_dict)

        self.rdb_session.commit()

        return ret

    def pause_round(self, round_id):
        rnd_status = {'status': 'paused'}
        query = self.edit_round(round_id, rnd_status)
        rnd = self.query(Round).filter(id=round_id).first()
        msg = '%s paused round "%s"' % (self.user.username, rnd.name)
        self.log_action('pause_round', round_id=round_id,
                        message=msg)
        return query

    def activate_round(self, round_id):
        rnd = self.get_round(round_id)
        tasks = create_initial_tasks(self.rdb_session, rnd)
        rnd_dict = {'status': 'active',
                    'open_date': datetime.now()}
        query = self.edit_round(round_id, rnd_dict)

        rnd = self.query(Round).filter(Round.id == round_id).first()
        msg = '%s activated round "%s"' % (self.user.username, rnd.name)
        self.log_action('activate_round', round_id=round_id,
                        message=msg)

        return tasks

    def close_round(self, round_id):
        pass

    def add_entries_from_cat(self):
        pass

    def add_entries_from_csv_gist(self, gist_url, round_id):
        rnd = self.get_round(round_id)

        if not rnd:
            raise DoesNotExist('round does not exist')
        entries = get_csv_from_gist(gist_url)

        commit_objs = []
        entry_chunks = chunked(entries, 200)

        for entry_chunk in entry_chunks:
            entry_names = [e.name for e in entry_chunk]
            db_entries = self.get_entries(entry_names)

            for entry in entry_chunk:
                db_entry = db_entries.get(entry.name)

                if db_entry:
                    entry = db_entry  # commit_objs.append(db_entry)
                else:
                    commit_objs.append(entry)

                round_entry = RoundEntry(entry=entry, round=rnd)
                commit_objs.append(round_entry)

        # self.rdb_session.bulk_save_objects(commit_objs)
        # Mystery: Why does this lead to a unique constraint failure
        # when adding new files?

        self.rdb_session.commit()
        return rnd

    def reassign(self, round_id, active_jurors):
        pass

    def add_juror(self, username):
        user = lookup_user(self.rdb_session, username=username)
        if not user:
            user_id = get_mw_userid(username)
            user = User(id=user_id,
                        username=username,
                        created_by=self.user.id)
            self.rdb_session.add(user)
            self.rdb_session.commit()
        return user

    def calculate_ratings_round(self, round_id):
        round_stats = self.get_round_stats(round_id)

        if round_stats['total_open_tasks']:
            raise InvalidAction('cannot close round with open tasks'
                                ' (%r outstanding)'
                                % round_stats['total_open_tasks'])

        ratings = []
        results = self.query(Rating, Entry,
                             func.avg(Rating.value).label('average'))\
                      .join(RoundEntry)\
                      .join(Entry)\
                      .filter(Rating.round_entry.has(round_id=round_id))\
                      .group_by(Rating.round_entry_id)\
                      .all()

        results.sort(key=lambda x: x[2], reverse=True)

        for rating in results:
            ratings.append((rating[1].name, rating[2], rating[1]))

        stats = Counter([r[1] for r in ratings])
        ret = {'ratings': ratings, 'stats': dict(stats)}
        return ret

    # Read methods
    def get_all_campaigns(self):
        campaigns = self.query(Campaign)\
                        .filter(
                            Campaign.coords.any(username=self.user.username))\
                        .all()
        return campaigns

    def get_campaign(self, campaign_id=None):
        campaign = self.query(Campaign)\
                       .filter(
                           Campaign.coords.any(username=self.user.username))\
                       .filter_by(id=campaign_id)\
                       .one_or_none()
        return campaign

    def get_round(self, round_id):
        round = self.query(Round)\
                    .filter(
                        Round.campaign.has(
                            Campaign.coords.any(username=self.user.username)))\
                    .filter_by(id=round_id)\
                    .one_or_none()
        return round

    def get_round_stats(self, round_id):
        total_tasks = self.query(Task)\
                          .filter(Task.round_entry.has(round_id=round_id),
                                  Task.cancel_date == None)\
                          .count()
        total_open_tasks = self.query(Task)\
                               .filter(Task.round_entry.has(round_id=round_id),
                                       Task.complete_date == None,
                                       Task.cancel_date == None)\
                               .count()
        return {'total_tasks': total_tasks,
                'total_open_tasks': total_open_tasks}

    def get_entries(self, filenames):
        entries = self.query(Entry)\
                      .filter(Entry.name.in_(filenames))\
                      .all()
        ret = {}
        for entry in entries:
            name = entry.name
            ret[name] = entry
        return ret


class OrganizerDAO(CoordinatorDAO):
    def check_is_organizer(self):
        return self.user.is_organizer

    def add_coordinator(self, username, campaign_id):
        user = lookup_user(self.rdb_session, username=username)
        if not user:
            print 'new user'
            user_id = get_mw_userid(username)
            user = User(id=user_id,
                        username=username,
                        created_by=self.user.id)
        campaign = self.get_campaign(campaign_id=campaign_id)
        if not campaign:
            raise DoesNotExist('campaign does not exist')
        if user in campaign.coords:
            raise InvalidAction('user is already a coordinator')
        campaign.coords.append(user)
        self.rdb_session.add(campaign)
        self.rdb_session.add(user)
        self.rdb_session.commit()

        msg = ('%s added %s as a coordinator of campaign "%s"'
               % (self.user.username, user.username, campaign.name))
        self.log_action('add_coordinator', campaign_id=campaign.id,
                        message=msg)
        return user

    def create_campaign(self, name):
        # TODO: Check if campaign with this name already exists?
        campaign = Campaign(name=name)
        self.rdb_session.add(campaign)
        campaign.coords.append(self.user)
        self.rdb_session.commit()

        self.log_action('create_campaign', campaign_id=campaign.id)

        return campaign

    # Read methods
    def get_all_campaigns(self):
        # Organizers can see everything, including rounds with which
        # they are not connected
        pass


class MaintainerDAO(OrganizerDAO):
    def check_is_maintainer(self):
        pass

    def get_audit_log(self, limit=100, offset=0):
        audit_logs = self.query(AuditLogEntry)\
                         .order_by(AuditLogEntry.create_date.desc())\
                         .limit(limit)\
                         .offset(offset)\
                         .all()
        return audit_logs

    def add_organizer(self, username):
        user = lookup_user(self.rdb_session, username=username)
        if user:
            created_by = self.user.id
        else:
            created_by = None
        if not user:
            user_id = get_mw_userid(username)
            user = User(id=user_id,
                        username=username,
                        created_by=created_by)
        if user.is_organizer:
            #raise Exception('organizer already exists')
            pass
        user.is_organizer = True
        self.rdb_session.add(user)
        self.rdb_session.commit()
        return user


class JurorDAO(UserDAO):
    """A Data Access Object for the Juror's view"""
    def is_juror(self):
        pass

    def edit_task(self, task_id, task_dict):
        # TODO: Confirm if dict keys are columns?
        ret = self.rdb_session.query(Task)\
                              .filter_by(id=task_id)\
                              .update(task_dict)
        self.rdb_session.commit()
        return ret

    def apply_rating(self, task_id, rating):
        task = self.get_task(task_id)
        if task.user != self.user:
            raise PermissionDenied()
        rating = Rating(user_id=self.user.id,
                        task_id=task_id,
                        round_entry_id=task.round_entry_id,
                        value=rating)
        self.rdb_session.add(rating)
        task_dict = {'complete_date': datetime.now()}
        self.edit_task(task_id, task_dict)

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

    def get_round_stats(self, round_id):
        total_tasks = self.query(Task)\
                          .filter(Task.round_entry.has(round_id=round_id),
                                  Task.user_id == self.user.id,
                                  Task.cancel_date == None)\
                          .count()
        total_open_tasks = self.query(Task)\
                               .filter(Task.round_entry.has(round_id=round_id),
                                       Task.user_id == self.user.id,
                                       Task.complete_date == None,
                                       Task.cancel_date == None)\
                               .count()
        return {'total_tasks': total_tasks, 'total_open_tasks': total_open_tasks}

    def get_tasks(self, num=1, offset=0):
        tasks = self.query(Task)\
                    .filter(Task.user == self.user,
                            Task.complete_date == None)\
                    .limit(num)\
                    .offset(offset)\
                    .all()
        return tasks

    def get_tasks_from_round(self, round_id, num=1, offset=0):
        tasks = self.query(Task)\
                    .filter(Task.user == self.user,
                            Task.complete_date == None,
                            Task.round_entry.has(round_id=round_id))\
                    .limit(num)\
                    .offset(offset)\
                    .all()
        return tasks

    def get_task(self, task_id):
        task = self.query(Task)\
                   .filter_by(id=task_id)\
                   .one_or_none()
        return task

    def get_next_round_task(self, round_id):
        pass


def lookup_user(rdb_session, username=None, userid=None):
    if not rdb_session:
        import pdb; pdb.set_trace()
    if not username and userid:
        raise TypeError('missing either a username or userid')
    if username and not userid:
        userid = get_mw_userid(username)

    user = rdb_session.query(User).filter(User.id == userid).one_or_none()
    return user


def create_initial_tasks(rdb_session, round):
    """this creates the initial tasks.

    there may well be a separate function for reassignment which reads
    from the incomplete Tasks table (that will have to ensure not to
    assign a rating which has already been completed by the same
    juror)
    """
    # TODO: deny quorum > number of jurors
    ret = []

    quorum = round.quorum
    jurors = [rj.user for rj in round.round_jurors if rj.is_active]
    random.shuffle(jurors)

    rdb_type = rdb_session.bind.dialect.name

    if rdb_type == 'mysql':
        rand_func = func.rand()
    else:
        rand_func = func.random()

    # this does the shuffling in the database
    shuffled_entries = rdb_session.query(RoundEntry)\
                                  .filter(RoundEntry.round_id == round.id)\
                                  .order_by(rand_func).all()

    to_process = itertools.chain.from_iterable([shuffled_entries] * quorum)
    # some pictures may get more than quorum votes
    # it's either that or some get less
    per_juror = int(ceil(len(shuffled_entries) * (float(quorum) / len(jurors))))

    juror_iters = itertools.chain.from_iterable([itertools.repeat(j, per_juror)
                                                 for j in jurors])

    pairs = itertools.izip_longest(to_process, juror_iters, fillvalue=None)
    for entry, juror in pairs:
        if juror is None:
            raise RuntimeError('should never run out of jurors first')
        if entry is None:
            break

        # TODO: bulk_save_objects
        task = Task(user=juror, round_entry=entry)
        ret.append(task)

    rdb_session.commit()
    return ret


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
