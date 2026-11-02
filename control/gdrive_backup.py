"""
VoidPanel Google Drive Backup & Sync Integration.
Handles OAuth 2.0 and Service Account token management,
folder auto-creation (VoidPanel Backups/<domain>/),
resumable chunked file uploads, and connection testing.
"""

import os
import json
import logging
import datetime
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

GDRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GDRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GDRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"


def get_gdrive_access_token(config):
    """
    Obtain a valid Google Drive access token for the given CloudBackupConfig.
    Supports both Service Account JSON mode and OAuth 2.0 refresh token mode.
    """
    if config.gdrive_auth_mode == 'service_account':
        if not config.gdrive_service_account_json or not config.gdrive_service_account_json.strip():
            raise ValueError("Service Account JSON key is empty.")
        
        try:
            key_data = json.loads(config.gdrive_service_account_json.strip())
        except Exception as e:
            raise ValueError(f"Invalid Service Account JSON format: {str(e)}")

        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_info(key_data, scopes=scopes)
        creds.refresh(Request())
        return creds.token

    else:
        # OAuth 2.0 Mode
        if not config.gdrive_refresh_token or not config.gdrive_refresh_token.strip():
            raise ValueError("Google Drive is not connected. Please authorize Google Drive first.")

        # Check cached access token
        now = timezone.now()
        if (
            config.gdrive_access_token
            and config.gdrive_token_expiry
            and config.gdrive_token_expiry > (now + datetime.timedelta(minutes=5))
        ):
            return config.gdrive_access_token

        # Exchange refresh token for fresh access token
        client_id = config.gdrive_client_id.strip() if config.gdrive_client_id else ''
        client_secret = config.gdrive_client_secret.strip() if config.gdrive_client_secret else ''

        if not client_id or not client_secret:
            # Fall back to settings if defined globally
            from django.conf import settings
            client_id = getattr(settings, 'GOOGLE_DRIVE_CLIENT_ID', client_id)
            client_secret = getattr(settings, 'GOOGLE_DRIVE_CLIENT_SECRET', client_secret)

        if not client_id or not client_secret:
            raise ValueError("Google OAuth Client ID or Client Secret is missing.")

        payload = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': config.gdrive_refresh_token.strip(),
            'grant_type': 'refresh_token',
        }

        resp = requests.post(OAUTH_TOKEN_URL, data=payload, timeout=20)
        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_data = resp.json()
                err_msg = err_data.get('error_description') or err_data.get('error') or resp.text
            except Exception:
                pass
            raise ValueError(f"Failed to refresh Google Drive token: {err_msg}")

        data = resp.json()
        new_token = data.get('access_token')
        expires_in = data.get('expires_in', 3600)

        if not new_token:
            raise ValueError("Google did not return an access token.")

        # Cache token in model
        config.gdrive_access_token = new_token
        config.gdrive_token_expiry = now + datetime.timedelta(seconds=int(expires_in))
        config.save(update_fields=['gdrive_access_token', 'gdrive_token_expiry'])

        return new_token


def test_gdrive_connection(config):
    """
    Test Google Drive connection and retrieve user email and Drive quota info.
    Returns: dict(status='success'|'error', email=..., quota=..., message=...)
    """
    try:
        token = get_gdrive_access_token(config)
        headers = {'Authorization': f'Bearer {token}'}

        # Query user profile and storage quota
        url = f"{GDRIVE_API_BASE}/about?fields=user,storageQuota"
        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code != 200:
            return {
                'status': 'error',
                'message': f"Google Drive API error ({resp.status_code}): {resp.text}"
            }

        data = resp.json()
        user_info = data.get('user', {})
        quota_info = data.get('storageQuota', {})

        email = user_info.get('emailAddress', '')
        display_name = user_info.get('displayName', '')

        # Save user email if found
        if email and config.gdrive_user_email != email:
            config.gdrive_user_email = email
            config.save(update_fields=['gdrive_user_email'])

        usage_bytes = int(quota_info.get('usage', 0))
        limit_bytes = int(quota_info.get('limit', 0))

        usage_mb = round(usage_bytes / (1024 * 1024), 1)
        limit_mb = round(limit_bytes / (1024 * 1024), 1) if limit_bytes > 0 else 'Unlimited'

        return {
            'status': 'success',
            'email': email,
            'display_name': display_name,
            'usage_mb': usage_mb,
            'limit_mb': limit_mb,
            'message': f"Connected successfully as {email or display_name} ({usage_mb} MB used)",
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def get_or_create_gdrive_folder(access_token, folder_name, parent_id=None):
    """
    Finds an existing folder with `folder_name` (under `parent_id` if given)
    or creates it if not found.
    Returns: folder ID (str)
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    # Escape single quotes in folder name
    safe_name = folder_name.replace("'", "\\'")
    query = f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    search_url = f"{GDRIVE_API_BASE}/files?q={requests.utils.quote(query)}&fields=files(id,name)&spaces=drive"
    resp = requests.get(search_url, headers=headers, timeout=20)

    if resp.status_code == 200:
        files = resp.json().get('files', [])
        if files:
            return files[0]['id']

    # Create folder
    create_body = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
    }
    if parent_id:
        create_body['parents'] = [parent_id]

    create_resp = requests.post(
        f"{GDRIVE_API_BASE}/files?fields=id,name",
        headers=headers,
        json=create_body,
        timeout=20,
    )

    if create_resp.status_code in (200, 201):
        return create_resp.json().get('id')

    raise ValueError(f"Could not create Google Drive folder '{folder_name}': {create_resp.text}")


def upload_file_to_gdrive(config, file_path, custom_filename=None):
    """
    Upload a local backup file to Google Drive using Google's Resumable Upload protocol.
    Streams large files directly without loading them entirely into memory.
    Places backups under: `VoidPanel Backups/<domain>/` (or custom folder).
    Returns: dict(status='success', file_id=..., filename=..., size=..., web_link=...)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Backup file not found at: {file_path}")

    filename = custom_filename or os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    access_token = get_gdrive_access_token(config)

    # 1. Resolve target folder in Google Drive
    target_folder_id = config.gdrive_folder_id.strip() if config.gdrive_folder_id else None

    if not target_folder_id:
        # Auto-create hierarchy: "VoidPanel Backups" -> "<domain>"
        root_folder_name = config.gdrive_folder_name.strip() or "VoidPanel Backups"
        root_folder_id = get_or_create_gdrive_folder(access_token, root_folder_name)
        domain_folder_id = get_or_create_gdrive_folder(access_token, config.domain, parent_id=root_folder_id)
        target_folder_id = domain_folder_id
    else:
        # Verify folder ID is accessible
        check_url = f"{GDRIVE_API_BASE}/files/{target_folder_id}?fields=id,name,trashed"
        ch_resp = requests.get(check_url, headers={'Authorization': f'Bearer {access_token}'}, timeout=15)
        if ch_resp.status_code != 200 or ch_resp.json().get('trashed'):
            # Fall back to auto-created hierarchy
            root_folder_name = config.gdrive_folder_name.strip() or "VoidPanel Backups"
            root_folder_id = get_or_create_gdrive_folder(access_token, root_folder_name)
            target_folder_id = get_or_create_gdrive_folder(access_token, config.domain, parent_id=root_folder_id)

    # 2. Initiate Resumable Upload Session
    init_headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Upload-Content-Type': 'application/zip',
        'X-Upload-Content-Length': str(file_size),
    }

    metadata = {
        'name': filename,
        'parents': [target_folder_id],
        'description': f"VoidPanel Automated Backup for {config.domain}",
    }

    init_url = f"{GDRIVE_UPLOAD_BASE}/files?uploadType=resumable"
    init_resp = requests.post(init_url, headers=init_headers, json=metadata, timeout=30)

    if init_resp.status_code != 200:
        raise ValueError(f"Failed to initiate Google Drive upload session: {init_resp.status_code} {init_resp.text}")

    upload_location = init_resp.headers.get('Location')
    if not upload_location:
        raise ValueError("Google Drive did not return an upload session Location URI.")

    # 3. Stream Upload File to Location URI
    logger.info("Starting Google Drive upload for %s (%d bytes) to %s", filename, file_size, config.domain)

    with open(file_path, 'rb') as f:
        put_headers = {
            'Content-Length': str(file_size),
            'Content-Type': 'application/zip',
        }
        # For typical backups (up to hundreds of MBs), streaming the file object directly
        # via requests handles transfer smoothly without buffering in RAM.
        put_resp = requests.put(upload_location, data=f, headers=put_headers, timeout=1800)

    if put_resp.status_code not in (200, 201):
        raise ValueError(f"Google Drive upload chunk failed ({put_resp.status_code}): {put_resp.text}")

    result_data = put_resp.json()
    file_id = result_data.get('id')
    web_link = result_data.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")

    logger.info("Google Drive upload completed successfully: file_id=%s filename=%s", file_id, filename)

    return {
        'status': 'success',
        'file_id': file_id,
        'filename': filename,
        'size_bytes': file_size,
        'folder_id': target_folder_id,
        'web_link': web_link,
        'message': f"Backup '{filename}' uploaded directly to Google Drive successfully!",
    }
