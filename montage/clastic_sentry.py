# NB: code heavily modified from sentry's own flask integration

from __future__ import absolute_import

import weakref

from sentry_sdk.hub import Hub, _should_send_default_pii
from sentry_sdk.utils import capture_internal_exceptions, event_from_exception
from sentry_sdk.integrations import Integration, DidNotEnable
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
from sentry_sdk.integrations._wsgi_common import RequestExtractor

from clastic import Middleware, Application, SubApplication
from clastic.errors import BadRequest


class SentryMiddleware(Middleware):
    provides = ('sentry_scope', 'sentry_hub')

    wsgi_wrapper = SentryWsgiMiddleware

    def request(self, next, request, _route):
        hub = Hub.current

        with hub.configure_scope() as scope:
            # Rely on WSGI middleware to start a trace
            scope.transaction = _route.pattern

            weak_request = weakref.ref(request)
            evt_processor = _make_request_event_processor(weak_request)
            scope.add_event_processor(evt_processor)

            try:
                ret = next(sentry_scope=scope, sentry_hub=hub)
            except BadRequest:
                raise
            except Exception as exc:
                client = hub.client

                event, hint = event_from_exception(
                    exc,
                    client_options=client.options,
                    mechanism={"type": "clastic"},
                )

                hub.capture_event(event, hint=hint)
                raise
        return ret


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
    def inner(event, hint):
        request = weak_request()

        # if the request is gone we are fine not logging the data from
        # it.  This might happen if the processor is pushed away to
        # another thread.
        if request is None:
            return event

        with capture_internal_exceptions():
            ClasticRequestExtractor(request).extract_into_event(event)

        return event

    return inner
