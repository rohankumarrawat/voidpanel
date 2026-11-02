import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/folder.dart';
import '../models/email_item.dart';
import '../providers/mail_provider.dart';
import '../widgets/email_tile.dart';
import 'email_detail_view.dart';

enum InboxTab { all, aiPriority, primary, social, promotions }

class InboxView extends StatefulWidget {
  const InboxView({super.key});

  @override
  State<InboxView> createState() => _InboxViewState();
}

class _InboxViewState extends State<InboxView> {
  InboxTab _activeTab = InboxTab.all;
  final TextEditingController _searchController = TextEditingController();
  String? _selectedEmailId;

  // Keyword-based email categorization
  static const _socialSenders = [
    'instagram', 'facebook', 'twitter', 'linkedin', 'snapchat', 'tiktok',
    'youtube', 'reddit', 'pinterest', 'whatsapp', 'telegram', 'discord',
    'slack', 'teams', 'zoom', 'meet', 'github', 'gitlab', 'bitbucket',
    'quora', 'medium', 'substack', 'notification', 'noreply', 'no-reply',
  ];
  static const _promoKeywords = [
    'unsubscribe', 'offer', 'sale', 'discount', 'promo', 'deal', 'coupon',
    'marketing', 'newsletter', 'subscription', 'limited time', 'free trial',
    'sponsored', 'advertisement', 'cashback', 'reward', 'upgrade', 'premium',
  ];

  bool _isSocial(dynamic email) {
    final sender = email.senderEmail.toLowerCase();
    final name = email.senderName.toLowerCase();
    return _socialSenders.any((kw) => sender.contains(kw) || name.contains(kw));
  }

  bool _isPromotion(dynamic email) {
    final subject = email.subject.toLowerCase();
    final snippet = email.snippet.toLowerCase();
    final body = email.body.toLowerCase();
    return _promoKeywords.any((kw) => subject.contains(kw) || snippet.contains(kw) || body.contains(kw));
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    var emails = provider.filteredEmails;
    if (provider.currentFolder == FolderType.inbox) {
      switch (_activeTab) {
        case InboxTab.aiPriority:
          emails = emails.where((e) => !e.isRead || e.isAiPriority).toList();
          break;
        case InboxTab.social:
          emails = emails.where((e) => _isSocial(e)).toList();
          break;
        case InboxTab.promotions:
          emails = emails.where((e) => _isPromotion(e)).toList();
          break;
        case InboxTab.primary:
          emails = emails.where((e) => !_isSocial(e) && !_isPromotion(e)).toList();
          break;
        case InboxTab.all:
          break;
      }
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final availableWidth = constraints.maxWidth;
        final isWide = availableWidth >= 700;

        final listPane = Column(
          children: [
            // 1. Search Box Bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1B1638) : const Color(0xFFF3F4F6),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                Icon(Icons.search_rounded, color: isDark ? Colors.grey[400] : const Color(0xFF9CA3AF), size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'Search emails by sender, subject or body...',
                      hintStyle: GoogleFonts.inter(
                        fontSize: 13,
                        color: isDark ? Colors.grey[400] : const Color(0xFF9CA3AF),
                      ),
                      border: InputBorder.none,
                    ),
                    onChanged: (val) => provider.setSearchQuery(val),
                  ),
                ),
                if (_searchController.text.isNotEmpty)
                  GestureDetector(
                    onTap: () {
                      _searchController.clear();
                      provider.setSearchQuery('');
                    },
                    child: Icon(Icons.close_rounded, color: isDark ? Colors.grey[400] : const Color(0xFF6B7280), size: 18),
                  )
                else
                  Icon(Icons.tune_rounded, color: isDark ? Colors.grey[400] : const Color(0xFF6B7280), size: 18),
              ],
            ),
          ),
        ),

        // 2. Modern Category Filter Pills — only shown for Inbox
        if (provider.currentFolder == FolderType.inbox)
        Container(
          height: 44,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: [
              _buildFilterPill('All', InboxTab.all, isDark),
              const SizedBox(width: 8),
              if (Provider.of<MailProvider>(context, listen: false).aiEnabled)
              _buildFilterPill('AI Priority', InboxTab.aiPriority, isDark, icon: Icons.auto_awesome_rounded),
              if (Provider.of<MailProvider>(context, listen: false).aiEnabled)
              const SizedBox(width: 8),
              _buildFilterPill('Primary', InboxTab.primary, isDark),
              const SizedBox(width: 8),
              _buildFilterPill('Social', InboxTab.social, isDark),
              const SizedBox(width: 8),
              _buildFilterPill('Promotions', InboxTab.promotions, isDark),
            ],
          ),
        ),
        const SizedBox(height: 6),

        // 3. Multi-Select Banner
        if (provider.isSelectionMode)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: const Color(0xFF6C5CE7),
            child: Row(
              children: [
                Text(
                  '${provider.selectedEmailIds.length} Selected',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.mark_email_read_rounded, color: Colors.white, size: 20),
                  tooltip: 'Mark Read',
                  onPressed: () => provider.bulkMarkRead(),
                ),
                IconButton(
                  icon: const Icon(Icons.archive_outlined, color: Colors.white, size: 20),
                  tooltip: 'Archive',
                  onPressed: () => provider.bulkArchive(),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, color: Colors.white, size: 20),
                  tooltip: 'Delete',
                  onPressed: () => provider.bulkDelete(),
                ),
              ],
            ),
          ),

        // 4. IMAP Sync Status / Error Banner
        if (provider.lastError != null)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: const Color(0xFFFEF2F2),
            child: Row(
              children: [
                const Icon(Icons.info_outline_rounded, color: Color(0xFFDC2626), size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'IMAP sync notice: ${provider.lastError}',
                    style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF991B1B)),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                TextButton(
                  onPressed: () => provider.refreshMail(),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),

        // Smooth background sync indicator
        if (provider.isLoading)
          const PreferredSize(
            preferredSize: Size.fromHeight(2),
            child: LinearProgressIndicator(
              minHeight: 2,
              backgroundColor: Colors.transparent,
              color: Color(0xFF6C5CE7),
            ),
          ),

        // 5. Email List
        Expanded(
          child: emails.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (provider.isLoading) ...[
                        const SizedBox(
                          width: 32,
                          height: 32,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Color(0xFF6C5CE7),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Syncing mailbox...',
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: isDark ? Colors.grey[300] : const Color(0xFF4B5563),
                          ),
                        ),
                      ] else ...[
                        Icon(
                          Icons.mark_email_read_outlined,
                          size: 56,
                          color: isDark ? const Color(0xFF2C2554) : const Color(0xFFD1D5DB),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'No emails found',
                          style: GoogleFonts.inter(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: isDark ? Colors.grey[300] : const Color(0xFF374151),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Your mailbox is up to date.',
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: isDark ? Colors.grey[500] : const Color(0xFF9CA3AF),
                          ),
                        ),
                      ],
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: emails.length,
                  separatorBuilder: (context, index) => Divider(
                    height: 1,
                    indent: 68,
                    endIndent: 16,
                    color: isDark ? const Color(0xFF2C2554) : const Color(0xFFF3F4F6),
                  ),
                  itemBuilder: (context, index) {
                    final email = emails[index];
                    return EmailTile(
                      email: email,
                      isCurrentPreview: isWide && email.id == _selectedEmailId,
                      onTap: () {
                        provider.markAsRead(email.id);
                        if (isWide) {
                          setState(() {
                            _selectedEmailId = email.id;
                          });
                        } else {
                          Navigator.pushNamed(
                            context,
                            '/email_detail',
                            arguments: email,
                          );
                        }
                      },
                    );
                  },
                ),
        ),
      ],
    );

        if (!isWide) {
          return listPane;
        }

        EmailItem? selectedEmail;
        if (_selectedEmailId != null) {
          try {
            selectedEmail = emails.firstWhere((e) => e.id == _selectedEmailId);
          } catch (_) {
            try {
              selectedEmail = provider.emails.firstWhere((e) => e.id == _selectedEmailId);
            } catch (_) {
              selectedEmail = null;
            }
          }
        }
        if (selectedEmail == null && emails.isNotEmpty) {
          selectedEmail = emails.first;
          _selectedEmailId = selectedEmail.id;
        }

        return Row(
          children: [
            SizedBox(
              width: availableWidth > 1100 ? 420 : (availableWidth > 850 ? 380 : 340),
              child: listPane,
            ),
            VerticalDivider(
              width: 1,
              thickness: 1,
              color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
            ),
            Expanded(
              child: selectedEmail != null
                  ? EmailDetailView(
                      key: ValueKey(selectedEmail.id),
                      email: selectedEmail,
                      isEmbedded: true,
                      onClose: () {
                        setState(() {
                          _selectedEmailId = null;
                        });
                      },
                    )
                  : _buildEmptyReadingPane(isDark),
            ),
          ],
        );
      },
    );
  }

  Widget _buildEmptyReadingPane(bool isDark) {
    return Container(
      color: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF8FAFC),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isDark ? const Color(0xFF1E1638) : const Color(0xFFFFF7ED),
                  border: Border.all(
                    color: const Color(0xFFFF7A00).withValues(alpha: 0.35),
                    width: 2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFFFF7A00).withValues(alpha: 0.15),
                      blurRadius: 18,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.mark_email_read_outlined,
                  size: 38,
                  color: Color(0xFFFF7A00),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'No Email Selected',
                style: GoogleFonts.outfit(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
              ),
              const SizedBox(height: 8),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 380),
                child: Text(
                  'Select an email from the left pane to preview details, conversations, and AI actions.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    height: 1.5,
                    color: isDark ? Colors.white60 : const Color(0xFF64748B),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/compose');
                },
                icon: const Icon(Icons.edit_outlined, size: 16),
                label: Text(
                  'Compose Message',
                  style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 13),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFF7A00),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFilterPill(String label, InboxTab tab, bool isDark, {IconData? icon}) {
    final isActive = _activeTab == tab;
    return GestureDetector(
      onTap: () => setState(() => _activeTab = tab),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isActive
                ? const Color(0xFFEEF0FF)
                : (isDark ? const Color(0xFF1B1638) : const Color(0xFFF3F4F6)),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: isActive ? const Color(0xFF6366F1) : Colors.transparent,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 14, color: isActive ? const Color(0xFF4F46E5) : const Color(0xFF6B7280)),
                const SizedBox(width: 6),
              ],
              Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: isActive ? FontWeight.bold : FontWeight.w600,
                  color: isActive
                      ? const Color(0xFF4F46E5)
                      : (isDark ? Colors.grey[300] : const Color(0xFF475569)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
