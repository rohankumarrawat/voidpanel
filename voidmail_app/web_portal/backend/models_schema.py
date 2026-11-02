# ==============================================================================
# VOIDONYX & VOIDPANEL — DJANGO BACKEND MODELS & DOVECOT INTEGRATION SCHEMA
# ==============================================================================

import crypt
import secrets
import string
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class SystemSetting(models.Model):
    """Global configuration for VoidOnyx Cloud Superadmin"""
    master_hostname = models.CharField(max_length=255, default='mail.voidpanel.com')
    primary_domain = models.CharField(max_length=255, default='voidonyx.com')
    default_quota_mb = models.IntegerField(default=5120)  # 5 GB default
    ai_gateway_url = models.URLField(default='https://voidonyx.in/api/ai/chat/')
    ai_license_key = models.CharField(max_length=255, blank=True)
    is_registration_open = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"System Config ({self.primary_domain})"


class VirtualDomain(models.Model):
    """Domains hosted on Postfix & Dovecot"""
    name = models.CharField(max_length=100, unique=True, help_text="e.g. voidonyx.com")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='domains')
    is_verified = models.BooleanField(default=False)
    dkim_selector = models.CharField(max_length=50, default='default')
    dkim_private_key = models.TextField(blank=True)
    dkim_public_key = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def generate_dkim_keys(self):
        """Placeholder for 2048-bit RSA DKIM key pair generation"""
        # In production: uses `cryptography.hazmat.primitives.asymmetric.rsa`
        pass


class VirtualMailbox(models.Model):
    """
    Dovecot & Postfix Virtual Mailbox accounts.
    Passwords are automatically hashed in {SHA512-CRYPT} format.
    """
    domain = models.ForeignKey(VirtualDomain, on_delete=models.CASCADE, related_name='mailboxes')
    username = models.CharField(max_length=100, help_text="e.g. alex")
    email = models.EmailField(unique=True, help_text="alex@domain.com")
    password_hash = models.CharField(max_length=255, help_text="{SHA512-CRYPT}$6$...")
    quota_mb = models.IntegerField(default=5120)
    used_mb = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_dovecot_password(self, raw_password):
        """Generate a SHA512-CRYPT hash that Dovecot native auth understands."""
        salt = crypt.mksalt(crypt.METHOD_SHA512)
        self.password_hash = "{SHA512-CRYPT}" + crypt.crypt(raw_password, salt)

    def save(self, *args, **kwargs):
        self.email = f"{self.username.strip()}@{self.domain.name.strip()}".lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class VirtualAlias(models.Model):
    """Email Forwarding & Burner Aliases (VoidMask)"""
    source_email = models.CharField(max_length=255, unique=True, help_text="shopping.xyz@voidonyx.in")
    destination_email = models.EmailField(help_text="real_user@gmail.com")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_email} -> {self.destination_email}"


class ApiKey(models.Model):
    """Developer Transactional Email API Keys (Resend clone)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100, default='Default Live Key')
    key = models.CharField(max_length=64, unique=True)
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


class DriveFile(models.Model):
    """VoidDrive Cloud Storage Files & Large Email Attachments"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drive_files')
    filename = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField()
    file_path = models.FileField(upload_to='voiddrive/%Y/%m/%d/')
    share_token = models.CharField(max_length=64, unique=True)
    is_public = models.BooleanField(default=False)
    password_protection = models.CharField(max_length=128, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = 'vd_' + secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} ({self.file_size_bytes} bytes)"
