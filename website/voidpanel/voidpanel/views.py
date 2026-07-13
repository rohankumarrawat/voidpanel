from datetime import timedelta
from decimal import Decimal
from smtplib import SMTPException
import json
import secrets
import threading
import time
import string
import random
try:
    import paramiko
except ImportError:
    paramiko = None
from django.core.mail import send_mail

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail.backends.smtp import EmailBackend
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from data.models import (
    AiProviderConfig,
    AutoSuspendSettings,
    BlogCategory,
    BlogPost,
    ChipTransaction,
    FundTransaction,
    ConnectResellerConfig,
    Coupon,
    CustomerProfile,
    DomainOrder,
    EmailMailbox,
    EmailOrder,
    EmailPlan,
    EmailPlanOverride,
    EmailService,
    HostingOrder,
    HostingPricingSettings,
    HostingService,
    Installed,
    Invoice,
    Message,
    OutboundEmailProfile,
    PanelLicenseRecord,
    RazorpayConfig,
    RazorpayPayment,
    ResellerPricingSettings,
    SSLPlan,
    SSLPlanOverride,
    SSLService,
    SuitePlan,
    SuiteService,
    SuiteOrder,
    VoidPanelServer,
    PortalActivity,
    StaffProfile,
    StaffRole,
    SupportTicket,
    TicketReply,
    WordPressInstallation,
    admindocumentation,
    clientdocumentation,
    negative_review,
    positive_review,
    updates,
    RemoteInstallationJob,
    get_static_hosting_package,
    get_static_email_plan,
    get_static_ssl_plan,
    StaticPlanWrapper,
)



import hashlib
import hmac
import json as _rjson
import logging
_logger = logging.getLogger(__name__)


# ─── Welcome Email ───────────────────────────────────────────────────────────────

def send_welcome_email(service, provision_result, invoice=None):
    """
    Send a branded welcome email with hosting credentials to the customer.
    Called after a successful provision_hosting_account() call.
    Uses OutboundEmailProfile (if configured) or falls back to Django EMAIL_* settings.
    """
    import smtplib
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    from django.conf import settings

    username  = provision_result.get('username', '')
    password  = provision_result.get('password', '')
    panel_url = provision_result.get('panel_url', '') or (service.panel_url or '')
    if service.server and service.server.login_url:
        panel_url = service.server.login_url

    if not username or not password:
        _logger.warning('send_welcome_email: missing credentials in provision_result — skipping email')
        return

    customer_name  = service.user.get_full_name() or service.user.username
    customer_email = service.user.email

    nameservers_list = []
    if service.server and service.server.nameservers:
        nameservers_list = [ns.strip() for ns in service.server.nameservers.split('\n') if ns.strip()]
    if not nameservers_list:
        nameservers_list = ['ns1.voidpanel.com', 'ns2.voidpanel.com']

    context = {
        'customer_name':  customer_name,
        'customer_email': customer_email,
        'domain':         service.domain,
        'plan_name':      service.service_name,
        'username':       username,
        'password':       password,
        'panel_url':      panel_url,
        'storage_gb':     service.storage_gb,
        'invoice_number': invoice.invoice_number if invoice else '—',
        'amount':         invoice.total if invoice else '—',
        'nameservers':    nameservers_list,
    }

    subject  = f'🎉 Your Hosting Account for {service.domain} is Ready — VoidPanel'
    html_msg = render_to_string('emails/welcome_hosting.html', context)
    text_msg = (
        f'Hi {customer_name},\n\n'
        f'Your hosting account for {service.domain} is now active.\n\n'
        f'Panel URL : {panel_url}\n'
        f'Username  : {username}\n'
        f'Password  : {password}\n\n'
        f'Please change your password after first login.\n\n'
        f'Need help? Open a ticket at https://voidpanel.com/portal/ticket/new/\n\n'
        f'— VoidPanel Team'
    )

    # Try OutboundEmailProfile first
    try:
        smtp_profile = (
            OutboundEmailProfile.objects
            .filter(is_active=True, send_on_service_activated=True)
            .order_by('-is_default')
            .first()
        )
    except Exception:
        smtp_profile = None

    try:
        if smtp_profile:
            email = EmailMessage(
                subject=subject,
                body=html_msg,
                from_email=f'{smtp_profile.from_name or "VoidPanel"} <{smtp_profile.from_email}>',
                to=[customer_email],
                reply_to=[smtp_profile.reply_to_email] if smtp_profile.reply_to_email else [],
            )
            email.content_subtype = 'html'
            backend = EmailBackend(
                host=smtp_profile.smtp_host,
                port=smtp_profile.smtp_port,
                username=smtp_profile.smtp_username,
                password=smtp_profile.smtp_password,
                use_tls=smtp_profile.use_tls,
                use_ssl=smtp_profile.use_ssl,
                fail_silently=False,
            )
            backend.open()
            backend.send_messages([email])
            backend.close()
        else:
            email = EmailMessage(
                subject=subject,
                body=html_msg,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer_email],
            )
            email.content_subtype = 'html'
            email.send(fail_silently=False)

        _logger.info('Welcome email sent to %s for domain %s', customer_email, service.domain)

    except Exception as exc:
        _logger.error('Failed to send welcome email to %s: %s', customer_email, exc)


def get_inr_to_currency_rate(target_currency):
    """
    Returns how much target_currency equals 1 INR.
    E.g. if target_currency is USD, returns ~0.012.
    """
    target_currency = target_currency.upper()
    if target_currency == 'INR':
        return Decimal('1.0')

    from django.core.cache import cache
    cache_key = f"inr_rate_{target_currency}"
    rate = cache.get(cache_key)
    if rate is not None:
        return Decimal(str(rate))

    try:
        import requests
        r = requests.get("https://open.er-api.com/v6/latest/INR", timeout=5)
        if r.status_code == 200:
            data = r.json()
            rates = data.get('rates', {})
            rate_val = rates.get(target_currency)
            if rate_val:
                cache.set(cache_key, rate_val, 3600)  # Cache for 1 hour
                return Decimal(str(rate_val))
    except Exception as e:
        _logger.error(f"Error fetching exchange rate: {e}")

    # Fallback rates
    fallbacks = {
        'USD': Decimal('0.012'),
        'EUR': Decimal('0.011'),
        'GBP': Decimal('0.0094'),
    }
    return fallbacks.get(target_currency, Decimal('1.0'))


def calculate_invoice_payment_split(invoice, profile):
    """
    Returns (chips_to_use, funds_to_deduct_inr, remaining_due_in_currency)
    """
    total_due = invoice.total
    currency = invoice.currency.upper()
    
    # Treat legacy USD entries as INR if the amount is INR-based
    if currency == 'USD' and total_due >= 10:
        currency = 'INR'

    # Skip chips/funds deduction for deposit invoices
    if invoice.description.startswith("Deposit Funds"):
        return 0, Decimal('0.00'), total_due

    pricing_settings = HostingPricingSettings.objects.first()
    credits_per_rupee = getattr(pricing_settings, 'credits_per_rupee', 100) or 100

    # Get rate: 1 INR = rate target_currency
    inr_to_curr = get_inr_to_currency_rate(currency)
    
    # Value of 1 Chip in target_currency:
    # 1 Chip = (1 / credits_per_rupee) * inr_to_curr
    chip_value_in_curr = (Decimal('1.0') / Decimal(str(credits_per_rupee))) * inr_to_curr

    # Step 1: Use chips first
    available_chips = profile.balance_chips
    if chip_value_in_curr > 0:
        chips_needed = int(total_due / chip_value_in_curr)
    else:
        chips_needed = 0
    chips_to_use = min(available_chips, chips_needed)

    chips_value_deducted = Decimal(str(chips_to_use)) * chip_value_in_curr
    remaining_due = max(Decimal('0.00'), total_due - chips_value_deducted)

    # Step 2: Use available funds (funds are in INR on the wallet, so convert to target currency)
    # Available funds in target currency:
    available_funds_in_curr = profile.balance_funds * inr_to_curr
    funds_to_use_in_curr = min(available_funds_in_curr, remaining_due)

    # Convert back to INR to get the exact amount to deduct from profile.balance_funds
    if inr_to_curr > 0:
        funds_to_deduct_inr = (funds_to_use_in_curr / inr_to_curr).quantize(Decimal('0.01'))
    else:
        funds_to_deduct_inr = Decimal('0.00')
    
    remaining_due = max(Decimal('0.00'), remaining_due - funds_to_use_in_curr)

    return chips_to_use, funds_to_deduct_inr, remaining_due


def _activate_service_after_provision(order, invoice=None):
    """
    Common logic: assign server, call provisioner, save panel_url + credentials,
    auto-install WordPress (for WordPress Hosting), send welcome email.
    """
    from voidpanel.provisioner import provision_hosting_account

    if not order.service:
        return {'status': 'error', 'message': 'No service linked to order'}

    # Assign server from package
    if hasattr(order, 'package') and order.package and order.package.server:
        order.service.server = order.package.server
        order.service.save(update_fields=['server'])

    # ── Pre-flag reseller services so provisioner routes correctly ────────────
    is_reseller = (
        getattr(order.service, 'is_reseller', False) or
        getattr(order.service, 'product_type', '') == 'Reseller Hosting' or
        (hasattr(order, 'package') and order.package and
         getattr(order.package, 'package_type', '') == 'reseller')
    )
    if is_reseller and not order.service.is_reseller:
        order.service.is_reseller = True
        order.service.save(update_fields=['is_reseller'])

    result = provision_hosting_account(order.service)
    order.provision_response = result

    if result.get('status') in ('ok', 'success'):
        order.service.status = 'active'

        # Save panel URL and server hostname returned by the API
        panel_url = result.get('panel_url', '') or result.get('reseller_dashboard_url', '')
        hostname  = result.get('hostname', '') or result.get('server_ip', '')
        if panel_url:
            # Store base URL only (strip /control/ or /control/reseller/ suffix)
            import re as _re
            panel_url = _re.sub(r'/control(/reseller)?/?$', '', panel_url.rstrip('/'))
            order.service.panel_url = panel_url
        if hostname:
            order.service.server_hostname = hostname

        # ── Save provisioned credentials so client can see them in portal ──
        username = result.get('username', '')
        password = result.get('password', '')
        if username:
            order.service.panel_username = username
        if password:
            order.service.panel_password = password

        save_fields = ['status', 'panel_url', 'server_hostname', 'panel_username', 'panel_password', 'is_reseller']
        order.service.save(update_fields=save_fields)
        order.status = 'active'
        order.save(update_fields=['status', 'provision_response'])

        # Log activity for the customer
        PortalActivity.objects.create(
            user=order.service.user,
            category='account',
            title=f'{"Reseller" if is_reseller else "Hosting"} account provisioned: {order.service.domain}',
            description=f'Username: {username} — Dashboard: {panel_url or order.service.server_hostname}',
        )


        # ── Auto-install WordPress for WordPress Hosting ───────────────────
        if getattr(order.service, 'product_type', '') == 'WordPress Hosting':
            _auto_install_wordpress(order.service, invoice=invoice)
        else:
            # Send standard welcome email for non-WP services
            send_welcome_email(order.service, result, invoice=invoice)

    else:
        order.status = 'failed'
        order.save(update_fields=['status', 'provision_response'])
        PortalActivity.objects.create(
            user=order.service.user,
            category='account',
            title=f'Provisioning failed: {order.service.domain}',
            description=result.get('message', 'Unknown error from provisioner'),
        )

    return result


def _auto_install_wordpress(service, invoice=None):
    """
    Called automatically after provisioning a WordPress Hosting service.
    Installs WordPress via the panel API v2, creates a WordPressInstallation record.
    """
    import requests as _rq

    # Create a pending install record immediately
    wp_install, _ = WordPressInstallation.objects.get_or_create(
        service=service,
        defaults={'status': 'installing'},
    )
    wp_install.status = 'installing'
    wp_install.save(update_fields=['status'])

    # Determine panel API base URL
    if service.server:
        api_base = service.server.url.rstrip('/')
        api_key  = service.server.api_key
    elif service.panel_url:
        api_base = service.panel_url.rstrip('/')
        api_key  = ''
    else:
        wp_install.status = 'failed'
        wp_install.save(update_fields=['status'])
        return

    # Generate WP admin credentials (use customer email + random password)
    import secrets as _secrets
    wp_admin_user  = service.panel_username or 'wpadmin'
    wp_admin_email = service.user.email
    wp_admin_pass  = _secrets.token_urlsafe(12)

    try:
        resp = _rq.post(
            f'{api_base}/api/v2/wordpress/install/',
            json={
                'domain':            service.domain,
                'wp_admin_user':     wp_admin_user,
                'wp_admin_email':    wp_admin_email,
                'wp_admin_password': wp_admin_pass,
                'site_title':        service.domain,
            },
            headers={'X-API-Token': api_key},
            timeout=180,   # WP download can take time
        )
        data = resp.json()
    except Exception as exc:
        _logger.error('WP auto-install failed for %s: %s', service.domain, exc)
        wp_install.status = 'failed'
        wp_install.save(update_fields=['status'])
        return

    if data.get('status') == 'success':
        from django.utils import timezone
        wp_install.status        = 'active'
        wp_install.wp_admin_user  = wp_admin_user
        wp_install.wp_admin_email = wp_admin_email
        wp_install.wp_admin_url   = data.get('data', {}).get('wp_admin_url', f'http://{service.domain}/wp-admin/')
        wp_install.installed_at   = timezone.now()
        wp_install.save()

        PortalActivity.objects.create(
            user=service.user,
            category='account',
            title=f'WordPress installed: {service.domain}',
            description=f'WP Admin: {wp_admin_user} | URL: {wp_install.wp_admin_url}',
        )

        # Send WP welcome email with credentials
        _send_wordpress_welcome_email(service, wp_install, wp_admin_pass, invoice=invoice)
    else:
        wp_install.status = 'failed'
        wp_install.save(update_fields=['status'])
        _logger.error('WP install API error for %s: %s', service.domain, data.get('message'))


def _send_wordpress_welcome_email(service, wp_install, wp_admin_pass, invoice=None):
    """Sends WordPress credentials welcome email to the customer."""
    try:
        from django.core.mail import EmailMessage
        from django.conf import settings
        customer_email = service.user.email
        customer_name  = service.user.get_full_name() or service.user.username
        html = f"""
<div style="font-family:'Inter',Arial,sans-serif;max-width:580px;margin:auto;background:#0f172a;color:#e2e8f0;border-radius:16px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#7c3aed,#4f46e5);padding:36px 32px;text-align:center;">
    <h1 style="margin:0;font-size:1.8rem;color:#fff;">&#127758; Your WordPress Site is Live!</h1>
    <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);">Your WordPress hosting is ready</p>
  </div>
  <div style="padding:28px 32px;">
    <p>Hi {customer_name},</p>
    <p>Your WordPress site for <strong>{service.domain}</strong> has been automatically set up. Here are your login details:</p>
    <div style="background:#1e293b;border-radius:12px;padding:20px 24px;margin:20px 0;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="color:#94a3b8;padding:6px 0;">Site URL</td><td style="font-weight:700;">http://{service.domain}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">WP Admin URL</td><td style="font-weight:700;">{wp_install.wp_admin_url}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Admin Username</td><td style="font-weight:700;">{wp_install.wp_admin_user}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Admin Email</td><td style="font-weight:700;">{wp_install.wp_admin_email}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Admin Password</td><td style="font-weight:700;color:#4ade80;">{wp_admin_pass}</td></tr>
      </table>
    </div>
    <p style="color:#94a3b8;font-size:.85rem;">Manage your WordPress, reset passwords, and issue SSL directly from your <a href="https://voidpanel.com/portal/" style="color:#7c3aed;">client portal</a>.</p>
    <p style="color:#94a3b8;font-size:.85rem;">If you did not make this request, please contact support immediately.</p>
  </div>
  <div style="background:#0f172a;padding:16px 32px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;font-size:.75rem;color:#475569;">
    VoidPanel — Managed WordPress Hosting
  </div>
</div>"""
        email = EmailMessage(
            subject=f'[VoidPanel] Your WordPress Site is Ready — {service.domain}',
            body=html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer_email],
        )
        email.content_subtype = 'html'
        email.send(fail_silently=True)
    except Exception as exc:
        _logger.error('WP welcome email failed for %s: %s', service.domain, exc)


# ─── Serializers ────────────────────────────────────────────────────────────────


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['text', 'date', 'photo']


class AdminDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = admindocumentation
        fields = ['text', 'date', 'link']


class ClientDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = clientdocumentation
        fields = ['text', 'date', 'link']


class InstalledSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installed
        fields = ['ip', 'number']


class UpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = updates
        fields = ['version']


class PositiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = positive_review
        fields = ['review', 'user', 'content']


class NegativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = negative_review
        fields = ['review', 'user', 'category', 'content']


# ─── API Views ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
def positive(request):
    serializer = PositiveSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def negative(request):
    serializer = NegativeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def latest_messages(request):
    msgs = Message.objects.all().order_by('-date')[:4]
    serializer = MessageSerializer(msgs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def update(request):
    """
    GET /version_name/
    Returns the latest VoidPanel version info.

    Format:
    {
        "version": "2.1.0",
        "notes": "Bug fixes and new reseller features",
        "script_url": "https://voidpanel.com/updates/2.1.0/update.sh",
        "released": "2026-05-01"
    }
    """
    try:
        latest = updates.objects.filter(is_active=True).order_by('-version').first()
        if not latest:
            return Response({'version': '1.0', 'notes': '', 'script_url': '', 'released': ''})
        return Response({
            'version':    latest.version,
            'notes':      latest.notes,
            'script_url': latest.script_url or f'https://voidpanel.com/updatepanel.sh',
            'released':   latest.date.isoformat() if latest.date else '',
        })
    except Exception:
        return Response({'version': '1.0', 'notes': '', 'script_url': '', 'released': ''})


def parse_version(v_str):
    import re
    if not v_str:
        return (0, 0, 0)
    # Match digits, e.g. "2.3.0" -> (2, 3, 0)
    match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?$', v_str)
    if not match:
        return (0, 0, 0)
    return tuple(int(x) if x is not None else 0 for x in match.groups())


@api_view(['GET'])
def version_migration_path(request):
    """
    GET /version_migration_path/?from=1.0.0
    Returns the ordered list of update steps a server must apply
    to go from its current version to the latest.

    Used by the control panel's updatepanel view to do step-by-step updates.
    """
    current = request.GET.get('from', '').strip()
    all_versions = list(updates.objects.filter(is_active=True))
    if not all_versions:
        return Response({'current': current, 'latest': current, 'steps': [], 'up_to_date': True})

    # Sort versions using semantic sorting
    all_versions.sort(key=lambda x: parse_version(x.version))
    latest = all_versions[-1].version

    # Filter versions strictly greater than current version
    current_parsed = parse_version(current)
    steps = []
    for v in all_versions:
        if not current or parse_version(v.version) > current_parsed:
            steps.append({
                'version':    v.version,
                'script_url': v.script_url or 'https://voidpanel.com/updatepanel.sh',
                'notes':      v.notes,
                'is_breaking': v.is_breaking,
                'min_version': v.min_version,
            })

    return Response({
        'current':    current or 'unknown',
        'latest':     latest,
        'steps':      steps,
        'up_to_date': len(steps) == 0,
    })




# ── Update Script Serving ────────────────────────────────────────────────────

def serve_update_script(request):
    """Serve the general fallback updatepanel.sh script."""
    import os
    from django.http import HttpResponse, Http404
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'static', 'updatepanel.sh'
    )
    if not os.path.exists(script_path):
        raise Http404('Update script not found')
    with open(script_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/x-shellscript')


def serve_install_script(request):
    """Serve the install.sh script for one-command installations."""
    import os
    from django.http import HttpResponse, Http404
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'static', 'install.sh'
    )
    if not os.path.exists(script_path):
        raise Http404('Install script not found')
    with open(script_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/x-shellscript')


def serve_version_script(request, version):
    """Serve a version-specific update.sh — e.g. /static/updates/2.1.0/update.sh"""
    import os, re
    from django.http import HttpResponse, Http404
    # Sanitize: only allow semver-like version strings
    if not re.match(r'^\d+\.\d+(\.\d+)?$', version):
        raise Http404('Invalid version format')
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'static', 'updates', version, 'update.sh'
    )
    if not os.path.exists(script_path):
        raise Http404(f'Update script for v{version} not found')
    with open(script_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/x-shellscript')


def serve_release_package(request, version):
    """Serve a version-specific tar.gz package — e.g. /releases/voidpanel-2.2.0.tar.gz"""
    import os, re
    from django.http import FileResponse, Http404
    
    version_clean = version
    if version.startswith("voidpanel-"):
        version_clean = version.replace("voidpanel-", "")
    if version_clean.endswith(".tar.gz"):
        version_clean = version_clean.replace(".tar.gz", "")

    if not re.match(r'^\d+\.\d+(\.\d+)?$', version_clean):
        raise Http404('Invalid version format')

    package_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'media', 'releases', f'voidpanel-{version_clean}.tar.gz'
    )
    if not os.path.exists(package_path):
        raise Http404(f'Release package for v{version_clean} not found')
        
    return FileResponse(open(package_path, 'rb'), as_attachment=True, filename=f'voidpanel-{version_clean}.tar.gz')



@api_view(['GET'])
def admindocs(request):
    docs = admindocumentation.objects.all().order_by('date')
    serializer = AdminDocSerializer(docs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def clientdocs(request):
    docs = clientdocumentation.objects.all().order_by('date')
    serializer = ClientDocSerializer(docs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def increment_number(request):
    ip_address = request.data.get('ip')
    installed_obj, _ = Installed.objects.get_or_create(ip=ip_address)
    installed_obj.number += 1
    installed_obj.save()
    serializer = InstalledSerializer(installed_obj)
    return Response(serializer.data, status=status.HTTP_200_OK)


def ensure_default_hosting_catalog():
    pricing, _ = HostingPricingSettings.objects.get_or_create(
        id=1,
        defaults={
            'title': 'Primary Pricing Rules',
            'storage_price_per_10gb': Decimal('1.50'),
            'ram_price_per_1gb': Decimal('4.00'),
            'cpu_price_per_core': Decimal('8.00'),
            'bandwidth_100gb_price': Decimal('5.00'),
            'bandwidth_500gb_price': Decimal('12.00'),
            'bandwidth_1000gb_price': Decimal('20.00'),
            'bandwidth_unmetered_price': Decimal('35.00'),
            'storage_min_gb': 10,
            'storage_max_gb': 500,
            'ram_min_gb': 1,
            'ram_max_gb': 32,
            'cpu_min_cores': 1,
            'cpu_max_cores': 16,
            'quarterly_discount_percent': 0,
            'annual_discount_percent': 10,
        },
    )
    defaults = [
        {
            'name': 'Starter',
            'slug': 'starter',
            'short_description': 'Great for a first website or lightweight applications.',
            'storage_gb': 25,
            'ram_gb': 2,
            'cpu_cores': 1,
            'bandwidth_label': '500GB',
            'allowed_domains': 1,
            'monthly_price': Decimal('19.00'),
            'sort_order': 1,
        },
        {
            'name': 'Professional',
            'slug': 'professional',
            'short_description': 'Balanced compute for production workloads and growing businesses.',
            'storage_gb': 80,
            'ram_gb': 8,
            'cpu_cores': 4,
            'bandwidth_label': '1TB',
            'allowed_domains': 10,
            'monthly_price': Decimal('49.00'),
            'is_featured': True,
            'sort_order': 2,
        },
        {
            'name': 'Business',
            'slug': 'business',
            'short_description': 'Higher performance footprint for agencies and serious multi-site hosting.',
            'storage_gb': 200,
            'ram_gb': 16,
            'cpu_cores': 8,
            'bandwidth_label': 'Unmetered',
            'allowed_domains': 50,
            'monthly_price': Decimal('99.00'),
            'sort_order': 3,
        },
    ]
    return pricing


def _bandwidth_choices(pricing):
    return [
        {'value': '100GB', 'label': '100GB', 'price': float(pricing.bandwidth_100gb_price)},
        {'value': '500GB', 'label': '500GB', 'price': float(pricing.bandwidth_500gb_price)},
        {'value': '1TB', 'label': '1TB', 'price': float(pricing.bandwidth_1000gb_price)},
        {'value': 'Unmetered', 'label': 'Unmetered', 'price': float(pricing.bandwidth_unmetered_price)},
    ]


# ─── Page Views ─────────────────────────────────────────────────────────────────

def index(request):
    return render(request, "index.html")


def get_active_hosting_packages(package_type):
    from data.models import _STATIC_HOSTING_PACKAGES, get_static_hosting_package, HostingPackageOverride
    res = []
    seen = set()
    for pid, p in _STATIC_HOSTING_PACKAGES.items():
        if p['package_type'] == package_type:
            pkg = get_static_hosting_package(pid)
            if pkg and getattr(pkg, 'is_active', True):
                res.append(pkg)
                seen.add(pid)
    try:
        extra_ovs = HostingPackageOverride.objects.filter(package_type=package_type).exclude(package_id__in=seen)
        for ov in extra_ovs:
            pkg = get_static_hosting_package(ov.package_id)
            if pkg and getattr(pkg, 'is_active', True):
                res.append(pkg)
    except Exception:
        pass
    res.sort(key=lambda x: (getattr(x, 'sort_order', 0) or 0, getattr(x, 'id', 0)))
    return res

def get_all_hosting_packages(package_type=None):
    from data.models import _STATIC_HOSTING_PACKAGES, get_static_hosting_package, HostingPackageOverride
    res = []
    seen = set()
    for pid, p in _STATIC_HOSTING_PACKAGES.items():
        if package_type is None or p['package_type'] == package_type:
            pkg = get_static_hosting_package(pid)
            if pkg:
                res.append(pkg)
                seen.add(pid)
    try:
        extra_ovs = HostingPackageOverride.objects.all()
        if package_type:
            extra_ovs = extra_ovs.filter(package_type=package_type)
        extra_ovs = extra_ovs.exclude(package_id__in=seen)
        for ov in extra_ovs:
            pkg = get_static_hosting_package(ov.package_id)
            if pkg:
                res.append(pkg)
    except Exception:
        pass
    res.sort(key=lambda x: (getattr(x, 'sort_order', 0) or 0, getattr(x, 'id', 0)))
    return res


def pricing(request):
    pricing_settings = ensure_default_hosting_catalog()
    packages = get_active_hosting_packages('shared')

    builder_config = {
        'storage': {
            'min': pricing_settings.storage_min_gb,
            'max': pricing_settings.storage_max_gb,
            'step': 10,
            'pricePerStep': float(pricing_settings.storage_price_per_10gb),
            'default': max(pricing_settings.storage_min_gb, 20),
        },
        'email': {
            'min': 5,
            'max': 200,
            'step': 5,
            'pricePerStep': 25.0,
            'default': 20,
        },
        'ftp': {
            'min': 1,
            'max': 50,
            'step': 1,
            'pricePerStep': 15.0,
            'default': 5,
        },
        'db': {
            'min': 1,
            'max': 50,
            'step': 1,
            'pricePerStep': 20.0,
            'default': 5,
        },
        'bandwidthChoices': _bandwidth_choices(pricing_settings),
        'discounts': {
            'monthly': 0,
            'quarterly': pricing_settings.quarterly_discount_percent,
            'annually': pricing_settings.annual_discount_percent,
        },
    }
    return render(
        request,
        "pricing.html",
        {
            'packages': packages,
            'builder_config': builder_config,
            'pricing_settings': pricing_settings,
        },
    )

def wordpress_hosting(request):
    pricing_settings = ensure_default_hosting_catalog()
    packages = get_active_hosting_packages('wordpress')
    builder_config = {
        'storage': {
            'min': pricing_settings.storage_min_gb,
            'max': pricing_settings.storage_max_gb,
            'step': 10,
            'pricePerStep': float(pricing_settings.storage_price_per_10gb),
            'default': max(pricing_settings.storage_min_gb, 15),
        },
        'email': {
            'min': 5,
            'max': 200,
            'step': 5,
            'pricePerStep': 25.0,
            'default': 20,
        },
        'ftp': {
            'min': 1,
            'max': 50,
            'step': 1,
            'pricePerStep': 15.0,
            'default': 5,
        },
        'db': {
            'min': 1,
            'max': 50,
            'step': 1,
            'pricePerStep': 20.0,
            'default': 5,
        },
        'bandwidthChoices': _bandwidth_choices(pricing_settings),
        'discounts': {
            'monthly': 0,
            'quarterly': pricing_settings.quarterly_discount_percent,
            'annually': pricing_settings.annual_discount_percent,
        },
    }
    return render(request, "wordpress_hosting.html", {
        "packages": packages,
        "builder_config": builder_config,
        "pricing_settings": pricing_settings,
    })

def order_summary(request):
    pricing_settings = ensure_default_hosting_catalog()
    builder_config = {
        'discounts': {
            'monthly': 0,
            'quarterly': pricing_settings.quarterly_discount_percent,
            'annually': pricing_settings.annual_discount_percent,
        }
    }
    return render(request, "order_summary.html", {'builder_config': builder_config})


def _ensure_default_reseller_catalog():
    """Seed pricing settings and three default reseller packages."""
    settings_obj, _ = ResellerPricingSettings.objects.get_or_create(
        pk=1,
        defaults={
            'title': 'Reseller Custom Pricing Rules',
            'base_price_monthly': Decimal('15.00'),
            'base_storage_gb': 10,
            'base_accounts': 5,
            'price_per_10gb_storage': Decimal('1.50'),
            'price_per_5_accounts': Decimal('2.00'),
            'storage_min_gb': 10,
            'storage_max_gb': 1000,
            'accounts_min': 5,
            'accounts_max': 500,
            'yearly_discount_percent': 15,
        },
    )
    defaults = [
        {
            'name': 'Startup Reseller',
            'slug': 'startup-reseller',
            'short_description': 'Perfect for freelancers launching their first hosting brand.',
            'storage_gb': 50,
            'max_accounts': 10,
            'monthly_price': Decimal('19.00'),
            'yearly_price': Decimal('193.00'),
            'sort_order': 1,
        },
        {
            'name': 'Business Reseller',
            'slug': 'business-reseller',
            'short_description': 'A solid pool for agencies managing a growing client base.',
            'storage_gb': 200,
            'max_accounts': 50,
            'monthly_price': Decimal('49.00'),
            'yearly_price': Decimal('499.00'),
            'is_featured': True,
            'sort_order': 2,
        },
        {
            'name': 'Enterprise Reseller',
            'slug': 'enterprise-reseller',
            'short_description': 'Maximum resources for established hosting businesses.',
            'storage_gb': 500,
            'max_accounts': 200,
            'monthly_price': Decimal('99.00'),
            'yearly_price': Decimal('999.00'),
            'sort_order': 3,
        },
    ]
    return settings_obj


def reseller_hosting(request):
    pricing_settings = _ensure_default_reseller_catalog()
    shared_pricing = ensure_default_hosting_catalog()
    packages = get_active_hosting_packages('reseller')
    builder_config = {
        'basePriceMonthly': float(pricing_settings.base_price_monthly),
        'baseStorageGb': pricing_settings.base_storage_gb,
        'baseAccounts': pricing_settings.base_accounts,
        'pricePerStorage': float(pricing_settings.price_per_10gb_storage),
        'pricePerAccounts': float(pricing_settings.price_per_5_accounts),
        'storage': {
            'min': pricing_settings.storage_min_gb,
            'max': pricing_settings.storage_max_gb,
            'default': 100,
            'step': 10,
        },
        'accounts': {
            'min': pricing_settings.accounts_min,
            'max': pricing_settings.accounts_max,
            'default': 20,
            'step': 5,
        },
        'email': {
            'min': 50,
            'max': 1000,
            'default': 200,
            'step': 50,
            'pricePerStep': 100.0,
        },
        'db': {
            'min': 50,
            'max': 1000,
            'default': 200,
            'step': 50,
            'pricePerStep': 80.0,
        },
        'bandwidthChoices': _bandwidth_choices(shared_pricing),
        'yearlyDiscountPercent': pricing_settings.yearly_discount_percent,
    }
    return render(request, 'reseller.html', {
        'packages': packages,
        'builder_config': builder_config,
        'builder_config_json': json.dumps(builder_config),
    })


@login_required(login_url='/login/')
def reseller_configure(request):
    """
    Step 1 of reseller checkout: collect the reseller's own domain,
    company/brand name, and billing cycle BEFORE creating the invoice.
    On POST, stores config in session and redirects to payment checkout.
    """
    pkg_slug   = request.GET.get('pkg', '') or request.POST.get('pkg', '')
    storage_gb = int(request.GET.get('storage', 100) or request.POST.get('storage', 100))
    accounts   = int(request.GET.get('accounts', 20)  or request.POST.get('accounts', 20))

    pkg = None
    if pkg_slug:
        pkg = get_static_hosting_package(pkg_slug)
        if pkg:
            storage_gb = pkg.storage_gb
            accounts   = pkg.allowed_domains  # In static reseller packages, allowed_domains is used for max_accounts

    if request.method == 'POST':
        domain       = request.POST.get('domain', '').strip().lower()
        company_name = request.POST.get('company_name', '').strip()
        cycle        = request.POST.get('cycle', 'monthly')

        if not domain:
            messages.error(request, 'Please enter your domain name.')
            return redirect(request.get_full_path())

        # Basic domain sanity check
        import re as _re
        if not _re.match(r'^[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]\.[a-z]{2,}$', domain):
            messages.error(request, 'Please enter a valid domain (e.g. myhosting.com).')
            return redirect(request.get_full_path())

        # Save to session so checkout can read it
        request.session['reseller_domain']       = domain
        request.session['reseller_company']      = company_name
        request.session['reseller_cycle']        = cycle
        request.session['reseller_pkg_slug']     = pkg_slug
        request.session['reseller_storage_gb']   = storage_gb
        request.session['reseller_accounts']     = accounts

        return redirect('/reseller-hosting/order/')

    return render(request, 'reseller_configure.html', {
        'pkg': pkg,
        'pkg_slug': pkg_slug,
        'storage_gb': storage_gb,
        'accounts': accounts,
    })


@login_required(login_url='/login/')
def reseller_order_checkout(request):
    """
    Reseller plan order checkout — Step 2.
    Reads domain/company/cycle from session (set by reseller_configure).
    Creates HostingService (is_reseller=True) + Invoice + HostingOrder.
    Redirects to invoice payment page — same payment flow as shared hosting.
    """
    from datetime import timedelta, date
    from decimal import Decimal
    from data.models import (
        HostingService, Invoice, HostingOrder, PortalActivity,
    )

    # ── Read from session (set by reseller_configure) ────────────────────────
    domain       = request.session.pop('reseller_domain',   None)
    company_name = request.session.pop('reseller_company',  '')
    cycle        = request.session.pop('reseller_cycle',    'monthly')
    pkg_slug     = request.session.pop('reseller_pkg_slug', request.GET.get('pkg', ''))
    storage_gb   = int(request.session.pop('reseller_storage_gb', request.GET.get('storage', 100)))
    accounts     = int(request.session.pop('reseller_accounts',   request.GET.get('accounts', 20)))

    # If no domain in session (user hit /order/ directly), redirect to configure
    if not domain:
        qs = f'?pkg={pkg_slug}' if pkg_slug else f'?storage={storage_gb}&accounts={accounts}'
        return redirect(f'/reseller-hosting/configure/{qs}')

    # ── Resolve package ─────────────────────────────────────────────────────
    pkg = None
    pkg_name = 'Custom Reseller'
    monthly_price = Decimal('19.00')

    if pkg_slug:
        pkg = get_static_hosting_package(pkg_slug)
        if pkg:
            storage_gb    = pkg.storage_gb
            accounts      = pkg.allowed_domains
            pkg_name      = pkg.name
            monthly_price = pkg.monthly_price

    # ── Calculate total ──────────────────────────────────────────────────────
    if cycle == 'yearly':
        total = (monthly_price * 12 * Decimal('0.85')).quantize(Decimal('0.01'))
    else:
        total = monthly_price

    # ── Build service + invoice + order ─────────────────────────────────────
    today     = date.today()
    due_delta = 365 if cycle == 'yearly' else 30
    next_due  = today + timedelta(days=due_delta)

    ensure_portal_seed_data(request.user)

    with transaction.atomic():
        service = HostingService.objects.create(
            user=request.user,
            service_name=pkg_name,
            domain=domain,                  # ← user's actual domain
            product_type='Reseller Hosting',
            is_reseller=True,
            status='pending',
            billing_cycle=cycle,
            monthly_price=monthly_price,
            next_due_date=next_due,
            server_hostname='in-mum-01.voidpanel.cloud',
            storage_gb=storage_gb,
            bandwidth_gb=0,
        )
        inv_count = Invoice.objects.filter(user=request.user).count()
        invoice = Invoice.objects.create(
            user=request.user,
            invoice_number=f'VP-{request.user.id:04d}-{inv_count + 1:03d}',
            description=f'{pkg_name} — {storage_gb} GB / {accounts} accounts ({cycle}) — {domain}',
            status='unpaid',
            total=total,
            currency='INR',
            due_date=today + timedelta(days=7),
        )

        order = HostingOrder.objects.create(
            user=request.user,
            package_name=pkg.slug if pkg else 'custom-reseller',
            service=service,
            invoice=invoice,
            domain=domain,
            billing_cycle=cycle,
            total=total,
            status='pending_payment',
        )
        PortalActivity.objects.create(
            user=request.user,
            category='billing',
            title=f'Reseller order placed: {pkg_name}',
            description=f'{storage_gb} GB / {accounts} accounts — Domain: {domain} — Company: {company_name} — Total: ₹{total}',
        )

    return redirect(f'/portal/invoice/{invoice.id}/pay/')








def _provision_reseller_account(user, storage_gb, max_accounts, package_name='Custom', company_name=''):

    """
    Calls the VoidPanel control panel API to create/activate a ResellerProfile.
    Uses VoidPanelServer from Super Admin → Servers for URL and API key.
    Returns dict with status, credentials, and panel URL.
    """
    import requests as _req

    # Get the server config from Super Admin → Servers
    server = None
    try:
        from data.models import VoidPanelServer
        server = VoidPanelServer.objects.filter(is_active=True).first()
    except Exception:
        pass

    if not server:
        return {
            'status': 'error',
            'error': 'Reseller API key rejected. Update the API key in Super Admin → Servers for this server.',
        }

    base_url = server.url.rstrip('/')
    api_key = server.api_key

    payload = {
        'api_key':      api_key,        # body key (legacy compat)
        'username':     user.username,
        'email':        user.email,
        'storage_gb':   int(storage_gb),
        'max_accounts': int(max_accounts),
        'package_name': package_name,
        'company_name': company_name,
    }
    try:
        resp = _req.post(
            f'{base_url}/control/api/reseller/provision/',
            json=payload,
            headers={
                'X-API-Token': api_key,     # header auth (preferred)
                'Content-Type': 'application/json',
            },
            timeout=15,
        )
        return resp.json()
    except Exception as e:
        _logger.error('Reseller provisioning failed: %s', e)
        return {'status': 'error', 'error': str(e)}


def aboutus(request):
    return render(request, "aboutus.html")


def addemail(request):
    return render(request, "addemail.html")


def ssl(request):
    return render(request, "addssl.html")


def voidpanelinfo(request):
    return render(request, "blogs/voidpanelinfo.html")


def overview(request):
    return render(request, "overview.html")


# ── Public Blog Views ────────────────────────────────────────────────────────
def blog_list_public(request):
    posts = BlogPost.objects.filter(status='published')
    return render(request, 'blog_list.html', {'posts': posts})

def blog_detail_public(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, status='published')
    
    # Optional: fetch some related or latest posts
    latest_posts = BlogPost.objects.filter(status='published').exclude(id=post.id)[:3]
    return render(request, 'blog_detail.html', {'post': post, 'latest_posts': latest_posts})


# ── Super Admin Blog Management ──────────────────────────────────────────────
@login_required
def super_admin_blogs(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('/')
    
    status_filter = request.GET.get('status', '')
    
    if status_filter:
        posts = BlogPost.objects.filter(status=status_filter)
    else:
        posts = BlogPost.objects.all()
        
    stats = {
        'total': BlogPost.objects.count(),
        'published': BlogPost.objects.filter(status='published').count(),
        'pending': BlogPost.objects.filter(status='pending_approval').count(),
    }
    
    return render(request, 'super_admin_blogs.html', {
        'posts': posts,
        'stats': stats,
        'active_page': 'blogs'
    })

@login_required
def super_admin_blog_write(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('/')
        
    categories = BlogCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        slug = request.POST.get('slug') or slugify(title)
        content = request.POST.get('content')
        cat_id = request.POST.get('category_id')
        tags = request.POST.get('tags', '')
        
        # Staff auto-publish immediately
        status = request.POST.get('status', 'published')
        
        # Image attachment
        featured_image = request.FILES.get('featured_image')

        # Use category if valid
        category = None
        if cat_id:
            try:
                category = BlogCategory.objects.get(id=cat_id)
            except BlogCategory.DoesNotExist:
                pass

        if BlogPost.objects.filter(slug=slug).exists():
            messages.error(request, "A blog post with this slug already exists.")
            return render(request, 'super_admin_blog_write.html', {'categories': categories, 'active_page': 'blogs'})

        post = BlogPost(
            title=title,
            slug=slug,
            author=request.user,
            category=category,
            content=content,
            tags=tags,
            status=status,
        )
        if featured_image:
            post.featured_image = featured_image
            
        if status == 'published':
            post.published_at = timezone.now()
            
        post.save()
        messages.success(request, f"Blog post '{title}' saved successfully.")
        return redirect('/super-admin/blogs/')

    return render(request, 'super_admin_blog_write.html', {
        'categories': categories,
        'active_page': 'blogs'
    })

@login_required
def super_admin_blog_action(request, post_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('/')
        
    post = get_object_or_404(BlogPost, id=post_id)
    action = request.POST.get('action')
    
    if action == 'publish':
        post.status = 'published'
        post.published_at = timezone.now()
        post.save()
        messages.success(request, f"Post '{post.title}' has been published.")
    elif action == 'reject':
        post.status = 'rejected'
        post.save()
        messages.success(request, f"Post '{post.title}' was rejected.")
    elif action == 'draft':
        post.status = 'draft'
        post.save()
        messages.success(request, f"Post '{post.title}' reverted to draft.")
    elif action == 'delete':
        post.delete()
        messages.success(request, "Blog post deleted.")
        
    return redirect('/super-admin/blogs/')

# ── Client/Portal Blog Submission ────────────────────────────────────────────
@login_required
def portal_blog_write(request):
    categories = BlogCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        cat_id = request.POST.get('category_id')
        featured_image = request.FILES.get('featured_image')
        
        # User posts are ALWAYS pending approval
        status = 'pending_approval'
        slug = slugify(title)

        # Basic dedup slug logic for users
        counter = 1
        original_slug = slug
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

        category = None
        if cat_id:
            try:
                category = BlogCategory.objects.get(id=cat_id)
            except BlogCategory.DoesNotExist:
                pass

        post = BlogPost(
            title=title,
            slug=slug,
            author=request.user,
            category=category,
            content=content,
            status=status,
        )
        if featured_image:
            post.featured_image = featured_image
            
        post.save()
        messages.success(request, "Thank you! Your blog post has been submitted and is pending admin approval.")
        return redirect('/portal/')

    return render(request, 'portal_blog_write.html', {
        'categories': categories,
    })


def db(request):
    return render(request, "db.html")


def chpass(request):
    return render(request, "chpass.html")


def addweb(request):
    return render(request, "addweb.html")


def notifications(request):
    context = {'data': Message.objects.all().order_by('-date')}
    return render(request, "notifications.html", context)


def docs(request):
    return render(request, "docs.html")


def blog(request):
    return render(request, "blog.html")


def blog1(request):
    return render(request, "blogs/blog1.html")


def blog2(request):
    return render(request, "blogs/blog2.html")


def blog3(request):
    return render(request, "blogs/blog3.html")


def blogs(request):
    return render(request, "blogs.html")


def whmcs(request):
    return render(request, "whmcs.html")


def whmcs_module(request):
    return render(request, "whmcs.html")


def _invoice_number_for_user(user, offset):
    return f"VP-{user.id or 0:04d}-{offset:03d}"


def _ticket_number_for_user(user, offset):
    return f"VP-TKT-{user.id or 0:04d}-{offset:03d}"


def _generate_username_from_email(email):
    base = email.split('@')[0].strip().lower()
    cleaned = ''.join(char if char.isalnum() else '_' for char in base).strip('_')
    cleaned = cleaned or 'user'
    username = cleaned[:150]
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix_text = f"_{suffix}"
        username = f"{cleaned[:150 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return username


def _detect_country_from_request(request):
    header_candidates = [
        request.META.get('HTTP_CF_IPCOUNTRY'),
        request.META.get('HTTP_X_VERCEL_IP_COUNTRY'),
        request.META.get('HTTP_CLOUDFRONT_VIEWER_COUNTRY'),
    ]
    for candidate in header_candidates:
        if candidate and candidate not in {'XX', 'T1'}:
            return candidate.upper()

    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    for part in accept_language.split(','):
        language = part.split(';')[0].strip()
        if '-' in language:
            region = language.split('-')[-1].upper()
            if len(region) == 2 and region.isalpha():
                return region
        if '_' in language:
            region = language.split('_')[-1].upper()
            if len(region) == 2 and region.isalpha():
                return region

    return 'IN'


def ensure_default_staff_roles():
    defaults = [
        {
            'name': 'Operations Manager',
            'description': 'Handles infrastructure, client onboarding, and operational escalations.',
            'can_manage_clients': True,
            'can_manage_infrastructure': True,
            'can_manage_support': True,
        },
        {
            'name': 'Billing Manager',
            'description': 'Responsible for invoices, renewals, and payment workflows.',
            'can_manage_clients': True,
            'can_manage_billing': True,
        },
        {
            'name': 'Support Lead',
            'description': 'Owns support queues, priority tickets, and customer communication.',
            'can_manage_support': True,
            'can_manage_clients': True,
        },
        {
            'name': 'Platform Administrator',
            'description': 'Full internal portal access for systems and staff coordination.',
            'can_manage_clients': True,
            'can_manage_billing': True,
            'can_manage_support': True,
            'can_manage_infrastructure': True,
            'can_manage_staff': True,
        },
    ]
    for item in defaults:
        StaffRole.objects.get_or_create(
            slug=slugify(item['name']),
            defaults=item,
        )


def _staff_permissions_summary(role):
    if not role:
        return []
    flags = [
        ('Clients', role.can_manage_clients),
        ('Billing', role.can_manage_billing),
        ('Support', role.can_manage_support),
        ('Infrastructure', role.can_manage_infrastructure),
        ('Staff', role.can_manage_staff),
    ]
    return [label for label, enabled in flags if enabled]


def _ensure_staff_profile(user, role=None, is_portal_admin=False, department='', display_title=''):
    profile, created = StaffProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': role,
            'is_portal_admin': is_portal_admin,
            'department': department,
            'display_title': display_title,
            'last_seen_at': timezone.now(),
        },
    )
    if not created:
        updated_fields = []
        if role and profile.role_id != role.id:
            profile.role = role
            updated_fields.append('role')
        if display_title and profile.display_title != display_title:
            profile.display_title = display_title
            updated_fields.append('display_title')
        if department and profile.department != department:
            profile.department = department
            updated_fields.append('department')
        if profile.is_portal_admin != is_portal_admin:
            profile.is_portal_admin = is_portal_admin
            updated_fields.append('is_portal_admin')
        profile.last_seen_at = timezone.now()
        updated_fields.append('last_seen_at')
        profile.save(update_fields=updated_fields)
    return profile


EMAIL_EVENT_FIELDS = [
    ('send_on_purchase', 'Send mail on purchase'),
    ('send_on_invoice_created', 'Send invoice created mail'),
    ('send_on_payment_received', 'Send payment received mail'),
    ('send_on_service_activated', 'Send service activation mail'),
    ('send_on_service_suspended', 'Send service suspension mail'),
    ('send_on_service_unsuspended', 'Send service reactivation mail'),
    ('send_on_service_terminated', 'Send service termination mail'),
    ('send_on_ticket_opened', 'Send ticket opened mail'),
    ('send_on_ticket_reply', 'Send ticket reply mail'),
    ('send_on_login_success', 'Send login successful mail'),
    ('send_on_password_reset', 'Send password reset mail'),
    ('send_on_account_created', 'Send account created mail'),
    ('send_on_security_alert', 'Send security alert mail'),
    ('send_on_system_update', 'Send system update mail'),
    ('send_on_domain_expiry_warning', 'Send domain expiry warning'),
    ('send_on_ssl_expiry_warning', 'Send SSL expiry warning'),
    ('send_on_live_chat', 'Send mail on live chat'),
]

EMAIL_PURPOSE_CHOICES = OutboundEmailProfile.PURPOSE_CHOICES


def _email_permission_summary(profile):
    return [label for field, label in EMAIL_EVENT_FIELDS if getattr(profile, field)]


def _test_email_profile_connection(profile):
    """
    Test the SMTP profile by opening a connection AND sending a real test email
    to the profile's own from_email address so the admin can verify delivery.
    Raises an exception with a descriptive message if anything fails.
    """
    from django.core.mail import EmailMessage as _EM
    from django.core.mail.backends.smtp import EmailBackend as _EB

    # 1. Test the raw SMTP connection first
    backend = _EB(
        host=profile.smtp_host,
        port=profile.smtp_port,
        username=profile.smtp_username or None,
        password=profile.smtp_password or None,
        use_tls=profile.use_tls,
        use_ssl=profile.use_ssl,
        timeout=10,
        fail_silently=False,
    )
    opened = backend.open()
    if not opened:
        raise SMTPException('SMTP server did not accept the connection.')

    # 2. Send a test email to the from_email address itself
    html_body = """
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 28px;
                border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
      <h2 style="color: #1e3a8a; margin: 0 0 16px;">✅ SMTP Test — VoidPanel</h2>
      <p style="color: #334155; font-size: 0.95rem; line-height: 1.6;">
        This is a test email from your VoidPanel installation.<br>
        Your SMTP configuration for profile <strong>{name}</strong> is working correctly!
      </p>
      <hr style="border:none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
      <p style="color: #94a3b8; font-size: 0.78rem;">
        Sent from: {host}:{port} &nbsp;|&nbsp; TLS: {tls} &nbsp;|&nbsp; SSL: {ssl}
      </p>
    </div>
    """.format(
        name=profile.profile_name,
        host=profile.smtp_host,
        port=profile.smtp_port,
        tls=profile.use_tls,
        ssl=profile.use_ssl,
    )
    test_email = _EM(
        subject=f'✅ VoidPanel SMTP Test — {profile.profile_name}',
        body=html_body,
        from_email=f'{profile.from_name or "VoidPanel"} <{profile.from_email}>',
        to=[profile.from_email],
    )
    test_email.content_subtype = 'html'
    backend.send_messages([test_email])
    backend.close()


def ensure_portal_seed_data(user, profile_defaults=None):
    profile_defaults = profile_defaults or {}
    profile, created = CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            'company_name': profile_defaults.get('company_name', ''),
            'phone': profile_defaults.get('phone', ''),
            'country': profile_defaults.get('country', 'India'),
            'city': profile_defaults.get('city', ''),
        },
    )
    if created:
        pricing_settings = HostingPricingSettings.objects.first()
        bonus = getattr(pricing_settings, 'signup_bonus_chips', 5000)
        profile.balance_chips = bonus
        profile.save(update_fields=['balance_chips'])
        if bonus > 0:
            ChipTransaction.objects.create(
                user=user,
                amount=bonus,
                transaction_type='grant',
                description='Registration bonus chips'
            )

    if not user.portal_activities.exists():
        PortalActivity.objects.create(
            user=user,
            category='account',
            title='Customer account created',
            description='Portal access was enabled and the workspace was prepared.',
        )


@login_required(login_url='/login/')
def portal(request):
    ensure_portal_seed_data(request.user)

    # ── Handle incoming reseller order activation ──────────────────────────
    reseller_provision_result = None
    new_service = request.GET.get('new_service', '')
    if new_service in ('reseller', 'reseller_custom') and request.user.is_authenticated:
        pkg_slug    = request.GET.get('pkg', '')
        storage_gb  = int(request.GET.get('storage', 50))
        max_accounts= int(request.GET.get('accounts', 10))
        cycle       = request.GET.get('cycle', 'monthly')
        pkg_name    = 'Custom Reseller'
        if pkg_slug:
            pkg_obj = get_static_hosting_package(pkg_slug)
            if pkg_obj:
                storage_gb   = pkg_obj.storage_gb
                max_accounts = pkg_obj.allowed_domains
                pkg_name     = pkg_obj.name
        reseller_provision_result = _provision_reseller_account(
            request.user, storage_gb, max_accounts, pkg_name,
            company_name=request.user.get_full_name() or request.user.username,
        )
    # ──────────────────────────────────────────────────────────────────────

    profile = request.user.customer_profile
    services = request.user.hosting_services.all().order_by('next_due_date')
    email_services = request.user.email_services.all().order_by('-created_at')
    invoices = request.user.invoices.all()
    tickets = request.user.support_tickets.all()
    activities = request.user.portal_activities.all()[:6]
    licenses = request.user.panel_licenses.all()

    unpaid_total = invoices.filter(status__in=['unpaid', 'overdue']).aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')
    paid_total = invoices.filter(status='paid').aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    active_service = services.filter(status='active').first()
    next_invoice = invoices.filter(status__in=['unpaid', 'overdue']).order_by('due_date').first()
    latest_ticket = tickets.first()
    service_mix = {
        'active': services.filter(status='active').count(),
        'pending': services.filter(status='pending').count(),
        'suspended': services.filter(status='suspended').count(),
    }

    context = {
        'profile': profile,
        'services': services,
        'email_services': email_services,
        'ssl_services': request.user.ssl_services.all().order_by('-created_at'),
        'suite_services': request.user.suite_services.select_related('plan', 'server').order_by('-created_at'),
        'invoices': invoices[:5],
        'tickets': tickets[:5],
        'activities': activities,
        'active_service': active_service,
        'next_invoice': next_invoice,
        'latest_ticket': latest_ticket,
        'service_mix': service_mix,
        'licenses': licenses,
        'reseller_provision_result': reseller_provision_result,
        'social_service': None,
        'marketing_service': None,
        'stats': {
            'active_services': services.filter(status='active').count(),
            'open_tickets': tickets.exclude(status='closed').count(),
            'unpaid_invoices': invoices.filter(status__in=['unpaid', 'overdue']).count(),
            'monthly_spend': services.filter(status='active').aggregate(
                total=Sum('monthly_price')
            )['total'] or Decimal('0.00'),
            'unpaid_total': unpaid_total,
            'paid_total': paid_total,
            'total_services': services.count(),
            'customer_since': profile.created_at,
        },
        'credits_per_rupee': getattr(HostingPricingSettings.objects.first(), 'credits_per_rupee', 100) or 100,
    }
    return render(request, "portal.html", context)

@login_required(login_url='/login/')
def portal_manage_wordpress(request, service_id):
    """
    Client-facing WordPress management portal.
    No full VoidPanel access — only WP install/uninstall/reset-pass + SSL.
    All actions proxied through the panel API v2.
    """
    import requests as _rq
    service = get_object_or_404(HostingService, id=service_id, user=request.user)
    if service.product_type != 'WordPress Hosting':
        return redirect(f'/portal/service/{service.id}/')

    # Get or create the WP installation record
    wp_install = getattr(service, 'wp_installation', None)

    # Fetch live status from panel API
    wp_live = None
    api_error = None
    if service.server:
        try:
            resp = _rq.get(
                f"{service.server.url.rstrip('/')}/api/v2/wordpress/status/",
                params={'domain': service.domain},
                headers={'X-API-Token': service.server.api_key},
                timeout=8,
            )
            rdata = resp.json()
            # API returns fields directly (not nested under 'data')
            if rdata.get('status') == 'success':
                wp_live = rdata   # contains installed, wp_version, wp_admin_url, ssl_active
            else:
                wp_live = rdata.get('data', rdata)
        except Exception as exc:
            api_error = str(exc)

    # Fetch SSL status
    ssl_live = None
    if service.server:
        try:
            ssl_resp = _rq.get(
                f"{service.server.url.rstrip('/')}/api/v2/ssl/status/",
                params={'domain': service.domain},
                headers={'X-API-Token': service.server.api_key},
                timeout=6,
            )
            sdata = ssl_resp.json()
            ssl_live = sdata.get('data', sdata)
        except Exception:
            pass

    # Sync wp_install record with live status if mismatch
    if wp_live and wp_live.get('installed') and wp_install and wp_install.status != 'active':
        wp_install.status = 'active'
        if not wp_install.wp_admin_url:
            wp_install.wp_admin_url = wp_live.get('wp_admin_url', f'http://{service.domain}/wp-admin/')
        wp_install.save(update_fields=['status', 'wp_admin_url'])


    ctx = {
        'service':    service,
        'wp_install': wp_install,
        'wp_live':    wp_live,
        'ssl_live':   ssl_live,
        'api_error':  api_error,
    }
    return render(request, 'portal_wordpress.html', ctx)


@login_required(login_url='/login/')
def portal_wordpress_action(request, service_id):
    """
    AJAX endpoint for WordPress management actions.
    POST body: {action: 'install'|'uninstall'|'reset_password'|'issue_ssl',
                wp_admin_email, wp_admin_password, new_password}
    Returns JSON.
    """
    import requests as _rq
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    service = get_object_or_404(HostingService, id=service_id, user=request.user)
    if service.product_type != 'WordPress Hosting':
        return JsonResponse({'status': 'error', 'message': 'Not a WordPress service'}, status=400)

    if not service.server:
        return JsonResponse({'status': 'error', 'message': 'No server assigned to this service'}, status=400)

    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST.dict()

    action = body.get('action', '').strip()
    api_base = service.server.url.rstrip('/')
    api_key  = service.server.api_key
    headers  = {'X-API-Token': api_key, 'Content-Type': 'application/json'}

    def _call(method, endpoint, payload=None, timeout=120):
        """Make an API call and return (data_dict, error_message)."""
        try:
            fn = _rq.post if method == 'POST' else _rq.get
            kwargs = {'headers': headers, 'timeout': timeout}
            if payload is not None:
                kwargs['json'] = payload
            resp = fn(f'{api_base}{endpoint}', **kwargs)
            data = resp.json()
            # Detect scope errors and give clear message
            if resp.status_code == 403 and 'missing required scope' in data.get('message', '').lower():
                scope = data['message'].split('scope:')[-1].strip() if 'scope:' in data['message'] else 'unknown'
                return None, (
                    f'The API token on the hosting server does not have the "{scope}" permission. '
                    f'Please go to VoidPanel → API Tokens and add the WordPress scopes to the token used by voidpanel.com.'
                )
            return data, None
        except _rq.exceptions.ConnectionError:
            return None, f'Cannot connect to server at {api_base}. Check server is online.'
        except _rq.exceptions.Timeout:
            return None, 'Request timed out. The server may be busy — try again in a moment.'
        except Exception as exc:
            return None, str(exc)

    # ── Install WordPress ─────────────────────────────────────────────
    if action == 'install':
        wp_email = body.get('wp_admin_email', service.user.email).strip()
        wp_pass  = body.get('wp_admin_password', '').strip()
        wp_user  = body.get('wp_admin_user', 'admin').strip()
        if not wp_pass:
            return JsonResponse({'status': 'error', 'message': 'WordPress admin password is required'}, status=400)
        try:
            resp = _rq.post(
                f'{api_base}/api/v2/wordpress/install/',
                json={'domain': service.domain, 'wp_admin_user': wp_user,
                      'wp_admin_email': wp_email, 'wp_admin_password': wp_pass,
                      'site_title': service.domain},
                headers=headers, timeout=180,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            from django.utils import timezone
            wp, _ = WordPressInstallation.objects.get_or_create(service=service)
            wp.status        = 'active'
            wp.wp_admin_user  = wp_user
            wp.wp_admin_email = wp_email
            wp.wp_admin_url   = data.get('data', {}).get('wp_admin_url', f'http://{service.domain}/wp-admin/')
            wp.installed_at   = timezone.now()
            wp.uninstalled_at = None
            wp.save()
            PortalActivity.objects.create(
                user=request.user, category='account',
                title=f'WordPress installed: {service.domain}',
                description=f'Admin: {wp_user}',
            )
            return JsonResponse({'status': 'success', 'message': 'WordPress installed successfully!',
                                 'wp_admin_url': wp.wp_admin_url})
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Install failed')}, status=400)

    # ── Uninstall WordPress ────────────────────────────────────────
    elif action == 'uninstall':
        try:
            resp = _rq.post(
                f'{api_base}/api/v2/wordpress/uninstall/',
                json={'domain': service.domain},
                headers=headers, timeout=60,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            from django.utils import timezone
            wp = getattr(service, 'wp_installation', None)
            if wp:
                wp.status = 'uninstalled'
                wp.uninstalled_at = timezone.now()
                wp.save(update_fields=['status', 'uninstalled_at'])
            PortalActivity.objects.create(
                user=request.user, category='account',
                title=f'WordPress uninstalled: {service.domain}',
                description='WordPress files and database removed.',
            )
            return JsonResponse({'status': 'success', 'message': 'WordPress has been uninstalled.'})
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Uninstall failed')}, status=400)

    # ── Reset WP Admin Password ───────────────────────────────────
    elif action == 'reset_password':
        new_pass = body.get('new_password', '').strip()
        wp_user  = body.get('wp_admin_user', 'admin').strip()
        if not new_pass or len(new_pass) < 8:
            return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters'}, status=400)
        try:
            resp = _rq.post(
                f'{api_base}/api/v2/wordpress/reset-password/',
                json={'domain': service.domain, 'new_password': new_pass, 'wp_admin_user': wp_user},
                headers=headers, timeout=30,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            PortalActivity.objects.create(
                user=request.user, category='account',
                title=f'WordPress password reset: {service.domain}',
                description='Admin password changed via client portal.',
            )
            return JsonResponse({'status': 'success', 'message': 'WordPress admin password updated!'})
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Password reset failed')}, status=400)

    # ── Issue / Renew SSL ────────────────────────────────────────────
    elif action == 'issue_ssl':
        try:
            resp = _rq.post(
                f'{api_base}/api/v2/ssl/issue/',
                json={'domain': service.domain},
                headers=headers, timeout=60,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            # Update SSL status in WP record
            wp = getattr(service, 'wp_installation', None)
            if wp:
                wp.ssl_status = 'active'
                wp.save(update_fields=['ssl_status'])
            PortalActivity.objects.create(
                user=request.user, category='account',
                title=f'SSL issued: {service.domain}',
                description='Let\'s Encrypt SSL certificate issued via client portal.',
            )
            return JsonResponse({'status': 'success', 'message': 'SSL certificate issued! It may take 1-2 minutes to become active.'})
        return JsonResponse({'status': 'error', 'message': data.get('message', 'SSL issuance failed')}, status=400)

    return JsonResponse({'status': 'error', 'message': f'Unknown action: {action}'}, status=400)

def get_voidpanel(request):
    """Public landing + license self-issue page at /get-voidpanel/."""
    from django.utils import timezone as _tz
    import datetime

    user_licenses = None
    if request.user.is_authenticated:
        user_licenses = request.user.panel_licenses.all()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to issue a license.')
            return redirect('/login/?next=/get-voidpanel/')
        action = request.POST.get('action')
        if action == 'issue_license':
            hostname = request.POST.get('hostname', '').strip()
            new_key = secrets.token_hex(32)
            # New users get a FREE 30-day Unlimited trial — no credit card needed
            is_first_license = not PanelLicenseRecord.objects.filter(user=request.user).exists()
            trial_expires = _tz.now() + datetime.timedelta(days=30) if is_first_license else None
            PanelLicenseRecord.objects.create(
                user=request.user,
                key=new_key,
                hostname=hostname,
                server_ip=None,
                status='active',
                tier=PanelLicenseRecord.TIER_UNLIMITED if is_first_license else PanelLicenseRecord.TIER_STARTER,
                is_trial=is_first_license,
                expires_at=trial_expires,
            )
            PortalActivity.objects.create(
                user=request.user,
                category='account',
                title='VoidPanel license issued',
                description=f'A new {"Unlimited trial" if is_first_license else "Starter"} license key was generated. Hostname: {hostname or "Not specified"}.'
            )
            if is_first_license:
                messages.success(request, '\U0001f389 Your FREE 30-day Unlimited trial license has been issued! Enjoy all features.')
            else:
                messages.success(request, 'Your license key has been issued! Copy it and use it during the installation wizard.')
            return redirect('/get-voidpanel/')

    razorpay_active = RazorpayConfig.objects.filter(pk=1, is_active=True).exists()
    return render(request, 'get_voidpanel.html', {
        'user_licenses': user_licenses,
        'razorpay_active': razorpay_active,
    })


@login_required(login_url='/login/')
def license_subscribe(request):
    """
    GET  /license/subscribe/?tier=pro|advanced|unlimited
    Shows a checkout page for the selected tier with Razorpay payment.
    """
    TIER_PRICES = {
        PanelLicenseRecord.TIER_PRO:       999,
        PanelLicenseRecord.TIER_ADVANCED:  2499,
        PanelLicenseRecord.TIER_UNLIMITED: 4999,
    }
    TIER_LABELS = {
        PanelLicenseRecord.TIER_PRO:       'Pro',
        PanelLicenseRecord.TIER_ADVANCED:  'Advanced',
        PanelLicenseRecord.TIER_UNLIMITED: 'Unlimited',
    }

    tier = request.GET.get('tier', 'pro').lower()
    if tier not in TIER_PRICES:
        tier = 'pro'

    rzp_config = RazorpayConfig.get()
    kid, _ = rzp_config.get_active_keys() if rzp_config.is_ready else (None, None)

    context = {
        'tier': tier,
        'tier_label': TIER_LABELS[tier],
        'price': TIER_PRICES[tier],
        'tier_prices': TIER_PRICES,
        'tier_labels': TIER_LABELS,
        'razorpay_key_id': kid,
        'razorpay_active': rzp_config.is_ready,
    }
    return render(request, 'license_subscribe.html', context)


@login_required(login_url='/login/')
def api_license_create_order(request):
    """
    POST /api/license/create-order/
    Body: {
        "tier":        "pro"|"advanced"|"unlimited",
        "hostname":    "panel.example.com",   (optional)
        "promo_code":  "LAUNCH20",            (optional)
        "final_amount": 799                   (client hint — server ignores and recalculates)
    }
    Server validates promo independently and creates a Razorpay order for the correct amount.
    Returns: { "order_id", "amount" (paise), "currency", "key_id", "tier", "prefill", "discount_inr", "final_inr" }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    TIER_PRICES = {
        PanelLicenseRecord.TIER_PRO:       999,
        PanelLicenseRecord.TIER_ADVANCED:  2499,
        PanelLicenseRecord.TIER_UNLIMITED: 4999,
    }

    try:
        data = _rjson.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    tier = data.get('tier', 'pro').lower()
    hostname   = data.get('hostname', '').strip()
    promo_code = data.get('promo_code', '').strip().upper()

    if tier not in TIER_PRICES:
        return JsonResponse({'error': 'Invalid tier'}, status=400)

    rzp_config = RazorpayConfig.get()
    if not rzp_config.is_ready:
        return JsonResponse({'error': 'Payment gateway not configured'}, status=503)

    base_inr = TIER_PRICES[tier]

    # ── Server-side promo validation ────────────────────────────────────────
    discount_inr = 0
    coupon_obj   = None
    if promo_code:
        coupon_obj = Coupon.objects.filter(code=promo_code).first()
        if coupon_obj and coupon_obj.is_valid(billing_cycle='monthly'):
            if coupon_obj.discount_type == 'percentage':
                discount_inr = round(base_inr * float(coupon_obj.discount_value) / 100)
            else:
                discount_inr = min(int(coupon_obj.discount_value), base_inr)
        else:
            coupon_obj = None  # invalid — treat as no promo

    final_inr   = max(1, base_inr - discount_inr)   # minimum ₹1 to avoid Razorpay 0-amount error
    amount_paise = final_inr * 100

    kid, ksecret = rzp_config.get_active_keys()
    try:
        try:
            import razorpay
        except ImportError:
            return JsonResponse({'error': 'Razorpay module not installed'}, status=503)

        client = razorpay.Client(auth=(kid, ksecret))
        receipt = f'lic_{request.user.id}_{tier}'[:40]
        rz_order = client.order.create({
            'amount':          amount_paise,
            'currency':        'INR',
            'receipt':         receipt,
            'payment_capture': 1,
            'notes': {
                'user_id':     str(request.user.id),
                'email':       request.user.email,
                'tier':        tier,
                'hostname':    hostname,
                'promo_code':  promo_code or '',
                'discount':    str(discount_inr),
                'type':        'license_subscription',
            }
        })
    except Exception as exc:
        return JsonResponse({'error': f'Razorpay error: {str(exc)[:160]}'}, status=502)

    # Store full intent in session for verify endpoint
    request.session['license_order_intent'] = {
        'rz_order_id':  rz_order['id'],
        'tier':         tier,
        'hostname':     hostname,
        'base_inr':     base_inr,
        'discount_inr': discount_inr,
        'final_inr':    final_inr,
        'promo_code':   promo_code,
        'coupon_id':    coupon_obj.pk if coupon_obj else None,
    }

    try:
        profile = CustomerProfile.objects.filter(user=request.user).first()
        user_phone = (profile.phone.strip() if profile and profile.phone else '') or '9999999999'
    except Exception:
        user_phone = '9999999999'

    return JsonResponse({
        'order_id':    rz_order['id'],
        'amount':      amount_paise,
        'currency':    'INR',
        'key_id':      kid,
        'tier':        tier,
        'base_inr':    base_inr,
        'discount_inr': discount_inr,
        'final_inr':   final_inr,
        'prefill': {
            'name':    request.user.get_full_name() or request.user.username,
            'email':   request.user.email,
            'contact': user_phone,
        },
    })


@login_required(login_url='/login/')
def api_license_verify_order(request):
    """
    POST /api/license/verify-order/
    Body: { "razorpay_order_id": "...", "razorpay_payment_id": "...", "razorpay_signature": "..." }
    On success: issues the license key for the purchased tier.
    """
    import hashlib, hmac as _hmac
    from django.utils import timezone as _tz
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    rzp_config = RazorpayConfig.get()
    _, ksecret = rzp_config.get_active_keys()
    if not ksecret:
        return JsonResponse({'error': 'Gateway not configured'}, status=503)

    try:
        data = _rjson.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid body'}, status=400)

    rz_order_id   = data.get('razorpay_order_id', '')
    rz_payment_id = data.get('razorpay_payment_id', '')
    rz_signature  = data.get('razorpay_signature', '')

    # HMAC-SHA256 verification
    msg = f"{rz_order_id}|{rz_payment_id}"
    expected = _hmac.new(ksecret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not _hmac.compare_digest(expected, rz_signature):
        return JsonResponse({'error': 'Payment verification failed — invalid signature'}, status=400)

    # Pull intent from session
    intent = request.session.pop('license_order_intent', {})
    tier     = intent.get('tier', 'pro')
    hostname = intent.get('hostname', '')

    TIER_PRICES = {
        PanelLicenseRecord.TIER_PRO:       999,
        PanelLicenseRecord.TIER_ADVANCED:  2499,
        PanelLicenseRecord.TIER_UNLIMITED: 4999,
    }
    if tier not in TIER_PRICES:
        tier = 'pro'

    # Issue the license
    new_key = secrets.token_hex(32)
    lic = PanelLicenseRecord.objects.create(
        user=request.user,
        key=new_key,
        hostname=hostname,
        server_ip=None,
        status='active',
        tier=tier,
        is_trial=False,
        expires_at=_tz.now() + __import__('datetime').timedelta(days=30),
    )

    PortalActivity.objects.create(
        user=request.user,
        category='billing',
        title=f'VoidPanel {tier.title()} license purchased',
        description=f'License key issued after successful Razorpay payment {rz_payment_id}. Hostname: {hostname or "Not specified"}.',
    )

    return JsonResponse({
        'status':      'ok',
        'license_id':  lic.id,
        'key_preview': lic.key[:20] + '...',
        'tier':        tier,
        'redirect':    f'/portal/license/{lic.id}/',
    })


@login_required(login_url='/login/')
def portal_license_detail(request, license_id):
    """Client portal: detailed view of a single license."""
    try:
        license = request.user.panel_licenses.get(id=license_id)
    except PanelLicenseRecord.DoesNotExist:
        messages.error(request, 'License not found.')
        return redirect('/portal/')
    return render(request, 'license_detail.html', {'license': license})


@login_required(login_url='/login/')
def super_admin_portal(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        handled = _handle_super_admin_post(request)
        if handled:
            return handled
    context = _build_super_admin_context('dashboard')
    return render(request, 'super_admin_dashboard.html', context)


def _super_admin_guard(request):
    if not request.user.is_superuser:
        messages.error(request, "Super admin access is required")
        return redirect('/portal/')
    return None


def _super_admin_redirect(request, fallback):
    target = request.POST.get('next') or request.META.get('HTTP_REFERER') or fallback
    return redirect(target)


def _handle_super_admin_post(request):
    action = request.POST.get('action')

    if action == 'create_role':
        role_name = request.POST.get('role_name', '').strip()
        description = request.POST.get('description', '').strip()
        if not role_name:
            messages.error(request, "Role name is required")
            return _super_admin_redirect(request, '/super-admin/roles/')
        slug = slugify(role_name)
        if StaffRole.objects.filter(slug=slug).exists():
            messages.error(request, "A role with that name already exists")
            return _super_admin_redirect(request, '/super-admin/roles/')
        StaffRole.objects.create(
            name=role_name,
            slug=slug,
            description=description,
            can_manage_clients=bool(request.POST.get('can_manage_clients')),
            can_manage_billing=bool(request.POST.get('can_manage_billing')),
            can_manage_support=bool(request.POST.get('can_manage_support')),
            can_manage_infrastructure=bool(request.POST.get('can_manage_infrastructure')),
            can_manage_staff=bool(request.POST.get('can_manage_staff')),
        )
        messages.success(request, "Staff role created")
        return _super_admin_redirect(request, '/super-admin/roles/')

    if action == 'create_staff':
        name = request.POST.get('staff_name', '').strip()
        email = request.POST.get('staff_email', '').strip().lower()
        password = request.POST.get('staff_password', '')
        role_id = request.POST.get('role_id')
        department = request.POST.get('department', '').strip()
        is_super_admin = bool(request.POST.get('is_super_admin'))
        if not name or not email or not password:
            messages.error(request, "Name, email, and password are required for new staff")
            return _super_admin_redirect(request, '/super-admin/staff/')
        if User.objects.filter(email=email).exists():
            messages.error(request, "That email is already in use")
            return _super_admin_redirect(request, '/super-admin/staff/')
        try:
            validate_password(password)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return _super_admin_redirect(request, '/super-admin/staff/')

        role = StaffRole.objects.filter(id=role_id).first()
        first_name, _, last_name = name.partition(' ')
        username = _generate_username_from_email(email)
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name.strip(),
                is_staff=True,
                is_superuser=is_super_admin,
            )
            ensure_portal_seed_data(user, profile_defaults={'country': 'IN'})
            _ensure_staff_profile(
                user,
                role=role,
                is_portal_admin=True,
                display_title=role.name if role else 'Staff Member',
                department=department,
            )
            PortalActivity.objects.create(
                user=user,
                category='account',
                title='Staff access provisioned',
                description='This account was promoted into the internal operations portal.',
            )
        messages.success(request, "Staff account created")
        return _super_admin_redirect(request, '/super-admin/staff/')

    if action == 'update_staff':
        user_id = request.POST.get('user_id')
        role_id = request.POST.get('role_id')
        department = request.POST.get('department', '').strip()
        title = request.POST.get('display_title', '').strip()
        user = User.objects.filter(id=user_id).first()
        role = StaffRole.objects.filter(id=role_id).first()
        if not user:
            messages.error(request, "Staff member not found")
            return _super_admin_redirect(request, '/super-admin/staff/')
        user.is_staff = bool(request.POST.get('is_staff'))
        user.is_superuser = bool(request.POST.get('is_superuser'))
        user.save(update_fields=['is_staff', 'is_superuser'])
        _ensure_staff_profile(
            user,
            role=role,
            is_portal_admin=bool(request.POST.get('is_portal_admin')),
            department=department,
            display_title=title or (role.name if role else 'Staff Member'),
        )
        messages.success(request, f"Updated access for {user.get_full_name() or user.username}")
        return _super_admin_redirect(request, '/super-admin/staff/')

    if action == 'create_email_profile':
        profile_name = request.POST.get('profile_name', '').strip()
        from_email = request.POST.get('from_email', '').strip()
        smtp_host = request.POST.get('smtp_host', '').strip()
        smtp_port = request.POST.get('smtp_port', '').strip() or '587'
        if not profile_name or not from_email or not smtp_host:
            messages.error(request, "Profile name, sender email, and SMTP host are required")
            return _super_admin_redirect(request, '/super-admin/emails/')
        should_be_default = bool(request.POST.get('is_default'))
        if should_be_default:
            OutboundEmailProfile.objects.update(is_default=False)
        email_profile = OutboundEmailProfile.objects.create(
            profile_name=profile_name,
            purpose_category=request.POST.get('purpose_category', 'transactional'),
            from_name=request.POST.get('from_name', '').strip(),
            from_email=from_email,
            reply_to_email=request.POST.get('reply_to_email', '').strip(),
            smtp_host=smtp_host,
            smtp_port=int(smtp_port),
            smtp_username=request.POST.get('smtp_username', '').strip(),
            smtp_password=request.POST.get('smtp_password', ''),
            use_tls=bool(request.POST.get('use_tls')),
            use_ssl=bool(request.POST.get('use_ssl')),
            is_active=bool(request.POST.get('is_active')),
            is_default=should_be_default or not OutboundEmailProfile.objects.exists(),
            **{field: bool(request.POST.get(field)) for field, _ in EMAIL_EVENT_FIELDS},
        )
        if not OutboundEmailProfile.objects.exclude(id=email_profile.id).exists():
            email_profile.is_default = True
            email_profile.save(update_fields=['is_default'])
        messages.success(request, "Email profile created")
        return _super_admin_redirect(request, '/super-admin/emails/')

    if action == 'edit_email_profile':
        profile_id = request.POST.get('profile_id')
        profile = OutboundEmailProfile.objects.filter(id=profile_id).first()
        if not profile:
            messages.error(request, "Email profile not found")
            return _super_admin_redirect(request, '/super-admin/emails/')
        profile_name = request.POST.get('profile_name', '').strip()
        from_email = request.POST.get('from_email', '').strip()
        smtp_host = request.POST.get('smtp_host', '').strip()
        smtp_port = request.POST.get('smtp_port', '').strip() or '587'
        if not profile_name or not from_email or not smtp_host:
            messages.error(request, "Profile name, sender email, and SMTP host are required")
            return _super_admin_redirect(request, '/super-admin/emails/')
        profile.profile_name = profile_name
        profile.purpose_category = request.POST.get('purpose_category', 'transactional')
        profile.from_name = request.POST.get('from_name', '').strip()
        profile.from_email = from_email
        profile.reply_to_email = request.POST.get('reply_to_email', '').strip()
        profile.smtp_host = smtp_host
        profile.smtp_port = int(smtp_port)
        profile.smtp_username = request.POST.get('smtp_username', '').strip()
        password = request.POST.get('smtp_password', '')
        if password:
            profile.smtp_password = password
        profile.use_tls = bool(request.POST.get('use_tls'))
        profile.use_ssl = bool(request.POST.get('use_ssl'))
        profile.is_active = bool(request.POST.get('is_active'))
        should_be_default = bool(request.POST.get('is_default'))
        if should_be_default:
            OutboundEmailProfile.objects.exclude(id=profile.id).update(is_default=False)
            profile.is_default = True
        for field, _ in EMAIL_EVENT_FIELDS:
            setattr(profile, field, bool(request.POST.get(field)))
        profile.save()
        messages.success(request, f"Email profile '{profile.profile_name}' updated successfully")
        return _super_admin_redirect(request, '/super-admin/emails/')

    if action == 'email_profile_action':
        profile = OutboundEmailProfile.objects.filter(id=request.POST.get('profile_id')).first()
        mode = request.POST.get('mode')
        if not profile:
            messages.error(request, "Email profile not found")
            return _super_admin_redirect(request, '/super-admin/emails/')
        if mode == 'make_default':
            OutboundEmailProfile.objects.update(is_default=False)
            profile.is_default = True
            profile.save(update_fields=['is_default'])
            messages.success(request, f"{profile.profile_name} is now the default email profile")
            return _super_admin_redirect(request, '/super-admin/emails/')
        if mode == 'toggle_active':
            profile.is_active = not profile.is_active
            profile.save(update_fields=['is_active'])
            messages.success(request, f"{profile.profile_name} was {'activated' if profile.is_active else 'paused'}")
            return _super_admin_redirect(request, '/super-admin/emails/')
        if mode == 'delete':
            name = profile.profile_name
            profile.delete()
            if not OutboundEmailProfile.objects.filter(is_default=True).exists():
                next_p = OutboundEmailProfile.objects.first()
                if next_p:
                    next_p.is_default = True
                    next_p.save(update_fields=['is_default'])
            messages.success(request, f"Email profile '{name}' was deleted")
            return _super_admin_redirect(request, '/super-admin/emails/')
        if mode == 'test_connection':
            try:
                _test_email_profile_connection(profile)
                messages.success(request, f"SMTP test connection succeeded for {profile.profile_name}")
            except Exception as exc:
                messages.error(request, f"SMTP test failed for {profile.profile_name}: {exc}")
            return _super_admin_redirect(request, '/super-admin/emails/')

    if action in ['create_hosting_package', 'create_reseller_package', 'toggle_reseller_package', 'toggle_hosting_package', 'edit_hosting_package']:
        from data.models import HostingPackageOverride, _STATIC_HOSTING_PACKAGES

        def int_or_none(val):
            val = str(val or '').strip()
            return int(val) if val.isdigit() else None

        def decimal_or_none(val):
            val = str(val or '').strip()
            try:
                return Decimal(val)
            except Exception:
                return None

        if action == 'edit_hosting_package':
            package_id = int_or_none(request.POST.get('package_id'))
            if package_id is None:
                messages.error(request, "Package ID is missing")
                return _super_admin_redirect(request, '/super-admin/hosting/')
            
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip()
            package_type = request.POST.get('package_type', '').strip()
            short_description = request.POST.get('short_description', '').strip()
            monthly_price = decimal_or_none(request.POST.get('monthly_price'))
            storage_gb = int_or_none(request.POST.get('storage_gb'))
            ram_gb = int_or_none(request.POST.get('ram_gb'))
            cpu_cores = int_or_none(request.POST.get('cpu_cores'))
            bandwidth_label = request.POST.get('bandwidth_label', '').strip()
            allowed_domains = int_or_none(request.POST.get('allowed_domains'))
            sort_order = int_or_none(request.POST.get('sort_order'))
            server_id = int_or_none(request.POST.get('server_id'))
            is_featured = bool(request.POST.get('is_featured') or request.POST.get('is_featured') == 'true')
            is_active = bool(request.POST.get('is_active') or request.POST.get('is_active') == 'true')
            has_email_marketing = bool(request.POST.get('has_email_marketing') or request.POST.get('has_email_marketing') == 'true')
            has_whatsapp_marketing = bool(request.POST.get('has_whatsapp_marketing') or request.POST.get('has_whatsapp_marketing') == 'true')
            has_automation = bool(request.POST.get('has_automation') or request.POST.get('has_automation') == 'true')
            has_analytics = bool(request.POST.get('has_analytics') or request.POST.get('has_analytics') == 'true')
            has_seo_crm = bool(request.POST.get('has_seo_crm') or request.POST.get('has_seo_crm') == 'true')

            # Update or create override
            HostingPackageOverride.objects.update_or_create(
                package_id=package_id,
                defaults={
                    'name': name,
                    'slug': slug,
                    'package_type': package_type,
                    'short_description': short_description,
                    'monthly_price': monthly_price,
                    'storage_gb': storage_gb,
                    'ram_gb': ram_gb,
                    'cpu_cores': cpu_cores,
                    'bandwidth_label': bandwidth_label,
                    'allowed_domains': allowed_domains,
                    'sort_order': sort_order,
                    'server_id': server_id,
                    'is_featured': is_featured,
                    'is_active': is_active,
                    'has_email_marketing': has_email_marketing,
                    'has_whatsapp_marketing': has_whatsapp_marketing,
                    'has_automation': has_automation,
                    'has_analytics': has_analytics,
                    'has_seo_crm': has_seo_crm,
                }
            )
            messages.success(request, f"Hosting package '{name}' updated successfully!")
            return _super_admin_redirect(request, '/super-admin/hosting/')

        elif action in ['create_hosting_package', 'create_reseller_package']:
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip()
            package_type = request.POST.get('package_type', 'shared').strip()
            short_description = request.POST.get('short_description', '').strip()
            monthly_price = decimal_or_none(request.POST.get('monthly_price'))
            storage_gb = int_or_none(request.POST.get('storage_gb'))
            ram_gb = int_or_none(request.POST.get('ram_gb'))
            cpu_cores = int_or_none(request.POST.get('cpu_cores'))
            bandwidth_label = request.POST.get('bandwidth_label', '').strip()
            allowed_domains = int_or_none(request.POST.get('allowed_domains'))
            sort_order = int_or_none(request.POST.get('sort_order'))
            server_id = int_or_none(request.POST.get('server_id'))
            is_featured = bool(request.POST.get('is_featured') or request.POST.get('is_featured') == 'true')
            is_active = bool(request.POST.get('is_active') or request.POST.get('is_active') == 'true')
            has_email_marketing = bool(request.POST.get('has_email_marketing') or request.POST.get('has_email_marketing') == 'true')
            has_whatsapp_marketing = bool(request.POST.get('has_whatsapp_marketing') or request.POST.get('has_whatsapp_marketing') == 'true')
            has_automation = bool(request.POST.get('has_automation') or request.POST.get('has_automation') == 'true')
            has_analytics = bool(request.POST.get('has_analytics') or request.POST.get('has_analytics') == 'true')
            has_seo_crm = bool(request.POST.get('has_seo_crm') or request.POST.get('has_seo_crm') == 'true')

            if not name:
                messages.error(request, "Package name is required")
                return _super_admin_redirect(request, '/super-admin/hosting/')

            if not slug:
                slug = slugify(name)

            max_id = max(list(_STATIC_HOSTING_PACKAGES.keys()) + [9])
            db_max = HostingPackageOverride.objects.aggregate(max_id=models.Max('package_id'))['max_id']
            if db_max:
                max_id = max(max_id, db_max)
            new_id = max_id + 1

            HostingPackageOverride.objects.create(
                package_id=new_id,
                name=name,
                slug=slug,
                package_type=package_type,
                short_description=short_description,
                monthly_price=monthly_price,
                storage_gb=storage_gb,
                ram_gb=ram_gb,
                cpu_cores=cpu_cores,
                bandwidth_label=bandwidth_label,
                allowed_domains=allowed_domains,
                sort_order=sort_order,
                server_id=server_id,
                is_featured=is_featured,
                is_active=is_active,
                has_email_marketing=has_email_marketing,
                has_whatsapp_marketing=has_whatsapp_marketing,
                has_automation=has_automation,
                has_analytics=has_analytics,
                has_seo_crm=has_seo_crm,
            )
            messages.success(request, f"Hosting package '{name}' created successfully!")
            return _super_admin_redirect(request, '/super-admin/hosting/')

        elif action in ['toggle_hosting_package', 'toggle_reseller_package']:
            package_id = int_or_none(request.POST.get('package_id'))
            mode = request.POST.get('mode')
            if package_id is None:
                messages.error(request, "Package ID is missing")
                return _super_admin_redirect(request, '/super-admin/hosting/')

            is_default = (package_id in _STATIC_HOSTING_PACKAGES)

            if mode == 'delete':
                if is_default:
                    ov, _ = HostingPackageOverride.objects.get_or_create(package_id=package_id)
                    ov.is_active = False
                    ov.save()
                    messages.success(request, "Default hosting package deactivated.")
                else:
                    HostingPackageOverride.objects.filter(package_id=package_id).delete()
                    messages.success(request, "Hosting package deleted successfully.")
            elif mode == 'activate':
                ov, _ = HostingPackageOverride.objects.get_or_create(package_id=package_id)
                ov.is_active = True
                ov.save()
                messages.success(request, "Hosting package activated.")
            elif mode == 'deactivate':
                ov, _ = HostingPackageOverride.objects.get_or_create(package_id=package_id)
                ov.is_active = False
                ov.save()
                messages.success(request, "Hosting package deactivated.")

            return _super_admin_redirect(request, '/super-admin/hosting/')


    if action == 'create_server':
        name    = request.POST.get('name', '').strip()
        url     = request.POST.get('url', '').strip().rstrip('/')
        api_key = request.POST.get('api_key', '').strip()
        if VoidPanelServer.objects.filter(name=name).exists():
            messages.error(request, "A server with that name already exists.")
            return _super_admin_redirect(request, '/super-admin/servers/')
        if not url or not api_key:
            messages.error(request, "URL and API key are required.")
            return _super_admin_redirect(request, '/super-admin/servers/')
        # Verify connectivity server-side as a safety net
        import requests as _req, time as _t
        start = _t.time()
        version = ''
        latency = None
        try:
            ping = _req.get(
                f'{url}/api/license/validate/',
                headers={'X-VoidPanel-Key': api_key},
                timeout=10,
            )
            latency = int((_t.time() - start) * 1000)
            if ping.status_code == 200:
                try: version = ping.json().get('version', '')
                except: version = ''
            elif ping.status_code == 403:
                messages.error(request, f"Server API key was rejected (403). Please double-check the API key for {url}.")
                return _super_admin_redirect(request, '/super-admin/servers/')
            else:
                messages.error(request, f"Server responded with HTTP {ping.status_code}. Check the URL and ensure the VoidPanel backend is running.")
                return _super_admin_redirect(request, '/super-admin/servers/')
        except _req.exceptions.ConnectionError:
            messages.error(request, f"Could not connect to {url}. Check the URL and ensure VoidPanel is running on that server.")
            return _super_admin_redirect(request, '/super-admin/servers/')
        except _req.exceptions.Timeout:
            messages.error(request, f"Connection to {url} timed out after 10 seconds.")
            return _super_admin_redirect(request, '/super-admin/servers/')
        except Exception as exc:
            messages.error(request, f"Unexpected error connecting to server: {exc}")
            return _super_admin_redirect(request, '/super-admin/servers/')

        VoidPanelServer.objects.create(
            name=name, url=url, api_key=api_key,
            is_active=bool(request.POST.get('is_active')),
            login_url=request.POST.get('login_url', '').strip(),
            nameservers=request.POST.get('nameservers', '').strip(),
            server_version=version,
            last_ping_latency_ms=latency,
            last_connected=timezone.now(),
        )
        messages.success(request, f"Server '{name}' connected successfully! Version: {version or 'unknown'} · Latency: {latency}ms")
        return _super_admin_redirect(request, '/super-admin/servers/')

    if action == 'delete_server':
        server_id = request.POST.get('server_id')
        server = VoidPanelServer.objects.filter(id=server_id).first()
        if server:
            server.delete()
            messages.success(request, "Server deleted successfully.")
        return _super_admin_redirect(request, '/super-admin/servers/')

    if action == 'edit_server':
        import requests as _req, time as _t
        server_id = request.POST.get('server_id')
        server = VoidPanelServer.objects.filter(id=server_id).first()
        if not server:
            messages.error(request, 'Server not found.')
            return _super_admin_redirect(request, '/super-admin/servers/')
        new_name    = request.POST.get('name', server.name).strip()
        new_url     = request.POST.get('url', server.url).strip().rstrip('/')
        new_key     = request.POST.get('api_key', '').strip()
        if not new_key:
            new_key = server.api_key  # keep existing key if field left blank
        new_active  = bool(request.POST.get('is_active'))
        # If name conflicts with another server, reject
        if VoidPanelServer.objects.filter(name=new_name).exclude(id=server_id).exists():
            messages.error(request, f'Another server named "{new_name}" already exists.')
            return _super_admin_redirect(request, '/super-admin/servers/')
        # Re-ping to update latency/version
        latency = server.last_ping_latency_ms
        version = server.server_version
        try:
            start = _t.time()
            ping = _req.get(
                f'{new_url}/api/license/validate/',
                headers={'X-VoidPanel-Key': new_key},
                timeout=10,
            )
            latency = int((_t.time() - start) * 1000)
            if ping.status_code == 200:
                try: version = ping.json().get('version', version)
                except: pass
            elif ping.status_code == 403:
                messages.error(request, 'API key was rejected (403) by the server. Server not updated.')
                return _super_admin_redirect(request, '/super-admin/servers/')
            else:
                messages.warning(request, f'Server responded with HTTP {ping.status_code} — saved anyway with previous stats.')
        except Exception as exc:
            messages.warning(request, f'Could not reach server ({exc}) — saved with previous stats.')
        server.name                = new_name
        server.url                 = new_url
        server.api_key             = new_key
        server.is_active           = new_active
        server.login_url           = request.POST.get('login_url', '').strip()
        server.nameservers         = request.POST.get('nameservers', '').strip()
        server.last_ping_latency_ms= latency
        server.server_version      = version
        server.last_connected      = timezone.now()
        server.save()
        messages.success(request, f"Server '{new_name}' updated. Latency: {latency}ms · Version: {version or 'unknown'}")
        return _super_admin_redirect(request, '/super-admin/servers/')

    if action == 'update_pricing_settings':
        settings_obj = ensure_default_hosting_catalog()
        # Shared hosting builder fields
        settings_obj.storage_price_per_10gb = Decimal(request.POST.get('storage_price_per_10gb') or '1.50')
        settings_obj.bandwidth_price_per_100gb = Decimal(request.POST.get('bandwidth_price_per_100gb') or '5.00')
        settings_obj.shared_max_emails = int(request.POST.get('shared_max_emails') or 10)
        settings_obj.shared_max_ftp = int(request.POST.get('shared_max_ftp') or 5)
        settings_obj.shared_max_databases = int(request.POST.get('shared_max_databases') or 5)
        settings_obj.storage_min_gb = int(request.POST.get('storage_min_gb') or 10)
        settings_obj.storage_max_gb = int(request.POST.get('storage_max_gb') or 500)
        settings_obj.bandwidth_min_gb = int(request.POST.get('bandwidth_min_gb') or 10)
        settings_obj.bandwidth_max_gb = int(request.POST.get('bandwidth_max_gb') or 1000)
        # Legacy VPS fields — preserved as-is from hidden form inputs
        settings_obj.ram_price_per_1gb = Decimal(request.POST.get('ram_price_per_1gb') or '4.00')
        settings_obj.cpu_price_per_core = Decimal(request.POST.get('cpu_price_per_core') or '8.00')
        settings_obj.bandwidth_100gb_price = Decimal(request.POST.get('bandwidth_100gb_price') or '5.00')
        settings_obj.bandwidth_500gb_price = Decimal(request.POST.get('bandwidth_500gb_price') or '12.00')
        settings_obj.bandwidth_1000gb_price = Decimal(request.POST.get('bandwidth_1000gb_price') or '20.00')
        settings_obj.bandwidth_unmetered_price = Decimal(request.POST.get('bandwidth_unmetered_price') or '35.00')
        settings_obj.ram_min_gb = int(request.POST.get('ram_min_gb') or 1)
        settings_obj.ram_max_gb = int(request.POST.get('ram_max_gb') or 32)
        settings_obj.cpu_min_cores = int(request.POST.get('cpu_min_cores') or 1)
        settings_obj.cpu_max_cores = int(request.POST.get('cpu_max_cores') or 16)
        settings_obj.quarterly_discount_percent = int(request.POST.get('quarterly_discount_percent') or 0)
        settings_obj.annual_discount_percent = int(request.POST.get('annual_discount_percent') or 10)
        settings_obj.save()
        messages.success(request, "Builder pricing settings updated")
        return _super_admin_redirect(request, '/super-admin/hosting/')
    return None


def _build_super_admin_context(active_page):
    ensure_default_staff_roles()
    pricing_settings = ensure_default_hosting_catalog()
    _ensure_staff_profile(
        User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first(),
        role=StaffRole.objects.filter(can_manage_staff=True).first(),
        is_portal_admin=True,
        display_title='Super Administrator',
        department='Executive',
    )
    staff_users = User.objects.filter(is_staff=True).order_by('first_name', 'username')
    for user in staff_users:
        _ensure_staff_profile(user, is_portal_admin=getattr(getattr(user, 'staff_profile', None), 'is_portal_admin', False))
    staff_profiles = StaffProfile.objects.select_related('user', 'role').filter(user__is_staff=True)
    roles = list(StaffRole.objects.all())
    client_count = User.objects.filter(is_staff=False, is_superuser=False).count()
    open_ticket_count = SupportTicket.objects.exclude(status='closed').count()
    unpaid_total = Invoice.objects.filter(status__in=['unpaid', 'overdue']).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    monthly_revenue = HostingService.objects.filter(status='active').aggregate(total=Sum('monthly_price'))['total'] or Decimal('0.00')
    recent_clients = User.objects.filter(is_staff=False).order_by('-date_joined')[:6]
    recent_tickets = SupportTicket.objects.select_related('user').all()[:6]
    email_profiles = OutboundEmailProfile.objects.all()
    hosting_packages = get_all_hosting_packages('shared') + get_all_hosting_packages('wordpress')
    hosting_packages.sort(key=lambda x: (getattr(x, 'sort_order', 0) or 0, getattr(x, 'id', 0)))
    reseller_packages = get_all_hosting_packages('reseller')
    super_admin_count = staff_profiles.filter(user__is_superuser=True).count()
    portal_admin_count = staff_profiles.filter(is_portal_admin=True).count()
    billing_role_count = StaffRole.objects.filter(can_manage_billing=True).count()
    support_role_count = StaffRole.objects.filter(can_manage_support=True).count()
    for profile in staff_profiles:
        profile.permission_summary = _staff_permissions_summary(profile.role)
    for email_profile in email_profiles:
        email_profile.permission_summary = _email_permission_summary(email_profile)
    email_profiles_by_purpose = {}
    for value, label in EMAIL_PURPOSE_CHOICES:
        bucket = [profile for profile in email_profiles if profile.purpose_category == value]
        if bucket:
            email_profiles_by_purpose[label] = bucket
    return {
        'active_page': active_page,
        'email_event_fields': EMAIL_EVENT_FIELDS,
        'email_purpose_choices': EMAIL_PURPOSE_CHOICES,
        'email_profiles': email_profiles,
        'email_profiles_by_purpose': email_profiles_by_purpose,
        'hosting_packages': hosting_packages,
        'reseller_packages': reseller_packages,
        'servers': VoidPanelServer.objects.all(),
        'pricing_settings': pricing_settings,
        'builder_bandwidth_choices': _bandwidth_choices(pricing_settings),
        'roles': roles,
        'staff_profiles': staff_profiles,
        'recent_clients': recent_clients,
        'recent_tickets': recent_tickets,
        'admin_stats': {
            'staff_count': staff_profiles.count(),
            'role_count': len(roles),
            'client_count': client_count,
            'open_ticket_count': open_ticket_count,
            'monthly_revenue': monthly_revenue,
            'unpaid_total': unpaid_total,
            'super_admin_count': super_admin_count,
            'portal_admin_count': portal_admin_count,
            'billing_role_count': billing_role_count,
            'support_role_count': support_role_count,
            'reseller_count': len(reseller_packages),
        },
        'license_count': PanelLicenseRecord.objects.count(),
        'license_active_count': PanelLicenseRecord.objects.filter(status='active').count(),
        'razorpay_active': RazorpayConfig.objects.filter(pk=1, is_active=True).exists(),
    }


@login_required(login_url='/login/')
def super_admin_staff(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        handled = _handle_super_admin_post(request)
        if handled:
            return handled
    return render(request, 'super_admin_staff.html', _build_super_admin_context('staff'))


@login_required(login_url='/login/')
def super_admin_roles(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        handled = _handle_super_admin_post(request)
        if handled:
            return handled
    return render(request, 'super_admin_roles.html', _build_super_admin_context('roles'))


@login_required(login_url='/login/')
def super_admin_servers(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        handled = _handle_super_admin_post(request)
        if handled:
            return handled
    return render(request, 'super_admin_servers.html', _build_super_admin_context('servers'))


@login_required(login_url='/login/')
def super_admin_emails(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        handled = _handle_super_admin_post(request)
        if handled:
            return handled
    return render(request, 'super_admin_emails.html', _build_super_admin_context('emails'))


@login_required(login_url='/login/')
def super_admin_chips(request):
    """Super admin page to manage Void Chips / Credits settings (signup bonus & exchange rate)."""
    denied = _super_admin_guard(request)
    if denied:
        return denied

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_settings':
            pricing_settings = HostingPricingSettings.objects.first()
            if not pricing_settings:
                pricing_settings = HostingPricingSettings.objects.create(title='Default Pricing Rules')
            try:
                pricing_settings.signup_bonus_chips = int(request.POST.get('signup_bonus_chips', 5000))
                pricing_settings.credits_per_rupee  = int(request.POST.get('credits_per_rupee', 100))
                pricing_settings.save(update_fields=['signup_bonus_chips', 'credits_per_rupee'])
                messages.success(request, 'Void Chips settings updated successfully.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid values — please enter whole numbers only.')
            return redirect('/super-admin/chips/')

        elif action == 'adjust_balance':
            from django.contrib.auth.models import User
            from data.models import CustomerProfile, ChipTransaction, FundTransaction
            user_id = request.POST.get('user_id')
            change_type = request.POST.get('change_type')  # 'chips' or 'funds'
            operation = request.POST.get('operation')      # 'add' or 'deduct'
            try:
                amount = Decimal(request.POST.get('amount', '0'))
            except Exception:
                messages.error(request, 'Invalid amount entered.')
                return redirect('/super-admin/chips/')
                
            try:
                target_user = User.objects.get(id=user_id)
                profile, _ = CustomerProfile.objects.get_or_create(user=target_user)
                if change_type == 'chips':
                    chips_amt = int(amount)
                    if operation == 'add':
                        profile.balance_chips += chips_amt
                        ChipTransaction.objects.create(
                            user=target_user,
                            amount=chips_amt,
                            transaction_type='grant',
                            description='Admin adjustment: added chips'
                        )
                        messages.success(request, f'Successfully added {chips_amt} chips to {target_user.username}.')
                    else:
                        profile.balance_chips = max(0, profile.balance_chips - chips_amt)
                        ChipTransaction.objects.create(
                            user=target_user,
                            amount=-chips_amt,
                            transaction_type='purchase',
                            description='Admin adjustment: deducted chips'
                        )
                        messages.success(request, f'Successfully deducted {chips_amt} chips from {target_user.username}.')
                    profile.save(update_fields=['balance_chips'])
                else:
                    if operation == 'add':
                        profile.balance_funds += amount
                        FundTransaction.objects.create(
                            user=target_user,
                            amount=amount,
                            transaction_type='deposit',
                            description='Admin adjustment: added funds'
                        )
                        messages.success(request, f'Successfully added ₹{amount} funds to {target_user.username}.')
                    else:
                        profile.balance_funds = max(Decimal('0.00'), profile.balance_funds - amount)
                        FundTransaction.objects.create(
                            user=target_user,
                            amount=-amount,
                            transaction_type='purchase',
                            description='Admin adjustment: deducted funds'
                        )
                        messages.success(request, f'Successfully deducted ₹{amount} funds from {target_user.username}.')
                    profile.save(update_fields=['balance_funds'])
            except User.DoesNotExist:
                messages.error(request, 'Selected user does not exist.')
            except Exception as exc:
                messages.error(request, f'Error: {exc}')
            return redirect('/super-admin/chips/')

    from django.contrib.auth.models import User
    users = User.objects.filter(is_superuser=False).select_related('customer_profile').order_by('username')
    ctx = _build_super_admin_context('chips')
    ctx['pricing_settings'] = HostingPricingSettings.objects.first() or HostingPricingSettings()
    ctx['users'] = users
    return render(request, 'super_admin_chips.html', ctx)


@login_required(login_url='/login/')
def super_admin_hosting(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        handled = _handle_super_admin_post(request)
        if handled:
            return handled
    return render(request, 'super_admin_hosting.html', _build_super_admin_context('hosting'))


@login_required(login_url='/login/')
def super_admin_reseller(request):
    """Super admin: manage all reseller accounts — create, edit quotas, suspend."""
    denied = _super_admin_guard(request)
    if denied:
        return denied

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_reseller':
            username    = request.POST.get('username', '').strip()
            email       = request.POST.get('email', '').strip()
            storage_gb  = int(request.POST.get('storage_gb', 50))
            max_accounts= int(request.POST.get('max_accounts', 10))
            company     = request.POST.get('company_name', '').strip()
            import secrets, string
            if not username or not email:
                messages.error(request, 'Username and email are required.')
                return redirect('/super-admin/reseller/')
            if User.objects.filter(username=username).exists():
                messages.error(request, f'User "{username}" already exists.')
                return redirect('/super-admin/reseller/')
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
            new_user = User.objects.create_user(username=username, email=email, password=password)
            # Call the control panel API to provision
            result = _provision_reseller_account(new_user, storage_gb, max_accounts, 'Admin-Created', company)
            if result.get('status') == 'provisioned':
                messages.success(request, f'Reseller "{username}" created. Password: {result.get("password", password)}')
            else:
                messages.warning(request, f'User created but panel provisioning failed: {result.get("error","")}. Retry from the panel.')
            return redirect('/super-admin/reseller/')

        elif action == 'update_quota':
            reseller_user_id = request.POST.get('reseller_user_id')
            storage_gb   = int(request.POST.get('storage_gb', 50))
            max_accounts = int(request.POST.get('max_accounts', 10))
            try:
                target_user = User.objects.get(id=reseller_user_id)
                result = _provision_reseller_account(target_user, storage_gb, max_accounts)
                messages.success(request, f'Quotas updated for {target_user.username}.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
            return redirect('/super-admin/reseller/')

        elif action == 'suspend_reseller':
            reseller_user_id = request.POST.get('reseller_user_id')
            try:
                target_user = User.objects.get(id=reseller_user_id)
                target_user.is_active = False
                target_user.save()
                messages.success(request, f'Reseller "{target_user.username}" suspended.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
            return redirect('/super-admin/reseller/')

        elif action == 'unsuspend_reseller':
            reseller_user_id = request.POST.get('reseller_user_id')
            try:
                target_user = User.objects.get(id=reseller_user_id)
                target_user.is_active = True
                target_user.save()
                messages.success(request, f'Reseller "{target_user.username}" reactivated.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
            return redirect('/super-admin/reseller/')

        elif action in ('create_package', 'update_package', 'delete_package'):
            from data.models import HostingPackageOverride, _STATIC_HOSTING_PACKAGES
            
            def int_or_none(val):
                val = str(val or '').strip()
                return int(val) if val.isdigit() else None

            def decimal_or_none(val):
                val = str(val or '').strip()
                try:
                    return Decimal(val)
                except Exception:
                    return None

            if action == 'update_package':
                package_id = int_or_none(request.POST.get('package_id'))
                if package_id is None:
                    messages.error(request, "Package ID is missing")
                    return redirect('/super-admin/reseller/')
                
                name = request.POST.get('name', '').strip()
                slug = request.POST.get('slug', '').strip()
                short_description = request.POST.get('short_description', '').strip()
                storage_gb = int_or_none(request.POST.get('storage_gb'))
                max_accounts = int_or_none(request.POST.get('max_accounts'))
                monthly_price = decimal_or_none(request.POST.get('monthly_price'))
                is_featured = bool(request.POST.get('is_featured') or request.POST.get('is_featured') == 'true')
                is_active = bool(request.POST.get('is_active') or request.POST.get('is_active') == 'true')
                sort_order = int_or_none(request.POST.get('sort_order'))
                server_id = int_or_none(request.POST.get('server_id'))

                has_email_marketing = bool(request.POST.get('has_email_marketing') or request.POST.get('has_email_marketing') == 'true')
                has_whatsapp_marketing = bool(request.POST.get('has_whatsapp_marketing') or request.POST.get('has_whatsapp_marketing') == 'true')
                has_automation = bool(request.POST.get('has_automation') or request.POST.get('has_automation') == 'true')
                has_analytics = bool(request.POST.get('has_analytics') or request.POST.get('has_analytics') == 'true')
                has_seo_crm = bool(request.POST.get('has_seo_crm') or request.POST.get('has_seo_crm') == 'true')

                HostingPackageOverride.objects.update_or_create(
                    package_id=package_id,
                    defaults={
                        'name': name,
                        'slug': slug,
                        'package_type': 'reseller',
                        'short_description': short_description,
                        'monthly_price': monthly_price,
                        'storage_gb': storage_gb,
                        'allowed_domains': max_accounts,
                        'sort_order': sort_order,
                        'server_id': server_id,
                        'is_featured': is_featured,
                        'is_active': is_active,
                        'has_email_marketing': has_email_marketing,
                        'has_whatsapp_marketing': has_whatsapp_marketing,
                        'has_automation': has_automation,
                        'has_analytics': has_analytics,
                        'has_seo_crm': has_seo_crm,
                    }
                )
                messages.success(request, f"Reseller plan '{name}' updated successfully!")
                return redirect('/super-admin/reseller/')

            elif action == 'create_package':
                name = request.POST.get('name', '').strip()
                slug = request.POST.get('slug', '').strip()
                short_description = request.POST.get('short_description', '').strip()
                storage_gb = int_or_none(request.POST.get('storage_gb'))
                max_accounts = int_or_none(request.POST.get('max_accounts'))
                monthly_price = decimal_or_none(request.POST.get('monthly_price'))
                is_featured = bool(request.POST.get('is_featured') or request.POST.get('is_featured') == 'true')
                is_active = bool(request.POST.get('is_active') or request.POST.get('is_active') == 'true')
                sort_order = int_or_none(request.POST.get('sort_order'))
                server_id = int_or_none(request.POST.get('server_id'))

                has_email_marketing = bool(request.POST.get('has_email_marketing') or request.POST.get('has_email_marketing') == 'true')
                has_whatsapp_marketing = bool(request.POST.get('has_whatsapp_marketing') or request.POST.get('has_whatsapp_marketing') == 'true')
                has_automation = bool(request.POST.get('has_automation') or request.POST.get('has_automation') == 'true')
                has_analytics = bool(request.POST.get('has_analytics') or request.POST.get('has_analytics') == 'true')
                has_seo_crm = bool(request.POST.get('has_seo_crm') or request.POST.get('has_seo_crm') == 'true')

                if not name:
                    messages.error(request, "Plan name is required")
                    return redirect('/super-admin/reseller/')
                if not slug:
                    from django.utils.text import slugify
                    slug = slugify(name)

                max_id = max(list(_STATIC_HOSTING_PACKAGES.keys()) + [9])
                db_max = HostingPackageOverride.objects.aggregate(max_id=models.Max('package_id'))['max_id']
                if db_max:
                    max_id = max(max_id, db_max)
                new_id = max_id + 1

                HostingPackageOverride.objects.create(
                    package_id=new_id,
                    name=name,
                    slug=slug,
                    package_type='reseller',
                    short_description=short_description,
                    monthly_price=monthly_price,
                    storage_gb=storage_gb,
                    allowed_domains=max_accounts,
                    sort_order=sort_order,
                    server_id=server_id,
                    is_featured=is_featured,
                    is_active=is_active,
                    has_email_marketing=has_email_marketing,
                    has_whatsapp_marketing=has_whatsapp_marketing,
                    has_automation=has_automation,
                    has_analytics=has_analytics,
                    has_seo_crm=has_seo_crm,
                )
                messages.success(request, f"Reseller plan '{name}' created successfully!")
                return redirect('/super-admin/reseller/')

            elif action == 'delete_package':
                package_id = int_or_none(request.POST.get('package_id'))
                if package_id:
                    HostingPackageOverride.objects.update_or_create(
                        package_id=package_id,
                        defaults={'is_active': False}
                    )
                    messages.success(request, "Reseller plan deactivated/deleted successfully.")
                return redirect('/super-admin/reseller/')

    reseller_portal_packages = get_all_hosting_packages('reseller')
    ctx = _build_super_admin_context('reseller')
    ctx['reseller_portal_packages'] = reseller_portal_packages
    return render(request, 'super_admin_reseller.html', ctx)


@login_required(login_url='/login/')
def super_admin_signals(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    return render(request, 'super_admin_signals.html', _build_super_admin_context('signals'))


def loginn(request):
    if request.user.is_authenticated:
        return redirect("/portal/")
    if request.method == 'POST':
        identity = request.POST.get('Email', '').strip()
        password = request.POST.get('password')
        user = authenticate(request, username=identity, password=password)
        if user is None and identity:
            matched_user = User.objects.filter(email__iexact=identity).first()
            if matched_user:
                user = authenticate(request, username=matched_user.username, password=password)
        if user is not None:
            login(request, user)
            PortalActivity.objects.create(
                user=user,
                category='account',
                title='User logged in',
                description='Accessed the portal successfully.',
            )
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                from django.urls import resolve
                try:
                    resolve(next_url)
                    return redirect(next_url)
                except Exception:
                    pass
            if user.is_superuser:
                return redirect('/super-admin/')
            return redirect('/portal/')
        else:
            messages.error(request, "Invalid username/email or password")
            return redirect('/login/')
    return render(request, "login.html")


def send_registration_otp_email(customer_email, otp_code):
    from django.core.mail import EmailMessage
    from django.conf import settings
    from data.models import OutboundEmailProfile
    from django.core.mail.backends.smtp import EmailBackend
    import logging
    _logger = logging.getLogger('voidpanel')

    subject = f'🔒 Email Verification Code: {otp_code} — VoidPanel'
    html_msg = f"""
    <div style="font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 32px; border: 1px solid #e2e8f0; border-radius: 16px; background: #ffffff;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h2 style="color: #1e3a8a; margin: 0; font-weight: 800; font-size: 1.5rem;">VoidPanel</h2>
        </div>
        <p style="font-size: 1rem; color: #334155; line-height: 1.6; margin-bottom: 20px;">Hi there,</p>
        <p style="font-size: 1rem; color: #334155; line-height: 1.6; margin-bottom: 24px;">Thank you for signing up for VoidPanel. Please use the following One-Time Password (OTP) to verify your email address and activate your account:</p>
        <div style="text-align: center; margin: 28px 0;">
            <span style="font-size: 2.25rem; font-weight: 800; letter-spacing: 0.2em; color: #2563eb; background: #eff6ff; padding: 12px 28px; border-radius: 12px; border: 1px dashed #bfdbfe; display: inline-block;">{otp_code}</span>
        </div>
        <p style="font-size: 0.88rem; color: #64748b; line-height: 1.6; margin-bottom: 28px;">This code is valid for 10 minutes. If you did not request this code, please ignore this email.</p>
        <div style="border-top: 1px solid #e2e8f0; padding-top: 16px; text-align: center; font-size: 0.8rem; color: #94a3b8;">
            © VoidPanel. Free & Open Source.
        </div>
    </div>
    """

    # Try OutboundEmailProfile first
    try:
        smtp_profile = (
            OutboundEmailProfile.objects
            .filter(is_active=True)
            .order_by('-is_default')
            .first()
        )
    except Exception:
        smtp_profile = None

    try:
        if smtp_profile:
            email = EmailMessage(
                subject=subject,
                body=html_msg,
                from_email=f'{smtp_profile.from_name or "VoidPanel"} <{smtp_profile.from_email}>',
                to=[customer_email],
                reply_to=[smtp_profile.reply_to_email] if smtp_profile.reply_to_email else [],
            )
            email.content_subtype = 'html'
            backend = EmailBackend(
                host=smtp_profile.smtp_host,
                port=smtp_profile.smtp_port,
                username=smtp_profile.smtp_username,
                password=smtp_profile.smtp_password,
                use_tls=smtp_profile.use_tls,
                use_ssl=smtp_profile.use_ssl,
                fail_silently=False,
            )
            backend.open()
            backend.send_messages([email])
            backend.close()
        else:
            email = EmailMessage(
                subject=subject,
                body=html_msg,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@voidpanel.com',
                to=[customer_email],
            )
            email.content_subtype = 'html'
            email.send(fail_silently=False)
        _logger.info('Verification OTP sent to %s', customer_email)
    except Exception as exc:
        _logger.error('Failed to send verification OTP to %s: %s', customer_email, exc)


def register(request):
    if request.user.is_authenticated:
        return redirect("/portal/")
    if request.method == 'POST':
        import re as _re
        import random
        email            = request.POST.get('Email', '').strip().lower()
        full_name        = request.POST.get('full_name', '').strip()
        phone_raw        = request.POST.get('phone', '').strip()
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        def _ctx():
            return {'full_name': full_name, 'Email': email, 'phone': phone_raw}

        if not full_name or not email:
            messages.error(request, "Please complete your name and email")
            return render(request, 'register.html', _ctx())

        # Phone validation — required, digits only, 7–15 chars
        phone_digits = _re.sub(r'[^\d]', '', phone_raw)
        if not phone_digits:
            messages.error(request, "Phone number is required.")
            return render(request, 'register.html', _ctx())
        if not (7 <= len(phone_digits) <= 15):
            messages.error(request, "Enter a valid phone number (7–15 digits).")
            return render(request, 'register.html', _ctx())

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'register.html', _ctx())
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return render(request, 'register.html', _ctx())
        try:
            validate_password(password)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, 'register.html', _ctx())

        # Generate OTP code and store signup info in session
        otp_code = str(random.randint(100000, 999999))
        request.session['reg_email'] = email
        request.session['reg_full_name'] = full_name
        request.session['reg_phone'] = phone_raw
        request.session['reg_password'] = password
        request.session['reg_otp'] = otp_code

        send_registration_otp_email(email, otp_code)

        messages.success(request, f"A 6-digit verification code has been sent to {email}.")
        return redirect("/register/verify/")

    return render(request, 'register.html')


def register_verify(request):
    if request.user.is_authenticated:
        return redirect("/portal/")
    
    email = request.session.get('reg_email')
    otp_code = request.session.get('reg_otp')
    if not email or not otp_code:
        messages.error(request, "Please register first.")
        return redirect("/register/")

    if request.method == 'POST':
        user_otp = request.POST.get('otp', '').strip()
        if user_otp == otp_code:
            full_name = request.session.get('reg_full_name')
            phone_raw = request.session.get('reg_phone')
            password = request.session.get('reg_password')

            name_parts = [part for part in full_name.split() if part]
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            username = _generate_username_from_email(email)
            country = _detect_country_from_request(request)

            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                ensure_portal_seed_data(
                    user,
                    profile_defaults={
                        'country': country,
                        'phone': phone_raw,
                    },
                )

            login(request, user)

            # Clear session
            for key in ['reg_email', 'reg_full_name', 'reg_phone', 'reg_password', 'reg_otp']:
                request.session.pop(key, None)

            messages.success(request, "Email verified successfully! Welcome to your VoidPanel Client Portal.")
            return redirect("/portal/")
        else:
            messages.error(request, "Invalid verification code. Please try again.")

    _ps = HostingPricingSettings.objects.first()
    _bonus_chips   = getattr(_ps, 'signup_bonus_chips', 5000) if _ps else 5000
    _rate          = getattr(_ps, 'credits_per_rupee', 100)  if _ps else 100
    _bonus_rupees  = int(_bonus_chips / _rate) if _rate else 0
    return render(request, 'verify_email.html', {
        'email':         email,
        'signup_bonus_chips': _bonus_chips,
        'bonus_rupees':  _bonus_rupees,
    })



def register_resend_otp(request):
    if request.user.is_authenticated:
        return redirect("/portal/")

    email = request.session.get('reg_email')
    if not email:
        messages.error(request, "Please register first.")
        return redirect("/register/")

    import random
    new_otp = str(random.randint(100000, 999999))
    request.session['reg_otp'] = new_otp

    send_registration_otp_email(email, new_otp)
    messages.success(request, f"A new verification code has been sent to {email}.")
    return redirect("/register/verify/")



def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('/')


# ══════════════════════════════════════════════════════════════
#  CART & CHECKOUT
# ══════════════════════════════════════════════════════════════

@login_required(login_url='/login/')
def cart_config(request, slug):
    """Step-1/2: Choose domain + billing cycle for a hosting package."""
    package = get_static_hosting_package(slug)
    if not package:
        messages.error(request, 'That hosting package does not exist or is no longer available.')
        return redirect('/web-hosting/')

    pricing_settings = ensure_default_hosting_catalog()
    discounts = {
        'monthly': 0,
        'quarterly': pricing_settings.quarterly_discount_percent,
        'annually': pricing_settings.annual_discount_percent,
    }

    if request.method == 'POST':
        domain = request.POST.get('domain', '').strip().lower()
        billing_cycle = request.POST.get('billing_cycle', 'monthly')
        coupon_code = request.POST.get('coupon_code', '').strip().upper()
        
        domain_action = request.POST.get('domain_action', 'existing')
        try:
            domain_price = Decimal(request.POST.get('domain_price', '0.00'))
        except:
            domain_price = Decimal('0.00')
        try:
            domain_years = int(request.POST.get('domain_years', '1'))
        except:
            domain_years = 1

        if not domain or '.' not in domain:
            messages.error(request, 'Please enter a valid domain name (e.g. example.com).')
            return render(request, 'cart_config.html', {'package': package, 'discounts': discounts})

        # Calculate discounted price
        discount_pct = discounts.get(billing_cycle, 0)
        total = package.monthly_price * (1 - Decimal(discount_pct) / 100)
        if billing_cycle == 'annually':
            total = total * 12
        elif billing_cycle == 'quarterly':
            total = total * 3
            
        applied_coupon = None
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code).first()
            if coupon and coupon.is_valid(billing_cycle=billing_cycle):
                applied_coupon = coupon
                if coupon.discount_type == 'percentage':
                    total = total * (1 - (coupon.discount_value / Decimal(100)))
                else:
                    total = total - coupon.discount_value
                    if total < 0: total = Decimal('0.00')

        total = total + domain_price
        total = total.quantize(Decimal('0.01'))

        today = timezone.localdate()
        due_delta = {'monthly': 30, 'quarterly': 90, 'annually': 365}.get(billing_cycle, 30)
        next_due = today + timedelta(days=due_delta)

        # ── Domain availability check for "register" action ─────────────────────
        domain_error = None
        if domain_action == 'register' and '.' in domain:
            try:
                from voidpanel.domain_client import ConnectResellerClient
                client = ConnectResellerClient()
                avail = client.check_domain(domain)
                # Most registrars return available=False or status='registered' for taken domains
                if avail.get('available') is False or avail.get('status') in ('registered', 'taken', 'unavailable'):
                    domain_error = f"The domain <strong>{domain}</strong> is already registered and cannot be registered again. You can choose <strong>Transfer Domain</strong> instead, or pick a different domain name."
            except Exception:
                # If domain check fails, don't block checkout — just skip silently
                pass

        if domain_error:
            return render(request, 'cart_config.html', {
                'package': package,
                'discounts': discounts,
                'domain_error': domain_error,
                'prefill_domain': domain,
            })

        ensure_portal_seed_data(request.user)

        with transaction.atomic():
            service = HostingService.objects.create(
                user=request.user,
                service_name=package.name,
                domain=domain,
                product_type=package.get_package_type_display(),
                status='pending',
                billing_cycle=billing_cycle,
                monthly_price=package.monthly_price,
                next_due_date=next_due,
                server_hostname='in-mum-01.voidpanel.cloud',
                storage_gb=package.storage_gb,
                bandwidth_gb=500,
            )
            inv_count = Invoice.objects.filter(user=request.user).count()
            
            invoice_desc = f'{package.name} Hosting — {domain}'
            if domain_action == 'register':
                invoice_desc = f'{package.name} Hosting + Domain Registration — {domain}'
            elif domain_action == 'transfer':
                invoice_desc = f'{package.name} Hosting + Domain Transfer — {domain}'

            invoice = Invoice.objects.create(
                user=request.user,
                invoice_number=f'VP-{request.user.id:04d}-{inv_count + 1:03d}',
                description=invoice_desc,
                status='unpaid',
                total=total,
                currency='INR',
                due_date=today + timedelta(days=7),
            )
            
            if domain_action in ['register', 'transfer']:
                from data.models import DomainOrder
                DomainOrder.objects.create(
                    user=request.user,
                    domain_name=domain,
                    years=domain_years,
                    wholesale_price=Decimal('0.00'),
                    final_price=domain_price,
                    status='pending_payment',
                    invoice=invoice,
                )

            order = HostingOrder.objects.create(
                user=request.user,
                package_name=package.slug,
                service=service,
                invoice=invoice,
                domain=domain,
                billing_cycle=billing_cycle,
                total=total,
                status='pending_payment',
            )
            PortalActivity.objects.create(
                user=request.user,
                category='billing',
                title=f'Order placed: {package.name}',
                description=f'Domain: {domain} ({domain_action}) — Billing: {billing_cycle} — Total: ${total}',
            )
            
            if applied_coupon:
                applied_coupon.current_uses += 1
                applied_coupon.save(update_fields=['current_uses'])

        return redirect(f'/portal/invoice/{invoice.id}/pay/')

    return render(request, 'cart_config.html', {
        'package': package,
        'discounts': discounts,
    })


@login_required(login_url='/login/')
def invoice_pay(request, inv_id):
    """Show an invoice with payment instructions. Admin can confirm payment."""
    invoice = Invoice.objects.filter(id=inv_id, user=request.user).first()
    if not invoice:
        # Superusers can view any invoice
        if request.user.is_superuser:
            invoice = Invoice.objects.filter(id=inv_id).first()
        if not invoice:
            messages.error(request, 'Invoice not found.')
            return redirect('/portal/')

    # Superuser manual payment confirmation
    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')
        if action == 'mark_paid':
            invoice.status = 'paid'
            invoice.paid_date = timezone.localdate()
            invoice.save(update_fields=['status', 'paid_date'])
            # Activate linked service
            if hasattr(invoice, 'order') and invoice.order:
                order = invoice.order
                order.status = 'provisioning'
                order.save(update_fields=['status'])
                _activate_service_after_provision(order, invoice=invoice)
            
            # Activate linked suite order
            try:
                suite_order = invoice.suite_order
            except Exception:
                suite_order = None
            if suite_order:
                suite_order.status = 'paid'
                suite_order.save(update_fields=['status'])
                _activate_suite_service(suite_order)

            PortalActivity.objects.create(
                user=invoice.user,
                category='billing',
                title='Invoice marked as paid',
                description=f'{invoice.invoice_number} for {invoice.total} {invoice.currency}',
            )
            messages.success(request, f'Invoice {invoice.invoice_number} marked as paid and provisioning triggered.')
            return redirect(f'/portal/invoice/{inv_id}/pay/')

    from data.models import CustomerProfile
    profile = CustomerProfile.objects.filter(user=request.user).first()
    order = getattr(invoice, 'order', None)
    domain_order = getattr(invoice, 'domain_order', None)
    rzp_config = RazorpayConfig.get()
    return render(request, 'invoice_pay.html', {
        'invoice':      invoice,
        'order':        order,
        'domain_order': domain_order,
        'razorpay_on':  rzp_config.is_ready,
        'profile':      profile,
    })


def order_complete(request):
    """Handles post-payment landing from Razorpay or manual form submit."""
    if request.method == 'POST':
        service_type    = request.POST.get('service_type', '')
        plan_id         = request.POST.get('plan_id', '')
        billing_cycle   = request.POST.get('billing_cycle', 'monthly')
        price           = request.POST.get('price', '0')
        razorpay_pid    = request.POST.get('razorpay_payment_id', '')

        if service_type == 'social_media' and request.user.is_authenticated and plan_id:
            try:
                service = _activate_social_service(
                    user=request.user,
                    plan_id=int(plan_id),
                    billing_cycle=billing_cycle,
                    price_paid=price,
                )
                if service:
                    request.session.pop('social_order', None)
                    messages.success(
                        request,
                        '🎉 Social Media Manager activated! Connect your first account below.'
                    )
                    return redirect('/portal/#social')
            except Exception as e:
                messages.error(request, f'Activation error: {e}')
                return redirect('/social-media/')

    return render(request, 'order_complete.html')


# ══════════════════════════════════════════════════════════════
#  CLIENT PORTAL — TICKET SYSTEM
# ══════════════════════════════════════════════════════════════

@login_required(login_url='/login/')
def portal_ticket_new(request):
    """Client creates a new support ticket."""
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        department = request.POST.get('department', 'Support')
        priority = request.POST.get('priority', 'medium')
        body = request.POST.get('body', '').strip()

        if not subject or not body:
            messages.error(request, 'Subject and message body are required.')
            return render(request, 'portal_ticket_new.html')

        ticket_count = SupportTicket.objects.filter(user=request.user).count()
        ticket = SupportTicket.objects.create(
            user=request.user,
            ticket_number=f'VP-TKT-{request.user.id:04d}-{ticket_count + 1:03d}',
            subject=subject,
            department=department,
            priority=priority,
            status='open',
            last_reply_at=timezone.now(),
        )
        TicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            is_staff_reply=False,
            body=body,
        )
        PortalActivity.objects.create(
            user=request.user,
            category='support',
            title=f'Ticket opened: {subject}',
            description=f'Department: {department} | Priority: {priority}',
        )
        messages.success(request, f'Ticket {ticket.ticket_number} created. Our team will respond shortly.')
        return redirect(f'/portal/ticket/{ticket.id}/')

    return render(request, 'portal_ticket_new.html')


@login_required(login_url='/login/')
def portal_ticket_detail(request, ticket_id):
    """View a ticket thread and add a reply."""
    ticket = SupportTicket.objects.filter(id=ticket_id).first()
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('/portal/')
    # Only owner or staff can view
    if ticket.user != request.user and not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('/portal/')

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            TicketReply.objects.create(
                ticket=ticket,
                author=request.user,
                is_staff_reply=request.user.is_staff,
                body=body,
            )
            ticket.last_reply_at = timezone.now()
            if request.user.is_staff:
                ticket.status = 'answered'
            else:
                ticket.status = 'open'
            ticket.save(update_fields=['last_reply_at', 'status'])
            messages.success(request, 'Reply posted.')
        return redirect(f'/portal/ticket/{ticket_id}/')

    replies = ticket.replies.select_related('author').all()
    return render(request, 'portal_ticket_detail.html', {
        'ticket': ticket,
        'replies': replies,
    })


# ══════════════════════════════════════════════════════════════
#  SUPER ADMIN — CLIENTS, BILLING, TICKETS
# ══════════════════════════════════════════════════════════════

@login_required(login_url='/login/')
def super_admin_clients(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'suspend_all':
            uid = request.POST.get('user_id')
            HostingService.objects.filter(user_id=uid, status='active').update(status='suspended')
            messages.success(request, 'All active services for that client have been suspended.')
        return _super_admin_redirect(request, '/super-admin/clients/')

    clients = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')
    client_data = []
    for c in clients:
        unpaid = Invoice.objects.filter(user=c, status__in=['unpaid', 'overdue']).aggregate(
            total=Sum('total'))['total'] or Decimal('0.00')
        client_data.append({
            'user': c,
            'active_services': HostingService.objects.filter(user=c, status='active').count(),
            'total_services': HostingService.objects.filter(user=c).count(),
            'open_tickets': SupportTicket.objects.filter(user=c).exclude(status='closed').count(),
            'unpaid_balance': unpaid,
        })
    ctx = _build_super_admin_context('clients')
    ctx['client_data'] = client_data
    return render(request, 'super_admin_clients.html', ctx)


@login_required(login_url='/login/')
def super_admin_billing(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_paid':
            inv_id = request.POST.get('invoice_id')
            inv = Invoice.objects.filter(id=inv_id).first()
            if inv:
                inv.status = 'paid'
                inv.paid_date = timezone.localdate()
                inv.save(update_fields=['status', 'paid_date'])
                # Activate linked service via provisioner (auto-creates account + sends email)
                if hasattr(inv, 'order') and inv.order:
                    inv.order.status = 'provisioning'
                    inv.order.save(update_fields=['status'])
                    _activate_service_after_provision(inv.order, invoice=inv)
                messages.success(request, f'Invoice {inv.invoice_number} marked as paid and hosting account provisioned.')
        elif action == 'create_invoice':
            uid = request.POST.get('user_id')
            desc = request.POST.get('description', '').strip()
            total = request.POST.get('total', '0')
            due = request.POST.get('due_date')
            user = User.objects.filter(id=uid).first()
            if user and desc and due:
                cnt = Invoice.objects.filter(user=user).count()
                Invoice.objects.create(
                    user=user,
                    invoice_number=f'VP-{user.id:04d}-{cnt + 1:03d}',
                    description=desc,
                    status='unpaid',
                    total=Decimal(total),
                    currency='USD',
                    due_date=due,
                )
                messages.success(request, f'Invoice created for {user.get_full_name() or user.username}.')
        elif action == 'delete_invoice':
            inv_id = request.POST.get('invoice_id')
            inv = Invoice.objects.filter(id=inv_id).first()
            if inv:
                inv_num = inv.invoice_number
                inv.delete()
                messages.success(request, f'Invoice {inv_num} deleted successfully.')
            else:
                messages.error(request, 'Invoice not found.')
        return _super_admin_redirect(request, '/super-admin/billing/')

    status_filter = request.GET.get('status', '')
    invoices = Invoice.objects.select_related('user').order_by('-created_at')
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    clients = User.objects.filter(is_staff=False).order_by('username')
    ctx = _build_super_admin_context('billing')
    ctx['invoices'] = invoices[:100]
    ctx['clients'] = clients
    ctx['status_filter'] = status_filter
    return render(request, 'super_admin_billing.html', ctx)


@login_required(login_url='/login/')
def super_admin_tickets(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    dept_filter = request.GET.get('dept', '')
    status_filter = request.GET.get('status', '')
    tickets = SupportTicket.objects.select_related('user').order_by('-last_reply_at')
    if dept_filter:
        tickets = tickets.filter(department=dept_filter)
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    ctx = _build_super_admin_context('tickets')
    ctx['tickets'] = tickets[:100]
    ctx['dept_filter'] = dept_filter
    ctx['status_filter'] = status_filter
    return render(request, 'super_admin_tickets.html', ctx)


@login_required(login_url='/login/')
def super_admin_ticket_detail(request, ticket_id):
    denied = _super_admin_guard(request)
    if denied:
        return denied
    ticket = SupportTicket.objects.select_related('user').filter(id=ticket_id).first()
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('/super-admin/tickets/')
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        close = request.POST.get('close_ticket')
        if body:
            TicketReply.objects.create(
                ticket=ticket,
                author=request.user,
                is_staff_reply=True,
                body=body,
            )
            ticket.last_reply_at = timezone.now()
            ticket.status = 'closed' if close else 'answered'
            ticket.save(update_fields=['last_reply_at', 'status'])
            messages.success(request, 'Staff reply posted.')
        return redirect(f'/super-admin/tickets/{ticket_id}/')
    replies = ticket.replies.select_related('author').all()
    ctx = _build_super_admin_context('tickets')
    ctx['ticket'] = ticket
    ctx['replies'] = replies
    ctx['license_count'] = PanelLicenseRecord.objects.count()
    return render(request, 'super_admin_ticket_detail.html', ctx)


# ── License API (called by installed panel instances) ────────────────────────────

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import secrets


@csrf_exempt
def api_license_register(request):
    """
    POST /api/license/register/
    Called by a fresh VoidPanel installation during activation.
    Body: {"key": "<64-char hex>", "hostname": "..."}
    Validates the key and binds it to the server IP.
    Returns: {"status": "ok", "key": "<64-char hex>"}
             {"status": "error", "error": "..."}
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'POST required'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON body'}, status=400)

    key = body.get('key', '').strip()
    hostname = body.get('hostname', '').strip()
    email = body.get('email', '').strip()
    password = body.get('password', '').strip()
    mode = body.get('mode', 'login').strip()

    if not key and not (email and password):
        return JsonResponse({'status': 'error', 'error': 'License key or email/password is required'}, status=400)

    # Determine client IP
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    client_ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')

    from django.utils import timezone

    if email and password:
        from django.contrib.auth import authenticate
        from django.contrib.auth.models import User
        auth_user = None

        if mode == 'register':
            # Create a new user if one doesn't exist with this email
            if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
                return JsonResponse({'status': 'error', 'error': 'An account with this email already exists.'}, status=400)
            try:
                # Use email as the username for new API-registered users
                auth_user = User.objects.create_user(username=email, email=email, password=password)
            except Exception as e:
                return JsonResponse({'status': 'error', 'error': f'Registration failed: {str(e)}'}, status=500)
        else:
            # Login mode
            try:
                usr = User.objects.get(email=email)
                auth_user = authenticate(username=usr.username, password=password)
            except User.DoesNotExist:
                auth_user = authenticate(username=email, password=password)
                
            if not auth_user:
                return JsonResponse({'status': 'error', 'error': 'Invalid email or password.'}, status=401)
            
        # Create a new license key on the fly for the valid user
        # Check if this is a brand-new user (first license)
        from django.utils import timezone as _tz
        import datetime
        is_new_user = not PanelLicenseRecord.objects.filter(user=auth_user).exists()
        new_key = secrets.token_hex(32)
        trial_expires = _tz.now() + datetime.timedelta(days=30) if is_new_user else None
        lic = PanelLicenseRecord.objects.create(
            user=auth_user,
            key=new_key,
            hostname=hostname,
            server_ip=client_ip,
            status='active',
            tier='pro',          # 30-day Pro trial for new users; existing = Pro by default
            is_trial=is_new_user,
            expires_at=trial_expires,
            last_ping=_tz.now(),
        )
        resp = {
            'status':      'ok',
            'key':         new_key,
            'tier':        lic.tier,
            'is_trial':    lic.is_trial,
            'expires_at':  lic.expires_at.isoformat() if lic.expires_at else None,
            'features':    lic.features,
        }
        if is_new_user:
            resp['trial_message'] = 'Welcome! You have a 30-day free Pro trial. Enjoy full features!'
        return JsonResponse(resp)

    # Existing logic if 'key' is provided instead
    try:
        record = PanelLicenseRecord.objects.get(key=key)
    except PanelLicenseRecord.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'Invalid license key'}, status=401)

    if record.status != 'active':
        return JsonResponse({'status': 'error', 'error': f'License is {record.status}'}, status=403)

    if record.server_ip:
        if record.server_ip != client_ip:
            return JsonResponse({'status': 'error', 'error': 'License is already bound to another IP address'}, status=403)
    else:
        record.server_ip = client_ip

    if hostname:
        record.hostname = hostname

    record.last_ping = timezone.now()
    record.save(update_fields=['server_ip', 'hostname', 'last_ping'])

    return JsonResponse({'status': 'ok', 'key': key})


@csrf_exempt
def api_license_validate(request):
    """
    POST /api/license/validate/
    Called nightly (or on demand) by an installed VoidPanel instance.
    Body: {"key": "<64-char hex>"}
    Returns full tier/feature payload — NO hard IP lock (IP changes with NAT/IPv6).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'POST required'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON body'}, status=400)

    key = body.get('key', '').strip()
    if not key:
        return JsonResponse({'status': 'not_found'}, status=404)

    try:
        record = PanelLicenseRecord.objects.select_related('user').get(key=key)
    except PanelLicenseRecord.DoesNotExist:
        return JsonResponse({'status': 'not_found'}, status=404)

    # Determine client IP — update last_seen_ip for audit (DO NOT block on mismatch)
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    client_ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')

    from django.utils import timezone as _tz
    update_fields = ['last_ping', 'last_seen_ip']
    record.last_ping    = _tz.now()
    record.last_seen_ip = client_ip

    # Handle trial expiry — downgrade tier to starter, do NOT revoke
    if record.is_trial and record.is_expired and record.tier != 'starter':
        record.tier = 'starter'
        update_fields.append('tier')

    record.save(update_fields=update_fields)

    if record.status != 'active':
        return JsonResponse({'status': record.status, 'tier': record.effective_tier})

    return JsonResponse({
        'status':       'active',
        'tier':         record.effective_tier,
        'is_trial':     record.is_trial,
        'days_remaining': record.days_remaining,
        'expires_at':   record.expires_at.isoformat() if record.expires_at else None,
        'features':     record.features,
        'hostname':     record.hostname,
    })


# ── Super Admin: License Management ───────────────────────────────────────

@login_required(login_url='/login/')
def super_admin_licenses(request):
    """Super admin license management listing page."""
    denied = _super_admin_guard(request)
    if denied:
        return denied

    ctx = _build_super_admin_context('licenses')
    ctx['licenses']  = PanelLicenseRecord.objects.select_related('user').all()
    ctx['total']     = PanelLicenseRecord.objects.count()
    ctx['active']    = PanelLicenseRecord.objects.filter(status='active').count()
    ctx['suspended'] = PanelLicenseRecord.objects.filter(status='suspended').count()
    ctx['revoked']   = PanelLicenseRecord.objects.filter(status='revoked').count()
    ctx['tier_starter']   = PanelLicenseRecord.objects.filter(tier='starter').count()
    ctx['tier_pro']       = PanelLicenseRecord.objects.filter(tier='pro').count()
    ctx['tier_advanced']  = PanelLicenseRecord.objects.filter(tier='advanced').count()
    ctx['tier_unlimited'] = PanelLicenseRecord.objects.filter(tier='unlimited').count()
    ctx['trials_active']  = PanelLicenseRecord.objects.filter(is_trial=True, status='active').count()
    ctx['tier_choices']   = PanelLicenseRecord.TIER_CHOICES
    # Build feature comparison matrix for UI table
    FEAT = PanelLicenseRecord.TIER_FEATURES
    ctx['feature_matrix'] = [
        {'name': '🌐 Web Hosting Management',      'starter': FEAT['starter']['hosting_mgmt'],        'pro': FEAT['pro']['hosting_mgmt'],        'advanced': FEAT['advanced']['hosting_mgmt'],        'unlimited': FEAT['unlimited']['hosting_mgmt']},
        {'name': '📧 Email Plans',                  'starter': FEAT['starter']['email_plans'],          'pro': FEAT['pro']['email_plans'],          'advanced': FEAT['advanced']['email_plans'],          'unlimited': FEAT['unlimited']['email_plans']},
        {'name': '🔒 SSL Plans',                    'starter': FEAT['starter']['ssl_plans'],            'pro': FEAT['pro']['ssl_plans'],            'advanced': FEAT['advanced']['ssl_plans'],            'unlimited': FEAT['unlimited']['ssl_plans']},
        {'name': '💳 Billing & Invoices',           'starter': FEAT['starter']['billing'],              'pro': FEAT['pro']['billing'],              'advanced': FEAT['advanced']['billing'],              'unlimited': FEAT['unlimited']['billing']},
        {'name': '💬 Live Chat Support',            'starter': FEAT['starter']['live_chat'],            'pro': FEAT['pro']['live_chat'],            'advanced': FEAT['advanced']['live_chat'],            'unlimited': FEAT['unlimited']['live_chat']},
        {'name': '📣 Marketing Suite',              'starter': FEAT['starter']['marketing_suite'],      'pro': FEAT['pro']['marketing_suite'],      'advanced': FEAT['advanced']['marketing_suite'],      'unlimited': FEAT['unlimited']['marketing_suite']},
        {'name': '🔍 SEO Tools',                    'starter': FEAT['starter']['seo_tools'],            'pro': FEAT['pro']['seo_tools'],            'advanced': FEAT['advanced']['seo_tools'],            'unlimited': FEAT['unlimited']['seo_tools']},
        {'name': '📱 Social Media Connect',         'starter': FEAT['starter']['social_media'],         'pro': FEAT['pro']['social_media'],         'advanced': FEAT['advanced']['social_media'],         'unlimited': FEAT['unlimited']['social_media']},
        {'name': '💚 WhatsApp Automation',          'starter': FEAT['starter']['whatsapp_automation'],  'pro': FEAT['pro']['whatsapp_automation'],  'advanced': FEAT['advanced']['whatsapp_automation'],  'unlimited': FEAT['unlimited']['whatsapp_automation']},
        {'name': '🐳 Docker Manager',               'starter': FEAT['starter']['docker_manager'],       'pro': FEAT['pro']['docker_manager'],       'advanced': FEAT['advanced']['docker_manager'],       'unlimited': FEAT['unlimited']['docker_manager']},
        {'name': '⚙️ Script Installer (MERN/Python)','starter': FEAT['starter']['script_installer'],    'pro': FEAT['pro']['script_installer'],    'advanced': FEAT['advanced']['script_installer'],    'unlimited': FEAT['unlimited']['script_installer']},
        {'name': '🤖 Void AI Assistant',            'starter': FEAT['starter']['ai_assistant'],         'pro': FEAT['pro']['ai_assistant'],         'advanced': FEAT['advanced']['ai_assistant'],         'unlimited': FEAT['unlimited']['ai_assistant']},
        {'name': '🎯 Digital Suite',                'starter': FEAT['starter']['digital_suite'],        'pro': FEAT['pro']['digital_suite'],        'advanced': FEAT['advanced']['digital_suite'],        'unlimited': FEAT['unlimited']['digital_suite']},
        {'name': '🏪 Reseller Hosting Mgmt',        'starter': FEAT['starter']['reseller_hosting'],     'pro': FEAT['pro']['reseller_hosting'],     'advanced': FEAT['advanced']['reseller_hosting'],     'unlimited': FEAT['unlimited']['reseller_hosting']},
        {'name': '🏷️ White-label Branding',         'starter': FEAT['starter']['white_label'],          'pro': FEAT['pro']['white_label'],          'advanced': FEAT['advanced']['white_label'],          'unlimited': FEAT['unlimited']['white_label']},
        {'name': '🎖️ Priority Support',             'starter': FEAT['starter']['priority_support'],     'pro': FEAT['pro']['priority_support'],     'advanced': FEAT['advanced']['priority_support'],     'unlimited': FEAT['unlimited']['priority_support']},
    ]
    return render(request, 'super_admin_licenses.html', ctx)


@login_required(login_url='/login/')
def super_admin_license_action(request):
    """Handle suspend / activate / revoke / tier-change actions on a PanelLicenseRecord."""
    denied = _super_admin_guard(request)
    if denied:
        return denied
    if request.method != 'POST':
        return redirect('/super-admin/licenses/')

    action     = request.POST.get('action')
    license_id = request.POST.get('license_id')
    record     = PanelLicenseRecord.objects.filter(id=license_id).first()
    if not record:
        messages.error(request, 'License not found.')
        return redirect('/super-admin/licenses/')

    if action == 'suspend':
        record.status = 'suspended'
        record.save(update_fields=['status'])
        messages.success(request, f'License …{record.key[48:]} suspended.')
    elif action == 'activate':
        record.status = 'active'
        record.save(update_fields=['status'])
        messages.success(request, f'License …{record.key[48:]} re-activated.')
    elif action == 'revoke':
        record.status = 'revoked'
        record.save(update_fields=['status'])
        messages.success(request, f'License …{record.key[48:]} permanently revoked.')
    elif action == 'delete':
        record.delete()
        messages.success(request, 'License record deleted.')
    elif action == 'change_tier':
        new_tier = request.POST.get('new_tier', '').strip()
        valid_tiers = [t[0] for t in PanelLicenseRecord.TIER_CHOICES]
        if new_tier in valid_tiers:
            record.tier = new_tier
            record.is_trial = False          # manual tier change = not trial
            record.expires_at = None         # manual = lifetime
            record.save(update_fields=['tier', 'is_trial', 'expires_at'])
            messages.success(request, f'License tier changed to {record.get_tier_display()}.')
        else:
            messages.error(request, 'Invalid tier selected.')
    elif action == 'reset_ip':
        record.server_ip = None
        record.last_seen_ip = None
        record.save(update_fields=['server_ip', 'last_seen_ip'])
        messages.success(request, f'IP lock cleared for license …{record.key[48:]}. It can now activate from any IP.')
    else:
        messages.error(request, 'Unknown action.')

    return redirect('/super-admin/licenses/')


# ── Web-Based SSH Installer ──────────────────────────────────────────────

def _run_ssh_install_thread(job_id, ip, username, password, license_key, email):
    """Background thread to perform the SSH installation simulation/execution."""
    try:
        job = RemoteInstallationJob.objects.get(id=job_id)
    except RemoteInstallationJob.DoesNotExist:
        return

    def append_log(text):
        job.logs += text + "\n"
        job.save(update_fields=['logs'])

    job.status = RemoteInstallationJob.STATUS_RUNNING
    job.progress = 5
    append_log(f"[{time.strftime('%H:%M:%S')}] Connecting to {ip} as {username}...")
    job.save(update_fields=['status', 'progress'])

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Establish connection
        client.connect(hostname=ip, username=username, password=password, timeout=10)
        append_log(f"[{time.strftime('%H:%M:%S')}] SSH connection established successfully.")
        
        job.progress = 15
        job.save(update_fields=['progress'])
        time.sleep(1)

        # ── Step 1: Pre-flight update ──────────────────────────────────────
        append_log(f"[{time.strftime('%H:%M:%S')}] Updating package lists...")
        _, stdout_s, stderr_s = client.exec_command("apt-get update -y 2>&1", timeout=120)
        for line in stdout_s:
            append_log(f" > {line.rstrip()}")
        job.progress = 15
        job.save(update_fields=['progress'])

        # ── Step 2: Ensure curl + wget ────────────────────────────────────
        append_log(f"[{time.strftime('%H:%M:%S')}] Installing curl and wget...")
        _, stdout_s, _ = client.exec_command("apt-get install -y curl wget 2>&1", timeout=120)
        for line in stdout_s:
            append_log(f" > {line.rstrip()}")
        job.progress = 25
        job.save(update_fields=['progress'])

        # ── Step 3: Download and run the real install script ──────────────
        append_log(f"[{time.strftime('%H:%M:%S')}] Downloading VoidPanel installer from voidpanel.com...")
        install_cmd = (
            f"export TERM=xterm DEBIAN_FRONTEND=noninteractive; "
            f"curl -fsSL https://voidpanel.com/op/ubuntu.sh -o /tmp/vp_install.sh && "
            f"chmod +x /tmp/vp_install.sh && "
            f"bash /tmp/vp_install.sh 2>&1"
        )
        transport = client.get_transport()
        channel = transport.open_session()
        channel.set_combine_stderr(True)
        channel.exec_command(install_cmd)

        # Stream real output — ubuntu.sh takes 10-20 min on a fresh VPS
        TIMEOUT = 1800  # 30 minutes max
        start_time = time.time()
        progress_val = 30

        while not channel.exit_status_ready():
            if time.time() - start_time > TIMEOUT:
                append_log(f"[{time.strftime('%H:%M:%S')}] ERROR: Installation timed out after 30 minutes.")
                job.status = RemoteInstallationJob.STATUS_FAILED
                job.save(update_fields=['status', 'logs'])
                channel.close()
                client.close()
                return

            if channel.recv_ready():
                raw = channel.recv(4096).decode('utf-8', errors='replace')
                for line in raw.splitlines():
                    if line.strip():
                        append_log(line)
                # Advance progress bar gradually up to 90%
                if progress_val < 90:
                    progress_val = min(progress_val + 1, 90)
                    job.progress = progress_val
                    job.save(update_fields=['progress', 'logs'])
            else:
                time.sleep(1)

        exit_code = channel.recv_exit_status()
        # Drain any remaining output
        while channel.recv_ready():
            raw = channel.recv(4096).decode('utf-8', errors='replace')
            for line in raw.splitlines():
                if line.strip():
                    append_log(line)
        job.save(update_fields=['logs'])

        if exit_code != 0:
            append_log(f"[{time.strftime('%H:%M:%S')}] ERROR: ubuntu.sh exited with code {exit_code}.")
            job.status = RemoteInstallationJob.STATUS_FAILED
            job.save(update_fields=['status'])
            client.close()
            return

        # ── Step 4: Read real credentials from /root/voidpanel_access.txt ─
        append_log(f"[{time.strftime('%H:%M:%S')}] Fetching installation credentials...")
        _, cred_out, _ = client.exec_command("cat /root/voidpanel_access.txt 2>/dev/null || echo ''", timeout=15)
        cred_text = cred_out.read().decode('utf-8', errors='replace').strip()

        panel_user = "admin"
        panel_pass = ""
        # Parse /root/voidpanel_access.txt lines exactly:
        #   Username: admin
        #   Password: XXXXXXXX
        # Must NOT match "MySQL Root Pass:", "Web Engine:", etc.
        for line in cred_text.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith('username:'):
                val = stripped.split(':', 1)[1].strip()
                if val:
                    panel_user = val
            elif lower.startswith('password:'):
                val = stripped.split(':', 1)[1].strip()
                if val:
                    panel_pass = val

        if not panel_pass:
            # Fallback: generate a secure password if we couldn't parse the file
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            panel_pass = ''.join(random.choice(chars) for _ in range(16))
            append_log(f"[{time.strftime('%H:%M:%S')}] Warning: Could not read credentials file — a temporary password has been generated.")

        append_log(f"[{time.strftime('%H:%M:%S')}] Installation Complete!")
        job.admin_username = panel_user
        job.admin_password = panel_pass
        job.progress = 100
        job.status = RemoteInstallationJob.STATUS_COMPLETED
        job.save(update_fields=['progress', 'status', 'admin_username', 'admin_password'])
        
        # Send Email Notification
        try:
            send_mail(
                subject='VoidPanel Installation Completed',
                message=f'Your VoidPanel installation on {ip} has finished successfully.\n\nLogin URL: https://{ip}/\nUsername: {panel_user}\nPassword: {panel_pass}\n\nPlease save these credentials securely.',
                from_email='noreply@voidpanel.com',
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as e:
            append_log(f"[{time.strftime('%H:%M:%S')}] Warning: Failed to send email notice ({e}).")
            job.save(update_fields=['logs'])
            
    except Exception as e:
        append_log(f"[{time.strftime('%H:%M:%S')}] ERROR: {str(e)}")
        job.status = RemoteInstallationJob.STATUS_FAILED
        job.save(update_fields=['status'])
    finally:
        client.close()


@login_required(login_url='/login/')
def portal_remote_install_start(request, license_id):
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'status': 'error', 'error': 'POST required'})
    
    from django.http import JsonResponse
    try:
        license = request.user.panel_licenses.get(id=license_id)
    except PanelLicenseRecord.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'License not found'})

    ip = request.POST.get('ip', '').strip()
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')

    if not ip or not username or not password:
        return JsonResponse({'status': 'error', 'error': 'IP, Username, and Password are required'})
    
    # Create the job
    job = RemoteInstallationJob.objects.create(
        license=license,
        user=request.user,
        ip_address=ip,
        status=RemoteInstallationJob.STATUS_PENDING,
        progress=0
    )
    
    # Start thread
    thread = threading.Thread(
        target=_run_ssh_install_thread,
        args=(job.id, ip, username, password, license.key, request.user.email)
    )
    thread.daemon = True
    thread.start()
    
    return JsonResponse({'status': 'ok', 'job_id': job.id})


@login_required(login_url='/login/')
def portal_remote_install_status(request, license_id, job_id):
    from django.http import JsonResponse
    try:
        license = request.user.panel_licenses.get(id=license_id)
        job = RemoteInstallationJob.objects.get(id=job_id, license=license, user=request.user)
    except (PanelLicenseRecord.DoesNotExist, RemoteInstallationJob.DoesNotExist):
        return JsonResponse({'status': 'error', 'error': 'Job or License not found'}, status=404)

    data = {
        'status': 'ok',
        'job_status': job.status,
        'progress': job.progress,
        'logs': job.logs,
    }
    
    if job.status == RemoteInstallationJob.STATUS_COMPLETED:
        data['credentials'] = {
            'username': job.admin_username,
            'password': job.admin_password,
        }
    
    return JsonResponse(data)


# ── Super Admin Live Chat ──────────────────────────────────────────────────
@login_required(login_url="/login/")
def super_admin_livechat_dashboard(request):
    if not request.user.is_superuser and not getattr(request.user, 'is_staff', False):
        return redirect('/portal/')
    
    from chatting.models import LiveChatSession
    sessions = LiveChatSession.objects.all().order_by('-updated_at')
    return render(request, "super_admin_livechat_dashboard.html", {"sessions": sessions})

@login_required(login_url="/login/")
def super_admin_livechat_detail(request, session_id):
    if not request.user.is_superuser and not getattr(request.user, 'is_staff', False):
        return redirect('/portal/')
        
    from chatting.models import LiveChatSession
    session = get_object_or_404(LiveChatSession, id=session_id)
    return render(request, "super_admin_livechat_detail.html", {"chat_session": session})

@login_required(login_url="/login/")
def super_admin_livechat_assign(request, session_id):
    if not request.user.is_superuser and not getattr(request.user, 'is_staff', False):
        return redirect('/portal/')
        
    from chatting.models import LiveChatSession
    session = get_object_or_404(LiveChatSession, id=session_id)
    session.assigned_agent = request.user
    session.save()
    return redirect(f'/super-admin/livechat/{session_id}/')

# ══════════════════════════════════════════════════════════════
#  DOMAINS & COUPONS
# ══════════════════════════════════════════════════════════════

def domain_registration(request):
    """Public domain search and registration page"""
    from voidpanel.domain_client import ConnectResellerClient
    client = ConnectResellerClient()
    return render(request, "domain_search.html", {'domain_api_enabled': True})

def api_domain_check(request):
    """AJAX endpoint for testing domain availability (single domain)"""
    domain = request.GET.get('domain', '').strip().lower()
    if not domain or '.' not in domain:
        return JsonResponse({"error": "Invalid domain name"})
    from voidpanel.domain_client import ConnectResellerClient
    client = ConnectResellerClient()
    result = client.check_domain(domain)
    return JsonResponse(result)

def api_domain_check_bulk(request):
    """AJAX endpoint for checking domain across multiple TLDs"""
    name = request.GET.get('name', '').strip().lower()
    if not name:
        return JsonResponse({"error": "Invalid name"})
    
    # Extract base name and typed TLD
    parts = name.split('.')
    base = parts[0].strip()
    if not base:
        return JsonResponse({"error": "Invalid name"})
        
    user_tld = '.' + '.'.join(parts[1:]) if len(parts) > 1 else None

    # Default TLD list to check
    DEFAULT_TLDS = ['.com', '.in', '.net', '.org', '.co.in', '.io']
    if user_tld and user_tld.startswith('.'):
        # Prioritize the user's typed TLD as the first item, and append default TLDs (excluding duplicate)
        tlds = [user_tld] + [t for t in DEFAULT_TLDS if t != user_tld]
    else:
        tlds = DEFAULT_TLDS

    from voidpanel.domain_client import ConnectResellerClient
    client = ConnectResellerClient()
    results = client.check_bulk(base, tlds=tlds)
    if isinstance(results, dict) and 'error' in results:
        return JsonResponse({"error": results['error']})
    return JsonResponse({"results": results})

@login_required(login_url='/login/')
def domain_order_checkout(request):
    """Creates a DomainOrder and invoice, then redirects to portal invoice page."""
    domain_name = request.GET.get('domain', '').strip().lower()
    price_inr = request.GET.get('price', '0')
    years = int(request.GET.get('years', 1))
    
    if not domain_name or '.' not in domain_name:
        messages.error(request, 'Invalid domain name.')
        return redirect('/domain-registration/')

    try:
        final_price = Decimal(price_inr).quantize(Decimal('0.01'))
    except:
        final_price = Decimal('999.00')

    # ── Domain availability check before creating order ─────────────────────
    action = request.GET.get('action', 'register')
    if action == 'register':
        try:
            from voidpanel.domain_client import ConnectResellerClient
            client = ConnectResellerClient()
            avail = client.check_domain(domain_name)
            if avail.get('available') is False or avail.get('status') in ('registered', 'taken', 'unavailable'):
                messages.error(
                    request,
                    f"❌ The domain '{domain_name}' is already registered. "
                    "Please search for a different domain or use the Transfer option."
                )
                return redirect('/domain-registration/')
        except Exception:
            pass  # Don't block on API failure

    ensure_portal_seed_data(request.user)
    
    today = timezone.localdate()
    with transaction.atomic():
        inv_count = Invoice.objects.filter(user=request.user).count()
        invoice = Invoice.objects.create(
            user=request.user,
            invoice_number=f'VP-DOM-{request.user.id:04d}-{inv_count + 1:03d}',
            description=f'Domain Registration: {domain_name} ({years} Year)',
            status='unpaid',
            total=final_price,
            currency='INR',
            due_date=today + timedelta(days=7),
        )
        domain_order = DomainOrder.objects.create(
            user=request.user,
            domain_name=domain_name,
            years=years,
            wholesale_price=Decimal(0),
            final_price=final_price,
            status='pending_payment',
            invoice=invoice,
        )
        PortalActivity.objects.create(
            user=request.user,
            category='billing',
            title=f'Domain order initiated: {domain_name}',
            description=f'{years} year(s) — ₹{final_price}',
        )
    
    messages.success(request, f'Domain order created for {domain_name}. Please complete your payment.')
    return redirect(f'/portal/invoice/{invoice.id}/pay/')

@csrf_exempt
def api_coupon_validate(request):
    """AJAX endpoint for validating coupon code on cart checkout"""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    
    import json
    try:
        body = json.loads(request.body)
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    code = body.get('code', '').strip().upper()
    if not code:
        return JsonResponse({"error": "Empty code"})
    
    coupon = Coupon.objects.filter(code=code).first()
    if not coupon:
        return JsonResponse({"error": "Invalid or expired coupon code"})
        
    billing_cycle = body.get('billing_cycle', '').strip().lower() or None
    if not coupon.is_valid(billing_cycle=billing_cycle):
        if billing_cycle and not coupon.is_valid():
            # Failed general validity (expired/max uses)
            return JsonResponse({"error": "Coupon is no longer valid or has reached its usage limit"})
        elif billing_cycle:
            # Failed billing cycle constraint specifically
            return JsonResponse({"error": f"Coupon is not applicable to the selected '{billing_cycle}' billing cycle"})
        else:
            return JsonResponse({"error": "Coupon is no longer valid or has reached its usage limit"})
    
    return JsonResponse({
        "status": "ok",
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_value": float(coupon.discount_value)
    })

# ── Super Admin Configs ──

@login_required(login_url="/login/")
def super_admin_domain_api(request):
    denied = _super_admin_guard(request)
    if denied: return denied
    
    config = ConnectResellerConfig.objects.first()
    if not config:
        config = ConnectResellerConfig.objects.create(margin_percentage=20)

    if request.method == "POST":
        config.api_key = request.POST.get("api_key", "").strip()
        config.reseller_id = request.POST.get("reseller_id", "").strip()
        config.margin_percentage = int(request.POST.get("margin_percentage", 20))
        config.is_active = request.POST.get("is_active") == "on"
        config.save()
        messages.success(request, "Domain API Configuration saved successfully.")
        return redirect("/super-admin/domain-api/")
        
    ctx = _build_super_admin_context('domain-api')
    ctx['config'] = config
    return render(request, "super_admin_domain_api.html", ctx)


@login_required(login_url="/login/")
def super_admin_coupons(request):
    denied = _super_admin_guard(request)
    if denied: return denied
    
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            code = request.POST.get("code", "").strip().upper()
            dtype = request.POST.get("discount_type")
            dval = request.POST.get("discount_value")
            max_uses = request.POST.get("max_uses")
            valid_until = request.POST.get("valid_until")
            
            applicable_monthly = 'applicable_monthly' in request.POST
            applicable_quarterly = 'applicable_quarterly' in request.POST
            applicable_annually = 'applicable_annually' in request.POST
            
            if Coupon.objects.filter(code=code).exists():
                messages.error(request, f"Coupon code {code} already exists.")
            else:
                Coupon.objects.create(
                    code=code,
                    discount_type=dtype,
                    discount_value=dval,
                    max_uses=int(max_uses) if max_uses else None,
                    valid_until=valid_until if valid_until else None,
                    applicable_monthly=applicable_monthly,
                    applicable_quarterly=applicable_quarterly,
                    applicable_annually=applicable_annually,
                    is_active=True
                )
                messages.success(request, f"Coupon {code} created successfully.")
        elif action == "toggle":
            cid = request.POST.get("coupon_id")
            c = Coupon.objects.filter(id=cid).first()
            if c:
                c.is_active = not c.is_active
                c.save()
                messages.success(request, f"Coupon {c.code} status toggled.")
        elif action == "delete":
            cid = request.POST.get("coupon_id")
            Coupon.objects.filter(id=cid).delete()
            messages.success(request, "Coupon deleted.")
        return redirect("/super-admin/coupons/")
        
    ctx = _build_super_admin_context('coupons')
    ctx['coupons'] = Coupon.objects.all().order_by('-created_at')
    return render(request, "super_admin_coupons.html", ctx)


# ══════════════════════════════════════════════════════════════
#  PANEL TICKET API — called by installed VoidPanel instances
# ══════════════════════════════════════════════════════════════

import json as _json_mod

@csrf_exempt
def api_panel_ticket_create(request):
    """
    POST /api/panel/ticket/create/
    Called by VoidPanel installed instances. Authenticates via license key,
    links to the owning user account, and creates a SupportTicket.

    Body (JSON):
      {
        "license_key": "<64-hex>",
        "subject": "...",
        "department": "Hosting|Technical|Billing|Other",
        "priority": "low|medium|high|urgent",
        "body": "..."
      }

    Returns:
      {"ok": true, "ticket_id": 7, "ticket_number": "VP-TKT-0003-001"}
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    try:
        data = _json_mod.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    license_key = data.get('license_key', '').strip()
    subject     = data.get('subject',     '').strip()
    department  = data.get('department',  'Technical').strip()
    priority    = data.get('priority',    'medium').strip()
    body        = data.get('body',        '').strip()

    if not license_key:
        return JsonResponse({'ok': False, 'error': 'license_key required'}, status=400)
    if not subject or not body:
        return JsonResponse({'ok': False, 'error': 'subject and body required'}, status=400)

    # Resolve license → user account
    record = PanelLicenseRecord.objects.filter(key=license_key, status='active').first()
    if not record:
        return JsonResponse({'ok': False, 'error': 'Invalid or inactive license key'}, status=403)

    user = record.user
    if not user:
        return JsonResponse({'ok': False, 'error': 'License has no linked user account'}, status=403)

    # Create the ticket + opening reply
    ticket_count = SupportTicket.objects.filter(user=user).count()
    ticket = SupportTicket.objects.create(
        user=user,
        ticket_number=f'VP-TKT-{user.id:04d}-{ticket_count + 1:03d}',
        subject=subject,
        department=department,
        priority=priority,
        status='open',
        last_reply_at=timezone.now(),
    )
    TicketReply.objects.create(
        ticket=ticket,
        author=user,
        is_staff_reply=False,
        body=body,
    )
    PortalActivity.objects.create(
        user=user,
        category='support',
        title=f'Ticket from panel: {subject}',
        description=f'Submitted via installed VoidPanel — Dept: {department} | Priority: {priority}',
    )

    return JsonResponse({
        'ok': True,
        'ticket_id': ticket.id,
        'ticket_number': ticket.ticket_number,
    })


@csrf_exempt
def api_panel_ticket_list(request):
    """
    POST /api/panel/ticket/list/
    Returns all tickets and their replies for the license-key-linked account.

    Body (JSON): {"license_key": "<64-hex>"}

    Returns:
      {
        "ok": true,
        "tickets": [
          {
            "id": 7,
            "ticket_number": "VP-TKT-0003-001",
            "subject": "...",
            "status": "answered",
            "priority": "medium",
            "department": "Technical",
            "last_reply_at": "2026-04-21T12:00:00Z",
            "has_unread_reply": true,
            "replies": [
              {"id": 1, "is_staff": false, "author": "rohan", "body": "...", "created_at": "..."},
              {"id": 2, "is_staff": true, "author": "Support Team", "body": "...", "created_at": "..."}
            ]
          }
        ]
      }
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    try:
        data = _json_mod.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    license_key = data.get('license_key', '').strip()
    if not license_key:
        return JsonResponse({'ok': False, 'error': 'license_key required'}, status=400)

    record = PanelLicenseRecord.objects.filter(key=license_key, status='active').first()
    if not record or not record.user:
        return JsonResponse({'ok': False, 'error': 'Invalid license'}, status=403)

    user = record.user
    tickets = SupportTicket.objects.filter(user=user).order_by('-last_reply_at').prefetch_related('replies__author')

    result = []
    for t in tickets:
        replies_data = []
        last_reply_is_staff = False
        for r in t.replies.all():
            replies_data.append({
                'id': r.id,
                'is_staff': r.is_staff_reply,
                'author': 'Support Team' if r.is_staff_reply else (r.author.get_full_name() or r.author.username),
                'body': r.body,
                'created_at': r.created_at.strftime('%d %b %Y %H:%M'),
            })
            last_reply_is_staff = r.is_staff_reply

        result.append({
            'id': t.id,
            'ticket_number': t.ticket_number,
            'subject': t.subject,
            'status': t.status,
            'priority': t.priority,
            'department': t.department,
            'last_reply_at': t.last_reply_at.strftime('%d %b %Y %H:%M'),
            'has_new_reply': last_reply_is_staff,
            'replies': replies_data,
        })

    return JsonResponse({'ok': True, 'tickets': result})


@csrf_exempt
def api_panel_ticket_reply(request):
    """
    POST /api/panel/ticket/reply/
    Called by VoidPanel installed instances to post a reply to a ticket.

    Body (JSON):
      {
        "license_key": "<64-hex>",
        "ticket_number": "VP-TKT-0001-003",
        "body": "..."
      }

    Returns:
      {"ok": true}
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    try:
        data = _json_mod.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    license_key = data.get('license_key', '').strip()
    ticket_number = data.get('ticket_number', '').strip()
    body = data.get('body', '').strip()

    if not license_key or not ticket_number or not body:
        return JsonResponse({'ok': False, 'error': 'license_key, ticket_number, and body are required'}, status=400)

    record = PanelLicenseRecord.objects.filter(key=license_key, status='active').first()
    if not record or not record.user:
        return JsonResponse({'ok': False, 'error': 'Invalid license'}, status=403)

    ticket = SupportTicket.objects.filter(ticket_number=ticket_number, user=record.user).first()
    if not ticket:
        return JsonResponse({'ok': False, 'error': 'Ticket not found'}, status=404)

    TicketReply.objects.create(
        ticket=ticket,
        author=record.user,
        is_staff_reply=False,
        body=body,
    )
    ticket.last_reply_at = timezone.now()
    ticket.status = 'open'
    ticket.save(update_fields=['last_reply_at', 'status'])

    return JsonResponse({'ok': True})


# ══════════════════════════════════════════════════════════════
#  RAZORPAY PAYMENT GATEWAY
# ══════════════════════════════════════════════════════════════

import hmac
import hashlib
import json as _rjson


# ── Super Admin: Payment Gateway Config ───────────────────────────────────────

@login_required(login_url='/login/')
def super_admin_payment_gateway(request):
    """Manage Razorpay API credentials and view payment stats."""
    denied = _super_admin_guard(request)
    if denied:
        return denied

    config = RazorpayConfig.get()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save':
            test_key_id     = request.POST.get('test_key_id', '').strip()
            test_key_secret = request.POST.get('test_key_secret', '').strip()
            live_key_id     = request.POST.get('live_key_id', '').strip()
            live_key_secret = request.POST.get('live_key_secret', '').strip()
            webhook_secret  = request.POST.get('webhook_secret', '').strip()
            is_active  = request.POST.get('is_active') == 'on'
            is_live    = request.POST.get('is_live_mode') == 'on'

            config.test_key_id = test_key_id
            if test_key_secret:
                config.test_key_secret = test_key_secret
            config.live_key_id = live_key_id
            if live_key_secret:
                config.live_key_secret = live_key_secret
            if webhook_secret:
                config.webhook_secret = webhook_secret
            config.is_active    = is_active
            config.is_live_mode = is_live
            config.save()
            mode_str = 'Live' if is_live else 'Test'
            messages.success(request, f'Configuration saved — gateway in {mode_str} mode.')
        elif action == 'test':
            kid, ksecret = config.get_active_keys()
            if not kid or not ksecret:
                mode_label = config.mode_label
                messages.error(request, f'No {mode_label} keys saved yet. Add them and save first.')
            else:
                try:
                    try:
                        import razorpay
                    except ImportError:
                        messages.error(request, '❌ Razorpay module not installed. Run: pip install razorpay==2.0.1 in the website venv.')
                        return _super_admin_redirect(request, '/super-admin/payment-gateway/')
                    client = razorpay.Client(auth=(kid, ksecret))
                    client.order.all({'count': 1})
                    messages.success(request, f'✅ {config.mode_label} mode connection successful — credentials are valid.')
                except Exception as e:
                    messages.error(request, f'❌ Connection failed: {str(e)[:140]}')
        return _super_admin_redirect(request, '/super-admin/payment-gateway/')

    # Stats
    total_payments   = RazorpayPayment.objects.filter(status='captured').count()
    total_revenue    = RazorpayPayment.objects.filter(status='captured').aggregate(
                           s=Sum('amount_paise'))['s'] or 0
    recent_payments  = RazorpayPayment.objects.select_related('invoice', 'user').order_by('-created_at')[:15]
    failed_payments  = RazorpayPayment.objects.filter(status='failed').count()

    ctx = _build_super_admin_context('payment_gateway')
    ctx.update({
        'config': config,
        'total_payments': total_payments,
        'total_revenue_inr': total_revenue / 100,
        'recent_payments': recent_payments,
        'failed_payments': failed_payments,
    })
    return render(request, 'super_admin_payment_gateway.html', ctx)


# ── API: Create Razorpay Order ────────────────────────────────────────────────

@login_required(login_url='/login/')
@csrf_exempt
def api_razorpay_create_order(request):
    """
    POST /api/payment/razorpay/create-order/
    Body: { "invoice_id": 7 }
    Returns: { "order_id": "order_xxx", "amount": 49900, "currency": "INR",
               "key_id": "rzp_test_xxx", "name": "VoidPanel", "description": "...",
               "prefill": {"name": "...", "email": "..."} }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    config = RazorpayConfig.get()
    if not config.is_ready:
        return JsonResponse({'error': 'Payment gateway not configured or disabled'}, status=503)

    try:
        data = _rjson.loads(request.body)
        inv_id = int(data.get('invoice_id', 0))
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    invoice = Invoice.objects.filter(id=inv_id, user=request.user).first()
    if not invoice:
        return JsonResponse({'error': 'Invoice not found'}, status=404)
    if invoice.status == 'paid':
        return JsonResponse({'error': 'Invoice is already paid'}, status=400)

    # Minimum Razorpay amount is ₹1 (100 paise)
    amount_paise = max(int(invoice.total * 100), 100)

    kid, ksecret = config.get_active_keys()
    try:
        try:
            import razorpay
        except ImportError:
            return JsonResponse({'error': 'Razorpay module not installed on the server. Please run: pip install razorpay==2.0.1'}, status=503)
        client = razorpay.Client(auth=(kid, ksecret))
        rz_order = client.order.create({
            'amount':   amount_paise,
            'currency': 'INR',
            'receipt':  invoice.invoice_number[:40],   # Razorpay limit 40 chars
            'payment_capture': 1,                       # Auto-capture on success
            'notes': {
                'invoice_id':  str(invoice.id),
                'invoice_num': invoice.invoice_number,
                'user_id':     str(request.user.id),
                'email':       request.user.email,
            }
        })
    except Exception as e:
        return JsonResponse({'error': f'Razorpay error: {str(e)[:160]}'}, status=502)

    # Audit log
    RazorpayPayment.objects.create(
        invoice=invoice,
        user=request.user,
        razorpay_order_id=rz_order['id'],
        amount_paise=amount_paise,
        status='created',
    )

    # Get phone from profile if available, otherwise use a safe default
    try:
        from data.models import CustomerProfile
        profile = CustomerProfile.objects.filter(user=request.user).first()
        user_phone = (profile.phone.strip() if profile and profile.phone else '') or '9999999999'
    except Exception:
        user_phone = '9999999999'

    return JsonResponse({
        'order_id':    rz_order['id'],
        'amount':      amount_paise,
        'currency':    'INR',
        'key_id':      kid,
        'name':        'VoidPanel',
        'description': invoice.description,
        'invoice_id':  invoice.id,
        'prefill': {
            'name':    request.user.get_full_name() or request.user.username,
            'email':   request.user.email,
            'contact': user_phone,
        }
    })


def process_paid_invoice(invoice, user):
    """
    Handles payment processing for a paid invoice.
    Updates CustomerProfile (balance_funds, balance_chips), logs transactions.
    Safe to be called multiple times (idempotent because of checking invoice.status == 'paid').
    """
    if invoice.status == 'paid':
        return

    from data.models import CustomerProfile, FundTransaction, ChipTransaction, HostingPricingSettings
    from decimal import Decimal

    is_deposit = invoice.description.startswith("Deposit Funds")
    is_chips   = invoice.description.startswith("Purchase AI Chips")

    with transaction.atomic():
        profile, _ = CustomerProfile.objects.select_for_update().get_or_create(user=user)
        
        if is_deposit:
            profile.balance_funds += invoice.total
            profile.save(update_fields=['balance_funds'])
            FundTransaction.objects.create(
                user=user,
                amount=invoice.total,
                transaction_type='deposit',
                description=invoice.description
            )
        elif is_chips:
            try:
                chips_qty = int(invoice.description.split(' — ')[1].split(' ')[0])
            except Exception:
                pricing_settings = HostingPricingSettings.objects.first()
                rate = getattr(pricing_settings, 'credits_per_rupee', 100) or 100
                chips_qty = int(invoice.total * rate)

            profile.balance_chips += chips_qty
            profile.save(update_fields=['balance_chips'])
            ChipTransaction.objects.create(
                user=user,
                amount=chips_qty,
                transaction_type='purchase',
                description=invoice.description
            )
        else:
            chips_to_use, funds_to_deduct_inr, remaining_due = calculate_invoice_payment_split(invoice, profile)
            if chips_to_use > 0:
                profile.balance_chips = max(0, profile.balance_chips - chips_to_use)
                ChipTransaction.objects.create(
                    user=user,
                    amount=-chips_to_use,
                    transaction_type='purchase',
                    description=f'Paid for invoice {invoice.invoice_number}'
                )
            if funds_to_deduct_inr > 0:
                profile.balance_funds = max(Decimal('0.00'), profile.balance_funds - funds_to_deduct_inr)
                FundTransaction.objects.create(
                    user=user,
                    amount=-funds_to_deduct_inr,
                    transaction_type='purchase',
                    description=f'Paid for invoice {invoice.invoice_number}'
                )
            profile.save(update_fields=['balance_chips', 'balance_funds'])

        invoice.status    = 'paid'
        invoice.paid_date = timezone.localdate()
        invoice.save(update_fields=['status', 'paid_date'])


# ── API: Verify Razorpay Payment ──────────────────────────────────────────────

@login_required(login_url='/login/')
@csrf_exempt
def api_razorpay_verify(request):
    """
    POST /api/payment/razorpay/verify/
    Body: { "razorpay_order_id": "...", "razorpay_payment_id": "...",
            "razorpay_signature": "...", "invoice_id": 7 }
    Verifies HMAC signature, marks invoice paid, triggers provisioning.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    config = RazorpayConfig.get()
    _, ksecret = config.get_active_keys()
    if not ksecret:
        return JsonResponse({'error': 'Gateway not configured'}, status=503)

    try:
        data = _rjson.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid body'}, status=400)

    rz_order_id   = data.get('razorpay_order_id', '')
    rz_payment_id = data.get('razorpay_payment_id', '')
    rz_signature  = data.get('razorpay_signature', '')
    inv_id        = data.get('invoice_id')

    # 1. Verify HMAC-SHA256 signature using Razorpay Python SDK utility
    msg = f"{rz_order_id}|{rz_payment_id}"
    expected_sig = hmac.new(
        ksecret.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, rz_signature):
        # Log failure
        rp = RazorpayPayment.objects.filter(razorpay_order_id=rz_order_id).first()
        if rp:
            rp.status = 'failed'
            rp.error_description = 'Signature mismatch'
            rp.save(update_fields=['status', 'error_description'])
        return JsonResponse({'error': 'Signature verification failed'}, status=400)

    # 2. Update payment log
    rp = RazorpayPayment.objects.filter(razorpay_order_id=rz_order_id).first()
    if rp:
        rp.razorpay_payment_id = rz_payment_id
        rp.razorpay_signature  = rz_signature
        rp.status = 'captured'
        rp.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'status'])

    # 3. Mark invoice as paid and process balances/funds/chips
    invoice = Invoice.objects.filter(id=inv_id, user=request.user).first()
    if not invoice:
        return JsonResponse({'error': 'Invoice not found after payment'}, status=404)

    process_paid_invoice(invoice, request.user)

    # 4. Trigger provisioning for hosting orders
    order = getattr(invoice, 'order', None)
    if order:
        order.status = 'provisioning'
        order.save(update_fields=['status'])
        try:
            _activate_service_after_provision(order, invoice=invoice)
        except Exception as prov_err:
            order.status = 'failed'
            order.provision_response = {'error': str(prov_err)}
            order.save(update_fields=['status', 'provision_response'])

    # 5. Domain order payment
    domain_order = getattr(invoice, 'domain_order', None)
    if domain_order:
        domain_order.status = 'processing'
        domain_order.save(update_fields=['status'])

    # 6. Professional Email order provisioning
    try:
        email_order = invoice.email_order
    except Exception:
        email_order = None
    if email_order and email_order.status == 'pending_payment':
        email_order.status = 'provisioning'
        email_order.save(update_fields=['status'])
        try:
            _activate_email_service(email_order, invoice=invoice)
            email_order.status = 'active'
            email_order.provision_response = {'status': 'success'}
            email_order.save(update_fields=['status', 'provision_response'])
        except Exception as email_err:
            _logger.error('Email provisioning failed for order %s: %s', email_order.pk, email_err)
            email_order.status = 'failed'
            email_order.provision_response = {'error': str(email_err)}
            email_order.save(update_fields=['status', 'provision_response'])

    # 7. SSL order provisioning
    try:
        ssl_order = invoice.ssl_order
    except Exception:
        ssl_order = None
    if ssl_order and ssl_order.status == 'pending_payment':
        ssl_order.status = 'provisioning'
        ssl_order.save(update_fields=['status'])
        try:
            _activate_ssl_service(ssl_order, invoice=invoice)
            ssl_order.status = 'active'
            ssl_order.provision_response = {'status': 'success'}
            ssl_order.save(update_fields=['status', 'provision_response'])
        except Exception as ssl_err:
            _logger.error('SSL provisioning failed for order %s: %s', ssl_order.pk, ssl_err)
            ssl_order.status = 'failed'
            ssl_order.provision_response = {'error': str(ssl_err)}
            ssl_order.save(update_fields=['status', 'provision_response'])

    # 8. Suite order activation
    try:
        suite_order_obj = invoice.suite_order
    except Exception:
        suite_order_obj = None
    if suite_order_obj and suite_order_obj.status == 'pending_payment':
        try:
            _activate_suite_service(suite_order_obj)
        except Exception as suite_err:
            _logger.error('Suite activation failed for order %s: %s', suite_order_obj.pk, suite_err)

    PortalActivity.objects.create(
        user=request.user,
        category='billing',
        title='Payment confirmed via Razorpay',
        description=f'Invoice {invoice.invoice_number} — {invoice.currency} {invoice.total} — Payment ID: {rz_payment_id}',
    )

    # Build final response with provisioning outcome
    order_after = getattr(invoice, 'order', None)
    provision_status = None
    provision_message = None
    if order_after and order_after.provision_response:
        prov = order_after.provision_response
        provision_status = prov.get('status', 'unknown')
        provision_message = prov.get('message', '')

    return JsonResponse({
        'ok': True,
        'invoice_number': invoice.invoice_number,
        'provision': provision_status or 'na',
        'provision_message': provision_message or '',
        'redirect': f'/portal/invoice/{invoice.id}/pay/',
    })


@csrf_exempt
@login_required(login_url='/login/')
def api_wallet_pay(request):
    """
    POST /api/payment/wallet/pay/
    Body: { "invoice_id": 7 }
    Pays an invoice using available chips and funds without launching Razorpay.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = _rjson.loads(request.body)
        inv_id = int(data.get('invoice_id', 0))
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)
        
    invoice = Invoice.objects.filter(id=inv_id, user=request.user).first()
    if not invoice:
        return JsonResponse({'error': 'Invoice not found'}, status=404)
    if invoice.status == 'paid':
        return JsonResponse({'error': 'Invoice is already paid'}, status=400)
        
    profile = CustomerProfile.objects.get_or_create(user=request.user)[0]
    
    with transaction.atomic():
        profile = CustomerProfile.objects.select_for_update().get(id=profile.id)
        chips_to_use, funds_to_deduct_inr, remaining_due = calculate_invoice_payment_split(invoice, profile)
        
        if remaining_due > 0:
            return JsonResponse({'error': 'Insufficient wallet balance to pay this invoice fully.'}, status=400)
            
        # Deduct balances
        if chips_to_use > 0:
            profile.balance_chips = max(0, profile.balance_chips - chips_to_use)
            ChipTransaction.objects.create(
                user=request.user,
                amount=-chips_to_use,
                transaction_type='purchase',
                description=f'Paid for invoice {invoice.invoice_number}'
            )
        if funds_to_deduct_inr > 0:
            profile.balance_funds = max(Decimal('0.00'), profile.balance_funds - funds_to_deduct_inr)
            FundTransaction.objects.create(
                user=request.user,
                amount=-funds_to_deduct_inr,
                transaction_type='purchase',
                description=f'Paid for invoice {invoice.invoice_number}'
            )
        profile.save()
        
        # Mark paid
        invoice.status    = 'paid'
        invoice.paid_date = timezone.localdate()
        invoice.save(update_fields=['status', 'paid_date'])
        
        # Trigger provisioning
        order = getattr(invoice, 'order', None)
        if order:
            order.status = 'provisioning'
            order.save(update_fields=['status'])
            try:
                _activate_service_after_provision(order, invoice=invoice)
            except Exception as prov_err:
                order.status = 'failed'
                order.provision_response = {'error': str(prov_err)}
                order.save(update_fields=['status', 'provision_response'])
                
        # Domain order
        domain_order = getattr(invoice, 'domain_order', None)
        if domain_order:
            domain_order.status = 'processing'
            domain_order.save(update_fields=['status'])
            
        # Professional Email
        try:
            email_order = invoice.email_order
        except Exception:
            email_order = None
        if email_order and email_order.status == 'pending_payment':
            email_order.status = 'provisioning'
            email_order.save(update_fields=['status'])
            try:
                _activate_email_service(email_order, invoice=invoice)
                email_order.status = 'active'
                email_order.provision_response = {'status': 'success'}
                email_order.save(update_fields=['status', 'provision_response'])
            except Exception as email_err:
                _logger.error('Email provisioning failed for order %s: %s', email_order.pk, email_err)
                email_order.status = 'failed'
                email_order.provision_response = {'error': str(email_err)}
                email_order.save(update_fields=['status', 'provision_response'])

        # SSL Order
        try:
            ssl_order = invoice.ssl_order
        except Exception:
            ssl_order = None
        if ssl_order and ssl_order.status == 'pending_payment':
            ssl_order.status = 'provisioning'
            ssl_order.save(update_fields=['status'])
            try:
                _activate_ssl_service(ssl_order, invoice=invoice)
                ssl_order.status = 'active'
                ssl_order.provision_response = {'status': 'success'}
                ssl_order.save(update_fields=['status', 'provision_response'])
            except Exception as ssl_err:
                _logger.error('SSL provisioning failed for order %s: %s', ssl_order.pk, ssl_err)
                ssl_order.status = 'failed'
                ssl_order.provision_response = {'error': str(ssl_err)}
                ssl_order.save(update_fields=['status', 'provision_response'])

        # Suite Order
        try:
            suite_order_obj = invoice.suite_order
        except Exception:
            suite_order_obj = None
        if suite_order_obj and suite_order_obj.status == 'pending_payment':
            try:
                _activate_suite_service(suite_order_obj)
            except Exception as suite_err:
                _logger.error('Suite activation failed for order %s: %s', suite_order_obj.pk, suite_err)

        PortalActivity.objects.create(
            user=request.user,
            category='billing',
            title='Paid invoice using wallet',
            description=f'Invoice {invoice.invoice_number} paid via wallet (Chips used: {chips_to_use}, Funds used: ₹{funds_to_deduct_inr})',
        )
                
    return JsonResponse({'success': True, 'message': 'Invoice paid successfully using wallet.'})


@login_required(login_url='/login/')
def wallet_deposit(request):
    """
    POST /portal/wallet/deposit/
    Creates a deposit invoice for the specified amount and redirects to pay page.
    """
    if request.method != 'POST':
        return redirect('/portal/')
        
    try:
        amount = Decimal(request.POST.get('amount', '0.00'))
    except Exception:
        messages.error(request, "Invalid deposit amount.")
        return redirect('/portal/')
        
    if amount < 10:
        messages.error(request, "Minimum deposit amount is ₹10.")
        return redirect('/portal/')
        
    cnt = Invoice.objects.filter(user=request.user).count()
    invoice = Invoice.objects.create(
        user=request.user,
        invoice_number=f'DEP-{request.user.id:04d}-{cnt + 1:03d}',
        description=f'Deposit Funds to Wallet — {amount} INR',
        status='unpaid',
        total=amount,
        currency='INR',
        due_date=timezone.localdate()
    )
    return redirect(f'/portal/invoice/{invoice.id}/pay/')


@login_required(login_url='/login/')
def wallet_buy_chips(request):
    """
    POST /portal/wallet/buy_chips/
    Creates a chips purchase invoice for the specified amount (INR) and redirects to pay page.
    """
    if request.method != 'POST':
        return redirect('/portal/')
        
    try:
        amount = Decimal(request.POST.get('amount', '0.00'))
    except Exception:
        messages.error(request, "Invalid chips purchase amount.")
        return redirect('/portal/')
        
    if amount < 10:
        messages.error(request, "Minimum purchase amount is ₹10.")
        return redirect('/portal/')
        
    from data.models import HostingPricingSettings
    pricing_settings = HostingPricingSettings.objects.first()
    credits_per_rupee = getattr(pricing_settings, 'credits_per_rupee', 100) or 100
    chips_qty = int(amount * credits_per_rupee)

    cnt = Invoice.objects.filter(user=request.user).count()
    invoice = Invoice.objects.create(
        user=request.user,
        invoice_number=f'CHP-{request.user.id:04d}-{cnt + 1:03d}',
        description=f'Purchase AI Chips — {chips_qty} Chips ({amount} INR)',
        status='unpaid',
        total=amount,
        currency='INR',
        due_date=timezone.localdate()
    )
    return redirect(f'/portal/invoice/{invoice.id}/pay/')

# ── API: Razorpay Webhook ─────────────────────────────────────────────────────

@csrf_exempt
def api_razorpay_webhook(request):
    """
    POST /api/payment/razorpay/webhook/
    Handles async webhook events from Razorpay dashboard.
    Events handled: payment.captured, payment.failed
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    config = RazorpayConfig.get()

    # Verify webhook signature if secret is set
    if config.webhook_secret:
        received_sig = request.headers.get('X-Razorpay-Signature', '')
        expected_sig = hmac.new(
            config.webhook_secret.encode('utf-8'),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, received_sig):
            return JsonResponse({'error': 'Invalid webhook signature'}, status=400)

    try:
        payload = _rjson.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = payload.get('event', '')
    entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    rz_order_id   = entity.get('order_id', '')
    rz_payment_id = entity.get('id', '')

    rp = RazorpayPayment.objects.filter(razorpay_order_id=rz_order_id).first()
    if not rp:
        return JsonResponse({'ok': True, 'note': 'Payment record not found — possibly manual order'})

    if event == 'payment.captured':
        rp.razorpay_payment_id = rz_payment_id
        rp.status = 'captured'
        rp.save(update_fields=['razorpay_payment_id', 'status'])

        # Mark invoice paid if not already
        if rp.invoice and rp.invoice.status != 'paid':
            process_paid_invoice(rp.invoice, rp.user)

            # ── AUTO-PROVISION: trigger hosting account creation ──────────────
            invoice_obj = rp.invoice
            order_obj = getattr(invoice_obj, 'order', None)
            if order_obj and hasattr(order_obj, 'service') and order_obj.service:
                svc = order_obj.service
                if svc.product_type in ('Shared Hosting', 'WordPress Hosting', 'Reseller Hosting'):
                    try:
                        import threading
                        def _provision_bg():
                            _activate_service_after_provision(order_obj, invoice=invoice_obj)
                        threading.Thread(target=_provision_bg, daemon=True).start()
                        _logger.info('Razorpay webhook: provisioning started for domain %s', svc.domain)
                    except Exception as exc:
                        _logger.error('Razorpay webhook: provisioning error for %s: %s', svc.domain, exc)

    elif event == 'payment.failed':
        rp.status = 'failed'
        rp.error_description = entity.get('error_description', 'unknown')
        rp.save(update_fields=['status', 'error_description'])

    return JsonResponse({'ok': True, 'event': event})

def super_admin_notifications(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied
        
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == "send_panel_notification":
            title = request.POST.get('title', 'VoidPanel Update')
            text = request.POST.get('text', '')
            if not text:
                messages.error(request, 'Notification text is required.')
            else:
                photo = request.FILES.get('photo')
                msg = Message(title=title, text=text)
                if photo:
                    msg.photo = photo
                msg.save()
                messages.success(request, 'Notification broadcasted to all VoidPanel instances successfully.')
            return redirect('/super-admin/notifications/')
            
        elif action == "delete_panel_notification":
            msg_id = request.POST.get('notification_id')
            try:
                Message.objects.get(id=msg_id).delete()
                messages.success(request, 'Notification deleted.')
            except Message.DoesNotExist:
                messages.error(request, 'Notification not found.')
            return redirect('/super-admin/notifications/')
            
        elif action == "email_all_users":
            subject = request.POST.get('subject', '')
            body = request.POST.get('body', '')
            if not subject or not body:
                messages.error(request, 'Subject and message body are required to email all users.')
            else:
                from django.contrib.auth import get_user_model
                users = get_user_model().objects.filter(is_active=True)
                recipient_list = [u.email for u in users if u.email]
                messages.success(request, f'Email broadcast queued for {len(recipient_list)} users.')
            return redirect('/super-admin/notifications/')

    context = _build_super_admin_context('notifications')
    context['notifications'] = Message.objects.all().order_by('-date')
    return render(request, 'super_admin_notifications.html', context)

@login_required
def super_admin_ai_keys(request):
    """Super admin view to manage AI provider API keys from the portal UI."""
    if not request.user.is_superuser:
        return redirect('/')

    config = AiProviderConfig.get()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'save':
            config.active_provider   = request.POST.get('active_provider', config.active_provider)
            config.tokens_per_request = int(request.POST.get('tokens_per_request', config.tokens_per_request))

            # Only update keys if a non-empty value was submitted (avoid clearing on partial saves)
            gemini_key = request.POST.get('gemini_api_key', '').strip()
            if gemini_key:
                config.gemini_api_key = gemini_key
            # Gemini model: use custom text input if "custom" was selected
            gemini_model_raw = request.POST.get('gemini_model', config.gemini_model).strip()
            if gemini_model_raw == 'custom':
                gemini_model_raw = request.POST.get('gemini_model_custom', config.gemini_model).strip()
            config.gemini_model = gemini_model_raw or config.gemini_model

            claude_key = request.POST.get('claude_api_key', '').strip()
            if claude_key:
                config.claude_api_key = claude_key
            # Claude model: use custom text input if "custom" was selected
            claude_model_raw = request.POST.get('claude_model', config.claude_model).strip()
            if claude_model_raw == 'custom':
                claude_model_raw = request.POST.get('claude_model_custom', config.claude_model).strip()
            config.claude_model = claude_model_raw or config.claude_model

            openai_key = request.POST.get('openai_api_key', '').strip()
            if openai_key:
                config.openai_api_key = openai_key
            # OpenAI model: use custom text input if "custom" was selected
            openai_model_raw = request.POST.get('openai_model', config.openai_model).strip()
            if openai_model_raw == 'custom':
                openai_model_raw = request.POST.get('openai_model_custom', config.openai_model).strip()
            config.openai_model = openai_model_raw or config.openai_model

            huggingface_key = request.POST.get('huggingface_api_key', '').strip()
            if huggingface_key:
                config.huggingface_api_key = huggingface_key
            config.huggingface_model = request.POST.get('huggingface_model', config.huggingface_model).strip() or config.huggingface_model

            config.save()
            messages.success(request, 'AI provider configuration saved successfully.')
        elif action == 'clear_gemini':
            config.gemini_api_key = ''
            config.save()
            messages.warning(request, 'Gemini API key cleared.')
        elif action == 'clear_claude':
            config.claude_api_key = ''
            config.save()
            messages.warning(request, 'Claude API key cleared.')
        elif action == 'clear_openai':
            config.openai_api_key = ''
            config.save()
            messages.warning(request, 'OpenAI API key cleared.')
        elif action == 'clear_huggingface':
            config.huggingface_api_key = ''
            config.save()
            messages.warning(request, 'Hugging Face user access token cleared.')

        return redirect('/super-admin/ai-keys/')

    context = _build_super_admin_context('ai_keys')
    context['ai_config'] = config
    return render(request, 'super_admin_ai_keys.html', context)


@login_required(login_url='/login/')
def api_admin_server_test(request):
    """
    POST /api/admin/server/test/
    Body: { "url": "http://...", "api_key": "..." }
    Pings the VoidPanel backend API to verify connectivity before saving a server node.
    Returns: { "ok": true/false, "version": "...", "latency_ms": 42, "error": "..." }
    """
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    try:
        import json as _json
        data = _json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON body'}, status=400)

    url = data.get('url', '').strip().rstrip('/')
    api_key = data.get('api_key', '').strip()

    if not url or not api_key:
        return JsonResponse({'ok': False, 'error': 'URL and API key are required'})

    import requests as _req
    import time as _time

    start = _time.time()
    try:
        resp = _req.get(
            f'{url}/api/license/validate/',
            headers={'X-VoidPanel-Key': api_key},
            timeout=10,
        )
        latency_ms = int((_time.time() - start) * 1000)
        if resp.status_code == 200:
            try:
                rdata = resp.json()
            except Exception:
                rdata = {}
            return JsonResponse({
                'ok': True,
                'latency_ms': latency_ms,
                'version': rdata.get('version', 'unknown'),
                'message': 'Server connected successfully',
            })
        elif resp.status_code == 403:
            return JsonResponse({'ok': False, 'error': 'Invalid API key — server rejected the request (403 Forbidden)'})
        else:
            return JsonResponse({'ok': False, 'error': f'Server returned HTTP {resp.status_code}'})
    except _req.exceptions.ConnectionError:
        return JsonResponse({'ok': False, 'error': 'Connection refused — check the URL and ensure the VoidPanel backend is running'})
    except _req.exceptions.Timeout:
        return JsonResponse({'ok': False, 'error': 'Connection timed out after 10 seconds'})
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)})

# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT PORTAL — SERVICE DETAIL PAGE & SSO AUTO-LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@login_required(login_url='/login/')
def portal_service_detail(request, service_id):
    """
    Full service detail page — shows credentials, shortcuts, and SSO login button.
    URL: /portal/service/<service_id>/
    """
    service = get_object_or_404(HostingService, id=service_id, user=request.user)

    # Determine shortcuts deep-links based on panel_base_url
    panel_base = service.panel_base_url

    shortcuts = [
        {'icon': 'fa-folder-open',   'label': 'File Manager',     'path': '/control/filemanager/',                                    'color': '#6366f1', 'desc': 'Browse & edit files'},
        {'icon': 'fa-lock',          'label': 'SSL Certificates', 'path': '/control/runssl/' + service.domain + '/',                  'color': '#10b981', 'desc': 'Manage SSL/TLS'},
        {'icon': 'fa-wordpress',     'label': 'WordPress',        'path': '/control/app-installer/' + service.domain + '/',           'color': '#3b82f6', 'desc': 'One-click installer'},
        {'icon': 'fa-envelope',      'label': 'Email Accounts',   'path': '/control/listemail/' + service.domain + '/',              'color': '#f59e0b', 'desc': 'Manage email'},
        {'icon': 'fa-database',      'label': 'Databases',        'path': '/control/fulldbwizard/' + service.domain + '/',            'color': '#8b5cf6', 'desc': 'MySQL databases'},
        {'icon': 'fa-network-wired', 'label': 'FTP Access',       'path': '/control/ftp/' + service.domain + '/',                    'color': '#06b6d4', 'desc': 'FTP accounts'},
        {'icon': 'fa-globe',         'label': 'DNS Manager',      'path': '/control/eadns/?domain=' + service.domain,                'color': '#ec4899', 'desc': 'Manage DNS records'},
        {'icon': 'fa-hard-drive',    'label': 'Backups',          'path': '/control/backup/' + service.domain + '/',                 'color': '#f97316', 'desc': 'Download & restore'},
        {'icon': 'fa-chart-line',    'label': 'Analytics',        'path': '/control/analytics/' + service.domain + '/',              'color': '#14b8a6', 'desc': 'Traffic stats'},
        {'icon': 'fa-terminal',      'label': 'SSH Terminal',     'path': '/control/terminal/',                                       'color': '#64748b', 'desc': 'Browser terminal'},
    ]

    # Build SSO shortcut URLs (each goes through the auto-login redirect)
    import urllib.parse
    for sc in shortcuts:
        sc['url'] = f'/portal/service/{service_id}/login/?next={urllib.parse.quote(sc["path"])}'

    context = {
        'service':   service,
        'shortcuts': shortcuts,
        'panel_base': panel_base,
    }
    return render(request, 'portal_service_detail.html', context)


@login_required(login_url='/login/')
def portal_service_autologin(request, service_id):
    """
    Generates a one-time SSO token and redirects to the VoidPanel panel.
    URL: /portal/service/<service_id>/login/?next=/filemanager/
    """
    service = get_object_or_404(HostingService, id=service_id, user=request.user)

    if not service.panel_base_url:
        messages.error(request, 'No panel URL configured for this service. Contact support.')
        return redirect(f'/portal/service/{service_id}/')

    # For reseller services, default to the reseller dashboard
    default_next = '/control/reseller/' if getattr(service, 'is_reseller', False) else '/control/'
    next_path = request.GET.get('next', default_next)
    # Safety: only allow relative paths
    if not next_path.startswith('/'):
        next_path = default_next

    import urllib.parse
    token = service.generate_sso_token()
    panel_url = service.panel_base_url.rstrip('/')
    next_enc = urllib.parse.quote(next_path)

    # Normalize scheme: port 8080 is HTTP, port 8082 is HTTPS
    # Old provisioner stored https://IP:8080 which browsers reject (no SSL on 8080)
    if ':8080' in panel_url and panel_url.startswith('https://'):
        panel_url = panel_url.replace('https://', 'http://', 1)

    redirect_url = f'{panel_url}/autologin/?token={token}&domain={service.domain}&next={next_enc}'
    return redirect(redirect_url)


@login_required(login_url='/login/')
def portal_service_manage(request, service_id):
    """
    AJAX/POST endpoint for service actions: unsuspend, request backup, etc.
    """
    service = get_object_or_404(HostingService, id=service_id, user=request.user)
    action = request.POST.get('action', '')

    if action == 'request_backup':
        PortalActivity.objects.create(
            user=request.user,
            category='account',
            title=f'Backup requested: {service.domain}',
            description='Manual backup requested from client portal.',
        )
        return JsonResponse({'ok': True, 'message': 'Backup request submitted. You will receive an email when ready.'})

    return JsonResponse({'ok': False, 'message': 'Unknown action'}, status=400)


# ── SSO Token Validation API (called by the VoidPanel panel server) ───────────

from django.views.decorators.csrf import csrf_exempt as _csrf_exempt

@_csrf_exempt
def api_sso_validate(request):
    """
    GET /api/sso/validate/?token=TOKEN&domain=DOMAIN
    Called by the VoidPanel panel backend to validate a one-time SSO token.
    Returns 200 with {valid: true, username: '...', panel_username: '...'} on success.
    """
    token  = request.GET.get('token', '').strip()
    domain = request.GET.get('domain', '').strip()

    if not token or not domain:
        return JsonResponse({'valid': False, 'error': 'token and domain required'}, status=400)

    service = HostingService.objects.filter(domain=domain).first()
    if not service:
        return JsonResponse({'valid': False, 'error': 'Domain not found'}, status=404)

    if service.validate_sso_token(token):
        return JsonResponse({
            'valid': True,
            'domain': service.domain,
            'username': service.user.username,
            'panel_username': service.panel_username or service.user.username,
            'email': service.user.email,
            'service_id': service.id,
        })
    else:
        return JsonResponse({'valid': False, 'error': 'Invalid or expired token'}, status=403)


# ══════════════════════════════════════════════════════════════════════════════
#  SUPER ADMIN — AUTO-SUSPEND CONTROL
# ══════════════════════════════════════════════════════════════════════════════

@login_required(login_url='/login/')
def super_admin_auto_suspend(request):
    """
    Super admin page to control overdue auto-suspension.
    URL: /super-admin/auto-suspend/
    """
    denied = _super_admin_guard(request)
    if denied:
        return denied

    settings_obj = AutoSuspendSettings.get()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_settings':
            settings_obj.enabled              = request.POST.get('enabled') == '1'
            settings_obj.overdue_days         = int(request.POST.get('overdue_days', 15))
            settings_obj.warning_days         = int(request.POST.get('warning_days', 10))
            settings_obj.send_warning_email   = request.POST.get('send_warning_email') == '1'
            settings_obj.send_suspension_email = request.POST.get('send_suspension_email') == '1'
            settings_obj.updated_by = request.user.username
            settings_obj.save()
            messages.success(request, 'Auto-suspend settings updated successfully.')
            return redirect('/super-admin/auto-suspend/')

        elif action == 'manual_suspend':
            svc_id = request.POST.get('service_id')
            svc = HostingService.objects.filter(id=svc_id).first()
            if svc:
                _call_panel_suspend(svc)
                svc.status = 'suspended'
                svc.save(update_fields=['status'])
                PortalActivity.objects.create(
                    user=svc.user,
                    category='billing',
                    title=f'Service manually suspended: {svc.domain}',
                    description=f'Manually suspended by superadmin {request.user.username}.',
                )
                messages.success(request, f'Service {svc.domain} suspended.')
            return redirect('/super-admin/auto-suspend/')

        elif action == 'manual_unsuspend':
            svc_id = request.POST.get('service_id')
            svc = HostingService.objects.filter(id=svc_id).first()
            if svc:
                _call_panel_unsuspend(svc)
                svc.status = 'active'
                svc.save(update_fields=['status'])
                PortalActivity.objects.create(
                    user=svc.user,
                    category='billing',
                    title=f'Service reactivated: {svc.domain}',
                    description=f'Manually unsuspended by superadmin {request.user.username}.',
                )
                messages.success(request, f'Service {svc.domain} reactivated.')
            return redirect('/super-admin/auto-suspend/')

    from django.utils import timezone as tz
    today = tz.localdate()

    # Build overdue report
    overdue_services = []
    for svc in HostingService.objects.select_related('user').filter(status__in=['active', 'suspended']):
        overdue_inv = svc.user.invoices.filter(
            status__in=['overdue', 'unpaid'],
            due_date__lt=today,
        ).order_by('due_date').first()
        if overdue_inv:
            days = (today - overdue_inv.due_date).days
            overdue_services.append({
                'service': svc,
                'invoice': overdue_inv,
                'days_overdue': days,
                'will_suspend': days >= settings_obj.overdue_days,
            })

    overdue_services.sort(key=lambda x: x['days_overdue'], reverse=True)

    ctx = _build_super_admin_context('auto_suspend')
    ctx.update({
        'settings':         settings_obj,
        'overdue_services': overdue_services,
    })
    return render(request, 'super_admin_auto_suspend.html', ctx)



def _call_panel_suspend(service):
    """Call VoidPanel API to suspend the hosting account."""
    import requests as _rq
    panel = service.panel_base_url
    if not panel:
        return
    try:
        server = service.server
        api_key = server.api_key if server else ''
        _rq.post(
            f'{panel}/api/v2/accounts/suspend/',
            json={'domain': service.domain},
            headers={'X-API-Token': api_key},
            timeout=15,
        )
    except Exception as exc:
        _logger.error('_call_panel_suspend error for %s: %s', service.domain, exc)


def _call_panel_unsuspend(service):
    """Call VoidPanel API to unsuspend the hosting account."""
    import requests as _rq
    panel = service.panel_base_url
    if not panel:
        return
    try:
        server = service.server
        api_key = server.api_key if server else ''
        _rq.post(
            f'{panel}/api/v2/accounts/unsuspend/',
            json={'domain': service.domain},
            headers={'X-API-Token': api_key},
            timeout=15,
        )
    except Exception as exc:
        _logger.error('_call_panel_unsuspend error for %s: %s', service.domain, exc)


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL EMAIL — Provisioner + Portal + Admin
# ═══════════════════════════════════════════════════════════════════════════════

def _send_email_welcome(email_service, primary_mailbox, password):
    """Send welcome email with IMAP/SMTP/Webmail settings to the customer."""
    try:
        from django.core.mail import EmailMessage as DjangoEmail
        from django.conf import settings as djsettings
        server_url = email_service.server.url if email_service.server else 'http://panel'
        if email_service.server and email_service.server.login_url:
            server_url = email_service.server.login_url
        panel_host = server_url.replace('http://', '').replace('https://', '').split('/')[0].split(':')[0]
        webmail    = email_service.webmail_url or f'http://{panel_host}:9002'
        html = f"""
<div style="font-family:'Inter',Arial,sans-serif;max-width:580px;margin:auto;background:#0f172a;color:#e2e8f0;border-radius:16px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#0ea5e9,#7c3aed);padding:36px 32px;text-align:center;">
    <div style="font-size:2rem;">📧</div>
    <h1 style="margin:8px 0 0;font-size:1.6rem;color:#fff;">Your Professional Email is Ready!</h1>
    <p style="margin:6px 0 0;color:rgba(255,255,255,.8);">{email_service.domain}</p>
  </div>
  <div style="padding:28px 32px;">
    <p>Hi {email_service.user.get_full_name() or email_service.user.username},</p>
    <p>Your professional email hosting for <strong>{email_service.domain}</strong> is now active. Here are your details:</p>
    <div style="background:#1e293b;border-radius:12px;padding:20px 24px;margin:20px 0;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="color:#94a3b8;padding:6px 0;width:140px;">Email Address</td><td style="font-weight:700;">{primary_mailbox}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Password</td><td style="font-weight:700;color:#4ade80;">{password}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Webmail</td><td><a href="{webmail}" style="color:#38bdf8;">{webmail}</a></td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">IMAP Server</td><td style="font-weight:700;">{panel_host}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">IMAP Port</td><td>993 (SSL)</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">SMTP Server</td><td style="font-weight:700;">{panel_host}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">SMTP Port</td><td>587 (STARTTLS) / 465 (SSL)</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Plan</td><td>{email_service.max_mailboxes} Mailboxes</td></tr>
      </table>
    </div>
    <p style="color:#94a3b8;font-size:.85rem;">Manage your mailboxes from your <a href="https://voidpanel.com/portal/" style="color:#7c3aed;">client portal</a>. Add more emails, reset passwords, and open Webmail all from one place.</p>
  </div>
  <div style="background:#0f172a;padding:16px 32px;border-top:1px solid rgba(255,255,255,.06);text-align:center;font-size:.75rem;color:#475569;">
    VoidPanel — Professional Email Hosting
  </div>
</div>"""
        msg = DjangoEmail(
            subject=f'[VoidPanel] Your Professional Email is Active — {email_service.domain}',
            body=html,
            from_email=djsettings.DEFAULT_FROM_EMAIL,
            to=[email_service.user.email],
        )
        msg.content_subtype = 'html'
        msg.send(fail_silently=True)
    except Exception as exc:
        _logger.error('Email welcome send failed for %s: %s', email_service.domain, exc)


def _activate_email_service(order, invoice=None):
    """
    Called after payment for a Professional Email plan.
    Creates the EmailService record, provisions the primary mailbox via API,
    and sends a welcome email.
    """
    import requests as _rq, secrets as _sec
    from django.utils import timezone
    from datetime import timedelta

    service_name = getattr(order, 'service_name', 'Professional Email')
    domain       = getattr(order, 'domain', '') or ''
    plan         = getattr(order, 'email_plan', None)

    if not domain:
        _logger.error('_activate_email_service: no domain on order %s', order.pk)
        return

    server = plan.server if plan and plan.server else VoidPanelServer.objects.filter(is_active=True).first()
    if not server:
        _logger.error('_activate_email_service: no server available')
        return

    # Build panel + webmail URLs
    panel_host  = server.url.replace('http://', '').replace('https://', '').split(':')[0]
    panel_url   = server.url.rstrip('/')
    webmail_url = f'http://{panel_host}:9002'

    email_svc = EmailService.objects.create(
        user          = order.user,
        plan_name     = plan.name if plan else 'Professional Email',
        server        = server,
        domain        = domain,
        status        = 'pending',
        billing_cycle = getattr(order, 'billing_cycle', 'monthly'),
        monthly_price = getattr(order, 'price', plan.monthly_price if plan else 0),
        next_due_date = (timezone.now() + timedelta(days=30)).date(),
        panel_url     = panel_url,
        webmail_url   = webmail_url,
        max_mailboxes = plan.max_mailboxes if plan else 5,
    )

    # Create primary mailbox: admin@domain.com
    primary_email = f'admin@{domain}'
    primary_pass  = _sec.token_urlsafe(12)

    try:
        resp = _rq.post(
            f'{panel_url}/api/v2/email/create/',
            json={'domain': domain, 'email': primary_email, 'password': primary_pass},
            headers={'X-API-Token': server.api_key},
            timeout=20,
        )
        data = resp.json()
        if data.get('status') == 'success':
            EmailMailbox.objects.create(
                service       = email_svc,
                email_address = primary_email,
                password      = primary_pass,
            )
            email_svc.status = 'active'
            email_svc.save(update_fields=['status'])
            PortalActivity.objects.create(
                user        = order.user,
                category    = 'account',
                title       = f'Professional Email activated: {domain}',
                description = f'Primary mailbox {primary_email} created on {server.name}',
            )
            _send_email_welcome(email_svc, primary_email, primary_pass)
        else:
            _logger.error('Email provision API error for %s: %s', domain, data.get('message'))
    except Exception as exc:
        _logger.error('Email provision failed for %s: %s', domain, exc)


# ── Public Pricing Page ───────────────────────────────────────────────────────




def professional_email_page(request):
    """Public landing + pricing page for Professional Email plans."""
    default_plans = [get_static_email_plan(i) for i in (1, 2, 3)]
    plans = [p for p in default_plans if p and p.get('is_active', True)]
    try:
        from data.models import EmailPlan
        custom_db_plans = EmailPlan.objects.filter(is_active=True).order_by('sort_order', 'monthly_price')
        for db_plan in custom_db_plans:
            wrapper = get_static_email_plan(f"custom_{db_plan.pk}")
            if wrapper:
                plans.append(wrapper)
    except Exception:
        pass
    return render(request, 'professional_email.html', {'plans': plans})


# ── Email Order: Step 1 — Configure (collect domain) ─────────────────────────

@login_required(login_url='/login/')
def email_configure(request, plan_id):
    """
    Step 1: Customer picks a plan → enters their domain → submits.
    On POST, stores plan + domain in session and redirects to checkout.
    """
    plan = get_static_email_plan(plan_id)
    if not plan:
        raise Http404("Plan not found")

    if request.method == 'POST':
        domain = request.POST.get('domain', '').strip().lower()
        billing_cycle = request.POST.get('billing_cycle', 'monthly')

        # Basic domain validation
        import re
        if not domain or not re.match(r'^[a-z0-9][a-z0-9\-\.]{1,60}\.[a-z]{2,}$', domain):
            messages.error(request, 'Please enter a valid domain name (e.g. yourcompany.com)')
            return render(request, 'email_configure.html', {'plan': plan})

        # Check domain not already on an active email service for this user
        if EmailService.objects.filter(user=request.user, domain=domain,
                                       status__in=['active', 'pending']).exists():
            messages.error(request, f'You already have an active email service for {domain}.')
            return render(request, 'email_configure.html', {'plan': plan})

        # Store in session
        request.session['email_order'] = {
            'plan_id':       plan['id'],
            'domain':        domain,
            'billing_cycle': billing_cycle,
        }
        return redirect('email_checkout')

    return render(request, 'email_configure.html', {'plan': plan})


# ── Email Order: Step 2 — Checkout (create Invoice + EmailOrder) ──────────────

@login_required(login_url='/login/')
def email_checkout(request):
    """
    Step 2: Creates an Invoice and EmailOrder, then redirects to the payment page.
    Session key 'email_order' must be set by email_configure.
    """
    session_data = request.session.get('email_order')
    if not session_data:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('professional_email')

    plan_id       = session_data.get('plan_id')
    domain        = session_data.get('domain', '').strip()
    billing_cycle = session_data.get('billing_cycle', 'monthly')

    plan = get_static_email_plan(plan_id)
    if not plan:
        messages.error(request, 'Plan not found.')
        return redirect('professional_email')

    # Price based on billing cycle
    if billing_cycle == 'quarterly':
        price = plan['monthly_price'] * 3
        cycle_label = 'Quarterly'
    elif billing_cycle == 'annually':
        price = plan['monthly_price'] * 12
        cycle_label = 'Annual'
    else:
        price = plan['monthly_price']
        cycle_label = 'Monthly'

    with transaction.atomic():
        inv_count = Invoice.objects.filter(user=request.user).count()
        invoice = Invoice.objects.create(
            user           = request.user,
            invoice_number = f'VP-{request.user.id:04d}-{inv_count + 1:03d}',
            status         = 'unpaid',
            total          = price,
            due_date       = (timezone.now() + timedelta(days=3)).date(),
            description    = f"{plan['name']} Professional Email — {domain} ({cycle_label})",
        )
        email_order = EmailOrder.objects.create(
            user          = request.user,
            invoice       = invoice,
            domain        = domain,
            billing_cycle = billing_cycle,
            price         = price,
            status        = 'pending_payment',
            plan_name     = plan['name'],
        )
        PortalActivity.objects.create(
            user        = request.user,
            category    = 'billing',
            title       = f'Email order created: {domain}',
            description = f"Plan: {plan['name']} | {cycle_label} | ₹{price}",
        )

    # Clear session
    request.session.pop('email_order', None)

    return redirect(f'/portal/invoice/{invoice.id}/pay/')

# ── Client Portal: Email Manager ─────────────────────────────────────────────

@login_required(login_url='/login/')
def portal_manage_email(request, service_id):
    """
    Dedicated email management portal for a Professional Email service.
    Lists mailboxes, shows IMAP/SMTP info, quota, Webmail links.
    No full panel access.
    """
    import requests as _rq
    email_svc = get_object_or_404(EmailService, id=service_id, user=request.user)

    # Fetch live mailbox list from panel
    live_mailboxes = []
    api_error = None
    if email_svc.server:
        try:
            resp = _rq.get(
                f"{email_svc.server.url.rstrip('/')}/api/v2/email/list/",
                params={'domain': email_svc.domain},
                headers={'X-API-Token': email_svc.server.api_key},
                timeout=8,
            )
            data = resp.json()
            if data.get('status') == 'success':
                live_emails = {e['email'] for e in data.get('data', {}).get('emails', [])}
                # Merge with DB records to show passwords
                db_mailboxes = {m.email_address: m for m in email_svc.mailboxes.all()}
                for addr in live_emails:
                    mb = db_mailboxes.get(addr)
                    live_mailboxes.append({
                        'email':    addr,
                        'password': mb.password if mb else '••••••••',
                        'id':       mb.pk if mb else None,
                    })
                # Also show DB records not yet on server (installing)
                for addr, mb in db_mailboxes.items():
                    if addr not in live_emails:
                        live_mailboxes.append({
                            'email':    addr,
                            'password': mb.password,
                            'id':       mb.pk,
                            'pending':  True,
                        })
        except Exception as exc:
            api_error = str(exc)
            live_mailboxes = [
                {'email': m.email_address, 'password': m.password, 'id': m.pk}
                for m in email_svc.mailboxes.all()
            ]

    panel_host = ''
    webmail_url = ''
    if email_svc.server:
        source_url = email_svc.server.login_url if email_svc.server.login_url else email_svc.server.url
        panel_host = source_url.replace('http://', '').replace('https://', '').split('/')[0].split(':')[0]
        webmail_url = f"http://{panel_host}:9002"
    else:
        webmail_url = email_svc.webmail_url

    ctx = {
        'email_svc':       email_svc,
        'live_mailboxes':  live_mailboxes,
        'api_error':       api_error,
        'panel_host':      panel_host,
        'webmail_url':     webmail_url,
        'quota_pct':       email_svc.quota_pct,
    }
    return render(request, 'portal_email_manager.html', ctx)


@login_required(login_url='/login/')
def portal_email_action(request, service_id):
    """
    AJAX endpoint for email mailbox management actions.
    POST JSON: {action: 'add'|'delete'|'change_password', email, password, new_password}
    """
    import requests as _rq
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    email_svc = get_object_or_404(EmailService, id=service_id, user=request.user)
    if not email_svc.server:
        return JsonResponse({'status': 'error', 'message': 'No server assigned to this service'}, status=400)

    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST.dict()

    action   = body.get('action', '').strip()
    api_base = email_svc.server.url.rstrip('/')
    api_key  = email_svc.server.api_key
    headers  = {'X-API-Token': api_key}

    # ── Add Mailbox ───────────────────────────────────────────────────────────
    if action == 'add':
        # Quota check
        if email_svc.mailbox_count >= email_svc.max_mailboxes:
            return JsonResponse({
                'status': 'error',
                'message': f'Quota reached: your plan allows {email_svc.max_mailboxes} mailboxes.'
            }, status=400)

        local  = body.get('local', '').strip().lower()
        passwd = body.get('password', '').strip()
        if not local or not passwd:
            return JsonResponse({'status': 'error', 'message': 'Email local part and password are required'}, status=400)
        if len(passwd) < 8:
            return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters'}, status=400)

        full_email = f'{local}@{email_svc.domain}'

        # Check not already exists
        if EmailMailbox.objects.filter(email_address=full_email).exists():
            return JsonResponse({'status': 'error', 'message': f'{full_email} already exists'}, status=409)

        try:
            resp = _rq.post(
                f'{api_base}/api/v2/email/create/',
                json={'domain': email_svc.domain, 'email': full_email, 'password': passwd},
                headers=headers, timeout=20,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            EmailMailbox.objects.create(
                service=email_svc, email_address=full_email, password=passwd
            )
            PortalActivity.objects.create(
                user=request.user, category='account',
                title=f'Mailbox created: {full_email}',
                description=f'Added via client portal for {email_svc.domain}',
            )
            return JsonResponse({'status': 'success', 'message': f'{full_email} created successfully!',
                                 'email': full_email})
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Create failed')}, status=400)

    # ── Delete Mailbox ────────────────────────────────────────────────────────
    elif action == 'delete':
        email_addr = body.get('email', '').strip()
        if not email_addr or not email_addr.endswith(f'@{email_svc.domain}'):
            return JsonResponse({'status': 'error', 'message': 'Invalid email address'}, status=400)

        try:
            resp = _rq.post(
                f'{api_base}/api/v2/email/delete/',
                json={'domain': email_svc.domain, 'email': email_addr},
                headers=headers, timeout=15,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            EmailMailbox.objects.filter(service=email_svc, email_address=email_addr).delete()
            PortalActivity.objects.create(
                user=request.user, category='account',
                title=f'Mailbox deleted: {email_addr}',
                description='Removed via client portal.',
            )
            return JsonResponse({'status': 'success', 'message': f'{email_addr} deleted.'})
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Delete failed')}, status=400)

    # ── Change Password ───────────────────────────────────────────────────────
    elif action == 'change_password':
        email_addr = body.get('email', '').strip()
        new_pass   = body.get('new_password', '').strip()
        if not email_addr or not new_pass:
            return JsonResponse({'status': 'error', 'message': 'Email and new password are required'}, status=400)
        if len(new_pass) < 8:
            return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters'}, status=400)
        if not email_addr.endswith(f'@{email_svc.domain}'):
            return JsonResponse({'status': 'error', 'message': 'Invalid email address'}, status=400)

        try:
            resp = _rq.post(
                f'{api_base}/api/v2/email/change-password/',
                json={'domain': email_svc.domain, 'email': email_addr, 'password': new_pass},
                headers=headers, timeout=15,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            mb = EmailMailbox.objects.filter(service=email_svc, email_address=email_addr).first()
            if mb:
                mb.password = new_pass
                mb.save(update_fields=['password'])
            PortalActivity.objects.create(
                user=request.user, category='account',
                title=f'Mailbox password changed: {email_addr}',
                description='Password reset via client portal.',
            )
            return JsonResponse({'status': 'success', 'message': f'Password updated for {email_addr}'})
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Password change failed')}, status=400)

    return JsonResponse({'status': 'error', 'message': f'Unknown action: {action}'}, status=400)


# ── Super Admin: Email Plans ──────────────────────────────────────────────────

@login_required(login_url='/login/')
def super_admin_email_plans(request):
    """Superadmin page to manage Professional Email plans — static (editable via override) + custom (DB-backed)."""
    denied = _super_admin_guard(request)
    if denied:
        return denied

    if request.method == 'POST':
        action  = request.POST.get('action', '')
        plan_id = request.POST.get('plan_id')

        # ── Static plan overrides (IDs 1–3) ────────────────────────────────
        if action == 'edit_email_plan' and plan_id:
            try:
                pid = int(plan_id)
                ov, _ = EmailPlanOverride.objects.get_or_create(plan_id=pid)
                ov.name                   = request.POST.get('name', '').strip() or None
                ov.slug                   = request.POST.get('slug', '').strip() or None
                ov.short_description      = request.POST.get('short_description', '').strip() or None
                raw_price                 = request.POST.get('monthly_price', '')
                ov.monthly_price          = Decimal(raw_price) if raw_price else None
                raw_mb                    = request.POST.get('max_mailboxes', '')
                ov.max_mailboxes          = int(raw_mb) if raw_mb else None
                raw_sg                    = request.POST.get('storage_per_mailbox_gb', '')
                ov.storage_per_mailbox_gb = int(raw_sg) if raw_sg else None
                raw_so                    = request.POST.get('sort_order', '')
                ov.sort_order             = int(raw_so) if raw_so else None
                ov.is_featured            = 'is_featured' in request.POST
                ov.is_active              = 'is_active' in request.POST
                ov.save()
                messages.success(request, f"Email Plan #{pid} updated.")
            except Exception as exc:
                messages.error(request, f"Error saving plan: {exc}")

        elif action == 'toggle_email_plan' and plan_id:
            try:
                pid = int(plan_id)
                ov, _ = EmailPlanOverride.objects.get_or_create(plan_id=pid)
                ov.is_active = not ov.is_active
                ov.save()
                messages.success(request, f"Email Plan #{pid} {'activated' if ov.is_active else 'deactivated'}.")
            except Exception as exc:
                messages.error(request, f"Toggle failed: {exc}")

        elif action == 'reset_email_plan' and plan_id:
            try:
                EmailPlanOverride.objects.filter(plan_id=int(plan_id)).delete()
                messages.success(request, f"Email Plan #{plan_id} reset to defaults.")
            except Exception as exc:
                messages.error(request, f"Reset failed: {exc}")

        # ── Custom plan CRUD ────────────────────────────────────────────────
        elif action == 'create_email_plan':
            try:
                import re, uuid
                name = request.POST.get('name', '').strip()
                if not name:
                    raise ValueError("Plan name is required.")
                slug = request.POST.get('slug', '').strip()
                if not slug:
                    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                # Ensure uniqueness
                if EmailPlan.objects.filter(slug=slug).exists():
                    slug = f"{slug}-{uuid.uuid4().hex[:4]}"
                ep = EmailPlan(
                    name                  = name,
                    slug                  = slug,
                    short_description     = request.POST.get('short_description', '').strip(),
                    monthly_price         = Decimal(request.POST.get('monthly_price') or '0'),
                    max_mailboxes         = int(request.POST.get('max_mailboxes') or 5),
                    storage_per_mailbox_gb = int(request.POST.get('storage_per_mailbox_gb') or 5),
                    sort_order            = int(request.POST.get('sort_order') or 0),
                    is_featured           = 'is_featured' in request.POST,
                    is_active             = 'is_active' in request.POST,
                )
                ep.save()
                messages.success(request, f"Email plan \"{ep.name}\" created.")
            except Exception as exc:
                messages.error(request, f"Failed to create email plan: {exc}")

        elif action == 'edit_custom_email_plan' and plan_id:
            try:
                ep = EmailPlan.objects.get(pk=int(plan_id))
                import re
                ep.name                   = request.POST.get('name', '').strip() or ep.name
                ep.slug                   = request.POST.get('slug', '').strip() or ep.slug
                ep.short_description      = request.POST.get('short_description', '').strip()
                ep.monthly_price          = Decimal(request.POST.get('monthly_price') or '0')
                ep.max_mailboxes          = int(request.POST.get('max_mailboxes') or ep.max_mailboxes)
                ep.storage_per_mailbox_gb = int(request.POST.get('storage_per_mailbox_gb') or ep.storage_per_mailbox_gb)
                ep.sort_order             = int(request.POST.get('sort_order') or 0)
                ep.is_featured            = 'is_featured' in request.POST
                ep.is_active              = 'is_active' in request.POST
                ep.save()
                messages.success(request, f"Email plan \"{ep.name}\" updated.")
            except Exception as exc:
                messages.error(request, f"Failed to update plan: {exc}")

        elif action == 'delete_email_plan' and plan_id:
            try:
                ep = EmailPlan.objects.get(pk=int(plan_id))
                name = ep.name
                ep.delete()
                messages.success(request, f"Email plan \"{name}\" deleted.")
            except Exception as exc:
                messages.error(request, f"Failed to delete plan: {exc}")

        return redirect('/super-admin/email-plans/')

    static_plans = [get_static_email_plan(i) for i in (1, 2, 3)]
    custom_plans  = list(EmailPlan.objects.order_by('sort_order', 'monthly_price'))
    servers = VoidPanelServer.objects.filter(is_active=True)
    ctx = _build_super_admin_context('email_plans')
    ctx.update({
        'static_email_plans': static_plans,
        'custom_email_plans':  custom_plans,
        'servers': servers,
    })
    return render(request, 'super_admin_email_plans.html', ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# SSL CERTIFICATE SERVICE — Provisioner + Portal + Admin
# ═══════════════════════════════════════════════════════════════════════════════

def _send_ssl_welcome(ssl_service):
    """Send SSL activation welcome email to customer."""
    try:
        from django.core.mail import EmailMessage as DjangoEmail
        from django.conf import settings as djsettings
        days = ssl_service.days_until_expiry or 90
        expires_str = ssl_service.expires_at.strftime('%B %d, %Y') if ssl_service.expires_at else 'N/A'
        html = f"""
<div style="font-family:'Inter',Arial,sans-serif;max-width:580px;margin:auto;background:#0f172a;color:#e2e8f0;border-radius:16px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#22c55e,#0ea5e9);padding:36px 32px;text-align:center;">
    <div style="font-size:2rem;">🔒</div>
    <h1 style="margin:8px 0 0;font-size:1.6rem;color:#fff;">SSL Certificate Activated!</h1>
    <p style="margin:6px 0 0;color:rgba(255,255,255,.85);">{ssl_service.domain}</p>
  </div>
  <div style="padding:28px 32px;">
    <p>Hi {ssl_service.user.get_full_name() or ssl_service.user.username},</p>
    <p>Your SSL certificate for <strong>{ssl_service.domain}</strong> has been issued successfully and is now active.</p>
    <div style="background:#1e293b;border-radius:12px;padding:20px 24px;margin:20px 0;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="color:#94a3b8;padding:6px 0;width:140px;">Domain</td><td style="font-weight:700;">{ ssl_service.domain}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Type</td><td style="font-weight:700;">{ssl_service.plan.get_ssl_type_display() if ssl_service.plan else 'DV SSL'}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Issued by</td><td style="font-weight:700;color:#4ade80;">Let's Encrypt</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Valid until</td><td style="font-weight:700;color:#4ade80;">{expires_str}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 0;">Days remaining</td><td style="font-weight:700;">{days} days</td></tr>
      </table>
    </div>
    <p style="color:#94a3b8;font-size:.85rem;">Your NGINX configuration has been updated automatically. Your site is now accessible over <strong>HTTPS</strong>.</p>
    <p style="color:#94a3b8;font-size:.85rem;">Manage and renew your SSL certificate from your <a href="https://voidpanel.com/portal/" style="color:#22c55e;">client portal</a>.</p>
  </div>
  <div style="background:#0f172a;padding:16px 32px;border-top:1px solid rgba(255,255,255,.06);text-align:center;font-size:.75rem;color:#475569;">
    VoidPanel — SSL Certificate Management
  </div>
</div>"""
        msg = DjangoEmail(
            subject=f'[VoidPanel] SSL Certificate Active — {ssl_service.domain}',
            body=html,
            from_email=djsettings.DEFAULT_FROM_EMAIL,
            to=[ssl_service.user.email],
        )
        msg.content_subtype = 'html'
        msg.send(fail_silently=True)
    except Exception as exc:
        _logger.error('SSL welcome email failed for %s: %s', ssl_service.domain, exc)


def _activate_ssl_service(order, invoice=None):
    """
    Called after payment for an SSL Certificate plan.
    Creates the SSLService record, triggers certbot via the panel API,
    and sends a welcome email.
    """
    import requests as _rq
    from django.utils import timezone
    from datetime import timedelta

    domain   = getattr(order, 'domain', '') or ''
    plan     = getattr(order, 'ssl_plan', None)

    if not domain:
        _logger.error('_activate_ssl_service: no domain on order %s', order.pk)
        return

    server = plan.server if plan and plan.server else VoidPanelServer.objects.filter(is_active=True).first()
    if not server:
        _logger.error('_activate_ssl_service: no server available')
        return

    validity = plan.validity_days if plan else 90

    ssl_svc = SSLService.objects.create(
        user          = order.user,
        plan_name     = plan.name if plan else '',
        server        = server,
        domain        = domain,
        status        = 'pending',
        monthly_price = getattr(order, 'price', plan.monthly_price if plan else 0),
        next_due_date = (timezone.now() + timedelta(days=validity)).date(),
        cert_path     = f'/etc/letsencrypt/live/{domain}/',
        notes         = '',
    )

    # Trigger certbot via panel API
    try:
        resp = _rq.post(
            f"{server.url.rstrip('/')}/api/v2/ssl/issue/",
            json={'domain': domain},
            headers={'X-API-Token': server.api_key},
            timeout=60,
        )
        data = resp.json()
        if data.get('status') == 'success':
            now = timezone.now()
            ssl_svc.status         = 'active'
            ssl_svc.issued_at      = now
            ssl_svc.expires_at     = now + timedelta(days=validity)
            ssl_svc.last_renewed_at= now
            ssl_svc.save(update_fields=['status', 'issued_at', 'expires_at', 'last_renewed_at'])
            PortalActivity.objects.create(
                user        = order.user,
                category    = 'account',
                title       = f'SSL Certificate issued: {domain}',
                description = f'Let\'s Encrypt cert issued on {server.name}',
            )
            _send_ssl_welcome(ssl_svc)
        else:
            ssl_svc.status = 'failed'
            ssl_svc.notes  = data.get('message', 'Certbot failed')
            ssl_svc.save(update_fields=['status', 'notes'])
            _logger.error('SSL provision failed for %s: %s', domain, data.get('message'))
    except Exception as exc:
        ssl_svc.status = 'failed'
        ssl_svc.notes  = str(exc)
        ssl_svc.save(update_fields=['status', 'notes'])
        _logger.error('SSL provision error for %s: %s', domain, exc)



# ── SSL Order: Step 1 — Configure (collect domain) ─────────────────────────

@login_required(login_url='/login/')
def ssl_configure(request, plan_id):
    """
    Step 1: Customer picks a plan → enters domain → submits.
    Stores plan + domain in session and redirects to checkout.
    """
    plan = get_static_ssl_plan(plan_id)
    if not plan:
        raise Http404("Plan not found")

    if request.method == 'POST':
        domain = request.POST.get('domain', '').strip().lower()
        billing_cycle = request.POST.get('billing_cycle', 'quarterly')

        # Basic domain validation
        import re
        if not domain or not re.match(r'^[a-z0-9][a-z0-9\-\.]{1,60}\.[a-z]{2,}$', domain):
            messages.error(request, 'Please enter a valid domain name (e.g. yourdomain.com)')
            return render(request, 'ssl_configure.html', {'plan': plan})

        # Check domain not already on an active SSL service for this user
        if SSLService.objects.filter(user=request.user, domain=domain,
                                      status__in=['active', 'pending']).exists():
            messages.error(request, f'You already have an active SSL service for {domain}.')
            return render(request, 'ssl_configure.html', {'plan': plan})

        # Store in session
        request.session['ssl_order'] = {
            'plan_id':       plan['id'],
            'domain':        domain,
            'billing_cycle': billing_cycle,
        }
        return redirect('ssl_checkout')

    return render(request, 'ssl_configure.html', {'plan': plan})


# ── SSL Order: Step 2 — Checkout (create Invoice + SSLOrder) ──────────────

@login_required(login_url='/login/')
def ssl_checkout(request):
    """
    Session key 'ssl_order' must be set by ssl_configure.
    Creates an unpaid Invoice and SSLOrder record, then redirects to payment page.
    """
    session_data = request.session.get('ssl_order')
    if not session_data:
        messages.error(request, "Please configure your SSL certificate details first.")
        return redirect('ssl_certificates')

    plan = get_static_ssl_plan(session_data['plan_id'])
    if not plan:
        messages.error(request, "SSL plan not found.")
        return redirect('ssl_certificates')

    domain = session_data['domain']
    billing_cycle = session_data['billing_cycle']

    # Calculate price
    from decimal import Decimal
    base_price = plan.quarterly_price
    if billing_cycle == 'annually':
        # Apply 10% discount for annual (quarterly price * 4 * 0.9)
        price = (base_price * Decimal('4') * Decimal('0.9')).quantize(Decimal('0.01'))
        desc = f"SSL Certificate Plan: {plan.name} (Annual) — {domain}"
    else:
        price = Decimal(str(base_price))
        desc = f"SSL Certificate Plan: {plan.name} (Quarterly) — {domain}"

    # Create Invoice
    from django.utils import timezone
    import uuid
    invoice_num = f"INV-SSL-{uuid.uuid4().hex[:8].upper()}"
    invoice = Invoice.objects.create(
        user=request.user,
        invoice_number=invoice_num,
        description=desc,
        status='unpaid',
        total=price,
        currency='INR',
        due_date=timezone.localdate() + timezone.timedelta(days=7),
    )

    # Create SSLOrder
    from data.models import SSLOrder
    SSLOrder.objects.create(
        user=request.user,
        plan_name=plan.name,
        invoice=invoice,
        domain=domain,
        billing_cycle=billing_cycle,
        price=price,
        status='pending_payment',
    )

    # Clear session config
    request.session.pop('ssl_order', None)

    return redirect(f'/portal/invoice/{invoice.id}/pay/')


def ssl_certificate_page(request):
    """Public landing + pricing page for SSL Certificate plans."""
    default_plans = [get_static_ssl_plan(i) for i in (1, 2, 3)]
    plans = [p for p in default_plans if p and p.get('is_active', True)]
    try:
        from data.models import SSLPlan
        custom_db_plans = SSLPlan.objects.filter(is_active=True).order_by('sort_order', 'quarterly_price')
        for db_plan in custom_db_plans:
            wrapper = get_static_ssl_plan(f"custom_{db_plan.pk}")
            if wrapper:
                plans.append(wrapper)
    except Exception:
        pass
    return render(request, 'ssl_certificates.html', {'plans': plans})


# ── Client Portal: SSL Manager ────────────────────────────────────────────────

@login_required(login_url='/login/')
def portal_manage_ssl(request, service_id):
    """
    Dedicated SSL management portal for a customer's SSL service.
    Shows certificate status, expiry countdown, renew button.
    No full panel access.
    """
    import requests as _rq
    ssl_svc   = get_object_or_404(SSLService, id=service_id, user=request.user)
    live_status = None
    api_error   = None

    if ssl_svc.server:
        try:
            resp = _rq.get(
                f"{ssl_svc.server.url.rstrip('/')}/api/v2/ssl/status/",
                params={'domain': ssl_svc.domain},
                headers={'X-API-Token': ssl_svc.server.api_key},
                timeout=8,
            )
            data = resp.json()
            if data.get('status') == 'success':
                live_status = data.get('data', {}).get('ssl_status', 'inactive')
                # Sync local status with live cert status
                if live_status == 'active' and ssl_svc.status in ('pending', 'failed'):
                    from django.utils import timezone
                    from datetime import timedelta
                    validity = ssl_svc.plan.validity_days if ssl_svc.plan else 90
                    ssl_svc.status    = 'active'
                    ssl_svc.issued_at = ssl_svc.issued_at or timezone.now()
                    ssl_svc.expires_at= ssl_svc.expires_at or (timezone.now() + timedelta(days=validity))
                    ssl_svc.save(update_fields=['status', 'issued_at', 'expires_at'])
        except Exception as exc:
            api_error = str(exc)

    ctx = {
        'ssl_svc':     ssl_svc,
        'live_status': live_status,
        'api_error':   api_error,
        'days_left':   ssl_svc.days_until_expiry,
        'expiry_pct':  ssl_svc.expiry_pct,
    }
    return render(request, 'portal_ssl_manager.html', ctx)


@login_required(login_url='/login/')
def portal_ssl_action(request, service_id):
    """
    AJAX endpoint for SSL actions: check_status, renew.
    POST JSON: {action: 'check_status'|'renew'}
    """
    import requests as _rq
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    ssl_svc = get_object_or_404(SSLService, id=service_id, user=request.user)
    if not ssl_svc.server:
        return JsonResponse({'status': 'error', 'message': 'No server assigned to this SSL service'}, status=400)

    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST.dict()

    action   = body.get('action', '').strip()
    api_base = ssl_svc.server.url.rstrip('/')
    api_key  = ssl_svc.server.api_key
    headers  = {'X-API-Token': api_key}

    # ── Check Status ──────────────────────────────────────────────────────────
    if action == 'check_status':
        try:
            resp = _rq.get(
                f'{api_base}/api/v2/ssl/status/',
                params={'domain': ssl_svc.domain},
                headers=headers, timeout=10,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            live = data.get('data', {}).get('ssl_status', 'inactive')
            if live == 'active' and ssl_svc.status in ('pending', 'failed', 'expired'):
                from django.utils import timezone
                from datetime import timedelta
                validity = ssl_svc.plan.validity_days if ssl_svc.plan else 90
                ssl_svc.status     = 'active'
                ssl_svc.expires_at = ssl_svc.expires_at or (timezone.now() + timedelta(days=validity))
                ssl_svc.save(update_fields=['status', 'expires_at'])
            return JsonResponse({
                'status':      'success',
                'live_status': live,
                'days_left':   ssl_svc.days_until_expiry,
                'message':     f'Certificate is {live} on server',
            })
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Status check failed')}, status=400)

    # ── Renew ─────────────────────────────────────────────────────────────────
    elif action == 'renew':
        try:
            resp = _rq.post(
                f'{api_base}/api/v2/ssl/issue/',
                json={'domain': ssl_svc.domain},
                headers=headers, timeout=90,
            )
            data = resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

        if data.get('status') == 'success':
            from django.utils import timezone
            from datetime import timedelta
            validity = ssl_svc.plan.validity_days if ssl_svc.plan else 90
            now = timezone.now()
            ssl_svc.status          = 'active'
            ssl_svc.last_renewed_at = now
            ssl_svc.expires_at      = now + timedelta(days=validity)
            ssl_svc.save(update_fields=['status', 'last_renewed_at', 'expires_at'])
            PortalActivity.objects.create(
                user        = request.user,
                category    = 'account',
                title       = f'SSL renewed: {ssl_svc.domain}',
                description = 'Renewed via client portal.',
            )
            return JsonResponse({
                'status':  'success',
                'message': f'SSL certificate renewed for {ssl_svc.domain}! Valid for {validity} days.',
                'days_left': ssl_svc.days_until_expiry,
            })
        return JsonResponse({'status': 'error', 'message': data.get('message', 'Renewal failed — ensure domain DNS points to server')}, status=400)

    return JsonResponse({'status': 'error', 'message': f'Unknown action: {action}'}, status=400)


@login_required(login_url='/login/')
def portal_ssl_download(request, service_id, file_type):
    """
    Downloads individual certificate or key files from the remote server.
    """
    import requests as _rq
    from django.http import HttpResponse, Http404

    ssl_svc = get_object_or_404(SSLService, id=service_id, user=request.user)
    if not ssl_svc.server:
        messages.error(request, "No server assigned to this SSL service")
        return redirect('portal_manage_ssl', service_id=service_id)

    mapping = {
        'cert':      'cert.pem',
        'key':       'privkey.pem',
        'fullchain': 'fullchain.pem',
        'chain':     'chain.pem',
    }
    filename = mapping.get(file_type)
    if not filename:
        raise Http404("Invalid file type requested")

    try:
        api_base = ssl_svc.server.url.rstrip('/')
        api_key  = ssl_svc.server.api_key
        resp = _rq.get(
            f'{api_base}/api/v2/ssl/download/',
            params={'domain': ssl_svc.domain},
            headers={'X-API-Token': api_key},
            timeout=10,
        )
        data = resp.json()
        if data.get('status') == 'success':
            files = data.get('data', {})
            content = files.get(filename)
            if not content:
                messages.error(request, f"File {filename} is empty or not available on the server.")
                return redirect('portal_manage_ssl', service_id=service_id)

            response = HttpResponse(content, content_type='application/x-pem-file')
            response['Content-Disposition'] = f'attachment; filename="{ssl_svc.domain}.{filename}"'
            return response
        else:
            messages.error(request, f"Could not retrieve files: {data.get('message', 'Unknown error')}")
            return redirect('portal_manage_ssl', service_id=service_id)
    except Exception as exc:
        messages.error(request, f"Server communication error: {exc}")
        return redirect('portal_manage_ssl', service_id=service_id)


# ── Super Admin: SSL Plans ────────────────────────────────────────────────────

@login_required(login_url='/login/')
def super_admin_ssl_plans(request):
    """Superadmin — manage Let's Encrypt SSL plans (3-month cycles, static overrides + custom DB plans)."""
    denied = _super_admin_guard(request)
    if denied:
        return denied

    if request.method == 'POST':
        action  = request.POST.get('action', '')
        plan_id = request.POST.get('plan_id')

        # ── Static plan overrides (IDs 1–3) ────────────────────────────────
        if action == 'edit_ssl_plan' and plan_id:
            try:
                pid = int(plan_id)
                ov, _ = SSLPlanOverride.objects.get_or_create(plan_id=pid)
                ov.name              = request.POST.get('name', '').strip() or None
                ov.slug              = request.POST.get('slug', '').strip() or None
                ov.short_description = request.POST.get('short_description', '').strip() or None
                ov.ssl_type          = request.POST.get('ssl_type', '').strip() or None
                raw_qp               = request.POST.get('quarterly_price', '')
                ov.quarterly_price   = Decimal(raw_qp) if raw_qp else None
                raw_md               = request.POST.get('max_domains', '')
                ov.max_domains       = int(raw_md) if raw_md else None
                raw_so               = request.POST.get('sort_order', '')
                ov.sort_order        = int(raw_so) if raw_so else None
                ov.is_featured       = 'is_featured' in request.POST
                ov.is_active         = 'is_active' in request.POST
                ov.auto_renew        = 'auto_renew' in request.POST
                ov.save()
                messages.success(request, f"SSL Plan #{pid} updated.")
            except Exception as exc:
                messages.error(request, f"Error saving SSL plan: {exc}")

        elif action == 'toggle_ssl_plan' and plan_id:
            try:
                pid = int(plan_id)
                ov, _ = SSLPlanOverride.objects.get_or_create(plan_id=pid)
                ov.is_active = not ov.is_active
                ov.save()
                messages.success(request, f"SSL Plan #{pid} {'activated' if ov.is_active else 'deactivated'}.")
            except Exception as exc:
                messages.error(request, f"Toggle failed: {exc}")

        elif action == 'reset_ssl_plan' and plan_id:
            try:
                SSLPlanOverride.objects.filter(plan_id=int(plan_id)).delete()
                messages.success(request, f"SSL Plan #{plan_id} reset to defaults.")
            except Exception as exc:
                messages.error(request, f"Reset failed: {exc}")

        # ── Custom SSL plan CRUD ────────────────────────────────────────────
        elif action == 'create_ssl_plan':
            try:
                import re, uuid
                name = request.POST.get('name', '').strip()
                if not name:
                    raise ValueError("Plan name is required.")
                slug = request.POST.get('slug', '').strip()
                if not slug:
                    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                if SSLPlan.objects.filter(slug=slug).exists():
                    slug = f"{slug}-{uuid.uuid4().hex[:4]}"
                sp = SSLPlan(
                    name              = name,
                    slug              = slug,
                    short_description = request.POST.get('short_description', '').strip(),
                    ssl_type          = request.POST.get('ssl_type', 'dv'),
                    quarterly_price   = Decimal(request.POST.get('quarterly_price') or '0'),
                    max_domains       = int(request.POST.get('max_domains') or 1),
                    validity_days     = 90,  # always 90 for Let's Encrypt
                    sort_order        = int(request.POST.get('sort_order') or 0),
                    is_featured       = 'is_featured' in request.POST,
                    is_active         = 'is_active' in request.POST,
                    auto_renew        = 'auto_renew' in request.POST,
                )
                sp.save()
                messages.success(request, f"SSL plan \"{sp.name}\" created.")
            except Exception as exc:
                messages.error(request, f"Failed to create SSL plan: {exc}")

        elif action == 'edit_custom_ssl_plan' and plan_id:
            try:
                sp = SSLPlan.objects.get(pk=int(plan_id))
                sp.name              = request.POST.get('name', '').strip() or sp.name
                sp.slug              = request.POST.get('slug', '').strip() or sp.slug
                sp.short_description = request.POST.get('short_description', '').strip()
                sp.ssl_type          = request.POST.get('ssl_type', 'dv')
                sp.quarterly_price   = Decimal(request.POST.get('quarterly_price') or '0')
                sp.max_domains       = int(request.POST.get('max_domains') or sp.max_domains)
                sp.sort_order        = int(request.POST.get('sort_order') or 0)
                sp.is_featured       = 'is_featured' in request.POST
                sp.is_active         = 'is_active' in request.POST
                sp.auto_renew        = 'auto_renew' in request.POST
                sp.save()
                messages.success(request, f"SSL plan \"{sp.name}\" updated.")
            except Exception as exc:
                messages.error(request, f"Failed to update SSL plan: {exc}")

        elif action == 'delete_ssl_plan' and plan_id:
            try:
                sp = SSLPlan.objects.get(pk=int(plan_id))
                name = sp.name
                sp.delete()
                messages.success(request, f"SSL plan \"{name}\" deleted.")
            except Exception as exc:
                messages.error(request, f"Failed to delete SSL plan: {exc}")

        return redirect('/super-admin/ssl-plans/')

    static_plans = [get_static_ssl_plan(i) for i in (1, 2, 3)]
    custom_plans  = list(SSLPlan.objects.order_by('sort_order', 'quarterly_price'))
    servers = VoidPanelServer.objects.filter(is_active=True)
    ctx = _build_super_admin_context('ssl_plans')
    ctx.update({
        'static_ssl_plans': static_plans,
        'custom_ssl_plans':  custom_plans,
        'servers': servers,
    })
    return render(request, 'super_admin_ssl_plans.html', ctx)


# ── Super Admin: SSL Services Monitor ────────────────────────────────────────

@login_required(login_url='/login/')
def super_admin_ssl_services(request):
    """
    Superadmin page to monitor all customer SSL certificates,
    see expiry status, and manually trigger renewals.
    """
    import requests as _rq
    denied = _super_admin_guard(request)
    if denied:
        return denied

    if request.method == 'POST':
        action     = request.POST.get('action', '')
        service_id = request.POST.get('service_id')

        # Manual renewal triggered by superadmin
        if action == 'renew_ssl' and service_id:
            ssl_svc = SSLService.objects.filter(id=service_id).first()
            if ssl_svc and ssl_svc.server:
                try:
                    resp = _rq.post(
                        f"{ssl_svc.server.url.rstrip('/')}/api/v2/ssl/issue/",
                        json={'domain': ssl_svc.domain},
                        headers={'X-API-Token': ssl_svc.server.api_key},
                        timeout=90,
                    )
                    data = resp.json()
                    if data.get('status') == 'success':
                        from django.utils import timezone
                        from datetime import timedelta
                        validity = ssl_svc.plan.validity_days if ssl_svc.plan else 90
                        now = timezone.now()
                        ssl_svc.status          = 'active'
                        ssl_svc.last_renewed_at = now
                        ssl_svc.expires_at      = now + timedelta(days=validity)
                        ssl_svc.save(update_fields=['status', 'last_renewed_at', 'expires_at'])
                        messages.success(request, f'SSL renewed for {ssl_svc.domain}')
                    else:
                        messages.error(request, f'Renewal failed for {ssl_svc.domain}: {data.get("message")}')
                except Exception as exc:
                    messages.error(request, f'Error renewing {ssl_svc.domain}: {exc}')
            return redirect('/super-admin/ssl-services/')

    filter_mode = request.GET.get('filter', 'all')
    services = SSLService.objects.select_related('user', 'plan', 'server').order_by('-created_at')

    if filter_mode == 'expiring':
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() + timedelta(days=30)
        services = services.filter(expires_at__lte=cutoff, status='active')
    elif filter_mode == 'failed':
        services = services.filter(status='failed')
    elif filter_mode == 'active':
        services = services.filter(status='active')

    ctx = _build_super_admin_context('ssl_services')
    ctx.update({
        'ssl_services': services,
        'filter_mode':  filter_mode,
        'total':        SSLService.objects.count(),
        'active_count': SSLService.objects.filter(status='active').count(),
        'expiring_count': SSLService.objects.filter(
            status='active',
            expires_at__lte=__import__('django.utils.timezone', fromlist=['timezone']).timezone.now() + __import__('datetime').timedelta(days=30)
        ).count() if False else SSLService.objects.filter(status__in=['expiring']).count(),
        'failed_count': SSLService.objects.filter(status='failed').count(),
    })
    return render(request, 'super_admin_ssl_services.html', ctx)


# ══════════════════════════════════════════════════════════════════
#  SOCIAL MEDIA MANAGEMENT — WEBSITE + PORTAL VIEWS (LEGACY REMOVED)
# ══════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
#  MARKETING SUITE — WEBSITE & BILLING (LEGACY REMOVED)
# ══════════════════════════════════════════════════════════════



# ── Super Admin: Social Media API Keys ──────────────────────────────────────

@login_required(login_url='/login/')
def super_admin_social_api(request):
    """Manage per-platform OAuth API keys and enable/disable toggles."""
    if not request.user.is_superuser:
        return redirect('/')
    from data.models import SocialPlatformSettings
    cfg = SocialPlatformSettings.get()

    if request.method == 'POST' and request.POST.get('action') == 'save_api_config':
        cfg.facebook_enabled       = bool(request.POST.get('facebook_enabled'))
        cfg.facebook_app_id        = request.POST.get('facebook_app_id', '').strip()
        cfg.facebook_app_secret    = request.POST.get('facebook_app_secret', '').strip() or cfg.facebook_app_secret

        cfg.instagram_enabled      = bool(request.POST.get('instagram_enabled'))
        cfg.instagram_app_id       = request.POST.get('instagram_app_id', '').strip()
        cfg.instagram_app_secret   = request.POST.get('instagram_app_secret', '').strip() or cfg.instagram_app_secret

        cfg.twitter_enabled        = bool(request.POST.get('twitter_enabled'))
        cfg.twitter_api_key        = request.POST.get('twitter_api_key', '').strip()
        cfg.twitter_api_secret     = request.POST.get('twitter_api_secret', '').strip() or cfg.twitter_api_secret
        cfg.twitter_bearer_token   = request.POST.get('twitter_bearer_token', '').strip() or cfg.twitter_bearer_token

        cfg.linkedin_enabled       = bool(request.POST.get('linkedin_enabled'))
        cfg.linkedin_client_id     = request.POST.get('linkedin_client_id', '').strip()
        cfg.linkedin_client_secret = request.POST.get('linkedin_client_secret', '').strip() or cfg.linkedin_client_secret

        cfg.youtube_enabled        = bool(request.POST.get('youtube_enabled'))
        cfg.google_client_id       = request.POST.get('google_client_id', '').strip()
        cfg.google_client_secret   = request.POST.get('google_client_secret', '').strip() or cfg.google_client_secret

        cfg.tiktok_enabled         = bool(request.POST.get('tiktok_enabled'))
        cfg.tiktok_client_key      = request.POST.get('tiktok_client_key', '').strip()
        cfg.tiktok_client_secret   = request.POST.get('tiktok_client_secret', '').strip() or cfg.tiktok_client_secret

        cfg.pinterest_enabled      = bool(request.POST.get('pinterest_enabled'))
        cfg.pinterest_app_id       = request.POST.get('pinterest_app_id', '').strip()
        cfg.pinterest_app_secret   = request.POST.get('pinterest_app_secret', '').strip() or cfg.pinterest_app_secret

        cfg.threads_enabled        = bool(request.POST.get('threads_enabled'))
        cfg.threads_app_id         = request.POST.get('threads_app_id', '').strip()
        cfg.threads_app_secret     = request.POST.get('threads_app_secret', '').strip() or cfg.threads_app_secret

        cfg.gbusiness_enabled      = bool(request.POST.get('gbusiness_enabled'))
        cfg.save()
        messages.success(request, '✅ Social Media API settings saved successfully.')
        return redirect('/super-admin/social-api/')

    enabled_list = cfg.enabled_platform_list()
    ctx = _build_super_admin_context('social_api')
    ctx.update({
        'cfg':           cfg,
        'enabled_count': len(enabled_list),
        'disabled_count': 9 - len(enabled_list),
    })
    return render(request, 'super_admin_social_api.html', ctx)


# ── Public API: Panel Config Sync ────────────────────────────────────────────

def api_social_platform_config(request):
    """
    Secure JSON endpoint — installed VoidPanel instances call this to check
    which social platforms are enabled.

    SECURITY: App IDs and secrets are NEVER returned. Credentials stay on
    voidpanel.com and are used only during the OAuth relay flow.

    Accepts license key via:
        Header:  X-VoidPanel-License: <key>
        OR GET param: ?license=<key>
    """
    from django.http import JsonResponse
    from data.models import SocialPlatformSettings

    # ── 1. Validate licence key ───────────────────────────────────────────
    license_key = (
        request.headers.get('X-VoidPanel-License')
        or request.headers.get('Authorization', '').removeprefix('Bearer ')
        or request.GET.get('license', '')
    ).strip()

    authenticated = False
    if license_key:
        from data.models import PanelLicenseRecord
        authenticated = PanelLicenseRecord.objects.filter(
            key=license_key, status=PanelLicenseRecord.STATUS_ACTIVE
        ).exists()

    # ── 2. Fetch settings ─────────────────────────────────────────────────
    cfg = SocialPlatformSettings.get()

    # ── 3. Build response — ONLY enabled flags, NEVER secrets ─────────────
    platforms = {
        'fb': {'enabled': cfg.facebook_enabled},
        'ig': {'enabled': cfg.instagram_enabled},
        'tw': {'enabled': cfg.twitter_enabled},
        'li': {'enabled': cfg.linkedin_enabled},
        'yt': {'enabled': cfg.youtube_enabled},
        'tt': {'enabled': cfg.tiktok_enabled},
        'pi': {'enabled': cfg.pinterest_enabled},
        'th': {'enabled': cfg.threads_enabled},
        'gb': {'enabled': cfg.gbusiness_enabled},
    }

    return JsonResponse({
        'authenticated': authenticated,
        'enabled_platforms': cfg.enabled_platform_list(),
        'platforms': platforms,
        'updated_at': cfg.updated_at.isoformat() if cfg.updated_at else None,
    })


# ── Super Admin: Update Manager ─────────────────────────────────────────────

@login_required(login_url='/login/')
def super_admin_update_manager(request):
    """Update Manager page — shows version of all registered servers."""
    if not request.user.is_superuser:
        return redirect('/')
    from data.models import VoidPanelServer
    import requests as _req
    servers = []
    for s in VoidPanelServer.objects.all():
        entry = {'name': s.name, 'url': s.url, 'id': s.id, 'is_active': s.is_active, 'version': '—', 'latest': '—', 'needs_update': False}
        try:
            r = _req.get(f"{s.url.rstrip('/')}/checkversion/",
                         headers={'X-VoidPanel-Key': s.api_key}, timeout=5)
            if r.status_code == 200:
                entry['version'] = r.json().get('version', '—')
        except Exception:
            entry['version'] = 'Unreachable'
        servers.append(entry)
    latest = '—'
    try:
        lr = _req.get('https://voidpanel.com/version_name/', timeout=5)
        if lr.status_code == 200:
            latest = lr.json().get('version', '—')
    except Exception:
        pass
    for s in servers:
        s['latest'] = latest
        if s['version'] not in ('—', 'Unreachable') and latest not in ('—',):
            s['needs_update'] = s['version'] < latest
    return render(request, 'super_admin_update_manager.html',
                  {'servers': servers, 'latest': latest})


@login_required(login_url='/login/')
def super_admin_push_update(request):
    """POST: Trigger update on one or all registered servers via API key."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    from data.models import VoidPanelServer
    import requests as _req
    data = json.loads(request.body) if request.body else {}
    server_id = data.get('server_id')
    qs = VoidPanelServer.objects.filter(id=server_id) if server_id else VoidPanelServer.objects.filter(is_active=True)
    results = []
    for s in qs:
        try:
            r = _req.post(f"{s.url.rstrip('/')}/updatepanel/",
                          headers={'X-VoidPanel-Key': s.api_key, 'Content-Type': 'application/json'},
                          json={}, timeout=20)
            msg = r.json().get('message', '') if 'application/json' in r.headers.get('Content-Type','') else r.text[:100]
            results.append({'server': s.name, 'status': 'ok' if r.status_code == 200 else 'error', 'message': msg})
        except Exception as e:
            results.append({'server': s.name, 'status': 'error', 'message': str(e)})
    ok = sum(1 for r in results if r['status'] == 'ok')
    return JsonResponse({'status': 'done', 'pushed': ok, 'errors': len(results)-ok, 'results': results})


# ══════════════════════════════════════════════════════════════════════════════
#  SOCIAL MEDIA OAUTH RELAY — Secure intermediary for self-hosted panels
# ══════════════════════════════════════════════════════════════════════════════

def _validate_panel_license(request):
    """Extract and validate the license key. Returns (license_key, is_valid)."""
    from data.models import PanelLicenseRecord
    license_key = (
        request.GET.get('license', '')
        or request.headers.get('X-VoidPanel-License', '')
        or request.headers.get('Authorization', '').removeprefix('Bearer ')
    ).strip()
    if not license_key:
        return '', False
    valid = PanelLicenseRecord.objects.filter(
        key=license_key, status=PanelLicenseRecord.STATUS_ACTIVE
    ).exists()
    return license_key, valid


def social_oauth_connect(request, platform):
    """
    Step 1 of the OAuth relay flow.
    A self-hosted VoidPanel redirects the user's browser here with:
        ?license=<key>&callback_uri=<panel_callback_url>
    We validate the license, then redirect the user to the social platform's
    OAuth authorization page. Credentials never leave this server.
    """
    import secrets, hashlib, base64
    from data.models import SocialPlatformSettings

    license_key, valid = _validate_panel_license(request)
    if not valid:
        return JsonResponse({'error': 'Invalid or missing license key.'}, status=403)

    callback_uri = request.GET.get('callback_uri', '').strip()
    if not callback_uri:
        return JsonResponse({'error': 'Missing callback_uri parameter.'}, status=400)

    cfg = SocialPlatformSettings.get()

    # Store relay state in session so we can verify on callback
    request.session['oauth_relay_license'] = license_key
    request.session['oauth_relay_callback'] = callback_uri
    request.session['oauth_relay_platform'] = platform

    # Our own callback URL on voidpanel.com
    our_callback = request.build_absolute_uri(f'/social/oauth/callback/{platform}/')

    # Twitter/X PKCE
    tw_verifier = secrets.token_urlsafe(64)
    tw_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(tw_verifier.encode()).digest()
    ).rstrip(b'=').decode()
    request.session['tw_code_verifier'] = tw_verifier
    tw_state = secrets.token_urlsafe(16)
    request.session['tw_state'] = tw_state

    OAUTH_URLS = {
        'fb': (
            f"https://www.facebook.com/v19.0/dialog/oauth"
            f"?client_id={cfg.facebook_app_id}"
            f"&redirect_uri={our_callback}"
            f"&scope=pages_manage_posts,pages_read_engagement,pages_show_list,"
            f"instagram_basic,instagram_content_publish"
            f"&response_type=code"
        ),
        'ig': (
            f"https://www.facebook.com/v19.0/dialog/oauth"
            f"?client_id={cfg.facebook_app_id}"
            f"&redirect_uri={our_callback}"
            f"&scope=pages_manage_posts,pages_read_engagement,pages_show_list,"
            f"instagram_basic,instagram_content_publish"
            f"&response_type=code"
        ),
        'tw': (
            f"https://twitter.com/i/oauth2/authorize"
            f"?response_type=code"
            f"&client_id={cfg.twitter_api_key}"
            f"&redirect_uri={our_callback}"
            f"&scope=tweet.read%20tweet.write%20users.read%20offline.access"
            f"&state={tw_state}"
            f"&code_challenge={tw_challenge}"
            f"&code_challenge_method=S256"
        ),
        'li': (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id={cfg.linkedin_client_id}"
            f"&redirect_uri={our_callback}"
            f"&scope=w_member_social%20r_liteprofile%20r_emailaddress"
        ),
        'pi': (
            f"https://www.pinterest.com/oauth/"
            f"?consumer_id={cfg.pinterest_app_id}"
            f"&redirect_uri={our_callback}"
            f"&response_type=code"
            f"&scope=pins:read,pins:write,boards:read"
        ),
        'yt': (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={cfg.google_client_id}"
            f"&redirect_uri={our_callback}"
            f"&response_type=code"
            f"&access_type=offline"
            f"&scope=https://www.googleapis.com/auth/youtube.readonly"
            f"%20https://www.googleapis.com/auth/youtube.upload"
        ),
        'gb': (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={cfg.google_client_id}"
            f"&redirect_uri={our_callback}"
            f"&response_type=code"
            f"&access_type=offline"
            f"&scope=https://www.googleapis.com/auth/business.manage"
        ),
        'th': (
            f"https://www.threads.net/oauth/authorize"
            f"?client_id={cfg.threads_app_id}"
            f"&redirect_uri={our_callback}"
            f"&scope=threads_basic,threads_content_publish"
            f"&response_type=code"
        ),
        'tt': (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={cfg.tiktok_client_key}"
            f"&redirect_uri={our_callback}"
            f"&response_type=code"
            f"&scope=user.info.basic,video.list,video.upload"
        ),
    }

    url = OAUTH_URLS.get(platform)
    if not url:
        return JsonResponse({'error': f"Platform '{platform}' not supported."}, status=400)
    return redirect(url)


def social_oauth_callback(request, platform):
    """
    Step 2 of the OAuth relay flow.
    The social platform redirects back here with ?code=...
    We exchange the code for tokens (using the secrets stored on this server),
    fetch profile info, store everything in an OAuthRelayState record,
    then redirect the user back to the panel's callback_uri with ?relay_code=...
    """
    import secrets as _secrets_mod
    import requests as _req
    from data.models import SocialPlatformSettings, OAuthRelayState

    license_key = request.session.get('oauth_relay_license', '')
    callback_uri = request.session.get('oauth_relay_callback', '')
    if not license_key or not callback_uri:
        return HttpResponse('OAuth relay session expired. Please try connecting again from your panel.', status=400)

    code = request.GET.get('code', '')
    if not code:
        # User cancelled or error
        sep = '&' if '?' in callback_uri else '?'
        return redirect(f"{callback_uri}{sep}error=oauth_cancelled")

    cfg = SocialPlatformSettings.get()
    our_callback = request.build_absolute_uri(f'/social/oauth/callback/{platform}/')

    token_data = {}
    profile_data = {}

    # ── Token exchange ────────────────────────────────────────────────────
    try:
        if platform in ('fb', 'ig'):
            r = _req.post('https://graph.facebook.com/v19.0/oauth/access_token', data={
                'client_id': cfg.facebook_app_id,
                'client_secret': cfg.facebook_app_secret,
                'code': code,
                'redirect_uri': our_callback,
            }, timeout=10)
            token_data = r.json()

        elif platform == 'tw':
            verifier = request.session.pop('tw_code_verifier', '')
            r = _req.post('https://api.twitter.com/2/oauth2/token', data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': our_callback,
                'code_verifier': verifier,
            }, auth=(cfg.twitter_api_key, cfg.twitter_api_secret), timeout=10)
            token_data = r.json()

        elif platform == 'li':
            r = _req.post('https://www.linkedin.com/oauth/v2/accessToken', data={
                'grant_type': 'authorization_code', 'code': code,
                'client_id': cfg.linkedin_client_id, 'client_secret': cfg.linkedin_client_secret,
                'redirect_uri': our_callback,
            }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
            token_data = r.json()

        elif platform in ('yt', 'gb'):
            r = _req.post('https://oauth2.googleapis.com/token', data={
                'code': code, 'client_id': cfg.google_client_id,
                'client_secret': cfg.google_client_secret, 'grant_type': 'authorization_code',
                'redirect_uri': our_callback,
            }, timeout=10)
            token_data = r.json()

        elif platform == 'th':
            r = _req.post('https://graph.threads.net/oauth/access_token', data={
                'client_id': cfg.threads_app_id, 'client_secret': cfg.threads_app_secret,
                'code': code, 'grant_type': 'authorization_code',
                'redirect_uri': our_callback,
            }, timeout=10)
            token_data = r.json()

        elif platform == 'tt':
            r = _req.post('https://open.tiktokapis.com/v2/oauth/token/', data={
                'client_key': cfg.tiktok_client_key, 'client_secret': cfg.tiktok_client_secret,
                'code': code, 'grant_type': 'authorization_code',
                'redirect_uri': our_callback,
            }, timeout=10)
            token_data = r.json()

        elif platform == 'pi':
            r = _req.post('https://api.pinterest.com/v5/oauth/token', data={
                'grant_type': 'authorization_code', 'code': code,
                'redirect_uri': our_callback,
            }, auth=(cfg.pinterest_app_id, cfg.pinterest_app_secret), timeout=10)
            token_data = r.json()

    except Exception as e:
        token_data = {'error': str(e)}

    access_token = token_data.get('access_token', '')
    if not access_token:
        sep = '&' if '?' in callback_uri else '?'
        return redirect(f"{callback_uri}{sep}error=token_exchange_failed")

    # ── Fetch profile / pages ─────────────────────────────────────────────
    accounts = []  # list of account dicts to send back to the panel

    try:
        if platform == 'fb':
            pages_r = _req.get(
                f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}",
                timeout=10
            )
            if pages_r.status_code == 200:
                for page in pages_r.json().get('data', []):
                    accounts.append({
                        'platform': 'fb',
                        'account_id': page.get('id'),
                        'account_name': page.get('name', 'FB Page'),
                        'access_token': page.get('access_token', ''),
                        'page_id': page.get('id'),
                        'page_name': page.get('name', ''),
                    })

        elif platform == 'ig':
            pages_r = _req.get(
                f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}",
                timeout=10
            )
            if pages_r.status_code == 200:
                for page in pages_r.json().get('data', []):
                    p_id = page.get('id')
                    p_token = page.get('access_token', '')
                    ig_r = _req.get(
                        f"https://graph.facebook.com/v19.0/{p_id}"
                        f"?fields=instagram_business_account{{id,username,name,profile_picture_url,followers_count}}"
                        f"&access_token={p_token}",
                        timeout=10
                    )
                    if ig_r.status_code == 200:
                        ig_data = ig_r.json().get('instagram_business_account')
                        if ig_data:
                            accounts.append({
                                'platform': 'ig',
                                'account_id': ig_data.get('id'),
                                'account_name': ig_data.get('name') or ig_data.get('username', ''),
                                'account_username': ig_data.get('username', ''),
                                'access_token': p_token,
                                'page_id': p_id,
                                'profile_picture_url': ig_data.get('profile_picture_url', ''),
                                'followers_count': ig_data.get('followers_count', 0),
                            })

        elif platform == 'tw':
            me_r = _req.get(
                'https://api.twitter.com/2/users/me?user.fields=profile_image_url,public_metrics,username,name',
                headers={'Authorization': f'Bearer {access_token}'}, timeout=10
            )
            if me_r.status_code == 200:
                me = me_r.json().get('data', {})
                accounts.append({
                    'platform': 'tw',
                    'account_id': me.get('id', ''),
                    'account_name': me.get('name', 'Twitter Account'),
                    'account_username': me.get('username', ''),
                    'access_token': access_token,
                    'refresh_token': token_data.get('refresh_token', ''),
                    'profile_picture_url': me.get('profile_image_url', ''),
                    'followers_count': me.get('public_metrics', {}).get('followers_count', 0),
                })

        elif platform == 'li':
            me_r = _req.get(
                'https://api.linkedin.com/v2/me?projection=(id,localizedFirstName,localizedLastName,profilePicture(displayImage~:playableStreams))',
                headers={'Authorization': f'Bearer {access_token}'}, timeout=10
            )
            if me_r.status_code == 200:
                me = me_r.json()
                pic = ''
                try:
                    pic = me['profilePicture']['displayImage~']['elements'][-1]['identifiers'][0]['identifier']
                except Exception:
                    pass
                accounts.append({
                    'platform': 'li',
                    'account_id': me.get('id', ''),
                    'account_name': f"{me.get('localizedFirstName','')} {me.get('localizedLastName','')}".strip() or 'LinkedIn Account',
                    'access_token': access_token,
                    'refresh_token': token_data.get('refresh_token', ''),
                    'profile_picture_url': pic,
                })

        elif platform in ('yt', 'gb'):
            me_r = _req.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}, timeout=10
            )
            if me_r.status_code == 200:
                me = me_r.json()
                accounts.append({
                    'platform': platform,
                    'account_id': me.get('id', ''),
                    'account_name': me.get('name', f'{platform.upper()} Account'),
                    'access_token': access_token,
                    'refresh_token': token_data.get('refresh_token', ''),
                    'profile_picture_url': me.get('picture', ''),
                })

        elif platform == 'th':
            me_r = _req.get(
                f"https://graph.threads.net/v1.0/me?fields=id,username,name,threads_profile_picture_url,threads_biography&access_token={access_token}",
                timeout=10
            )
            if me_r.status_code == 200:
                me = me_r.json()
                accounts.append({
                    'platform': 'th',
                    'account_id': me.get('id', ''),
                    'account_name': me.get('name') or me.get('username', 'Threads Account'),
                    'account_username': me.get('username', ''),
                    'access_token': access_token,
                    'refresh_token': token_data.get('refresh_token', ''),
                    'profile_picture_url': me.get('threads_profile_picture_url', ''),
                })

        elif platform == 'tt':
            me_r = _req.post(
                'https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,avatar_url,follower_count',
                headers={'Authorization': f'Bearer {access_token}'}, timeout=10
            )
            if me_r.status_code == 200:
                me = me_r.json().get('data', {}).get('user', {})
                accounts.append({
                    'platform': 'tt',
                    'account_id': me.get('open_id', ''),
                    'account_name': me.get('display_name', 'TikTok Account'),
                    'access_token': access_token,
                    'refresh_token': token_data.get('refresh_token', ''),
                    'profile_picture_url': me.get('avatar_url', ''),
                    'followers_count': me.get('follower_count', 0),
                })

        elif platform == 'pi':
            me_r = _req.get(
                'https://api.pinterest.com/v5/user_account',
                headers={'Authorization': f'Bearer {access_token}'}, timeout=10
            )
            if me_r.status_code == 200:
                me = me_r.json()
                accounts.append({
                    'platform': 'pi',
                    'account_id': me.get('username', ''),
                    'account_name': me.get('business_name') or me.get('username', 'Pinterest Account'),
                    'account_username': me.get('username', ''),
                    'access_token': access_token,
                    'refresh_token': token_data.get('refresh_token', ''),
                    'profile_picture_url': me.get('profile_image', ''),
                    'followers_count': me.get('follower_count', 0),
                })

    except Exception:
        pass  # profile fetch failed, but token is still valid

    # If no accounts were found, create a generic one with the token
    if not accounts:
        accounts.append({
            'platform': platform,
            'account_id': code[:16],
            'account_name': f'{platform.upper()} Account',
            'access_token': access_token,
            'refresh_token': token_data.get('refresh_token', ''),
        })

    # Add common token metadata to each account
    for acc in accounts:
        acc.setdefault('refresh_token', token_data.get('refresh_token', ''))
        acc['expires_in'] = token_data.get('expires_in')

    # ── Create relay record ───────────────────────────────────────────────
    relay_code = _secrets_mod.token_urlsafe(32)
    OAuthRelayState.objects.create(
        relay_code=relay_code,
        license_key=license_key,
        token_data={'accounts': accounts, 'platform': platform},
    )

    # Clean up expired relays (older than 10 minutes)
    from django.utils import timezone as _tz
    from datetime import timedelta
    OAuthRelayState.objects.filter(
        created_at__lt=_tz.now() - timedelta(minutes=10)
    ).delete()

    # ── Redirect back to the panel ────────────────────────────────────────
    sep = '&' if '?' in callback_uri else '?'
    return redirect(f"{callback_uri}{sep}relay_code={relay_code}")


@csrf_exempt
def api_social_retrieve_tokens(request):
    """
    Step 3 — Server-to-server call from the self-hosted panel.
    POST with JSON: {"license": "...", "relay_code": "..."}
    Returns the token data and deletes the relay record.
    Single-use: the relay code is consumed immediately.
    """
    from data.models import OAuthRelayState
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    license_key = body.get('license', '').strip()
    relay_code = body.get('relay_code', '').strip()

    if not license_key or not relay_code:
        return JsonResponse({'error': 'Missing license or relay_code.'}, status=400)

    # Validate license
    _, valid = _validate_panel_license(request)
    if not valid:
        # Also check from the body since this is server-to-server
        from data.models import PanelLicenseRecord
        valid = PanelLicenseRecord.objects.filter(
            key=license_key, status=PanelLicenseRecord.STATUS_ACTIVE
        ).exists()
    if not valid:
        return JsonResponse({'error': 'Invalid license key.'}, status=403)

    # Fetch and consume the relay
    from django.utils import timezone as _tz
    from datetime import timedelta
    relay = OAuthRelayState.objects.filter(
        relay_code=relay_code,
        license_key=license_key,
        created_at__gte=_tz.now() - timedelta(minutes=10),  # 10-min expiry
    ).first()

    if not relay:
        return JsonResponse({'error': 'Relay code expired or invalid.'}, status=404)

    data = relay.token_data
    relay.delete()  # Single use — consumed

    return JsonResponse({'status': 'ok', **data})


@csrf_exempt
def api_social_refresh_token(request):
    """
    Server-to-server call from self-hosted panel to refresh an expired token.
    POST with JSON: {"license": "...", "platform": "...", "refresh_token": "..."}
    Uses the secrets stored on voidpanel.com to perform the refresh.
    """
    from data.models import SocialPlatformSettings
    import requests as _req

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    license_key = body.get('license', '').strip()
    platform = body.get('platform', '').strip()
    refresh_token = body.get('refresh_token', '').strip()

    if not license_key or not platform or not refresh_token:
        return JsonResponse({'error': 'Missing license, platform, or refresh_token.'}, status=400)

    # Validate license
    from data.models import PanelLicenseRecord
    if not PanelLicenseRecord.objects.filter(
        key=license_key, status=PanelLicenseRecord.STATUS_ACTIVE
    ).exists():
        return JsonResponse({'error': 'Invalid license key.'}, status=403)

    cfg = SocialPlatformSettings.get()
    new_token_data = {}

    try:
        if platform in ('fb', 'ig'):
            # Facebook long-lived tokens don't use refresh_token in the same way.
            # Exchange the existing token for a new long-lived one.
            r = _req.get(
                f"https://graph.facebook.com/v19.0/oauth/access_token"
                f"?grant_type=fb_exchange_token"
                f"&client_id={cfg.facebook_app_id}"
                f"&client_secret={cfg.facebook_app_secret}"
                f"&fb_exchange_token={refresh_token}",
                timeout=10
            )
            new_token_data = r.json()

        elif platform == 'tw':
            r = _req.post('https://api.twitter.com/2/oauth2/token', data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            }, auth=(cfg.twitter_api_key, cfg.twitter_api_secret), timeout=10)
            new_token_data = r.json()

        elif platform == 'li':
            r = _req.post('https://www.linkedin.com/oauth/v2/accessToken', data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': cfg.linkedin_client_id,
                'client_secret': cfg.linkedin_client_secret,
            }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
            new_token_data = r.json()

        elif platform in ('yt', 'gb'):
            r = _req.post('https://oauth2.googleapis.com/token', data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': cfg.google_client_id,
                'client_secret': cfg.google_client_secret,
            }, timeout=10)
            new_token_data = r.json()

        elif platform == 'th':
            r = _req.post('https://graph.threads.net/oauth/access_token', data={
                'grant_type': 'th_exchange_token',
                'client_secret': cfg.threads_app_secret,
                'access_token': refresh_token,
            }, timeout=10)
            new_token_data = r.json()

        elif platform == 'tt':
            r = _req.post('https://open.tiktokapis.com/v2/oauth/token/', data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_key': cfg.tiktok_client_key,
                'client_secret': cfg.tiktok_client_secret,
            }, timeout=10)
            new_token_data = r.json()

        elif platform == 'pi':
            r = _req.post('https://api.pinterest.com/v5/oauth/token', data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            }, auth=(cfg.pinterest_app_id, cfg.pinterest_app_secret), timeout=10)
            new_token_data = r.json()

        else:
            return JsonResponse({'error': f'Refresh not supported for platform: {platform}'}, status=400)

    except Exception as e:
        return JsonResponse({'error': f'Refresh failed: {str(e)}'}, status=502)

    if 'error' in new_token_data:
        return JsonResponse({'error': f"Platform error: {new_token_data.get('error_description', new_token_data.get('error'))}"}, status=502)

    return JsonResponse({
        'status': 'ok',
        'access_token': new_token_data.get('access_token', ''),
        'refresh_token': new_token_data.get('refresh_token', refresh_token),
        'expires_in': new_token_data.get('expires_in'),
    })


def try_voidpanel(request):
    from data.models import TryVoidPanelConfig
    config = TryVoidPanelConfig.get_config()
    if not config.is_enabled:
        return redirect('/')
    return render(request, 'try_voidpanel.html', {'config': config})


@login_required(login_url='/login/')
def super_admin_try_voidpanel(request):
    from data.models import TryVoidPanelConfig
    denied = _super_admin_guard(request)
    if denied:
        return denied

    config = TryVoidPanelConfig.get_config()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_try_voidpanel':
            config.is_enabled = bool(request.POST.get('is_enabled'))
            config.headline = request.POST.get('headline', '').strip()
            config.sub_headline = request.POST.get('sub_headline', '').strip()
            config.panel_url = request.POST.get('panel_url', '').strip()
            config.demo_username = request.POST.get('demo_username', '').strip()
            config.demo_password = request.POST.get('demo_password', '').strip()
            config.server_ip = request.POST.get('server_ip', '').strip()
            config.note = request.POST.get('note', '').strip()
            config.save()
            messages.success(request, "Try VoidPanel settings updated successfully!")
            return redirect('/super-admin/try-voidpanel/')

    context = _build_super_admin_context('try_voidpanel')
    context['config'] = config
    return render(request, 'super_admin_try_voidpanel.html', context)


@login_required(login_url='/login/')
def portal_delete_service(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'message': 'POST required'}, status=400)
    
    service_type = request.POST.get('service_type', '').strip()
    service_id = request.POST.get('service_id', '').strip()
    
    if not service_type or not service_id:
        return JsonResponse({'ok': False, 'message': 'Missing service_type or service_id'}, status=400)
        
    try:
        service_id = int(service_id)
    except ValueError:
        return JsonResponse({'ok': False, 'message': 'Invalid service ID'}, status=400)

    from data.models import HostingService, EmailService, SSLService, PanelLicenseRecord, PortalActivity

    # 1. Hosting Service
    if service_type == 'hosting':
        service = HostingService.objects.filter(id=service_id, user=request.user).first()
        if not service:
            return JsonResponse({'ok': False, 'message': 'Hosting service not found'}, status=404)
        
        # Call control panel API to terminate user if server is linked
        if service.server and service.panel_username:
            try:
                import requests as _rq
                _rq.post(
                    f"{service.server.url.rstrip('/')}/api/v2/terminate/",
                    headers={'X-VoidPanel-Key': service.server.api_key},
                    json={'username': service.panel_username},
                    timeout=10
                )
            except Exception as e:
                pass
        
        # Log activity
        PortalActivity.objects.create(
            user=request.user,
            category='account',
            title=f'Hosting terminated: {service.domain}',
            description=f'Service {service.service_name} for {service.domain} was deleted from client portal.',
        )
        service.delete()
        return JsonResponse({'ok': True, 'message': 'Hosting service deleted successfully.'})

    # 2. Email Service
    elif service_type == 'email':
        service = EmailService.objects.filter(id=service_id, user=request.user).first()
        if not service:
            return JsonResponse({'ok': False, 'message': 'Email service not found'}, status=404)
        
        # Log activity
        PortalActivity.objects.create(
            user=request.user,
            category='account',
            title=f'Email service deleted: {service.domain}',
            description=f'Email plan {service.plan_name} for {service.domain} was deleted.',
        )
        service.delete()
        return JsonResponse({'ok': True, 'message': 'Email service deleted successfully.'})

    # 3. SSL Service
    elif service_type == 'ssl':
        service = SSLService.objects.filter(id=service_id, user=request.user).first()
        if not service:
            return JsonResponse({'ok': False, 'message': 'SSL service not found'}, status=404)
        
        # Log activity
        PortalActivity.objects.create(
            user=request.user,
            category='account',
            title=f'SSL Certificate deleted: {service.domain}',
            description=f'SSL service {service.plan_name} for {service.domain} was deleted.',
        )
        service.delete()
        return JsonResponse({'ok': True, 'message': 'SSL service deleted successfully.'})

    # 4. License Service
    elif service_type == 'license':
        service = PanelLicenseRecord.objects.filter(id=service_id, user=request.user).first()
        if not service:
            return JsonResponse({'ok': False, 'message': 'Panel license not found'}, status=404)
        
        # Log activity
        PortalActivity.objects.create(
            user=request.user,
            category='account',
            title=f'VoidPanel License deleted',
            description=f'License key for host {service.hostname or "unknown"} was deleted.',
        )
        service.delete()
        return JsonResponse({'ok': True, 'message': 'Panel license deleted successfully.'})

    else:
        return JsonResponse({'ok': False, 'message': 'Unknown service type'}, status=400)


def terms_and_conditions(request):
    return render(request, "terms.html")


def privacy_policy(request):
    return render(request, "privacy.html")


def _call_suite_toggle_status(service, is_active):
    """Call control panel server API to enable/disable suite subscription."""
    server = service.server
    if not server:
        return False
    import urllib.request
    import json
    
    # Resolve backend URL: if server has login_url e.g. http://ip:8080/, use it
    base_url = server.login_url or f"http://{server.ip_address}:8080"
    url = f"{base_url.rstrip('/')}/control/api/suite/toggle-status/"
    headers = {
        'Content-Type': 'application/json',
        'X-Suite-API-Key': 'vp-suite-api-k3y-v01dp4nel2024!',
    }
    payload = {
        'email': service.user.email,
        'is_active': is_active,
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res.get('ok', False)
    except Exception as exc:
        _logger.error('_call_suite_toggle_status error for %s: %s', service.user.email, exc)
        return False


def super_admin_services(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_service_db_only':
            stype = request.POST.get('service_type')
            sid = request.POST.get('service_id')
            
            from data.models import HostingService, EmailService, SSLService, PanelLicenseRecord, SuiteService
            deleted_name = ""
            try:
                if stype == 'hosting':
                    obj = HostingService.objects.filter(id=sid).first()
                    if obj:
                        deleted_name = f"Hosting: {obj.domain}"
                        obj.delete()
                elif stype == 'email':
                    obj = EmailService.objects.filter(id=sid).first()
                    if obj:
                        deleted_name = f"Email: {obj.domain}"
                        obj.delete()
                elif stype == 'ssl':
                    obj = SSLService.objects.filter(id=sid).first()
                    if obj:
                        deleted_name = f"SSL: {obj.domain}"
                        obj.delete()
                elif stype == 'license':
                    obj = PanelLicenseRecord.objects.filter(id=sid).first()
                    if obj:
                        deleted_name = f"License: {obj.key[:8]}..."
                        obj.delete()
                elif stype == 'suite':
                    obj = SuiteService.objects.filter(id=sid).first()
                    if obj:
                        deleted_name = f"Suite: {obj.service_name}"
                        obj.delete()
                
                if deleted_name:
                    messages.success(request, f"Successfully erased '{deleted_name}' from the database only.")
                else:
                    messages.error(request, f"Service not found or already deleted.")
            except Exception as e:
                messages.error(request, f"Error deleting service: {e}")
            
            return redirect('/super-admin/services/')

        elif action == 'suspend_suite':
            sid = request.POST.get('service_id')
            from data.models import SuiteService
            service = SuiteService.objects.filter(id=sid).first()
            if service:
                service.status = 'suspended'
                service.save(update_fields=['status'])
                _call_suite_toggle_status(service, is_active=False)
                messages.success(request, f"Suite service '{service.service_name}' suspended successfully.")
            else:
                messages.error(request, "Suite service not found.")
            return redirect('/super-admin/services/')

        elif action == 'unsuspend_suite':
            sid = request.POST.get('service_id')
            from data.models import SuiteService
            service = SuiteService.objects.filter(id=sid).first()
            if service:
                service.status = 'active'
                service.save(update_fields=['status'])
                _call_suite_toggle_status(service, is_active=True)
                messages.success(request, f"Suite service '{service.service_name}' unsuspended successfully.")
            else:
                messages.error(request, "Suite service not found.")
            return redirect('/super-admin/services/')

        if action == 'assign_hosting_service':
            user_id = request.POST.get('user_id')
            domain = request.POST.get('domain', '').strip().lower()
            service_name = request.POST.get('service_name', '').strip()
            server_id = request.POST.get('server_id')
            panel_username = request.POST.get('panel_username', '').strip()
            panel_password = request.POST.get('panel_password', '').strip()
            monthly_price = request.POST.get('monthly_price', '0')
            billing_cycle = request.POST.get('billing_cycle', 'monthly')
            next_due_date = request.POST.get('next_due_date')
            storage_gb = request.POST.get('storage_gb', '25')
            bandwidth_gb = request.POST.get('bandwidth_gb', '250')
            is_reseller = bool(request.POST.get('is_reseller'))

            from django.contrib.auth.models import User
            from data.models import VoidPanelServer, HostingService
            import datetime

            user_obj = User.objects.filter(id=user_id).first()
            server_obj = VoidPanelServer.objects.filter(id=server_id).first()

            if not user_obj:
                messages.error(request, "Selected client/user not found.")
                return redirect('/super-admin/services/')
            if not domain:
                messages.error(request, "Domain name is required.")
                return redirect('/super-admin/services/')

            try:
                if next_due_date:
                    due_date = datetime.datetime.strptime(next_due_date, '%Y-%m-%d').date()
                else:
                    due_date = datetime.date.today() + datetime.timedelta(days=30)
            except Exception:
                due_date = datetime.date.today() + datetime.timedelta(days=30)

            if server_obj:
                panel_url = server_obj.url
            else:
                panel_url = f"http://127.0.0.1:8080"

            try:
                HostingService.objects.create(
                    user=user_obj,
                    service_name=service_name or "Custom Shared Hosting Plan",
                    domain=domain,
                    product_type="Reseller Hosting" if is_reseller else "Shared Hosting",
                    status="active",
                    billing_cycle=billing_cycle,
                    monthly_price=Decimal(monthly_price),
                    next_due_date=due_date,
                    server_hostname=server_obj.name if server_obj else "Localhost",
                    panel_url=panel_url,
                    server=server_obj,
                    storage_gb=int(storage_gb),
                    bandwidth_gb=int(bandwidth_gb),
                    panel_username=panel_username,
                    panel_password=panel_password,
                    is_reseller=is_reseller
                )
                messages.success(request, f"Hosting service successfully assigned to {user_obj.username} for {domain}!")
            except Exception as e:
                messages.error(request, f"Error assigning service: {e}")

            return redirect('/super-admin/services/')

        if action == 'edit_hosting_service':
            sid = request.POST.get('service_id')
            from data.models import HostingService
            service = HostingService.objects.filter(id=sid).first()
            if not service:
                messages.error(request, "Hosting service not found.")
                return redirect('/super-admin/services/')

            user_id = request.POST.get('user_id')
            domain = request.POST.get('domain', '').strip().lower()
            service_name = request.POST.get('service_name', '').strip()
            server_id = request.POST.get('server_id')
            panel_username = request.POST.get('panel_username', '').strip()
            panel_password = request.POST.get('panel_password', '').strip()
            monthly_price = request.POST.get('monthly_price', '0')
            billing_cycle = request.POST.get('billing_cycle', 'monthly')
            next_due_date = request.POST.get('next_due_date')
            storage_gb = request.POST.get('storage_gb', '25')
            bandwidth_gb = request.POST.get('bandwidth_gb', '250')
            is_reseller = bool(request.POST.get('is_reseller'))

            from django.contrib.auth.models import User
            from data.models import VoidPanelServer
            import datetime

            user_obj = User.objects.filter(id=user_id).first()
            server_obj = VoidPanelServer.objects.filter(id=server_id).first()

            if not user_obj:
                messages.error(request, "Selected client/user not found.")
                return redirect('/super-admin/services/')
            if not domain:
                messages.error(request, "Domain name is required.")
                return redirect('/super-admin/services/')

            try:
                if next_due_date:
                    due_date = datetime.datetime.strptime(next_due_date, '%Y-%m-%d').date()
                else:
                    due_date = datetime.date.today() + datetime.timedelta(days=30)
            except Exception:
                due_date = datetime.date.today() + datetime.timedelta(days=30)

            if server_obj:
                panel_url = server_obj.url
            else:
                panel_url = f"http://127.0.0.1:8080"

            try:
                service.user = user_obj
                service.domain = domain
                service.service_name = service_name or "Custom Shared Hosting Plan"
                service.product_type = "Reseller Hosting" if is_reseller else "Shared Hosting"
                service.server = server_obj
                service.server_hostname = server_obj.name if server_obj else "Localhost"
                service.panel_url = panel_url
                service.panel_username = panel_username
                service.panel_password = panel_password
                service.monthly_price = Decimal(monthly_price)
                service.billing_cycle = billing_cycle
                service.next_due_date = due_date
                service.storage_gb = int(storage_gb)
                service.bandwidth_gb = int(bandwidth_gb)
                service.is_reseller = is_reseller
                service.save()
                messages.success(request, f"Hosting service details for {domain} updated successfully!")
            except Exception as e:
                messages.error(request, f"Error updating hosting service: {e}")

        if action == 'send_service_info_whatsapp':
            sid      = request.POST.get('service_id')
            wa_tpl_id = request.POST.get('wa_template_id', '')
            whatsapp_mode = request.POST.get('whatsapp_mode', 'full')
            from data.models import HostingService, GlobalWhatsAppTemplate
            service = HostingService.objects.filter(id=sid).first()
            if not service:
                messages.error(request, "Hosting service not found.")
                return redirect('/super-admin/services/')

            phone = None
            if service.user:
                try:
                    phone = service.user.customer_profile.phone
                except Exception:
                    pass

            if not phone:
                messages.error(request, "Customer does not have a phone number configured.")
                return redirect('/super-admin/services/')

            customer_name = service.user.get_full_name() or service.user.username
            panel_url = service.panel_url or (service.server.url if service.server else '—')
            if service.server and getattr(service.server, 'login_url', None):
                panel_url = service.server.login_url

            # ── Placeholder map ───────────────────────────────────────────────
            ph = {
                'name':      customer_name,
                'email':     service.user.email,
                'service':   service.service_name,
                'domain':    service.domain,
                'username':  service.panel_username or service.user.username,
                'password':  service.panel_password or '—',
                'panel_url': panel_url,
                'amount':    str(service.monthly_price),
                'storage':   str(service.storage_gb),
                'invoice_id': 'MANUAL',
                'date':      __import__('datetime').date.today().strftime('%B %d, %Y'),
            }

            def fill_wa_ph(text):
                for k, v in ph.items():
                    text = text.replace('{{' + k + '}}', str(v))
                return text

            if wa_tpl_id:
                tpl = GlobalWhatsAppTemplate.objects.filter(id=wa_tpl_id, is_active=True).first()
                if tpl:
                    msg = fill_wa_ph(tpl.body)
                else:
                    messages.error(request, 'Selected WA template not found.')
                    return redirect('/super-admin/services/')
            elif whatsapp_mode == 'full':
                msg = (
                    f"Hello {customer_name} 👋\n\n"
                    f"🔑 *Hosting Account Login Details*\n"
                    f"Plan: {service.service_name}\n"
                    f"Domain: {service.domain}\n"
                    f"Username: {service.panel_username or service.user.username}\n"
                    f"Password: {service.panel_password or '—'}\n"
                    f"Panel Login URL: {panel_url}\n"
                    f"Storage: {service.storage_gb} GB\n\n"
                    f"Thank you for choosing VoidPanel! 🚀"
                )
            else:
                msg = (
                    f"Hello {customer_name} 👋\n\n"
                    f"📋 *Hosting Service Overview*\n"
                    f"Plan: {service.service_name}\n"
                    f"Domain: {service.domain}\n"
                    f"Status: Active ✅\n"
                    f"Storage: {service.storage_gb} GB\n\n"
                    f"Thank you for choosing VoidPanel! 🚀"
                )

            res = _call_wa_api('send', method='POST', payload={'to': phone, 'message': msg})
            if res.get('ok') or res.get('success'):
                from data.models import WhatsAppLog
                WhatsAppLog.objects.create(
                    user=service.user,
                    phone_to=phone,
                    message=msg,
                    msg_type='alert',
                    status='sent'
                )
                messages.success(request, f"Account info WhatsApp sent to {phone} successfully!")
            else:
                err_msg = res.get('error', 'Daemon error')
                messages.error(request, f"Failed to send WhatsApp: {err_msg}")
            
            return redirect('/super-admin/services/')

        if action == 'send_service_info_email':
            sid        = request.POST.get('service_id')
            tpl_id     = request.POST.get('email_template_id', '')
            email_mode = request.POST.get('email_mode', 'full')
            from data.models import HostingService, GlobalEmailTemplate
            service = HostingService.objects.filter(id=sid).first()
            if not service:
                messages.error(request, "Hosting service not found.")
                return redirect('/super-admin/services/')

            from django.core.mail import EmailMessage
            from django.template.loader import render_to_string
            from data.models import OutboundEmailProfile
            from django.core.mail.backends.smtp import EmailBackend
            import re

            customer_name  = service.user.get_full_name() or service.user.username
            customer_email = service.user.email

            nameservers_list = []
            if service.server and service.server.nameservers:
                nameservers_list = [ns.strip() for ns in service.server.nameservers.split('\n') if ns.strip()]
            if not nameservers_list:
                nameservers_list = ['ns1.voidpanel.com', 'ns2.voidpanel.com']

            panel_url = service.panel_url or (service.server.url if service.server else '—')
            if service.server and getattr(service.server, 'login_url', None):
                panel_url = service.server.login_url

            # ── Placeholder map for {{...}} substitution ──────────────────────
            ph = {
                'name':        customer_name,
                'email':       customer_email,
                'domain':      service.domain,
                'service':     service.service_name,
                'plan_name':   service.service_name,
                'username':    service.panel_username or service.user.username,
                'password':    service.panel_password or '—',
                'panel_url':   panel_url,
                'amount':      str(service.monthly_price),
                'storage':     str(service.storage_gb),
                'invoice_id':  'MANUAL',
                'date':        __import__('datetime').date.today().strftime('%B %d, %Y'),
            }

            def fill_placeholders(text):
                for k, v in ph.items():
                    text = text.replace('{{' + k + '}}', str(v))
                return text

            # ── Use GlobalEmailTemplate if selected ───────────────────────────
            if tpl_id:
                tpl = GlobalEmailTemplate.objects.filter(id=tpl_id, is_active=True).first()
                if tpl:
                    html_msg = fill_placeholders(tpl.content_html)
                    subject  = fill_placeholders(tpl.subject) if tpl.subject else f'Message from VoidPanel — {customer_name}'
                else:
                    messages.error(request, 'Selected email template not found.')
                    return redirect('/super-admin/services/')
            else:
                # Fall back to legacy welcome_hosting template
                context = {
                    'customer_name': customer_name,
                    'customer_email': customer_email,
                    'domain': service.domain,
                    'plan_name': service.service_name,
                    'username': service.panel_username or service.user.username,
                    'password': service.panel_password or '—',
                    'panel_url': panel_url,
                    'storage_gb': service.storage_gb,
                    'nameservers': nameservers_list,
                    'hide_credentials': (email_mode == 'overview'),
                    'amount': service.monthly_price,
                    'invoice_number': 'MANUAL',
                }
                subject  = f'📋 Service Overview: {service.domain} — VoidPanel' if email_mode == 'overview' else f'🔑 Account Login Details: {service.domain} — VoidPanel'
                html_msg = render_to_string('emails/welcome_hosting.html', context)

            try:
                smtp_profile = (
                    OutboundEmailProfile.objects
                    .filter(is_active=True)
                    .order_by('-is_default')
                    .first()
                )
            except Exception:
                smtp_profile = None

            try:
                if smtp_profile:
                    email = EmailMessage(
                        subject=subject,
                        body=html_msg,
                        from_email=f'{smtp_profile.from_name or "VoidPanel"} <{smtp_profile.from_email}>',
                        to=[customer_email],
                        reply_to=[smtp_profile.reply_to_email] if smtp_profile.reply_to_email else [],
                    )
                    email.content_subtype = 'html'
                    backend = EmailBackend(
                        host=smtp_profile.smtp_host,
                        port=smtp_profile.smtp_port,
                        username=smtp_profile.smtp_username,
                        password=smtp_profile.smtp_password,
                        use_tls=smtp_profile.use_tls,
                        use_ssl=smtp_profile.use_ssl,
                        fail_silently=False,
                    )
                    backend.open()
                    backend.send_messages([email])
                    backend.close()
                else:
                    email = EmailMessage(
                        subject=subject,
                        body=html_msg,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[customer_email],
                    )
                    email.content_subtype = 'html'
                    email.send(fail_silently=False)
                messages.success(request, f"Account info email ({email_mode}) sent to {customer_email}!")
            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")

            return redirect('/super-admin/services/')

    # GET request
    from data.models import HostingService, EmailService, SSLService, PanelLicenseRecord, SuiteService
    from django.contrib.auth.models import User
    
    hosting_svcs = HostingService.objects.select_related('user', 'server').order_by('-created_at')
    email_svcs = EmailService.objects.select_related('user', 'server').order_by('-created_at')
    ssl_svcs = SSLService.objects.select_related('user', 'server').order_by('-created_at')
    license_svcs = PanelLicenseRecord.objects.select_related('user').order_by('-issued_at')
    suite_svcs = SuiteService.objects.select_related('user', 'server').order_by('-created_at')
    portal_users = User.objects.filter(is_staff=False, is_superuser=False).order_by('username')

    from data.models import GlobalEmailTemplate, GlobalWhatsAppTemplate
    email_tpls = GlobalEmailTemplate.objects.filter(is_active=True).order_by('name')
    wa_tpls    = GlobalWhatsAppTemplate.objects.filter(is_active=True).order_by('name')

    ctx = _build_super_admin_context('super_admin_services')
    ctx.update({
        'hosting_services': hosting_svcs,
        'email_services':   email_svcs,
        'ssl_services':     ssl_svcs,
        'license_services': license_svcs,
        'suite_services':   suite_svcs,
        'portal_users':     portal_users,
        'email_templates':  email_tpls,
        'wa_templates':     wa_tpls,
    })
    return render(request, 'super_admin_services.html', ctx)


def _call_wa_api(endpoint, method='GET', payload=None):
    import urllib.request
    import json
    url = f"http://127.0.0.1:3001/{endpoint.lstrip('/')}"
    headers = {
        'Content-Type': 'application/json',
    }
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as exc:
        _logger.error('WhatsApp local daemon API error for %s: %s', endpoint, exc)
        return {'ok': False, 'error': str(exc)}


def super_admin_whatsapp(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied

    from data.models import WhatsAppConfig, WhatsAppLog
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    config, created = WhatsAppConfig.objects.get_or_create(id=1)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_settings':
            config.is_enabled = request.POST.get('is_enabled') == 'on'
            config.phone_number = request.POST.get('phone_number', '').strip()
            config.alert_on_invoice_created = request.POST.get('alert_on_invoice_created') == 'on'
            config.alert_on_service_suspend = request.POST.get('alert_on_service_suspend') == 'on'
            config.alert_on_ticket_opened = request.POST.get('alert_on_ticket_opened') == 'on'
            config.save()
            messages.success(request, "WhatsApp integration settings updated successfully.")
            return redirect('/super-admin/whatsapp/')

        elif action == 'logout':
            res = _call_wa_api('logout', method='POST')
            messages.success(request, "Logged out from WhatsApp Web session.")
            return redirect('/super-admin/whatsapp/')

        elif action == 'send_test':
            phone = request.POST.get('phone_number', '').strip()
            message = request.POST.get('message', '').strip()
            if not phone or not message:
                messages.error(request, "Recipient phone and message content are required.")
            else:
                res = _call_wa_api('send', method='POST', payload={'to': phone, 'message': message})
                if res.get('ok'):
                    WhatsAppLog.objects.create(
                        phone_to=phone,
                        message=message,
                        msg_type='alert',
                        status='sent'
                    )
                    messages.success(request, f"Test message successfully sent to {phone}!")
                else:
                    err_msg = res.get('error', 'Unknown daemon error')
                    WhatsAppLog.objects.create(
                        phone_to=phone,
                        message=message,
                        msg_type='alert',
                        status='failed',
                        error_msg=err_msg
                    )
                    messages.error(request, f"Failed to send message: {err_msg}")
            return redirect('/super-admin/whatsapp/')

        elif action == 'broadcast':
            target_group = request.POST.get('target_group')
            message = request.POST.get('message', '').strip()
            if not message:
                messages.error(request, "Broadcast message content is required.")
                return redirect('/super-admin/whatsapp/')

            # Resolve contact list based on group
            contacts = []
            users_query = User.objects.filter(is_staff=False, is_superuser=False)
            
            for u in users_query:
                try:
                    ph = u.customer_profile.phone
                except Exception:
                    ph = None
                if not ph:
                    continue

                if target_group == 'all':
                    contacts.append(u)
                elif target_group == 'unpaid_invoices':
                    from data.models import Invoice
                    if Invoice.objects.filter(user=u, status='unpaid').exists():
                        contacts.append(u)
                elif target_group == 'active_hosting':
                    from data.models import HostingService
                    if HostingService.objects.filter(user=u, status='active').exists():
                        contacts.append(u)

            if not contacts:
                messages.error(request, "No clients found with valid phone numbers in this group.")
                return redirect('/super-admin/whatsapp/')

            # Prepare broadcast dispatch payload
            phone_list = [c.customer_profile.phone for c in contacts]
            
            # Send asynchronously using threading to prevent browser wait
            def run_broadcast_async(phones, text, users_map):
                res = _call_wa_api('broadcast', method='POST', payload={'contacts': phones, 'message': text})
                for r in res.get('results', []):
                    usr = users_map.get(r['to'])
                    WhatsAppLog.objects.create(
                        user=usr,
                        phone_to=r['to'],
                        message=text,
                        msg_type='broadcast',
                        status='sent' if r.get('ok') else 'failed',
                        error_msg='' if r.get('ok') else r.get('error', 'Daemon error')
                    )

            users_map = {u.customer_profile.phone: u for u in contacts}
            import threading
            threading.Thread(target=run_broadcast_async, args=(phone_list, message, users_map), daemon=True).start()

            messages.success(request, f"Broadcast bulk send triggered for {len(phone_list)} clients in the background.")
            return redirect('/super-admin/whatsapp/')

    # GET Request: Fetch status & QR code
    status_res = _call_wa_api('status')
    state = status_res.get('state', 'idle')
    qr_code = None
    
    if state != 'connected':
        qr_res = _call_wa_api('qr')
        qr_code = qr_res.get('qr')
        state = qr_res.get('state', state)

    logs = WhatsAppLog.objects.select_related('user').order_by('-created_at')[:20]

    ctx = _build_super_admin_context('whatsapp')
    ctx.update({
        'config': config,
        'state': state,
        'qr_code': qr_code,
        'logs': logs,
    })
    return render(request, 'super_admin_whatsapp.html', ctx)


def send_whatsapp_notification_async(user, message, alert_type):
    """
    Sends a WhatsApp message in a background thread if WhatsApp integration is enabled
    and the target number is registered.
    """
    import threading
    
    def _run():
        from data.models import WhatsAppConfig, WhatsAppLog
        config = WhatsAppConfig.objects.filter(id=1).first()
        if not config or not config.is_enabled:
            return
            
        if alert_type == 'invoice_created' and not config.alert_on_invoice_created:
            return
        if alert_type == 'service_suspend' and not config.alert_on_service_suspend:
            return
        if alert_type == 'ticket_opened' and not config.alert_on_ticket_opened:
            return

        phone = None
        if user and user.is_authenticated:
            try:
                phone = user.customer_profile.phone
            except Exception:
                pass

        if not phone:
            # If no client phone, fallback to admin's configured phone for alert monitoring
            if alert_type == 'ticket_opened' and config.phone_number:
                phone = config.phone_number
            else:
                return

        res = _call_wa_api('send', method='POST', payload={'to': phone, 'message': message})
        is_ok = res.get('ok') or res.get('success') or False
        WhatsAppLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            phone_to=phone,
            message=message,
            msg_type='alert',
            status='sent' if is_ok else 'failed',
            error_msg='' if is_ok else res.get('error', 'Daemon error')
        )

    threading.Thread(target=_run, daemon=True).start()


from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def api_global_templates(request):
    from data.models import GlobalEmailTemplate
    templates = []
    for t in GlobalEmailTemplate.objects.filter(is_active=True):
        templates.append({
            'id': t.id,
            'name': t.name,
            'subject': t.subject,
            'content_html': t.content_html,
        })
    return JsonResponse({'global_templates': templates})


# ══════════════════════════════════════════════════════════════════════════════
#  DIGITAL SUITES — PUBLIC LANDING PAGES
# ══════════════════════════════════════════════════════════════════════════════

def social_media_suite_page(request):
    plans = list(SuitePlan.objects.filter(suite='social', is_active=True).order_by('sort_order', 'monthly_price'))
    return render(request, 'social_suite.html', {'plans': plans, 'suite': 'social',
        'suite_title': 'Social Media Suite', 'suite_color': '#f472b6',
        'suite_tagline': 'Schedule, publish and analyse your social presence across every platform — all in one place.',
        'suite_icon': 'fa-brands fa-instagram'})


def seo_suite_page(request):
    plans = list(SuitePlan.objects.filter(suite='seo', is_active=True).order_by('sort_order', 'monthly_price'))
    return render(request, 'seo_suite.html', {'plans': plans, 'suite': 'seo',
        'suite_title': 'SEO Suite', 'suite_color': '#818cf8',
        'suite_tagline': 'Rank higher, track keywords, audit your site and outrank competitors with AI-powered SEO tools.',
        'suite_icon': 'fa-solid fa-magnifying-glass-chart'})


def marketing_suite_page(request):
    plans = list(SuitePlan.objects.filter(suite='marketing', is_active=True).order_by('sort_order', 'monthly_price'))
    return render(request, 'marketing_suite.html', {'plans': plans, 'suite': 'marketing',
        'suite_title': 'Marketing Suite', 'suite_color': '#fbbf24',
        'suite_tagline': 'Run email campaigns, manage leads, automate follow-ups and grow your audience on autopilot.',
        'suite_icon': 'fa-solid fa-bullhorn'})


# ══════════════════════════════════════════════════════════════════════════════
#  DIGITAL SUITES — BUY FLOW
# ══════════════════════════════════════════════════════════════════════════════

@login_required(login_url='/login/')
def suite_order_configure(request, suite, plan_id):
    """Step 1: User picks a plan → selects billing cycle → session → checkout."""
    VALID_SUITES = ('social', 'seo', 'marketing')
    if suite not in VALID_SUITES:
        from django.http import Http404
        raise Http404('Unknown suite')

    try:
        plan = SuitePlan.objects.get(pk=plan_id, suite=suite, is_active=True)
    except SuitePlan.DoesNotExist:
        messages.error(request, 'Plan not found or no longer available.')
        slug_map = {'social': 'social-media-suite', 'seo': 'seo-suite', 'marketing': 'marketing-suite'}
        return redirect(f'/{slug_map.get(suite, suite)}/')

    if request.method == 'POST':
        billing_cycle = request.POST.get('billing_cycle', 'monthly')
        if billing_cycle not in ('monthly', 'annually'):
            billing_cycle = 'monthly'

        existing = SuiteService.objects.filter(user=request.user, suite=suite, status__in=['active', 'pending']).first()
        if existing:
            messages.warning(request, f'You already have an active {plan.get_suite_display()} subscription.')
            return redirect('/portal/')

        coupon_code = request.POST.get('coupon_code', '').strip().upper()

        request.session['suite_order'] = {
            'plan_id': plan.pk,
            'suite': suite,
            'billing_cycle': billing_cycle,
            'coupon_code': coupon_code
        }
        return redirect('suite_checkout')

    return render(request, 'suite_configure.html', {'plan': plan, 'suite': suite})


@login_required(login_url='/login/')
def suite_checkout(request):
    """Step 2: Creates Invoice + SuiteOrder, attempts wallet auto-pay, else shows Razorpay."""
    session_data = request.session.get('suite_order')
    if not session_data:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('/')

    plan_id       = session_data.get('plan_id')
    suite         = session_data.get('suite')
    billing_cycle = session_data.get('billing_cycle', 'monthly')
    coupon_code   = session_data.get('coupon_code', '').strip().upper()

    try:
        plan = SuitePlan.objects.get(pk=plan_id, is_active=True)
    except SuitePlan.DoesNotExist:
        messages.error(request, 'Plan not found.')
        return redirect('/')

    if billing_cycle == 'annually' and plan.yearly_price:
        price = plan.yearly_price
        cycle_label = 'Annual'
    else:
        price = plan.monthly_price
        cycle_label = 'Monthly'

    from decimal import Decimal
    applied_coupon = None
    desc_suffix = ""
    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if coupon and coupon.is_valid(billing_cycle=billing_cycle):
            applied_coupon = coupon
            if coupon.discount_type == 'percentage':
                price = price * (1 - (coupon.discount_value / Decimal('100')))
                desc_suffix = f" (Coupon: {coupon.code} - {coupon.discount_value}% off)"
            else:
                price = price - coupon.discount_value
                desc_suffix = f" (Coupon: {coupon.code} - ₹{coupon.discount_value} off)"
            price = max(price, Decimal('0.00'))

    price = price.quantize(Decimal('0.01'))
    suite_display = plan.get_suite_display()

    with transaction.atomic():
        inv_count = Invoice.objects.filter(user=request.user).count()
        invoice = Invoice.objects.create(
            user=request.user,
            invoice_number=f'VP-{request.user.id:04d}-{inv_count + 1:03d}',
            status='unpaid', total=price,
            due_date=(timezone.now() + timedelta(days=3)).date(),
            description=f"{plan.name} {suite_display} — {cycle_label}{desc_suffix}",
        )
        suite_order = SuiteOrder.objects.create(
            user=request.user, invoice=invoice, plan=plan,
            suite=suite, billing_cycle=billing_cycle, price=price, status='pending_payment',
        )
        PortalActivity.objects.create(
            user=request.user, category='billing',
            title=f'{suite_display} order created: {plan.name}',
            description=f'Invoice #{invoice.invoice_number} — ₹{price} ({cycle_label}){desc_suffix}',
        )

    request.session['suite_order'] = {**session_data, 'invoice_id': invoice.pk, 'suite_order_id': suite_order.pk}

    # Wallet auto-pay
    try:
        profile = CustomerProfile.objects.get(user=request.user)
        if profile.balance_funds >= price:
            with transaction.atomic():
                profile.balance_funds -= price
                profile.save(update_fields=['balance_funds'])
                invoice.status = 'paid'
                invoice.save(update_fields=['status'])
                suite_order.status = 'paid'
                suite_order.save(update_fields=['status'])
                _activate_suite_service(suite_order)
            del request.session['suite_order']
            messages.success(request, f'✅ {suite_display} — {plan.name} activated! Wallet debited ₹{price}.')
            return redirect('/portal/')
    except CustomerProfile.DoesNotExist:
        pass

    return render(request, 'invoice_pay.html', {'invoice': invoice, 'suite_order': suite_order, 'plan': plan})


def _send_suite_welcome_email(service, invoice=None):
    """
    Send a welcome email for Digital Suite activation.
    Uses OutboundEmailProfile (if configured) or falls back to Django EMAIL_* settings.
    """
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail.backends.smtp import EmailBackend
    from data.models import OutboundEmailProfile

    customer_name  = service.user.get_full_name() or service.user.username
    customer_email = service.user.email
    if not customer_email:
        return

    context = {
        'customer_name':  customer_name,
        'customer_email': customer_email,
        'plan_name':      service.service_name,
        'plan_level':     service.plan.name,
        'suite_display':  service.plan.get_suite_display(),
        'billing_cycle':  service.billing_cycle,
        'invoice_number': invoice.invoice_number if invoice else '—',
        'amount':         invoice.total if invoice else '—',
    }

    subject  = f'🎉 Your Digital Suite is Ready: {service.plan.get_suite_display()} — VoidPanel'
    html_msg = render_to_string('emails/welcome_suite.html', context)

    # Try OutboundEmailProfile first
    try:
        smtp_profile = (
            OutboundEmailProfile.objects
            .filter(is_active=True, send_on_service_activated=True)
            .order_by('-is_default')
            .first()
        )
    except Exception:
        smtp_profile = None

    try:
        if smtp_profile:
            email = EmailMessage(
                subject=subject,
                body=html_msg,
                from_email=f'{smtp_profile.from_name or "VoidPanel"} <{smtp_profile.from_email}>',
                to=[customer_email],
                reply_to=[smtp_profile.reply_to_email] if smtp_profile.reply_to_email else [],
            )
            email.content_subtype = 'html'
            backend = EmailBackend(
                host=smtp_profile.smtp_host,
                port=smtp_profile.smtp_port,
                username=smtp_profile.smtp_username,
                password=smtp_profile.smtp_password,
                use_tls=smtp_profile.use_tls,
                use_ssl=smtp_profile.use_ssl,
                fail_silently=False,
            )
            backend.open()
            backend.send_messages([email])
            backend.close()
        else:
            email = EmailMessage(
                subject=subject,
                body=html_msg,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer_email],
            )
            email.content_subtype = 'html'
            email.send(fail_silently=False)

        _logger.info('Digital Suite welcome email sent to %s', customer_email)
    except Exception as exc:
        _logger.error('Failed to send digital suite welcome email to %s: %s', customer_email, exc)


def _activate_suite_service(suite_order):
    """Internal: called after confirmed payment. Creates SuiteService."""
    plan          = suite_order.plan
    billing_cycle = suite_order.billing_cycle
    due_date      = (timezone.now() + timedelta(days=365 if billing_cycle == 'annually' else 30)).date()

    # Increment Coupon uses if found in invoice description
    try:
        import re
        from data.models import Coupon
        if suite_order.invoice and suite_order.invoice.description:
            match = re.search(r'\(Coupon:\s*([A-Za-z0-9_-]+)\s*-', suite_order.invoice.description)
            if match:
                coupon_code = match.group(1)
                coupon = Coupon.objects.filter(code=coupon_code).first()
                if coupon:
                    coupon.current_uses += 1
                    coupon.save(update_fields=['current_uses'])
    except Exception as e:
        pass

    service = SuiteService.objects.create(
        user=suite_order.user, plan=plan, suite=plan.suite,
        service_name=f"{plan.get_suite_display()} — {plan.name}",
        status='active', billing_cycle=billing_cycle,
        monthly_price=plan.monthly_price, server=plan.server,
        next_due_date=due_date, activated_at=timezone.now(),
    )
    suite_order.status = 'paid'
    suite_order.save(update_fields=['status'])

    PortalActivity.objects.create(
        user=suite_order.user, category='service',
        title=f'{plan.get_suite_display()} activated',
        description=f'Plan: {plan.name} | Billing: {billing_cycle}',
    )
    threading.Thread(target=_send_suite_welcome_email, args=(service, suite_order.invoice), daemon=True).start()
    threading.Thread(target=_provision_suite_on_panel, args=(service,), daemon=True).start()
    return service


def _provision_suite_on_panel(service):
    """Call VoidPanel server API to create suite account. Silent on failure."""
    try:
        server = service.server
        if not server:
            return
        import urllib.request
        import json
        panel_url = (server.login_url or server.url or '').rstrip('/')
        email     = service.user.email or f'{service.user.username}@voidpanel.site'
        payload   = json.dumps({
            'email': email,
            'first_name': service.user.first_name or service.user.username,
            'last_name': service.user.last_name or '',
            'suite': service.suite,
            'plan_slug': service.plan.panel_plan_slug or service.plan.name,
            'auto_login': False
        }).encode('utf-8')
        req = urllib.request.Request(f'{panel_url}/control/api/suite/create-account/',
                                     data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('X-Suite-API-Key', 'vp-suite-api-k3y-v01dp4nel2024!')
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  DIGITAL SUITES — PORTAL SSO LAUNCH
# ══════════════════════════════════════════════════════════════════════════════

@login_required(login_url='/login/')
def portal_suite_sso(request, service_id):
    """Call VoidPanel server API to get a one-time SSO token and redirect user."""
    service = get_object_or_404(SuiteService, pk=service_id, user=request.user)
    if not service.is_active:
        messages.error(request, 'This suite service is not active.')
        return redirect('/portal/')

    base  = service.panel_base_url
    if not base:
        messages.error(request, 'No panel server configured for this service. Contact support.')
        return redirect('/portal/')

    import urllib.request
    import json
    
    try:
        email = service.user.email or f'{service.user.username}@voidpanel.site'
        payload = json.dumps({
            'hosting_domain': service.user.username,
            'user_email': email,
            'suite': service.suite,
            'plan_slug': service.plan.panel_plan_slug or service.plan.name
        }).encode('utf-8')
        
        req = urllib.request.Request(f'{base}/control/api/suite/sso-token/',
                                     data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('X-Suite-API-Key', 'vp-suite-api-k3y-v01dp4nel2024!')
        
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if data.get('ok') and data.get('sso_url'):
            return redirect(f"{base}{data['sso_url']}")
        else:
            messages.error(request, f"Error generating login link: {data.get('error', 'Unknown error')}")
    except Exception as e:
        messages.error(request, f"Failed to connect to control panel: {str(e)}")
        
    return redirect('/portal/')


# ══════════════════════════════════════════════════════════════════════════════
#  DIGITAL SUITES — SUPER-ADMIN PLAN MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def super_admin_suite_plans(request):
    """/super-admin/suite-plans/ — full CRUD for SuitePlan."""
    denied = _super_admin_guard(request)
    if denied:
        return denied

    servers = VoidPanelServer.objects.filter(is_active=True).order_by('name')

    # Get suite query param
    selected_suite = request.GET.get('suite', '').strip().lower()
    if selected_suite not in ['social', 'seo', 'marketing']:
        selected_suite = ''

    redirect_url = 'super_admin_suite_plans'
    if selected_suite:
        redirect_url += f'?suite={selected_suite}'

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'delete':
            plan_id = request.POST.get('plan_id')
            try:
                plan = SuitePlan.objects.get(pk=plan_id)
                if SuiteService.objects.filter(plan=plan, status__in=['active', 'pending']).exists():
                    messages.error(request, f'Cannot delete "{plan.name}" — it has active services.')
                else:
                    plan.delete()
                    messages.success(request, 'Plan deleted.')
            except SuitePlan.DoesNotExist:
                messages.error(request, 'Plan not found.')
            return redirect(redirect_url)

        suite         = request.POST.get('suite', '').strip()
        name          = request.POST.get('name', '').strip()
        slug          = request.POST.get('slug', '').strip()
        short_desc    = request.POST.get('short_description', '').strip()
        monthly_price = request.POST.get('monthly_price', '0').strip()
        yearly_price  = request.POST.get('yearly_price', '0').strip()
        server_id     = request.POST.get('server_id', '').strip()
        panel_slug    = request.POST.get('panel_plan_slug', '').strip()
        sort_order    = request.POST.get('sort_order', '0').strip()
        is_featured   = bool(request.POST.get('is_featured'))
        is_active     = bool(request.POST.get('is_active'))
        plan_id       = request.POST.get('plan_id', '').strip()

        features = [f.strip() for f in request.POST.get('features', '').splitlines() if f.strip()]
        limits   = {}
        for line in request.POST.get('limits', '').splitlines():
            if '=' in line:
                k, _, v = line.partition('=')
                try:
                    limits[k.strip()] = int(v.strip())
                except ValueError:
                    limits[k.strip()] = v.strip()

        if not name or not suite:
            messages.error(request, 'Name and suite are required.')
            return redirect(redirect_url)

        if not slug:
            from django.template.defaultfilters import slugify as _slugify
            slug = _slugify(f'{suite}-{name}')

        server_obj = VoidPanelServer.objects.filter(pk=server_id).first() if server_id else None

        from decimal import Decimal as _D
        try:
            mp = _D(monthly_price)
            yp = _D(yearly_price)
        except Exception:
            mp = yp = _D('0')

        so = int(sort_order or 0)

        if action == 'edit' and plan_id:
            try:
                plan = SuitePlan.objects.get(pk=plan_id)
                plan.suite = suite; plan.name = name; plan.slug = slug
                plan.short_description = short_desc; plan.monthly_price = mp
                plan.yearly_price = yp; plan.server = server_obj
                plan.panel_plan_slug = panel_slug; plan.features = features
                plan.limits = limits; plan.sort_order = so
                plan.is_featured = is_featured; plan.is_active = is_active
                plan.save()
                messages.success(request, f'Plan "{name}" updated.')
            except SuitePlan.DoesNotExist:
                messages.error(request, 'Plan not found.')
        else:
            SuitePlan.objects.create(
                suite=suite, name=name, slug=slug, short_description=short_desc,
                monthly_price=mp, yearly_price=yp, server=server_obj,
                panel_plan_slug=panel_slug, features=features, limits=limits,
                sort_order=so, is_featured=is_featured, is_active=is_active,
            )
            messages.success(request, f'Plan "{name}" created.')

        return redirect(redirect_url)

    plans = SuitePlan.objects.select_related('server').order_by('suite', 'sort_order')
    if selected_suite:
        plans = plans.filter(suite=selected_suite)

    ctx   = _build_super_admin_context('suite_plans')
    ctx.update({
        'plans': plans,
        'servers': servers,
        'suite_choices': SuitePlan.SUITE_CHOICES,
        'current_suite': selected_suite
    })
    return render(request, 'super_admin_suite_plans.html', ctx)



# ── Base Email & WhatsApp Templates Manager ────────────────────────────────────

@login_required
def super_admin_base_email(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied

    from data.models import GlobalEmailTemplate, GlobalWhatsAppTemplate

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'create_email':
            name     = request.POST.get('name', '').strip()
            subject  = request.POST.get('subject', '').strip()
            category = request.POST.get('category', 'general')
            html     = request.POST.get('content_html', '').strip()
            if not name or not html:
                messages.error(request, 'Name and HTML content are required.')
            else:
                GlobalEmailTemplate.objects.create(name=name, subject=subject, category=category, content_html=html)
                messages.success(request, f'Email template "{name}" created successfully.')
            return redirect('/super-admin/base-email/')

        elif action == 'edit_email':
            tid = request.POST.get('template_id')
            try:
                tpl = GlobalEmailTemplate.objects.get(id=tid)
                tpl.name         = request.POST.get('name', tpl.name).strip()
                tpl.subject      = request.POST.get('subject', tpl.subject).strip()
                tpl.category     = request.POST.get('category', tpl.category)
                tpl.content_html = request.POST.get('content_html', tpl.content_html).strip()
                tpl.is_active    = request.POST.get('is_active') == 'on'
                tpl.save()
                messages.success(request, f'Email template "{tpl.name}" updated.')
            except GlobalEmailTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
            return redirect('/super-admin/base-email/')

        elif action == 'delete_email':
            tid = request.POST.get('template_id')
            try:
                tpl = GlobalEmailTemplate.objects.get(id=tid)
                name = tpl.name
                tpl.delete()
                messages.success(request, f'Email template "{name}" deleted.')
            except GlobalEmailTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
            return redirect('/super-admin/base-email/')

        elif action == 'toggle_email':
            tid = request.POST.get('template_id')
            try:
                tpl = GlobalEmailTemplate.objects.get(id=tid)
                tpl.is_active = not tpl.is_active
                tpl.save(update_fields=['is_active'])
                messages.success(request, f'Template {"activated" if tpl.is_active else "deactivated"}.')
            except GlobalEmailTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
            return redirect('/super-admin/base-email/')

        elif action == 'create_wa':
            name     = request.POST.get('wa_name', '').strip()
            category = request.POST.get('wa_category', 'general')
            body     = request.POST.get('wa_body', '').strip()
            if not name or not body:
                messages.error(request, 'Name and body are required.')
            else:
                GlobalWhatsAppTemplate.objects.create(name=name, category=category, body=body)
                messages.success(request, f'WhatsApp template "{name}" created.')
            return redirect('/super-admin/base-email/?tab=whatsapp')

        elif action == 'edit_wa':
            tid = request.POST.get('wa_id')
            try:
                tpl = GlobalWhatsAppTemplate.objects.get(id=tid)
                tpl.name      = request.POST.get('wa_name', tpl.name).strip()
                tpl.category  = request.POST.get('wa_category', tpl.category)
                tpl.body      = request.POST.get('wa_body', tpl.body).strip()
                tpl.is_active = request.POST.get('is_active') == 'on'
                tpl.save()
                messages.success(request, f'WhatsApp template "{tpl.name}" updated.')
            except GlobalWhatsAppTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
            return redirect('/super-admin/base-email/?tab=whatsapp')

        elif action == 'delete_wa':
            tid = request.POST.get('wa_id')
            try:
                tpl = GlobalWhatsAppTemplate.objects.get(id=tid)
                name = tpl.name
                tpl.delete()
                messages.success(request, f'WhatsApp template "{name}" deleted.')
            except GlobalWhatsAppTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
            return redirect('/super-admin/base-email/?tab=whatsapp')

        elif action == 'toggle_wa':
            tid = request.POST.get('wa_id')
            try:
                tpl = GlobalWhatsAppTemplate.objects.get(id=tid)
                tpl.is_active = not tpl.is_active
                tpl.save(update_fields=['is_active'])
                messages.success(request, f'Template {"activated" if tpl.is_active else "deactivated"}.')
            except GlobalWhatsAppTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
            return redirect('/super-admin/base-email/?tab=whatsapp')

    email_templates = GlobalEmailTemplate.objects.all()
    wa_templates    = GlobalWhatsAppTemplate.objects.all()

    ctx = _build_super_admin_context('base_email')
    ctx.update({
        'email_templates':  email_templates,
        'wa_templates':     wa_templates,
        'email_categories': GlobalEmailTemplate.CATEGORY_CHOICES,
        'wa_categories':    GlobalWhatsAppTemplate.CATEGORY_CHOICES,
        'active_tab':       request.GET.get('tab', 'email'),
    })
    return render(request, 'super_admin_base_email.html', ctx)
