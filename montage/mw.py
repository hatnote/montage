
from clastic import Middleware
from clastic.route import NullRoute

from rdb import User, UserDAO


def public(endpoint_func):
    """A simple decorator for skipping auth steps on certain endpoints,
    if it's a public page, for instance.
    """
    endpoint_func.is_public = True

    return endpoint_func


class UserMiddleware(Middleware):
    endpoint_provides = ('user', 'user_dao')

    def endpoint(self, next, cookie, rdb_session, _route):
        # endpoints are default non-public
        ep_is_public = (getattr(_route.endpoint, 'is_public', False)
                        or '/static/' in _route.pattern
                        or isinstance(_route, NullRoute))

        try:
            userid = cookie['userid']
        except (KeyError, TypeError):
            if ep_is_public:
                return next(user=None, user_dao=None)
            return {'authorized': False}  # TODO: better convention

        user = rdb_session.query(User).filter(User.id == userid).first()
        if user is None and not ep_is_public:
            return {'authorized': False}  # user does not exist

        user_dao = UserDAO(rdb_session=rdb_session, user=user)

        return next(user=user, user_dao=user_dao)


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
