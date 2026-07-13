from django.contrib import admin
from .models import LiveChatSession, LiveChatMessage

admin.site.register(LiveChatSession)
admin.site.register(LiveChatMessage)
