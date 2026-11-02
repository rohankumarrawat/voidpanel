from django.contrib import admin
from .models import DriveFile

@admin.register(DriveFile)
class DriveFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'user', 'file_size_bytes', 'is_public', 'created_at')
    search_fields = ('filename', 'share_token')
