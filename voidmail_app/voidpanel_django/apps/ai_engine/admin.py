from django.contrib import admin
from .models import AiTaskItem, MorningBriefing, UserAiPreference

@admin.register(AiTaskItem)
class AiTaskItemAdmin(admin.ModelAdmin):
    list_display = ('task_description', 'source_email_subject', 'sender', 'due_date', 'is_completed')
    list_filter = ('is_completed', 'due_date')

@admin.register(MorningBriefing)
class MorningBriefingAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'unread_count', 'high_priority_count')

@admin.register(UserAiPreference)
class UserAiPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'default_tone', 'enable_morning_briefing', 'enable_auto_categorization')
