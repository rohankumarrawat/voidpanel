"""
VoidApp API — DNS zone management endpoints.

GET    /api/v1/dns/records/        — List DNS records
POST   /api/v1/dns/records/create/ — Add DNS record
POST   /api/v1/dns/records/edit/   — Edit DNS record
POST   /api/v1/dns/records/delete/ — Delete DNS record
"""

import os
import logging

from control.models import domain as Domain, user as CtrlUser
from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')


@api_auth_required()
def api_dns_list(request):
    """List all DNS records for the user's domain."""
    ctrl_user = request.ctrl_user

    try:
        from voidplatform.config import paths
        from function import get_active_zone_file_path, parse_dns_zone_file, format_dns_data

        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
        zone_file = get_active_zone_file_path(ctrl_user.domain)

        if not zone_file or not os.path.exists(zone_file):
            # Try default path
            zone_file = os.path.join(paths.BIND_ZONE_DIR, f'db.{ctrl_user.domain}')

        records = []
        if os.path.exists(zone_file):
            raw = parse_dns_zone_file(zone_file)
            records = format_dns_data(raw)

        return api_response(data={
            'domain': ctrl_user.domain,
            'records': records,
        })

    except Domain.DoesNotExist:
        return api_response(error='Domain not found.', status=404)
    except Exception as e:
        logger.exception('Failed to read DNS for %s', ctrl_user.domain)
        return api_response(error=f'Failed to read DNS records: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_dns_add(request):
    """
    Add a DNS record.

    POST body:
    {
        "type": "A",
        "name": "www",
        "value": "1.2.3.4",
        "ttl": "3600"
    }
    """
    data = parse_json_body(request)
    record_type = data.get('type', '').strip().upper()
    name = data.get('name', '').strip()
    value = data.get('value', '').strip()
    ttl = data.get('ttl', '3600').strip()
    ctrl_user = request.ctrl_user

    if not record_type or not name or not value:
        return api_response(error='Type, name, and value are required.', status=400)

    valid_types = {'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'NS', 'CAA'}
    if record_type not in valid_types:
        return api_response(error=f'Invalid record type. Use: {", ".join(valid_types)}', status=400)

    try:
        from voidplatform.config import paths
        from function import get_active_zone_file_path, update_soa_serial_in_content, fix_zone_file_permissions
        from voidplatform import get_platform

        zone_file = get_active_zone_file_path(ctrl_user.domain)
        if not zone_file:
            zone_file = os.path.join(paths.BIND_ZONE_DIR, f'db.{ctrl_user.domain}')

        if not os.path.exists(zone_file):
            return api_response(error='Zone file not found.', status=404)

        # Read current content
        with open(zone_file, 'r') as f:
            content = f.read()

        # Build record line
        if record_type == 'MX':
            priority = data.get('priority', '10').strip()
            record_line = f'{name}\t{ttl}\tIN\tMX\t{priority}\t{value}\n'
        elif record_type == 'TXT':
            if not value.startswith('"'):
                value = f'"{value}"'
            record_line = f'{name}\t{ttl}\tIN\tTXT\t{value}\n'
        else:
            record_line = f'{name}\t{ttl}\tIN\t{record_type}\t{value}\n'

        # Update SOA serial and append record
        content = update_soa_serial_in_content(content)
        content += record_line

        with open(zone_file, 'w') as f:
            f.write(content)

        fix_zone_file_permissions(zone_file)

        # Reload DNS
        try:
            from panel.views import get_dns_service_name
            get_platform().services.reload(get_dns_service_name())
        except Exception:
            pass

        return api_response(data={'message': 'DNS record added.'})

    except Exception as e:
        logger.exception('Failed to add DNS record')
        return api_response(error=f'Failed to add record: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_dns_delete(request):
    """
    Delete a DNS record.

    POST body:
    {
        "line_content": "www\t3600\tIN\tA\t1.2.3.4"
    }
    """
    data = parse_json_body(request)
    line_content = data.get('line_content', '').strip()
    ctrl_user = request.ctrl_user

    if not line_content:
        return api_response(error='Record content is required.', status=400)

    try:
        from voidplatform.config import paths
        from function import get_active_zone_file_path, update_soa_serial_in_content, fix_zone_file_permissions
        from voidplatform import get_platform

        zone_file = get_active_zone_file_path(ctrl_user.domain)
        if not zone_file:
            zone_file = os.path.join(paths.BIND_ZONE_DIR, f'db.{ctrl_user.domain}')

        with open(zone_file, 'r') as f:
            lines = f.readlines()

        # Remove matching line
        new_lines = [l for l in lines if l.strip() != line_content.strip()]

        if len(new_lines) == len(lines):
            return api_response(error='Record not found.', status=404)

        content = ''.join(new_lines)
        content = update_soa_serial_in_content(content)

        with open(zone_file, 'w') as f:
            f.write(content)

        fix_zone_file_permissions(zone_file)

        try:
            from panel.views import get_dns_service_name
            get_platform().services.reload(get_dns_service_name())
        except Exception:
            pass

        return api_response(data={'message': 'DNS record deleted.'})

    except Exception as e:
        return api_response(error=f'Failed to delete record: {str(e)}', status=500)
