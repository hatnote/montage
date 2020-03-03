from __future__ import absolute_import

import weakref

from sentry_sdk.hub import Hub, _should_send_default_pii
from sentry_sdk.utils import capture_internal_exceptions, event_from_exception
from sentry_sdk.integrations import Integration, DidNotEnable
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
from sentry_sdk.integrations._wsgi_common import RequestExtractor

from sentry_sdk._types import MYPY

if MYPY:
    from sentry_sdk.integrations.wsgi import _ScopedResponse
    from typing import Any
    from typing import Dict
    from werkzeug.datastructures import ImmutableTypeConversionDict
    from werkzeug.datastructures import ImmutableMultiDict
    from werkzeug.datastructures import FileStorage
    from typing import Union
    from typing import Callable

    from sentry_sdk._types import EventProcessor


from clastic import Middleware, Application, SubApplication
from clastic.errors import BadRequest


def integrate_sentry(clastic_app):
    # avoid double-wrapping
    if getattr(clastic_app._dispatch_wsgi, '_sentry_integrated', None):
        return clastic_app

    ret = Application(routes=[SubApplication('/', clastic_app)],
                      middlewares=[SentryMiddleware()])

    orig_wsgi = ret._dispatch_wsgi

    def sentry_patched_wsgi_app(environ, start_response):
        # type: (Any, Dict[str, str], Callable[..., Any]) -> _ScopedResponse
        # if Hub.current.get_integration(ClasticIntegration) is None:
        #     return old_app(self, environ, start_response)

        return SentryWsgiMiddleware(lambda *a, **kw: orig_wsgi(*a, **kw))(
            environ, start_response
        )

    ret._dispatch_wsgi = sentry_patched_wsgi_app
    ret._dispatch_wsgi._sentry_integrated = True
    return ret


class SentryMiddleware(Middleware):
    provides = ('sentry_scope',)

    def request(self, next, request, _route):
        # type: (Clastic, **Any) -> None
        hub = Hub.current
        #integration = hub.get_integration(ClasticIntegration)
        #if integration is None:
        #    return next(sentry_scope=None)

        with hub.configure_scope() as scope:
            # Rely on WSGI middleware to start a trace
            scope.transaction = _route.pattern

            weak_request = weakref.ref(request)
            evt_processor = _make_request_event_processor(weak_request)
            scope.add_event_processor(evt_processor)

            try:
                ret = next(sentry_scope=scope)  # TODO
            except BadRequest:
                raise
            except Exception as exc:
                client = hub.client  # type: Any

                event, hint = event_from_exception(
                    exc,
                    client_options=client.options,
                    mechanism={"type": "clastic"},
                )

                hub.capture_event(event, hint=hint)
                raise
        return ret



"""
def _push_appctx(*args, **kwargs):
    # type: (*Clastic, **Any) -> None
    hub = Hub.current
    if hub.get_integration(ClasticIntegration) is not None:
        # always want to push scope regardless of whether WSGI app might already
        # have (not the case for CLI for example)
        scope_manager = hub.push_scope()
        scope_manager.__enter__()
        _app_ctx_stack.top.sentry_sdk_scope_manager = scope_manager
        with hub.configure_scope() as scope:
            scope._name = "clastic"


def _pop_appctx(*args, **kwargs):
    # type: (*Clastic, **Any) -> None
    scope_manager = getattr(_app_ctx_stack.top, "sentry_sdk_scope_manager", None)
    if scope_manager is not None:
        scope_manager.__exit__(None, None, None)
"""


class ClasticRequestExtractor(RequestExtractor):
    def env(self):
        # type: () -> Dict[str, str]
        return self.request.environ

    def cookies(self):
        # type: () -> ImmutableTypeConversionDict[Any, Any]
        return self.request.cookies

    def raw_data(self):
        # type: () -> bytes
        return self.request.get_data()

    def form(self):
        # type: () -> ImmutableMultiDict[str, Any]
        return self.request.form

    def files(self):
        # type: () -> ImmutableMultiDict[str, Any]
        return self.request.files

    def is_json(self):
        # type: () -> bool
        return self.request.is_json

    def json(self):
        # type: () -> Any
        return self.request.get_json()

    def size_of_file(self, file):
        # type: (FileStorage) -> int
        return file.content_length


def _make_request_event_processor(weak_request):
    # type: (Clastic, Callable[[], Request], ClasticIntegration) -> EventProcessor
    def inner(event, hint):
        # type: (Dict[str, Any], Dict[str, Any]) -> Dict[str, Any]
        request = weak_request()

        # if the request is gone we are fine not logging the data from
        # it.  This might happen if the processor is pushed away to
        # another thread.
        if request is None:
            return event

        with capture_internal_exceptions():
            ClasticRequestExtractor(request).extract_into_event(event)

        # if _should_send_default_pii():
        #     with capture_internal_exceptions():
        #         _add_user_to_event(event)

        return event

    return inner


# suitable for montage perhaps
"""
def _add_user_to_event(event):
    # type: (Dict[str, Any]) -> None
    if clastic_login is None:
        return

    user = clastic_login.current_user
    if user is None:
        return

    with capture_internal_exceptions():
        # Access this object as late as possible as accessing the user
        # is relatively costly

        user_info = event.setdefault("user", {})

        try:
            user_info.setdefault("id", user.get_id())
            # TODO: more configurable user attrs here
        except AttributeError:
            # might happen if:
            # - clastic_login could not be imported
            # - clastic_login is not configured
            # - no user is logged in
            pass

        # The following attribute accesses are ineffective for the general
        # Clastic-Login case, because the User interface of Clastic-Login does not
        # care about anything but the ID. However, Clastic-User (based on
        # Clastic-Login) documents a few optional extra attributes.
        #
        # https://github.com/lingthio/Clastic-User/blob/a379fa0a281789618c484b459cb41236779b95b1/docs/source/data_models.rst#fixed-data-model-property-names

        try:
            user_info.setdefault("email", user.email)
        except Exception:
            pass

        try:
            user_info.setdefault("username", user.username)
            user_info.setdefault("username", user.email)
        except Exception:
            pass
"""
