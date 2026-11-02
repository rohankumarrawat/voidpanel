class DriveFolder {
  final int id;
  final String name;
  final int? parentId;
  final String color;
  final bool isStarred;
  final bool isTrashed;
  final int fileCount;
  final String createdAt;
  final String updatedAt;

  const DriveFolder({
    required this.id,
    required this.name,
    this.parentId,
    this.color = '#5F6368',
    this.isStarred = false,
    this.isTrashed = false,
    this.fileCount = 0,
    this.createdAt = '',
    this.updatedAt = '',
  });

  factory DriveFolder.fromJson(Map<String, dynamic> json) {
    return DriveFolder(
      id: json['id'] is int ? json['id'] : int.tryParse('${json['id']}') ?? 0,
      name: json['name'] ?? 'Untitled Folder',
      parentId: json['parent_id'] != null ? (json['parent_id'] is int ? json['parent_id'] : int.tryParse('${json['parent_id']}')) : null,
      color: json['color'] ?? '#5F6368',
      isStarred: json['is_starred'] == true,
      isTrashed: json['is_trashed'] == true,
      fileCount: json['file_count'] is int ? json['file_count'] : int.tryParse('${json['file_count']}') ?? 0,
      createdAt: json['created_at'] ?? '',
      updatedAt: json['updated_at'] ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'parent_id': parentId,
    'color': color,
    'is_starred': isStarred,
    'is_trashed': isTrashed,
    'file_count': fileCount,
    'created_at': createdAt,
    'updated_at': updatedAt,
  };
}

class DriveFile {
  final int id;
  final String filename;
  final int? folderId;
  final String folderName;
  final int fileSizeBytes;
  final String formattedSize;
  final String extension;
  final String category;
  final String shareToken;
  final bool isPublic;
  final String shareRole;
  final bool isStarred;
  final bool isTrashed;
  final String downloadUrl;
  final String? shareUrl;
  final String createdAt;
  final String createdTime;
  final String owner;

  const DriveFile({
    required this.id,
    required this.filename,
    this.folderId,
    this.folderName = 'My Drive',
    this.fileSizeBytes = 0,
    this.formattedSize = '0 B',
    this.extension = '',
    this.category = 'other',
    this.shareToken = '',
    this.isPublic = false,
    this.shareRole = 'viewer',
    this.isStarred = false,
    this.isTrashed = false,
    this.downloadUrl = '',
    this.shareUrl,
    this.createdAt = '',
    this.createdTime = '',
    this.owner = 'Me',
  });

  factory DriveFile.fromJson(Map<String, dynamic> json) {
    return DriveFile(
      id: json['id'] is int ? json['id'] : int.tryParse('${json['id']}') ?? 0,
      filename: json['filename'] ?? 'Unnamed File',
      folderId: json['folder_id'] != null ? (json['folder_id'] is int ? json['folder_id'] : int.tryParse('${json['folder_id']}')) : null,
      folderName: json['folder_name'] ?? 'My Drive',
      fileSizeBytes: json['file_size_bytes'] is int ? json['file_size_bytes'] : int.tryParse('${json['file_size_bytes']}') ?? 0,
      formattedSize: json['formatted_size'] ?? '0 B',
      extension: json['extension'] ?? '',
      category: json['category'] ?? 'other',
      shareToken: json['share_token'] ?? '',
      isPublic: json['is_public'] == true,
      shareRole: json['share_role'] ?? 'viewer',
      isStarred: json['is_starred'] == true,
      isTrashed: json['is_trashed'] == true,
      downloadUrl: json['download_url'] ?? '',
      shareUrl: json['share_url'],
      createdAt: json['created_at'] ?? '',
      createdTime: json['created_time'] ?? '',
      owner: json['owner'] ?? 'Me',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'filename': filename,
    'folder_id': folderId,
    'folder_name': folderName,
    'file_size_bytes': fileSizeBytes,
    'formatted_size': formattedSize,
    'extension': extension,
    'category': category,
    'share_token': shareToken,
    'is_public': isPublic,
    'share_role': shareRole,
    'is_starred': isStarred,
    'is_trashed': isTrashed,
    'download_url': downloadUrl,
    'share_url': shareUrl,
    'created_at': createdAt,
    'created_time': createdTime,
    'owner': owner,
  };
}

class DriveBreadcrumb {
  final int? id;
  final String name;

  const DriveBreadcrumb({this.id, required this.name});

  factory DriveBreadcrumb.fromJson(Map<String, dynamic> json) {
    return DriveBreadcrumb(
      id: json['id'] != null ? (json['id'] is int ? json['id'] : int.tryParse('${json['id']}')) : null,
      name: json['name'] ?? 'Home',
    );
  }
}

class StorageQuotaInfo {
  final int quotaMb;
  final int quotaBytes;
  final int usedBytes;
  final int freeBytes;
  final double usedPercent;
  final String quotaFormatted;
  final String usedFormatted;
  final String freeFormatted;
  final bool isExceeded;

  const StorageQuotaInfo({
    this.quotaMb = 5120,
    this.quotaBytes = 5368709120,
    this.usedBytes = 0,
    this.freeBytes = 5368709120,
    this.usedPercent = 0.0,
    this.quotaFormatted = '5.0 GB',
    this.usedFormatted = '0 MB',
    this.freeFormatted = '5.0 GB',
    this.isExceeded = false,
  });

  factory StorageQuotaInfo.fromJson(Map<String, dynamic> json) {
    return StorageQuotaInfo(
      quotaMb: json['quota_mb'] is int ? json['quota_mb'] : int.tryParse('${json['quota_mb']}') ?? 5120,
      quotaBytes: json['quota_bytes'] is int ? json['quota_bytes'] : int.tryParse('${json['quota_bytes']}') ?? 5368709120,
      usedBytes: json['used_bytes'] is int ? json['used_bytes'] : int.tryParse('${json['used_bytes']}') ?? 0,
      freeBytes: json['free_bytes'] is int ? json['free_bytes'] : int.tryParse('${json['free_bytes']}') ?? 5368709120,
      usedPercent: (json['used_percent'] is num) ? (json['used_percent'] as num).toDouble() : double.tryParse('${json['used_percent']}') ?? 0.0,
      quotaFormatted: json['quota_formatted'] ?? '5.0 GB',
      usedFormatted: json['used_formatted'] ?? '0 MB',
      freeFormatted: json['free_formatted'] ?? '5.0 GB',
      isExceeded: json['is_exceeded'] == true,
    );
  }
}
