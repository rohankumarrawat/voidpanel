from django.conf import settings
from django.db import models

# Create your models here.
class updates(models.Model):
    version = models.CharField(max_length=10,default=None)
    date = models.DateField(auto_now_add=True)



class Message(models.Model):
    text = models.TextField()  # Field for the message content
    title=models.CharField(max_length=60,default=None)
    date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the message is created
    photo = models.ImageField(upload_to='media/', null=True, blank=True)  # Optional photo field

    def __str__(self):
        return self.text[:10]  # Return the first 50 characters of the message

class Installed(models.Model):
    ip = models.GenericIPAddressField()
    number = models.IntegerField(default=0)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.ip} - {self.number}'
    
class admindocumentation(models.Model):
    text = models.TextField()  # Field for the message content
    link=models.CharField(max_length=60,default=None)
    date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the message is created

class clientdocumentation(models.Model):
    text = models.TextField()  # Field for the message content
    link=models.CharField(max_length=60,default=None)
    date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the message is created


class positive_review(models.Model):
    review = models.TextField()  # Field for the message content
    content = models.TextField(default=None)  
    user=models.CharField(max_length=60,default=None)
    date = models.DateField(auto_now_add=True)


    def __str__(self):
        return self.user  

class negative_review(models.Model):
    review = models.TextField()  # Field for the message content
    content = models.TextField(default=None)  
    user=models.CharField(max_length=60,default=None)
    category=models.CharField(max_length=60,default=None)
    date = models.DateField(auto_now_add=True)

    

    def __str__(self):
        return self.user  


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    company_name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=80, blank=True, default='India')
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    portal_role = models.CharField(max_length=40, default='Account Owner')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} profile"


class HostingService(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended'),
    ]
    BILLING_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosting_services')
    service_name = models.CharField(max_length=120)
    domain = models.CharField(max_length=120)
    product_type = models.CharField(max_length=80, default='Shared Hosting')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CHOICES, default='monthly')
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    next_due_date = models.DateField()
    server_hostname = models.CharField(max_length=120, blank=True)
    panel_url = models.URLField(blank=True)
    server = models.ForeignKey('VoidPanelServer', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_services')
    storage_gb = models.PositiveIntegerField(default=25)
    bandwidth_gb = models.PositiveIntegerField(default=250)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service_name} ({self.user.username})"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('overdue', 'Overdue'),
        ('draft', 'Draft'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', '-created_at']

    def __str__(self):
        return self.invoice_number


class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('answered', 'Answered'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    ticket_number = models.CharField(max_length=30, unique=True)
    subject = models.CharField(max_length=180)
    department = models.CharField(max_length=80, default='Support')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    last_reply_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_reply_at']

    def __str__(self):
        return self.ticket_number


class PortalActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portal_activities')
    category = models.CharField(max_length=40, default='account')
    title = models.CharField(max_length=140)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class StaffRole(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    description = models.CharField(max_length=255, blank=True)
    can_manage_clients = models.BooleanField(default=False)
    can_manage_billing = models.BooleanField(default=False)
    can_manage_support = models.BooleanField(default=False)
    can_manage_infrastructure = models.BooleanField(default=False)
    can_manage_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class StaffProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.ForeignKey(StaffRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    display_title = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=80, blank=True)
    status_message = models.CharField(max_length=160, blank=True)
    is_portal_admin = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return self.display_title or self.user.username


class OutboundEmailProfile(models.Model):
    PURPOSE_CHOICES = [
        ('transactional', 'Transactional'),
        ('billing', 'Billing'),
        ('support', 'Support'),
        ('security', 'Security'),
        ('system', 'System Updates'),
        ('marketing', 'Marketing'),
        ('custom', 'Custom'),
    ]

    profile_name = models.CharField(max_length=120)
    purpose_category = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default='transactional')
    from_name = models.CharField(max_length=120, blank=True)
    from_email = models.EmailField()
    reply_to_email = models.EmailField(blank=True)
    smtp_host = models.CharField(max_length=160)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=160, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    send_on_purchase = models.BooleanField(default=True)
    send_on_invoice_created = models.BooleanField(default=True)
    send_on_payment_received = models.BooleanField(default=True)
    send_on_service_activated = models.BooleanField(default=True)
    send_on_service_suspended = models.BooleanField(default=False)
    send_on_service_unsuspended = models.BooleanField(default=False)
    send_on_service_terminated = models.BooleanField(default=False)
    send_on_ticket_opened = models.BooleanField(default=True)
    send_on_ticket_reply = models.BooleanField(default=True)
    send_on_login_success = models.BooleanField(default=False)
    send_on_password_reset = models.BooleanField(default=True)
    send_on_account_created = models.BooleanField(default=True)
    send_on_security_alert = models.BooleanField(default=True)
    send_on_system_update = models.BooleanField(default=False)
    send_on_domain_expiry_warning = models.BooleanField(default=True)
    send_on_ssl_expiry_warning = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'profile_name']

    def __str__(self):
        return self.profile_name


class VoidPanelServer(models.Model):
    name = models.CharField(max_length=120, unique=True, help_text="e.g., US-East Node 1")
    url = models.URLField(help_text="e.g., http://178.18.250.134:8080")
    api_key = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_connected = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class HostingPackage(models.Model):
    server = models.ForeignKey(VoidPanelServer, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages', help_text="Assigned server node for provisioning")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    short_description = models.CharField(max_length=180, blank=True)
    storage_gb = models.PositiveIntegerField(default=25)
    ram_gb = models.PositiveIntegerField(default=2)
    cpu_cores = models.PositiveIntegerField(default=1)
    bandwidth_label = models.CharField(max_length=40, default='500GB')
    allowed_domains = models.PositiveIntegerField(default=1)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'monthly_price']

    def __str__(self):
        return self.name


class HostingPricingSettings(models.Model):
    title = models.CharField(max_length=120, default='Primary Pricing Rules')
    storage_price_per_10gb = models.DecimalField(max_digits=8, decimal_places=2, default=1.50)
    ram_price_per_1gb = models.DecimalField(max_digits=8, decimal_places=2, default=4.00)
    cpu_price_per_core = models.DecimalField(max_digits=8, decimal_places=2, default=8.00)
    bandwidth_100gb_price = models.DecimalField(max_digits=8, decimal_places=2, default=5.00)
    bandwidth_500gb_price = models.DecimalField(max_digits=8, decimal_places=2, default=12.00)
    bandwidth_1000gb_price = models.DecimalField(max_digits=8, decimal_places=2, default=20.00)
    bandwidth_unmetered_price = models.DecimalField(max_digits=8, decimal_places=2, default=35.00)
    storage_min_gb = models.PositiveIntegerField(default=10)
    storage_max_gb = models.PositiveIntegerField(default=500)
    ram_min_gb = models.PositiveIntegerField(default=1)
    ram_max_gb = models.PositiveIntegerField(default=32)
    cpu_min_cores = models.PositiveIntegerField(default=1)
    cpu_max_cores = models.PositiveIntegerField(default=16)
    quarterly_discount_percent = models.PositiveIntegerField(default=0)
    annual_discount_percent = models.PositiveIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Hosting pricing settings'

    def __str__(self):
        return self.title


class TicketReply(models.Model):
    """A single reply in a support ticket thread (from client or staff)."""
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='replies',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ticket_replies',
    )
    is_staff_reply = models.BooleanField(default=False)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        prefix = '[Staff]' if self.is_staff_reply else '[Client]'
        return f"{prefix} {self.ticket.ticket_number} — {self.created_at:%Y-%m-%d %H:%M}"


class HostingOrder(models.Model):
    """Links a checkout session to a HostingService + Invoice before provisioning."""
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('paid', 'Paid'),
        ('provisioning', 'Provisioning'),
        ('active', 'Active'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hosting_orders',
    )
    package = models.ForeignKey(
        HostingPackage,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    service = models.OneToOneField(
        HostingService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order',
    )
    invoice = models.OneToOneField(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order',
    )
    domain = models.CharField(max_length=200)
    billing_cycle = models.CharField(max_length=20, default='monthly')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment')
    provision_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.pk} — {self.user.username} — {self.package.name}"
