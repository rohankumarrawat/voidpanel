"""
VoidApp API — Cron job management endpoints.

GET    /api/v1/cron/        — List cron jobs
POST   /api/v1/cron/create/ — Create cron job
POST   /api/v1/cron/delete/ — Delete cron job
"""

import sys
import subprocess
import logging

from control.models import cron as CronModel, user as CtrlUser
from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')


@api_auth_required()
def api_cron_list(request):
    """List all cron jobs for the current user's domain."""
    ctrl_user = request.ctrl_user
    crons = CronModel.objects.filter(domain=ctrl_user.domain)

    cron_list = []
    for c in crons:
        cron_list.append({
            'id': c.id,
            'schedule': c.duratioin,
            'command': c.path,
            'domain': c.domain,
        })

    return api_response(data={'cron_jobs': cron_list})


@api_auth_required()
@require_post
def api_cron_create(request):
    """
    Create a new cron job.

    POST body:
    {
        "schedule": "*/5 * * * *",
        "command": "/usr/bin/php /home/user/public_html/cron.php"
    }
    """
    data = parse_json_body(request)
    schedule = data.get('schedule', '').strip()
    command = data.get('command', '').strip()
    ctrl_user = request.ctrl_user

    if not schedule or not command:
        return api_response(error='Schedule and command are required.', status=400)

    # Sanitize — remove newlines to prevent cron injection
    schedule = schedule.replace('\n', '').replace('\r', '')
    command = command.replace('\n', '').replace('\r', '')

    # Basic cron schedule validation
    parts = schedule.split()
    if len(parts) < 5:
        return api_response(error='Invalid cron schedule. Must have 5 fields (min hour dom month dow).', status=400)

    try:
        if sys.platform != 'win32':
            # Read current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crons = result.stdout if result.returncode == 0 else ''

            # Add new cron entry using memory buffer (no shell injection)
            new_cron = f'{schedule} {command}\n'
            combined = new_cron + current_crons
            subprocess.run(['crontab', '-'], input=combined, text=True)
        else:
            from voidplatform.windows.cron import add_cron as _add_cron
            _add_cron(schedule, command)

        cron_obj = CronModel.objects.create(
            domain=ctrl_user.domain,
            path=command,
            duratioin=schedule
        )

        try:
            from control.activity import log_activity
            log_activity(request, 'success', 'system', domain=ctrl_user.domain,
                         action=f'Cron job created: {schedule} {command}',
                         detail='Created via VoidApp API')
        except Exception:
            pass

        return api_response(data={
            'id': cron_obj.id,
            'message': 'Cron job created successfully.'
        })

    except Exception as e:
        logger.exception('Failed to create cron job')
        return api_response(error=f'Failed to create cron job: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_cron_delete(request):
    """
    Delete a cron job.

    POST body: { "id": 123 }
    """
    data = parse_json_body(request)
    cron_id = data.get('id')
    ctrl_user = request.ctrl_user

    if not cron_id:
        return api_response(error='Cron job ID is required.', status=400)

    # Ownership check
    try:
        cron_obj = CronModel.objects.get(id=cron_id, domain=ctrl_user.domain)
    except CronModel.DoesNotExist:
        return api_response(error='Cron job not found.', status=404)

    try:
        if sys.platform != 'win32':
            # Remove from system crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crons = result.stdout if result.returncode == 0 else ''

            # Filter out lines containing this command
            filtered = '\n'.join(
                line for line in current_crons.split('\n')
                if cron_obj.path not in line
            ) + '\n'
            subprocess.run(['crontab', '-'], input=filtered, text=True)
        else:
            from voidplatform.windows.cron import delete_cron as _delete_cron
            _delete_cron(cron_obj.path)

        cron_obj.delete()

        return api_response(data={'message': 'Cron job deleted.'})

    except Exception as e:
        return api_response(error=f'Failed to delete cron job: {str(e)}', status=500)
