from django.contrib import admin
from .models import BurnOnReadMessage, VoidMaskAlias, VaultItem

@admin.register(BurnOnReadMessage)
class BurnOnReadMessageAdmin(admin.ModelAdmin):
    list_display = ('secret_token', 'view_count', 'is_burned', 'created_at')
    list_filter = ('is_burned',)

@admin.register(VoidMaskAlias)
class VoidMaskAliasAdmin(admin.ModelAdmin):
    list_display = ('alias_email', 'real_destination', 'label', 'is_forwarding_active', 'emails_forwarded_count')
    search_fields = ('alias_email', 'real_destination')

@admin.register(VaultItem)
class VaultItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'username', 'category', 'created_at')
