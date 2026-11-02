from django.contrib import admin
from .models import SystemSetting, VirtualDomain, VirtualMailbox, VirtualAlias, EmailSignature, ScheduledMessage, SharedInbox, MailFilterRule

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('primary_domain', 'master_hostname', 'default_quota_mb', 'updated_at')

@admin.register(VirtualDomain)
class VirtualDomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_verified', 'created_at')
    search_fields = ('name',)

@admin.register(VirtualMailbox)
class VirtualMailboxAdmin(admin.ModelAdmin):
    list_display = ('email', 'domain', 'quota_mb', 'used_mb', 'is_active', 'created_at')
    search_fields = ('email', 'username')
    list_filter = ('domain', 'is_active')

@admin.register(VirtualAlias)
class VirtualAliasAdmin(admin.ModelAdmin):
    list_display = ('source_email', 'destination_email', 'is_active', 'created_at')
    search_fields = ('source_email', 'destination_email')

@admin.register(EmailSignature)
class EmailSignatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'created_at')

@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'to_email', 'send_at', 'is_sent', 'is_cancelled')

@admin.register(SharedInbox)
class SharedInboxAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')

@admin.register(MailFilterRule)
class MailFilterRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'condition_field', 'condition_match', 'action_type', 'is_active')
