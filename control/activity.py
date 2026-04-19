"""
control.activity
~~~~~~~~~~~~~~~~
Thread-safe helper for writing ActivityLog records.

Usage:
    from control.activity import log_activity
    log_activity(request, 'success', 'mern', domain='example.com',
                 action='MERN deployed', detail='React compiled in 3m 12s')
"""
from __future__ import annotations
import threading
from typing import Optional
from django.http import JsonResponse, HttpRequest


def log_activity(
    request_or_user: "HttpRequest | str | None",
    level: str,
    category: str,
    *,
    domain: str = '',
    action: str,
    detail: str = '',
) -> None:
    """
    Write one ActivityLog row, safely.

    :param request_or_user: A Django HttpRequest (user/ip extracted automatically)
                            or a plain username string, or None.
    :param level:    'success' | 'info' | 'warning' | 'error'
    :param category: 'domain' | 'python' | 'mern' | 'email' | 'db' |
                     'ssl' | 'ftp' | 'system' | 'nginx' | 'backup'
    :param domain:   Target domain / subdomain (optional)
    :param action:   Short, human-readable title
    :param detail:   Long error message, stack trace, etc.
    """
    def _write():
        try:
            from control.models import ActivityLog

            username = ''
            ip       = ''

            if hasattr(request_or_user, 'user'):
                req = request_or_user
                username = getattr(req.user, 'username', '') if req.user.is_authenticated else ''
                ip = (
                    req.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                    or req.META.get('REMOTE_ADDR', '')
                )
            elif isinstance(request_or_user, str):
                username = request_or_user

            ActivityLog.objects.create(
                level    = level,
                category = category,
                domain   = domain,
                username = username,
                action   = action,
                detail   = detail,
                ip       = ip,
            )
        except Exception:
            pass  # Never crash the caller

    threading.Thread(target=_write, daemon=True).start()


# ── API Views ──────────────────────────────────────────────────────────────────

def api_activity_logs(request: HttpRequest) -> JsonResponse:
    """
    GET /api/activity-logs/

    Query params:
        domain    – filter by domain (optional)
        level     – filter by level (optional)
        category  – filter by category (optional)
        limit     – max rows to return (default 100, max 500)
        offset    – pagination offset (default 0)
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    from control.models import ActivityLog

    qs = ActivityLog.objects.all()

    # Non-superusers only see their own domain's logs
    if not request.user.is_superuser:
        from control.models import user as ctrl_user, domain as ctrl_domain
        try:
            u = ctrl_user.objects.get(username=request.user.username)
            # Collect all domains + subdomains for this user
            from control.models import subdomainname
            user_domains = list(ctrl_domain.objects.filter(dir=u.username).values_list('domain', flat=True))
            user_subs    = list(subdomainname.objects.filter(domain__in=user_domains).values_list('subdomain', flat=True))
            all_domains  = user_domains + user_subs
            qs = qs.filter(domain__in=all_domains)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=403)

    # Filters
    domain_filter   = request.GET.get('domain', '').strip()
    level_filter    = request.GET.get('level', '').strip()
    category_filter = request.GET.get('category', '').strip()
    search          = request.GET.get('q', '').strip()

    if domain_filter:
        qs = qs.filter(domain__icontains=domain_filter)
    if level_filter:
        qs = qs.filter(level=level_filter)
    if category_filter:
        qs = qs.filter(category=category_filter)
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(action__icontains=search) | Q(detail__icontains=search) | Q(domain__icontains=search))

    try:
        limit  = max(1, min(int(request.GET.get('limit', 100)), 500))
        offset = max(0, int(request.GET.get('offset', 0)))
    except ValueError:
        limit, offset = 100, 0

    total = qs.count()
    rows  = list(qs[offset:offset + limit].values(
        'id', 'timestamp', 'level', 'category', 'domain', 'username', 'action', 'detail', 'ip'
    ))

    # Convert timestamps to ISO format
    for row in rows:
        if row['timestamp']:
            row['timestamp'] = row['timestamp'].isoformat()

    return JsonResponse({'status': 'ok', 'total': total, 'logs': rows})


def api_clear_logs(request: HttpRequest) -> JsonResponse:
    """DELETE /api/activity-logs/clear/ — superadmin only."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    from control.models import ActivityLog
    deleted, _ = ActivityLog.objects.all().delete()
    log_activity(request, 'warning', 'system',
                 action='Activity log cleared',
                 detail=f'{deleted} records removed by superadmin')
    return JsonResponse({'status': 'ok', 'deleted': deleted})
