from django.contrib import admin
from .models import SystemNotification

@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
