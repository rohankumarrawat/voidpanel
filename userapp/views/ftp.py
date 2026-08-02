"""
VoidApp API — FTP account management endpoints.

GET    /api/v1/ftp/                   — List FTP accounts
POST   /api/v1/ftp/create/            — Create FTP account
POST   /api/v1/ftp/delete/            — Delete FTP account
POST   /api/v1/ftp/change-password/   — Change FTP password
POST   /api/v1/ftp/change-storage/    — Update FTP quota
"""

import os
import sys
import base64
import logging

from control.models import ftpaccount, user as CtrlUser, package as Package, ftp as FtpConfig
from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')


@api_auth_required()
def api_ftp_list(request):
    """List all FTP accounts for the current user."""
    ctrl_user = request.ctrl_user
    username = request.ctrl_username

    accounts = ftpaccount.objects.filter(main=str(username))
    ftp_list = []
    for acc in accounts:
        ftp_list.append({
            'id': acc.id,
            'username': acc.username,
            'storage': acc.storage,
        })

    # Get quota
    pkg = _get_pkg(ctrl_user.hosting_package)
    total = _safe_int(pkg.ftp) if pkg else 0

    return api_response(data={
        'accounts': ftp_list,
        'used': len(ftp_list),
        'total': total,
        'unlimited': total == 0,
    })


@api_auth_required()
@require_post
def api_ftp_create(request):
    """
    Create a new FTP account.

    POST body:
    {
        "username": "ftpuser",
        "password": "SecurePass!",
        "storage": "500",
        "path": "public_html"
    }
    """
    data = parse_json_body(request)
    name = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    storage = data.get('storage', '500').strip()
    path = data.get('path', 'public_html').strip()
    ctrl_user = request.ctrl_user
    username = request.ctrl_username
    domain_name = ctrl_user.domain

    # Validation
    if not name:
        return api_response(error='FTP username is required.', status=400)
    if not password or len(password) < 6:
        return api_response(error='Password must be at least 6 characters.', status=400)

    import re
    if not re.match(r'^[a-z0-9._-]+$', name):
        return api_response(error='Invalid username. Use only lowercase letters, numbers, dots, dashes.', status=400)

    fullname = f'{domain_name}_{name}'

    # Check if exists
    if ftpaccount.objects.filter(username=fullname).exists():
        return api_response(error='FTP account already exists.', status=409)

    # Check quota
    pkg = _get_pkg(ctrl_user.hosting_package)
    if pkg:
        max_ftp = _safe_int(pkg.ftp)
        if max_ftp > 0:
            current = ftpaccount.objects.filter(main=str(username)).count()
            if current >= max_ftp:
                return api_response(error=f'Quota exceeded. Maximum {max_ftp} FTP accounts allowed.', status=403)

    # Build path
    try:
        from voidplatform.config import paths
        from voidplatform import get_platform
        from function import run_command

        if not path.startswith('/'):
            path = '/' + path
        full_path = os.path.join(paths.HOME_BASE, str(username)) + path

        if sys.platform != 'win32':
            run_command(f'sudo mkdir -p {full_path}')
            try:
                plat = get_platform()
                plat.users.create_user(fullname, password, shell=paths.NOLOGIN_SHELL)
            except Exception:
                pass
            try:
                get_platform().users.set_quota(fullname, int(storage), int(storage))
            except Exception:
                pass
            run_command(f'sudo chown {fullname}:{fullname} {full_path}')
            run_command(f'echo "{fullname}" | sudo tee -a {paths.VSFTPD_USERLIST}')
            get_platform().services.restart('vsftpd')
        else:
            os.makedirs(full_path, exist_ok=True)

        # Save to DB
        password_b64 = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        ftp_obj = ftpaccount.objects.create(
            main=str(username),
            username=fullname,
            password=password_b64,
            storage=storage
        )

        try:
            from control.activity import log_activity
            log_activity(request, 'success', 'ftp', domain=domain_name,
                         action=f'FTP account created: {fullname}',
                         detail='Created via VoidApp API')
        except Exception:
            pass

        return api_response(data={
            'id': ftp_obj.id,
            'username': fullname,
            'message': 'FTP account created successfully.'
        })

    except Exception as e:
        logger.exception('Failed to create FTP account %s', fullname)
        return api_response(error=f'Failed to create FTP account: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_ftp_delete(request):
    """
    Delete an FTP account.

    POST body: { "username": "example.com_ftpuser" }
    """
    data = parse_json_body(request)
    ftp_username = data.get('username', '').strip()
    ctrl_user = request.ctrl_user
    username = request.ctrl_username

    if not ftp_username:
        return api_response(error='FTP username is required.', status=400)

    # Ownership check
    try:
        ftp_obj = ftpaccount.objects.get(username=ftp_username, main=str(username))
    except ftpaccount.DoesNotExist:
        return api_response(error='FTP account not found.', status=404)

    try:
        if sys.platform != 'win32':
            from voidplatform import get_platform
            from function import run_command
            from voidplatform.config import paths

            try:
                get_platform().users.delete_user(ftp_username)
            except Exception:
                pass
            run_command(f"sudo sed -i '/^{ftp_username}$/d' {paths.VSFTPD_USERLIST}")
            get_platform().services.restart('vsftpd')
    except Exception as e:
        logger.warning('Partial system cleanup for FTP %s: %s', ftp_username, e)

    ftp_obj.delete()

    try:
        from control.activity import log_activity
        log_activity(request, 'success', 'ftp', domain=ctrl_user.domain,
                     action=f'FTP account deleted: {ftp_username}',
                     detail='Deleted via VoidApp API')
    except Exception:
        pass

    return api_response(data={'message': f'FTP account {ftp_username} deleted.'})


@api_auth_required()
@require_post
def api_ftp_change_password(request):
    """
    Change FTP account password.

    POST body: { "username": "example.com_ftpuser", "password": "NewPass!" }
    """
    data = parse_json_body(request)
    ftp_username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    username = request.ctrl_username

    if not ftp_username or not password:
        return api_response(error='Username and password are required.', status=400)

    # Ownership
    if not ftpaccount.objects.filter(username=ftp_username, main=str(username)).exists():
        return api_response(error='FTP account not found.', status=404)

    try:
        if sys.platform != 'win32':
            from voidplatform import get_platform
            get_platform().users.change_password(ftp_username, password)
        return api_response(data={'message': 'FTP password updated.'})
    except Exception as e:
        return api_response(error=f'Failed to update password: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_ftp_change_storage(request):
    """
    Update FTP account storage quota.

    POST body: { "username": "example.com_ftpuser", "storage": "1000" }
    """
    data = parse_json_body(request)
    ftp_username = data.get('username', '').strip()
    storage = data.get('storage', '').strip()
    username = request.ctrl_username

    if not ftp_username or not storage:
        return api_response(error='Username and storage are required.', status=400)

    try:
        ftp_obj = ftpaccount.objects.get(username=ftp_username, main=str(username))
    except ftpaccount.DoesNotExist:
        return api_response(error='FTP account not found.', status=404)

    try:
        if sys.platform != 'win32':
            from voidplatform import get_platform
            get_platform().users.set_quota(ftp_username, int(storage), int(storage))

        ftp_obj.storage = storage
        ftp_obj.save()
        return api_response(data={'message': 'FTP quota updated.'})
    except Exception as e:
        return api_response(error=f'Failed to update quota: {str(e)}', status=500)


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
