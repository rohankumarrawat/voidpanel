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
