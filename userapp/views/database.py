"""
VoidApp API — Database management endpoints.

GET    /api/v1/databases/              — List databases
POST   /api/v1/databases/create/       — Create database
POST   /api/v1/databases/delete/       — Delete database
GET    /api/v1/databases/users/        — List DB users
POST   /api/v1/databases/users/create/ — Create DB user
"""

import sys
import logging

from control.models import user as CtrlUser, package as Package
from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')


def _get_admin_password():
    """Read MySQL root password from config."""
    try:
        from voidplatform.config import paths
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            return f.read().strip()
    except Exception:
        return ''


@api_auth_required()
def api_database_list(request):
    """List all databases for the current user."""
    ctrl_user = request.ctrl_user
    username = request.ctrl_username
    adminpw = _get_admin_password()

    prefix = f'{username}_'
    databases = []
    try:
        from function import get_database_names_with_filter
        databases = get_database_names_with_filter(adminpw, prefix)
    except Exception as e:
        logger.warning('Failed to list databases: %s', e)

    # Get DB users
    db_users = []
    try:
        from function import get_database_users_with_filter
        db_users = get_database_users_with_filter(adminpw, prefix)
    except Exception:
        pass

    # Get mappings
    mappings = []
    try:
        from function import get_database_privileges_with_filter
        mappings = get_database_privileges_with_filter(adminpw, prefix)
    except Exception:
        pass

    # Package quota
    pkg = _get_pkg(ctrl_user.hosting_package)
    total = _safe_int(pkg.databases_allowed) if pkg else 0

    return api_response(data={
        'databases': databases if isinstance(databases, list) else list(databases),
        'users': db_users if isinstance(db_users, list) else list(db_users),
        'mappings': mappings if isinstance(mappings, list) else list(mappings),
        'used': len(databases) if databases else 0,
        'total': total,
        'unlimited': total == 0,
        'prefix': prefix,
    })


@api_auth_required()
@require_post
def api_database_create(request):
    """
    Create a new MySQL database.

    POST body: { "name": "mydb" }
    The database will be prefixed with username_ automatically.
    """
    data = parse_json_body(request)
    name = data.get('name', '').strip()
    ctrl_user = request.ctrl_user
    username = request.ctrl_username
    adminpw = _get_admin_password()

    if not name:
        return api_response(error='Database name is required.', status=400)

    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        return api_response(error='Invalid database name. Use only letters, numbers, underscores.', status=400)

    final_name = f'{username}_{name}'

    # Check quota
    pkg = _get_pkg(ctrl_user.hosting_package)
    if pkg:
        max_db = _safe_int(pkg.databases_allowed)
        if max_db > 0:
            from function import get_database_names_with_filter
            current = len(get_database_names_with_filter(adminpw, f'{username}_'))
            if current >= max_db:
                return api_response(
                    error=f'Quota exceeded. Maximum {max_db} databases allowed.',
                    status=403
                )

    # Create the database
    try:
        from function import create_database_and_table
        if create_database_and_table(final_name, adminpw):
            try:
                from control.activity import log_activity
                log_activity(request, 'success', 'db', domain=ctrl_user.domain,
                             action=f'Database created: {final_name}',
                             detail='Created via VoidApp API')
            except Exception:
                pass
            return api_response(data={
                'name': final_name,
                'message': 'Database created successfully.'
            })
        else:
            return api_response(error='Database creation failed.', status=500)
    except Exception as e:
        logger.exception('Failed to create database %s', final_name)
        return api_response(error=f'Failed to create database: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_database_delete(request):
    """
    Delete a MySQL database.

    POST body: { "name": "username_mydb" }
    """
    data = parse_json_body(request)
    name = data.get('name', '').strip()
    ctrl_user = request.ctrl_user
    username = request.ctrl_username
    adminpw = _get_admin_password()

    if not name:
        return api_response(error='Database name is required.', status=400)

    # Ownership check: database must be prefixed with username_
    if not name.startswith(f'{username}_'):
        return api_response(error='You do not own this database.', status=403)

    try:
        from function import remove_database
        if remove_database(name, adminpw):
            try:
                from control.activity import log_activity
                log_activity(request, 'success', 'db', domain=ctrl_user.domain,
                             action=f'Database deleted: {name}',
                             detail='Deleted via VoidApp API')
            except Exception:
                pass
            return api_response(data={'message': f'Database {name} deleted.'})
        else:
            return api_response(error='Failed to delete database.', status=500)
    except Exception as e:
        return api_response(error=f'Failed to delete database: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_database_user_create(request):
    """
    Create a MySQL user.

    POST body: { "username": "myuser", "password": "pass123" }
    """
    data = parse_json_body(request)
    name = data.get('username', '').strip()
    password = data.get('password', '').strip()
    ctrl_user = request.ctrl_user
    username = request.ctrl_username
    adminpw = _get_admin_password()

    if not name or not password:
        return api_response(error='Username and password are required.', status=400)

    final_name = f'{username}_{name}'

    try:
        from function import create_mysql_user
        if create_mysql_user(final_name, password, adminpw):
            return api_response(data={
                'username': final_name,
                'message': 'Database user created.'
            })
        else:
            return api_response(error='Failed to create database user.', status=500)
    except Exception as e:
        return api_response(error=f'Failed to create user: {str(e)}', status=500)


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
