
import json

from clastic import Middleware, BaseResponse
from clastic.route import NullRoute
from clastic.render import render_basic
from boltons.tbutils import ExceptionInfo

from rdb import User, UserDAO


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

    def __init__(self, raise_errors=True):
        self.raise_errors = raise_errors

    def request(self, next, request):
        response_dict = {'errors': [], 'status': 'success'}

        try:
            request_data = request.get_data()
            request_dict = json.loads(request_data)
        except Exception:
            request_dict = None

        return next(response_dict=response_dict, request_dict=request_dict)

    def endpoint(self, next, response_dict, request, _route):
        # TODO: autoswitch resp status code
        try:
            ret = next()
        except Exception:
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
        elif isinstance(ret, dict):
            response_dict.update(ret)
        else:
            response_dict.update({'data': ret})

        return render_basic(context=response_dict,
                            request=request,
                            _route=_route)


class UserMiddleware(Middleware):
    endpoint_provides = ('user', 'user_dao')

    def endpoint(self, next, cookie, response_dict, rdb_session, _route):
        # endpoints are default non-public
        response_dict['user'] = None

        ep_is_public = (getattr(_route.endpoint, 'is_public', False)
                        or getattr(_route, 'is_public', False)
                        or '/static/' in _route.pattern
                        or isinstance(_route, NullRoute))

        try:
            userid = cookie['userid']
        except (KeyError, TypeError):
            if ep_is_public:
                return next(user=None, user_dao=None)

            err = 'invalid cookie userid, try logging in again'
            response_dict['errors'].append(err)
            return {}

        user = rdb_session.query(User).filter(User.id == userid).first()
        response_dict['user'] = user.to_dict() if user else user

        if user is None and not ep_is_public:
            err = 'unknown cookie userid, try logging in again'
            response_dict['errors'].append(err)
            return {}

        user_dao = UserDAO(rdb_session=rdb_session, user=user)

        ret = next(user=user, user_dao=user_dao)

        return ret


class DBSessionMiddleware(Middleware):
    provides = ('rdb_session',)

    def __init__(self, session_type):
        self.session_type = session_type

    def request(self, next):
        rdb_session = self.session_type()
        try:
            ret = next(rdb_session=rdb_session)
        except:
            rdb_session.rollback()
            raise
        else:
            rdb_session.commit()
        return ret
