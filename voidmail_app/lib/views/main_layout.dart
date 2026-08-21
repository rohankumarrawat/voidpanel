import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/folder.dart';
import '../providers/mail_provider.dart';
import '../widgets/ai_assistant_drawer.dart';
import '../widgets/folder_drawer.dart';
import 'inbox_view.dart';
import 'calendar_view.dart';
import 'contacts_view.dart';
import 'settings_view.dart';

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _currentIndex = 0;

  String _getFolderTitle(MailProvider provider) {
    final count = provider.filteredEmails.length;
    final folder = provider.currentFolder;
    if (provider.showUnifiedInbox) {
      switch (folder) {
        case FolderType.inbox: return 'Primary Mail ($count)';
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
      case FolderType.starred: return 'Starred ($count)';
      case FolderType.sent: return 'Sent ($count)';
      case FolderType.drafts: return 'Drafts ($count)';
      case FolderType.spam: return 'Spam ($count)';
      case FolderType.trash: return 'Trash ($count)';
      case FolderType.archive: return 'Archive ($count)';
      case FolderType.notes: return 'Notes ($count)';
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);

    return Scaffold(
      drawer: const FolderDrawer(),
      endDrawer: Builder(
        builder: (context) => AiAssistantDrawer(
          onClose: () => Navigator.pop(context),
        ),
      ),
      appBar: _currentIndex == 0
          ? AppBar(
              leading: Builder(
                builder: (scaffoldContext) => IconButton(
                  icon: const Icon(Icons.menu_rounded),
                  onPressed: () => Scaffold.of(scaffoldContext).openDrawer(),
                ),
              ),
              title: Text(
                _getFolderTitle(provider),
                style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 18),
              ),
              actions: [
                if (provider.isLoading)
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12.0),
                    child: Center(
                      child: SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Color(0xFF6C5CE7),
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
                if (provider.aiEnabled)
                Builder(
                  builder: (scaffoldContext) => IconButton(
                    icon: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6C5CE7).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.auto_awesome_rounded, color: Color(0xFF6C5CE7), size: 20),
                    ),
                    tooltip: 'AI Email Assistant',
                    onPressed: () {
                      Scaffold.of(scaffoldContext).openEndDrawer();
                    },
                  ),
                ),
                IconButton(
                  icon: Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6C5CE7),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.edit_outlined, color: Colors.white, size: 18),
                  ),
                  onPressed: () {
                    Navigator.pushNamed(context, '/compose');
                  },
                ),
                const SizedBox(width: 8),
              ],
            )
          : null,
      body: IndexedStack(
        index: _currentIndex,
        children: const [
          InboxView(),
          CalendarView(),
          ContactsView(),
          SettingsView(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (idx) {
          setState(() {
            _currentIndex = idx;
          });
        },
        selectedItemColor: const Color(0xFF6C5CE7),
        unselectedItemColor: const Color(0xFF9CA3AF),
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.mail_outline_rounded),
            activeIcon: Icon(Icons.mail_rounded),
            label: 'Mail',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.calendar_today_rounded),
            activeIcon: Icon(Icons.calendar_month_rounded),
            label: 'Calendar',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.people_outline_rounded),
            activeIcon: Icon(Icons.people_rounded),
            label: 'Contacts',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings_outlined),
            activeIcon: Icon(Icons.settings_rounded),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}
