import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/folder.dart';
import '../providers/mail_provider.dart';
import '../widgets/email_tile.dart';

enum InboxTab { all, aiPriority, primary, social, promotions }

class InboxView extends StatefulWidget {
  const InboxView({super.key});

  @override
  State<InboxView> createState() => _InboxViewState();
}

class _InboxViewState extends State<InboxView> {
  InboxTab _activeTab = InboxTab.all;
  final TextEditingController _searchController = TextEditingController();

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

    return Column(
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
                    return EmailTile(email: email);
                  },
                ),
        ),
      ],
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
