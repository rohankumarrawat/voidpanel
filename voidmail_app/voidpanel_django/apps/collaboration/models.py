import secrets
from django.db import models
from django.contrib.auth.models import User

class CalendarEvent(models.Model):
    """CalDAV Calendar Event"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_events', null=True, blank=True)
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    attendees = models.TextField(blank=True, help_text="Comma-separated emails")
    meeting_url = models.URLField(blank=True)
    meeting_type = models.CharField(max_length=50, default='video')  # video, call, in_person
    reminder_minutes = models.IntegerField(default=15)
    notes = models.TextField(blank=True, default='')
    source_email_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start_time': self.start_time.isoformat() if self.start_time else '',
            'end_time': self.end_time.isoformat() if self.end_time else '',
            'date_str': self.start_time.strftime('%b %d, %Y') if self.start_time else '',
            'time_str': self.start_time.strftime('%I:%M %p') if self.start_time else '',
            'end_time_str': self.end_time.strftime('%I:%M %p') if self.end_time else '',
            'attendees': [a.strip() for a in self.attendees.split(',') if a.strip()],
            'meeting_url': self.meeting_url,
            'meeting_type': self.meeting_type,
            'reminder_minutes': self.reminder_minutes,
            'notes': self.notes,
            'source_email_id': self.source_email_id
        }

    def __str__(self):
        return f"{self.title} ({self.start_time})"


class BookingSlot(models.Model):
    """Shareable Calendly-like Booking Page (voidonyx.in/book/<slug>)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_slots', null=True, blank=True)
    slug = models.SlugField(unique=True, help_text="e.g. rohan-20min-demo")
    title = models.CharField(max_length=150, default="30-Minute Video Meeting")
    description = models.TextField(blank=True, default="Select a convenient time slot for our 1-on-1 video call.")
    duration_minutes = models.IntegerField(default=30)
    working_hours_start = models.IntegerField(default=9)
    working_hours_end = models.IntegerField(default=18)
    timezone_name = models.CharField(max_length=64, default="Asia/Kolkata")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Book: {self.title} ({self.slug})"


class VoidDoc(models.Model):
    """Cloud Markdown & Rich Notes Document"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='docs', null=True, blank=True)
    title = models.CharField(max_length=200, default='Untitled Note')
    content = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class SignatureDocument(models.Model):
    """VoidSign PDF Digital Signatures (DocuSign clone)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signature_docs', null=True, blank=True)
    title = models.CharField(max_length=200)
    document_token = models.CharField(max_length=64, unique=True)
    pdf_file = models.FileField(upload_to='signatures/%Y/%m/', blank=True, null=True)
    signatory_email = models.EmailField()
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    signature_audit_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.document_token:
            self.document_token = 'sign_' + secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"VoidSign: {self.title} ({'Signed' if self.is_signed else 'Pending'})"


class FormDefinition(models.Model):
    """VoidForms Lead Capture & Surveys"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forms', null=True, blank=True)
    form_token = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=200)
    fields_json = models.TextField(default='[{"name": "Full Name", "type": "text"}, {"name": "Email", "type": "email"}]')
    delivery_email = models.EmailField()
    submissions_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.form_token:
            self.form_token = 'form_' + secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Form: {self.title} (Subs: {self.submissions_count})"


class MeetingSignal(models.Model):
    """WebRTC peer-to-peer signaling store for VoidMeet video rooms"""
    room_id = models.CharField(max_length=64, db_index=True)
    sender_id = models.CharField(max_length=64)
    sender_name = models.CharField(max_length=100, default='Guest')
    recipient_id = models.CharField(max_length=64, blank=True, default='')  # blank means broadcast
    signal_type = models.CharField(max_length=32)  # 'join', 'leave', 'offer', 'answer', 'candidate', 'chat'
    payload = models.TextField(blank=True, default='{}')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.room_id}: {self.sender_name} -> {self.signal_type}"
