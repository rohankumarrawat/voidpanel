"""
VoidApp API — SSL management endpoints.

GET    /api/v1/ssl/status/   — SSL status for domain + subdomains
POST   /api/v1/ssl/install/  — Trigger Let's Encrypt SSL
GET    /api/v1/ssl/log/      — SSL installation log
"""

import os
import threading
import logging

from control.models import (
    domain as Domain, subdomainname, user as CtrlUser
)
from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')


@api_auth_required()
def api_ssl_status(request):
    """Get SSL status for the user's domain and all subdomains."""
    ctrl_user = request.ctrl_user

    try:
        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
    except Domain.DoesNotExist:
        return api_response(error='Domain not found.', status=404)

    # Main domain SSL
    statuses = [{
        'name': dom_obj.domain,
        'ssl_active': dom_obj.sslstatus,
        'is_subdomain': False,
    }]

    # Subdomains SSL
    for sub in subdomainname.objects.filter(domain=ctrl_user.domain):
        statuses.append({
            'name': sub.subdomain,
            'ssl_active': getattr(sub, 'sslstatus', False),
            'is_subdomain': True,
        })

    return api_response(data={'statuses': statuses})


@api_auth_required()
@require_post
def api_ssl_install(request):
    """
    Trigger Let's Encrypt SSL installation.

    POST body: { "domain": "example.com" }
    Can be the main domain or a subdomain.
    """
    data = parse_json_body(request)
    target = data.get('domain', '').strip().lower()
    ctrl_user = request.ctrl_user

    if not target:
        return api_response(error='Domain is required.', status=400)

    # Verify ownership
    is_subdomain = False
    if target == ctrl_user.domain:
        # Main domain
        pass
    elif subdomainname.objects.filter(subdomain=target, domain=ctrl_user.domain).exists():
        is_subdomain = True
    else:
        return api_response(error='You do not own this domain.', status=403)

    # Trigger SSL in background (same pattern as panel)
    try:
        from control.views import _background_run_ssl
        threading.Thread(
            target=_background_run_ssl,
            args=(target, is_subdomain),
            daemon=True
        ).start()

        return api_response(data={
            'message': f'SSL installation started for {target}. Check log for progress.',
            'domain': target,
        })

    except Exception as e:
        logger.exception('Failed to start SSL for %s', target)
        return api_response(error=f'Failed to initiate SSL: {str(e)}', status=500)


@api_auth_required()
def api_ssl_log(request):
    """Get SSL installation log for the user's domain."""
    ctrl_user = request.ctrl_user

    try:
        from voidplatform.config import paths
        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
        log_path = os.path.join(paths.HOME_BASE, dom_obj.dir, 'logs', 'ssl.txt')

        logs = []
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                logs = f.readlines()

        return api_response(data={
            'logs': [line.strip() for line in logs if line.strip()],
            'domain': ctrl_user.domain,
        })

    except Domain.DoesNotExist:
        return api_response(error='Domain not found.', status=404)
    except Exception as e:
        return api_response(error=f'Failed to read log: {str(e)}', status=500)
