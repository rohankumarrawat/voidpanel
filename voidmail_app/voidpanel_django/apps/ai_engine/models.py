from django.db import models
from django.contrib.auth.models import User

class AiTaskItem(models.Model):
    """Auto-extracted actionable tasks and deadlines from emails"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_tasks', null=True, blank=True)
    task_description = models.CharField(max_length=255)
    source_email_subject = models.CharField(max_length=255, blank=True)
    sender = models.CharField(max_length=150, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Task: {self.task_description} (Due: {self.due_date})"


class MorningBriefing(models.Model):
    """Daily 8 AM Executive Email Digest"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='briefings', null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    summary_html = models.TextField()
    unread_count = models.IntegerField(default=0)
    high_priority_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Briefing for {self.date}"


class UserAiPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_prefs')
    default_tone = models.CharField(max_length=50, default='Executive & Crisp')
    enable_morning_briefing = models.BooleanField(default=True)
    enable_auto_categorization = models.BooleanField(default=True)
    preferred_language = models.CharField(max_length=20, default='en')

    def __str__(self):
        return f"AI Prefs for {self.user.username}"


class HuggingFaceApiKey(models.Model):
    """Hugging Face API key pool with automatic failover rotation"""
    api_key = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=150, help_text="e.g. rohanunsung@gmail.com")
    model_name = models.CharField(max_length=150, default='meta-llama/Llama-3.1-8B-Instruct')
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} ({self.api_key[:10]}...)"


class CustomDomainAiAccess(models.Model):
    """
    Controls AI feature access for entire custom business domains (e.g. acme.com).
    Whitelisted domains automatically grant AI privileges to all their email accounts.
    """
    domain = models.CharField(max_length=150, unique=True, help_text="e.g. acme.com")
    is_ai_enabled = models.BooleanField(default=True)
    plan_name = models.CharField(max_length=50, default='Pro AI')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_ai_domains')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.domain} (AI: {'Enabled' if self.is_ai_enabled else 'Disabled'})"

    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'is_ai_enabled': self.is_ai_enabled,
            'plan_name': self.plan_name,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class UserAiAccess(models.Model):
    """
    Individual email/user AI feature access control, upgrade requests, and status overrides.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_access_records')
    email = models.CharField(max_length=255, db_index=True)
    is_ai_enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=30, default='active', choices=[
        ('active', 'Active (Pro)'),
        ('pending', 'Pending Approval'),
        ('locked', 'Locked / Needs Upgrade')
    ])
    upgrade_requested = models.BooleanField(default=False)
    requested_at = models.DateTimeField(null=True, blank=True)
    request_note = models.TextField(blank=True, default='')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_ai_users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'email')

    def __str__(self):
        return f"{self.email} ({self.status})"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'is_ai_enabled': self.is_ai_enabled,
            'status': self.status,
            'upgrade_requested': self.upgrade_requested,
            'requested_at': self.requested_at.strftime('%Y-%m-%d %H:%M') if self.requested_at else None,
            'request_note': self.request_note,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

