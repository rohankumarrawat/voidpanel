from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone




# Create your models here.
class quick(models.Model):
    hostname = models.CharField(max_length=255,default=False)
    nameserver1 = models.CharField(max_length=255,default=False)
    nameserver2 = models.CharField(max_length=255,default=False)
    email = models.EmailField(max_length=255,default=False)
    status = models.BooleanField(default=False)
    show = models.BooleanField(default=False)
    count=models.IntegerField(default=0)

    def __str__(self):
        return self.hostname
    
class portnumber(models.Model):
    number = models.CharField(max_length=255)
 
    

class package(models.Model):
    name = models.CharField(max_length=100, unique=True)
    storage = models.TextField(help_text="Storage in GB")
    ftp = models.TextField(help_text="Storage in GB")
    subdomain = models.TextField(help_text="Storage in GB")
    bandwidth = models.TextField(help_text="Bandwidth in GB")
    # domains_allowed = models.TextField(help_text="Number of domains allowed")
    email_accounts = models.TextField(help_text="Number of email accounts allowed")
    databases_allowed = models.TextField(help_text="Number of databases allowed")

    # ── Suite add-ons bundled with this hosting package ─────────
    includes_social    = models.BooleanField(default=False, help_text='Include Social Media Suite')
    social_plan        = models.CharField(max_length=50, blank=True, default='', help_text='Social plan slug e.g. starter/growth/agency')
    includes_seo       = models.BooleanField(default=False, help_text='Include SEO Suite')
    seo_plan           = models.CharField(max_length=50, blank=True, default='', help_text='SEO plan slug e.g. lite/standard/advanced')
    includes_marketing = models.BooleanField(default=False, help_text='Include Marketing Suite')
    marketing_plan     = models.CharField(max_length=50, blank=True, default='', help_text='Marketing plan slug e.g. starter/pro/agency')

    def __str__(self):
        return self.name

    def included_suites(self):
        """Returns list of (suite_key, plan_slug) for all included suites."""
        out = []
        if self.includes_social:    out.append(('social',    self.social_plan    or 'starter'))
        if self.includes_seo:       out.append(('seo',       self.seo_plan       or 'lite'))
        if self.includes_marketing: out.append(('marketing', self.marketing_plan  or 'starter'))
        return out

class user(models.Model):
    username         = models.CharField(max_length=150)
    email            = models.CharField(max_length=150)
    domain           = models.CharField(max_length=150)
    hosting_package  = models.CharField(max_length=150)
    is_active        = models.BooleanField(default=True)
    shell            = models.BooleanField(default=False)
    is_superuser     = models.BooleanField(default=False)
    status           = models.BooleanField(default=True)
    # Reseller relationship — null for admin-owned accounts
    reseller         = models.ForeignKey(
        'ResellerProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sub_accounts',
        help_text='If set, this account belongs to this reseller\'s pool',
    )
    notes            = models.TextField(blank=True, default='')

    def __str__(self):
        return self.domain


# ═══════════════════════════════════════════════════════════
#  RESELLER PACKAGE
# ═══════════════════════════════════════════════════════════

class ResellerPackage(models.Model):
    """
    A hosting package defined BY a reseller for their sub-accounts.
    Scoped per reseller — they cannot see/use each other's packages.
    """
    reseller        = models.ForeignKey(
        'ResellerProfile',
        on_delete=models.CASCADE,
        related_name='packages',
        help_text='Reseller who owns this package',
    )
    name            = models.CharField(max_length=100, help_text='Package display name')
    storage_gb      = models.PositiveIntegerField(default=1,  help_text='Disk quota in GB')
    bandwidth_gb    = models.PositiveIntegerField(default=10, help_text='Monthly bandwidth in GB')
    email_accounts  = models.PositiveIntegerField(default=5,  help_text='Max email accounts')
    databases       = models.PositiveIntegerField(default=2,  help_text='Max databases')
    subdomains      = models.PositiveIntegerField(default=5,  help_text='Max subdomains')
    ftp_accounts    = models.PositiveIntegerField(default=2,  help_text='Max FTP accounts')
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together     = ('reseller', 'name')
        verbose_name        = 'Reseller Package'
        verbose_name_plural = 'Reseller Packages'
        ordering            = ['name']

    def __str__(self):
        return f"{self.name} [{self.reseller.auth_user.username}]"


# ═══════════════════════════════════════════════════════════
#  RESELLER PROFILE
# ═══════════════════════════════════════════════════════════

class ResellerProfile(models.Model):
    """
    Elevates a Django auth.User to a Reseller.
    Created by Super Admin when provisioning a reseller account.
    The linked `user` record is the reseller's OWN hosting account.
    Sub-accounts they create are tagged via user.reseller FK.
    """
    # Link to Django auth user (for login/session)
    auth_user        = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reseller_profile',
        help_text='Django auth user that logs in as reseller',
    )
    # Branding
    company_name     = models.CharField(max_length=120, blank=True, default='')
    branding_name    = models.CharField(
        max_length=60, blank=True, default='VoidPanel',
        help_text='Name shown to reseller in their dashboard',
    )
    # Resource pool
    storage_quota_gb = models.PositiveIntegerField(
        default=10,
        help_text='Total GB of disk space this reseller can allocate across ALL sub-accounts',
    )
    max_accounts     = models.PositiveIntegerField(
        default=5,
        help_text='Maximum number of hosting sub-accounts this reseller can create',
    )
    # State
    is_active        = models.BooleanField(default=True)
    notes            = models.TextField(blank=True, default='')
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Reseller Profile'
        verbose_name_plural = 'Reseller Profiles'

    def __str__(self):
        return f"{self.auth_user.username} [{self.storage_quota_gb} GB / {self.max_accounts} accts]"

    # ── Quota helpers ──────────────────────────────────────────────────────────

    def get_used_storage_gb(self):
        """Sum actual disk usage (GB) of all sub-account home directories."""
        import os
        try:
            from voidplatform.config import paths
            from function import get_directory_size_in_mb
        except ImportError:
            return 0.0
        total_mb = 0.0
        for sub in self.sub_accounts.filter(is_active=True):
            home = os.path.join(paths.HOME_BASE, sub.username)
            try:
                total_mb += get_directory_size_in_mb(home)
            except Exception:
                pass
        return round(total_mb / 1024, 2)

    def get_account_count(self):
        return self.sub_accounts.filter(is_active=True).count()

    def get_storage_percent(self):
        """0-100 integer for progress bars."""
        if self.storage_quota_gb <= 0:
            return 100
        used = self.get_used_storage_gb()
        return min(int((used / self.storage_quota_gb) * 100), 100)

    def get_account_percent(self):
        if self.max_accounts <= 0:
            return 100
        return min(int((self.get_account_count() / self.max_accounts) * 100), 100)

    def has_account_slot(self):
        """True if at least one more account can be created."""
        return self.get_account_count() < self.max_accounts

    def has_storage_for(self, extra_gb: float) -> bool:
        """True if adding extra_gb would not exceed the pool."""
        return (self.get_used_storage_gb() + extra_gb) <= self.storage_quota_gb

    def storage_remaining_gb(self):
        return max(0.0, self.storage_quota_gb - self.get_used_storage_gb())

class LoginActivity(models.Model):
    user = models.CharField(max_length=150)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=150)
    successful = models.BooleanField(default=True, help_text="Whether the login attempt was successful")


class domain(models.Model):
    domain = models.CharField(max_length=100, unique=True)
    email = models.CharField(max_length=255)
    php = models.CharField(max_length=10,default='8.3')
    dir = models.CharField(max_length=255)
    sslstatus = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    userdomain = models.BooleanField(default=False)
   
    def __str__(self):
        return self.domain
    
class allemail(models.Model):
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=255)
    domain = models.CharField(max_length=255)
    
   
    def __str__(self):
        return self.email


class cron(models.Model):
    domain = models.CharField(max_length=100)
    duratioin = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
   
    def __str__(self):
        return self.domain
    
class subdomainname(models.Model):
    domain = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    php = models.CharField(max_length=10,default='8.3')
    sslstatus = models.BooleanField(default=False)
    
   
    def __str__(self):
        return self.domain
    


class pythonname(models.Model):
    domain = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    main = models.CharField(max_length=100,default=None)
   
    def __str__(self):
        return self.domain
    
class mernname(models.Model):
    domain = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    main = models.CharField(max_length=100, null=True, blank=True)
    port = models.CharField(max_length=100, null=True, blank=True)
   
    def __str__(self):
        return self.domain
    
class phpextentions(models.Model):
    name = models.CharField(max_length=10)
    extentions = models.TextField(default=None)

class phpversion(models.Model):
    name = models.CharField(max_length=10)

class redir(models.Model):
    maindomain = models.CharField(max_length=100)
    domain = models.CharField(max_length=100)
    path = models.CharField(max_length=255)
    newpath = models.CharField(max_length=255)
    
    
   
    def __str__(self):
        return self.domain
   
class firewall(models.Model):
    status = models.BooleanField()

class ftp(models.Model):
    status = models.BooleanField()

class ftpaccount(models.Model):
    main = models.CharField(max_length=150, null=True, blank=True)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=150)
    storage = models.CharField(max_length=150)
    

    def __str__(self):
        return self.username

class EmailConfig(models.Model):
    hourly_limit = models.IntegerField(default=100, help_text="Max outgoing emails per hour")
    daily_limit = models.IntegerField(default=1000, help_text="Max outgoing emails per day")
    default_quota_mb = models.IntegerField(default=1024, help_text="Max MB per inbox")
    max_attachment_size_mb = models.IntegerField(default=50, help_text="Max attachment size in MB")
    enable_antispam = models.BooleanField(default=True, help_text="Enable SpamAssassin checks")
    spam_score_threshold = models.FloatField(default=5.0, help_text="Score before rejection")
    enforce_dkim_spf = models.BooleanField(default=True, help_text="Reject emails failing DKIM/SPF")
    max_concurrent_connections = models.IntegerField(default=20, help_text="SMTP concurrent limits")
    catch_all_capability = models.BooleanField(default=False, help_text="Allow wildcard aliases")
    allow_autoresponders = models.BooleanField(default=True, help_text="Allow vacation replies")
    enable_smtp_relay = models.BooleanField(default=False, help_text="Enable system-wide Postfix SMTP Relay")
    smtp_relay_host = models.CharField(max_length=255, default="[smtp.sendgrid.net]:587", help_text="SMTP Relay Host, e.g., [smtp.sendgrid.net]:587")
    smtp_relay_username = models.CharField(max_length=255, default="", blank=True, help_text="SMTP Relay Username")
    smtp_relay_password = models.CharField(max_length=255, default="", blank=True, help_text="SMTP Relay Password/API Key")

    def __str__(self):
        return "Global Email Configuration"


class ActivityLog(models.Model):
    """Structured audit log for all provisioning and administrative events."""

    class Level(models.TextChoices):
        SUCCESS = 'success', 'Success'
        INFO    = 'info',    'Info'
        WARNING = 'warning', 'Warning'
        ERROR   = 'error',   'Error'

    class Category(models.TextChoices):
        DOMAIN  = 'domain',  'Domain'
        PYTHON  = 'python',  'Python App'
        MERN    = 'mern',    'MERN Stack'
        EMAIL   = 'email',   'Email'
        DB      = 'db',      'Database'
        SSL     = 'ssl',     'SSL'
        FTP     = 'ftp',     'FTP'
        SYSTEM  = 'system',  'System'
        NGINX   = 'nginx',   'Nginx'
        BACKUP  = 'backup',  'Backup'

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    level     = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    category  = models.CharField(max_length=15, choices=Category.choices, default=Category.SYSTEM)
    domain    = models.CharField(max_length=255, blank=True, default='')
    username  = models.CharField(max_length=150, blank=True, default='')
    action    = models.CharField(max_length=255)
    detail    = models.TextField(blank=True, default='')
    ip        = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        ordering = ['-timestamp']
        indexes  = [
            models.Index(fields=['domain', '-timestamp']),
            models.Index(fields=['level',  '-timestamp']),
        ]

    def __str__(self):
        return f'[{self.level.upper()}] {self.action} ({self.domain})'


class PanelLicense(models.Model):
    """Stores the single activation license for this VoidPanel installation."""
    STATUS_ACTIVE    = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_EXPIRED   = 'expired'
    STATUS_INVALID   = 'invalid'

    key          = models.CharField(max_length=128, unique=True)
    email        = models.EmailField(help_text="voidpanel.com account email used to activate", blank=True)
    status       = models.CharField(max_length=20, default=STATUS_ACTIVE)
    hostname     = models.CharField(max_length=255, blank=True)
    issued_at    = models.DateTimeField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)

    # ── Tier & Feature Gating (populated nightly by refresh_license) ──────────
    tier          = models.CharField(
        max_length=20, default='starter',
        help_text='License tier: starter / pro / advanced / unlimited',
    )
    is_trial      = models.BooleanField(default=False)
    expires_at    = models.DateTimeField(null=True, blank=True)
    features_json = models.JSONField(
        default=dict, blank=True,
        help_text='Feature flags dict from api/license/validate',
    )

    class Meta:
        verbose_name = "Panel License"
        verbose_name_plural = "Panel Licenses"

    def __str__(self):
        return f"{self.key[:20]}... [{self.status}] tier={self.tier}"

    @property
    def is_valid(self):
        return self.status == self.STATUS_ACTIVE

    def has_feature(self, key: str, default: bool = False) -> bool:
        """Return True if the given feature flag is enabled for this license."""
        return bool(self.features_json.get(key, default))

    @property
    def white_label_enabled(self):
        return self.has_feature('white_label')

    @property
    def days_remaining(self):
        if not self.expires_at:
            return None
        from django.utils import timezone as _tz
        delta = self.expires_at - _tz.now()
        return max(0, delta.days)


class PanelBranding(models.Model):
    """
    White-label branding settings singleton.
    Only takes effect when the active license has white_label=True.
    """
    panel_name           = models.CharField(max_length=60, default='VoidPanel',
                               help_text='Brand name in sidebar and browser title')
    panel_logo_url       = models.URLField(blank=True, default='',
                               help_text='URL to custom logo image (leave blank for default)')
    favicon_url          = models.URLField(blank=True, default='',
                               help_text='URL to custom favicon .ico/.png (32x32)')
    primary_color        = models.CharField(max_length=20, default='#6366f1',
                               help_text='CSS hex accent colour')
    support_url          = models.URLField(blank=True, default='',
                               help_text='Support/helpdesk link (replaces default tickets link)')
    hide_voidpanel_badge = models.BooleanField(default=False,
                               help_text='Hide "Powered by VoidPanel" footer badge')
    updated_at           = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Panel Branding'
        verbose_name_plural = 'Panel Branding'

    def __str__(self):
        return f"Branding: {self.panel_name}"

    @classmethod
    def get(cls):
        """Returns the singleton branding object, creating defaults if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CloudBackupConfig(models.Model):
    """
    Per-domain cloud backup sync configuration.
    Stores credentials for Google Cloud Storage or Amazon S3.
    Managed via the Backup Manager UI in the control panel.
    """
    PROVIDER_GCS = 'gcs'
    PROVIDER_S3  = 's3'
    PROVIDER_CHOICES = [
        (PROVIDER_GCS, 'Google Cloud Storage'),
        (PROVIDER_S3,  'Amazon S3'),
    ]

    SCHEDULE_DAILY  = '0 2 * * *'
    SCHEDULE_WEEKLY = '0 2 * * 0'
    SCHEDULE_CHOICES = [
        ('daily',    'Daily at 2:00 AM'),
        ('weekly',   'Weekly (Sunday 2:00 AM)'),
        ('custom',   'Custom Cron'),
    ]

    domain   = models.CharField(max_length=255, unique=True, help_text="Domain this config belongs to")
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES, default=PROVIDER_GCS)

    # Google Cloud Storage
    gcs_bucket   = models.CharField(max_length=220, blank=True, help_text="GCS bucket name")
    gcs_key_json = models.TextField(blank=True, help_text="Service Account JSON key (paste full contents)")

    # Amazon S3
    s3_bucket      = models.CharField(max_length=220, blank=True)
    s3_access_key  = models.CharField(max_length=220, blank=True)
    s3_secret_key  = models.CharField(max_length=255, blank=True)
    s3_region      = models.CharField(max_length=60, blank=True, default='us-east-1')

    # Automation
    auto_backup_enabled  = models.BooleanField(default=False)
    auto_schedule_preset = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default='daily')
    auto_schedule_cron   = models.CharField(max_length=100, blank=True, default='0 2 * * *',
                                            help_text="Cron string (used when preset=custom)")
    sync_after_backup    = models.BooleanField(default=False,
                                               help_text="Auto-push to cloud immediately after each backup")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Cloud Backup Config"
        verbose_name_plural = "Cloud Backup Configs"

    def __str__(self):
        return f"{self.domain} → {self.get_provider_display()}"

    @property
    def is_configured(self):
        if self.provider == self.PROVIDER_GCS:
            return bool(self.gcs_bucket and self.gcs_key_json)
        return bool(self.s3_bucket and self.s3_access_key and self.s3_secret_key)

    def get_effective_cron(self):
        if self.auto_schedule_preset == 'daily':
            return self.SCHEDULE_DAILY
        elif self.auto_schedule_preset == 'weekly':
            return self.SCHEDULE_WEEKLY
        return self.auto_schedule_cron or self.SCHEDULE_DAILY


class InstalledScript(models.Model):
    """
    Tracks one-click script installations (WordPress, Ghost, Nextcloud, etc.)
    per domain so users can manage or uninstall them later.
    """
    STATUS_INSTALLING = 'installing'
    STATUS_ACTIVE     = 'active'
    STATUS_FAILED     = 'failed'
    STATUS_DELETED    = 'deleted'
    STATUS_CHOICES = [
        (STATUS_INSTALLING, 'Installing'),
        (STATUS_ACTIVE,     'Active'),
        (STATUS_FAILED,     'Failed'),
        (STATUS_DELETED,    'Deleted'),
    ]

    # Core
    domain      = models.CharField(max_length=255, db_index=True, help_text="The main domain this belongs to")
    username    = models.CharField(max_length=150, help_text="System user (dir) who owns this install")
    script_name = models.CharField(max_length=100, help_text="e.g. 'wordpress', 'ghost', 'nextcloud'")
    install_url = models.CharField(max_length=255, help_text="The URL where the script is installed (domain or subdomain)")
    install_dir = models.CharField(max_length=512, blank=True, help_text="Filesystem path, e.g. /home/user/public_html")

    # Admin credentials (hashed at rest is ideal; stored here for display)
    admin_user  = models.CharField(max_length=150, blank=True)
    admin_email = models.CharField(max_length=255, blank=True)
    admin_url   = models.CharField(max_length=512, blank=True, help_text="e.g. https://domain.com/wp-admin")

    # DB info
    db_name     = models.CharField(max_length=100, blank=True)
    db_user     = models.CharField(max_length=100, blank=True)
    db_pass     = models.CharField(max_length=100, blank=True)

    # State
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INSTALLING)
    log         = models.TextField(blank=True, default='', help_text="Installation log / error output")

    installed_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-installed_at']
        verbose_name        = 'Installed Script'
        verbose_name_plural = 'Installed Scripts'

    def __str__(self):
        return f"{self.script_name} @ {self.install_url} [{self.status}]"

    @property
    def script_display_name(self):
        names = {
            'wordpress':  'WordPress',
            'ghost':      'Ghost',
            'nextcloud':  'Nextcloud',
            'prestashop': 'PrestaShop',
            'opencart':   'OpenCart',
            'whmcs':      'WHMCS',
            'boxbilling':  'BoxBilling',
            'gitea':      'Gitea',
            'uptimekuma': 'Uptime Kuma',
            'n8n':        'n8n',
            'vscode':     'VS Code Server',
            'vaultwarden':'Vaultwarden',
            'bookstack':  'BookStack',
            'matomo':     'Matomo',
            'appwrite':   'Appwrite',
            'jellyfin':   'Jellyfin',
            'metabase':   'Metabase',
            'postiz':     'Postiz',
            'strapi':     'Strapi',
        }
        return names.get(self.script_name, self.script_name.title())


# ═══════════════════════════════════════════════════════════
#  PANEL API KEY
# ═══════════════════════════════════════════════════════════

import secrets as _secrets

class PanelAPIKey(models.Model):
    """
    Stores the single provisioning API key for this VoidPanel installation.
    The website (portal) must send this key in the X-VoidPanel-Key header
    when calling /api/provision/create/ and /api/license/validate/.

    Only one row should exist (singleton pattern via get_or_create).
    """
    key        = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    label      = models.CharField(
        max_length=120, blank=True, default='Default Provisioning Key',
        help_text='Friendly label for this key',
    )

    class Meta:
        verbose_name        = 'Panel API Key'
        verbose_name_plural = 'Panel API Keys'

    def __str__(self):
        return f'{self.label} ({self.key[:12]}…)'

    @classmethod
    def get_or_create_default(cls):
        """Return (instance, created) for the singleton API key row."""
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={'key': _secrets.token_urlsafe(40)},
        )
        return obj, created

    @classmethod
    def current_key(cls) -> str:
        """Return the current active API key string."""
        obj, _ = cls.get_or_create_default()
        return obj.key

    def regenerate(self):
        """Replace the key with a new random token."""
        self.key = _secrets.token_urlsafe(40)
        self.save(update_fields=['key', 'updated_at'])
        return self.key


# ═══════════════════════════════════════════════════════════
#  API TOKEN (v2 — per-key permission scopes)
# ═══════════════════════════════════════════════════════════

from django.utils import timezone as _tz

# All valid scope strings
ALL_SCOPES = [
    'accounts.create', 'accounts.list', 'accounts.suspend', 'accounts.unsuspend',
    'accounts.terminate', 'accounts.change_package', 'accounts.change_password',
    'dns.list', 'dns.create', 'dns.delete',
    'email.list', 'email.create', 'email.delete', 'email.change_password', 'email.suspend',
    'databases.list', 'databases.create', 'databases.delete',
    'ssl.list', 'ssl.issue',
    'ftp.list', 'ftp.create', 'ftp.delete',
    'subdomains.list', 'subdomains.create', 'subdomains.delete',
    'php.get', 'php.set',
    'backups.list', 'backups.create',
    'cron.list', 'cron.create', 'cron.delete',
    'server.status',
    'packages.list',
    # WordPress scopes
    'wordpress.status', 'wordpress.install', 'wordpress.uninstall', 'wordpress.reset_password',
]

# Scopes that resellers are NOT allowed to use
RESELLER_FORBIDDEN_SCOPES = {'server.status'}


class APIToken(models.Model):
    """
    Per-key API token with granular permission scopes.
    Superadmin keys: reseller=None, owner_type='superadmin'
    Reseller keys: reseller=<ResellerProfile>, owner_type='reseller'
    Reseller keys are restricted to their own sub-account pool.
    """
    OWNER_SUPERADMIN = 'superadmin'
    OWNER_RESELLER   = 'reseller'
    OWNER_CHOICES    = [
        (OWNER_SUPERADMIN, 'Super Admin'),
        (OWNER_RESELLER,   'Reseller'),
    ]

    key          = models.CharField(max_length=80, unique=True, db_index=True)
    label        = models.CharField(max_length=120, help_text='Friendly name for this token')
    owner_type   = models.CharField(max_length=20, choices=OWNER_CHOICES, default=OWNER_SUPERADMIN)
    reseller     = models.ForeignKey(
        'ResellerProfile',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='api_tokens',
        help_text='If set, this token belongs to this reseller',
    )
    scopes       = models.JSONField(
        default=list,
        help_text='List of allowed scope strings e.g. ["accounts.list","dns.create"]',
    )
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by   = models.CharField(max_length=150, blank=True, help_text='Username who created this token')

    class Meta:
        verbose_name        = 'API Token'
        verbose_name_plural = 'API Tokens'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.label} ({self.owner_type}) [{self.key[:12]}…]'

    @classmethod
    def generate(cls, label, owner_type, scopes, reseller=None, created_by=''):
        """Create and return a new APIToken with a random key."""
        # Sanitise scopes
        valid = set(ALL_SCOPES)
        if owner_type == cls.OWNER_RESELLER:
            valid -= RESELLER_FORBIDDEN_SCOPES
        clean_scopes = [s for s in scopes if s in valid]
        obj = cls.objects.create(
            key         = _secrets.token_urlsafe(48),
            label       = label,
            owner_type  = owner_type,
            reseller    = reseller,
            scopes      = clean_scopes,
            created_by  = created_by,
        )
        return obj

    def has_scope(self, scope: str) -> bool:
        return scope in (self.scopes or [])

    def touch(self):
        self.last_used_at = _tz.now()
        self.save(update_fields=['last_used_at'])


# ═══════════════════════════════════════════════════════════
#  SUPPORT TICKET SYSTEM (local, no external API needed)
# ═══════════════════════════════════════════════════════════

import uuid as _uuid

class SupportTicket(models.Model):
    STATUS_OPEN       = 'open'
    STATUS_INPROGRESS = 'in_progress'
    STATUS_RESOLVED   = 'resolved'
    STATUS_CLOSED     = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN,       'Open'),
        (STATUS_INPROGRESS, 'In Progress'),
        (STATUS_RESOLVED,   'Resolved'),
        (STATUS_CLOSED,     'Closed'),
    ]

    PRIORITY_LOW    = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH   = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW,    'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH,   'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    DEPT_TECHNICAL = 'Technical Support'
    DEPT_BILLING   = 'Billing'
    DEPT_SALES     = 'Sales'
    DEPT_ABUSE     = 'Abuse'
    DEPT_CHOICES   = [
        (DEPT_TECHNICAL, 'Technical Support'),
        (DEPT_BILLING,   'Billing'),
        (DEPT_SALES,     'Sales'),
        (DEPT_ABUSE,     'Abuse'),
    ]

    ticket_id   = models.CharField(max_length=16, unique=True, editable=False)
    subject     = models.CharField(max_length=255)
    department  = models.CharField(max_length=60, choices=DEPT_CHOICES, default=DEPT_TECHNICAL)
    priority    = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    message     = models.TextField()
    created_by  = models.CharField(max_length=150, help_text='Username of superadmin who created it')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
        ordering            = ['-created_at']

    def __str__(self):
        return f'[{self.ticket_id}] {self.subject}'

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = 'TKT-' + str(_uuid.uuid4()).upper()[:8]
        super().save(*args, **kwargs)


class TicketReply(models.Model):
    ticket     = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    author     = models.CharField(max_length=150)
    is_staff   = models.BooleanField(default=False)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Reply by {self.author} on {self.ticket}'


# ═══════════════════════════════════════════════════════════
#  SOCIAL MEDIA MANAGEMENT
# ═══════════════════════════════════════════════════════════

SOCIAL_PLATFORM_CHOICES = [
    ('fb',  'Facebook'),
    ('ig',  'Instagram'),
    ('tw',  'Twitter / X'),
    ('li',  'LinkedIn'),
    ('pi',  'Pinterest'),
    ('tt',  'TikTok'),
    ('yt',  'YouTube'),
    ('th',  'Threads'),
    ('gb',  'Google Business'),
]

SOCIAL_POST_STATUS = [
    ('draft',      'Draft'),
    ('scheduled',  'Scheduled'),
    ('published',  'Published'),
    ('failed',     'Failed'),
    ('cancelled',  'Cancelled'),
]


class SocialAccount(models.Model):
    """
    A connected social media account belonging to a hosting domain/user.
    One user can have multiple accounts per platform (e.g. 2 FB pages).
    """
    domain              = models.CharField(max_length=255, db_index=True)
    username            = models.CharField(max_length=150)       # VoidPanel username
    platform            = models.CharField(max_length=4, choices=SOCIAL_PLATFORM_CHOICES)
    account_id          = models.CharField(max_length=255, blank=True)
    account_name        = models.CharField(max_length=255, blank=True)
    account_username    = models.CharField(max_length=255, blank=True)
    profile_picture_url = models.URLField(blank=True)
    followers_count     = models.BigIntegerField(default=0)
    following_count     = models.BigIntegerField(default=0)
    # OAuth tokens — stored encrypted in practice; plaintext for dev
    access_token        = models.TextField(blank=True)
    refresh_token       = models.TextField(blank=True)
    token_expiry        = models.DateTimeField(null=True, blank=True)
    # FB-specific — for page tokens
    page_id             = models.CharField(max_length=255, blank=True)
    page_name           = models.CharField(max_length=255, blank=True)
    is_active           = models.BooleanField(default=True)
    connected_at        = models.DateTimeField(auto_now_add=True)
    last_synced_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering            = ['platform', 'account_name']
        verbose_name        = 'Social Account'
        verbose_name_plural = 'Social Accounts'

    def __str__(self):
        return f'{self.get_platform_display()} — {self.account_name} ({self.domain})'

    @property
    def platform_color(self):
        colors = {
            'fb': '#1877F2', 'ig': '#E1306C', 'tw': '#1DA1F2',
            'li': '#0A66C2', 'pi': '#E60023', 'tt': '#010101',
            'yt': '#FF0000', 'th': '#000000', 'gb': '#4285F4',
        }
        return colors.get(self.platform, '#6366f1')

    @property
    def platform_icon(self):
        icons = {
            'fb': 'fa-brands fa-facebook-f',
            'ig': 'fa-brands fa-instagram',
            'tw': 'fa-brands fa-x-twitter',
            'li': 'fa-brands fa-linkedin-in',
            'pi': 'fa-brands fa-pinterest-p',
            'tt': 'fa-brands fa-tiktok',
            'yt': 'fa-brands fa-youtube',
            'th': 'fa-brands fa-threads',
            'gb': 'fa-brands fa-google',
        }
        return icons.get(self.platform, 'fa-solid fa-share-nodes')


class SocialPost(models.Model):
    """
    A single post that can be published to one or more connected social accounts.
    """
    domain          = models.CharField(max_length=255, db_index=True)
    username        = models.CharField(max_length=150)
    accounts        = models.ManyToManyField(SocialAccount, blank=True, related_name='posts')
    caption_text    = models.TextField(blank=True)
    first_comment   = models.TextField(blank=True, help_text='First comment (hashtag trick)')
    media_urls      = models.JSONField(default=list, blank=True)   # list of file paths
    link_url        = models.URLField(blank=True)
    link_title      = models.CharField(max_length=255, blank=True)
    link_description= models.TextField(blank=True)
    link_thumbnail  = models.URLField(blank=True)
    status          = models.CharField(max_length=12, choices=SOCIAL_POST_STATUS, default='draft', db_index=True)
    scheduled_at    = models.DateTimeField(null=True, blank=True)
    published_at    = models.DateTimeField(null=True, blank=True)
    platform_post_ids = models.JSONField(default=dict, blank=True)  # {fb:"xxx", ig:"yyy"}
    error_message   = models.TextField(blank=True)
    is_recurring    = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=50, blank=True)  # daily|weekly|monthly
    # Aggregated metrics (refreshed from API)
    likes_count     = models.BigIntegerField(default=0)
    reach_count     = models.BigIntegerField(default=0)
    comments_count  = models.BigIntegerField(default=0)
    impressions_count = models.BigIntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Social Post'
        verbose_name_plural = 'Social Posts'

    def __str__(self):
        return f'[{self.status}] {self.domain} — {self.caption_text[:60]}'

    @property
    def platform_list(self):
        return list(self.accounts.values_list('platform', flat=True).distinct())


class SocialMediaAPIConfig(models.Model):
    """
    Singleton — admin configures OAuth app credentials for each platform.
    Stored once for the whole VoidPanel installation.
    """
    # Facebook & Instagram (same Meta app)
    facebook_app_id         = models.CharField(max_length=255, blank=True)
    facebook_app_secret     = models.CharField(max_length=255, blank=True)
    instagram_app_id        = models.CharField(max_length=255, blank=True)
    instagram_app_secret    = models.CharField(max_length=255, blank=True)
    # Twitter / X
    twitter_api_key         = models.CharField(max_length=255, blank=True)
    twitter_api_secret      = models.CharField(max_length=255, blank=True)
    twitter_bearer_token    = models.CharField(max_length=512, blank=True)
    # LinkedIn
    linkedin_client_id      = models.CharField(max_length=255, blank=True)
    linkedin_client_secret  = models.CharField(max_length=255, blank=True)
    # Pinterest
    pinterest_app_id        = models.CharField(max_length=255, blank=True)
    pinterest_app_secret    = models.CharField(max_length=255, blank=True)
    # TikTok
    tiktok_client_key       = models.CharField(max_length=255, blank=True)
    tiktok_client_secret    = models.CharField(max_length=255, blank=True)
    # YouTube / Google
    google_client_id        = models.CharField(max_length=255, blank=True)
    google_client_secret    = models.CharField(max_length=255, blank=True)
    # Threads (Meta)
    threads_app_id          = models.CharField(max_length=255, blank=True)
    threads_app_secret      = models.CharField(max_length=255, blank=True)
    # Feature flags
    enabled_platforms       = models.JSONField(
        default=list,
        help_text='List of enabled platform codes e.g. ["fb","ig","tw"]'
    )
    is_active               = models.BooleanField(default=True)
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Social Media API Config'
        verbose_name_plural = 'Social Media API Config'

    def __str__(self):
        return f'Social Media API Config (updated {self.updated_at})'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        import requests
        lic = PanelLicense.objects.first()
        headers = {}
        params = {}
        if lic:
            headers['Authorization'] = f'Bearer {lic.key}'
            headers['X-VoidPanel-License'] = lic.key
            params['license'] = lic.key
        try:
            r = requests.get('https://voidpanel.com/api/social/platform-config/', headers=headers, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                # Only sync enabled_platforms — secrets are NEVER sent by the API.
                # OAuth credentials stay on voidpanel.com and are used via the relay flow.
                obj.enabled_platforms = data.get('enabled_platforms', obj.enabled_platforms)
                obj.save()
        except Exception:
            pass
        return obj



# ── Per-Domain Social API Configuration (user-managed) ────────────────────────

class DomainSocialAPIConfig(models.Model):
    """
    Per-domain social media API credentials entered by the user directly.
    Each user/domain can configure their own OAuth app keys for each platform,
    enabling direct OAuth flows without relying on the voidpanel.com relay.
    """
    domain              = models.CharField(max_length=255, db_index=True, unique=True)
    username            = models.CharField(max_length=150)

    # ── Facebook & Instagram (same Meta Developer App) ─────────────
    facebook_app_id     = models.CharField(max_length=255, blank=True)
    facebook_app_secret = models.CharField(max_length=255, blank=True)

    # ── Twitter / X ────────────────────────────────────────────────
    twitter_api_key         = models.CharField(max_length=255, blank=True)
    twitter_api_secret      = models.CharField(max_length=255, blank=True)
    twitter_bearer_token    = models.CharField(max_length=512, blank=True)
    twitter_access_token    = models.CharField(max_length=512, blank=True)
    twitter_access_secret   = models.CharField(max_length=512, blank=True)

    # ── LinkedIn ───────────────────────────────────────────────────
    linkedin_client_id      = models.CharField(max_length=255, blank=True)
    linkedin_client_secret  = models.CharField(max_length=255, blank=True)

    # ── Pinterest ──────────────────────────────────────────────────
    pinterest_app_id        = models.CharField(max_length=255, blank=True)
    pinterest_app_secret    = models.CharField(max_length=255, blank=True)

    # ── TikTok ────────────────────────────────────────────────────
    tiktok_client_key       = models.CharField(max_length=255, blank=True)
    tiktok_client_secret    = models.CharField(max_length=255, blank=True)

    # ── YouTube / Google ──────────────────────────────────────────
    google_client_id        = models.CharField(max_length=255, blank=True)
    google_client_secret    = models.CharField(max_length=255, blank=True)

    # ── Threads (Meta — uses same Facebook app) ───────────────────
    # Threads uses the same Meta App ID & Secret as Facebook

    # ── Redirect URI (set by user in their developer console) ─────
    redirect_uri            = models.URLField(blank=True, help_text='Your OAuth callback URL — copy from your developer app settings')

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Domain Social API Config'
        verbose_name_plural = 'Domain Social API Configs'

    def __str__(self):
        return f'Social API Config — {self.domain}'

    @classmethod
    def get_for_domain(cls, domain):
        obj, _ = cls.objects.get_or_create(domain=domain, defaults={'username': ''})
        return obj

    def has_platform(self, platform):
        """Return True if user has entered credentials for this platform."""
        checks = {
            'fb':  bool(self.facebook_app_id and self.facebook_app_secret),
            'ig':  bool(self.facebook_app_id and self.facebook_app_secret),
            'tw':  bool(self.twitter_api_key and self.twitter_api_secret),
            'li':  bool(self.linkedin_client_id and self.linkedin_client_secret),
            'pi':  bool(self.pinterest_app_id and self.pinterest_app_secret),
            'tt':  bool(self.tiktok_client_key and self.tiktok_client_secret),
            'yt':  bool(self.google_client_id and self.google_client_secret),
            'th':  bool(self.facebook_app_id and self.facebook_app_secret),
        }
        return checks.get(platform, False)

    @property
    def configured_platforms(self):
        return [p for p in ['fb','ig','tw','li','pi','tt','yt','th'] if self.has_platform(p)]


# ── Marketing Hub Models ───────────────────────────────────────────────────────


class SMSGatewayConfig(models.Model):
    """Stores SMS API gateway credentials per user/domain."""
    PROVIDER_CHOICES = [
        ('twilio',    'Twilio'),
        ('msg91',     'MSG91'),
        ('vonage',    'Vonage (Nexmo)'),
        ('textlocal', 'TextLocal'),
        ('plivo',     'Plivo'),
        ('aws_sns',   'AWS SNS'),
    ]
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sms_gateways')
    domain      = models.CharField(max_length=253)
    provider    = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    api_key     = models.CharField(max_length=255, help_text='API Key / Account SID')
    api_secret  = models.CharField(max_length=255, blank=True, help_text='API Secret / Auth Token')
    sender_id   = models.CharField(max_length=20, blank=True, help_text='Sender ID or Phone Number (e.g. +1234567890)')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'domain', 'provider')

    def __str__(self):
        return f"{self.get_provider_display()} — {self.domain}"


class CustomSMTPConfig(models.Model):
    """Stores custom external SMTP credentials for email campaigns."""
    ENCRYPTION_CHOICES = [('tls', 'TLS (587)'), ('ssl', 'SSL (465)'), ('none', 'None (25)')]
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='custom_smtp_configs')
    domain       = models.CharField(max_length=253)
    label        = models.CharField(max_length=100, help_text='Display name, e.g. "My Gmail"')
    from_email   = models.EmailField(help_text='From address shown to recipients')
    smtp_host    = models.CharField(max_length=255, help_text='e.g. smtp.gmail.com')
    smtp_port    = models.PositiveIntegerField(default=587)
    smtp_user    = models.CharField(max_length=255, help_text='SMTP login username')
    smtp_password = models.CharField(max_length=255, help_text='SMTP login password or app password')
    encryption   = models.CharField(max_length=4, choices=ENCRYPTION_CHOICES, default='tls')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.label} ({self.from_email})"

class MarketingCampaign(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'), ('sms', 'SMS'), ('whatsapp', 'WhatsApp'),
        ('social', 'Social Media'), ('ad', 'Paid Ad'),
    ]
    STATUS_CHOICES = [('draft','Draft'),('scheduled','Scheduled'),('sent','Sent'),('paused','Paused')]

    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mkt_campaigns')
    domain       = models.CharField(max_length=253)
    name         = models.CharField(max_length=200)
    channel      = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='email')
    subject      = models.CharField(max_length=300, blank=True)
    sender_email = models.EmailField(blank=True, default='')
    body         = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    custom_smtp  = models.ForeignKey('CustomSMTPConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_count   = models.PositiveIntegerField(default=0)
    open_rate    = models.FloatField(default=0)
    click_rate   = models.FloatField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    # WhatsApp-specific media attachment
    wa_media_path = models.CharField(max_length=500, blank=True, default='',
                                     help_text='Server-side path to attached media file (image/video/doc)')
    wa_media_type = models.CharField(max_length=20, blank=True, default='',
                                     help_text='MIME type, e.g. image/jpeg, video/mp4, application/pdf')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.channel})"


class MarketingLead(models.Model):
    SOURCE_CHOICES = [
        ('manual','Manual'),('form','Website Form'),('import','CSV Import'),
        ('ad','Paid Ad'),('organic','Organic'),
    ]
    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mkt_leads')
    domain   = models.CharField(max_length=253)
    name     = models.CharField(max_length=200)
    email    = models.EmailField(blank=True)
    phone    = models.CharField(max_length=30, blank=True)
    source   = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    score    = models.PositiveSmallIntegerField(default=50, help_text='0-100 lead quality score')
    notes    = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score', '-created_at']

    def score_label(self):
        if self.score >= 70: return 'hot'
        if self.score >= 40: return 'warm'
        return 'cold'


class MarketingABTest(models.Model):
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mkt_ab_tests')
    domain    = models.CharField(max_length=253)
    name      = models.CharField(max_length=200)
    variant_a = models.TextField()
    variant_b = models.TextField()
    metric    = models.CharField(max_length=50, default='clicks')
    winner    = models.CharField(max_length=1, choices=[('A','A'),('B','B')], blank=True)
    clicks_a  = models.PositiveIntegerField(default=0)
    clicks_b  = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MarketingTemplate(models.Model):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mkt_templates')
    domain       = models.CharField(max_length=253)
    name         = models.CharField(max_length=200)
    subject      = models.CharField(max_length=300, blank=True, default='')
    content_html = models.TextField()
    content_json = models.TextField(blank=True, default='')  # JSON of drag-and-drop builder blocks
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class CampaignRecipient(models.Model):
    """Tracks individual recipient delivery + engagement per campaign."""
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'),
        ('opened', 'Opened'), ('clicked', 'Clicked'), ('bounced', 'Bounced'),
    ]
    campaign   = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='recipients')
    email      = models.EmailField()
    name       = models.CharField(max_length=200, blank=True, default='')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at    = models.DateTimeField(null=True, blank=True)
    opened_at  = models.DateTimeField(null=True, blank=True)
    error_msg  = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} — {self.get_status_display()}"


class DockerContainer(models.Model):
    user = models.CharField(max_length=150)             # VoidPanel owner username
    container_id = models.CharField(max_length=64, blank=True, null=True)
    name = models.CharField(max_length=100)             # Container custom name
    image = models.CharField(max_length=255)            # e.g., 'nginx:latest'
    ports = models.JSONField(default=dict, blank=True)  # Mappings: {"host_port": "container_port"}
    env_vars = models.JSONField(default=dict, blank=True)# Env variables: {"ENV_VAR": "value"}
    volumes = models.JSONField(default=dict, blank=True)# Volumes: {"host_path": "container_path"}
    domain = models.CharField(max_length=255, blank=True, default='') # Nginx reverse proxied domain routing
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.image})"


class CloudflareIntegration(models.Model):
    user = models.CharField(max_length=150)             # Owner username
    domain = models.CharField(max_length=255, unique=True)
    api_token = models.CharField(max_length=255)        # Cloudflare API Token
    email = models.CharField(max_length=255, blank=True, default='') # Cloudflare Email (for Global API Key)
    zone_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.domain} (Cloudflare)"


# ═══════════════════════════════════════════════════════════
#  AI CHIP BALANCE — Per-user credits for Agentic AI usage
# ═══════════════════════════════════════════════════════════

from django.contrib.auth.models import User as _AuthUser

class AIChipBalance(models.Model):
    """
    Tracks how many AI chips a panel user has remaining.
    Superadmin is exempt — checked in ai_views.py.
    One row per user (OneToOne).
    """
    user          = models.OneToOneField(
        _AuthUser, on_delete=models.CASCADE, related_name='ai_chip_balance'
    )
    chips         = models.IntegerField(default=20, help_text='Remaining AI chips. 0 = blocked.')
    last_refilled = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'AI Chip Balance'
        verbose_name_plural = 'AI Chip Balances'

    def __str__(self):
        return f"{self.user.username} — {self.chips} chips"

    @classmethod
    def get_for_user(cls, user):
        """Get or create the chip balance row for a user."""
        obj, _ = cls.objects.get_or_create(user=user, defaults={'chips': 20})
        return obj

    def deduct(self, amount=1, description='AI command'):
        """Deduct chips and log. Returns True if successful, False if insufficient."""
        if self.chips < amount:
            return False
        self.chips -= amount
        self.save(update_fields=['chips', 'updated_at'])
        AIChipTransaction.objects.create(
            user=self.user, amount=-amount,
            description=description, balance_after=self.chips,
        )
        return True

    def add(self, amount, description='Admin top-up'):
        """Add chips (admin top-up)."""
        self.chips += amount
        self.save(update_fields=['chips', 'updated_at'])
        AIChipTransaction.objects.create(
            user=self.user, amount=amount,
            description=description, balance_after=self.chips,
        )


class AIChipTransaction(models.Model):
    """Audit log of every AI chip deduction or addition."""
    user          = models.ForeignKey(
        _AuthUser, on_delete=models.CASCADE, related_name='ai_chip_transactions'
    )
    amount        = models.IntegerField(help_text='Negative = deduction, Positive = top-up')
    description   = models.CharField(max_length=255, default='AI command')
    balance_after = models.IntegerField(default=0)
    timestamp     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'AI Chip Transaction'
        verbose_name_plural = 'AI Chip Transactions'
        ordering            = ['-timestamp']

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.user.username} {sign}{self.amount} chips @ {self.timestamp:%Y-%m-%d %H:%M}"


# ═══════════════════════════════════════════════════════════
#  UPDATE SETTINGS — Auto vs Manual update configuration
# ═══════════════════════════════════════════════════════════

class UpdateSettings(models.Model):
    """
    Singleton (pk=1). Controls auto vs manual panel updates.
    Auto mode: cron runs manage.py auto_update at midnight.
    """
    MODE_AUTO    = 'auto'
    MODE_MANUAL  = 'manual'
    MODE_CHOICES = [
        (MODE_AUTO,   'Auto Update (midnight)'),
        (MODE_MANUAL, 'Manual Update'),
    ]
    mode             = models.CharField(
        max_length=10, choices=MODE_CHOICES, default=MODE_AUTO,
    )
    last_auto_update = models.DateTimeField(null=True, blank=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Update Settings'
        verbose_name_plural = 'Update Settings'

    def __str__(self):
        return f"Update mode: {self.get_mode_display()}"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'mode': cls.MODE_AUTO})
        return obj


class NotificationSettings(models.Model):
    """
    Singleton (pk=1). Stores SMTP credentials and toggles for panel notifications
    sent to the administrator email address.
    """
    smtp_host       = models.CharField(max_length=255, blank=True, null=True)
    smtp_port       = models.IntegerField(default=587)
    smtp_user       = models.CharField(max_length=255, blank=True, null=True)
    smtp_password   = models.CharField(max_length=255, blank=True, null=True)
    smtp_encryption = models.CharField(max_length=10, choices=[('tls', 'TLS'), ('ssl', 'SSL'), ('none', 'None')], default='tls')
    from_email      = models.EmailField(blank=True, null=True)

    is_smtp_verified = models.BooleanField(default=False)

    # User lifecycle events
    notify_user_created     = models.BooleanField(default=False)
    notify_user_suspended   = models.BooleanField(default=False)
    notify_user_unsuspended = models.BooleanField(default=False)
    notify_user_terminated  = models.BooleanField(default=False)

    # Security
    notify_login_alert = models.BooleanField(default=False)

    # Infrastructure events
    notify_ssl_generated      = models.BooleanField(default=False)
    notify_backup_created     = models.BooleanField(default=False)
    notify_script_installed   = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Notification Settings'
        verbose_name_plural = 'Notification Settings'

    def __str__(self):
        return f"SMTP Verified: {self.is_smtp_verified}"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WaConversation(models.Model):
    """One record per WhatsApp contact thread — powers the inbox sidebar.
    Scoped per-user: (domain + username + phone) is the unique key so each
    panel user has their own isolated inbox.
    """
    domain       = models.CharField(max_length=253, db_index=True)
    # username: panel login username — isolates the inbox per user
    username     = models.CharField(max_length=150, db_index=True, default='')
    phone        = models.CharField(max_length=30, db_index=True)
    name         = models.CharField(max_length=200, blank=True, default='')
    last_message = models.TextField(blank=True, default='')
    last_ts      = models.DateTimeField(null=True, blank=True)
    unread_count = models.PositiveIntegerField(default=0)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('domain', 'username', 'phone')]  # per-user isolation

    def __str__(self):
        return f"{self.name or self.phone} ({self.domain}/{self.username})"


class WaMessage(models.Model):
    """Every individual WhatsApp message — persisted so chats survive restarts.
    username field ensures messages are isolated per panel user.
    """
    DIRECTION_CHOICES = [('in', 'Incoming'), ('out', 'Outgoing')]

    conversation = models.ForeignKey(WaConversation, on_delete=models.CASCADE,
                                     related_name='messages', null=True, blank=True)
    domain       = models.CharField(max_length=253, db_index=True)
    # username: panel login username — isolates messages per user
    username     = models.CharField(max_length=150, db_index=True, default='')
    phone        = models.CharField(max_length=30, db_index=True)
    name         = models.CharField(max_length=200, blank=True, default='')
    text         = models.TextField()
    direction    = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default='out')
    message_id   = models.CharField(max_length=100, blank=True, default='')
    delivered    = models.BooleanField(default=False)
    read         = models.BooleanField(default=False)
    ts           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ts']
        indexes = [
            models.Index(fields=['domain', 'username', 'phone', 'ts']),
        ]

    def __str__(self):
        return f"[{self.direction}] {self.phone}: {self.text[:40]}"


class MarketingWorkflow(models.Model):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mkt_workflows')
    domain       = models.CharField(max_length=253, db_index=True)
    name         = models.CharField(max_length=200)
    trigger_type = models.CharField(max_length=50, default='contact_created')  # contact_created, score_gte_70, score_between_40_70
    status       = models.CharField(max_length=20, default='draft')  # draft, active
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.domain})"


class MarketingWorkflowStep(models.Model):
    workflow     = models.ForeignKey(MarketingWorkflow, on_delete=models.CASCADE, related_name='steps')
    step_order   = models.PositiveIntegerField()
    action_type  = models.CharField(max_length=20)  # send_email, send_sms, send_whatsapp, delay
    delay_days   = models.PositiveIntegerField(default=0)
    template_id  = models.PositiveIntegerField(null=True, blank=True)
    message_text = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['step_order']


class MarketingWorkflowEnrollment(models.Model):
    workflow           = models.ForeignKey(MarketingWorkflow, on_delete=models.CASCADE, related_name='enrollments')
    lead               = models.ForeignKey('MarketingLead', on_delete=models.CASCADE, related_name='enrollments')
    current_step_index = models.PositiveIntegerField(default=0)
    status             = models.CharField(max_length=20, default='running')  # running, completed, failed
    next_run_at        = models.DateTimeField(null=True, blank=True)
    last_run_at        = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('workflow', 'lead')]


# ═══════════════════════════════════════════════════════════════
#  SUITE PLATFORM — Plans, Subscriptions, SSO Tokens
# ═══════════════════════════════════════════════════════════════

SUITE_CHOICES = [
    ('social',    'Social Media Suite'),
    ('seo',       'SEO Suite'),
    ('marketing', 'Marketing Suite'),
]


class SuitePlan(models.Model):
    """
    A named, tiered plan for one of the three suites.
    Limits are stored as a JSON field for flexibility.
    """
    suite       = models.CharField(max_length=20, choices=SUITE_CHOICES)
    slug        = models.SlugField(max_length=50)          # e.g. 'growth', 'standard'
    name        = models.CharField(max_length=100)         # e.g. 'Growth', 'Standard'
    price_usd   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    limits      = models.JSONField(default=dict, help_text='JSON dict of plan limits')
    is_active   = models.BooleanField(default=True)
    sort_order  = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('suite', 'slug')
        ordering        = ['suite', 'sort_order']
        verbose_name    = 'Suite Plan'

    def __str__(self):
        return f"{self.get_suite_display()} — {self.name}"

    @property
    def limits_json(self):
        """Return limits as a proper JSON string (safe to embed in HTML data attributes)."""
        import json
        return json.dumps(self.limits or {})

    @classmethod
    def seed_defaults(cls):
        """Idempotently create default plans if they don't exist."""
        defaults = [
            # ─── Social Media Suite (INR, 20% below Indian market) ─────────────────
            ('social', 'starter', 'Starter', 699,  {
                'accounts': 5, 'posts_per_month': 100, 'ai_captions': 20,
                'platforms': ['instagram','facebook','twitter'],
                'analytics': 'basic', 'scheduler': True, 'csv_export': False,
                'team_members': 1, 'custom_branding': False,
            }),
            ('social', 'growth',  'Growth',  1999, {
                'accounts': 15, 'posts_per_month': 500, 'ai_captions': 100,
                'platforms': ['instagram','facebook','twitter','linkedin','pinterest','youtube'],
                'analytics': 'advanced', 'scheduler': True, 'csv_export': True,
                'team_members': 3, 'custom_branding': False, 'bulk_scheduling': True,
            }),
            ('social', 'agency',  'Agency',  4999, {
                'accounts': 0, 'posts_per_month': 0, 'ai_captions': 0,
                'platforms': 'all', 'analytics': 'white_label',
                'scheduler': True, 'csv_export': True,
                'team_members': 0, 'custom_branding': True, 'bulk_scheduling': True,
                'client_reporting': True, 'api_access': True,
            }),
            # ─── SEO Suite (INR, 20% below Indian market) ──────────────────────────
            ('seo', 'lite',     'Lite',     999,  {
                'domains': 3, 'keywords': 250, 'audits_per_month': 5,
                'backlink_rows': 500, 'competitor_tracking': 2,
                'rank_tracking': True, 'site_audit': True, 'reports': 'basic',
                'api_access': False,
            }),
            ('seo', 'standard', 'Standard', 2999, {
                'domains': 10, 'keywords': 1000, 'audits_per_month': 30,
                'backlink_rows': 5000, 'competitor_tracking': 10,
                'rank_tracking': True, 'site_audit': True, 'reports': 'full',
                'pdf_reports': True, 'api_access': False,
            }),
            ('seo', 'advanced', 'Advanced', 7999, {
                'domains': 0, 'keywords': 5000, 'audits_per_month': 0,
                'backlink_rows': 0, 'competitor_tracking': 0,
                'rank_tracking': True, 'site_audit': True, 'reports': 'white_label',
                'pdf_reports': True, 'api_access': True, 'custom_alerts': True,
            }),
            # ─── Marketing Suite (INR, 20% below Indian market) ────────────────────
            ('marketing', 'starter', 'Starter', 799,  {
                'contacts': 2000, 'emails_per_month': 15000,
                'campaigns_per_month': 10, 'landing_pages': 5,
                'automation': False, 'ab_testing': False,
                'sms_credits': 500, 'whatsapp': False,
                'team_members': 1, 'custom_domain': False,
            }),
            ('marketing', 'pro',     'Pro',     2499, {
                'contacts': 10000, 'emails_per_month': 100000,
                'campaigns_per_month': 0, 'landing_pages': 30,
                'automation': True, 'ab_testing': True,
                'sms_credits': 2000, 'whatsapp': True,
                'team_members': 5, 'custom_domain': True, 'advanced_segmentation': True,
            }),
            ('marketing', 'agency',  'Agency',  6999, {
                'contacts': 50000, 'emails_per_month': 500000,
                'campaigns_per_month': 0, 'landing_pages': 0,
                'automation': True, 'ab_testing': True,
                'sms_credits': 0, 'whatsapp': True,
                'team_members': 0, 'custom_domain': True,
                'advanced_segmentation': True, 'white_label': True, 'api_access': True,
            }),
        ]
        for suite, slug, name, price, limits in defaults:
            obj, created = cls.objects.get_or_create(
                suite=suite, slug=slug,
                defaults={'name':name, 'price_usd':price, 'limits':limits}
            )
            if not created:
                obj.limits = limits
                obj.save(update_fields=['limits'])


class SuiteSubscription(models.Model):
    """
    A standalone suite account for customers who buy a suite
    package directly (not via hosting). These users log in at
    /suite/login/ with separate credentials.
    """
    suite        = models.CharField(max_length=20, choices=SUITE_CHOICES)
    plan         = models.ForeignKey(SuitePlan, on_delete=models.PROTECT, related_name='subscriptions')
    email        = models.EmailField(unique=True)
    password     = models.CharField(max_length=128, help_text='hashed')
    first_name   = models.CharField(max_length=100, blank=True)
    last_name    = models.CharField(max_length=100, blank=True)
    company      = models.CharField(max_length=150, blank=True)
    is_active    = models.BooleanField(default=True)
    expires_at   = models.DateTimeField(null=True, blank=True, help_text='Null = never expires')
    created_at   = models.DateTimeField(auto_now_add=True)
    last_login   = models.DateTimeField(null=True, blank=True)
    # Optionally linked to a hosting user (for migration / dual-access)
    hosting_domain = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'Suite Subscription'
        ordering     = ['-created_at']

    def __str__(self):
        return f"{self.email} [{self.get_suite_display()} / {self.plan.name}]"

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def set_password(self, raw):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw)

    def check_password(self, raw):
        from django.contrib.auth.hashers import check_password
        return check_password(raw, self.password)


class SuiteSSOToken(models.Model):
    """
    One-time SSO token generated when a hosting-panel user clicks
    'Launch' for a suite their package includes. Token is valid for
    5 minutes and can only be used once.
    """
    token          = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    suite          = models.CharField(max_length=20, choices=SUITE_CHOICES)
    hosting_domain = models.CharField(max_length=255)
    user_email     = models.EmailField()
    plan_slug      = models.CharField(max_length=50, default='starter')
    created_at     = models.DateTimeField(auto_now_add=True)
    expires_at     = models.DateTimeField()
    used           = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Suite SSO Token'
        ordering     = ['-created_at']

    def __str__(self):
        return f"{self.suite} / {self.hosting_domain} / {'used' if self.used else 'valid'}"

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    @classmethod
    def create_for(cls, suite, hosting_domain, user_email, plan_slug='starter'):
        expires = timezone.now() + timezone.timedelta(minutes=5)
        return cls.objects.create(
            suite=suite,
            hosting_domain=hosting_domain,
            user_email=user_email,
            plan_slug=plan_slug,
            expires_at=expires,
        )
