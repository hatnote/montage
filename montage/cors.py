# -*- coding: utf-8 -*-

from clastic.middleware import Middleware

class CORSMiddleware(Middleware):
    """Middleware for handling Cross-Origin Resource Sharing (CORS).
    
    This middleware adds the necessary headers to enable CORS for a Clastic application.
    It handles preflight OPTIONS requests and adds CORS headers to all responses.
    """
    def __init__(self, 
                 allow_origins='*', 
                 allow_methods=None,
                 allow_headers=None,
                 allow_credentials=True,
                 expose_headers=None,
                 max_age=None):

        if allow_origins is None or allow_origins == '*':
            self.allow_all_origins = True
            self.allow_origins = []
        else:
            self.allow_all_origins = False
            if not isinstance(allow_origins, list):
                allow_origins = [allow_origins]
            self.allow_origins = allow_origins
        
        if allow_methods is None:
            allow_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
        
        if allow_headers is None:
            allow_headers = ['Content-Type', 'Authorization']
            
        if expose_headers is None:
            expose_headers = []
            
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers
        self.max_age = max_age

    def request(self, next, request):
        origin = request.headers.get('Origin')
        
        # If this is a preflight OPTIONS request, handle it directly
        if request.method == 'OPTIONS' and 'Access-Control-Request-Method' in request.headers:
            resp = self._handle_preflight(request)
            return resp
            
        # Otherwise, proceed with regular request handling and add CORS headers to response
        resp = next()
        self._add_cors_headers(resp, origin)
        return resp
    
    def _handle_preflight(self, request):
        from werkzeug.wrappers import Response
        
        origin = request.headers.get('Origin')
        resp = Response('')
        resp.status_code = 200
        
        # Add CORS headers
        self._add_cors_headers(resp, origin)
        
        # Add preflight-specific headers
        request_method = request.headers.get('Access-Control-Request-Method')
        if request_method and request_method in self.allow_methods:
            resp.headers['Access-Control-Allow-Methods'] = ', '.join(self.allow_methods)
        
        request_headers = request.headers.get('Access-Control-Request-Headers')
        if request_headers:
            resp.headers['Access-Control-Allow-Headers'] = ', '.join(self.allow_headers)
            
        if self.max_age is not None:
            resp.headers['Access-Control-Max-Age'] = str(self.max_age)
            
        return resp
    
    def _add_cors_headers(self, response, origin):
        try:
            if origin:
                if self.allow_all_origins or origin in self.allow_origins:
                    response.headers['Access-Control-Allow-Origin'] = origin
                    if hasattr(response, 'vary'):
                        response.vary.add('Origin')
                
            if self.allow_credentials:
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                
            if self.expose_headers:
                response.headers['Access-Control-Expose-Headers'] = ', '.join(self.expose_headers)
        except (AttributeError, TypeError):
            # Response object doesn't support CORS headers (e.g., exceptions)
            pass
            
    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(allow_origins=%r, allow_methods=%r)' % (cn, self.allow_origins, self.allow_methods)
