"""
VoidPanel Provisioning Bridge
Communicates with the VoidPanel backend REST API to create/suspend/terminate hosting accounts.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PROVISION_API_URL_DEFAULT = getattr(settings, 'VOIDPANEL_API_URL', 'http://178.18.250.134:8080')
PROVISION_API_KEY_DEFAULT = getattr(settings, 'VOIDPANEL_API_KEY', 'change-me-in-settings')


def _get_api_config(server=None):
    if server:
        return server.url.rstrip('/'), server.api_key
    # No server explicitly assigned — try to find any active server in the DB
    try:
        from data.models import VoidPanelServer
        auto = VoidPanelServer.objects.filter(is_active=True).first() \
               or VoidPanelServer.objects.first()
        if auto:
            logger.info('_get_api_config: no server arg, auto-selected "%s"', auto.name)
            return auto.url.rstrip('/'), auto.api_key
    except Exception:
        pass
    return PROVISION_API_URL_DEFAULT.rstrip('/'), PROVISION_API_KEY_DEFAULT


def _headers(api_key):
    return {
        'X-API-Token': api_key,         # preferred — validated via APIToken model
        'X-VoidPanel-Key': api_key,     # legacy fallback
        'Content-Type': 'application/json',
    }


def provision_hosting_account(service) -> dict:
    """
    Route to the correct provisioning API based on service type.
    - Reseller Hosting  → /control/api/reseller/provision/
    - Shared / WordPress → /api/provision/create/

    Returns dict with keys:
        status   : 'ok' | 'error_domain_exists' | 'error_api_unreachable' | 'error_auth' | 'error'
        message  : Human-readable description
        username : (optional) created system username
        panel_url: (optional) panel login URL
    """
    is_reseller = getattr(service, 'is_reseller', False) or \
                  getattr(service, 'product_type', '') == 'Reseller Hosting'

    if is_reseller:
        return provision_reseller_account(service)

    return _provision_shared_account(service)


def _provision_shared_account(service) -> dict:
    """Internal: provision a Shared Hosting or WordPress Hosting account."""
    api_url, api_key = _get_api_config(getattr(service, 'server', None))

    payload = {
        'domain':       service.domain,
        'email':        service.user.email,
        'package':      service.service_name,
        'storage_gb':   service.storage_gb,
        'bandwidth_gb': getattr(service, 'bandwidth_gb', 500),
    }
    try:
        resp = requests.post(
            f'{api_url}/api/provision/create/',
            json=payload,
            headers=_headers(api_key),
            timeout=60,
        )
        logger.info('Provision API HTTP %s for %s', resp.status_code, service.domain)

        if resp.status_code == 403:
            return {
                'status': 'error_auth',
                'message': 'The provisioning server rejected the API key (403 Forbidden). Contact your system administrator.',
            }

        try:
            data = resp.json()
        except Exception:
            return {
                'status': 'error',
                'message': f'Server returned non-JSON response (HTTP {resp.status_code}).',
            }

        raw_status = data.get('status', '')
        if raw_status in ('ok', 'success'):
            logger.info('Provision success for %s: %s', service.domain, data)
            data['status'] = 'ok'
            return data

        msg = (data.get('message') or data.get('error') or '').lower()
        if 'already exists' in msg or 'duplicate' in msg or 'domain exist' in msg:
            return {
                'status': 'error_domain_exists',
                'message': f"The domain '{service.domain}' already exists on the server.",
            }

        return {
            'status': 'error',
            'message': data.get('message') or data.get('error') or f'Provisioning failed (HTTP {resp.status_code}).',
        }

    except requests.ConnectionError:
        logger.error('Provision API unreachable for domain %s', service.domain)
        return {
            'status': 'error_api_unreachable',
            'message': 'Could not reach the provisioning server. It may be offline. Our team has been notified.',
        }
    except requests.Timeout:
        logger.error('Provision API timed out for domain %s', service.domain)
        return {
            'status': 'error_api_unreachable',
            'message': 'The provisioning server took too long to respond (30s timeout).',
        }
    except Exception as exc:
        logger.exception('Provision API call failed: %s', exc)
        return {'status': 'error', 'message': str(exc)}


def provision_reseller_account(service) -> dict:
    """
    Provision a Reseller Hosting account via /control/api/reseller/provision/.
    Reads storage_gb and max_accounts from the linked order's package (or service fields).
    Returns a normalised dict with status='ok' on success.
    """
    api_url, api_key = _get_api_config(getattr(service, 'server', None))

    # Resolve reseller-specific limits from the order package
    storage_gb   = getattr(service, 'storage_gb', 50)
    max_accounts = getattr(service, 'reseller_max_accounts', None)

    # Try to read from linked HostingOrder → package
    if max_accounts is None:
        try:
            order   = service.order  # OneToOne reverse
            package = order.package
            storage_gb   = package.storage_gb
            max_accounts = package.max_accounts
        except Exception:
            max_accounts = 10  # safe default

    # The control panel accepts auth via X-VoidPanel-Key header (same as shared hosting)
    # api_key is also sent in the body for older installs that validate from /etc/voidpanel_api_key

    # Try to read client package settings from the linked HostingOrder → package
    order_pkg = None
    try:
        order     = service.order
        order_pkg = order.package
    except Exception:
        pass

    def _safe_pkg_attr(pkg, attr, default):
        """Read an attr from the package, falling back to default if absent."""
        if pkg is None:
            return default
        return getattr(pkg, attr, default) or default

    # Derive a safe, unique username from the reseller's domain — NOT from service.user.username.
    # Using service.user.username (e.g. "admin") can conflict with system accounts on the
    # live control panel server, causing the provision to attach to the wrong user.
    raw_domain = getattr(service, 'domain', '') or service.user.email.split('@')[0]
    # Strip TLD and clean: jerheeer.com → jerheeer, my-site.co.uk → my-site
    cp_username = raw_domain.split('.')[0].lower()
    # Sanitize: keep only alphanumeric + hyphens, max 16 chars
    import re as _re
    cp_username = _re.sub(r'[^a-z0-9\-]', '', cp_username)[:16] or 'reseller'

    payload = {
        # api_key intentionally omitted from body — auth is via X-VoidPanel-Key header.
        # Including a non-empty api_key in the body causes auth failure on servers where
        # /etc/voidpanel_api_key is not set (expected='', so anything != '' → 401).
        'username':           cp_username,
        'email':              service.user.email,
        'domain':             getattr(service, 'domain', '') or f'{cp_username}.reseller',
        'storage_gb':         int(storage_gb),
        'max_accounts':       int(max_accounts),
        'package_name':       service.service_name,
        'company_name':       service.user.get_full_name() or service.user.username,
        # ── Per-client package settings (read from order package) ──────────
        'client_package_name':    _safe_pkg_attr(order_pkg, 'client_package_name', 'Starter Client Plan'),
        'client_storage_gb':      _safe_pkg_attr(order_pkg, 'client_storage_gb',   5),
        'client_bandwidth_gb':    _safe_pkg_attr(order_pkg, 'client_bandwidth_gb', 50),
        'client_email_accounts':  _safe_pkg_attr(order_pkg, 'client_email_accounts', 5),
        'client_databases':       _safe_pkg_attr(order_pkg, 'client_databases',    3),
        'client_subdomains':      _safe_pkg_attr(order_pkg, 'client_subdomains',   5),
        'client_ftp_accounts':    _safe_pkg_attr(order_pkg, 'client_ftp_accounts', 2),
    }

    try:
        resp = requests.post(
            f'{api_url}/control/api/reseller/provision/',
            json=payload,
            headers=_headers(api_key),   # X-VoidPanel-Key header — accepted by all installs
            timeout=60,
        )
        logger.info('Reseller provision HTTP %s for user %s', resp.status_code, service.user.username)

        if resp.status_code == 401:
            return {'status': 'error_auth', 'message': 'Reseller API key rejected. Update the API key in Super Admin → Servers for this server.'}
        if resp.status_code == 403:
            return {'status': 'error_auth', 'message': 'Reseller provisioning: access denied (403).'}

        try:
            data = resp.json()
        except Exception:
            return {'status': 'error', 'message': f'Reseller server non-JSON response (HTTP {resp.status_code}).'}

        raw_status = data.get('status', '')
        if raw_status in ('provisioned', 'ok', 'success'):
            logger.info('Reseller provision success for %s', service.user.username)
            data['status'] = 'ok'
            # Map field names to common provisioner contract
            data.setdefault('panel_url', data.get('reseller_dashboard_url', ''))
            data.setdefault('username', service.user.username)
            return data

        return {
            'status': 'error',
            'message': data.get('error') or data.get('message') or f'Reseller provisioning failed (HTTP {resp.status_code}).',
        }

    except requests.ConnectionError:
        return {'status': 'error_api_unreachable', 'message': 'Cannot reach the VoidPanel server for reseller provisioning.'}
    except requests.Timeout:
        return {'status': 'error_api_unreachable', 'message': 'Reseller provisioning server timed out.'}
    except Exception as exc:
        logger.exception('Reseller provision failed: %s', exc)
        return {'status': 'error', 'message': str(exc)}


def suspend_hosting_account(domain: str) -> dict:
    """POST to VoidPanel backend to suspend a domain."""
    from data.models import HostingService
    service = HostingService.objects.filter(domain=domain).first()
    api_url, api_key = _get_api_config(getattr(service, 'server', None) if service else None)

    try:
        resp = requests.post(
            f'{api_url}/api/provision/suspend/',
            json={'domain': domain},
            headers=_headers(api_key),
            timeout=15,
        )
        return resp.json()
    except Exception as exc:
        logger.exception('Suspend API call failed: %s', exc)
        return {'status': 'error', 'message': str(exc)}


def unsuspend_hosting_account(domain: str) -> dict:
    """POST to VoidPanel backend to unsuspend a domain."""
    from data.models import HostingService
    service = HostingService.objects.filter(domain=domain).first()
    api_url, api_key = _get_api_config(getattr(service, 'server', None) if service else None)

    try:
        resp = requests.post(
            f'{api_url}/api/provision/unsuspend/',
            json={'domain': domain},
            headers=_headers(api_key),
            timeout=15,
        )
        return resp.json()
    except Exception as exc:
        logger.exception('Unsuspend API call failed: %s', exc)
        return {'status': 'error', 'message': str(exc)}
