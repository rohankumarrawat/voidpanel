import 'package:flutter/material.dart';

enum FolderType {
  inbox,
  starred,
  sent,
  drafts,
  spam,
  trash,
  archive,
  notes,
}

class MailFolder {
  final FolderType type;
  final String title;
  final IconData icon;
  final Color? color;
  final int unreadCount;
  final bool isCustom;

  const MailFolder({
    required this.type,
    required this.title,
    required this.icon,
    this.color,
    this.unreadCount = 0,
    this.isCustom = false,
  });

  static const List<MailFolder> systemFolders = [
    MailFolder(type: FolderType.inbox, title: 'Inbox', icon: Icons.inbox_outlined, unreadCount: 12),
    MailFolder(type: FolderType.starred, title: 'Starred', icon: Icons.star_border_rounded),
    MailFolder(type: FolderType.sent, title: 'Sent', icon: Icons.send_outlined),
    MailFolder(type: FolderType.drafts, title: 'Drafts', icon: Icons.drafts_outlined, unreadCount: 4),
    MailFolder(type: FolderType.spam, title: 'Spam', icon: Icons.security_rounded, unreadCount: 8),
    MailFolder(type: FolderType.trash, title: 'Trash', icon: Icons.delete_outline_rounded),
    MailFolder(type: FolderType.archive, title: 'Archive', icon: Icons.archive_outlined),
    MailFolder(type: FolderType.notes, title: 'Notes', icon: Icons.sticky_note_2_outlined),
  ];
}
