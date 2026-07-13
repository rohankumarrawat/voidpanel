from django.db import models
from django.conf import settings

class LiveChatSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='live_chat_sessions')
    guest_name = models.CharField(max_length=150, blank=True)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES)
    assigned_agent = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_chats', null=True, blank=True, on_delete=models.SET_NULL)
    no_agent_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        email = self.user.email if self.user else self.guest_email
        return f"Chat #{self.id} with {email} [{self.status}]"


class LiveChatMessage(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('agent', 'Agent')
    ]
    MSG_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
    ]

    session = models.ForeignKey(LiveChatSession, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES)
    sender_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    msg_type = models.CharField(max_length=10, choices=MSG_TYPE_CHOICES, default='text')
    content = models.TextField(blank=True)
    # For file/image attachments
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"MSG #{self.id} | {self.sender_type} | Session #{self.session.id}"