"""
VoidApp API — Activity log endpoint.

GET /api/v1/activity/ — Paginated activity log for the current user.
"""

import logging
from control.models import ActivityLog
from userapp.decorators import api_response, api_auth_required

logger = logging.getLogger('voidpanel.userapp')


@api_auth_required()
def api_activity_list(request):
    """
    List activity logs for the current user's domain.

    Query params:
    - page: Page number (default 1)
    - limit: Items per page (default 20, max 100)
    - level: Filter by level (success, info, warning, error)
    - category: Filter by category (email, db, ssl, ftp, domain, etc.)
    """
    ctrl_user = request.ctrl_user
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 20)), 100)
    level = request.GET.get('level', '').strip()
    category = request.GET.get('category', '').strip()

    # Filter by user's domain
    qs = ActivityLog.objects.filter(domain=ctrl_user.domain)

    if level:
        qs = qs.filter(level=level)
    if category:
        qs = qs.filter(category=category)

    total = qs.count()
    offset = (page - 1) * limit
    logs = qs[offset:offset + limit]

    entries = []
    for log in logs:
        entries.append({
            'id': log.id,
            'timestamp': log.timestamp.isoformat() if log.timestamp else '',
            'level': log.level,
            'category': log.category,
            'action': log.action,
            'detail': log.detail,
            'ip': log.ip,
        })

    return api_response(data={
        'entries': entries,
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit if limit > 0 else 0,
    })
