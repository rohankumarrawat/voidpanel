"""
VoidPanel Provisioning API
Handles authenticated requests from the VoidPanel Website/Portal to create,
suspend and unsuspend hosting accounts on this server.

Authentication: Every request must include the header:
    X-VoidPanel-Key: <key shown in Admin → API Key Settings>
"""
import time
import threading
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from panel.logger import get_logger

logger = get_logger(__name__)


# ── Authentication ────────────────────────────────────────────────────────────

def _get_current_key() -> str:
    """Return the active API key from the database (with fallback to 'change-me')."""
    try:
        from control.models import PanelAPIKey
        return PanelAPIKey.current_key()
    except Exception:
        from django.conf import settings
        return getattr(settings, 'VOIDPANEL_API_KEY', 'change-me-in-settings')


def authenticate_request(request) -> bool:
    """Return True if the X-VoidPanel-Key header matches the stored key."""
    incoming = request.headers.get('X-VoidPanel-Key', '').strip()
    if not incoming:
        return False
    import hmac as _hmac
    expected = _get_current_key()
    # Use constant-time comparison to prevent timing attacks
    if _hmac.compare_digest(incoming, expected):
        return True
        
    # Fallback: Allow valid Superadmin APITokens to act as Master Keys
    try:
        from control.models import APIToken
        if APIToken.objects.filter(key=incoming, is_active=True, owner_type=APIToken.OWNER_SUPERADMIN).exists():
            return True
    except Exception:
        pass

    return False


# ── /api/license/validate/ ────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def portal_license_validate(request):
    """
    GET/POST /api/license/validate/
    Called by the VoidPanel Website "Test Connection" button.
    Returns server version and confirms the API key is valid.
    """
    if not authenticate_request(request):
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid or missing API key (X-VoidPanel-Key)'},
            status=403,
        )

    # Collect version info
    try:
        import importlib.metadata
        version = importlib.metadata.version('django')
        dj_ver = f'Django {version}'
    except Exception:
        dj_ver = 'Django (unknown)'

    try:
        from control.license import get_license
        lic = get_license()
        lic_status = lic.status if lic else 'unlicensed'
    except Exception:
        lic_status = 'unknown'

    import socket
    return JsonResponse({
        'status': 'ok',
        'message': 'Connection successful',
        'server_version': '2.0',
        'hostname': socket.gethostname(),
        'license_status': lic_status,
        'django_version': dj_ver,
    })


# ── /api/provision/create/ ────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def portal_provision_create(request):
    """
    POST /api/provision/create/
    Body: { domain, email, package, storage_gb?, bandwidth_gb? }
    Creates a hosting account in the background.
    """
    if not authenticate_request(request):
        return Response({'status': 'error', 'message': 'Invalid API Key'}, status=403)

    domain  = request.data.get('domain', '').strip().lower()
    email   = request.data.get('email', '').strip()
    package = request.data.get('package', '').strip()

    if not domain or '.' not in domain:
        return Response({'status': 'error', 'message': 'Missing or invalid domain'}, status=400)
    if not package:
        return Response({'status': 'error', 'message': 'Missing package'}, status=400)

    # Check domain not already in DB
    try:
        from control.models import domain as DomainModel
        if DomainModel.objects.filter(domain=domain).exists():
            return Response({
                'status': 'error_domain_exists',
                'message': f"Domain '{domain}' already exists on this server.",
            }, status=409)
    except Exception:
        pass

    import re
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(16))
    username = re.sub(r'[^a-z0-9]', '', domain.split('.')[0].lower())[:9] + secrets.token_hex(2)

    from panel.views import background_create_account
    thread = threading.Thread(
        target=background_create_account,
        args=(username, password, domain, package, email),
        daemon=True,
    )
    thread.start()

    import socket
    server_hostname = socket.gethostname()
    server_ip = ''
    try:
        server_ip = socket.gethostbyname(server_hostname)
    except Exception:
        pass

    logger.info('Provision queued: domain=%s user=%s package=%s', domain, username, package)
    return Response({
        'status':      'success',
        'message':     'Account provision queued',
        'username':    username,
        'password':    password,
        'panel_url':   f'http://{server_ip or server_hostname}:8080',
        'server_ip':   server_ip,
        'hostname':    server_hostname,
    })


# ── /api/provision/suspend/ ───────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def portal_provision_suspend(request):
    """POST /api/provision/suspend/  Body: { domain }"""
    if not authenticate_request(request):
        return Response({'status': 'error', 'message': 'Invalid API Key'}, status=403)

    domain_name = request.data.get('domain', '').strip().lower()
    if not domain_name:
        return Response({'status': 'error', 'message': 'Missing domain'}, status=400)

    try:
        from control.tasks import suspend_user_task
        from control.models import user
        u = user.objects.get(domain=domain_name)
        suspend_user_task.delay(u.username, domain_name)
        return Response({'status': 'success', 'message': 'Account suspended'})
    except Exception as exc:
        logger.exception('Suspend failed for %s: %s', domain_name, exc)
        return Response({'status': 'error', 'message': str(exc)}, status=400)


# ── /api/provision/unsuspend/ ─────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def portal_provision_unsuspend(request):
    """POST /api/provision/unsuspend/  Body: { domain }"""
    if not authenticate_request(request):
        return Response({'status': 'error', 'message': 'Invalid API Key'}, status=403)

    domain_name = request.data.get('domain', '').strip().lower()
    if not domain_name:
        return Response({'status': 'error', 'message': 'Missing domain'}, status=400)

    try:
        from control.tasks import unsuspend_user_task
        from control.models import user
        u = user.objects.get(domain=domain_name)
        unsuspend_user_task.delay(u.username, domain_name)
        return Response({'status': 'success', 'message': 'Account unsuspended'})
    except Exception as exc:
        logger.exception('Unsuspend failed for %s: %s', domain_name, exc)
        return Response({'status': 'error', 'message': str(exc)}, status=400)
