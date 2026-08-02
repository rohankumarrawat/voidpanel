"""
VoidApp API — Backup management endpoints.

GET    /api/v1/backups/             — List backups
POST   /api/v1/backups/create/      — Create backup
GET    /api/v1/backups/status/      — Check backup progress
POST   /api/v1/backups/delete/      — Delete backup
"""

import os
import json
import datetime
import threading
import logging

from control.models import domain as Domain, user as CtrlUser
from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')


def _get_backup_store(username):
    """Get backup directory (same pattern as panel)."""
    import subprocess
    from voidplatform.config import paths
    store = os.path.join(paths.HOME_BASE, str(username), '.backups')
    subprocess.run(['sudo', 'mkdir', '-p', store], check=False)
    subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', store], check=False)
    subprocess.run(['sudo', 'chmod', '777', store], check=False)
    return store


@api_auth_required()
def api_backup_list(request):
    """List all available backups for the current user."""
    ctrl_user = request.ctrl_user
    username = request.ctrl_username

    try:
        store = _get_backup_store(username)
        backups = []

        if os.path.exists(store):
            for f in sorted(os.listdir(store), reverse=True):
                if f.endswith('.zip') and not f.startswith('.'):
                    fpath = os.path.join(store, f)
                    try:
                        stat = os.stat(fpath)
                        size_mb = round(stat.st_size / (1024 * 1024), 2)
                        created = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                    except Exception:
                        size_mb = 0
                        created = ''

                    backups.append({
                        'filename': f,
                        'size_mb': size_mb,
                        'created': created,
                    })

        return api_response(data={'backups': backups})

    except Exception as e:
        return api_response(error=f'Failed to list backups: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_backup_create(request):
    """Trigger a full backup in the background."""
    ctrl_user = request.ctrl_user
    username = request.ctrl_username

    try:
        from voidplatform.config import paths
        from function import (
            get_directory_size_in_mb, get_database_names_with_filter,
            zip_multiple_locations_backup_user
        )

        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
        store = _get_backup_store(dom_obj.dir)

        # Check if backup already in progress
        progress_file = os.path.join(store, '.backup_progress')
        if os.path.exists(progress_file):
            return api_response(error='A backup is already in progress.', status=409)

        # Build locations to backup
        front = os.path.join(paths.HOME_BASE, dom_obj.dir)
        mail_dir = os.path.join(paths.HOME_BASE, dom_obj.dir, 'mail', dom_obj.domain)
        lets_dir = os.path.join(paths.LETSENCRYPT_LIVE, dom_obj.domain) if hasattr(paths, 'LETSENCRYPT_LIVE') else ''
        locations = [l for l in [front, mail_dir, lets_dir] if l and os.path.exists(l)]

        # Get admin password for DB dumps
        try:
            with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
                adminpw = f.read().strip()
        except Exception:
            adminpw = ''

        zip_filename = f"backup_{dom_obj.domain}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        def _run_backup():
            import tempfile
            import subprocess
            import time as _time
            completed_file = os.path.join(store, '.backup_done')
            try:
                if os.path.exists(completed_file):
                    os.remove(completed_file)
            except Exception:
                pass

            try:
                with open(progress_file, 'w') as pf:
                    pf.write(json.dumps({'pct': 5, 'ts': _time.time()}))
            except Exception:
                pass

            # Dump databases
            db_dump_dir = tempfile.mkdtemp(prefix='voidpanel_dbdump_')
            databases = get_database_names_with_filter(adminpw, f'{username}_')
            if databases:
                for db in databases:
                    db_path = os.path.join(db_dump_dir, f'{db}.sql')
                    try:
                        with open(db_path, 'w') as dump_f:
                            subprocess.run(
                                ['mysqldump', '-u', 'root', f'-p{adminpw}', db],
                                stdout=dump_f, stderr=subprocess.DEVNULL
                            )
                    except Exception:
                        pass

            zip_ok = False
            try:
                zip_multiple_locations_backup_user(store, locations, zip_filename, username, progress_file)
                zip_ok = True
            except Exception:
                pass
            finally:
                import shutil
                shutil.rmtree(db_dump_dir, ignore_errors=True)
                try:
                    if os.path.exists(progress_file):
                        os.remove(progress_file)
                except Exception:
                    pass
                try:
                    with open(completed_file, 'w') as cf:
                        cf.write(json.dumps({'ok': zip_ok, 'ts': _time.time()}))
                except Exception:
                    pass

        threading.Thread(target=_run_backup, daemon=True).start()

        return api_response(data={
            'message': 'Backup started in background.',
            'filename': f'{zip_filename}.zip',
        })

    except Exception as e:
        logger.exception('Failed to start backup')
        return api_response(error=f'Failed to start backup: {str(e)}', status=500)


@api_auth_required()
def api_backup_status(request):
    """Check backup progress."""
    ctrl_user = request.ctrl_user
    username = request.ctrl_username

    try:
        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
        store = _get_backup_store(dom_obj.dir)
        progress_file = os.path.join(store, '.backup_progress')
        completed_file = os.path.join(store, '.backup_done')

        # Check completed
        if os.path.exists(completed_file) and not os.path.exists(progress_file):
            try:
                os.remove(completed_file)
            except Exception:
                pass
            return api_response(data={'status': 'completed'})

        # Check in progress
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress = json.loads(f.read().strip())
                return api_response(data={
                    'status': 'running',
                    'percentage': progress.get('pct', 0)
                })
            except Exception:
                return api_response(data={'status': 'running', 'percentage': 0})

        return api_response(data={'status': 'idle'})

    except Exception as e:
        return api_response(data={'status': 'idle'})


@api_auth_required()
@require_post
def api_backup_delete(request):
    """
    Delete a backup file.

    POST body: { "filename": "backup_example.com_20260801_120000.zip" }
    """
    data = parse_json_body(request)
    filename = data.get('filename', '').strip()
    ctrl_user = request.ctrl_user
    username = request.ctrl_username

    if not filename or '..' in filename or '/' in filename:
        return api_response(error='Invalid filename.', status=400)

    try:
        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
        store = _get_backup_store(dom_obj.dir)
        filepath = os.path.join(store, filename)

        if not os.path.exists(filepath):
            return api_response(error='Backup file not found.', status=404)

        os.remove(filepath)
        return api_response(data={'message': f'Backup {filename} deleted.'})

    except Exception as e:
        return api_response(error=f'Failed to delete backup: {str(e)}', status=500)
