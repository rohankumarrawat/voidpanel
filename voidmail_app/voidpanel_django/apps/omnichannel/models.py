from django.db import models
from django.contrib.auth.models import User

class VipContact(models.Model):
    """Contacts that trigger WhatsApp & SMS VIP Instant Alerts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vip_contacts', null=True, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    whatsapp_number = models.CharField(max_length=30, blank=True, help_text="e.g. +919876543210")
    alert_keywords = models.CharField(max_length=255, default='URGENT, INVOICE, CONTRACT, SIGN', blank=True)
    enable_whatsapp_alert = models.BooleanField(default=True)
    enable_sms_alert = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"VIP: {self.name} ({self.email})"


class OmnichannelLog(models.Model):
    channel = models.CharField(max_length=20, choices=[('whatsapp', 'WhatsApp'), ('sms', 'SMS')])
    direction = models.CharField(max_length=10, choices=[('inbound', 'Inbound'), ('outbound', 'Outbound')])
    recipient = models.CharField(max_length=100)
    content = models.TextField()
    status = models.CharField(max_length=30, default='Delivered')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.channel.upper()} {self.direction} - {self.recipient}"
