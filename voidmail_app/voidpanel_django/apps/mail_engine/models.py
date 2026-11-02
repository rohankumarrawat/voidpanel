import crypt
from django.db import models
from django.contrib.auth.models import User

class SystemSetting(models.Model):
    """Global configuration for VoidOnyx Cloud Superadmin"""
    master_hostname = models.CharField(max_length=255, default='mail.voidpanel.com')
    primary_domain = models.CharField(max_length=255, default='voidonyx.com')
    default_quota_mb = models.IntegerField(default=5120)  # 5 GB default
    global_hourly_limit = models.IntegerField(default=100, help_text="Default global outbound sending limit (emails/hr)")
    ai_gateway_url = models.URLField(default='https://voidonyx.in/api/ai/chat/')
    ai_license_key = models.CharField(max_length=255, blank=True)
    is_registration_open = models.BooleanField(default=True)
    # WhatsApp OTP & Notification Gateway Settings
    whatsapp_provider = models.CharField(max_length=50, default='meta', blank=True, help_text="WhatsApp Provider (meta or custom)")
    whatsapp_api_url = models.URLField(default='https://graph.facebook.com/v21.0/1236644629538328/messages', blank=True, help_text="WhatsApp API URL e.g. Meta Graph Messages Endpoint")
    whatsapp_api_key = models.TextField(default='', blank=True, help_text="Permanent Meta API Token / Bearer Secret")
    whatsapp_sender_id = models.CharField(max_length=100, default='+91 93541 61484', blank=True, help_text="Verified Business Number")
    whatsapp_phone_number_id = models.CharField(max_length=100, default='1236644629538328', blank=True, help_text="Meta Phone Number ID")
    whatsapp_app_id = models.CharField(max_length=100, default='992161763849388', blank=True, help_text="Meta App ID")
    whatsapp_template = models.TextField(default='otp_template', help_text="Active WhatsApp Template Name for OTP")
    whatsapp_alert_template = models.CharField(max_length=100, default='email_alert_template', blank=True, help_text="Active WhatsApp Template Name for Email Alerts")
    test_mode_enabled = models.BooleanField(default=False, help_text="When enabled, default OTP 123456 is accepted without live API charge.")
    ai_auto_approve_new_users = models.BooleanField(default=True, help_text="Automatically enable AI features for new custom/professional domain accounts.")
    ai_free_default_domain = models.CharField(max_length=100, default='voidonyx.com', help_text="Default primary domain with free lifetime AI access.")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"System Config ({self.primary_domain})"


class RegistrationOtpSession(models.Model):
    """Temporary session storing pending registration details until WhatsApp OTP is verified"""
    phone_number = models.CharField(max_length=30)
    otp_code = models.CharField(max_length=10)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    domain_name = models.CharField(max_length=100, default='voidonyx.com')
    raw_password = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from datetime import timedelta
        from django.utils import timezone
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP Session for {self.username} ({self.phone_number})"



class VirtualDomain(models.Model):
    """Virtual Domains hosted on Postfix & Dovecot"""
    name = models.CharField(max_length=100, unique=True, help_text="e.g. voidonyx.com")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='domains')
    is_verified = models.BooleanField(default=True)
    dkim_selector = models.CharField(max_length=50, default='default')
    dkim_private_key = models.TextField(blank=True)
    dkim_public_key = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class VirtualMailbox(models.Model):
    """
    Dovecot & Postfix Virtual Mailbox accounts.
    Passwords are automatically hashed in {SHA512-CRYPT} format for native Dovecot auth.
    """
    domain = models.ForeignKey(VirtualDomain, on_delete=models.CASCADE, related_name='mailboxes')
    username = models.CharField(max_length=100, help_text="e.g. alex")
    email = models.EmailField(unique=True, help_text="alex@domain.com")
    password_hash = models.CharField(max_length=255, help_text="{SHA512-CRYPT}$6$...")
    quota_mb = models.IntegerField(default=5120)
    used_mb = models.IntegerField(default=0)
    hourly_limit = models.IntegerField(default=100, help_text="Outbound sending rate limit per hour")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_dovecot_password(self, raw_password):
        """Generate a SHA512-CRYPT hash that Dovecot native auth understands."""
        try:
            salt = crypt.mksalt(crypt.METHOD_SHA512)
            self.password_hash = "{SHA512-CRYPT}" + crypt.crypt(raw_password, salt)
        except Exception:
            import hashlib
            self.password_hash = "{SHA512-CRYPT}" + hashlib.sha512(raw_password.encode()).hexdigest()

    def save(self, *args, **kwargs):
        self.email = f"{self.username.strip()}@{self.domain.name.strip()}".lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class VirtualAlias(models.Model):
    """Email Forwarding & Virtual Aliases"""
    source_email = models.CharField(max_length=255, unique=True, help_text="alias@domain.com")
    destination_email = models.EmailField(help_text="real_user@gmail.com")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_email} -> {self.destination_email}"


class EmailSignature(models.Model):
    """Custom HTML Email Signatures"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signatures', null=True, blank=True)
    name = models.CharField(max_length=100, default='Default Business Signature')
    html_content = models.TextField()
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ScheduledMessage(models.Model):
    """Scheduled Send & 60-Second Undo Buffer Queue"""
    mailbox = models.ForeignKey(VirtualMailbox, on_delete=models.CASCADE, related_name='scheduled_messages', null=True, blank=True)
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body_html = models.TextField()
    send_at = models.DateTimeField()
    is_sent = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scheduled: {self.subject} to {self.to_email} at {self.send_at}"


class SharedInbox(models.Model):
    """Team Mailboxes (support@, sales@, billing@)"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    members = models.ManyToManyField(User, related_name='shared_inboxes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shared: {self.name} <{self.email}>"


class MailFilterRule(models.Model):
    """Sieve Filters & Auto-Routing Rules"""
    mailbox = models.ForeignKey(VirtualMailbox, on_delete=models.CASCADE, related_name='filter_rules', null=True, blank=True)
    name = models.CharField(max_length=100)
    condition_field = models.CharField(max_length=50, default='from') # from, subject, body
    condition_match = models.CharField(max_length=255)
    action_type = models.CharField(max_length=50, default='move_to_folder') # move_to_folder, tag, forward, delete
    action_value = models.CharField(max_length=255, default='Archive')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rule: {self.name}"


class UserLinkedAccount(models.Model):
    """
    Stores professional and custom domain accounts linked to a user's VoidOnyx workspace session.
    Allows managing and fast-switching across multiple business mailboxes.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linked_accounts')
    email = models.CharField(max_length=255)
    display_name = models.CharField(max_length=150, blank=True, default='')
    account_type = models.CharField(max_length=50, default='hosted', choices=[
        ('hosted', 'Hosted Domain'),
        ('professional', 'Professional Business Email'),
        ('external_imap', 'External IMAP/SMTP')
    ])
    domain = models.CharField(max_length=150)

    # IMAP / Incoming settings
    imap_host = models.CharField(max_length=255, blank=True, default='')
    imap_port = models.IntegerField(default=993)
    imap_user = models.CharField(max_length=255, blank=True, default='')
    imap_password = models.CharField(max_length=255, blank=True, default='')
    imap_security = models.CharField(max_length=20, default='SSL/TLS')

    # SMTP / Outgoing settings
    smtp_host = models.CharField(max_length=255, blank=True, default='')
    smtp_port = models.IntegerField(default=465)
    smtp_user = models.CharField(max_length=255, blank=True, default='')
    smtp_password = models.CharField(max_length=255, blank=True, default='')
    smtp_security = models.CharField(max_length=20, default='SSL/TLS')

    is_verified = models.BooleanField(default=False)
    last_sync_error = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'email')

    def __str__(self):
        return f"{self.user.username} -> {self.email} ({self.account_type})"

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'display_name': self.display_name or self.email.split('@')[0],
            'domain': self.domain,
            'account_type': self.account_type,
            'imap_host': self.imap_host,
            'imap_port': self.imap_port,
            'imap_security': self.imap_security,
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
            'smtp_security': self.smtp_security,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class UserDeletedVirtualEmail(models.Model):
    """
    Tracks deleted virtual or onboarding emails per user so they never reappear after deletion.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deleted_virtual_emails')
    email_id = models.CharField(max_length=255, db_index=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'email_id')

    def __str__(self):
        return f"{self.user.username} deleted {self.email_id}"


class UnansweredEmailTracker(models.Model):
    """
    AI-powered record of important incoming emails awaiting user reply.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unanswered_tracked_emails')
    email_id = models.CharField(max_length=255, db_index=True)
    account_email = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    sender = models.CharField(max_length=255)
    from_email = models.CharField(max_length=255)
    received_at = models.DateTimeField(null=True, blank=True)

    # AI Analysis fields
    is_important = models.BooleanField(default=True)
    urgency_level = models.CharField(max_length=50, default='Action Required')  # Urgent, Action Required, Question Asked, Follow-up
    ai_reason = models.CharField(max_length=255, blank=True, default='')
    action_needed = models.CharField(max_length=255, blank=True, default='')
    importance_score = models.IntegerField(default=80)

    # Answer status
    is_answered = models.BooleanField(default=False)
    answered_at = models.DateTimeField(null=True, blank=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'email_id')

    def to_dict(self):
        return {
            'id': self.id,
            'email_id': self.email_id,
            'account_email': self.account_email,
            'subject': self.subject,
            'sender': self.sender,
            'from_email': self.from_email,
            'received_at': self.received_at.isoformat() if self.received_at else '',
            'is_important': self.is_important,
            'urgency_level': self.urgency_level,
            'ai_reason': self.ai_reason,
            'action_needed': self.action_needed,
            'importance_score': self.importance_score,
            'is_answered': self.is_answered,
            'is_dismissed': self.is_dismissed,
            'created_at': self.created_at.strftime('%b %d, %I:%M %p')
        }


class CrmContact(models.Model):
    """
    Mini CRM Contact directory.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crm_contacts')
    name = models.CharField(max_length=150)
    email = models.EmailField()
    company_name = models.CharField(max_length=150, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    job_title = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=50, default='Lead', choices=[
        ('Lead', 'Lead'),
        ('Opportunity', 'Opportunity'),
        ('Customer', 'Customer'),
        ('Partner', 'Partner')
    ])
    notes = models.TextField(blank=True, default='')
    total_emails_exchanged = models.IntegerField(default=1)
    last_contacted_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'email')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'company_name': self.company_name or (self.email.split('@')[1] if '@' in self.email else ''),
            'phone': self.phone,
            'job_title': self.job_title,
            'status': self.status,
            'notes': self.notes,
            'total_emails': self.total_emails_exchanged,
            'last_contacted': self.last_contacted_at.strftime('%b %d, %Y') if self.last_contacted_at else 'Recent'
        }


class CrmCompany(models.Model):
    """
    Mini CRM Company entity.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crm_companies')
    name = models.CharField(max_length=150)
    domain = models.CharField(max_length=150)
    industry = models.CharField(max_length=100, blank=True, default='Technology')
    website = models.CharField(max_length=255, blank=True, default='')
    size = models.CharField(max_length=50, blank=True, default='1-50')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'domain')

    def to_dict(self):
        contacts_count = CrmContact.objects.filter(user=self.user, email__endswith='@' + self.domain).count()
        deals = CrmDeal.objects.filter(user=self.user, company=self)
        total_val = sum(d.amount for d in deals)
        return {
            'id': self.id,
            'name': self.name,
            'domain': self.domain,
            'industry': self.industry,
            'website': self.website or f"https://{self.domain}",
            'size': self.size,
            'contacts_count': contacts_count,
            'total_deals_val': float(total_val)
        }


class CrmDeal(models.Model):
    """
    Mini CRM Sales Pipeline Deal.
    """
    STAGE_CHOICES = [
        ('lead', 'New Lead'),
        ('contacted', 'Contacted'),
        ('proposal', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('won', 'Closed Won'),
        ('lost', 'Closed Lost')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crm_deals')
    title = models.CharField(max_length=200)
    company = models.ForeignKey(CrmCompany, on_delete=models.SET_NULL, null=True, blank=True, related_name='deals')
    contact = models.ForeignKey(CrmContact, on_delete=models.SET_NULL, null=True, blank=True, related_name='deals')
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default='lead')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    expected_close_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'company_name': self.company.name if self.company else (self.contact.company_name if self.contact else 'Direct Client'),
            'contact_name': self.contact.name if self.contact else '',
            'contact_email': self.contact.email if self.contact else '',
            'stage': self.stage,
            'amount': float(self.amount),
            'formatted_amount': f"₹{self.amount:,.2f}",
            'close_date': self.expected_close_date.strftime('%b %d, %Y') if self.expected_close_date else '',
            'notes': self.notes,
            'created_at': self.created_at.strftime('%b %d')
        }


class DeviceSessionLog(models.Model):
    """
    Security Center device and active login monitoring.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_sessions')
    session_key = models.CharField(max_length=100, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    browser = models.CharField(max_length=100, default='Chrome')
    os = models.CharField(max_length=100, default='macOS')
    location = models.CharField(max_length=150, default='United States')
    is_current = models.BooleanField(default=False)
    last_active_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            'id': self.id,
            'ip_address': self.ip_address or '127.0.0.1',
            'browser': self.browser,
            'os': self.os,
            'location': self.location,
            'is_current': self.is_current,
            'last_active': self.last_active_at.strftime('%b %d, %I:%M %p')
        }


class WhatsAppAlertRule(models.Model):
    """
    VIP & Domain Alert Rule configured by a workspace user.
    Dispatches WhatsApp notifications whenever emails arrive from specific emails or domains.
    """
    RULE_TYPE_CHOICES = [
        ('domain', 'Domain (@company.com)'),
        ('email', 'Specific Email Address'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='whatsapp_alert_rules')
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES, default='domain')
    pattern = models.CharField(max_length=255, help_text="e.g. acme.com or ceo@investor.com")
    whatsapp_number = models.CharField(max_length=30, help_text="Target WhatsApp phone number e.g. +919876543210")
    label = models.CharField(max_length=150, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def to_dict(self):
        return {
            'id': self.id,
            'rule_type': self.rule_type,
            'pattern': self.pattern,
            'whatsapp_number': self.whatsapp_number,
            'label': self.label or self.pattern,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%b %d, %Y')
        }


class WhatsAppAlertLog(models.Model):
    """
    Audit log of dispatched WhatsApp email notifications to avoid duplicate alerts.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='whatsapp_alert_logs')
    rule = models.ForeignKey(WhatsAppAlertRule, on_delete=models.SET_NULL, null=True, blank=True)
    email_id = models.CharField(max_length=255, db_index=True)
    sender = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=50)
    status = models.CharField(max_length=30, default='Delivered')  # Delivered, Simulated, Failed
    response_payload = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        unique_together = ('user', 'email_id', 'recipient_phone')

    def to_dict(self):
        return {
            'id': self.id,
            'email_id': self.email_id,
            'sender': self.sender,
            'subject': self.subject,
            'recipient_phone': self.recipient_phone,
            'status': self.status,
            'sent_at': self.sent_at.strftime('%b %d, %I:%M %p')
        }


class UserTwoFactorProfile(models.Model):
    """
    Two-Factor Authentication configuration for a user.
    When is_2fa_enabled=False: user signs in directly with password (normal login).
    When is_2fa_enabled=True: password is required first, followed by hardware key or OTP verification.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor_profile')
    is_2fa_enabled = models.BooleanField(default=False)
    whatsapp_number = models.CharField(max_length=30, blank=True, default='')
    last_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'is_2fa_enabled': self.is_2fa_enabled,
            'whatsapp_number': self.whatsapp_number,
            'keys_count': self.user.security_keys.count(),
            'last_verified': self.last_verified_at.strftime('%b %d, %Y %I:%M %p') if self.last_verified_at else None
        }

    def __str__(self):
        status = "Enabled" if self.is_2fa_enabled else "Disabled"
        return f"2FA Profile for {self.user.username} ({status})"


class UserSecurityKey(models.Model):
    """
    FIDO2 Passkeys, Touch ID, Face ID, USB Hardware Security Keys registered by user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_keys')
    name = models.CharField(max_length=150, help_text="e.g. MacBook Touch ID, YubiKey 5, iPhone Passkey")
    key_type = models.CharField(max_length=50, default='passkey')  # 'passkey', 'biometric', 'security_key'
    credential_id = models.TextField(help_text="WebAuthn credential ID")
    public_key = models.TextField(blank=True, default='', help_text="WebAuthn public key or key metadata")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'key_type': self.key_type,
            'credential_id': self.credential_id[:16] + '...' if len(self.credential_id) > 16 else self.credential_id,
            'created_at': self.created_at.strftime('%b %d, %Y'),
            'last_used': self.last_used_at.strftime('%b %d, %I:%M %p') if self.last_used_at else 'Never'
        }

    def __str__(self):
        return f"{self.name} ({self.user.username})"





