"""
VoidApp API — Email management endpoints.

GET    /api/v1/emails/                  — List email accounts
POST   /api/v1/emails/create/           — Create email account
POST   /api/v1/emails/delete/           — Delete email account
POST   /api/v1/emails/change-password/  — Change email password
"""

import os
import sys
import base64
import shlex
import logging
import subprocess

from django.views.decorators.csrf import csrf_exempt

from control.models import allemail, domain as Domain, user as CtrlUser, package as Package
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


# ── Helpers ──────────────────────────────────────────────────────────────────

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
