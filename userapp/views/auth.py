"""
VoidApp API — Authentication endpoints.

POST /api/v1/auth/login/   — Login with username/password, returns API token
GET  /api/v1/auth/me/      — Get current user profile + package quotas
POST /api/v1/auth/logout/  — Invalidate session
"""

import logging
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.views.decorators.csrf import csrf_exempt

from control.models import user as CtrlUser, package as Package
from userapp.decorators import (
    api_response, api_auth_required, create_token,
    parse_json_body, require_post, _get_client_ip
)

logger = logging.getLogger('voidpanel.userapp')


@csrf_exempt
@require_post
def api_login(request):
    """
    Authenticate user and return API token.

    POST body (JSON):
    {
        "username": "myuser",
        "password": "mypassword"
    }

    Returns:
    {
        "status": "ok",
        "data": {
            "token": "...",
            "username": "myuser",
            "domain": "example.com",
            "is_admin": false
        }
    }
    """
    data = parse_json_body(request)
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return api_response(error='Username and password are required.', status=400)

    # Rate limit login attempts more aggressively (10 per minute per IP)
    from userapp.decorators import _rate_limit_check
    client_ip = _get_client_ip(request)
    rate_key = f'login:{client_ip}'
    allowed, _, _ = _rate_limit_check(rate_key, max_requests=10, window=60)
    if not allowed:
        return api_response(error='Too many login attempts. Please try again later.', status=429)

    user = authenticate(username=username, password=password)
    if user is None:
        logger.warning('VoidApp login failed for username=%s from IP=%s', username, client_ip)
        return api_response(error='Invalid username or password.', status=401)

    if not user.is_active:
        return api_response(error='Account is disabled.', status=403)

    # Create Django session as well (for web compatibility)
    auth_login(request, user)

    # Log the login
    try:
        from control.models import LoginActivity
        LoginActivity.objects.create(
            user=username,
            ip_address=client_ip,
            successful=True
        )
    except Exception:
        pass

    # Resolve control panel user
    ctrl_user = CtrlUser.objects.filter(username=username).first()
    domain = ctrl_user.domain if ctrl_user else ''

    # Create API token
    token = create_token(user.id, username)

    return api_response(data={
        'token': token,
        'username': username,
        'domain': domain,
        'is_admin': user.is_superuser,
    })


@api_auth_required()
def api_me(request):
    """
    Get current user profile with package quotas.

    GET /api/v1/auth/me/

    Returns user info, domain, package details, and resource quotas.
    """
    ctrl_user = request.ctrl_user
    pkg = _get_package(ctrl_user.hosting_package)

    data = {
        'username': ctrl_user.username,
        'email': ctrl_user.email,
        'domain': ctrl_user.domain,
        'hosting_package': ctrl_user.hosting_package,
        'is_active': ctrl_user.is_active,
        'shell_access': getattr(ctrl_user, 'shell', False),
        'package': {
            'name': pkg.name if pkg else 'Unknown',
            'storage_gb': _safe_int(pkg.storage) if pkg else 0,
            'email_accounts': _safe_int(pkg.email_accounts) if pkg else 0,
            'databases': _safe_int(pkg.databases_allowed) if pkg else 0,
            'ftp_accounts': _safe_int(pkg.ftp) if pkg else 0,
            'subdomains': _safe_int(pkg.subdomain) if pkg else 0,
            'bandwidth_gb': _safe_int(pkg.bandwidth) if pkg else 0,
        }
    }
    return api_response(data=data)


@csrf_exempt
@api_auth_required()
@require_post
def api_logout(request):
    """Logout and destroy session."""
    auth_logout(request)
    return api_response(data={'message': 'Logged out successfully.'})


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_package(package_name):
    """Safely get a package by name."""
    try:
        if not package_name:
            return None
        return Package.objects.get(name=package_name)
    except Package.DoesNotExist:
        return None


def _safe_int(val):
    """Convert to int, return 0 for 'unlimited' or invalid values."""
    try:
        v = str(val).strip().lower()
        if v in ('unlimited', '∞', ''):
            return 0  # 0 means unlimited in VoidPanel convention
        return int(v)
    except (ValueError, TypeError):
        return 0
