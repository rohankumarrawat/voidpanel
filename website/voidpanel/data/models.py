from django.conf import settings
from django.db import models
from decimal import Decimal

# Create your models here.
class StaticPlanWrapper:
    def __init__(self, data_dict):
        self._data = data_dict
        self.__dict__.update(data_dict)

    @property
    def server(self):
        sid = self.get('server_id')
        if sid:
            try:
                from data.models import VoidPanelServer
                return VoidPanelServer.objects.filter(id=sid).first()
            except Exception:
                pass
        return None

    @property
    def max_accounts(self):
        val = self._data.get('max_accounts')
        if val is not None:
            return val
        val = self._data.get('allowed_domains')
        if val is not None:
            return val
        pid = self._data.get('id')
        if pid == 7: return 10
        if pid == 8: return 50
        if pid == 9: return 200
        return None

    @property
    def allowed_domains(self):
        return self.max_accounts

    @property
    def monthly_price(self):
        val = self._data.get('monthly_price')
        if val is not None:
            return val
        qp = self._data.get('quarterly_price')
        if qp is not None:
            return (Decimal(str(qp)) / 3).quantize(Decimal('0.01'))
        return None

    def get_ssl_type_display(self):
        stype = self._data.get('ssl_type')
        if stype == 'dv':
            return 'Single Domain'
        elif stype == 'wildcard':
            return 'Wildcard SSL'
        elif stype == 'multi':
            return 'Multi-Domain'
        return 'Standard SSL'

    def get_package_type_display(self):
        ptype = self._data.get('package_type')
        if ptype == 'shared':
            return 'Shared Hosting'
        elif ptype == 'wordpress':
            return 'WordPress Hosting'
        elif ptype == 'reseller':
            return 'Reseller Hosting'
        return 'Shared Hosting'

    def __getattr__(self, name):
        if name == 'max_accounts':
            return self.max_accounts
        if name == 'allowed_domains':
            return self.allowed_domains
        if name == 'get_package_type_display':
            return self.get_package_type_display
        return None

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data

    def __str__(self):
        return getattr(self, 'name', '')

_STATIC_HOSTING_PACKAGES = {
    # ── Shared Hosting ── (competitive with Hostinger India / GoDaddy / BigRock)
    1: {
        'id': 1,
        'package_type': 'shared',
        'name': 'Cloud Starter',
        'slug': 'cloud-starter',
        'short_description': 'Launch your first website with high-speed NVMe SSD, free Let\'s Encrypt SSL, and full VoidPanel control.',
        'storage_gb': 10,
        'ram_gb': 1,
        'cpu_cores': 1,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('149.00'),
        'is_featured': False,
        'is_active': True,
        'sort_order': 1,
        'server_id': 1,
        'has_email_marketing': False,
        'has_whatsapp_marketing': False,
        'has_automation': False,
        'has_analytics': False,
        'has_seo_crm': True,
    },
    2: {
        'id': 2,
        'package_type': 'shared',
        'name': 'Cloud Pro',
        'slug': 'cloud-pro',
        'short_description': 'The best value plan for growing businesses — 3x storage, double CPU/RAM, and email marketing tools.',
        'storage_gb': 30,
        'ram_gb': 2,
        'cpu_cores': 2,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('299.00'),
        'is_featured': True,
        'is_active': True,
        'sort_order': 2,
        'server_id': 1,
        'has_email_marketing': True,
        'has_whatsapp_marketing': False,
        'has_automation': True,
        'has_analytics': False,
        'has_seo_crm': True,
    },
    3: {
        'id': 3,
        'package_type': 'shared',
        'name': 'Cloud Business',
        'slug': 'cloud-business',
        'short_description': 'High-performance cloud infrastructure for agencies, e-commerce stores, and high-traffic websites.',
        'storage_gb': 100,
        'ram_gb': 4,
        'cpu_cores': 4,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('599.00'),
        'is_featured': False,
        'is_active': True,
        'sort_order': 3,
        'server_id': 1,
        'has_email_marketing': True,
        'has_whatsapp_marketing': True,
        'has_automation': True,
        'has_analytics': True,
        'has_seo_crm': True,
    },
    # ── WordPress Hosting ── (competitive with BigRock WP / Hostinger WP)
    4: {
        'id': 4,
        'package_type': 'wordpress',
        'name': 'WP Cloud Starter',
        'slug': 'wp-cloud-starter',
        'short_description': 'Pre-configured WordPress cloud instance with one-click installer, OPcache acceleration, and free SSL.',
        'storage_gb': 15,
        'ram_gb': 1,
        'cpu_cores': 1,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('199.00'),
        'is_featured': False,
        'is_active': True,
        'sort_order': 4,
        'server_id': 1,
        'has_email_marketing': False,
        'has_whatsapp_marketing': False,
        'has_automation': False,
        'has_analytics': False,
        'has_seo_crm': True,
    },
    5: {
        'id': 5,
        'package_type': 'wordpress',
        'name': 'WP Cloud Pro',
        'slug': 'wp-cloud-pro',
        'short_description': 'Ultra-fast NVMe storage, WooCommerce-ready, PHP 8.3 with dedicated caching and automated backups.',
        'storage_gb': 50,
        'ram_gb': 2,
        'cpu_cores': 2,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('399.00'),
        'is_featured': True,
        'is_active': True,
        'sort_order': 5,
        'server_id': 1,
        'has_email_marketing': False,
        'has_whatsapp_marketing': False,
        'has_automation': False,
        'has_analytics': False,
        'has_seo_crm': True,
    },
    6: {
        'id': 6,
        'package_type': 'wordpress',
        'name': 'WP Cloud Enterprise',
        'slug': 'wp-cloud-enterprise',
        'short_description': 'Maximum compute power and isolated resources for demanding WooCommerce stores and high-traffic blogs.',
        'storage_gb': 150,
        'ram_gb': 6,
        'cpu_cores': 4,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('799.00'),
        'is_featured': False,
        'is_active': True,
        'sort_order': 6,
        'server_id': 1,
        'has_email_marketing': False,
        'has_whatsapp_marketing': False,
        'has_automation': False,
        'has_analytics': False,
        'has_seo_crm': True,
    },
    # ── Reseller Hosting ── (competitive with BigRock Reseller / GoDaddy Reseller)
    7: {
        'id': 7,
        'package_type': 'reseller',
        'name': 'Reseller Cloud Starter',
        'slug': 'reseller-cloud-starter',
        'short_description': 'Start your web hosting business with 10 client accounts, custom branding, and full WHM-style control.',
        'storage_gb': 50,
        'ram_gb': 4,
        'cpu_cores': 2,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('999.00'),
        'is_featured': False,
        'is_active': True,
        'sort_order': 7,
        'server_id': 1,
        'has_email_marketing': False,
        'has_whatsapp_marketing': False,
        'has_automation': False,
        'has_analytics': False,
        'has_seo_crm': True,
    },
    8: {
        'id': 8,
        'package_type': 'reseller',
        'name': 'Reseller Cloud Pro',
        'slug': 'reseller-cloud-pro',
        'short_description': 'Scale to 50 client accounts with enhanced NVMe resources, automated client billing, and custom nameservers.',
        'storage_gb': 150,
        'ram_gb': 8,
        'cpu_cores': 4,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('1999.00'),
        'is_featured': True,
        'is_active': True,
        'sort_order': 8,
        'server_id': 1,
        'has_email_marketing': False,
        'has_whatsapp_marketing': False,
        'has_automation': False,
        'has_analytics': False,
        'has_seo_crm': True,
    },
    9: {
        'id': 9,
        'package_type': 'reseller',
        'name': 'Reseller Cloud Enterprise',
        'slug': 'reseller-cloud-enterprise',
        'short_description': 'Unlimited client accounts, top-tier compute resources, and 100% white-label VoidPanel platform branding.',
        'storage_gb': 500,
        'ram_gb': 16,
        'cpu_cores': 8,
        'bandwidth_label': 'Unmetered',
        'monthly_price': Decimal('3999.00'),
        'is_featured': False,
        'is_active': True,
        'sort_order': 9,
        'server_id': 1,
        'has_email_marketing': False,
        'has_whatsapp_marketing': False,
        'has_automation': False,
        'has_analytics': False,
        'has_seo_crm': True,
    },
}


def get_static_hosting_package(pkg_id):
    """Return a StaticPlanWrapper for the given package id or slug.
    DB overrides (HostingPackageOverride) are merged on top of the static
    defaults so super-admin edits persist without code changes.
    """
    try:
        pid = int(pkg_id)
        base = _STATIC_HOSTING_PACKAGES.get(pid)
    except (ValueError, TypeError):
        base = None
        for p in _STATIC_HOSTING_PACKAGES.values():
            if p['slug'] == pkg_id or p['name'] == pkg_id:
                base = p
                pid = p['id']
                break

    if base is None:
        ov = None
        try:
            pid = int(pkg_id)
            ov = HostingPackageOverride.objects.filter(package_id=pid).first()
        except (ValueError, TypeError):
            ov = HostingPackageOverride.objects.filter(slug=pkg_id).first()
            if not ov:
                ov = HostingPackageOverride.objects.filter(name=pkg_id).first()
        
        if ov:
            data = {
                'id': ov.package_id,
                'package_type': ov.package_type or 'shared',
                'name': ov.name or f"Package #{ov.package_id}",
                'slug': ov.slug or f"package-{ov.package_id}",
                'short_description': ov.short_description or '',
                'storage_gb': ov.storage_gb or 10,
                'ram_gb': ov.ram_gb or 1,
                'cpu_cores': ov.cpu_cores or 1,
                'bandwidth_label': ov.bandwidth_label or '100GB',
                'monthly_price': ov.monthly_price or Decimal('19.00'),
                'is_featured': ov.is_featured,
                'is_active': ov.is_active,
                'sort_order': ov.sort_order or ov.package_id,
                'server_id': ov.server_id or 1,
                'allowed_domains': ov.allowed_domains or 1,
                'has_email_marketing': ov.has_email_marketing,
                'has_whatsapp_marketing': ov.has_whatsapp_marketing,
                'has_automation': ov.has_automation,
                'has_analytics': ov.has_analytics,
                'has_seo_crm': ov.has_seo_crm,
            }
            return StaticPlanWrapper(data)
        return None

    data = dict(base)  # copy so we don't mutate the global dict

    # Merge any admin overrides saved in the database
    try:
        ov = HostingPackageOverride.objects.filter(package_id=pid).first()
        if ov:
            if ov.name:              data['name']              = ov.name
            if ov.slug:              data['slug']              = ov.slug
            if ov.short_description: data['short_description'] = ov.short_description
            if ov.monthly_price is not None: data['monthly_price'] = ov.monthly_price
            if ov.storage_gb is not None:    data['storage_gb']    = ov.storage_gb
            if ov.ram_gb is not None:        data['ram_gb']        = ov.ram_gb
            if ov.cpu_cores is not None:     data['cpu_cores']     = ov.cpu_cores
            if ov.bandwidth_label:           data['bandwidth_label'] = ov.bandwidth_label
            if ov.allowed_domains is not None: data['allowed_domains'] = ov.allowed_domains
            if ov.sort_order is not None:    data['sort_order']    = ov.sort_order
            data['server_id'] = ov.server_id
            data['is_featured'] = ov.is_featured
            data['is_active']   = ov.is_active
            data['has_email_marketing'] = ov.has_email_marketing
            data['has_whatsapp_marketing'] = ov.has_whatsapp_marketing
            data['has_automation'] = ov.has_automation
            data['has_analytics'] = ov.has_analytics
            data['has_seo_crm'] = ov.has_seo_crm
    except Exception:
        pass  # DB not yet migrated — fall back to static defaults

    return StaticPlanWrapper(data)


def get_static_email_plan(plan_id):
    plans = {
        1: {
            'id': 1,
            'name': 'Email Cloud Starter',
            'slug': 'email-cloud-starter',
            'max_mailboxes': 5,
            'storage_per_mailbox_gb': 5,
            'monthly_price': Decimal('99.00'),
            'is_featured': False,
            'is_active': True,
            'short_description': 'Ideal for freelancers and small teams needing professional domain email.',
            'sort_order': 1,
        },
        2: {
            'id': 2,
            'name': 'Email Cloud Pro',
            'slug': 'email-cloud-pro',
            'max_mailboxes': 20,
            'storage_per_mailbox_gb': 10,
            'monthly_price': Decimal('299.00'),
            'is_featured': True,
            'is_active': True,
            'short_description': 'Perfect for growing companies needing high quotas and spam protection.',
            'sort_order': 2,
        },
        3: {
            'id': 3,
            'name': 'Email Cloud Enterprise',
            'slug': 'email-cloud-enterprise',
            'max_mailboxes': 100,
            'storage_per_mailbox_gb': 25,
            'monthly_price': Decimal('999.00'),
            'is_featured': False,
            'is_active': True,
            'short_description': 'Dedicated scalability, advanced routing, and enterprise storage pools.',
            'sort_order': 3,
        }
    }
    try:
        pid = int(plan_id)
        val = plans.get(pid)
    except (ValueError, TypeError):
        val = None
        for p in plans.values():
            if p['slug'] == plan_id or p['name'] == plan_id:
                val = p
                break
    if val is None:
        try:
            from django.apps import apps
            EmailPlan = apps.get_model('data', 'EmailPlan')
            clean_id = str(plan_id)
            if clean_id.startswith('custom_'):
                clean_id = clean_id.replace('custom_', '')
            elif clean_id.startswith('custom-'):
                clean_id = clean_id.replace('custom-', '')

            db_plan = None
            try:
                db_plan = EmailPlan.objects.get(pk=int(clean_id))
            except (ValueError, TypeError, EmailPlan.DoesNotExist):
                try:
                    db_plan = EmailPlan.objects.get(slug=plan_id)
                except EmailPlan.DoesNotExist:
                    try:
                        db_plan = EmailPlan.objects.get(name=plan_id)
                    except EmailPlan.DoesNotExist:
                        pass

            if db_plan:
                data = {
                    'id': f"custom_{db_plan.pk}",
                    'name': db_plan.name,
                    'slug': db_plan.slug,
                    'max_mailboxes': db_plan.max_mailboxes,
                    'storage_per_mailbox_gb': db_plan.storage_per_mailbox_gb,
                    'monthly_price': db_plan.monthly_price,
                    'is_featured': db_plan.is_featured,
                    'is_active': db_plan.is_active,
                    'short_description': db_plan.short_description,
                    'sort_order': db_plan.sort_order,
                }
                return StaticPlanWrapper(data)
        except Exception:
            pass
        return None
    data = dict(val)
    # Merge DB overrides
    try:
        ov = EmailPlanOverride.objects.filter(plan_id=data['id']).first()
        if ov:
            if ov.name:                          data['name']                    = ov.name
            if ov.slug:                          data['slug']                    = ov.slug
            if ov.short_description:             data['short_description']       = ov.short_description
            if ov.monthly_price is not None:     data['monthly_price']           = ov.monthly_price
            if ov.max_mailboxes is not None:     data['max_mailboxes']           = ov.max_mailboxes
            if ov.storage_per_mailbox_gb is not None: data['storage_per_mailbox_gb'] = ov.storage_per_mailbox_gb
            if ov.sort_order is not None:        data['sort_order']              = ov.sort_order
            data['is_featured'] = ov.is_featured
            data['is_active']   = ov.is_active
    except Exception:
        pass
    return StaticPlanWrapper(data)


def get_static_ssl_plan(plan_id):
    """Let's Encrypt SSL plans — 90-day (3 month) validity only.
    quarterly_price is the single price charged per renewal cycle.
    """
    plans = {
        1: {
            'id': 1,
            'name': 'Standard DV SSL',
            'slug': 'standard-dv-ssl',
            'ssl_type': 'dv',
            'validity_days': 90,
            'max_domains': 1,
            'quarterly_price': Decimal('149.00'),
            'auto_renew': True,
            'is_featured': False,
            'is_active': True,
            'sort_order': 1,
            'short_description': 'Single domain HTTPS via Let\'s Encrypt — renewed every 3 months.',
        },
        2: {
            'id': 2,
            'name': 'Wildcard SSL',
            'slug': 'wildcard-ssl',
            'ssl_type': 'wildcard',
            'validity_days': 90,
            'max_domains': 1,
            'quarterly_price': Decimal('399.00'),
            'auto_renew': True,
            'is_featured': True,
            'is_active': True,
            'sort_order': 2,
            'short_description': 'Wildcard *.yourdomain.com via Let\'s Encrypt — renewed every 3 months.',
        },
        3: {
            'id': 3,
            'name': 'Multi-Domain SSL',
            'slug': 'multi-domain-ssl',
            'ssl_type': 'multi',
            'validity_days': 90,
            'max_domains': 5,
            'quarterly_price': Decimal('599.00'),
            'auto_renew': True,
            'is_featured': False,
            'is_active': True,
            'sort_order': 3,
            'short_description': 'Up to 5 SANs via Let\'s Encrypt — renewed every 3 months.',
        }
    }
    try:
        pid = int(plan_id)
        val = plans.get(pid)
    except (ValueError, TypeError):
        val = None
        for p in plans.values():
            if p['slug'] == plan_id or p['name'] == plan_id:
                val = p
                break
    if val is None:
        try:
            from django.apps import apps
            SSLPlan = apps.get_model('data', 'SSLPlan')
            clean_id = str(plan_id)
            if clean_id.startswith('custom_'):
                clean_id = clean_id.replace('custom_', '')
            elif clean_id.startswith('custom-'):
                clean_id = clean_id.replace('custom-', '')

            db_plan = None
            try:
                db_plan = SSLPlan.objects.get(pk=int(clean_id))
            except (ValueError, TypeError, SSLPlan.DoesNotExist):
                try:
                    db_plan = SSLPlan.objects.get(slug=plan_id)
                except SSLPlan.DoesNotExist:
                    try:
                        db_plan = SSLPlan.objects.get(name=plan_id)
                    except SSLPlan.DoesNotExist:
                        pass

            if db_plan:
                data = {
                    'id': f"custom_{db_plan.pk}",
                    'name': db_plan.name,
                    'slug': db_plan.slug,
                    'ssl_type': db_plan.ssl_type,
                    'validity_days': db_plan.validity_days,
                    'max_domains': db_plan.max_domains,
                    'quarterly_price': db_plan.quarterly_price,
                    'auto_renew': db_plan.auto_renew,
                    'is_featured': db_plan.is_featured,
                    'is_active': db_plan.is_active,
                    'sort_order': db_plan.sort_order,
                    'short_description': db_plan.short_description,
                }
                return StaticPlanWrapper(data)
        except Exception:
            pass
        return None
    data = dict(val)
    # Merge DB overrides
    try:
        ov = SSLPlanOverride.objects.filter(plan_id=data['id']).first()
        if ov:
            if ov.name:                         data['name']              = ov.name
            if ov.slug:                         data['slug']              = ov.slug
            if ov.short_description:            data['short_description'] = ov.short_description
            if ov.quarterly_price is not None:  data['quarterly_price']   = ov.quarterly_price
            if ov.max_domains is not None:      data['max_domains']       = ov.max_domains
            if ov.ssl_type:                     data['ssl_type']          = ov.ssl_type
            if ov.sort_order is not None:       data['sort_order']        = ov.sort_order
            data['is_featured'] = ov.is_featured
            data['is_active']   = ov.is_active
            data['auto_renew']  = ov.auto_renew
    except Exception:
        pass
    return StaticPlanWrapper(data)



def get_static_social_plan(plan_id):
    plans = {
        1: {
            'id': 1,
            'name': 'Starter Social',
            'slug': 'starter-social',
            'monthly_price': Decimal('199.00'),
            'yearly_price': Decimal('1990.00'),
            'effective_yearly_price': Decimal('1990.00'),
            'max_accounts': 3,
            'max_scheduled_posts_per_month': 30,
            'max_ai_captions_per_month': 5,
            'max_team_members': 1,
            'media_storage_gb': 1,
            'allowed_platforms': ["fb","ig","tw"],
            'has_analytics': True,
            'has_advanced_analytics': False,
            'has_unified_inbox': False,
            'has_ai_captions': True,
            'has_csv_export': False,
            'has_calendar_view': True,
            'has_bulk_schedule': False,
            'has_link_shortener': False,
            'short_description': 'Manage up to 3 core accounts with calendar scheduling.',
        },
        2: {
            'id': 2,
            'name': 'Business Social',
            'slug': 'business-social',
            'monthly_price': Decimal('499.00'),
            'yearly_price': Decimal('4990.00'),
            'effective_yearly_price': Decimal('4990.00'),
            'max_accounts': 10,
            'max_scheduled_posts_per_month': 150,
            'max_ai_captions_per_month': 50,
            'max_team_members': 3,
            'media_storage_gb': 5,
            'allowed_platforms': [],
            'has_analytics': True,
            'has_advanced_analytics': True,
            'has_unified_inbox': True,
            'has_ai_captions': True,
            'has_csv_export': True,
            'has_calendar_view': True,
            'has_bulk_schedule': True,
            'has_link_shortener': True,
            'short_description': 'Ideal for active business lists and multiple platforms.',
        },
        3: {
            'id': 3,
            'name': 'Enterprise Social',
            'slug': 'enterprise-social',
            'monthly_price': Decimal('999.00'),
            'yearly_price': Decimal('9990.00'),
            'effective_yearly_price': Decimal('9990.00'),
            'max_accounts': 30,
            'max_scheduled_posts_per_month': 1000,
            'max_ai_captions_per_month': 500,
            'max_team_members': 10,
            'media_storage_gb': 20,
            'allowed_platforms': [],
            'has_analytics': True,
            'has_advanced_analytics': True,
            'has_unified_inbox': True,
            'has_ai_captions': True,
            'has_csv_export': True,
            'has_calendar_view': True,
            'has_bulk_schedule': True,
            'has_link_shortener': True,
            'short_description': 'High capacity for agency and large enterprise needs.',
        }
    }
    try:
        pid = int(plan_id)
        val = plans.get(pid)
    except (ValueError, TypeError):
        val = None
        for p in plans.values():
            if p['slug'] == plan_id or p['name'] == plan_id:
                val = p
                break
    if val:
        return StaticPlanWrapper(val)
    return None

def get_static_marketing_plan(plan_id):
    plans = {
        1: {
            'id': 1,
            'name': 'Starter Marketing',
            'slug': 'starter-marketing',
            'monthly_price': Decimal('299.00'),
            'effective_yearly_price': Decimal('2990.00'),
            'max_leads': 500,
            'max_emails_per_month': 5000,
            'max_ai_copies_per_month': 10,
            'has_ab_testing': False,
            'has_whatsapp_automation': False,
            'short_description': 'Perfect for small lists and beginning marketers.',
        },
        2: {
            'id': 2,
            'name': 'Business Marketing',
            'slug': 'business-marketing',
            'monthly_price': Decimal('599.00'),
            'effective_yearly_price': Decimal('5990.00'),
            'max_leads': 5000,
            'max_emails_per_month': 50000,
            'max_ai_copies_per_month': 100,
            'has_ab_testing': True,
            'has_whatsapp_automation': True,
            'short_description': 'Ideal for active business lists and campaigns.',
        },
        3: {
            'id': 3,
            'name': 'Enterprise Marketing',
            'slug': 'enterprise-marketing',
            'monthly_price': Decimal('1199.00'),
            'effective_yearly_price': Decimal('11990.00'),
            'max_leads': 50000,
            'max_emails_per_month': 500000,
            'max_ai_copies_per_month': 1000,
            'has_ab_testing': True,
            'has_whatsapp_automation': True,
            'short_description': 'Scalable capacity for large enterprises.',
        }
    }
    try:
        pid = int(plan_id)
        val = plans.get(pid)
    except (ValueError, TypeError):
        val = None
        for p in plans.values():
            if p['slug'] == plan_id or p['name'] == plan_id:
                val = p
                break
    if val:
        return StaticPlanWrapper(val)
    return None

class updates(models.Model):
    """Each row is a VoidPanel release. The migration path API returns all versions
    between a server's current version and the latest, in sorted order."""
    version     = models.CharField(max_length=20, default=None, unique=True,
                                   help_text="Semantic version, e.g. 2.1.0")
    date        = models.DateField(auto_now_add=True)
    # ── Release metadata ──────────────────────────────────────────────────────
    notes       = models.TextField(blank=True, help_text="What changed in this release")
    script_url  = models.URLField(blank=True,
                                  help_text="URL to the updatepanel.sh for THIS version (e.g. https://voidpanel.com/updates/2.1.0/update.sh)")
    min_version = models.CharField(max_length=20, blank=True,
                                   help_text="Minimum version required before this update can be applied (leave blank = any)")
    is_breaking = models.BooleanField(default=False,
                                      help_text="If True, servers must not skip this version")
    is_active   = models.BooleanField(default=True,
                                      help_text="Inactive versions are excluded from the migration path")

    class Meta:
        ordering = ['version']

    def __str__(self):
        return f"VoidPanel {self.version}"



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
    balance_funds = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_chips = models.IntegerField(default=0)
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

    # ── Panel credentials (filled after provisioning) ─────────────────────────
    panel_username = models.CharField(max_length=150, blank=True, help_text='System username on the VoidPanel server')
    panel_password = models.CharField(max_length=255, blank=True, help_text='Plain-text password shown once after provisioning')

    # ── SSO auto-login token (single-use, 5-minute TTL) ───────────────────────
    sso_token      = models.CharField(max_length=64, blank=True)
    sso_token_expires = models.DateTimeField(null=True, blank=True)

    # ── Reseller flag ─────────────────────────────────────────────────────────
    is_reseller    = models.BooleanField(default=False, help_text='True when this is a Reseller Hosting service')

    def __str__(self):
        return f"{self.service_name} ({self.user.username})"

    def save(self, *args, **kwargs):
        is_suspending = False
        if self.pk:
            old = HostingService.objects.filter(pk=self.pk).values('status').first()
            if old and old['status'] != 'suspended' and self.status == 'suspended':
                is_suspending = True
        
        super().save(*args, **kwargs)
        
        if is_suspending:
            try:
                from voidpanel.views import send_whatsapp_notification_async
                msg = f"Hosting Service Suspended: {self.service_name} ({self.domain})\nReason: Billing renewal overdue or manual administrator action.\nContact support to reactivate."
                send_whatsapp_notification_async(self.user, msg, 'service_suspend')
            except Exception as e:
                import logging
                logging.error(f"Error sending WhatsApp hosting suspension alert: {e}")

    def generate_sso_token(self):
        """Generate a fresh single-use SSO token valid for 5 minutes."""
        import secrets
        from django.utils import timezone
        from datetime import timedelta
        self.sso_token = secrets.token_hex(32)
        self.sso_token_expires = timezone.now() + timedelta(minutes=5)
        self.save(update_fields=['sso_token', 'sso_token_expires'])
        return self.sso_token

    def validate_sso_token(self, token):
        """Returns True if token matches and has not expired. Invalidates on success."""
        from django.utils import timezone
        if not self.sso_token or self.sso_token != token:
            return False
        if self.sso_token_expires and timezone.now() > self.sso_token_expires:
            return False
        # Invalidate immediately (single-use)
        self.sso_token = ''
        self.sso_token_expires = None
        self.save(update_fields=['sso_token', 'sso_token_expires'])
        return True

    @property
    def is_hosting_service(self):
        """True for services that have a VoidPanel control panel."""
        return self.product_type in ('Shared Hosting', 'WordPress Hosting', 'Reseller Hosting')

    @property
    def panel_base_url(self):
        """Return the base panel URL (from server URL or panel_url field)."""
        if self.server:
            if self.server.login_url:
                return self.server.login_url.rstrip('/')
            if self.server.url:
                return self.server.url.rstrip('/')
        if self.panel_url:
            return self.panel_url.rstrip('/')
        return ''


class WordPressInstallation(models.Model):
    """
    Tracks the state of a WordPress installation for a HostingService.
    Created when WP is provisioned; updated on install/uninstall.
    """
    STATUS_CHOICES = [
        ('installing', 'Installing'),
        ('active',     'Active'),
        ('uninstalled','Uninstalled'),
        ('failed',     'Failed'),
    ]
    SSL_CHOICES = [
        ('none',    'No SSL'),
        ('pending', 'Pending'),
        ('active',  'Active'),
        ('expired', 'Expired'),
    ]

    service        = models.OneToOneField(
        HostingService,
        on_delete=models.CASCADE,
        related_name='wp_installation',
    )
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='installing')
    wp_admin_user  = models.CharField(max_length=60,  blank=True)
    wp_admin_email = models.CharField(max_length=120, blank=True)
    wp_admin_url   = models.URLField(blank=True)
    wp_version     = models.CharField(max_length=20,  blank=True)
    db_name        = models.CharField(max_length=80,  blank=True)
    ssl_status     = models.CharField(max_length=10,  choices=SSL_CHOICES, default='none')
    installed_at   = models.DateTimeField(null=True, blank=True)
    uninstalled_at = models.DateTimeField(null=True, blank=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'WP @ {self.service.domain} [{self.status}]'


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

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            try:
                from voidpanel.views import send_whatsapp_notification_async
                msg = f"New Invoice Generated: {self.invoice_number}\nDescription: {self.description}\nAmount: ₹{self.total}\nDue Date: {self.due_date}"
                send_whatsapp_notification_async(self.user, msg, 'invoice_created')
            except Exception as e:
                import logging
                logging.error(f"Error sending WhatsApp invoice alert: {e}")


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

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new and not self.last_reply_at:
            from django.utils import timezone
            self.last_reply_at = timezone.now()
        super().save(*args, **kwargs)
        if is_new:
            try:
                from voidpanel.views import send_whatsapp_notification_async
                msg = f"New Support Ticket Opened: #{self.ticket_number}\nSubject: {self.subject}\nPriority: {self.priority.upper()}\nClient: {self.user.username} ({self.user.email})"
                send_whatsapp_notification_async(None, msg, 'ticket_opened')
            except Exception as e:
                import logging
                logging.error(f"Error sending WhatsApp ticket alert: {e}")


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
    send_on_live_chat = models.BooleanField(default=True)
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
    login_url = models.CharField(max_length=300, blank=True, default='', help_text="Global login URL for this server (e.g. https://panel.yourdomain.com:8443)")
    nameservers = models.TextField(blank=True, default='ns1.voidpanel.com\nns2.voidpanel.com', help_text="Nameservers for this server, one per line")
    server_version = models.CharField(max_length=40, blank=True, help_text="VoidPanel version reported by this node")
    last_ping_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_connected = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name





class HostingPricingSettings(models.Model):
    title = models.CharField(max_length=120, default='Primary Pricing Rules')
    # --- Shared Hosting Builder Pricing ---
    storage_price_per_10gb = models.DecimalField(max_digits=8, decimal_places=2, default=1.50)
    bandwidth_price_per_100gb = models.DecimalField(max_digits=8, decimal_places=2, default=5.00)
    # Shared hosting limits (defaults applied to new plans)
    shared_max_emails = models.PositiveIntegerField(default=10)
    shared_max_ftp = models.PositiveIntegerField(default=5)
    shared_max_databases = models.PositiveIntegerField(default=5)
    # Storage slider range for the builder
    storage_min_gb = models.PositiveIntegerField(default=10)
    storage_max_gb = models.PositiveIntegerField(default=500)
    # Bandwidth slider range
    bandwidth_min_gb = models.PositiveIntegerField(default=10)
    bandwidth_max_gb = models.PositiveIntegerField(default=1000)
    # --- Legacy VPS / Advanced fields (kept for backward compat) ---
    ram_price_per_1gb = models.DecimalField(max_digits=8, decimal_places=2, default=4.00)
    cpu_price_per_core = models.DecimalField(max_digits=8, decimal_places=2, default=8.00)
    bandwidth_100gb_price = models.DecimalField(max_digits=8, decimal_places=2, default=5.00)
    bandwidth_500gb_price = models.DecimalField(max_digits=8, decimal_places=2, default=12.00)
    bandwidth_1000gb_price = models.DecimalField(max_digits=8, decimal_places=2, default=20.00)
    bandwidth_unmetered_price = models.DecimalField(max_digits=8, decimal_places=2, default=35.00)
    ram_min_gb = models.PositiveIntegerField(default=1)
    ram_max_gb = models.PositiveIntegerField(default=32)
    cpu_min_cores = models.PositiveIntegerField(default=1)
    cpu_max_cores = models.PositiveIntegerField(default=16)
    quarterly_discount_percent = models.PositiveIntegerField(default=0)
    annual_discount_percent = models.PositiveIntegerField(default=10)
    signup_bonus_chips = models.IntegerField(default=5000)
    credits_per_rupee = models.IntegerField(default=100)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Hosting pricing settings'

    def __str__(self):
        return self.title


class HostingPackageOverride(models.Model):
    package_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    slug = models.CharField(max_length=150, blank=True, null=True)
    package_type = models.CharField(max_length=50, blank=True, null=True)
    short_description = models.TextField(blank=True, null=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    storage_gb = models.IntegerField(null=True, blank=True)
    ram_gb = models.IntegerField(null=True, blank=True)
    cpu_cores = models.IntegerField(null=True, blank=True)
    bandwidth_label = models.CharField(max_length=100, blank=True, null=True)
    allowed_domains = models.IntegerField(null=True, blank=True)
    sort_order = models.IntegerField(null=True, blank=True)
    server_id = models.IntegerField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    has_email_marketing = models.BooleanField(default=False)
    has_whatsapp_marketing = models.BooleanField(default=False)
    has_automation = models.BooleanField(default=False)
    has_analytics = models.BooleanField(default=False)
    has_seo_crm = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Hosting package overrides'

    def __str__(self):
        return f"Override for Package #{self.package_id} ({self.name or 'Unnamed'})"


class EmailPlanOverride(models.Model):
    """DB-backed overrides for the 3 static Professional Email plans (IDs 1–3).
    Any non-null field here overrides the static default returned by get_static_email_plan().
    """
    plan_id = models.IntegerField(unique=True)  # 1, 2, or 3
    name = models.CharField(max_length=150, blank=True, null=True)
    slug = models.CharField(max_length=150, blank=True, null=True)
    short_description = models.TextField(blank=True, null=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_mailboxes = models.IntegerField(null=True, blank=True)
    storage_per_mailbox_gb = models.IntegerField(null=True, blank=True)
    sort_order = models.IntegerField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Email plan overrides'

    def __str__(self):
        return f"Email Plan Override #{self.plan_id} ({self.name or 'unnamed'})"


class SSLPlanOverride(models.Model):
    """DB-backed overrides for the 3 static Let's Encrypt SSL plans (IDs 1–3).
    Plans are sold as 3-month (90-day) cycles only — quarterly_price is the single billing field.
    """
    plan_id = models.IntegerField(unique=True)  # 1, 2, or 3
    name = models.CharField(max_length=150, blank=True, null=True)
    slug = models.CharField(max_length=150, blank=True, null=True)
    short_description = models.TextField(blank=True, null=True)
    ssl_type = models.CharField(max_length=20, blank=True, null=True)  # dv / wildcard / multi
    quarterly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_domains = models.IntegerField(null=True, blank=True)
    sort_order = models.IntegerField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'SSL plan overrides'

    def __str__(self):
        return f"SSL Plan Override #{self.plan_id} ({self.name or 'unnamed'})"






class EmailPlan(models.Model):
    """Admin-created Professional Email plans (in addition to the 3 static ones)."""
    name                  = models.CharField(max_length=150)
    slug                  = models.CharField(max_length=150, unique=True)
    short_description     = models.TextField(blank=True, default='')
    monthly_price         = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_mailboxes         = models.IntegerField(default=5)
    storage_per_mailbox_gb = models.IntegerField(default=5)
    sort_order            = models.IntegerField(default=0)
    is_featured           = models.BooleanField(default=False)
    is_active             = models.BooleanField(default=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'monthly_price']
        verbose_name_plural = 'Email plans'

    def __str__(self):
        return f"{self.name} (₹{self.monthly_price}/mo)"

    @property
    def id_str(self):
        return f"custom_{self.pk}"


class SSLPlan(models.Model):
    """Admin-created SSL Certificate plans (in addition to the 3 static ones).
    Always Let's Encrypt — 90-day validity, sold as 3-month (quarterly) cycles.
    """
    SSL_TYPE_CHOICES = [
        ('dv',       'Domain Validated (DV)'),
        ('wildcard', 'Wildcard (*.domain.com)'),
        ('multi',    'Multi-Domain (SANs)'),
    ]
    name              = models.CharField(max_length=150)
    slug              = models.CharField(max_length=150, unique=True)
    short_description = models.TextField(blank=True, default='')
    ssl_type          = models.CharField(max_length=20, choices=SSL_TYPE_CHOICES, default='dv')
    quarterly_price   = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_domains       = models.IntegerField(default=1)
    validity_days     = models.IntegerField(default=90)
    sort_order        = models.IntegerField(default=0)
    is_featured       = models.BooleanField(default=False)
    is_active         = models.BooleanField(default=True)
    auto_renew        = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'quarterly_price']
        verbose_name_plural = 'SSL plans'

    def __str__(self):
        return f"{self.name} (₹{self.quarterly_price}/3mo)"

    @property
    def id_str(self):
        return f"custom_{self.pk}"


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
    package_name = models.CharField(max_length=150, blank=True, default='')

    @property
    def package(self):
        return get_static_hosting_package(self.package_name)
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
        return f"Order #{self.pk} — {self.user.username} — {self.package.name if self.package else self.package_name}"


class PanelLicenseRecord(models.Model):
    """
    Issued license key for an installed VoidPanel instance.
    Created via the /api/license/register/ endpoint when an admin activates a fresh panel.
    Managed by super admins via /super-admin/licenses/.
    """
    STATUS_ACTIVE    = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_REVOKED   = 'revoked'
    STATUS_CHOICES = [
        (STATUS_ACTIVE,    'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_REVOKED,   'Revoked'),
    ]

    TIER_STARTER   = 'starter'
    TIER_PRO       = 'pro'
    TIER_ADVANCED  = 'advanced'
    TIER_UNLIMITED = 'unlimited'
    TIER_CHOICES = [
        (TIER_STARTER,   'Starter — Free'),
        (TIER_PRO,       'Pro — ₹999/mo'),
        (TIER_ADVANCED,  'Advanced — ₹2,499/mo'),
        (TIER_UNLIMITED, 'Unlimited — ₹4,999/mo'),
    ]

    TIER_FEATURES = {
        TIER_STARTER: {
            'hosting_mgmt':        True,
            'email_plans':         True,
            'ssl_plans':           True,
            'billing':             True,
            'live_chat':           True,
            'marketing_suite':     False,
            'seo_tools':           False,
            'social_media':        False,
            'whatsapp_automation': False,
            'docker_manager':      False,
            'script_installer':    False,
            'ai_assistant':        False,
            'digital_suite':       False,
            'reseller_hosting':    False,
            'white_label':         False,
            'priority_support':    False,
        },
        TIER_PRO: {
            'hosting_mgmt':        True,
            'email_plans':         True,
            'ssl_plans':           True,
            'billing':             True,
            'live_chat':           True,
            'marketing_suite':     True,
            'seo_tools':           True,
            'social_media':        True,
            'whatsapp_automation': True,
            'docker_manager':      False,
            'script_installer':    False,
            'ai_assistant':        False,
            'digital_suite':       False,
            'reseller_hosting':    False,
            'white_label':         False,
            'priority_support':    False,
        },
        TIER_ADVANCED: {
            'hosting_mgmt':        True,
            'email_plans':         True,
            'ssl_plans':           True,
            'billing':             True,
            'live_chat':           True,
            'marketing_suite':     True,
            'seo_tools':           True,
            'social_media':        True,
            'whatsapp_automation': True,
            'docker_manager':      True,
            'script_installer':    True,
            'ai_assistant':        True,
            'digital_suite':       True,
            'reseller_hosting':    True,
            'white_label':         False,
            'priority_support':    False,
        },
        TIER_UNLIMITED: {
            'hosting_mgmt':        True,
            'email_plans':         True,
            'ssl_plans':           True,
            'billing':             True,
            'live_chat':           True,
            'marketing_suite':     True,
            'seo_tools':           True,
            'social_media':        True,
            'whatsapp_automation': True,
            'docker_manager':      True,
            'script_installer':    True,
            'ai_assistant':        True,
            'digital_suite':       True,
            'reseller_hosting':    True,
            'white_label':         True,
            'priority_support':    True,
        },
    }

    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='panel_licenses',
        help_text="voidpanel.com account that owns this license",
    )
    key           = models.CharField(max_length=128, unique=True)
    hostname      = models.CharField(max_length=255, blank=True, help_text="Server hostname at activation time")
    server_ip     = models.GenericIPAddressField(null=True, blank=True)
    last_seen_ip  = models.GenericIPAddressField(null=True, blank=True, help_text="Last IP that pinged validate (audit only)")
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    tier          = models.CharField(max_length=20, choices=TIER_CHOICES, default=TIER_PRO,
                                     help_text="License tier determines which features are available")
    is_trial      = models.BooleanField(default=False, help_text="If True, this is a 30-day free trial")
    expires_at    = models.DateTimeField(null=True, blank=True,
                                         help_text="License expiry. Null = lifetime/manual renewal")
    issued_at     = models.DateTimeField(auto_now_add=True)
    last_ping     = models.DateTimeField(null=True, blank=True, help_text="Last time the panel pinged for validation")
    notes         = models.TextField(blank=True)

    class Meta:
        ordering = ['-issued_at']
        verbose_name = "Panel License"
        verbose_name_plural = "Panel Licenses"

    def __str__(self):
        return f"{self.key[:20]}… [{self.tier.upper()}|{self.status}] — {self.user.email}"

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def effective_tier(self):
        """Returns the actual tier — downgrades to starter if trial expired."""
        if self.is_trial and self.is_expired:
            return self.TIER_STARTER
        return self.tier

    @property
    def features(self):
        """Returns feature dict for the effective tier."""
        return self.TIER_FEATURES.get(self.effective_tier, self.TIER_FEATURES[self.TIER_STARTER])

    @property
    def days_remaining(self):
        if not self.expires_at:
            return None
        from django.utils import timezone
        import math
        delta = (self.expires_at - timezone.now()).total_seconds()
        return max(0, math.ceil(delta / 86400))



class RemoteInstallationJob(models.Model):
    """
    Logs background SSH remote installations.
    """
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    license = models.ForeignKey(PanelLicenseRecord, on_delete=models.CASCADE, related_name='install_jobs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    progress = models.IntegerField(default=0)
    logs = models.TextField(blank=True)
    admin_username = models.CharField(max_length=100, blank=True, help_text="Generated on complete")
    admin_password = models.CharField(max_length=100, blank=True, help_text="Generated on complete")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Install #{self.id} for {self.ip_address} ({self.status})"


class TryVoidPanelConfig(models.Model):
    """Singleton model — stores the demo VoidPanel server credentials for the
    'Try VoidPanel' public landing page.  Only one row should exist (pk=1)."""
    is_enabled          = models.BooleanField(default=False,
        help_text="When disabled, the Try VoidPanel banner and page are hidden.")
    headline            = models.CharField(max_length=200,
        default="Try VoidPanel Free — No Credit Card Needed",
        help_text="Short headline shown on the Try VoidPanel page.")
    sub_headline        = models.CharField(max_length=400, blank=True, default="",
        help_text="Optional one-line sub-heading below the main headline.")
    panel_url           = models.CharField(max_length=500, blank=True, default="",
        help_text="Full URL of the demo panel, e.g. https://demo.voidpanel.com")
    demo_username       = models.CharField(max_length=150, blank=True, default="demo",
        help_text="Username shown to visitors for the demo panel login.")
    demo_password       = models.CharField(max_length=300, blank=True, default="",
        help_text="Password shown to visitors (store plain text — this is a demo account).")
    server_ip           = models.CharField(max_length=100, blank=True, default="",
        help_text="Optional: IP address displayed for SSH / additional info.")
    note                = models.TextField(blank=True, default="",
        help_text="Optional note shown below the credentials (e.g. reset schedule, limitations).")
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Try VoidPanel Config"
        verbose_name_plural = "Try VoidPanel Config"

    def __str__(self):
        status = "ENABLED" if self.is_enabled else "DISABLED"
        return f"Try VoidPanel Config [{status}]"

    @classmethod
    def get_config(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'is_enabled': False,
            'headline': "Try VoidPanel Free — No Credit Card Needed",
            'demo_username': 'demo',
        })
        return obj


class BlogCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Blog Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_posts')
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    content = models.TextField(help_text="Rich text content of the blog post")
    featured_image = models.ImageField(upload_to='blog_images/', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    meta_description = models.CharField(max_length=300, blank=True)
    tags = models.CharField(max_length=250, blank=True, help_text="Comma-separated tags")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    @property
    def tag_list(self):
        if not self.tags: return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def __str__(self):
        return self.title


class GlobalEmailTemplate(models.Model):
    CATEGORY_CHOICES = [
        ('purchase',   'Purchase / Order Confirmation'),
        ('invoice',    'Invoice'),
        ('suspend',    'Service Suspension'),
        ('welcome',    'Welcome / Onboarding'),
        ('live_chat',  'Live Chat'),
        ('password',   'Password Reset'),
        ('general',    'General'),
    ]
    name         = models.CharField(max_length=200)
    subject      = models.CharField(max_length=300, blank=True, default='')
    category     = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='general')
    content_html = models.TextField()
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class GlobalWhatsAppTemplate(models.Model):
    CATEGORY_CHOICES = [
        ('purchase',   'Purchase / Order Confirmation'),
        ('invoice',    'Invoice'),
        ('suspend',    'Service Suspension'),
        ('welcome',    'Welcome / Onboarding'),
        ('live_chat',  'Live Chat Missed'),
        ('otp',        'OTP / Verification'),
        ('general',    'General'),
    ]
    name       = models.CharField(max_length=200)
    category   = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='general')
    body       = models.TextField(help_text='Message body. Use {{name}}, {{amount}}, {{service}}, etc. as placeholders.')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WhatsApp Template'
        verbose_name_plural = 'WhatsApp Templates'

    def __str__(self):
        return self.name


class ConnectResellerConfig(models.Model):
    """Stores the global ConnectReseller credentials and domain pricing margin."""
    api_key = models.CharField(max_length=255)
    reseller_id = models.CharField(max_length=100, blank=True)
    margin_percentage = models.PositiveIntegerField(default=20, help_text="Percentage margin to add to wholesale domain prices")
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "ConnectReseller Config"
        verbose_name_plural = "ConnectReseller Configs"

    def __str__(self):
        return f"ConnectReseller Config (Active: {self.is_active})"


class Coupon(models.Model):
    """Promotional discount codes for products and services."""
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount (₹)')
    ]
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank for unlimited uses")
    current_uses = models.PositiveIntegerField(default=0)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Billing Cycle applicability constraints
    applicable_monthly = models.BooleanField(default=True, help_text="Applicable for monthly billing cycle")
    applicable_quarterly = models.BooleanField(default=True, help_text="Applicable for quarterly billing cycle")
    applicable_annually = models.BooleanField(default=True, help_text="Applicable for annual/yearly billing cycle")

    def is_valid(self, billing_cycle=None):
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        if self.valid_until and timezone.now() > self.valid_until:
            return False
        if billing_cycle:
            billing_cycle = billing_cycle.lower()
            if billing_cycle == 'monthly' and not self.applicable_monthly:
                return False
            if billing_cycle == 'quarterly' and not self.applicable_quarterly:
                return False
            if billing_cycle in ['annually', 'yearly'] and not self.applicable_annually:
                return False
        return True

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else '₹'}"


class DomainOrder(models.Model):
    """Tracks domain registrations separately from HostingOrders."""
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('paid', 'Paid'),
        ('processing', 'Processing Registration'),
        ('active', 'Active (Registered)'),
        ('failed', 'Registration Failed'),
        ('cancelled', 'Cancelled')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='domain_orders')
    domain_name = models.CharField(max_length=200)
    years = models.PositiveIntegerField(default=1)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment')
    invoice = models.OneToOneField('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='domain_order')
    api_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.domain_name} ({self.user.username})"


class RazorpayConfig(models.Model):
    """
    Singleton — stores separate Test and Live Razorpay credentials.
    Admin switches between modes via is_live_mode flag.
    """
    # ── Test keys (rzp_test_…) ────────────────────────────────────────────────
    test_key_id     = models.CharField(max_length=100, blank=True,
                                       help_text="Test Key ID — starts with rzp_test_")
    test_key_secret = models.CharField(max_length=140, blank=True,
                                       help_text="Test Key Secret")

    # ── Live keys (rzp_live_…) ────────────────────────────────────────────────
    live_key_id     = models.CharField(max_length=100, blank=True,
                                       help_text="Live Key ID — starts with rzp_live_")
    live_key_secret = models.CharField(max_length=140, blank=True,
                                       help_text="Live Key Secret — treat like a password")

    # ── Webhook ───────────────────────────────────────────────────────────────
    webhook_secret  = models.CharField(max_length=140, blank=True,
                                       help_text="Webhook signing secret from Razorpay dashboard")

    # ── Control flags ─────────────────────────────────────────────────────────
    is_active       = models.BooleanField(default=False,
                                          help_text="Show Razorpay checkout on invoice pages")
    is_live_mode    = models.BooleanField(default=False,
                                          help_text="False = Test mode  |  True = Live (real money)")

    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Razorpay Config"
        verbose_name_plural = "Razorpay Configs"

    def __str__(self):
        mode  = "LIVE" if self.is_live_mode else "TEST"
        state = "Active" if self.is_active else "Disabled"
        return f"Razorpay [{mode}] — {state}"

    @classmethod
    def get(cls):
        """Returns the singleton, creating an empty one if none exists."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_active_keys(self):
        """
        Returns (key_id, key_secret) for the currently active mode.
        Returns ('', '') if the active mode has no keys configured.
        """
        if self.is_live_mode:
            return self.live_key_id, self.live_key_secret
        return self.test_key_id, self.test_key_secret

    @property
    def is_ready(self):
        """True when the gateway is active AND the current-mode keys are filled in."""
        if not self.is_active:
            return False
        kid, ksecret = self.get_active_keys()
        return bool(kid) and bool(ksecret)

    @property
    def mode_label(self):
        return "Live" if self.is_live_mode else "Test"

    @property
    def live_keys_complete(self):
        return bool(self.live_key_id) and bool(self.live_key_secret)

    @property
    def test_keys_complete(self):
        return bool(self.test_key_id) and bool(self.test_key_secret)



class RazorpayPayment(models.Model):
    """Audit log for every Razorpay payment attempt tied to an Invoice."""
    STATUS_CHOICES = [
        ('created',  'Order Created'),
        ('captured', 'Payment Captured'),
        ('failed',   'Payment Failed'),
        ('refunded', 'Refunded'),
    ]

    invoice           = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='razorpay_payments',
    )
    user              = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    razorpay_order_id   = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=255, blank=True)
    amount_paise        = models.PositiveIntegerField(help_text="Amount in paise (INR × 100)")
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    error_description   = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Razorpay Payment"
        verbose_name_plural = "Razorpay Payments"

    def __str__(self):
        return f"{self.razorpay_order_id} — {self.get_status_display()}"

    @property
    def amount_inr(self):
        return self.amount_paise / 100



class ResellerPricingSettings(models.Model):
    title = models.CharField(max_length=120, default='Reseller Custom Pricing Rules')
    base_price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=15.00, help_text="Base price containing the infrastructure minimal cost + voidpanel access")
    base_storage_gb = models.PositiveIntegerField(default=10, help_text="Base storage included in base price")
    base_accounts = models.PositiveIntegerField(default=5, help_text="Base accounts included in base price")
    
    price_per_10gb_storage = models.DecimalField(max_digits=8, decimal_places=2, default=1.50)
    price_per_5_accounts = models.DecimalField(max_digits=8, decimal_places=2, default=2.00)
    
    storage_min_gb = models.PositiveIntegerField(default=10)
    storage_max_gb = models.PositiveIntegerField(default=1000)
    accounts_min = models.PositiveIntegerField(default=5)
    accounts_max = models.PositiveIntegerField(default=500)
    
    yearly_discount_percent = models.PositiveIntegerField(default=15)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reseller Pricing Settings"
        verbose_name_plural = "Reseller Pricing Settings"

    def __str__(self):
        return self.title

    @classmethod
    def get(cls):
        """Returns the singleton, creating an empty one if none exists."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj




class AiProviderConfig(models.Model):
    """
    Singleton — stores API keys for all AI providers used by VoidPanel Agentic AI.
    Super admin manages these from /super-admin/ai-keys/.
    """
    PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('claude', 'Anthropic Claude'),
        ('openai', 'OpenAI ChatGPT'),
        ('huggingface', 'Hugging Face'),
    ]

    gemini_api_key  = models.CharField(max_length=255, blank=True, help_text="Google Gemini API Key")
    gemini_model    = models.CharField(max_length=80, default='gemini-1.5-flash')
    claude_api_key  = models.CharField(max_length=255, blank=True, help_text="Anthropic Claude API Key")
    claude_model    = models.CharField(max_length=80, default='claude-3-5-sonnet-20241022')
    openai_api_key  = models.CharField(max_length=255, blank=True, help_text="OpenAI API Key")
    openai_model    = models.CharField(max_length=80, default='gpt-4o')
    huggingface_api_key = models.CharField(max_length=255, blank=True, help_text="Hugging Face API Key")
    huggingface_model   = models.CharField(max_length=150, default='meta-llama/Llama-3.1-8B-Instruct')
    active_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='gemini',
                                       help_text="Which provider processes panel AI requests")
    tokens_per_request = models.PositiveIntegerField(default=1, help_text="Tokens deducted per chat request")
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "AI Provider Config"
        verbose_name_plural = "AI Provider Config"

    def __str__(self):
        return f"AI Config — Active: {self.get_active_provider_display()}"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def get_active_key(self):
        return {
            'gemini': self.gemini_api_key,
            'claude': self.claude_api_key,
            'openai': self.openai_api_key,
            'huggingface': self.huggingface_api_key
        }.get(self.active_provider, '')

    def get_active_model(self):
        return {
            'gemini': self.gemini_model,
            'claude': self.claude_model,
            'openai': self.openai_model,
            'huggingface': self.huggingface_model
        }.get(self.active_provider, '')

    @property
    def is_configured(self):
        return bool(self.get_active_key())


# ═══════════════════════════════════════════════════════════════
#  AUTO-SUSPEND SETTINGS  (singleton — pk=1)
# ═══════════════════════════════════════════════════════════════

class AutoSuspendSettings(models.Model):
    """
    Superadmin-controlled global settings for automatic service suspension
    when invoices become overdue.
    """
    enabled          = models.BooleanField(
        default=True,
        help_text='Master toggle — if False, NO automatic suspension will occur regardless of other settings.',
    )
    overdue_days     = models.PositiveIntegerField(
        default=15,
        help_text='Days after invoice due date before the hosting service is automatically suspended.',
    )
    warning_days     = models.PositiveIntegerField(
        default=10,
        help_text='Days after due date to send the customer a warning email before suspension.',
    )
    send_warning_email = models.BooleanField(
        default=True,
        help_text='Send an overdue warning email to the customer before suspension.',
    )
    send_suspension_email = models.BooleanField(
        default=True,
        help_text='Send a suspension notification email to the customer.',
    )
    updated_by       = models.CharField(max_length=150, blank=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Auto-Suspend Settings'
        verbose_name_plural = 'Auto-Suspend Settings'

    def __str__(self):
        status = 'ENABLED' if self.enabled else 'DISABLED'
        return f'Auto-Suspend [{status}] — {self.overdue_days} days overdue'

    @classmethod
    def get(cls):
        """Return singleton settings row (creates with defaults if missing)."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ── Professional Email ────────────────────────────────────────────────────────




class EmailService(models.Model):
    """
    An active Professional Email subscription for a customer.
    Provisioned automatically after payment; tracks domain, server, and billing.
    """
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('active',     'Active'),
        ('suspended',  'Suspended'),
        ('terminated', 'Terminated'),
    ]
    BILLING_CHOICES = [
        ('monthly',   'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually',  'Annually'),
    ]

    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_services',
    )
    plan_name     = models.CharField(max_length=150, blank=True, default='')

    @property
    def plan(self):
        return get_static_email_plan(self.plan_name)
    server        = models.ForeignKey(
        VoidPanelServer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_services',
    )
    domain        = models.CharField(max_length=120, help_text='Customer domain, e.g. mycompany.com')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CHOICES, default='monthly')
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    next_due_date = models.DateField(null=True, blank=True)
    panel_url     = models.URLField(blank=True, help_text='Base URL of the panel server')
    webmail_url   = models.URLField(blank=True, help_text='Direct Roundcube webmail URL')
    max_mailboxes = models.PositiveIntegerField(default=5)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Service'

    def __str__(self):
        return f'{self.domain} — {self.user.username} [{self.status}]'

    @property
    def mailbox_count(self):
        return self.mailboxes.count()

    @property
    def quota_used(self):
        return self.mailboxes.count()

    @property
    def quota_pct(self):
        if self.max_mailboxes == 0:
            return 0
        return int((self.mailboxes.count() / self.max_mailboxes) * 100)


class EmailMailbox(models.Model):
    """
    A single mailbox within an EmailService.
    Created via the portal or automatically on provisioning.
    """
    service       = models.ForeignKey(
        EmailService,
        on_delete=models.CASCADE,
        related_name='mailboxes',
    )
    email_address = models.EmailField(unique=True)
    password      = models.CharField(max_length=255, blank=True, help_text='Stored for portal display only')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['email_address']
        verbose_name = 'Email Mailbox'

    def __str__(self):
        return self.email_address


class SSLOrder(models.Model):
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('paid',            'Paid'),
        ('provisioning',    'Provisioning'),
        ('active',          'Active'),
        ('failed',          'Failed'),
        ('cancelled',       'Cancelled'),
    ]

    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ssl_orders',
    )
    plan_name     = models.CharField(max_length=150, blank=True, default='')

    @property
    def ssl_plan(self):
        return get_static_ssl_plan(self.plan_name)

    @property
    def plan(self):
        return self.ssl_plan

    invoice       = models.OneToOneField(
        Invoice,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ssl_order',
    )
    domain        = models.CharField(max_length=200)
    billing_cycle = models.CharField(max_length=20, default='quarterly')
    price         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status        = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment')
    provision_response = models.JSONField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SSL Order'

    def __str__(self):
        return f'SSLOrder #{self.pk} — {self.domain} — {self.user.username}'


class EmailOrder(models.Model):
    """
    Tracks a Professional Email plan purchase through the checkout → payment → provisioning
    pipeline.  Created at checkout, linked to an Invoice, and consumed by
    _activate_email_service() after Razorpay payment confirmation.
    """
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('provisioning',    'Provisioning'),
        ('active',          'Active'),
        ('failed',          'Failed'),
        ('cancelled',       'Cancelled'),
    ]

    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_orders',
    )
    plan_name     = models.CharField(max_length=150, blank=True, default='')

    @property
    def email_plan(self):
        return get_static_email_plan(self.plan_name)

    @property
    def plan(self):
        return self.email_plan
    invoice       = models.OneToOneField(
        Invoice,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_order',
    )
    domain        = models.CharField(max_length=200, help_text='Customer domain, e.g. mycompany.com')
    billing_cycle = models.CharField(max_length=20, default='monthly')
    price         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status        = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment')
    provision_response = models.JSONField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Order'

    def __str__(self):
        return f'EmailOrder #{self.pk} — {self.domain} — {self.user.username}'


# ── SSL Certificate Service ───────────────────────────────────────────────────




class SSLService(models.Model):
    """
    An active SSL Certificate subscription for a customer domain.
    Provisioned automatically after payment via certbot on the server.
    """
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('active',   'Active'),
        ('expiring', 'Expiring Soon'),
        ('expired',  'Expired'),
        ('failed',   'Failed'),
        ('suspended','Suspended'),
    ]

    user           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ssl_services',
    )
    plan_name      = models.CharField(max_length=150, blank=True, default='')

    @property
    def plan(self):
        return get_static_ssl_plan(self.plan_name)
    server         = models.ForeignKey(
        VoidPanelServer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ssl_services',
    )
    domain         = models.CharField(max_length=120, help_text='Primary domain (e.g. example.com)')
    san_domains    = models.JSONField(default=list, blank=True, help_text='Additional SANs for multi-domain plans')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    monthly_price  = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    next_due_date  = models.DateField(null=True, blank=True)
    cert_path      = models.CharField(max_length=255, blank=True, help_text='Path on server, e.g. /etc/letsencrypt/live/domain/')
    issued_at      = models.DateTimeField(null=True, blank=True)
    expires_at     = models.DateTimeField(null=True, blank=True)
    last_renewed_at= models.DateTimeField(null=True, blank=True)
    notes          = models.TextField(blank=True, help_text='Error messages or admin notes')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SSL Service'

    def __str__(self):
        return f'{self.domain} [{self.status}] — {self.user.username}'

    @property
    def days_until_expiry(self):
        if not self.expires_at:
            return None
        from django.utils import timezone
        delta = self.expires_at - timezone.now()
        return max(delta.days, 0)

    @property
    def expiry_pct(self):
        """Percentage of validity period remaining (for countdown bar)."""
        if not self.issued_at or not self.expires_at:
            return 0
        from django.utils import timezone
        total = (self.expires_at - self.issued_at).days or 90
        remaining = (self.expires_at - timezone.now()).days
        return max(0, min(100, int((remaining / total) * 100)))

    @property
    def is_expiring_soon(self):
        d = self.days_until_expiry
        return d is not None and d <= 30


# ══════════════════════════════════════════════════════
#  SOCIAL MEDIA MANAGEMENT — PLANS & SERVICES
# ══════════════════════════════════════════════════════




class SocialMediaService(models.Model):
    """
    A user's active Social Media Management subscription.
    Created automatically after payment via _activate_social_service().
    """
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('active',    'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    BILLING_CHOICES = [
        ('monthly',  'Monthly'),
        ('annually', 'Annually'),
    ]

    user                        = models.ForeignKey(
                                    settings.AUTH_USER_MODEL,
                                    on_delete=models.CASCADE,
                                    related_name='social_media_services'
                                  )
    plan_name                   = models.CharField(max_length=150, blank=True, default='')

    @property
    def plan(self):
        return get_static_social_plan(self.plan_name)
    status                      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle               = models.CharField(max_length=20, choices=BILLING_CHOICES, default='monthly')
    monthly_price               = models.DecimalField(max_digits=8, decimal_places=2)
    next_due_date               = models.DateField(null=True, blank=True)
    # Usage counters — reset each billing period
    accounts_connected          = models.PositiveIntegerField(default=0)
    posts_scheduled_this_month  = models.PositiveIntegerField(default=0)
    ai_captions_used_this_month = models.PositiveIntegerField(default=0)
    media_storage_used_mb       = models.PositiveIntegerField(default=0)
    # Timestamps
    activated_at                = models.DateTimeField(null=True, blank=True)
    created_at                  = models.DateTimeField(auto_now_add=True)
    updated_at                  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Social Media Service'
        verbose_name_plural = 'Social Media Services'

    def __str__(self):
        return f'{self.user.username} — {self.plan.name} ({self.status})'

    @property
    def is_active(self):
        return self.status == 'active'

    def can_connect_account(self):
        if self.plan.max_accounts == 0:
            return True
        return self.accounts_connected < self.plan.max_accounts

    def can_schedule_post(self):
        if self.plan.max_scheduled_posts_per_month == 0:
            return True
        return self.posts_scheduled_this_month < self.plan.max_scheduled_posts_per_month

    def can_use_ai(self):
        if not self.plan.has_ai_captions:
            return False
        if self.plan.max_ai_captions_per_month == 0:
            return True
        return self.ai_captions_used_this_month < self.plan.max_ai_captions_per_month

    def platform_allowed(self, code):
        if not self.plan.allowed_platforms:
            return True
        return code in self.plan.allowed_platforms

# ══════════════════════════════════════════════════════
#  MARKETING SUITE — PLANS & SERVICES
# ══════════════════════════════════════════════════════




class MarketingService(models.Model):
    """
    A user's active Marketing Suite subscription.
    Created automatically after payment via _activate_marketing_service().
    """
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('active',    'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    BILLING_CHOICES = [
        ('monthly',  'Monthly'),
        ('annually', 'Annually'),
    ]

    user                        = models.ForeignKey(
                                    settings.AUTH_USER_MODEL,
                                    on_delete=models.CASCADE,
                                    related_name='marketing_services'
                                  )
    plan_name                   = models.CharField(max_length=150, blank=True, default='')

    @property
    def plan(self):
        return get_static_marketing_plan(self.plan_name)
    status                      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle               = models.CharField(max_length=20, choices=BILLING_CHOICES, default='monthly')
    monthly_price               = models.DecimalField(max_digits=8, decimal_places=2)
    next_due_date               = models.DateField(null=True, blank=True)
    
    # Usage counters — reset each billing period (except leads which is total)
    leads_stored                = models.PositiveIntegerField(default=0)
    emails_sent_this_month      = models.PositiveIntegerField(default=0)
    ai_copies_used_this_month   = models.PositiveIntegerField(default=0)
    
    # Timestamps
    activated_at                = models.DateTimeField(null=True, blank=True)
    created_at                  = models.DateTimeField(auto_now_add=True)
    updated_at                  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Marketing Service'
        verbose_name_plural = 'Marketing Services'

    def __str__(self):
        return f'{self.user.username} — {self.plan.name} ({self.status})'

    @property
    def is_active(self):
        return self.status == 'active'

    def can_add_lead(self):
        if self.plan.max_leads == 0:
            return True
        return self.leads_stored < self.plan.max_leads

    def can_send_email(self):
        if self.plan.max_emails_per_month == 0:
            return True
        return self.emails_sent_this_month < self.plan.max_emails_per_month

    def can_use_ai(self):
        if self.plan.max_ai_copies_per_month == 0:
            return True
        return self.ai_copies_used_this_month < self.plan.max_ai_copies_per_month


# ── Marketing Hub Data Models ──────────────────────────────────────────────────

class MarketingCampaign(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'), ('sms', 'SMS'), ('whatsapp', 'WhatsApp'),
        ('social', 'Social Media'), ('ad', 'Paid Ad'),
    ]
    STATUS_CHOICES = [('draft','Draft'),('scheduled','Scheduled'),('sent','Sent'),('paused','Paused')]

    service      = models.ForeignKey(MarketingService, on_delete=models.CASCADE, related_name='campaigns')
    name         = models.CharField(max_length=200)
    channel      = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='email')
    subject      = models.CharField(max_length=300, blank=True)
    body         = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_count   = models.PositiveIntegerField(default=0)
    open_rate    = models.FloatField(default=0)
    click_rate   = models.FloatField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.channel})"


class MarketingLead(models.Model):
    SOURCE_CHOICES = [
        ('manual','Manual'),('form','Website Form'),('import','CSV Import'),
        ('ad','Paid Ad'),('organic','Organic'),
    ]
    service  = models.ForeignKey(MarketingService, on_delete=models.CASCADE, related_name='leads')
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
    service   = models.ForeignKey(MarketingService, on_delete=models.CASCADE, related_name='ab_tests')
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


# ── Social Media Platform API Settings (Super Admin) ──────────────────────────
class SocialPlatformSettings(models.Model):
    """
    Singleton — super admin configures per-platform API keys and enabled status.
    Panels can query the API endpoint to sync these settings.
    """
    PLATFORM_CODES = ['fb', 'ig', 'tw', 'li', 'yt', 'tt', 'pi', 'th', 'gb']

    # Facebook
    facebook_enabled       = models.BooleanField(default=False)
    facebook_app_id        = models.CharField(max_length=255, blank=True)
    facebook_app_secret    = models.CharField(max_length=255, blank=True)

    # Instagram (same Meta app)
    instagram_enabled      = models.BooleanField(default=False)
    instagram_app_id       = models.CharField(max_length=255, blank=True)
    instagram_app_secret   = models.CharField(max_length=255, blank=True)

    # Twitter / X
    twitter_enabled        = models.BooleanField(default=False)
    twitter_api_key        = models.CharField(max_length=255, blank=True)
    twitter_api_secret     = models.CharField(max_length=255, blank=True)
    twitter_bearer_token   = models.CharField(max_length=512, blank=True)

    # LinkedIn
    linkedin_enabled       = models.BooleanField(default=False)
    linkedin_client_id     = models.CharField(max_length=255, blank=True)
    linkedin_client_secret = models.CharField(max_length=255, blank=True)

    # YouTube / Google
    youtube_enabled        = models.BooleanField(default=False)
    google_client_id       = models.CharField(max_length=255, blank=True)
    google_client_secret   = models.CharField(max_length=255, blank=True)

    # TikTok
    tiktok_enabled         = models.BooleanField(default=False)
    tiktok_client_key      = models.CharField(max_length=255, blank=True)
    tiktok_client_secret   = models.CharField(max_length=255, blank=True)

    # Pinterest
    pinterest_enabled      = models.BooleanField(default=False)
    pinterest_app_id       = models.CharField(max_length=255, blank=True)
    pinterest_app_secret   = models.CharField(max_length=255, blank=True)

    # Threads (Meta)
    threads_enabled        = models.BooleanField(default=False)
    threads_app_id         = models.CharField(max_length=255, blank=True)
    threads_app_secret     = models.CharField(max_length=255, blank=True)

    # Google Business
    gbusiness_enabled      = models.BooleanField(default=False)

    updated_at             = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Social Platform Settings'
        verbose_name_plural = 'Social Platform Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def enabled_platform_list(self):
        """Return list of enabled platform codes, e.g. ['fb', 'ig', 'tw']"""
        result = []
        mapping = {
            'fb': self.facebook_enabled,
            'ig': self.instagram_enabled,
            'tw': self.twitter_enabled,
            'li': self.linkedin_enabled,
            'yt': self.youtube_enabled,
            'tt': self.tiktok_enabled,
            'pi': self.pinterest_enabled,
            'th': self.threads_enabled,
            'gb': self.gbusiness_enabled,
        }
        return [code for code, enabled in mapping.items() if enabled]


class OAuthRelayState(models.Model):
    """
    Stores temporary OAuth token data and platform profile info on voidpanel.com
    during the server-to-server relay OAuth flow.
    """
    relay_code = models.CharField(max_length=255, unique=True)
    license_key = models.CharField(max_length=255)
    token_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OAuth Relay State"
        verbose_name_plural = "OAuth Relay States"

    def __str__(self):
        return f"Relay {self.relay_code[:8]}... for License {self.license_key[:8]}..."


class FundTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fund_transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=[('deposit', 'Deposit'), ('purchase', 'Purchase'), ('refund', 'Refund'), ('adjustment', 'Admin Adjustment')])
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Fund {self.amount} for {self.user.username}"


class ChipTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chip_transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=[('grant', 'Grant'), ('purchase', 'Purchase'), ('adjustment', 'Admin Adjustment')])
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Chip {self.amount} for {self.user.username}"


# ══════════════════════════════════════════════════════════════════
#  DIGITAL SUITES — PLANS, SERVICES, ORDERS
#  (Social Media Suite / SEO Suite / Marketing Suite)
# ══════════════════════════════════════════════════════════════════

class SuitePlan(models.Model):
    """
    Admin-managed plan for one of the three Digital Suites.
    Created/edited via /super-admin/suite-plans/ — no code changes required.
    """
    SUITE_CHOICES = [
        ('social',    'Social Media Suite'),
        ('seo',       'SEO Suite'),
        ('marketing', 'Marketing Suite'),
    ]
    BILLING_CHOICES = [
        ('monthly',  'Monthly'),
        ('annually', 'Annually'),
    ]

    suite             = models.CharField(max_length=20, choices=SUITE_CHOICES, db_index=True)
    name              = models.CharField(max_length=120)
    slug              = models.SlugField(max_length=120, unique=True)
    short_description = models.TextField(blank=True)
    monthly_price     = models.DecimalField(max_digits=10, decimal_places=2)
    yearly_price      = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                            help_text='Annual price (total). Set 0 to disable yearly billing.')
    server            = models.ForeignKey(
                            'VoidPanelServer',
                            on_delete=models.SET_NULL,
                            null=True, blank=True,
                            related_name='suite_plans',
                            help_text='VoidPanel server that hosts this suite.',
                        )
    # plan_slug used to call /control/api/suite/create-account/ on the panel server
    panel_plan_slug   = models.CharField(max_length=50, blank=True, default='',
                            help_text='Slug sent to panel API e.g. starter / growth / pro')
    features          = models.JSONField(default=list,
                            help_text='List of feature strings shown on pricing card.')
    limits            = models.JSONField(default=dict,
                            help_text='Dict of plan limits e.g. {"accounts":5,"posts_per_month":90}')
    is_active         = models.BooleanField(default=True)
    is_featured       = models.BooleanField(default=False,
                            help_text='Highlight this plan as "Most Popular".')
    sort_order        = models.PositiveIntegerField(default=0)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['suite', 'sort_order', 'monthly_price']
        verbose_name = 'Suite Plan'
        verbose_name_plural = 'Suite Plans'

    def __str__(self):
        return f"{self.get_suite_display()} — {self.name}"

    @property
    def yearly_savings(self):
        """Monthly equivalent when billed yearly vs. 12 × monthly."""
        if not self.yearly_price:
            return 0
        return (self.monthly_price * 12) - self.yearly_price

    @property
    def suite_icon(self):
        icons = {
            'social':    'fa-brands fa-instagram',
            'seo':       'fa-solid fa-magnifying-glass-chart',
            'marketing': 'fa-solid fa-bullhorn',
        }
        return icons.get(self.suite, 'fa-solid fa-bolt')

    @property
    def suite_color(self):
        colors = {
            'social':    '#f472b6',
            'seo':       '#818cf8',
            'marketing': '#fbbf24',
        }
        return colors.get(self.suite, '#6366f1')


class SuiteService(models.Model):
    """
    Active Digital Suite subscription for a website user.
    Created automatically after payment is confirmed.
    SSO token pattern mirrors HostingService.
    """
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('active',    'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    BILLING_CHOICES = [
        ('monthly',  'Monthly'),
        ('annually', 'Annually'),
    ]

    user          = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                        related_name='suite_services',
                    )
    plan          = models.ForeignKey(
                        SuitePlan,
                        on_delete=models.PROTECT,
                        related_name='services',
                    )
    suite         = models.CharField(max_length=20)   # snapshotted from plan
    service_name  = models.CharField(max_length=150)  # e.g. "Social Media Suite — Growth"
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CHOICES, default='monthly')
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshotted
    server        = models.ForeignKey(
                        'VoidPanelServer',
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='suite_services',
                    )
    next_due_date = models.DateField(null=True, blank=True)
    activated_at  = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    # ── SSO auto-login token (single-use, 5-minute TTL) ─────────────────────
    sso_token         = models.CharField(max_length=64, blank=True)
    sso_token_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Suite Service'
        verbose_name_plural = 'Suite Services'

    def __str__(self):
        return f"{self.service_name} ({self.user.username}) — {self.status}"

    def save(self, *args, **kwargs):
        is_suspending = False
        if self.pk:
            old = SuiteService.objects.filter(pk=self.pk).values('status').first()
            if old and old['status'] != 'suspended' and self.status == 'suspended':
                is_suspending = True
        
        super().save(*args, **kwargs)
        
        if is_suspending:
            try:
                from voidpanel.views import send_whatsapp_notification_async
                msg = f"Suite Service Suspended: {self.service_name}\nReason: Billing renewal overdue or manual administrator action.\nContact support to reactivate."
                send_whatsapp_notification_async(self.user, msg, 'service_suspend')
            except Exception as e:
                import logging
                logging.error(f"Error sending WhatsApp suite suspension alert: {e}")

    @property
    def is_active(self):
        return self.status == 'active'

    def generate_sso_token(self):
        """Generate a fresh single-use SSO token valid for 5 minutes."""
        import secrets
        from django.utils import timezone
        from datetime import timedelta
        self.sso_token = secrets.token_hex(32)
        self.sso_token_expires = timezone.now() + timedelta(minutes=5)
        self.save(update_fields=['sso_token', 'sso_token_expires'])
        return self.sso_token

    def validate_sso_token(self, token):
        """Returns True if token matches and has not expired. Invalidates on success."""
        from django.utils import timezone
        if not self.sso_token or self.sso_token != token:
            return False
        if self.sso_token_expires and timezone.now() > self.sso_token_expires:
            return False
        self.sso_token = ''
        self.sso_token_expires = None
        self.save(update_fields=['sso_token', 'sso_token_expires'])
        return True

    @property
    def panel_base_url(self):
        """Return the base panel URL from the linked server."""
        if self.server:
            return (self.server.login_url or self.server.url or '').rstrip('/')
        return ''


class SuiteOrder(models.Model):
    """
    Pending order record created at checkout, before payment.
    Converted to SuiteService on payment confirmation.
    """
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('paid',            'Paid'),
        ('failed',          'Failed'),
        ('cancelled',       'Cancelled'),
    ]

    user          = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                        related_name='suite_orders',
                    )
    invoice       = models.OneToOneField(
                        'Invoice',
                        on_delete=models.CASCADE,
                        related_name='suite_order',
                    )
    plan          = models.ForeignKey(
                        SuitePlan,
                        on_delete=models.PROTECT,
                        related_name='orders',
                    )
    suite         = models.CharField(max_length=20)
    billing_cycle = models.CharField(max_length=20, default='monthly')
    price         = models.DecimalField(max_digits=10, decimal_places=2)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                     default='pending_payment')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Suite Order'

    def __str__(self):
        return f"SuiteOrder #{self.id} — {self.suite}/{self.plan.name} — {self.status}"


class WhatsAppConfig(models.Model):
    """
    Stores settings and global alert preferences for WhatsApp integration.
    Only one record should exist.
    """
    is_enabled        = models.BooleanField(default=False)
    phone_number      = models.CharField(max_length=30, blank=True, default='')
    
    # Auto-alert triggers
    alert_on_invoice_created  = models.BooleanField(default=True)
    alert_on_service_suspend  = models.BooleanField(default=True)
    alert_on_ticket_opened    = models.BooleanField(default=True)
    
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'WhatsApp Config'
        verbose_name_plural = 'WhatsApp Configs'

    def __str__(self):
        return f"WhatsApp Config (Enabled: {self.is_enabled})"


class WhatsAppLog(models.Model):
    """
    Audit log tracking all sent WhatsApp alert and broadcast notifications.
    """
    MSG_TYPES = [
        ('alert',     'Alert Notification'),
        ('broadcast', 'Sales/Marketing Broadcast'),
    ]
    STATUSES = [
        ('sent',   'Sent'),
        ('failed', 'Failed'),
    ]
    user        = models.ForeignKey(
                      settings.AUTH_USER_MODEL,
                      on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name='whatsapp_logs',
                  )
    phone_to    = models.CharField(max_length=30)
    message     = models.TextField()
    msg_type    = models.CharField(max_length=30, choices=MSG_TYPES)
    status      = models.CharField(max_length=20, choices=STATUSES, default='sent')
    error_msg   = models.TextField(blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WhatsApp Log'
        verbose_name_plural = 'WhatsApp Logs'

    def __str__(self):
        return f"WhatsApp Log #{self.id} to {self.phone_to} — {self.status}"

