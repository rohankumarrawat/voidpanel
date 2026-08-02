"""
VoidApp API — Security decorators and authentication utilities.

Token format: Django's built-in TimestampSigner for HMAC-based tokens.
No external dependency needed — uses Django's SECRET_KEY for signing.
"""

import json
import functools
import time
import hashlib
import logging

from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User as AuthUser
from django.views.decorators.csrf import csrf_exempt

from control.models import user as CtrlUser

logger = logging.getLogger('voidpanel.userapp')

# ── Token Configuration ─────────────────────────────────────────────────────

TOKEN_MAX_AGE = 86400 * 7  # 7 days
TOKEN_SALT = 'voidapp-api-token-v1'


def create_token(user_id, username):
    """Create a signed, time-limited API token for a user."""
    payload = {
        'uid': user_id,
        'usr': username,
        'iat': int(time.time()),
    }
    return signing.dumps(payload, salt=TOKEN_SALT)


def verify_token(token):
    """
    Verify and decode an API token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        return payload
    except (signing.BadSignature, signing.SignatureExpired):
        return None


# ── Rate Limiting ────────────────────────────────────────────────────────────

# Simple in-memory rate limiter (per-IP, per-endpoint)
_rate_store = {}


def _rate_limit_check(key, max_requests=60, window=60):
    """
    Check if the rate limit is exceeded for a given key.
    Returns (allowed: bool, remaining: int, reset_at: float).
    """
    now = time.time()
    if key not in _rate_store:
        _rate_store[key] = []

    # Remove expired entries
    _rate_store[key] = [t for t in _rate_store[key] if t > now - window]

    if len(_rate_store[key]) >= max_requests:
        return False, 0, _rate_store[key][0] + window

    _rate_store[key].append(now)
    return True, max_requests - len(_rate_store[key]), now + window


# ── Decorators ───────────────────────────────────────────────────────────────

def api_response(data=None, error=None, status=200):
    """Standardised JSON API response."""
    body = {'status': 'ok' if error is None else 'error'}
    if data is not None:
        body['data'] = data
    if error is not None:
        body['error'] = error
    resp = JsonResponse(body, status=status)
    # No CORS wildcard — this API is consumed by native Flutter apps only.
    # Specific origins can be added here if a web frontend is needed later.
    return resp


def api_auth_required(max_requests=60, window=60):
    """
    Decorator that enforces API token authentication.

    Checks for:
    1. Bearer token in Authorization header (primary — for Flutter)
    2. Django session auth (fallback — for web)

    Also applies per-IP rate limiting.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            # ── Handle preflight CORS ────────────────────────────────
            if request.method == 'OPTIONS':
                return api_response(data={'ok': True})

            # ── Rate limiting ────────────────────────────────────────
            client_ip = _get_client_ip(request)
            rate_key = f'{client_ip}:{request.path}'
            allowed, remaining, reset_at = _rate_limit_check(rate_key, max_requests, window)
            if not allowed:
                resp = api_response(error='Rate limit exceeded. Try again later.', status=429)
                resp['X-RateLimit-Remaining'] = '0'
                resp['X-RateLimit-Reset'] = str(int(reset_at))
                return resp

            # ── Token authentication ─────────────────────────────────
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            api_user = None

            if auth_header.startswith('Bearer '):
                token = auth_header[7:].strip()
                payload = verify_token(token)
                if payload is None:
                    return api_response(error='Invalid or expired token.', status=401)
                try:
                    api_user = AuthUser.objects.get(id=payload['uid'])
                except AuthUser.DoesNotExist:
                    return api_response(error='User no longer exists.', status=401)

            # ── Session fallback ─────────────────────────────────────
            elif request.user.is_authenticated:
                api_user = request.user

            if api_user is None:
                return api_response(error='Authentication required.', status=401)

            # ── Resolve the control panel user ───────────────────────
            # Admins impersonating via session
            if api_user.is_superuser:
                ctrl_username = request.session.get('name', api_user.username)
            else:
                ctrl_username = api_user.username

            try:
                ctrl_user = CtrlUser.objects.get(username=ctrl_username)
            except CtrlUser.DoesNotExist:
                return api_response(error='Hosting account not found.', status=404)

            # Attach resolved objects to request for views
            request.api_user = api_user
            request.ctrl_user = ctrl_user
            request.ctrl_username = ctrl_username

            # Add rate limit headers
            response = view_func(request, *args, **kwargs)
            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Remaining'] = str(remaining)
            return response

        return wrapper
    return decorator


def _get_client_ip(request):
    """Extract client IP from request, respecting proxy headers."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def parse_json_body(request):
    """Safely parse JSON request body. Returns dict or empty dict."""
    if request.content_type and 'json' in request.content_type:
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return {}
    # Fall back to POST data
    return dict(request.POST)


def validate_domain_ownership(request, domain_name):
    """
    Verify that the current user owns the given domain.
    Returns True if ownership confirmed, False otherwise.
    """
    ctrl_user = request.ctrl_user
    # Primary domain match
    if ctrl_user.domain == domain_name:
        return True
    # Check if it's a subdomain of the user's domain
    from control.models import subdomainname
    if subdomainname.objects.filter(domain=ctrl_user.domain, subdomain=domain_name).exists():
        return True
    return False


def require_post(view_func):
    """Decorator that ensures POST method."""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method != 'POST':
            return api_response(error='POST method required.', status=405)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_method(*methods):
    """Decorator that ensures specific HTTP methods."""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return api_response(
                    error=f'Method not allowed. Use: {", ".join(methods)}',
                    status=405
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
