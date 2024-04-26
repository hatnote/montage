
"""
WSGI middleware for profiling SQLAlchemy, based on SQLTap.

See https://github.com/bradbeattie/sqltap
"""

import queue
import urllib.parse as urlparse

import sqltap
from werkzeug import Response, Request
from clastic import Middleware

class SQLTapWSGIiddleware:
    """ SQLTap dashboard middleware for WSGI applications.

    For example, if you are using Flask::

        app.wsgi_app = SQLTapMiddleware(app.wsgi_app)

    And then you can use SQLTap dashboard from ``/__sqltap__`` page (this
    path prefix can be set by ``path`` parameter).

    :param app: A WSGI application object to be wrap.
    :param path: A path prefix for access. Default is `'/__sqltap__'`
    """

    def __init__(self, app, path='/__sqltap__'):
        self.app = app
        self.path = path.rstrip('/')
        self.on = False
        self.collector = queue.Queue(0)
        self.stats = []
        self.profiler = sqltap.ProfilingSession(collect_fn=self.collector.put)

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path == self.path or path == self.path + '/':
            return self.render(environ, start_response)
        
        query = urlparse.parse_qs(environ.get('QUERY_STRING', ''))
        enable = query.get('profilesql', [''])[0].lower() == 'true'
        if enable:
            self.profiler.start()

        try:
            resp = self.app(environ, start_response)
        finally:
            if enable:
                self.profiler.stop()

        return resp

    def render(self, environ, start_response):
        verb = environ.get('REQUEST_METHOD', 'GET').strip().upper()
        if verb not in ('GET', 'POST'):
            response = Response('405 Method Not Allowed', status=405,
                                mimetype='text/plain')
            response.headers['Allow'] = 'GET, POST'
            return response(environ, start_response)
        try:
            while True:
                self.stats.append(self.collector.get(block=False))
        except queue.Empty:
            pass

        return self.render_response(environ, start_response)

    def render_response(self, environ, start_response):
        html = sqltap.report(self.stats, middleware=self, report_format="wsgi")
        response = Response(html.encode('utf-8'), mimetype="text/html")
        return response(environ, start_response)


class SQLProfilerMiddleware(Middleware):
    def endpoint(self, next, api_act, request: Request):
        enabled = request.method in ['GET', 'POST', 'PUT', 'DELETE'] and request.args.get('profilesql', 'false').lower() == 'true'

        if not enabled:
            return next()
        
        stats = []
        collector = queue.Queue(0)
        profiler = sqltap.ProfilingSession(collect_fn=collector.put)
        profiler.start()
        try:
            resp = next()
        finally:
            profiler.stop()
        try:
            while True:
                stats.append(collector.get(block=False))
        except queue.Empty:
            pass

        text_report = sqltap.report(stats, report_format="text")

        if isinstance(resp, dict):
            resp['__sql_profile__'] = text_report
        else:
            api_act['sql_profile'] = f'unsupported response type {type(resp)} for sql profile ({len(text_report)} bytes)'

        return resp


        

