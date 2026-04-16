# def application(environ, start_response):
#     status = '200 OK'
#     headers = [('Content-type', 'text/plain; charset=utf-8')]
#     start_response(status, headers)
#     return [b"Hello, world! This is a test WSGI application."]

from voidpanel.wsgi import application