from django.contrib import admin
from .models import ApiKey

@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'user', 'monthly_limit', 'requests_used_this_month', 'is_active', 'created_at')
    search_fields = ('name', 'key')
