import secrets, os
from django.db import models
from django.contrib.auth.models import User


class DriveFolder(models.Model):
    """Google Drive Style Folder Hierarchy"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drive_folders')
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    color = models.CharField(max_length=30, default='#5F6368')  # Google Drive folder color palette
    is_starred = models.BooleanField(default=False)
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'color': self.color,
            'is_starred': self.is_starred,
            'is_trashed': self.is_trashed,
            'file_count': self.files.filter(is_trashed=False).count(),
            'created_at': self.created_at.strftime('%b %d, %Y') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%b %d, %Y, %I:%M %p') if self.updated_at else ''
        }

    def __str__(self):
        return f"📁 {self.name} ({self.user.username})"


class DriveFile(models.Model):
    """VoidDrive Sovereign Cloud Storage Files & Email Attachments"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drive_files', null=True, blank=True)
    folder = models.ForeignKey(DriveFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name='files')
    filename = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField(default=0)
    file_path = models.FileField(upload_to='voiddrive/%Y/%m/%d/', blank=True, null=True)
    share_token = models.CharField(max_length=64, unique=True, blank=True)
    is_public = models.BooleanField(default=False)
    share_role = models.CharField(max_length=20, default='viewer')  # 'viewer' or 'editor'
    shared_emails = models.TextField(blank=True, default='[]')
    is_starred = models.BooleanField(default=False)
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    password_protection = models.CharField(max_length=128, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = 'vd_' + secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Physically remove the file from server disk
        if self.file_path:
            try:
                if os.path.isfile(self.file_path.path):
                    os.remove(self.file_path.path)
            except Exception:
                pass
        super().delete(*args, **kwargs)

    @property
    def extension(self):
        return os.path.splitext(self.filename)[1].lower().replace('.', '')

    @property
    def category(self):
        ext = self.extension
        if ext in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'pages']:
            return 'document'
        elif ext in ['xls', 'xlsx', 'csv', 'ods', 'numbers', 'sheet']:
            return 'spreadsheet'
        elif ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico']:
            return 'image'
        elif ext in ['mp4', 'mov', 'avi', 'mkv', 'mp3', 'wav', 'ogg', 'aac', 'm4a']:
            return 'media'
        elif ext in ['zip', 'rar', 'tar', 'gz', '7z', 'bz2']:
            return 'archive'
        elif ext in ['py', 'js', 'ts', 'html', 'css', 'json', 'xml', 'sh', 'sql', 'md', 'yaml', 'yml']:
            return 'code'
        return 'other'

    @property
    def formatted_size(self):
        size = self.file_size_bytes
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'folder_id': self.folder_id,
            'folder_name': self.folder.name if self.folder else 'My Drive',
            'file_size_bytes': self.file_size_bytes,
            'formatted_size': self.formatted_size,
            'extension': self.extension,
            'category': self.category,
            'share_token': self.share_token,
            'is_public': self.is_public,
            'share_role': getattr(self, 'share_role', 'viewer') or 'viewer',
            'shared_emails': getattr(self, 'shared_emails', '[]') or '[]',
            'is_starred': self.is_starred,
            'is_trashed': self.is_trashed,
            'download_url': f"/drive/api/download/{self.id}/",
            'share_url': f"/drive/share/{self.share_token}/" if self.is_public else None,
            'created_at': self.created_at.strftime('%b %d, %Y') if self.created_at else '',
            'created_time': self.created_at.strftime('%b %d, %Y, %I:%M %p') if self.created_at else '',
            'owner': self.user.get_full_name() or self.user.username if self.user else 'Me'
        }

    def __str__(self):
        return f"{self.filename} ({self.formatted_size})"
