"""
VoidApp API — Dashboard overview endpoint.

GET /api/v1/dashboard/ — Returns all dashboard stats for the current user.
"""

import os
import logging

from control.models import (
    user as CtrlUser, domain as Domain, package as Package,
    allemail, subdomainname, ftpaccount, cron as CronModel
)
from userapp.decorators import api_response, api_auth_required

logger = logging.getLogger('voidpanel.userapp')


@api_auth_required()
def api_dashboard(request):
    """
    Full dashboard stats including storage, email, DB, FTP, subdomain quotas.

    Returns a comprehensive overview matching the web panel dashboard.
    """
    ctrl_user = request.ctrl_user
    username = request.ctrl_username

    # Get package
    pkg = _safe_get_package(ctrl_user.hosting_package)

    # ── Server IP ────────────────────────────────────────────────────────
    try:
        from function import get_server_ip
        server_ip = get_server_ip()
    except Exception:
        server_ip = ''

    # ── Storage ──────────────────────────────────────────────────────────
    storage_total = _safe_int(pkg.storage)
    storage_used = 0
    try:
        from function import get_directory_size_in_mb
        from voidplatform.config import paths
        home_dir = os.path.join(paths.HOME_BASE, str(username))
        storage_used = int(get_directory_size_in_mb(home_dir))
    except Exception:
        pass

    storage_unlimited = (storage_total == 0)
    storage_pct = 0
    if not storage_unlimited and storage_total > 0:
        storage_pct = min(round((storage_used / storage_total) * 100, 1), 100)

    # ── Email ────────────────────────────────────────────────────────────
    email_total = _safe_int(pkg.email_accounts)
    email_used = allemail.objects.filter(domain=ctrl_user.domain).count()
    email_unlimited = (email_total == 0)
    email_pct = 0
    if not email_unlimited and email_total > 0:
        email_pct = min(round((email_used / email_total) * 100, 1), 100)

    # ── Databases ────────────────────────────────────────────────────────
    db_total = _safe_int(pkg.databases_allowed)
    db_used = 0
    try:
        from function import get_database_names_with_filter
        from voidplatform.config import paths as _paths
        with open(_paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpw = f.read().strip()
        db_used = len(get_database_names_with_filter(adminpw, f'{username}_'))
    except Exception:
        pass
    db_unlimited = (db_total == 0)
    db_pct = 0
    if not db_unlimited and db_total > 0:
        db_pct = min(round((db_used / db_total) * 100, 1), 100)

    # ── FTP ──────────────────────────────────────────────────────────────
    ftp_total = _safe_int(pkg.ftp)
    ftp_used = ftpaccount.objects.filter(main=str(username)).count()
    ftp_unlimited = (ftp_total == 0)
    ftp_pct = 0
    if not ftp_unlimited and ftp_total > 0:
        ftp_pct = min(round((ftp_used / ftp_total) * 100, 1), 100)

    # ── Subdomains ───────────────────────────────────────────────────────
    sub_total = _safe_int(pkg.subdomain)
    sub_used = subdomainname.objects.filter(domain=ctrl_user.domain).count()
    sub_unlimited = (sub_total == 0)
    sub_pct = 0
    if not sub_unlimited and sub_total > 0:
        sub_pct = min(round((sub_used / sub_total) * 100, 1), 100)

    # ── Cron jobs count ──────────────────────────────────────────────────
    cron_count = CronModel.objects.filter(domain=ctrl_user.domain).count()

    # ── SSL status ───────────────────────────────────────────────────────
    ssl_active = False
    try:
        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
        ssl_active = dom_obj.sslstatus
    except Domain.DoesNotExist:
        pass

    # ── Website status ───────────────────────────────────────────────────
    website_live = False
    try:
        from function import is_website_live
        website_live = is_website_live(f'http://{ctrl_user.domain}')
    except Exception:
        pass

    data = {
        'domain': ctrl_user.domain,
        'username': ctrl_user.username,
        'server_ip': server_ip,
        'ssl_active': ssl_active,
        'website_live': website_live,
        'package_name': ctrl_user.hosting_package,
        'quotas': {
            'storage': {
                'used': storage_used,
                'total': storage_total,
                'unlimited': storage_unlimited,
                'percentage': storage_pct,
                'unit': 'MB',
            },
            'email': {
                'used': email_used,
                'total': email_total,
                'unlimited': email_unlimited,
                'percentage': email_pct,
            },
            'databases': {
                'used': db_used,
                'total': db_total,
                'unlimited': db_unlimited,
                'percentage': db_pct,
            },
            'ftp': {
                'used': ftp_used,
                'total': ftp_total,
                'unlimited': ftp_unlimited,
                'percentage': ftp_pct,
            },
            'subdomains': {
                'used': sub_used,
                'total': sub_total,
                'unlimited': sub_unlimited,
                'percentage': sub_pct,
            },
        },
        'cron_jobs': cron_count,
    }

    return api_response(data=data)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_get_package(name):
    """Get package or return a fallback with zeros."""
    try:
        if name:
            return Package.objects.get(name=name)
    except Package.DoesNotExist:
        pass
    return Package(storage='0', email_accounts='0', subdomain='0',
                   databases_allowed='0', ftp='0', bandwidth='0')


def _safe_int(val):
    try:
        v = str(val).strip().lower()
        if v in ('unlimited', '∞', ''):
            return 0
        return int(v)
    except (ValueError, TypeError):
        return 0
