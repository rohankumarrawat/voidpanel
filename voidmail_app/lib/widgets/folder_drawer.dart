import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/folder.dart';
import '../providers/mail_provider.dart';

class FolderDrawer extends StatelessWidget {
  const FolderDrawer({super.key});

  String _formatDisplayName(String email) {
    if (!email.contains('@')) return 'VoidMail Account';
    final handle = email.split('@')[0];
    if (handle.isEmpty) return 'VoidMail Account';
    return handle[0].toUpperCase() + handle.substring(1);
  }

  Color _getAccountColor(int index) {
    const colors = [
      Color(0xFF6C5CE7), Color(0xFF00B894), Color(0xFFE17055),
      Color(0xFF0984E3), Color(0xFFEC4899), Color(0xFFF59E0B),
    ];
    return colors[index % colors.length];
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final accounts = provider.accounts;
    final activeIndex = provider.activeAccountIndex;
    final currentEmail = provider.currentEmail;
    final displayName = _formatDisplayName(currentEmail);
    final serverHost = provider.config?.imapHost ?? 'mail.voidonyx.in';
    final isUnified = provider.showUnifiedInbox;

    return Drawer(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : Colors.white,
      child: SafeArea(
        child: Column(
          children: [
            // 1. Account Switcher Header
            Container(
              margin: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF6C5CE7), Color(0xFF5A49E3)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(24),
              ),
              child: Column(
                children: [
                  // Active account info
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 14, 8, 10),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 18,
                          backgroundColor: Colors.white24,
                          child: Text(
                            displayName.isNotEmpty ? displayName[0].toUpperCase() : 'V',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                isUnified ? 'Primary Mail' : displayName,
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                                overflow: TextOverflow.ellipsis,
                              ),
                              Text(
                                isUnified ? '${accounts.length} accounts linked' : currentEmail,
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.logout_rounded, color: Colors.white, size: 18),
                          tooltip: 'Logout',
                          onPressed: () {
                            provider.logout();
                            Navigator.pushReplacementNamed(context, '/login');
                          },
                        ),
                      ],
                    ),
                  ),

                  // Account avatars row (multi-account switcher)
                  if (accounts.length > 1 || accounts.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: [
                            // "All Inboxes" pill
                            GestureDetector(
                              onTap: () {
                                provider.toggleUnifiedInbox();
                                Navigator.pop(context);
                              },
                              child: Container(
                                margin: const EdgeInsets.only(right: 8),
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: isUnified ? Colors.white : Colors.white24,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.all_inbox_rounded, size: 14,
                                      color: isUnified ? const Color(0xFF6C5CE7) : Colors.white70),
                                    const SizedBox(width: 4),
                                    Text('Primary',
                                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                                        color: isUnified ? const Color(0xFF6C5CE7) : Colors.white70)),
                                  ],
                                ),
                              ),
                            ),

                            // Individual account avatars
                            ...accounts.asMap().entries.map((entry) {
                              final idx = entry.key;
                              final acc = entry.value;
                              final isActive = !isUnified && idx == activeIndex;
                              final initial = acc.email.isNotEmpty ? acc.email[0].toUpperCase() : '?';
                              final color = _getAccountColor(idx);

                              return GestureDetector(
                                onTap: () {
                                  provider.switchAccount(idx);
                                  Navigator.pop(context);
                                },
                                onLongPress: () {
                                  // Show remove dialog
                                  showDialog(
                                    context: context,
                                    builder: (ctx) => AlertDialog(
                                      title: Text('Remove Account', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
                                      content: Text('Remove ${acc.email}?', style: GoogleFonts.inter()),
                                      actions: [
                                        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
                                        TextButton(
                                          onPressed: () {
                                            provider.removeAccount(idx);
                                            Navigator.pop(ctx);
                                          },
                                          child: const Text('Remove', style: TextStyle(color: Colors.red)),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                                child: Container(
                                  margin: const EdgeInsets.only(right: 8),
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: isActive ? Colors.white : Colors.transparent,
                                      width: 2,
                                    ),
                                  ),
                                  child: CircleAvatar(
                                    radius: 14,
                                    backgroundColor: color,
                                    child: Text(initial, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11)),
                                  ),
                                ),
                              );
                            }),

                            // Add account button
                            GestureDetector(
                              onTap: () {
                                final nav = Navigator.of(context, rootNavigator: true);
                                Navigator.pop(context); // close drawer
                                Future.microtask(() {
                                  nav.pushNamed('/login', arguments: {'addAccount': true});
                                });
                              },
                              child: Container(
                                width: 28, height: 28,
                                decoration: BoxDecoration(
                                  color: Colors.white24,
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(Icons.add_rounded, color: Colors.white, size: 16),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),

            // 2. Folder List
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                children: [
                  ...MailFolder.systemFolders.map((folder) {
                    final isSelected = provider.currentFolder == folder.type;
                    final unreadCount = provider.getUnreadCount(folder.type);

                    return GestureDetector(
                      onTap: () {
                        provider.selectFolder(folder.type);
                        Navigator.pop(context);
                      },
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 2),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? (isDark ? const Color(0xFF1B1638) : const Color(0xFFF3F0FF))
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              folder.icon,
                              color: isSelected
                                  ? const Color(0xFF6C5CE7)
                                  : (isDark ? Colors.grey[400] : const Color(0xFF4B5563)),
                              size: 20,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                folder.title,
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                                  color: isSelected
                                      ? const Color(0xFF6C5CE7)
                                      : (isDark ? Colors.white : const Color(0xFF1F2937)),
                                ),
                              ),
                            ),
                            if (unreadCount > 0)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: isSelected ? const Color(0xFF6C5CE7) : const Color(0xFFE0E7FF),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  '$unreadCount',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: isSelected ? Colors.white : const Color(0xFF4338CA),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),

            // 3. Connection Info
            Container(
              margin: const EdgeInsets.all(12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1B1638) : const Color(0xFFF9FAFC),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEFEFF6)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 8, height: 8,
                        decoration: const BoxDecoration(color: Color(0xFF10B981), shape: BoxShape.circle),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        isUnified ? '${accounts.length} Accounts Active' : 'IMAP & SMTP Active',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                      const Spacer(),
                      const Icon(Icons.cloud_done_rounded, size: 16, color: Color(0xFF10B981)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    isUnified ? 'Primary mail mode' : 'Server: $serverHost',
                    style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
