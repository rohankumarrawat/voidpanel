"""
VoidApp API — Email management endpoints.

GET    /api/v1/emails/                        — List email accounts
POST   /api/v1/emails/create/                 — Create email account
POST   /api/v1/emails/delete/                 — Delete email account
POST   /api/v1/emails/change-password/        — Change email password
GET    /api/v1/emails/whitelist/              — List whitelisted IPs for VoidMail AI
POST   /api/v1/emails/whitelist/add/          — Add IP to VoidMail AI whitelist
POST   /api/v1/emails/whitelist/remove/       — Remove IP from whitelist
GET    /api/v1/emails/ai-status/              — Check if caller IP is whitelisted for AI
"""

import os
import sys
import base64
import shlex
import logging
import subprocess

from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings

from control.models import (
    allemail, domain as Domain, user as CtrlUser, package as Package,
    VoidMailWhitelistIP, VoidMailUpgradeLead, VoidMailWhitelistedDomain, EmailDeviceToken,
    VoidMailAppLogin,
)
from control.fcm_service import send_fcm_push_to_email, broadcast_fcm_push

from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')



@api_auth_required()
def api_email_list(request):
    """List all email accounts for the current user's domain."""
    ctrl_user = request.ctrl_user
    emails = allemail.objects.filter(domain=ctrl_user.domain)

    email_list = []
    for em in emails:
        email_list.append({
            'id': em.id,
            'email': em.email,
            'domain': em.domain,
        })

    # Get quota info
    pkg = _get_pkg(ctrl_user.hosting_package)
    total = _safe_int(pkg.email_accounts) if pkg else 0

    return api_response(data={
        'emails': email_list,
        'used': len(email_list),
        'total': total,
        'unlimited': total == 0,
    })


@api_auth_required()
@require_post
def api_email_create(request):
    """
    Create a new email account.

    POST body:
    {
        "username": "info",
        "password": "SecurePass123!"
    }
    """
    data = parse_json_body(request)
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    ctrl_user = request.ctrl_user
    domain_name = ctrl_user.domain

    # Validation
    if not username:
        return api_response(error='Email username is required.', status=400)
    if not password or len(password) < 6:
        return api_response(error='Password must be at least 6 characters.', status=400)

    # Sanitise username — only alphanumeric, dots, dashes, underscores
    import re
    if not re.match(r'^[a-z0-9._-]+$', username):
        return api_response(error='Invalid email username. Use only letters, numbers, dots, dashes.', status=400)

    full_email = f'{username}@{domain_name}'

    # Check if already exists
    if allemail.objects.filter(email=full_email).exists():
        return api_response(error='Email account already exists.', status=409)

    # Check quota
    pkg = _get_pkg(ctrl_user.hosting_package)
    if pkg:
        max_emails = _safe_int(pkg.email_accounts)
        if max_emails > 0:
            current = allemail.objects.filter(domain=domain_name).count()
            if current >= max_emails:
                return api_response(
                    error=f'Quota exceeded. Maximum {max_emails} email accounts allowed.',
                    status=403
                )

    # Create the email account on the system
    try:
        from function import run_command
        from voidplatform.config import paths
        import tempfile

        if sys.platform != 'win32':
            # Add domain to virtual domains
            with tempfile.NamedTemporaryFile('w', delete=False) as tf:
                tf.write(f'{domain_name}\n')
                tmp_domain = tf.name
            run_command(f"sudo bash -c 'grep -q \"^{domain_name}$\" {paths.POSTFIX_VIRTUAL_DOMAINS} || cat {tmp_domain} >> {paths.POSTFIX_VIRTUAL_DOMAINS}'")

            # Add alias mapping
            with tempfile.NamedTemporaryFile('w', delete=False) as tf:
                tf.write(f'{full_email} {full_email}\n')
                tmp_alias = tf.name
            run_command(f"sudo bash -c 'grep -q \"^{full_email} \" {paths.POSTFIX_VIRTUAL_ALIAS} || cat {tmp_alias} >> {paths.POSTFIX_VIRTUAL_ALIAS}'")

            run_command(f'sudo postmap {paths.POSTFIX_VIRTUAL_ALIAS}')
            run_command(f'sudo postmap {paths.POSTFIX_VIRTUAL_DOMAINS}')

            # Determine system owner
            sys_owner = ctrl_user.username

            # Run the email provisioning script
            script_path = os.path.join(paths.PANEL_ROOT, 'emailadd.sh')
            script_cmd = f'sudo bash {shlex.quote(script_path)} {shlex.quote(full_email)} {shlex.quote(password)} {shlex.quote(sys_owner)}'
            run_command(script_cmd)

        # Save to database
        password_b64 = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        email_obj = allemail.objects.create(
            domain=domain_name,
            email=full_email,
            password=password_b64
        )

        # Log activity
        try:
            from control.activity import log_activity
            log_activity(request, 'success', 'email', domain=domain_name,
                         action=f'Email account created: {full_email}',
                         detail='Created via VoidApp API')
        except Exception:
            pass

        return api_response(data={
            'id': email_obj.id,
            'email': full_email,
            'message': 'Email account created successfully.'
        })

    except Exception as e:
        logger.exception('Failed to create email %s', full_email)
        return api_response(error=f'Failed to create email: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_email_delete(request):
    """
    Delete an email account.

    POST body: { "email": "info@example.com" }
    """
    data = parse_json_body(request)
    email = data.get('email', '').strip().lower()
    ctrl_user = request.ctrl_user

    if not email:
        return api_response(error='Email address is required.', status=400)

    # Ownership check
    try:
        email_obj = allemail.objects.get(email=email, domain=ctrl_user.domain)
    except allemail.DoesNotExist:
        return api_response(error='Email account not found.', status=404)

    # Delete from system
    try:
        if sys.platform != 'win32':
            from function import run_command
            from voidplatform.config import paths

            # Remove from Dovecot users file
            dovecot_users = '/etc/dovecot/users'
            if os.path.exists(dovecot_users):
                run_command(f"sudo sed -i '/^{email}:/d' {dovecot_users}")

            # Remove from virtual alias map
            run_command(f"sudo sed -i '/^{email} /d' {paths.POSTFIX_VIRTUAL_ALIAS}")
            run_command(f'sudo postmap {paths.POSTFIX_VIRTUAL_ALIAS}')

            # Reload Dovecot
            subprocess.run(['sudo', 'systemctl', 'reload', 'dovecot'],
                           capture_output=True, check=False, timeout=10)
    except Exception as e:
        logger.warning('System-level email deletion partial failure for %s: %s', email, e)

    # Delete from database
    email_obj.delete()

    try:
        from control.activity import log_activity
        log_activity(request, 'success', 'email', domain=ctrl_user.domain,
                     action=f'Email account deleted: {email}',
                     detail='Deleted via VoidApp API')
    except Exception:
        pass

    return api_response(data={'message': f'Email account {email} deleted successfully.'})


@api_auth_required()
@require_post
def api_email_change_password(request):
    """
    Change password for an email account.

    POST body: { "email": "info@example.com", "password": "NewPass123!" }
    """
    data = parse_json_body(request)
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    ctrl_user = request.ctrl_user

    if not email or not password:
        return api_response(error='Email and new password are required.', status=400)
    if len(password) < 6:
        return api_response(error='Password must be at least 6 characters.', status=400)

    # Ownership check
    try:
        email_obj = allemail.objects.get(email=email, domain=ctrl_user.domain)
    except allemail.DoesNotExist:
        return api_response(error='Email account not found.', status=404)

    try:
        if sys.platform != 'win32':
            # Generate SHA512-CRYPT hash for Dovecot
            result = subprocess.run(
                ['doveadm', 'pw', '-s', 'SHA512-CRYPT', '-p', password],
                capture_output=True, text=True, timeout=10
            )
            hashed = result.stdout.strip()

            if hashed:
                dovecot_users = '/etc/dovecot/users'
                if os.path.exists(dovecot_users):
                    with open(dovecot_users, 'r') as f:
                        lines = f.readlines()
                    with open(dovecot_users, 'w') as f:
                        for line in lines:
                            if line.startswith(email + ':'):
                                parts = line.strip().split(':')
                                rest = ':'.join(parts[2:]) if len(parts) > 2 else '5000:5000::'
                                f.write(f'{email}:{hashed}:{rest}\n')
                            else:
                                f.write(line)

                    subprocess.run(['sudo', 'systemctl', 'reload', 'dovecot'],
                                   capture_output=True, check=False, timeout=10)

        # Update database
        password_b64 = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        email_obj.password = password_b64
        email_obj.save()

        return api_response(data={'message': 'Password updated successfully.'})

    except Exception as e:
        logger.exception('Failed to change password for %s', email)
        return api_response(error=f'Failed to update password: {str(e)}', status=500)


# ══════════════════════════════════════════════════════════════════════════════
#  VOIDMAIL AI WHITELIST IP ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@api_auth_required()
def api_email_whitelist_list(request):
    """List all whitelisted IPs for VoidMail AI features for the user's domain."""
    ctrl_user = request.ctrl_user
    entries = VoidMailWhitelistIP.objects.filter(domain=ctrl_user.domain).order_by('-created_at')

    ip_list = []
    for entry in entries:
        ip_list.append({
            'id': entry.id,
            'ip_address': entry.ip_address,
            'domain': entry.domain,
            'label': entry.label,
            'created_at': entry.created_at.isoformat(),
        })

    return api_response(data={'whitelist': ip_list, 'count': len(ip_list)})


@api_auth_required()
@require_post
def api_email_whitelist_add(request):
    """
    Add an IP to the VoidMail AI whitelist for the user's domain.

    POST body: { "ip_address": "1.2.3.4", "label": "Office Network" }
    """
    data = parse_json_body(request)
    ip_address = data.get('ip_address', '').strip()
    label = data.get('label', '').strip()
    ctrl_user = request.ctrl_user
    domain_name = ctrl_user.domain

    if not ip_address:
        return api_response(error='IP address is required.', status=400)

    # Check if already exists
    if VoidMailWhitelistIP.objects.filter(ip_address=ip_address, domain=domain_name).exists():
        return api_response(error='This IP is already whitelisted for this domain.', status=409)

    entry = VoidMailWhitelistIP.objects.create(
        ip_address=ip_address,
        domain=domain_name,
        label=label,
    )

    try:
        from control.activity import log_activity
        log_activity(request, 'success', 'email', domain=domain_name,
                     action=f'VoidMail AI whitelist IP added: {ip_address}',
                     detail=f'Label: {label or "none"}')
    except Exception:
        pass

    return api_response(data={
        'id': entry.id,
        'ip_address': entry.ip_address,
        'domain': entry.domain,
        'label': entry.label,
        'message': f'IP {ip_address} whitelisted for VoidMail AI features.',
    })


@api_auth_required()
@require_post
def api_email_whitelist_remove(request):
    """
    Remove an IP from the VoidMail AI whitelist.

    POST body: { "ip_address": "1.2.3.4" }
    """
    data = parse_json_body(request)
    ip_address = data.get('ip_address', '').strip()
    ctrl_user = request.ctrl_user

    if not ip_address:
        return api_response(error='IP address is required.', status=400)

    try:
        entry = VoidMailWhitelistIP.objects.get(ip_address=ip_address, domain=ctrl_user.domain)
    except VoidMailWhitelistIP.DoesNotExist:
        return api_response(error='IP not found in whitelist.', status=404)

    entry.delete()

    try:
        from control.activity import log_activity
        log_activity(request, 'success', 'email', domain=ctrl_user.domain,
                     action=f'VoidMail AI whitelist IP removed: {ip_address}',
                     detail='Removed via VoidApp API')
    except Exception:
        pass

    return api_response(data={'message': f'IP {ip_address} removed from VoidMail AI whitelist.'})


@csrf_exempt
def api_email_ai_status(request):
    """
    Check if the caller's domain or IP is whitelisted for VoidMail AI features.

    Returns: { ai_enabled: true/false, voidonyx_url, license_key, domain }
    """
    # Try getting domain from query params, auth session, or email body
    domain_name = request.GET.get('domain', '').strip().lower()
    if not domain_name and hasattr(request, 'ctrl_user') and request.ctrl_user:
        domain_name = request.ctrl_user.domain.strip().lower()

    caller_ip = _get_client_ip(request)

    # 1. Check Domain-Level Whitelist (from Superadmin 1-Click Whitelist)
    is_domain_whitelisted = False
    if domain_name:
        is_domain_whitelisted = VoidMailWhitelistedDomain.objects.filter(
            domain__iexact=domain_name,
            is_active=True,
        ).exists()

    # 2. Check IP-Level Whitelist
    is_ip_whitelisted = False
    if domain_name:
        is_ip_whitelisted = VoidMailWhitelistIP.objects.filter(
            ip_address=caller_ip,
            domain__iexact=domain_name,
        ).exists()
    else:
        is_ip_whitelisted = VoidMailWhitelistIP.objects.filter(
            ip_address=caller_ip,
        ).exists()

    is_whitelisted = is_domain_whitelisted or is_ip_whitelisted

    # VoidOnyx URL and license key for AI gateway
    voidonyx_url = 'https://voidonyx.in'
    license_key = ''

    try:
        from control.license import get_license_key
        license_key = get_license_key() or ''
    except Exception:
        license_key = getattr(django_settings, 'VOIDPANEL_LICENSE_KEY', '')

    return api_response(data={
        'ai_enabled': is_whitelisted,
        'caller_ip': caller_ip,
        'domain': domain_name,
        'is_domain_whitelisted': is_domain_whitelisted,
        'is_ip_whitelisted': is_ip_whitelisted,
        'voidonyx_url': voidonyx_url,
        'license_key': license_key,
    })


# ── VoidMail AI Upgrade Lead Capture & 1-Click Whitelist ──────────────────────

@csrf_exempt
@require_post
def api_email_upgrade_lead_submit(request):
    """
    Capture an upgrade lead from a user requesting VoidMail AI access.
    POST body: { "name": "...", "email": "...", "phone": "...", "domain": "...", "notes": "..." }
    """
    body = parse_json_body(request)
    name = (body.get('name') or '').strip()
    email_addr = (body.get('email') or '').strip().lower()
    phone = (body.get('phone') or '').strip()
    domain_part = (body.get('domain') or '').strip().lower()
    notes = (body.get('notes') or '').strip()
    caller_ip = _get_client_ip(request)

    if not name or not phone:
        return api_response(status='error', error='Name and phone number are required', code=400)

    if not email_addr:
        return api_response(status='error', error='Email address is required', code=400)

    if not domain_part:
        if '@' in email_addr:
            domain_part = email_addr.split('@')[-1]
        else:
            domain_part = email_addr

    # Create or update the upgrade lead
    lead, created = VoidMailUpgradeLead.objects.update_or_create(
        email=email_addr,
        defaults={
            'name': name,
            'phone': phone,
            'domain': domain_part,
            'caller_ip': caller_ip,
            'notes': notes,
        }
    )

    logger.info(
        '[VoidMail Lead] Captured AI upgrade request: %s (%s, phone: %s, domain: %s)',
        name, email_addr, phone, domain_part
    )

    # Dual-write to VoidOnyx DB so superadmin can see the lead
    try:
        import sqlite3, pathlib, datetime
        voidonyx_db = pathlib.Path('/home/voidpanelc091/voidpanel/db.sqlite3')
        if voidonyx_db.exists():
            conn = sqlite3.connect(str(voidonyx_db))
            now_iso = datetime.datetime.now().isoformat()
            # Check if lead already exists for this email
            existing = conn.execute(
                "SELECT id FROM data_voidmailaiupgradelead WHERE email = ?",
                (email_addr,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE data_voidmailaiupgradelead SET name=?, phone=?, domain=?, notes=?, updated_at=? WHERE email=?",
                    (name, phone, domain_part, notes, now_iso, email_addr)
                )
            else:
                conn.execute(
                    "INSERT INTO data_voidmailaiupgradelead "
                    "(name, email, phone, domain, status, notes, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)",
                    (name, email_addr, phone, domain_part, notes, now_iso, now_iso)
                )
            conn.commit()
            conn.close()
    except Exception:
        pass  # Non-critical — main record already saved above

    return api_response(data={
        'success': True,
        'message': f'AI Upgrade request for {domain_part} received successfully.',
        'lead_id': lead.id,
        'domain': domain_part,
        'status': lead.status,
    })


@csrf_exempt
@require_post
def api_email_upgrade_lead_whitelist(request):
    """
    1-Click Whitelist Action from Superadmin / Panel to instantly enable AI for a lead's domain.
    POST body: { "lead_id": 123 } or { "domain": "example.com" }
    """
    body = parse_json_body(request)
    lead_id = body.get('lead_id')
    domain_name = (body.get('domain') or '').strip().lower()

    lead = None
    if lead_id:
        try:
            lead = VoidMailUpgradeLead.objects.get(id=lead_id)
            domain_name = lead.domain.lower()
        except VoidMailUpgradeLead.DoesNotExist:
            return api_response(status='error', error='Lead not found', code=404)

    if not domain_name:
        return api_response(status='error', error='domain or lead_id is required', code=400)

    # 1. Create or activate whitelisted domain
    whitelisted_domain, created = VoidMailWhitelistedDomain.objects.update_or_create(
        domain=domain_name,
        defaults={
            'is_active': True,
            'lead': lead,
            'notes': f'1-Click Whitelisted for lead {lead.name} ({lead.email})' if lead else 'Superadmin Whitelisted',
        }
    )

    # 2. Update lead status if exists
    if lead:
        lead.status = 'whitelisted'
        lead.save(update_fields=['status', 'updated_at'])

    # Also update any other pending leads for this same domain
    VoidMailUpgradeLead.objects.filter(domain__iexact=domain_name, status='pending').update(status='whitelisted')

    logger.info('[VoidMail Superadmin] 1-Click Whitelisted domain: %s (AI is now active)', domain_name)

    return api_response(data={
        'success': True,
        'message': f'Domain {domain_name} has been whitelisted and AI is now active!',
        'domain': domain_name,
        'is_active': True,
    })



# ── FCM Push Notification Device Registration ────────────────────────────────

@csrf_exempt
@require_post
def api_email_device_register(request):
    """
    Register or update an FCM push notification token for an email account.
    POST body: { "email": "user@domain.com", "fcm_token": "...", "platform": "android", "device_name": "Pixel 8" }
    """
    body = parse_json_body(request)
    email_addr = (body.get('email') or '').strip().lower()
    fcm_token = (body.get('fcm_token') or '').strip()
    platform = (body.get('platform') or 'android').strip().lower()
    device_name = (body.get('device_name') or '').strip()

    if not email_addr or not fcm_token:
        return api_response(status='error', error='email and fcm_token are required', code=400)

    domain_part = email_addr.split('@')[-1] if '@' in email_addr else ''

    token_obj, created = EmailDeviceToken.objects.update_or_create(
        fcm_token=fcm_token,
        defaults={
            'email': email_addr,
            'domain': domain_part,
            'platform': platform if platform in ('android', 'ios', 'web') else 'android',
            'device_name': device_name,
            'is_active': True,
        }
    )

    logger.info('[FCM] Device token %s for %s (%s)', 'registered' if created else 'updated', email_addr, platform)

    # Dual-write to VoidOnyx DB so superadmin can see registered devices
    try:
        import sqlite3, pathlib, datetime
        voidonyx_db = pathlib.Path('/home/voidpanelc091/voidpanel/db.sqlite3')
        if voidonyx_db.exists():
            conn = sqlite3.connect(str(voidonyx_db))
            now_iso = datetime.datetime.now().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO data_emaildevicetoken "
                "(email, domain, fcm_token, platform, device_name, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (email_addr, domain_part, fcm_token, platform, device_name, now_iso, now_iso)
            )
            conn.commit()
            conn.close()
    except Exception:
        pass  # Non-critical — main record already saved above

    return api_response(data={
        'registered': True,
        'email': email_addr,
        'platform': platform,
    }, message='Device token successfully registered for push notifications.')


@csrf_exempt
@require_post
def api_email_device_unregister(request):
    """
    Unregister an FCM push notification token on logout/removal.
    POST body: { "fcm_token": "..." } or { "email": "..." }
    """
    body = parse_json_body(request)
    fcm_token = (body.get('fcm_token') or '').strip()
    email_addr = (body.get('email') or '').strip().lower()

    if fcm_token:
        EmailDeviceToken.objects.filter(fcm_token=fcm_token).update(is_active=False)
    elif email_addr:
        EmailDeviceToken.objects.filter(email__iexact=email_addr).update(is_active=False)
    else:
        return api_response(status='error', error='fcm_token or email is required', code=400)

    return api_response(data={'unregistered': True}, message='Device token unregistered.')


@csrf_exempt
@require_post
def api_email_device_test_push(request):
    """
    Send a test push notification to verified devices for an email address.
    POST body: { "email": "user@domain.com" }
    """
    body = parse_json_body(request)
    email_addr = (body.get('email') or '').strip().lower()
    if not email_addr:
        return api_response(status='error', error='email is required', code=400)

    result = send_fcm_push_to_email(
        email_address=email_addr,
        sender_name='VoidMail Team',
        subject='Push Notifications Active! 🚀',
        snippet='You will now receive instant email alerts even when VoidMail is closed.',
        email_id='test_ping',
    )
    return api_response(data=result, message='Test push notification dispatched.')


@csrf_exempt
@require_post
def api_email_device_broadcast_push(request):
    """
    Send a custom broadcast push notification to all registered devices.
    POST body: { "title": "...", "body": "...", "domain": "" (optional) }
    The sender_email is inferred from the session for audit safety.
    """
    body = parse_json_body(request)
    title = (body.get('title') or '').strip()
    push_body = (body.get('body') or '').strip()
    domain_filter = (body.get('domain') or '').strip()
    sender_email = (body.get('sender_email') or '').strip()

    if not title or not push_body:
        return api_response(error='title and body are required', status=400)

    result = broadcast_fcm_push(
        title=title,
        body=push_body,
        domain=domain_filter,
        sender_email=sender_email,
    )

    logger.info('[PUSH BROADCAST] Title="%s" Body="%s" Domain="%s" Sender="%s" Result=%s',
                title, push_body[:50], domain_filter, sender_email, result)

    return api_response(data=result)



@csrf_exempt
@require_post
def api_email_track_login(request):
    """
    Track an app login for analytics.
    POST body: { "email": "...", "domain": "...", "platform": "android", "device_name": "...", "login_method": "voidpanel" }
    """
    body = parse_json_body(request)
    email = (body.get('email') or '').strip()
    domain_val = (body.get('domain') or '').strip()
    platform = (body.get('platform') or 'android').strip()
    device_name = (body.get('device_name') or '').strip()
    login_method = (body.get('login_method') or 'voidpanel').strip()

    if not email:
        return api_response(error='email is required', status=400)

    # Extract domain from email if not provided
    if not domain_val and '@' in email:
        domain_val = email.split('@')[1]

    # Get client IP
    ip = _get_client_ip(request)

    VoidMailAppLogin.objects.create(
        email=email,
        domain=domain_val,
        platform=platform,
        device_name=device_name,
        ip_address=ip,
        login_method=login_method,
    )

    # Also write to the VoidOnyx project's DB so the super admin can see it
    try:
        import sqlite3, pathlib, datetime
        voidonyx_db = pathlib.Path('/home/voidpanelc091/voidpanel/db.sqlite3')
        if voidonyx_db.exists():
            conn = sqlite3.connect(str(voidonyx_db))
            conn.execute(
                "INSERT INTO data_voidmailapplogin (email, domain, platform, device_name, ip_address, login_method, logged_in_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (email, domain_val, platform, device_name, ip, login_method, datetime.datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
    except Exception:
        pass  # Non-critical — main record already saved above

    logger.info('[APP LOGIN] %s (%s) from %s via %s', email, domain_val, ip, login_method)

    return api_response(data={'tracked': True})


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    """Extract the real client IP, respecting X-Forwarded-For behind proxies."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')

def _get_pkg(name):
    try:
        return Package.objects.get(name=name) if name else None
    except Package.DoesNotExist:
        return None

def _safe_int(val):
    try:
        v = str(val).strip().lower()
        if v in ('unlimited', '∞', ''):
            return 0
        return int(v)
    except (ValueError, TypeError):
        return 0
