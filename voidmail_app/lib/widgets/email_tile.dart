import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/email_item.dart';
import '../models/folder.dart';
import '../providers/mail_provider.dart';

class EmailTile extends StatelessWidget {
  final EmailItem email;
  final bool isSelected;
  final bool isSelectionMode;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final VoidCallback? onStarToggle;

  const EmailTile({
    super.key,
    required this.email,
    this.isSelected = false,
    this.isSelectionMode = false,
    this.onTap,
    this.onLongPress,
    this.onStarToggle,
  });

  String _formatTimestamp(DateTime dt) {
    final now = DateTime.now();
    if (dt.day == now.day && dt.month == now.month && dt.year == now.year) {
      return DateFormat('h:mm a').format(dt);
    } else if (dt.day == now.day - 1 && dt.month == now.month && dt.year == now.year) {
      return 'Yesterday';
    } else {
      return DateFormat('MMM d').format(dt);
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context, listen: false);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final tileIsSelected = provider.selectedEmailIds.contains(email.id);
    final inSelectionMode = provider.isSelectionMode;

    return InkWell(
      onTap: onTap ??
          () {
            if (inSelectionMode) {
              provider.toggleSelection(email.id);
            } else {
              provider.markAsRead(email.id);
              Navigator.pushNamed(context, '/email_detail', arguments: email);
            }
          },
      onLongPress: onLongPress ??
          () {
            provider.toggleSelection(email.id);
          },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: tileIsSelected
              ? (isDark ? const Color(0xFF2C2554) : const Color(0xFFF3F0FF))
              : (!email.isRead
                  ? (isDark ? const Color(0xFF16122E) : const Color(0xFFFAF9FF))
                  : Colors.transparent),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Checkbox or Avatar
            if (inSelectionMode)
              Padding(
                padding: const EdgeInsets.only(right: 12, top: 4),
                child: Checkbox(
                  value: tileIsSelected,
                  activeColor: const Color(0xFF6C5CE7),
                  onChanged: (_) => provider.toggleSelection(email.id),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.only(right: 12),
                child: CircleAvatar(
                  radius: 20,
                  backgroundColor: email.sendFailed
                      ? const Color(0xFFEF4444)
                      : (email.isSendingStatus ? const Color(0xFFF59E0B) : email.avatarColor),
                  child: email.isSendingStatus
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : email.sendFailed
                          ? const Icon(Icons.error_outline_rounded, size: 20, color: Colors.white)
                          : Text(
                              email.senderName.isNotEmpty ? email.senderName[0].toUpperCase() : 'V',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                ),
              ),

            // Content Column
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Text(
                          email.folder == FolderType.sent
                              ? 'To: ${email.recipientEmail.isNotEmpty ? email.recipientEmail : "Unknown"}'
                              : email.senderName,
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight: !email.isRead ? FontWeight.bold : FontWeight.w600,
                            color: isDark ? Colors.white : const Color(0xFF1E1B4B),
                          ),
                          overflow: TextOverflow.ellipsis,
                          maxLines: 1,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _formatTimestamp(email.timestamp),
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: !email.isRead ? FontWeight.bold : FontWeight.normal,
                          color: !email.isRead
                              ? const Color(0xFF6C5CE7)
                              : (isDark ? Colors.grey[400] : const Color(0xFF9CA3AF)),
                        ),
                      ),
                      if (!email.isRead) ...[
                        const SizedBox(width: 6),
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: Color(0xFF6C5CE7),
                            shape: BoxShape.circle,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 2),

                  // Sending / Delivery Failed Badge
                  if (email.isSendingStatus)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          const SizedBox(
                            width: 10,
                            height: 10,
                            child: CircularProgressIndicator(strokeWidth: 1.5, color: Color(0xFF6C5CE7)),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Sending in background...',
                            style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF6C5CE7), fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    )
                  else if (email.sendFailed)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          GestureDetector(
                            onTap: () => provider.retrySendEmail(email),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: const Color(0xFFEF4444).withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.refresh_rounded, size: 12, color: Color(0xFFEF4444)),
                                  const SizedBox(width: 4),
                                  Text(
                                    'Delivery Failed • Tap to Retry',
                                    style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFFEF4444), fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                  Text(
                    email.subject,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: !email.isRead ? FontWeight.bold : FontWeight.w500,
                      color: isDark ? Colors.grey[200] : const Color(0xFF374151),
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      // Account badge for unified inbox
                      if (provider.showUnifiedInbox && email.accountEmail != null) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                          margin: const EdgeInsets.only(right: 6),
                          decoration: BoxDecoration(
                            color: const Color(0xFF6C5CE7).withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            email.accountEmail!.split('@').first,
                            style: GoogleFonts.inter(
                              fontSize: 9,
                              fontWeight: FontWeight.bold,
                              color: const Color(0xFF6C5CE7),
                            ),
                          ),
                        ),
                      ],
                      Expanded(
                        child: Text(
                          email.snippet,
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Star Button
            IconButton(
              icon: Icon(
                email.isStarred ? Icons.star_rounded : Icons.star_outline_rounded,
                color: email.isStarred
                    ? const Color(0xFFF59E0B)
                    : (isDark ? Colors.grey[600] : const Color(0xFFD1D5DB)),
                size: 20,
              ),
              onPressed: onStarToggle ?? () => provider.toggleStar(email.id),
            ),
          ],
        ),
      ),
    );
  }
}
