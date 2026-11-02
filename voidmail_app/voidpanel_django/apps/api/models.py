import secrets
from django.db import models
from django.contrib.auth.models import User

class ApiKey(models.Model):
    """Developer Transactional Email API Keys (Resend / SendGrid clone)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys', null=True, blank=True)
    name = models.CharField(max_length=100, default='Default Production Key')
    key = models.CharField(max_length=64, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    monthly_limit = models.IntegerField(default=50000)
    requests_used_this_month = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = 'vp_live_' + secrets.token_hex(24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.key[:14]}...)"
