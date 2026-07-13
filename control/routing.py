from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/terminal/$', consumers.TerminalConsumer.as_asgi()),
    re_path(r'ws/user-terminal/(?P<username>[a-z0-9_]{1,32})/$', consumers.UserTerminalConsumer.as_asgi()),
]
