import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/folder.dart';
import '../providers/mail_provider.dart';
import '../widgets/ai_assistant_drawer.dart';
import '../widgets/folder_drawer.dart';
import 'inbox_view.dart';
import 'drive_view.dart';
import 'crm_view.dart';
import 'calendar_view.dart';
import 'security_shield_view.dart';
import 'whatsapp_alerts_view.dart';
import 'settings_view.dart';

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  String _getFolderTitle(MailProvider provider) {
    final count = provider.filteredEmails.length;
    final folder = provider.currentFolder;
    if (provider.showUnifiedInbox) {
      switch (folder) {
        case FolderType.inbox: return 'Primary Mail ($count)';
        case FolderType.unanswered: return 'Primary Unanswered ($count)';
        case FolderType.starred: return 'Primary Starred ($count)';
        case FolderType.sent: return 'Primary Sent ($count)';
        case FolderType.drafts: return 'Primary Drafts ($count)';
        case FolderType.spam: return 'Primary Spam ($count)';
        case FolderType.trash: return 'Primary Trash ($count)';
        case FolderType.archive: return 'Primary Archive ($count)';
        case FolderType.notes: return 'Primary Notes ($count)';
      }
    }
    switch (folder) {
      case FolderType.inbox: return 'Inbox ($count)';
      case FolderType.unanswered: return 'Unanswered ($count)';
      case FolderType.starred: return 'Starred ($count)';
      case FolderType.sent: return 'Sent ($count)';
      case FolderType.drafts: return 'Drafts ($count)';
      case FolderType.spam: return 'Spam ($count)';
      case FolderType.trash: return 'Trash ($count)';
      case FolderType.archive: return 'Archive ($count)';
      case FolderType.notes: return 'Notes ($count)';
    }
  }

  PreferredSizeWidget? _buildAppBar(BuildContext context, MailProvider provider) {
    final activeIndex = provider.activeSuiteIndex;

    // VoidDrive (1), Mini CRM (2), Calendar (3), and Shield (4) provide their own dedicated bespoke headers
    if (activeIndex != 0) {
      return null;
    }

    return AppBar(
      leading: Builder(
        builder: (scaffoldContext) => IconButton(
          icon: const Icon(Icons.menu_rounded),
          onPressed: () => Scaffold.of(scaffoldContext).openDrawer(),
        ),
      ),
      title: FittedBox(
        fit: BoxFit.scaleDown,
        alignment: Alignment.centerLeft,
        child: Text(
          _getFolderTitle(provider),
          style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 18),
        ),
      ),
      actions: [
        if (activeIndex == 0) ...[
          if (provider.isLoading)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0),
              child: Center(
                child: SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: provider.accentColor,
                  ),
                ),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              tooltip: 'Sync IMAP Mailbox',
              onPressed: () => provider.refreshMail(),
            ),
          IconButton(
            icon: Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: provider.accentColor,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.edit_outlined, color: Colors.white, size: 18),
            ),
            onPressed: () {
              Navigator.pushNamed(context, '/compose');
            },
          ),
          const SizedBox(width: 8),
        ] else if (activeIndex == 1) ...[
          IconButton(
            icon: const Icon(Icons.shield_outlined, color: Color(0xFF6366F1)),
            tooltip: 'Zero-Knowledge Encrypted',
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: const Row(
                    children: [
                      Icon(Icons.lock_outline_rounded, color: Color(0xFF6366F1), size: 18),
                      SizedBox(width: 8),
                      Text('🛡️ VoidDrive: Zero-Knowledge Encrypted Storage Active'),
                    ],
                  ),
                  behavior: SnackBarBehavior.floating,
                  backgroundColor: const Color(0xFF1E1B4B),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Settings',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsView()),
              );
            },
          ),
        ] else if (activeIndex == 4) ...[
          IconButton(
            icon: const Icon(Icons.mark_chat_read_rounded, color: Color(0xFF10B981)),
            tooltip: 'WhatsApp VIP Alerts',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const WhatsAppAlertsView()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Settings',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsView()),
              );
            },
          ),
        ] else ...[
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Settings',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsView()),
              );
            },
          ),
        ],
      ],
    );
  }

  Widget _buildDesktopNavigationRail(BuildContext context, MailProvider provider, bool isDark) {
    final activeIndex = provider.activeSuiteIndex;
    final accent = provider.accentColor;

    final suiteItems = [
      (Icons.mail_outline_rounded, Icons.mail_rounded, 'Mail', 0),
      (Icons.cloud_outlined, Icons.cloud_rounded, 'Drive', 1),
      (Icons.leaderboard_outlined, Icons.leaderboard_rounded, 'CRM', 2),
      (Icons.calendar_today_rounded, Icons.calendar_month_rounded, 'Calendar', 3),
      (Icons.shield_outlined, Icons.shield_rounded, 'Shield', 4),
    ];

    return Container(
      width: 76,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF110D24) : const Color(0xFFF9FAFB),
        border: Border(
          right: BorderSide(
            color: isDark ? Colors.white10 : const Color(0xFFE5E7EB),
            width: 1,
          ),
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 12),
            // Logo / Branding Icon
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [accent, accent.withValues(alpha: 0.8)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: accent.withValues(alpha: 0.35),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: const Icon(Icons.mail_rounded, color: Colors.white, size: 24),
            ),
            const SizedBox(height: 20),

            // Suite Navigation Items
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  children: suiteItems.map((item) {
                    final isSelected = activeIndex == item.$4;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () => provider.setActiveSuiteIndex(item.$4),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? accent.withValues(alpha: isDark ? 0.22 : 0.12)
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                isSelected ? item.$2 : item.$1,
                                color: isSelected
                                    ? accent
                                    : (isDark ? Colors.white60 : const Color(0xFF6B7280)),
                                size: 22,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                item.$3,
                                style: GoogleFonts.inter(
                                  fontSize: 10,
                                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                  color: isSelected
                                      ? accent
                                      : (isDark ? Colors.white60 : const Color(0xFF6B7280)),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),

            // Bottom Actions: Folders Drawer, AI Assistant, Settings, Profile Avatar
            Builder(
              builder: (scaffoldCtx) {
                return Column(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.folder_open_rounded),
                      tooltip: 'Folders & Labels',
                      color: isDark ? Colors.white70 : const Color(0xFF4B5563),
                      onPressed: () => Scaffold.of(scaffoldCtx).openDrawer(),
                    ),
                    IconButton(
                      icon: Container(
                        padding: const EdgeInsets.all(5),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF8B5CF6), Color(0xFF6366F1)],
                          ),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(Icons.auto_awesome, color: Colors.white, size: 16),
                      ),
                      tooltip: 'VoidMail AI Assistant',
                      onPressed: () => Scaffold.of(scaffoldCtx).openEndDrawer(),
                    ),
                    IconButton(
                      icon: const Icon(Icons.settings_outlined),
                      tooltip: 'Settings',
                      color: isDark ? Colors.white70 : const Color(0xFF4B5563),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const SettingsView()),
                        );
                      },
                    ),
                    const SizedBox(height: 8),
                    // User Avatar with tooltip
                    Tooltip(
                      message: provider.currentEmail,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(20),
                        onTap: () => Scaffold.of(scaffoldCtx).openDrawer(),
                        child: CircleAvatar(
                          radius: 18,
                          backgroundColor: accent.withValues(alpha: 0.2),
                          child: Text(
                            provider.currentEmail.isNotEmpty
                                ? provider.currentEmail[0].toUpperCase()
                                : 'V',
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              color: accent,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final isDesktop = MediaQuery.of(context).size.width >= 720;

    final bodyStack = IndexedStack(
      index: provider.activeSuiteIndex,
      children: const [
        InboxView(),
        DriveView(),
        CrmView(),
        CalendarView(),
        SecurityShieldView(),
      ],
    );

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        final scaffold = Scaffold.maybeOf(context);
        if (scaffold?.isDrawerOpen ?? false) {
          scaffold?.closeDrawer();
        } else if (scaffold?.isEndDrawerOpen ?? false) {
          scaffold?.closeEndDrawer();
        }
      },
      child: Scaffold(
        drawer: const FolderDrawer(),
        endDrawer: Builder(
          builder: (drawerCtx) => AiAssistantDrawer(
            onClose: () {
              final scaffold = Scaffold.maybeOf(drawerCtx);
              if (scaffold?.isEndDrawerOpen ?? false) {
                scaffold?.closeEndDrawer();
              } else if (Navigator.of(drawerCtx).canPop()) {
                Navigator.of(drawerCtx).pop();
              }
            },
          ),
        ),
        appBar: _buildAppBar(context, provider),
        body: isDesktop
            ? Row(
                children: [
                  _buildDesktopNavigationRail(context, provider, isDark),
                  Expanded(child: bodyStack),
                ],
              )
            : bodyStack,
        bottomNavigationBar: isDesktop
            ? null
            : BottomNavigationBar(
                currentIndex: provider.activeSuiteIndex,
                onTap: (idx) {
                  provider.setActiveSuiteIndex(idx);
                },
                selectedItemColor: provider.accentColor,
                unselectedItemColor: const Color(0xFF9CA3AF),
                type: BottomNavigationBarType.fixed,
                selectedFontSize: 11,
                unselectedFontSize: 11,
                items: const [
                  BottomNavigationBarItem(
                    icon: Icon(Icons.mail_outline_rounded),
                    activeIcon: Icon(Icons.mail_rounded),
                    label: 'Mail',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.cloud_outlined),
                    activeIcon: Icon(Icons.cloud_rounded),
                    label: 'Drive',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.leaderboard_outlined),
                    activeIcon: Icon(Icons.leaderboard_rounded),
                    label: 'CRM',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.calendar_today_rounded),
                    activeIcon: Icon(Icons.calendar_month_rounded),
                    label: 'Calendar',
                  ),
                  BottomNavigationBarItem(
                    icon: Icon(Icons.shield_outlined),
                    activeIcon: Icon(Icons.shield_rounded),
                    label: 'Shield',
                  ),
                ],
              ),
      ),
    );
  }
}
