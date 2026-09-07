from app import app


class PrefixMiddleware:
    """WSGI middleware to handle URL routing and fix PATH_INFO on Vercel."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Use Vercel's original matched path header if provided
        matched_path = environ.get('HTTP_X_MATCHED_PATH')
        if matched_path:
            environ['PATH_INFO'] = matched_path
        else:
            # 2. Strip serverless function prefixes if present
            path_info = environ.get('PATH_INFO', '')
            for prefix in ('/api/index.py', '/api/index', '/api'):
                if path_info.startswith(prefix):
                    new_path = path_info[len(prefix):]
                    environ['PATH_INFO'] = new_path if (new_path.startswith('/') or not new_path) else ('/' + new_path)
                    if not environ['PATH_INFO']:
                        environ['PATH_INFO'] = '/'
                    break
        return self.wsgi_app(environ, start_response)


# Wrap Flask's WSGI application with the middleware
app.wsgi_app = PrefixMiddleware(app.wsgi_app)
