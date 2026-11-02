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
  final bool needsReply;
  final String? urgencyLevel;
  final String? aiReason;
  final String? actionNeeded;
  final int? importanceScore;
  final int? priorityScore;
  final bool isUnwanted;
  bool isAnswered;

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
    this.needsReply = false,
    this.urgencyLevel,
    this.aiReason,
    this.actionNeeded,
    this.importanceScore,
    this.priorityScore,
    this.isUnwanted = false,
    this.isAnswered = false,
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
    bool? needsReply,
    String? urgencyLevel,
    String? aiReason,
    String? actionNeeded,
    int? importanceScore,
    int? priorityScore,
    bool? isUnwanted,
    bool? isAnswered,
    bool? isAiPriority,
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
      needsReply: needsReply ?? this.needsReply,
      urgencyLevel: urgencyLevel ?? this.urgencyLevel,
      aiReason: aiReason ?? this.aiReason,
      actionNeeded: actionNeeded ?? this.actionNeeded,
      importanceScore: importanceScore ?? this.importanceScore,
      priorityScore: priorityScore ?? this.priorityScore,
      isUnwanted: isUnwanted ?? this.isUnwanted,
      isAnswered: isAnswered ?? this.isAnswered,
      isAiPriority: isAiPriority ?? this.isAiPriority,
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
    'needsReply': needsReply,
    'urgencyLevel': urgencyLevel,
    'aiReason': aiReason,
    'actionNeeded': actionNeeded,
    'importanceScore': importanceScore,
    'priorityScore': priorityScore,
    'isUnwanted': isUnwanted,
    'isAnswered': isAnswered,
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
      needsReply: json['needsReply'] ?? false,
      urgencyLevel: json['urgencyLevel'],
      aiReason: json['aiReason'],
      actionNeeded: json['actionNeeded'],
      importanceScore: json['importanceScore'],
      priorityScore: json['priorityScore'],
      isUnwanted: json['isUnwanted'] ?? false,
      isAnswered: json['isAnswered'] ?? false,
    );
  }

  factory EmailItem.fromWorkspaceJson(Map<String, dynamic> json, {String? defaultAccountEmail}) {
    FolderType parsedFolder = FolderType.inbox;
    final folderStr = (json['folder'] as String? ?? 'inbox').toLowerCase();
    if (folderStr == 'sent') {
      parsedFolder = FolderType.sent;
    } else if (folderStr == 'drafts') {
      parsedFolder = FolderType.drafts;
    } else if (folderStr == 'trash') {
      parsedFolder = FolderType.trash;
    } else if (folderStr == 'spam' || folderStr == 'junk') {
      parsedFolder = FolderType.spam;
    } else if (folderStr == 'archive') {
      parsedFolder = FolderType.archive;
    }

    DateTime parsedDate;
    if (json['mtime'] != null) {
      try {
        final seconds = (json['mtime'] as num).toDouble();
        parsedDate = DateTime.fromMillisecondsSinceEpoch((seconds * 1000).toInt());
      } catch (_) {
        parsedDate = DateTime.now();
      }
    } else {
      parsedDate = DateTime.now();
    }

    final sender = json['sender']?.toString() ?? json['from']?.toString() ?? 'VoidOnyx';
    final fromEmail = json['from']?.toString() ?? 'security@voidonyx.com';
    final targetAccount = json['account_email']?.toString() ?? defaultAccountEmail ?? '';

    Color avatarColor = const Color(0xFFFF7A00);
    if (sender.toLowerCase().contains('security')) {
      avatarColor = const Color(0xFF10B981);
    } else if (sender.toLowerCase().contains('ai')) {
      avatarColor = const Color(0xFF8B5CF6);
    } else if (sender.toLowerCase().contains('server')) {
      avatarColor = const Color(0xFF3B82F6);
    }

    final attachmentsList = <String>[];
    if (json['attachments'] is List) {
      for (final att in json['attachments']) {
        if (att is Map && att['name'] != null) {
          attachmentsList.add(att['name'].toString());
        }
      }
    }

    final rawHtml = json['body_html']?.toString() ?? '';
    final rawSnippet = json['snippet']?.toString() ?? '';
    final plainBody = rawHtml.isNotEmpty
        ? rawHtml.replaceAll(RegExp(r'<[^>]*>'), ' ').replaceAll(RegExp(r'\s+'), ' ').trim()
        : rawSnippet;

    final isUnread = json['is_unread'] == true;
    final isStarred = json['is_starred'] == true;
    final pScore = (json['ai_priority_score'] ?? json['priority_score'] as num?)?.toInt();
    final isAi = json['ai_priority'] == 'high' || (pScore != null && pScore >= 75);

    // Unanswered status determination
    bool needsReply = json['needs_reply'] == true ||
        (json['is_answered'] == false && json['urgency_level'] != null && json['urgency_level'] != 'Normal');
    String? urgency = json['urgency_level']?.toString();
    String? reason = json['ai_reason']?.toString();

    // Heuristic fallback for emails awaiting answer
    if (!needsReply && parsedFolder == FolderType.inbox) {
      final combined = '${json['subject'] ?? ''} $rawSnippet $plainBody'.toLowerCase();
      if (combined.contains('?') ||
          combined.contains('pricing') ||
          combined.contains('proposal') ||
          combined.contains('quote') ||
          combined.contains('urgent') ||
          combined.contains('meeting') ||
          combined.contains('can you') ||
          combined.contains('please confirm') ||
          combined.contains('let me know')) {
        needsReply = true;
        urgency ??= combined.contains('urgent') ? 'Urgent' : (combined.contains('?') ? 'Question Asked' : 'Action Required');
        reason ??= 'Pending question or actionable request';
      }
    }

    return EmailItem(
      id: json['id']?.toString() ?? 'msg-${DateTime.now().millisecondsSinceEpoch}',
      senderName: sender,
      senderEmail: fromEmail,
      recipientEmail: targetAccount,
      subject: json['subject']?.toString() ?? '(No Subject)',
      snippet: rawSnippet.isNotEmpty ? rawSnippet : (plainBody.length > 120 ? plainBody.substring(0, 120) : plainBody),
      body: plainBody,
      timestamp: parsedDate,
      isRead: !isUnread,
      isStarred: isStarred,
      hasAttachments: json['has_attachments'] == true || attachmentsList.isNotEmpty,
      attachmentNames: attachmentsList,
      folder: parsedFolder,
      avatarColor: avatarColor,
      isAiPriority: isAi,
      category: json['category']?.toString() ?? 'Primary',
      htmlBody: rawHtml.isNotEmpty ? rawHtml : null,
      accountEmail: targetAccount.isNotEmpty ? targetAccount : defaultAccountEmail,
      needsReply: needsReply,
      urgencyLevel: urgency,
      aiReason: reason,
      actionNeeded: json['action_needed']?.toString(),
      importanceScore: (json['importance_score'] as num?)?.toInt(),
      priorityScore: pScore,
      isUnwanted: json['is_unwanted'] == true,
      isAnswered: json['is_answered'] == true,
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
