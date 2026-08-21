import 'dart:convert';
import 'package:flutter/material.dart';
import 'folder.dart';

class EmailItem {
  final String id;
  final String senderName;
  final String senderEmail;
  final String recipientEmail;
  final String subject;
  final String snippet;
  final String body;
  final DateTime timestamp;
  bool isRead;
  bool isStarred;
  final bool hasAttachments;
  final List<String> attachmentNames;
  FolderType folder;
  final Color avatarColor;
  bool isSendingStatus;
  bool sendFailed;
  String? sendErrorDetail;
  final String? aiSummary;
  final bool isAiPriority;
  final String category;
  final IconData? brandIcon;
  final String? htmlBody;
  final String? accountEmail; // Which account this email belongs to

  EmailItem({
    required this.id,
    required this.senderName,
    required this.senderEmail,
    required this.recipientEmail,
    required this.subject,
    required this.snippet,
    required this.body,
    required this.timestamp,
    this.isRead = false,
    this.isStarred = false,
    this.hasAttachments = false,
    this.attachmentNames = const [],
    this.folder = FolderType.inbox,
    this.avatarColor = const Color(0xFF6C5CE7),
    this.isSendingStatus = false,
    this.sendFailed = false,
    this.sendErrorDetail,
    this.aiSummary,
    this.isAiPriority = false,
    this.category = 'Primary',
    this.brandIcon,
    this.htmlBody,
    this.accountEmail,
  });

  EmailItem copyWith({
    String? id,
    String? senderName,
    String? senderEmail,
    String? recipientEmail,
    String? subject,
    String? snippet,
    String? body,
    DateTime? timestamp,
    bool? isRead,
    bool? isStarred,
    bool? hasAttachments,
    List<String>? attachmentNames,
    FolderType? folder,
    Color? avatarColor,
    bool? isSendingStatus,
    bool? sendFailed,
    String? sendErrorDetail,
    String? htmlBody,
  }) {
    return EmailItem(
      id: id ?? this.id,
      senderName: senderName ?? this.senderName,
      senderEmail: senderEmail ?? this.senderEmail,
      recipientEmail: recipientEmail ?? this.recipientEmail,
      subject: subject ?? this.subject,
      snippet: snippet ?? this.snippet,
      body: body ?? this.body,
      timestamp: timestamp ?? this.timestamp,
      isRead: isRead ?? this.isRead,
      isStarred: isStarred ?? this.isStarred,
      hasAttachments: hasAttachments ?? this.hasAttachments,
      attachmentNames: attachmentNames ?? this.attachmentNames,
      folder: folder ?? this.folder,
      avatarColor: avatarColor ?? this.avatarColor,
      isSendingStatus: isSendingStatus ?? this.isSendingStatus,
      sendFailed: sendFailed ?? this.sendFailed,
      sendErrorDetail: sendErrorDetail ?? this.sendErrorDetail,
      htmlBody: htmlBody ?? this.htmlBody,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'senderName': senderName,
    'senderEmail': senderEmail,
    'recipientEmail': recipientEmail,
    'subject': subject,
    'snippet': snippet,
    'body': body,
    'timestamp': timestamp.toIso8601String(),
    'isRead': isRead,
    'isStarred': isStarred,
    'hasAttachments': hasAttachments,
    'attachmentNames': attachmentNames,
    'folder': folder.name,
    'avatarColor': avatarColor.value,
    'isSendingStatus': isSendingStatus,
    'sendFailed': sendFailed,
    'sendErrorDetail': sendErrorDetail,
    'aiSummary': aiSummary,
    'isAiPriority': isAiPriority,
    'category': category,
    'htmlBody': htmlBody,
    'accountEmail': accountEmail,
  };

  factory EmailItem.fromJson(Map<String, dynamic> json) {
    FolderType parsedFolder = FolderType.inbox;
    final folderStr = json['folder'] as String? ?? 'inbox';
    for (final f in FolderType.values) {
      if (f.name == folderStr) {
        parsedFolder = f;
        break;
      }
    }

    DateTime parsedDate;
    try {
      parsedDate = DateTime.parse(json['timestamp'] ?? '');
    } catch (_) {
      parsedDate = DateTime.now();
    }

    Color parsedColor = const Color(0xFF6C5CE7);
    if (json['avatarColor'] != null) {
      try {
        parsedColor = Color(json['avatarColor'] as int);
      } catch (_) {}
    }

    return EmailItem(
      id: json['id']?.toString() ?? '',
      senderName: json['senderName'] ?? '',
      senderEmail: json['senderEmail'] ?? '',
      recipientEmail: json['recipientEmail'] ?? '',
      subject: json['subject'] ?? '(No Subject)',
      snippet: json['snippet'] ?? '',
      body: json['body'] ?? '',
      timestamp: parsedDate,
      isRead: json['isRead'] ?? false,
      isStarred: json['isStarred'] ?? false,
      hasAttachments: json['hasAttachments'] ?? false,
      attachmentNames: (json['attachmentNames'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      folder: parsedFolder,
      avatarColor: parsedColor,
      isSendingStatus: json['isSendingStatus'] ?? false,
      sendFailed: json['sendFailed'] ?? false,
      sendErrorDetail: json['sendErrorDetail'],
      aiSummary: json['aiSummary'],
      isAiPriority: json['isAiPriority'] ?? false,
      category: json['category'] ?? 'Primary',
      htmlBody: json['htmlBody'],
      accountEmail: json['accountEmail'],
    );
  }

  static String encodeList(List<EmailItem> items) {
    try {
      return jsonEncode(items.map((e) => e.toJson()).toList());
    } catch (_) {
      return '[]';
    }
  }

  static List<EmailItem> decodeList(String jsonStr) {
    try {
      final decoded = jsonDecode(jsonStr);
      if (decoded is List) {
        return decoded
            .whereType<Map>()
            .map((item) => EmailItem.fromJson(Map<String, dynamic>.from(item)))
            .toList();
      }
    } catch (_) {}
    return [];
  }
}
