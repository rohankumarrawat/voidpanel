import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/folder.dart';
import '../models/voidpanel_config.dart';
import '../providers/mail_provider.dart';
import '../views/whatsapp_alerts_view.dart';
import '../views/settings_view.dart';
import 'upgrade_lead_modal.dart';


class FolderDrawer extends StatelessWidget {
  const FolderDrawer({super.key});

  void _safeCloseDrawer(BuildContext context) {
    final scaffold = Scaffold.maybeOf(context);
    if (scaffold?.isDrawerOpen ?? false) {
      scaffold?.closeDrawer();
    } else if (Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
    }
  }

  String _formatDisplayName(String email) {
    if (!email.contains('@')) return 'VoidMail Account';
    final handle = email.split('@')[0];
    if (handle.isEmpty) return 'VoidMail Account';
    return handle[0].toUpperCase() + handle.substring(1);
  }

  Color _getAccountColor(int index) {
    const colors = [
      Color(0xFFFF7A00), Color(0xFF00B894), Color(0xFFE17055),
      Color(0xFF0984E3), Color(0xFFEC4899), Color(0xFFFFB800),
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
    final currentFolder = provider.currentFolder;
    final folders = MailFolder.systemFolders;


    return Drawer(
      backgroundColor: isDark ? const Color(0xFF100B07) : Colors.white,
      child: SafeArea(
        child: Column(
          children: [
            // 1. Account Switcher Header
            Container(
              margin: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFFF7A00), Color(0xFFE65100)],
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
                              Row(
                                children: [
                                  Flexible(
                                    child: Text(
                                      displayName,
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: currentEmail.toLowerCase().contains('voidonyx')
                                          ? Colors.white.withValues(alpha: 0.25)
                                          : const Color(0xFF3B82F6),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      currentEmail.toLowerCase().contains('voidonyx')
                                          ? 'VoidOnyx'
                                          : 'Business',
                                      style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                              Text(
                                serverHost,
                                style: const TextStyle(color: Colors.white70, fontSize: 11),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.logout_rounded, color: Colors.white, size: 18),
                          tooltip: provider.isCurrentAccountPrimary ? 'Logout All Accounts' : 'Logout This Email',
                          onPressed: () => _showLogoutConfirmDialog(context, provider),
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
                                _safeCloseDrawer(context);
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
                                      color: isUnified ? provider.accentColor : Colors.white70),
                                    const SizedBox(width: 4),
                                    Text('Primary',
                                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                                        color: isUnified ? provider.accentColor : Colors.white70)),
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
                                  _safeCloseDrawer(context);
                                },
                                onLongPress: () {
                                  _showAccountOptionsDialog(context, provider, acc, idx);
                                },
                                child: Tooltip(
                                  message: '${acc.email} (Tap to switch, long-press for options)',
                                  child: Container(
                                    margin: const EdgeInsets.only(right: 8),
                                    padding: const EdgeInsets.all(2),
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
                                      child: Text(
                                        initial,
                                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                                      ),
                                    ),
                                  ),
                                ),
                              );
                            }),

                            // Add Business Email "+" button
                            GestureDetector(
                              onTap: () {
                                _safeCloseDrawer(context);
                                Navigator.pushNamed(
                                  context,
                                  '/login',
                                  arguments: {'addAccount': true},
                                );
                              },
                              child: Container(
                                margin: const EdgeInsets.only(left: 4),
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                decoration: BoxDecoration(
                                  color: Colors.white24,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.add_business_rounded, size: 14, color: Colors.white),
                                    SizedBox(width: 4),
                                    Text('+ Business Mail', style: TextStyle(fontSize: 11, color: Colors.white, fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),

            // 2. Mail Folders, Aliases, & Workspace Suites
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                children: [
                  // ── SECTION 1: MAILBOX FOLDERS (HIGHEST PRIORITY) ──
                  Padding(
                    padding: const EdgeInsets.fromLTRB(8, 4, 8, 6),
                    child: Text(
                      'MAILBOX',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8,
                        color: isDark ? Colors.grey[400] : Colors.grey[600],
                      ),
                    ),
                  ),

                  // Folder items (Inbox, Unanswered, Starred, Sent, Drafts, Archive, Spam, Trash, Notes)
                  ...folders.map((folder) {
                    final isSelected = provider.activeSuiteIndex == 0 && currentFolder == folder.type;
                    final unreadCount = provider.getUnreadCount(folder.type);
                    final isUnanswered = folder.type == FolderType.unanswered;
                    final itemColor = isUnanswered ? const Color(0xFFD97706) : provider.accentColor;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 2),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: () {
                          provider.setActiveSuiteIndex(0);
                          provider.selectFolder(folder.type);
                          _safeCloseDrawer(context);
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? (isUnanswered
                                    ? (isDark ? const Color(0xFF2E1C12) : const Color(0xFFFEF3C7))
                                    : (isDark ? const Color(0xFF1C140D) : const Color(0xFFFFF7ED)))
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                folder.icon,
                                color: isSelected
                                    ? itemColor
                                    : (isUnanswered
                                        ? const Color(0xFFD97706)
                                        : (isDark ? Colors.grey[400] : const Color(0xFF4B5563))),
                                size: 18,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  folder.title,
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                                    color: isSelected
                                        ? itemColor
                                        : (isDark ? Colors.white : const Color(0xFF1F2937)),
                                  ),
                                ),
                              ),
                              if (unreadCount > 0)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: isUnanswered
                                        ? const Color(0xFFFEF3C7)
                                        : (isSelected ? provider.accentColor : const Color(0xFFFFEDD5)),
                                    borderRadius: BorderRadius.circular(10),
                                    border: isUnanswered ? Border.all(color: const Color(0xFFFCD34D), width: 1) : null,
                                  ),
                                  child: Text(
                                    '$unreadCount',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: isUnanswered
                                        ? const Color(0xFFB45309)
                                        : (isSelected ? Colors.white : const Color(0xFFC2410C)),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }),

                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Divider(height: 1),
                  ),

                  // ── SECTION 2: EMAIL ALIASES & ROUTING ──
                  Padding(
                    padding: const EdgeInsets.fromLTRB(8, 4, 8, 6),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'EMAIL ALIASES (${provider.userAliases.length})',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.8,
                            color: isDark ? Colors.grey[400] : Colors.grey[600],
                          ),
                        ),
                        InkWell(
                          onTap: () => _showAddAliasDialog(context, provider),
                          borderRadius: BorderRadius.circular(6),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                            child: Row(
                              children: [
                                Icon(Icons.add_rounded, size: 14, color: provider.accentColor),
                                const SizedBox(width: 2),
                                Text(
                                  'Add',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: provider.accentColor,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Primary Account Identity
                  _buildAliasItem(
                    context: context,
                    email: provider.currentEmail,
                    isPrimary: true,
                    isSelected: provider.selectedAliasFilter == null,
                    isDark: isDark,
                    accentColor: provider.accentColor,
                    onTap: () {
                      provider.filterByAlias(null);
                      _safeCloseDrawer(context);
                    },
                  ),

                  // Virtual Aliases
                  ...provider.userAliases.map((alias) {
                    final sourceEmail = alias['source_email']?.toString() ?? '';
                    final aliasId = alias['id'] is int
                        ? alias['id'] as int
                        : int.tryParse(alias['id']?.toString() ?? '') ?? 0;
                    final isSelected = provider.selectedAliasFilter == sourceEmail;

                    return _buildAliasItem(
                      context: context,
                      email: sourceEmail,
                      isPrimary: false,
                      isSelected: isSelected,
                      isDark: isDark,
                      accentColor: provider.accentColor,
                      onTap: () {
                        provider.filterByAlias(isSelected ? null : sourceEmail);
                        _safeCloseDrawer(context);
                      },
                      onDelete: () => _showDeleteAliasConfirm(context, provider, aliasId, sourceEmail),
                    );
                  }),

                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Divider(height: 1),
                  ),

                  // ── SECTION 3: CLOUD WORKSPACE SUITES ──
                  Padding(
                    padding: const EdgeInsets.fromLTRB(8, 4, 8, 6),
                    child: Text(
                      'WORKSPACE SUITES',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8,
                        color: isDark ? Colors.grey[400] : Colors.grey[600],
                      ),
                    ),
                  ),

                  // 1. VoidDrive
                  _buildSuiteItem(
                    icon: Icons.cloud_rounded,
                    title: 'VoidDrive',
                    subtitle: 'Cloud File Storage',
                    isActive: provider.activeSuiteIndex == 1,
                    accentColor: const Color(0xFF4F46E5),
                    isDark: isDark,
                    onTap: () {
                      provider.setActiveSuiteIndex(1);
                      _safeCloseDrawer(context);
                    },
                  ),

                  // 2. Mini CRM
                  _buildSuiteItem(
                    icon: Icons.leaderboard_rounded,
                    title: 'Mini CRM',
                    subtitle: 'Pipeline & Deals Kanban',
                    isActive: provider.activeSuiteIndex == 2,
                    accentColor: const Color(0xFF059669),
                    isDark: isDark,
                    onTap: () {
                      provider.setActiveSuiteIndex(2);
                      _safeCloseDrawer(context);
                    },
                  ),

                  // 3. VoidCalendar
                  _buildSuiteItem(
                    icon: Icons.calendar_month_rounded,
                    title: 'VoidCalendar',
                    subtitle: 'Meetings & Schedule',
                    isActive: provider.activeSuiteIndex == 3,
                    accentColor: const Color(0xFF7C3AED),
                    isDark: isDark,
                    onTap: () {
                      provider.setActiveSuiteIndex(3);
                      _safeCloseDrawer(context);
                    },
                  ),

                  // 4. Security Shield
                  _buildSuiteItem(
                    icon: Icons.shield_rounded,
                    title: 'Security Shield',
                    subtitle: 'Domain Health & Burn Mail',
                    isActive: provider.activeSuiteIndex == 4,
                    accentColor: const Color(0xFF10B981),
                    isDark: isDark,
                    onTap: () {
                      provider.setActiveSuiteIndex(4);
                      _safeCloseDrawer(context);
                    },
                  ),

                  // 5. WhatsApp VIP Alerts
                  _buildSuiteItem(
                    icon: Icons.mark_chat_read_rounded,
                    title: 'WhatsApp VIP Alerts',
                    subtitle: 'Instant Alerts & 2-Way Reply',
                    isActive: false,
                    accentColor: const Color(0xFF10B981),
                    isDark: isDark,
                    onTap: () {
                      _safeCloseDrawer(context);
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (context) => const WhatsAppAlertsView()),
                      );
                    },
                  ),

                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Divider(height: 1),
                  ),

                  // ── SECTION 4: SETTINGS ──
                  _buildSuiteItem(
                    icon: Icons.settings_rounded,
                    title: 'Workspace Settings',
                    subtitle: 'Preferences & Accounts',
                    isActive: false,
                    accentColor: const Color(0xFF64748B),
                    isDark: isDark,
                    onTap: () {
                      _safeCloseDrawer(context);
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (context) => const SettingsView()),
                      );
                    },
                  ),
                ],
              ),
            ),

            // 3. AI Upgrade Card (Visible if AI is not yet enabled)
            if (!provider.aiEnabled)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: isDark
                        ? [const Color(0xFF2E1C12), const Color(0xFF1E150F)]
                        : [const Color(0xFFFFF7ED), const Color(0xFFFFEDD5)],
                  ),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: const Color(0xFFFF7A00).withValues(alpha: 0.4),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.auto_awesome, color: Color(0xFFFF7A00), size: 16),
                        SizedBox(width: 6),
                        Text(
                          'VoidMail AI',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFFFF7A00),
                          ),
                        ),
                        Spacer(),
                        Text(
                          'Free',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF10B981),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Get smart summaries, email writer & AI search for your domain.',
                      style: TextStyle(
                        fontSize: 11,
                        color: isDark ? Colors.white60 : Colors.black54,
                      ),
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      height: 32,
                      child: ElevatedButton(
                        onPressed: () {
                          _safeCloseDrawer(context);
                          UpgradeLeadModal.show(context);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFFFF7A00),
                          foregroundColor: Colors.white,
                          padding: EdgeInsets.zero,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                          elevation: 0,
                        ),
                        child: const Text(
                          'Request Free Upgrade',
                          style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            // 4. Connection Info
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

  Widget _buildSuiteItem({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool isActive,
    required Color accentColor,
    required bool isDark,
    required VoidCallback onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 3),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
          decoration: BoxDecoration(
            color: isActive
                ? accentColor.withValues(alpha: 0.12)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: isActive ? accentColor : accentColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  icon,
                  size: 16,
                  color: isActive ? Colors.white : accentColor,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: isActive ? FontWeight.bold : FontWeight.w600,
                        color: isActive
                            ? accentColor
                            : (isDark ? Colors.white : const Color(0xFF1F2937)),
                      ),
                    ),
                    Text(
                      subtitle,
                      style: TextStyle(
                        fontSize: 10,
                        color: isDark ? Colors.grey[400] : Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
              if (isActive)
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: accentColor,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAliasItem({
    required BuildContext context,
    required String email,
    required bool isPrimary,
    required bool isSelected,
    required bool isDark,
    required Color accentColor,
    required VoidCallback onTap,
    VoidCallback? onDelete,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 2),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected
                ? (isDark ? const Color(0xFF1C140D) : const Color(0xFFFFF7ED))
                : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            border: isSelected
                ? Border.all(color: accentColor.withValues(alpha: 0.3), width: 1)
                : null,
          ),
          child: Row(
            children: [
              Icon(
                isPrimary ? Icons.mark_email_read_rounded : Icons.alternate_email_rounded,
                color: isSelected
                    ? accentColor
                    : (isDark ? Colors.grey[400] : const Color(0xFF4B5563)),
                size: 16,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      email,
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                        color: isSelected
                            ? accentColor
                            : (isDark ? Colors.white : const Color(0xFF1F2937)),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      isPrimary ? 'Primary Sovereign Mailbox' : 'Virtual Alias',
                      style: TextStyle(
                        fontSize: 10,
                        color: isDark ? Colors.grey[400] : Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
              if (isPrimary)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    'Primary',
                    style: TextStyle(
                      fontSize: 9.5,
                      fontWeight: FontWeight.bold,
                      color: accentColor,
                    ),
                  ),
                )
              else if (onDelete != null)
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, size: 16),
                  color: isDark ? Colors.grey[400] : Colors.grey[500],
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                  tooltip: 'Delete Alias',
                  onPressed: onDelete,
                ),
            ],
          ),
        ),
      ),
    );
  }

  void _showAddAliasDialog(BuildContext context, MailProvider provider) {
    showDialog(
      context: context,
      builder: (ctx) => _AddAliasDialog(provider: provider),
    );
  }

  void _showDeleteAliasConfirm(BuildContext context, MailProvider provider, int aliasId, String sourceEmail) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Alias'),
        content: Text('Are you sure you want to delete alias "$sourceEmail"? Emails sent to this address will no longer be received.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final res = await provider.deleteAlias(aliasId, sourceEmail);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(res['message'] ?? 'Alias deleted'),
                    behavior: SnackBarBehavior.floating,
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  void _showLogoutConfirmDialog(BuildContext context, MailProvider provider) {
    final isPrimary = provider.isCurrentAccountPrimary;
    final currentEmail = provider.currentEmail;
    final primaryEmail = provider.primaryAccount?.email ?? 'primary email';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(
              isPrimary ? Icons.logout_rounded : Icons.person_remove_rounded,
              color: isPrimary ? Colors.redAccent : const Color(0xFFFF7A00),
            ),
            const SizedBox(width: 10),
            Text(isPrimary ? 'Logout All Accounts' : 'Logout This Email'),
          ],
        ),
        content: Text(
          isPrimary
              ? 'Logging out of your primary email ($currentEmail) will log out all accounts on this device and return to login.'
              : 'Are you sure you want to log out of $currentEmail?\n\nYou will remain logged in to your primary email ($primaryEmail).',
          style: const TextStyle(fontSize: 13, height: 1.4),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              if (isPrimary) {
                _safeCloseDrawer(context);
                await provider.logoutAll();
                if (context.mounted) {
                  Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
                }
              } else {
                final allLoggedOut = await provider.logout();
                if (context.mounted) {
                  _safeCloseDrawer(context);
                  if (allLoggedOut) {
                    Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Logged out of $currentEmail. Switched to $primaryEmail.'),
                        behavior: SnackBarBehavior.floating,
                      ),
                    );
                  }
                }
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: Text(isPrimary ? 'Logout All' : 'Logout Email'),
          ),
        ],
      ),
    );
  }

  void _showAccountOptionsDialog(BuildContext context, MailProvider provider, ServerConfig acc, int idx) {
    final primary = provider.primaryAccount;
    final isPrimaryAcc = (primary != null && primary.id == acc.id) ||
                         (provider.accounts.isNotEmpty && provider.accounts.first.id == acc.id);
    final isCurrentAcc = provider.currentEmail.toLowerCase() == acc.email.toLowerCase();

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: _getAccountColor(idx),
                    child: Text(
                      acc.email.isNotEmpty ? acc.email[0].toUpperCase() : '?',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          acc.email,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          isPrimaryAcc ? 'Primary Email' : 'Professional Email',
                          style: TextStyle(
                            fontSize: 12,
                            color: isPrimaryAcc ? const Color(0xFFFF7A00) : Colors.grey[600],
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(),
              if (!isCurrentAcc)
                ListTile(
                  leading: const Icon(Icons.swap_horiz_rounded),
                  title: const Text('Switch to this account'),
                  onTap: () {
                    Navigator.pop(ctx);
                    provider.switchAccount(idx);
                    _safeCloseDrawer(context);
                  },
                ),
              ListTile(
                leading: Icon(
                  isPrimaryAcc ? Icons.logout_rounded : Icons.delete_outline_rounded,
                  color: Colors.redAccent,
                ),
                title: Text(
                  isPrimaryAcc ? 'Logout all accounts' : 'Remove / Logout this email',
                  style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.w600),
                ),
                subtitle: Text(
                  isPrimaryAcc
                      ? 'Signs out of all mailboxes and returns to login'
                      : 'Removes this professional account without affecting primary mail',
                  style: TextStyle(fontSize: 11, color: Colors.grey[500]),
                ),
                onTap: () async {
                  Navigator.pop(ctx);
                  if (isPrimaryAcc) {
                    _safeCloseDrawer(context);
                    await provider.logoutAll();
                    if (context.mounted) {
                      Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
                    }
                  } else {
                    final allLoggedOut = await provider.removeAccount(acc.id);
                    if (context.mounted) {
                      _safeCloseDrawer(context);
                      if (allLoggedOut) {
                        Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
                      } else {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Logged out of ${acc.email}'),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      }
                    }
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AddAliasDialog extends StatefulWidget {
  final MailProvider provider;
  const _AddAliasDialog({required this.provider});

  @override
  State<_AddAliasDialog> createState() => _AddAliasDialogState();
}

class _AddAliasDialogState extends State<_AddAliasDialog> {
  final _prefixController = TextEditingController();
  late String _selectedDomain;
  bool _isLoading = false;
  String? _errorMsg;

  @override
  void initState() {
    super.initState();
    _selectedDomain = widget.provider.currentDomain.contains('voidonyx')
        ? 'voidonyx.com'
        : widget.provider.currentDomain;
  }

  @override
  void dispose() {
    _prefixController.dispose();
    super.dispose();
  }

  Future<void> _handleCreate() async {
    final prefix = _prefixController.text.trim().toLowerCase();
    if (prefix.isEmpty) {
      setState(() => _errorMsg = 'Please enter an alias prefix');
      return;
    }
    if (prefix.contains('@') || prefix.contains(' ')) {
      setState(() => _errorMsg = 'Prefix should not contain "@" or spaces');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMsg = null;
    });

    final result = await widget.provider.createAlias(prefix, domain: _selectedDomain);

    if (!mounted) return;

    setState(() => _isLoading = false);

    if (result['success'] == true) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle_rounded, color: Colors.white, size: 16),
              const SizedBox(width: 8),
              Text('Alias $prefix@$_selectedDomain saved!'),
            ],
          ),
          backgroundColor: const Color(0xFF10B981),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      setState(() {
        _errorMsg = result['message'] ?? 'Failed to create alias';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: const Row(
        children: [
          Icon(Icons.alternate_email_rounded, color: Color(0xFFFF7A00), size: 22),
          SizedBox(width: 8),
          Text('Add Email Alias', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Emails sent to this alias will automatically arrive in your primary inbox (${widget.provider.currentEmail}).',
              style: TextStyle(
                fontSize: 12,
                color: isDark ? Colors.grey[400] : Colors.grey[600],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextField(
                    controller: _prefixController,
                    autofocus: true,
                    decoration: InputDecoration(
                      hintText: 'e.g. support, billing',
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 2,
                  child: DropdownButtonFormField<String>(
                    value: _selectedDomain,
                    isExpanded: true,
                    decoration: InputDecoration(
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    items: [
                      const DropdownMenuItem(value: 'voidonyx.com', child: Text('@voidonyx.com', style: TextStyle(fontSize: 11))),
                      const DropdownMenuItem(value: 'voidonyx.in', child: Text('@voidonyx.in', style: TextStyle(fontSize: 11))),
                      if (!['voidonyx.com', 'voidonyx.in'].contains(widget.provider.currentDomain))
                        DropdownMenuItem(value: widget.provider.currentDomain, child: Text('@${widget.provider.currentDomain}', style: const TextStyle(fontSize: 11))),
                    ],
                    onChanged: (val) {
                      if (val != null) setState(() => _selectedDomain = val);
                    },
                  ),
                ),
              ],
            ),
            if (_errorMsg != null) ...[
              const SizedBox(height: 10),
              Text(
                _errorMsg!,
                style: const TextStyle(color: Colors.red, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isLoading ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _isLoading ? null : _handleCreate,
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFFFF7A00),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
          child: _isLoading
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : const Text('Create Alias'),
        ),
      ],
    );
  }
}

