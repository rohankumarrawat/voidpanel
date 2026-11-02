import secrets
from django.db import models
from django.contrib.auth.models import User

class BurnOnReadMessage(models.Model):
    """Self-Destructing Encrypted Message (deletes permanently upon 1st view)"""
    secret_token = models.CharField(max_length=64, unique=True)
    encrypted_payload = models.TextField()
    passcode_hash = models.CharField(max_length=128, blank=True, null=True)
    max_views = models.IntegerField(default=1)
    view_count = models.IntegerField(default=0)
    is_burned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.secret_token:
            self.secret_token = 'burn_' + secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"BurnOnRead: {self.secret_token} (Burned: {self.is_burned})"


class VoidMaskAlias(models.Model):
    """Disposable Burner Aliases (e.g. shopping.a8b1@voidonyx.in -> user@voidonyx.com)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='burner_aliases', null=True, blank=True)
    alias_email = models.CharField(max_length=255, unique=True)
    real_destination = models.EmailField()
    label = models.CharField(max_length=100, default='Shopping / Newsletter')
    is_forwarding_active = models.BooleanField(default=True)
    emails_forwarded_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alias_email} -> {self.real_destination}"


class VaultItem(models.Model):
    """VoidVault Zero-Knowledge Password Locker"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vault_items', null=True, blank=True)
    title = models.CharField(max_length=150)
    service_url = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=150)
    encrypted_password = models.TextField()
    category = models.CharField(max_length=50, default='Login')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vault: {self.title} ({self.username})"
