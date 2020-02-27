
import json
import time
import datetime

import clastic
from clastic import Middleware, BaseResponse
from clastic.route import NullRoute
from clastic.render import render_basic
from boltons.tbutils import ExceptionInfo

from rdb import User, UserDAO
from utils import MontageError


def public(endpoint_func):
    """A simple decorator for skipping auth steps on certain endpoints,
    if it's a public page, for instance.
    """
    endpoint_func.is_public = True

    return endpoint_func

class MessageMiddleware(Middleware):
    """Manages the data format consistency and serialization for all
    endpoints.

    Convention: All messages have status: "success" by default. Any
    response with one or more messages in "errors" gets status:
    "failure". Uncaught endpoint function exceptions get status:
    "exception".
    """
    provides = ('response_dict', 'request_dict')

    def __init__(self, raise_errors=True, use_ashes=False, debug_errors=False):
        self.raise_errors = raise_errors
        self.use_ashes = use_ashes
        self.debug_errors = debug_errors

    def request(self, next, request):
        response_dict = {'errors': [], 'status': 'success'}

        try:
            request_data = request.get_data()
            request_dict = json.loads(request_data)
        except Exception:
            request_dict = None
        if request.args:
            if request_dict:
                request_dict.update(request.args.items())
            else:
                request_dict = dict(request.args.items())

        return next(response_dict=response_dict, request_dict=request_dict)

    def endpoint(self, next, response_dict, request, _route):
        # TODO: autoswitch resp status code
        try:
            ret = next()
        except Exception as e:
            if self.debug_errors and not isinstance(e, MontageError):
                import pdb; pdb.post_mortem()
            if self.raise_errors:
                raise
            ret = None
            exc_info = ExceptionInfo.from_current()
            err = '%s: %s' % (exc_info.exc_type, exc_info.exc_msg)
            response_dict['errors'].append(err)
            response_dict['status'] = 'exception'
        else:
            if response_dict.get('errors'):
                response_dict['status'] = 'failure'

        if isinstance(ret, BaseResponse):
            # preserialized responses (and 404s, etc.)  TODO: log that
            # we're skipping over response_dict if the response status
            # code == 2xx
            # TODO: autoserialize body if no body is set
            return ret
        elif isinstance(ret, dict) and (ret.get('use_ashes') or self.use_ashes):
            return ret
        elif isinstance(ret, dict):
            response_dict.update(ret)
        else:
            response_dict.update({'data': ret})

        return render_basic(context=response_dict,
                            request=request,
                            _route=_route)


class UserMiddleware(Middleware):
    """The UserMiddleware looks up the logged in user and provides a
    database interface (UserDAO). Sessions are authenticated through
    signed cookies.

    * "superuser" feature. If there is a configured superuser, they can
    pass the user they'd like to act as, assuming they can provide a
    valid signed cookie.

    """
    endpoint_provides = ('user', 'user_dao')

    def endpoint(self, next, cookie, rdb_session, _route, config,
                 request_dict, response_dict, timings_dict):
        # endpoints are default non-public
        response_dict['user'] = None
        start_time = time.time()
        timings_dict['lookup_user'] = 0.0
        ep_is_public = (getattr(_route.endpoint, 'is_public', False)
                        or getattr(_route, 'is_public', False)
                        or '/static/' in _route.pattern
                        or isinstance(_route, NullRoute))

        try:
            userid = cookie['userid']
        except (KeyError, TypeError):
            if ep_is_public:
                return next(user=None, user_dao=None)
            import pdb;pdb.set_trace()
            err = 'invalid cookie userid, try logging in again.'
            response_dict['errors'].append(err)
            return {}

        user = rdb_session.query(User).filter(User.id == userid).first()

        if user is None and not ep_is_public:
            err = 'unknown cookie userid, try logging in again'
            response_dict['errors'].append(err)
            return {}

        superuser = config.get('superuser')
        superusers = config.get('superusers', [superuser] if superuser else [])
        if superusers and user.username in superusers:
            su_to = request_dict and request_dict.get('su_to')
            if su_to:
                user = (rdb_session.query(User)
                        .filter(User.username == su_to)
                        .first())
            if not user:
                err = 'unknown su_to user %r' % (su_to,)
                response_dict['errors'].append(err)
                return {}

        now = datetime.datetime.utcnow()
        last_minute = now - datetime.timedelta(seconds=60)
        if not user.last_active_date or user.last_active_date < last_minute:
            # updates only up to once a minute
            user.last_active_date = now

        response_dict['user'] = user.to_dict() if user else user
        user_dao = UserDAO(rdb_session=rdb_session, user=user)
        timings_dict['lookup_user'] = time.time() - start_time
        ret = next(user=user, user_dao=user_dao)

        return ret


class TimingMiddleware(Middleware):
    provides = ('timings_dict',)

    def request(self, next, response_dict):
        response_dict['timings'] = timings_dict = {}
        ret = next(timings_dict=timings_dict)
        return ret

    def endpoint(self, next, timings_dict):
        start_time = time.time()
        ret = next()
        timings_dict['endpoint'] = round(time.time() - start_time, 3)
        if (isinstance(ret, BaseResponse)
            and getattr(ret, 'mimetype', '').startswith('text/html')
            and isinstance(ret.data, basestring)):
            ret.data += ('<!-- Timings: ' + json.dumps(timings_dict) + ' -->')
        return ret


class DBSessionMiddleware(Middleware):
    provides = ('rdb_session',)

    def __init__(self, session_type, get_engine):
        self.session_type = session_type
        self.get_engine = get_engine

        self.engine = None

    def request(self, next):
        if not self.engine:
            # lazy initialization because uwsgi config
            self.engine = self.get_engine()
            self.session_type.configure(bind=self.engine)

        rdb_session = self.session_type()
        try:
            ret = next(rdb_session=rdb_session)
        except Exception:
            rdb_session.rollback()
            raise
        else:
            if ret.status_code >= 400:
                rdb_session.rollback()
            else:
                rdb_session.commit()
        finally:
            rdb_session.close()
        return ret


import os.path

from lithoxyl import (Logger,
                      StreamEmitter,
                      SensibleSink,
                      SensibleFilter,
                      SensibleFormatter)

API_LOG_FMT = (' {status_char} - {process_id:>5} - {iso_end_notz}'
               ' - {duration_ms:>8.3f}ms - {end_message}')


class LoggingMiddleware(Middleware):
    provides = ('api_log', 'api_act',)

    def __init__(self, log_path, act_name='API'):
        self.log_path = os.path.abspath(log_path)
        root, ext = os.path.splitext(self.log_path)
        self.exc_log_path = '%s.exc%s' % (root, ext)
        self.act_name = act_name

        self._setup_api_log()

    def request(self, next, request, _route):
        try:
            act_name = '%s%s' % (request.method, _route.pattern)
            with self.api_log.critical(act_name) as api_act:
                # basic redacted url
                api_act['path'] = request.path
                api_act.data_map.update(request.args.items())
                try:
                    ret = next(api_act=api_act, api_log=self.api_log)
                except clastic.errors.BadRequest as br:
                    api_act.data_map.update(br.to_dict())
                    api_act.failure()
                    ret = br
                api_act['code'] = ret.status_code
        except Exception:
            exc_info = ExceptionInfo.from_current()
            text = u'\n\n' + exc_info.get_formatted() + '\n\n'
            self.exc_log_file_obj.write(text.encode('utf8'))
            self.exc_log_file_obj.flush()
            raise
        return ret

    def endpoint(self, next, api_act):
        ret = next()
        try:
            api_act['username'] = ret['user'].username
        except Exception:
            pass
        return ret

    def _setup_api_log(self):
        self.log_file_obj = open(self.log_path, 'ab')
        self.exc_log_file_obj = open(self.exc_log_path, 'ab')

        self.api_log = Logger(self.act_name.lower() + '_log')
        self._api_fmtr = SensibleFormatter(API_LOG_FMT)
        self._api_emtr = StreamEmitter(self.log_file_obj)
        self._api_fltr = SensibleFilter(success='info',
                                        failure='debug',
                                        exception='debug')
        self._api_sink = SensibleSink(formatter=self._api_fmtr,
                                      emitter=self._api_emtr,
                                      filters=[self._api_fltr])
        self.api_log.add_sink(self._api_sink)

        self._exc_emtr = StreamEmitter(self.exc_log_file_obj)
        self._exc_fltr = SensibleFilter(success=None,
                                        failure=None,
                                        exception='info')
        self._exc_sink = SensibleSink(formatter=self._api_fmtr,
                                      emitter=self._exc_emtr,
                                      filters=[self._exc_fltr])
        self.api_log.add_sink(self._exc_sink)


import os
import sys
import json
import uuid
import socket


class ReplayLogMiddleware(Middleware):
    def __init__(self, log_path):
        self.log_path = os.path.abspath(log_path)
        self.log_file = open(self.log_path, 'ab')
        self.start_timestamp = datetime.datetime.utcnow().isoformat()
        self.hostname = socket.gethostname()

    def endpoint(self, next, user, request_dict, request):
        cur_id = str(uuid.uuid4())
        log_file = self.log_file
        data = {'id': cur_id,
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'start_timestamp': self.start_timestamp,
                'host': self.hostname,
                'pid': os.getpid(),
                'path': request.path,
                'method': request.method,
                'request_dict': request_dict,
                'user': getattr(user, 'username', None)}
        try:
            log_file.write(json.dumps(data, sort_keys=True) + '\n')
            log_file.flush()
        except Exception:
            sys.stderr.write('failed to write replay log in %s\n'
                             % os.getpid())
            sys.stderr.flush()
        try:
            ret = next()
        except Exception as e:
            exc_data = {'id': cur_id, 'exception': repr(e)}
            try:
                log_file.write(json.dumps(exc_data, sort_keys=True) + '\n')
            except Exception:
                sys.stderr.write('failed to write replay log exc in %s\n'
                                 % os.getpid())
                sys.stderr.flush()
            raise
        return ret
