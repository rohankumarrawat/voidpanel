import secrets
from django.db import models
from django.contrib.auth.models import User

class EmailTrackingLog(models.Model):
    """Zero-Plugin Read & Link Click Tracker"""
    token = models.CharField(max_length=64, unique=True)
    sender_email = models.EmailField()
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    open_count = models.IntegerField(default=0)
    first_opened_at = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    last_ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_user_agent = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = 'trk_' + secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Tracking {self.recipient_email} - {self.subject} (Opens: {self.open_count})"


class FollowUpSequence(models.Model):
    """Automated Email Drip Sequences"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sequences', null=True, blank=True)
    name = models.CharField(max_length=150)
    trigger_condition = models.CharField(max_length=50, default='if_no_reply_in_3_days')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class SequenceStep(models.Model):
    sequence = models.ForeignKey(FollowUpSequence, on_delete=models.CASCADE, related_name='steps')
    step_number = models.IntegerField(default=1)
    delay_days = models.IntegerField(default=3)
    subject = models.CharField(max_length=255)
    body = models.TextField()

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"{self.sequence.name} - Step {self.step_number}"


class TextSnippet(models.Model):
    """Dynamic Keyboard Text Expander (;pitch, ;bank, etc.)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='snippets', null=True, blank=True)
    shortcut = models.CharField(max_length=30, help_text="e.g. ;pitch or ;bank")
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shortcut} ({self.title})"


class SharedThread(models.Model):
    """1-Click Shareable Email Thread Web Links"""
    thread_token = models.CharField(max_length=64, unique=True)
    subject = models.CharField(max_length=255)
    sanitized_html = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.thread_token:
            self.thread_token = 'th_' + secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Shared Thread: {self.subject}"
