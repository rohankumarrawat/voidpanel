from django.contrib import admin
from .models import EmailTrackingLog, FollowUpSequence, SequenceStep, TextSnippet, SharedThread

@admin.register(EmailTrackingLog)
class EmailTrackingLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'subject', 'open_count', 'first_opened_at', 'last_opened_at')
    search_fields = ('recipient_email', 'subject', 'token')

@admin.register(FollowUpSequence)
class FollowUpSequenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'trigger_condition', 'is_active', 'created_at')

@admin.register(SequenceStep)
class SequenceStepAdmin(admin.ModelAdmin):
    list_display = ('sequence', 'step_number', 'delay_days', 'subject')

@admin.register(TextSnippet)
class TextSnippetAdmin(admin.ModelAdmin):
    list_display = ('shortcut', 'title', 'created_at')

@admin.register(SharedThread)
class SharedThreadAdmin(admin.ModelAdmin):
    list_display = ('subject', 'thread_token', 'expires_at', 'created_at')
