import os, uuid, json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.utils import timezone
from django.conf import settings
from .models import DriveFile, DriveFolder


def get_user_quota_info(user):
    """
    Computes storage quota details for an authenticated user:
    - quota_mb: from VirtualMailbox (default 5,120 MB / 5.0 GB)
    - used_bytes: sum of uploaded file sizes
    - free_bytes: remaining space
    - used_percent: float percentage
    """
    quota_mb = 5120  # Default 5 GB
    email_addr = getattr(user, 'email', '') or f"{user.username}@voidonyx.com"

    try:
        from apps.mail_engine.models import VirtualMailbox
        mb = VirtualMailbox.objects.filter(email__iexact=email_addr).first()
        if not mb:
            mb = VirtualMailbox.objects.filter(username__iexact=user.username).first()
        if mb and mb.quota_mb:
            quota_mb = mb.quota_mb
    except Exception:
        pass

    quota_bytes = quota_mb * 1024 * 1024
    # Calculate used bytes for non-permanently-deleted files
    used_bytes = DriveFile.objects.filter(user=user).aggregate(models.Sum('file_size_bytes'))['file_size_bytes__sum'] or 0
    free_bytes = max(0, quota_bytes - used_bytes)
    used_percent = min(100.0, round((used_bytes / quota_bytes) * 100, 1)) if quota_bytes > 0 else 0.0

    quota_formatted = f"{quota_mb / 1024:.1f} GB" if quota_mb >= 1024 else f"{quota_mb} MB"
    
    if used_bytes < 1024 * 1024:
        used_formatted = f"{used_bytes / 1024:.1f} KB"
    elif used_bytes < 1024 * 1024 * 1024:
        used_formatted = f"{used_bytes / (1024 * 1024):.1f} MB"
    else:
        used_formatted = f"{used_bytes / (1024 * 1024 * 1024):.2f} GB"

    if free_bytes < 1024 * 1024:
        free_formatted = f"{free_bytes / 1024:.1f} KB"
    elif free_bytes < 1024 * 1024 * 1024:
        free_formatted = f"{free_bytes / (1024 * 1024):.1f} MB"
    else:
        free_formatted = f"{free_bytes / (1024 * 1024 * 1024):.2f} GB"

    return {
        'quota_mb': quota_mb,
        'quota_bytes': quota_bytes,
        'used_bytes': used_bytes,
        'free_bytes': free_bytes,
        'used_percent': used_percent,
        'quota_formatted': quota_formatted,
        'used_formatted': used_formatted,
        'free_formatted': free_formatted,
        'is_exceeded': used_bytes >= quota_bytes
    }


def get_drive_files_api(request):
    """
    Google Drive-style hierarchical view:
    Returns folders, files, breadcrumbs, recent suggested files, and quota stats.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    quota = get_user_quota_info(request.user)
    view_type = request.GET.get('view', 'my_drive').lower()  # 'my_drive', 'recent', 'starred', 'trash'
    raw_folder_id = request.GET.get('folder_id')
    folder_id = int(raw_folder_id) if raw_folder_id and raw_folder_id != 'null' and raw_folder_id.isdigit() else None

    current_folder = None
    breadcrumbs = [{'id': None, 'name': 'My Drive'}]

    if folder_id:
        current_folder_obj = DriveFolder.objects.filter(id=folder_id, user=request.user).first()
        if current_folder_obj:
            current_folder = current_folder_obj.to_dict()
            # Build breadcrumb trail upwards to root
            trail = []
            curr = current_folder_obj
            while curr:
                trail.append({'id': curr.id, 'name': curr.name})
                curr = curr.parent
            trail.reverse()
            breadcrumbs.extend(trail)

    # Base querysets
    folders_qs = DriveFolder.objects.filter(user=request.user)
    files_qs = DriveFile.objects.filter(user=request.user)

    if view_type == 'trash':
        folders_qs = folders_qs.filter(is_trashed=True)
        files_qs = files_qs.filter(is_trashed=True)
    elif view_type == 'starred':
        folders_qs = folders_qs.filter(is_starred=True, is_trashed=False)
        files_qs = files_qs.filter(is_starred=True, is_trashed=False)
    elif view_type == 'recent':
        folders_qs = folders_qs.none()
        files_qs = files_qs.filter(is_trashed=False)
    else:
        # Standard My Drive folder navigation
        folders_qs = folders_qs.filter(is_trashed=False, parent_id=folder_id)
        files_qs = files_qs.filter(is_trashed=False, folder_id=folder_id)

    # Search filter
    q = request.GET.get('q', '').strip().lower()
    if q:
        folders_qs = folders_qs.filter(name__icontains=q)
        files_qs = files_qs.filter(filename__icontains=q)

    # Category filter
    cat = request.GET.get('category', '').strip().lower()
    files_list = []
    ordered_files = files_qs.order_by('-created_at')
    if view_type == 'recent':
        ordered_files = ordered_files[:50]

    for f in ordered_files:
        if cat and cat != 'all':
            if f.category != cat:
                continue
        files_list.append(f.to_dict())

    folders_list = [f.to_dict() for f in folders_qs.order_by('name')]

    # Suggested / Recent Shelf (Top 4 recently uploaded active files)
    suggested_files = [f.to_dict() for f in DriveFile.objects.filter(user=request.user, is_trashed=False).order_by('-created_at')[:4]]

    counts = {
        'total_files': DriveFile.objects.filter(user=request.user, is_trashed=False).count(),
        'total_folders': DriveFolder.objects.filter(user=request.user, is_trashed=False).count(),
        'starred_count': DriveFile.objects.filter(user=request.user, is_starred=True, is_trashed=False).count() + DriveFolder.objects.filter(user=request.user, is_starred=True, is_trashed=False).count(),
        'trash_count': DriveFile.objects.filter(user=request.user, is_trashed=True).count() + DriveFolder.objects.filter(user=request.user, is_trashed=True).count(),
    }

    return JsonResponse({
        'status': 'success',
        'view': view_type,
        'current_folder': current_folder,
        'breadcrumbs': breadcrumbs,
        'folders': folders_list,
        'files': files_list,
        'suggested_files': suggested_files if view_type == 'my_drive' and not folder_id and not q else [],
        'quota': quota,
        'counts': counts
    })


@csrf_exempt
def create_folder_api(request):
    """Create a new Google Drive folder with optional parent and color"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    name = (data.get('name') or '').strip() or 'Untitled Folder'
    raw_parent_id = data.get('parent_id')
    parent_id = int(raw_parent_id) if raw_parent_id and str(raw_parent_id).isdigit() else None
    color = data.get('color', '#5F6368')

    folder = DriveFolder.objects.create(
        user=request.user,
        name=name,
        parent_id=parent_id,
        color=color
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Created folder '{folder.name}'",
        'folder': folder.to_dict()
    })


@csrf_exempt
def upload_drive_file_api(request):
    """
    Upload one or multiple files into current folder,
    strictly verifying storage quota before saving to disk.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    files = request.FILES.getlist('files')
    if not files and 'file' in request.FILES:
        files = [request.FILES['file']]

    if not files:
        return JsonResponse({'status': 'error', 'message': 'No files uploaded'}, status=400)

    raw_folder_id = request.POST.get('folder_id')
    folder_id = int(raw_folder_id) if raw_folder_id and str(raw_folder_id).isdigit() else None

    quota = get_user_quota_info(request.user)
    incoming_total_bytes = sum(f.size for f in files)

    if quota['used_bytes'] + incoming_total_bytes > quota['quota_bytes']:
        overflow_mb = round((quota['used_bytes'] + incoming_total_bytes - quota['quota_bytes']) / (1024 * 1024), 1)
        return JsonResponse({
            'status': 'error',
            'code': 'QUOTA_EXCEEDED',
            'message': f"Storage quota exceeded! Uploading {round(incoming_total_bytes / (1024 * 1024), 1)} MB would exceed your {quota['quota_formatted']} limit by {overflow_mb} MB. Please free up space or delete old files.",
            'quota': quota
        }, status=400)

    uploaded_records = []
    for uploaded in files:
        drive_file = DriveFile(
            user=request.user,
            folder_id=folder_id,
            filename=uploaded.name,
            file_size_bytes=uploaded.size,
            file_path=uploaded,
            is_public=False
        )
        drive_file.save()
        uploaded_records.append(drive_file.to_dict())

    updated_quota = get_user_quota_info(request.user)

    return JsonResponse({
        'status': 'success',
        'message': f"Successfully uploaded {len(uploaded_records)} file(s)",
        'uploaded': uploaded_records,
        'quota': updated_quota
    })


@csrf_exempt
def rename_item_api(request):
    """Rename a file or folder"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    item_type = data.get('type')  # 'folder' or 'file'
    item_id = data.get('id')
    new_name = (data.get('name') or '').strip()

    if not item_id or not new_name:
        return JsonResponse({'status': 'error', 'message': 'Item ID and name required'}, status=400)

    if item_type == 'folder':
        folder = get_object_or_404(DriveFolder, id=item_id, user=request.user)
        folder.name = new_name
        folder.save(update_fields=['name', 'updated_at'])
        return JsonResponse({'status': 'success', 'folder': folder.to_dict()})
    else:
        f = get_object_or_404(DriveFile, id=item_id, user=request.user)
        f.filename = new_name
        f.save(update_fields=['filename'])
        return JsonResponse({'status': 'success', 'file': f.to_dict()})


@csrf_exempt
def toggle_star_api(request):
    """Toggle starred status for file or folder"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    item_type = data.get('type')
    item_id = data.get('id')

    if item_type == 'folder':
        folder = get_object_or_404(DriveFolder, id=item_id, user=request.user)
        folder.is_starred = not folder.is_starred
        folder.save(update_fields=['is_starred', 'updated_at'])
        return JsonResponse({'status': 'success', 'is_starred': folder.is_starred})
    else:
        f = get_object_or_404(DriveFile, id=item_id, user=request.user)
        f.is_starred = not f.is_starred
        f.save(update_fields=['is_starred'])
        return JsonResponse({'status': 'success', 'is_starred': f.is_starred})


@csrf_exempt
def update_folder_color_api(request):
    """Change folder color palette"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    folder_id = data.get('folder_id')
    color = data.get('color', '#5F6368')

    folder = get_object_or_404(DriveFolder, id=folder_id, user=request.user)
    folder.color = color
    folder.save(update_fields=['color', 'updated_at'])

    return JsonResponse({'status': 'success', 'folder': folder.to_dict()})


@csrf_exempt
def trash_item_api(request):
    """Soft-delete file(s) or folder(s) to Trash"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    file_ids = data.get('file_ids') or ([data.get('file_id')] if data.get('file_id') else [])
    folder_ids = data.get('folder_ids') or ([data.get('folder_id')] if data.get('folder_id') else [])

    now = timezone.now()
    if file_ids:
        DriveFile.objects.filter(id__in=file_ids, user=request.user).update(is_trashed=True, trashed_at=now)
    if folder_ids:
        DriveFolder.objects.filter(id__in=folder_ids, user=request.user).update(is_trashed=True, trashed_at=now)

    return JsonResponse({'status': 'success', 'message': 'Moved to Trash'})


@csrf_exempt
def restore_item_api(request):
    """Restore file(s) or folder(s) from Trash"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    file_ids = data.get('file_ids') or ([data.get('file_id')] if data.get('file_id') else [])
    folder_ids = data.get('folder_ids') or ([data.get('folder_id')] if data.get('folder_id') else [])

    if file_ids:
        DriveFile.objects.filter(id__in=file_ids, user=request.user).update(is_trashed=False, trashed_at=None)
    if folder_ids:
        DriveFolder.objects.filter(id__in=folder_ids, user=request.user).update(is_trashed=False, trashed_at=None)

    return JsonResponse({'status': 'success', 'message': 'Restored from Trash'})


@csrf_exempt
def permanent_delete_api(request):
    """Permanently delete specific file(s) or folder(s) from server disk and database"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    file_ids = data.get('file_ids') or ([data.get('file_id')] if data.get('file_id') else [])
    folder_ids = data.get('folder_ids') or ([data.get('folder_id')] if data.get('folder_id') else [])

    count = 0
    if file_ids:
        files = DriveFile.objects.filter(id__in=file_ids)
        if not request.user.is_superuser:
            files = files.filter(models.Q(user=request.user) | models.Q(user__isnull=True))
        for f in files:
            f.delete()  # Automatically removes file from disk via DriveFile.delete()
            count += 1

    if folder_ids:
        folders = DriveFolder.objects.filter(id__in=folder_ids)
        if not request.user.is_superuser:
            folders = folders.filter(models.Q(user=request.user) | models.Q(user__isnull=True))
        for fol in folders:
            for f in fol.files.all():
                f.delete()
            fol.delete()
            count += 1

    updated_quota = get_user_quota_info(request.user)

    return JsonResponse({
        'status': 'success',
        'message': f"Permanently deleted {count} item(s)",
        'count': count,
        'quota': updated_quota
    })


@csrf_exempt
def empty_trash_api(request):
    """Permanently delete all trashed files and folders from server disk and database"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    trashed_files = DriveFile.objects.filter(is_trashed=True)
    if not request.user.is_superuser:
        trashed_files = trashed_files.filter(models.Q(user=request.user) | models.Q(user__isnull=True))
    count = trashed_files.count()
    for f in trashed_files:
        f.delete()  # Physically removes from disk and DB

    trashed_folders = DriveFolder.objects.filter(is_trashed=True)
    if not request.user.is_superuser:
        trashed_folders = trashed_folders.filter(models.Q(user=request.user) | models.Q(user__isnull=True))
    for fol in trashed_folders:
        for f in fol.files.all():
            f.delete()
        fol.delete()

    updated_quota = get_user_quota_info(request.user)

    return JsonResponse({
        'status': 'success',
        'message': f"Permanently deleted {count} file(s)",
        'count': count,
        'quota': updated_quota
    })


@csrf_exempt
def delete_drive_file_api(request):
    """Immediate permanent delete endpoint"""
    return permanent_delete_api(request)


def download_drive_file_api(request, file_id):
    """Secure authenticated download or inline preview"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    drive_file = get_object_or_404(DriveFile, id=file_id, user=request.user)
    if not drive_file.file_path or not os.path.exists(drive_file.file_path.path):
        raise Http404("File not found on storage disk.")

    inline = request.GET.get('inline') == '1'
    ext = (drive_file.extension or '').lower().replace('.', '')

    content_type = 'application/octet-stream'
    if ext == 'pdf':
        content_type = 'application/pdf'
    elif ext in ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg']:
        content_type = f'image/{ext if ext != "svg" else "svg+xml"}'
    elif ext in ['txt', 'log', 'md', 'csv', 'json', 'py', 'js', 'html', 'css', 'xml']:
        content_type = 'text/plain; charset=utf-8'

    response = FileResponse(
        open(drive_file.file_path.path, 'rb'),
        as_attachment=not inline,
        filename=drive_file.filename,
        content_type=content_type
    )
    if inline:
        response['Content-Disposition'] = f'inline; filename="{drive_file.filename}"'
    return response


def get_file_content_api(request, file_id):
    """Read text/document or spreadsheet data for the in-browser editor"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    drive_file = get_object_or_404(DriveFile, id=file_id, user=request.user)
    if not drive_file.file_path or not os.path.exists(drive_file.file_path.path):
        return JsonResponse({'status': 'error', 'message': 'File not found'}, status=404)

    ext = (drive_file.extension or '').lower().replace('.', '')

    try:
        with open(drive_file.file_path.path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Cannot read file: {str(e)}'}, status=500)

    return JsonResponse({
        'status': 'success',
        'file_id': drive_file.id,
        'filename': drive_file.filename,
        'extension': ext,
        'category': drive_file.category,
        'content': content
    })


@csrf_exempt
def save_file_content_api(request):
    """Save edited Google Docs text or Google Sheets CSV data"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    file_id = data.get('file_id')
    new_content = data.get('content', '')

    drive_file = get_object_or_404(DriveFile, id=file_id, user=request.user)
    raw_bytes = new_content.encode('utf-8')
    new_size = len(raw_bytes)

    # Check storage quota
    quota = get_user_quota_info(request.user)
    diff = new_size - drive_file.file_size_bytes
    if diff > 0 and (quota['used_bytes'] + diff) > quota['quota_bytes']:
        return JsonResponse({
            'status': 'error',
            'code': 'QUOTA_EXCEEDED',
            'message': 'Cannot save: Storage quota exceeded.'
        }, status=400)

    if not drive_file.file_path or not os.path.exists(drive_file.file_path.path):
        from django.core.files.base import ContentFile
        drive_file.file_path.save(drive_file.filename, ContentFile(raw_bytes), save=False)
    else:
        with open(drive_file.file_path.path, 'wb') as f:
            f.write(raw_bytes)

    drive_file.file_size_bytes = new_size
    drive_file.save(update_fields=['file_size_bytes'])

    return JsonResponse({
        'status': 'success',
        'message': 'Saved successfully',
        'file': drive_file.to_dict()
    })


@csrf_exempt
def create_doc_or_sheet_api(request):
    """Create a new Google Doc or Google Spreadsheet in Drive"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    item_type = data.get('type', 'doc')  # 'doc' or 'sheet'
    folder_id = data.get('folder_id')

    folder = None
    if folder_id:
        folder = DriveFolder.objects.filter(id=folder_id, user=request.user).first()

    from django.core.files.base import ContentFile
    if item_type == 'sheet':
        base_name = "Untitled spreadsheet"
        ext = ".sheet"
        initial_content = json.dumps({
            "version": "2.0",
            "sheets": [
                {
                    "name": "Sheet1",
                    "cells": {},
                    "colWidths": {},
                    "rowCount": 50,
                    "colCount": 26
                }
            ],
            "activeSheetIndex": 0
        }, indent=2)
    else:
        base_name = "Untitled document"
        ext = ".doc"
        initial_content = "<h2>Untitled document</h2><p>Start typing your document here...</p>"

    # Ensure unique filename
    existing_count = DriveFile.objects.filter(user=request.user, folder=folder, filename__startswith=base_name).count()
    filename = f"{base_name}{ext}" if existing_count == 0 else f"{base_name} ({existing_count + 1}){ext}"

    content_bytes = initial_content.encode('utf-8')
    drive_file = DriveFile(
        user=request.user,
        folder=folder,
        filename=filename,
        file_size_bytes=len(content_bytes)
    )
    drive_file.file_path.save(filename, ContentFile(content_bytes), save=False)
    drive_file.save()

    return JsonResponse({
        'status': 'success',
        'message': f"Created {filename}",
        'file': drive_file.to_dict()
    })



@csrf_exempt
def toggle_share_link_api(request):
    """Toggle public/private status for a drive file (backward compatibility)"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    file_id = data.get('file_id')
    drive_file = get_object_or_404(DriveFile, id=file_id, user=request.user)

    drive_file.is_public = not drive_file.is_public
    drive_file.save(update_fields=['is_public'])

    host = request.get_host()
    proto = 'https' if request.is_secure() else 'http'
    share_url = f"{proto}://{host}/drive/share/{drive_file.share_token}/" if drive_file.is_public else None

    return JsonResponse({
        'status': 'success',
        'is_public': drive_file.is_public,
        'share_url': share_url,
        'share_token': drive_file.share_token
    })


@csrf_exempt
def get_file_share_info_api(request, file_id):
    """Retrieve full sharing details for Google Drive Share Modal"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    drive_file = get_object_or_404(DriveFile, id=file_id, user=request.user)

    host = request.get_host()
    proto = 'https' if request.is_secure() else 'http'
    share_url = f"{proto}://{host}/drive/share/{drive_file.share_token}/"

    try:
        shared_list = json.loads(drive_file.shared_emails or '[]')
    except Exception:
        shared_list = []

    owner_name = drive_file.user.get_full_name() or drive_file.user.username
    owner_email = drive_file.user.email or f"{drive_file.user.username}@voidonyx.com"

    return JsonResponse({
        'status': 'success',
        'file_id': drive_file.id,
        'filename': drive_file.filename,
        'clean_title': os.path.splitext(drive_file.filename)[0],
        'extension': drive_file.extension,
        'category': drive_file.category,
        'is_public': drive_file.is_public,
        'general_access': 'anyone_with_link' if drive_file.is_public else 'restricted',
        'share_role': getattr(drive_file, 'share_role', 'viewer') or 'viewer',
        'share_url': share_url,
        'owner': {
            'name': owner_name,
            'email': owner_email,
            'is_me': True
        },
        'shared_users': shared_list
    })


@csrf_exempt
def update_share_access_api(request):
    """
    Update general access (restricted vs anyone_with_link),
    default share role (viewer vs editor), or add/remove collaborators.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    file_id = data.get('file_id')
    drive_file = get_object_or_404(DriveFile, id=file_id, user=request.user)

    if 'general_access' in data:
        gen = data.get('general_access')
        drive_file.is_public = (gen == 'anyone_with_link')

    if 'share_role' in data:
        role = data.get('share_role')
        if role in ['viewer', 'editor', 'commenter']:
            drive_file.share_role = role

    try:
        shared_list = json.loads(drive_file.shared_emails or '[]')
    except Exception:
        shared_list = []

    # Add collaborator
    invite_email = (data.get('invite_email') or '').strip().lower()
    invite_role = data.get('invite_role', 'viewer')
    if invite_email:
        existing = next((u for u in shared_list if u.get('email') == invite_email), None)
        if existing:
            existing['role'] = invite_role
        else:
            shared_list.append({
                'email': invite_email,
                'role': invite_role,
                'added_at': timezone.now().strftime('%b %d, %Y')
            })
        drive_file.shared_emails = json.dumps(shared_list)

    # Remove collaborator
    remove_email = (data.get('remove_email') or '').strip().lower()
    if remove_email:
        shared_list = [u for u in shared_list if u.get('email') != remove_email]
        drive_file.shared_emails = json.dumps(shared_list)

    drive_file.save()

    host = request.get_host()
    proto = 'https' if request.is_secure() else 'http'
    share_url = f"{proto}://{host}/drive/share/{drive_file.share_token}/"

    return JsonResponse({
        'status': 'success',
        'message': 'Share settings updated successfully',
        'file_id': drive_file.id,
        'is_public': drive_file.is_public,
        'general_access': 'anyone_with_link' if drive_file.is_public else 'restricted',
        'share_role': drive_file.share_role,
        'share_url': share_url,
        'shared_users': shared_list
    })


@csrf_exempt
def public_save_file_content_api(request, token):
    """Allow authorized editors via share link to save changes directly"""
    drive_file = get_object_or_404(DriveFile, share_token=token)

    can_edit = False
    if drive_file.is_public and getattr(drive_file, 'share_role', 'viewer') == 'editor':
        can_edit = True
    elif request.user.is_authenticated:
        if request.user == drive_file.user:
            can_edit = True
        else:
            try:
                shared_list = json.loads(drive_file.shared_emails or '[]')
                user_email = (request.user.email or '').lower()
                user_entry = next((u for u in shared_list if u.get('email', '').lower() == user_email), None)
                if user_entry and user_entry.get('role') == 'editor':
                    can_edit = True
            except Exception:
                pass

    if not can_edit:
        return JsonResponse({'status': 'error', 'message': 'You only have view access. Editing is restricted.'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    new_content = data.get('content', '')
    raw_bytes = new_content.encode('utf-8')

    if not drive_file.file_path or not os.path.exists(drive_file.file_path.path):
        from django.core.files.base import ContentFile
        drive_file.file_path.save(drive_file.filename, ContentFile(raw_bytes), save=False)
    else:
        with open(drive_file.file_path.path, 'wb') as f:
            f.write(raw_bytes)

    drive_file.file_size_bytes = len(raw_bytes)
    drive_file.save(update_fields=['file_size_bytes'])

    return JsonResponse({
        'status': 'success',
        'message': 'Changes saved successfully',
        'file_size': drive_file.formatted_size
    })


def share_file_view(request, token):
    """
    Public luxury view for shared files & documents,
    replicating Google Drive's permissions (View vs Edit) and access control.
    """
    drive_file = get_object_or_404(DriveFile, share_token=token)

    # 1. Direct Download Request (?download=1)
    if request.GET.get('download') == '1':
        if not drive_file.file_path or not os.path.exists(drive_file.file_path.path):
            raise Http404("File not found on storage server.")
        return FileResponse(open(drive_file.file_path.path, 'rb'), as_attachment=True, filename=drive_file.filename)

    # 2. Check Access Permissions
    has_access = False
    effective_role = 'viewer'

    if drive_file.is_public:
        has_access = True
        effective_role = getattr(drive_file, 'share_role', 'viewer') or 'viewer'
    elif request.user.is_authenticated:
        if request.user == drive_file.user:
            has_access = True
            effective_role = 'editor'
        else:
            try:
                shared_list = json.loads(drive_file.shared_emails or '[]')
                user_email = (request.user.email or f"{request.user.username}@voidonyx.com").lower()
                user_entry = next((u for u in shared_list if u.get('email', '').lower() == user_email), None)
                if user_entry:
                    has_access = True
                    effective_role = user_entry.get('role', 'viewer')
            except Exception:
                pass

    # 3. If Access Denied (Restricted link and user unauthorized)
    if not has_access:
        user_info = f"Signed in as <b>{request.user.email or request.user.username}</b>" if request.user.is_authenticated else "You are not signed in"
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Access Denied — VoidDrive</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #F8FAFC; color: #1E293B; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
    .card {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px; max-width: 480px; width: 100%; padding: 36px 32px; text-align: center; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.08); }}
    .icon {{ width: 64px; height: 64px; border-radius: 16px; background: #FEF2F2; color: #DC2626; display: inline-flex; align-items: center; justify-content: center; font-size: 28px; margin-bottom: 20px; }}
    h2 {{ font-size: 22px; font-weight: 800; margin: 0 0 10px 0; color: #0F172A; }}
    p {{ color: #64748B; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0; }}
    .btn {{ display: inline-block; background: #0B57D0; color: #FFFFFF; text-decoration: none; font-weight: 700; font-size: 14px; padding: 10px 24px; border-radius: 20px; transition: background 0.15s; }}
    .btn:hover {{ background: #0842A0; }}
    .footer {{ margin-top: 24px; font-size: 12px; color: #94A3B8; border-top: 1px solid #F1F5F9; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon"><i class="fa-solid fa-lock"></i></div>
    <h2>You need access</h2>
    <p>This item is restricted. Ask the owner for access, or switch to an account with permission.<br><br><span style="font-size: 13px; color: #475569;">{user_info}</span></p>
    <a href="/login/" class="btn">Sign in to another account</a>
    <div class="footer">VoidDrive Sovereign Cloud Storage</div>
  </div>
</body>
</html>"""
        return HttpResponse(html, status=403)

    # 4. Access Granted - Prepare Display
    ext = drive_file.extension
    is_editor = (effective_role == 'editor')
    role_badge = f'<span style="background: #DEF7EC; color: #03543F; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 12px; display: inline-flex; align-items: center; gap: 5px;"><i class="fa-solid fa-pen-to-square"></i> Editor</span>' if is_editor else f'<span style="background: #E1EFFE; color: #1E429F; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 12px; display: inline-flex; align-items: center; gap: 5px;"><i class="fa-solid fa-eye"></i> View only</span>'

    # Read content for editable/viewable docs
    raw_content = ""
    if ext in ['doc', 'docx', 'txt', 'md', 'html', 'csv']:
        if drive_file.file_path and os.path.exists(drive_file.file_path.path):
            try:
                with open(drive_file.file_path.path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_content = f.read()
            except Exception:
                raw_content = ""

    # Document (Docs) View / Edit
    if ext in ['doc', 'docx', 'txt', 'md']:
        editable_attr = 'contenteditable="true"' if is_editor else 'contenteditable="false"'
        save_btn_html = f'''<button id="btn-save-shared" type="button" onclick="saveSharedDoc()" style="background: #0B57D0; color: #FFFFFF; border: none; padding: 7px 18px; font-size: 13px; border-radius: 20px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
          <i class="fa-solid fa-cloud-arrow-up"></i> <span>Save</span>
        </button>''' if is_editor else ''

        save_script = f'''
        let isSaving = false;
        function saveSharedDoc() {{
          if (isSaving) return;
          const editor = document.getElementById('shared-doc-canvas');
          const status = document.getElementById('shared-doc-status');
          if (!editor) return;

          isSaving = true;
          if (status) status.innerText = 'Saving changes...';

          fetch('/drive/api/public-save/{token}/', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ content: editor.innerHTML }})
          }})
          .then(r => r.json())
          .then(data => {{
            isSaving = false;
            if (data.status === 'success') {{
              if (status) status.innerText = 'Saved to Docs • Just now';
            }} else {{
              if (status) status.innerText = data.message || 'Error saving';
            }}
          }})
          .catch(err => {{
            isSaving = false;
            if (status) status.innerText = 'Save failed';
          }});
        }}

        // Auto-save debounced if editor
        let autoSaveTimer = null;
        document.addEventListener('DOMContentLoaded', () => {{
          const editor = document.getElementById('shared-doc-canvas');
          if (editor && {str(is_editor).lower()}) {{
            editor.addEventListener('input', () => {{
              const status = document.getElementById('shared-doc-status');
              if (status) status.innerText = 'Saving changes...';
              clearTimeout(autoSaveTimer);
              autoSaveTimer = setTimeout(saveSharedDoc, 1500);
            }});
          }}
        }});
        ''' if is_editor else ''

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{drive_file.filename} — VoidDrive Docs</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{ font-family: Arial, sans-serif; background: #F8F9FA; margin: 0; padding: 0; color: #1F1F1F; display: flex; flex-direction: column; min-height: 100vh; }}
    .topbar {{ height: 56px; background: #FFFFFF; border-bottom: 1px solid #DADCE0; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; position: sticky; top: 0; z-index: 100; }}
    .paper-container {{ flex: 1; overflow-y: auto; padding: 32px 16px; display: flex; justify-content: center; }}
    .paper {{ background: #FFFFFF; width: 816px; min-height: 1056px; padding: 72px 96px; box-shadow: 0 1px 3px 1px rgba(60,64,67,0.15); border-radius: 2px; outline: none; line-height: 1.6; font-size: 14px; box-sizing: border-box; }}
    .paper h1 {{ font-size: 28px; font-weight: 800; margin: 0 0 16px 0; }}
    .paper h2 {{ font-size: 22px; font-weight: 700; margin: 20px 0 10px 0; }}
    .paper p {{ margin: 0 0 12px 0; }}
    .paper table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    .paper th, .paper td {{ border: 1px solid #CBD5E1; padding: 8px 12px; }}
    .paper th {{ background: #F8FAFC; }}
    .action-btn {{ text-decoration: none; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 13px; font-weight: 600; color: #444746; padding: 7px 14px; border-radius: 20px; display: inline-flex; align-items: center; gap: 6px; border: 1px solid #DADCE0; background: #FFFFFF; transition: all 0.15s; }}
    .action-btn:hover {{ background: #F1F3F4; }}
  </style>
</head>
<body>
  <div class="topbar">
    <div style="display: flex; align-items: center; gap: 12px;">
      <i class="fa-solid fa-file-lines" style="color: #4285F4; font-size: 24px;"></i>
      <div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-weight: 700; font-size: 15px; color: #1F1F1F;">{os.path.splitext(drive_file.filename)[0]}</span>
          {role_badge}
        </div>
        <div id="shared-doc-status" style="font-size: 11px; color: #5F6368; font-family: 'Plus Jakarta Sans', sans-serif;">{'Shared Docs Canvas' if not is_editor else 'Ready to edit'}</div>
      </div>
    </div>
    <div style="display: flex; align-items: center; gap: 8px;">
      {save_btn_html}
      <a href="javascript:window.print()" class="action-btn" title="Print document"><i class="fa-solid fa-print"></i> Print</a>
      <a href="?download=1" class="action-btn" title="Download file"><i class="fa-solid fa-download"></i> Download</a>
    </div>
  </div>

  <div class="paper-container">
    <div id="shared-doc-canvas" class="paper" {editable_attr} spellcheck="true">
      {raw_content if raw_content.strip() else '<p>Start typing your document...</p>'}
    </div>
  </div>

  <script>
    {save_script}
  </script>
</body>
</html>"""
        return HttpResponse(html)

    # Spreadsheet (Sheets) View
    elif ext in ['csv', 'xls', 'xlsx']:
        rows = []
        for line in raw_content.splitlines():
            if line.strip():
                rows.append([c.strip(' "') for c in line.split(',')])

        table_rows_html = ""
        for r_idx, row in enumerate(rows):
            cells = "".join([f"<td style='border: 1px solid #CBD5E1; padding: 6px 12px;'>{cell}</td>" for cell in row])
            table_rows_html += f"<tr><th style='background:#F8FAFC; border:1px solid #CBD5E1; width:40px; text-align:center; color:#64748B;'>{r_idx+1}</th>{cells}</tr>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{drive_file.filename} — VoidDrive Sheets</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #F8FAFC; margin: 0; }}
    .topbar {{ height: 56px; background: #FFFFFF; border-bottom: 1px solid #E2E8F0; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }}
    table {{ border-collapse: collapse; width: 100%; background: #FFFFFF; font-size: 13px; font-family: Arial, sans-serif; }}
  </style>
</head>
<body>
  <div class="topbar">
    <div style="display: flex; align-items: center; gap: 12px;">
      <i class="fa-solid fa-file-excel" style="color: #0F9D58; font-size: 24px;"></i>
      <div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-weight: 700; font-size: 15px;">{drive_file.filename}</span>
          {role_badge}
        </div>
      </div>
    </div>
    <a href="?download=1" style="text-decoration: none; font-size: 13px; font-weight: 600; color: #0F9D58; padding: 7px 16px; border: 1px solid #A8DAB5; border-radius: 20px; background: #E6F4EA;">
      <i class="fa-solid fa-download"></i> Download CSV
    </a>
  </div>
  <div style="overflow: auto; padding: 20px;">
    <table>{table_rows_html}</table>
  </div>
</body>
</html>"""
        return HttpResponse(html)

    # Image View
    elif ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{drive_file.filename} — VoidDrive Preview</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{ margin: 0; background: #0F172A; min-height: 100vh; display: flex; flex-direction: column; font-family: 'Plus Jakarta Sans', sans-serif; }}
    .topbar {{ height: 56px; background: rgba(15,23,42,0.9); border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; color: #FFFFFF; }}
  </style>
</head>
<body>
  <div class="topbar">
    <span style="font-weight: 700; font-size: 15px;">{drive_file.filename} ({drive_file.formatted_size})</span>
    <a href="?download=1" style="color: #FFFFFF; text-decoration: none; font-size: 13px; background: #4F46E5; padding: 6px 16px; border-radius: 20px;"><i class="fa-solid fa-download"></i> Download</a>
  </div>
  <div style="flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px;">
    <img src="?download=1" style="max-width: 90vw; max-height: 80vh; border-radius: 8px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);">
  </div>
</body>
</html>"""
        return HttpResponse(html)

    # General File Download Card
    else:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{drive_file.filename} — VoidDrive Shared File</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: radial-gradient(circle at 50% 0%, #1E1B4B, #0F172A 80%); color: #F8FAFC; min-height: 100vh; margin: 0; display: flex; align-items: center; justify-content: center; padding: 24px; }}
    .card {{ background: rgba(30, 41, 59, 0.85); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 24px; padding: 40px; max-width: 500px; width: 100%; text-align: center; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6); }}
    .icon-box {{ width: 72px; height: 72px; border-radius: 20px; background: linear-gradient(135deg, #4F46E5, #9333EA); color: #FFFFFF; display: inline-flex; align-items: center; justify-content: center; font-size: 28px; margin-bottom: 20px; }}
    .btn {{ display: inline-flex; align-items: center; gap: 10px; background: linear-gradient(135deg, #FF5C00, #EA580C); color: #FFFFFF; text-decoration: none; font-weight: 700; font-size: 15px; padding: 14px 32px; border-radius: 12px; margin-top: 24px; transition: all 0.2s ease; }}
    .btn:hover {{ transform: translateY(-2px); }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon-box"><i class="fa-solid fa-cloud-arrow-down"></i></div>
    <div style="font-size: 11px; font-weight: 800; color: #818CF8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">VoidDrive Sovereign Share</div>
    <h2 style="font-size: 20px; font-weight: 700; margin: 0 0 8px 0; word-break: break-all;">{drive_file.filename}</h2>
    <p style="color: #94A3B8; font-size: 14px; margin: 0 0 20px 0;">{drive_file.formatted_size} • {role_badge}</p>
    <a href="?download=1" class="btn"><i class="fa-solid fa-download"></i> Download File</a>
  </div>
</body>
</html>"""
        return HttpResponse(html)
