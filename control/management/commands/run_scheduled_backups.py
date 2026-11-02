import os
import sys
import json
import logging
import datetime
import tempfile
import subprocess
from django.core.management.base import BaseCommand
from django.utils import timezone
from control.models import CloudBackupConfig, domain as Domain, user as User
from voidplatform.config import paths

logger = logging.getLogger('voidpanel.backup')


def _is_backup_due(config, now=None):
    """
    Check if a scheduled backup is due for execution.
    """
    if not config.auto_backup_enabled:
        return False

    if now is None:
        now = timezone.now()

    # Parse target hour and minute (UTC)
    time_str = config.auto_schedule_time or '02:00'
    try:
        parts = time_str.split(':')
        target_hour = int(parts[0])
        target_min = int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        target_hour = 2
        target_min = 0

    preset = config.auto_schedule_preset or 'daily'

    # Check if already ran today
    if config.last_backup_at:
        # If last backup was within the last 20 hours for daily
        time_since_last = (now - config.last_backup_at).total_seconds()
        if preset == 'daily' and time_since_last < 20 * 3600:
            return False
        if preset == 'weekly' and time_since_last < 6 * 86400:
            return False

    # Check time window (within 15 minutes of scheduled time)
    hour_match = (now.hour == target_hour)
    min_diff = abs(now.minute - target_min)
    time_match = hour_match and (min_diff <= 15)

    if preset == 'daily':
        return time_match

    elif preset == 'weekly':
        # 0 = Sunday, 1 = Monday ... 6 = Saturday (Python weekday(): 0=Mon, 6=Sun)
        current_day_sunday_based = (now.weekday() + 1) % 7
        target_day = config.auto_schedule_weekday if config.auto_schedule_weekday is not None else 0
        return (current_day_sunday_based == target_day) and time_match

    elif preset == 'custom':
        # Try croniter if installed
        try:
            from croniter import croniter
            cron_expr = config.auto_schedule_cron or '0 2 * * *'
            iter = croniter(cron_expr, now)
            prev_run = iter.get_prev(datetime.datetime)
            # If prev_run happened within the last 15 minutes and config hasn't run since then
            if (now.replace(tzinfo=None) - prev_run).total_seconds() <= 900:
                if not config.last_backup_at or config.last_backup_at.replace(tzinfo=None) < prev_run:
                    return True
            return False
        except ImportError:
            # Fallback to daily hour check
            return time_match

    return False


def execute_backup_for_domain(domain_name, force=False, stdout=None):
    """
    Perform a complete backup for a domain and sync directly to Google Drive
    (or configured cloud provider) if enabled.
    """
    def log(msg, is_error=False):
        logger.info(msg)
        if stdout:
            stdout.write(msg)

    now = timezone.now()
    try:
        config = CloudBackupConfig.objects.get(domain=domain_name)
    except CloudBackupConfig.DoesNotExist:
        log(f"No backup configuration found for {domain_name}", is_error=True)
        return False, "Config not found"

    if not force and not _is_backup_due(config, now):
        log(f"Backup is not due for {domain_name} (preset={config.auto_schedule_preset}, time={config.auto_schedule_time})")
        return False, "Not due"

    try:
        dom_obj = Domain.objects.get(domain=domain_name)
    except Domain.DoesNotExist:
        log(f"Domain object {domain_name} does not exist", is_error=True)
        return False, "Domain does not exist"

    # Find domain owner
    owner = User.objects.filter(domain=domain_name).first()
    owner_username = owner.username if owner else dom_obj.dir

    from control.views import _get_backup_store, _resolve_mail_domain_dir
    from function import (
        get_database_names_with_filter,
        zip_multiple_locations_backup_user
    )

    backup_store = _get_backup_store(dom_obj.dir)
    timestamp_str = now.strftime('%Y%m%d_%H%M%S')
    zip_filename = f"backup_{domain_name}_{timestamp_str}"
    zip_path = os.path.join(backup_store, f"{zip_filename}.zip")

    front = os.path.join(paths.HOME_BASE, dom_obj.dir)
    mail = _resolve_mail_domain_dir(dom_obj.domain)
    open1 = os.path.join(paths.OPENDKIM_KEY_DIR, dom_obj.domain) if paths.OPENDKIM_KEY_DIR else ''
    lets = os.path.join(paths.LETSENCRYPT_LIVE, dom_obj.domain) if hasattr(paths, 'LETSENCRYPT_LIVE') else ''

    locations = [l for l in [front, mail, open1, lets] if l and os.path.exists(l)]

    log(f"Starting automated backup for {domain_name} (User: {owner_username})...")

    # 1. Dump MySQL Databases
    db_dump_dir = tempfile.mkdtemp(prefix='voidpanel_dbdump_')
    try:
        with open(paths.MYSQL_PASSWORD_FILE, 'r') as f:
            adminpw = f.read().strip()
    except Exception:
        adminpw = ''

    if adminpw:
        try:
            databases = get_database_names_with_filter(adminpw, f"{owner_username}_")
            if databases:
                for db in databases:
                    db_path = os.path.join(db_dump_dir, f"{db}.sql")
                    try:
                        with open(db_path, "w") as dump_file:
                            subprocess.run(
                                ["mysqldump", "-u", "root", f"-p{adminpw}", db],
                                stdout=dump_file,
                                stderr=subprocess.DEVNULL,
                                timeout=180
                            )
                    except Exception as e:
                        logger.warning(f"Could not dump DB {db}: {e}")
                if os.path.exists(db_dump_dir):
                    locations.append(db_dump_dir)
        except Exception as e:
            logger.warning(f"Error querying databases for {owner_username}: {e}")

    # 2. Generate ZIP archive
    zip_ok = False
    try:
        progress_file = os.path.join(backup_store, ".backup_progress")
        zip_multiple_locations_backup_user(backup_store, locations, zip_filename, owner_username, progress_file)
        zip_ok = os.path.exists(zip_path) and os.path.getsize(zip_path) > 0
    except Exception as e:
        log(f"Error zipping backup for {domain_name}: {e}", is_error=True)
        config.last_backup_status = f"Zip Failed: {str(e)[:200]}"
        config.save(update_fields=['last_backup_status'])
        return False, str(e)
    finally:
        # Cleanup DB dump
        try:
            import shutil
            shutil.rmtree(db_dump_dir, ignore_errors=True)
        except Exception:
            pass
        # Remove progress marker
        try:
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except Exception:
            pass

    if not zip_ok:
        log(f"Zip failed or produced empty file for {domain_name}", is_error=True)
        config.last_backup_status = "Backup archive creation failed"
        config.save(update_fields=['last_backup_status'])
        return False, "Archive creation failed"

    log(f"Backup archive created: {zip_path} ({round(os.path.getsize(zip_path)/(1024*1024), 2)} MB)")

    # 3. Cloud Sync (Google Drive, GCS, or S3)
    cloud_status_msg = "Local Only"
    if config.sync_after_backup or config.provider == CloudBackupConfig.PROVIDER_GDRIVE:
        log(f"Syncing backup to cloud provider '{config.provider}'...")
        try:
            if config.provider == CloudBackupConfig.PROVIDER_GDRIVE:
                from control.gdrive_backup import upload_file_to_gdrive
                res = upload_file_to_gdrive(config, zip_path)
                cloud_status_msg = f"Synced to Google Drive ({res.get('file_id')})"
                log(f"Successfully uploaded to Google Drive! File ID: {res.get('file_id')}")

            elif config.provider == CloudBackupConfig.PROVIDER_GCS:
                from google.cloud import storage as gcs_storage
                from google.oauth2 import service_account
                key_data = json.loads(config.gcs_key_json)
                creds = service_account.Credentials.from_service_account_info(key_data)
                client = gcs_storage.Client(credentials=creds, project=key_data.get('project_id'))
                bucket = client.bucket(config.gcs_bucket)
                blob = bucket.blob(f"voidpanel-backups/{domain_name}/{os.path.basename(zip_path)}")
                blob.upload_from_filename(zip_path)
                cloud_status_msg = f"Synced to GCS (gs://{config.gcs_bucket})"
                log("Successfully uploaded to Google Cloud Storage")

            elif config.provider == CloudBackupConfig.PROVIDER_S3:
                import boto3
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=config.s3_access_key,
                    aws_secret_access_key=config.s3_secret_key,
                    region_name=config.s3_region,
                )
                s3_key = f"voidpanel-backups/{domain_name}/{os.path.basename(zip_path)}"
                s3.upload_file(zip_path, config.s3_bucket, s3_key)
                cloud_status_msg = f"Synced to S3 (s3://{config.s3_bucket}/{s3_key})"
                log("Successfully uploaded to Amazon S3")

            # Remove local copy if user opted not to keep it
            if not config.keep_local_copy:
                try:
                    os.remove(zip_path)
                    log(f"Local copy removed as keep_local_copy=False.")
                except Exception as e:
                    logger.warning(f"Could not remove local copy: {e}")

        except Exception as e:
            log(f"Cloud sync error for {domain_name}: {e}", is_error=True)
            cloud_status_msg = f"Cloud sync failed: {str(e)[:150]}"

    # 4. Update status and notification
    config.last_backup_at = now
    config.last_backup_status = f"Completed at {now.strftime('%Y-%m-%d %H:%M:%S UTC')} — {cloud_status_msg}"
    config.save(update_fields=['last_backup_at', 'last_backup_status'])

    try:
        from control.utils import trigger_backup_created_notification
        trigger_backup_created_notification(str(owner_username), str(domain_name), zip_filename + ".zip")
    except Exception:
        pass

    log(f"Finished backup for {domain_name}: {config.last_backup_status}")
    return True, config.last_backup_status


class Command(BaseCommand):
    help = 'Runs scheduled automated backups for domains and syncs them to Google Drive or other configured cloud storage.'

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=str, help='Run backup for a specific domain only')
        parser.add_argument('--force', action='store_true', help='Force backup now regardless of schedule check')

    def handle(self, *args, **options):
        target_domain = options.get('domain')
        force = options.get('force', False)

        if target_domain:
            qs = CloudBackupConfig.objects.filter(domain=target_domain)
            if not qs.exists():
                self.stdout.write(self.style.ERROR(f"No CloudBackupConfig found for domain: {target_domain}"))
                return
        else:
            qs = CloudBackupConfig.objects.filter(auto_backup_enabled=True)

        count = qs.count()
        self.stdout.write(f"Checking {count} domain backup configurations...")

        for config in qs:
            try:
                execute_backup_for_domain(config.domain, force=force, stdout=self.stdout)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Unhandled error backing up {config.domain}: {e}"))
