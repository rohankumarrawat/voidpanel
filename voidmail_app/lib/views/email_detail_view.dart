import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import '../models/email_item.dart';
import '../models/folder.dart';
import '../providers/mail_provider.dart';

class EmailDetailView extends StatefulWidget {
  const EmailDetailView({super.key});

  @override
  State<EmailDetailView> createState() => _EmailDetailViewState();
}

class _EmailDetailViewState extends State<EmailDetailView> {
  final TextEditingController _replyController = TextEditingController();
  bool _isReplying = false;

  // AI Suggested Reply state
  String _aiReplyText = '';
  bool _aiReplyLoading = false;
  String _aiReplyError = '';
  String _selectedTone = 'Professional';
  bool _aiReplyFetched = false;

  void _fetchAiReply(EmailItem email, {String tone = 'Professional'}) async {
    final provider = Provider.of<MailProvider>(context, listen: false);
    if (!provider.aiEnabled) return;

    setState(() {
      _aiReplyLoading = true;
      _aiReplyError = '';
      _selectedTone = tone;
    });

    final result = await provider.getAiReplySuggestion(
      originalEmail: '${email.subject}\n\n${email.body}',
      senderName: email.senderName,
      tone: tone.toLowerCase(),
    );

    if (!mounted) return;
    setState(() {
      _aiReplyLoading = false;
      _aiReplyFetched = true;
      if (result['success'] == true) {
        _aiReplyText = result['response'] ?? 'No suggestion generated.';
      } else {
        _aiReplyError = result['error'] ?? 'Failed to generate AI reply.';
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final email = ModalRoute.of(context)!.settings.arguments as EmailItem;
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final initial = email.senderName.isNotEmpty
        ? email.senderName.characters.first.toUpperCase()
        : '?';

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : Colors.white,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: Icon(
              email.isStarred ? Icons.star_rounded : Icons.star_outline_rounded,
              color: email.isStarred ? const Color(0xFFF59E0B) : Colors.grey,
            ),
            onPressed: () => provider.toggleStar(email.id),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline_rounded),
            onPressed: () {
              provider.deleteEmail(email.id);
              Navigator.pop(context);
            },
          ),
          IconButton(
            icon: const Icon(Icons.archive_outlined),
            onPressed: () {
              provider.moveEmailToFolder(email.id, FolderType.archive);
              Navigator.pop(context);
            },
          ),
          IconButton(
            icon: const Icon(Icons.mark_email_unread_outlined),
            onPressed: () {
              provider.toggleRead(email.id);
              Navigator.pop(context);
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Subject Header
                    Text(
                      email.subject,
                      style: GoogleFonts.inter(
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        color: isDark ? Colors.white : const Color(0xFF1E1B4B),
                      ),
                    ),
                    const SizedBox(height: 10),

                    // Folder Badge (`Inbox`)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6C5CE7),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        email.folder.name.toUpperCase(),
                        style: GoogleFonts.inter(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),

                    const SizedBox(height: 20),

                    // Sender Header Card
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF16122E) : const Color(0xFFFAF9FF),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEFEFF6),
                        ),
                      ),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 20,
                            backgroundColor: email.avatarColor,
                            child: Text(
                              initial,
                              style: GoogleFonts.inter(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  email.senderName,
                                  style: GoogleFonts.inter(
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                    color: isDark ? Colors.white : const Color(0xFF1E1B4B),
                                  ),
                                ),
                                Text(
                                  '<${email.senderEmail}>',
                                  style: GoogleFonts.inter(
                                    fontSize: 11,
                                    color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                          Text(
                            DateFormat('MMM d, h:mm a').format(email.timestamp),
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 20),

                    // ── Email Body ──
                    if (email.htmlBody != null && email.htmlBody!.trim().isNotEmpty)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF16122E) : Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5),
                          ),
                        ),
                        child: HtmlWidget(
                          email.htmlBody!,
                          textStyle: GoogleFonts.inter(
                            fontSize: 14,
                            height: 1.6,
                            color: isDark ? Colors.grey[300] : const Color(0xFF1E1B4B),
                          ),
                        ),
                      )
                    else
                      SelectableText(
                        email.body.isNotEmpty
                            ? email.body
                            : '(No message content)',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          height: 1.6,
                          color: isDark ? Colors.grey[300] : const Color(0xFF1E1B4B),
                        ),
                      ),

                    const SizedBox(height: 24),

                    // AI Suggested Reply Card — calls VoidOnyx AI in real-time
                    if (provider.aiEnabled)
                    Builder(
                      builder: (context) {
                        // Auto-fetch on first render
                        if (!_aiReplyFetched && !_aiReplyLoading) {
                          WidgetsBinding.instance.addPostFrameCallback((_) {
                            _fetchAiReply(email);
                          });
                        }

                        return Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: isDark ? const Color(0xFF1F1A42) : const Color(0xFFF4F2FF),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(
                              color: isDark ? const Color(0xFF4F46E5) : const Color(0xFFC7D2FE),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Flexible(
                                    child: Text(
                                      'AI Suggested Reply',
                                      style: GoogleFonts.inter(
                                        fontSize: 13,
                                        fontWeight: FontWeight.bold,
                                        color: const Color(0xFF4F46E5),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF4F46E5).withOpacity(0.1),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Text(
                                      '✨ AI Powered',
                                      style: GoogleFonts.inter(fontSize: 10, color: const Color(0xFF4F46E5), fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),

                              // AI Reply Content
                              if (_aiReplyLoading)
                                const Padding(
                                  padding: EdgeInsets.symmetric(vertical: 20),
                                  child: Center(
                                    child: Column(
                                      children: [
                                        SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF4F46E5))),
                                        SizedBox(height: 8),
                                        Text('Generating AI reply...', style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
                                      ],
                                    ),
                                  ),
                                )
                              else if (_aiReplyError.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 10),
                                  child: Column(
                                    children: [
                                      Text(_aiReplyError, style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFFEF4444))),
                                      const SizedBox(height: 8),
                                      TextButton.icon(
                                        onPressed: () => _fetchAiReply(email, tone: _selectedTone),
                                        icon: const Icon(Icons.refresh, size: 14),
                                        label: const Text('Retry'),
                                      ),
                                    ],
                                  ),
                                )
                              else if (_aiReplyText.isNotEmpty)
                                SelectableText(
                                  _aiReplyText,
                                  style: GoogleFonts.inter(fontSize: 13, height: 1.4, color: isDark ? Colors.grey[200] : const Color(0xFF1E1B4B)),
                                )
                              else
                                Text(
                                  'Tap a tone below to generate a reply suggestion.',
                                  style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF94A3B8)),
                                ),

                              const SizedBox(height: 14),

                              // Tone Selection Pills
                              SingleChildScrollView(
                                scrollDirection: Axis.horizontal,
                                child: Row(
                                  children: ['Professional', 'Friendly', 'Short', 'Detailed'].map((tone) {
                                    return Padding(
                                      padding: const EdgeInsets.only(right: 8),
                                      child: GestureDetector(
                                        onTap: () => _fetchAiReply(email, tone: tone),
                                        child: _buildTonePill(tone, _selectedTone == tone, isDark),
                                      ),
                                    );
                                  }).toList(),
                                ),
                              ),
                              const SizedBox(height: 14),

                              // Action Buttons
                              if (_aiReplyText.isNotEmpty)
                              Wrap(
                                spacing: 10,
                                children: [
                                  ElevatedButton.icon(
                                    onPressed: () {
                                      setState(() {
                                        _replyController.text = _aiReplyText;
                                      });
                                    },
                                    icon: const Icon(Icons.download_done_rounded, size: 16, color: Colors.white),
                                    label: Text('Insert Reply', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF4F46E5),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                    ),
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.copy_rounded, size: 18, color: Color(0xFF4F46E5)),
                                    onPressed: () {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text('Copied AI reply to clipboard!'), duration: Duration(seconds: 1)),
                                      );
                                    },
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),

            // Bottom Quick Reply Bar
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF16122E) : Colors.white,
                border: Border(
                  top: BorderSide(
                    color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEFEFF6),
                  ),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Container(
                      height: 44,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1B1638) : const Color(0xFFF3F4F6),
                        borderRadius: BorderRadius.circular(22),
                      ),
                      child: TextField(
                        controller: _replyController,
                        decoration: InputDecoration(
                          hintText: 'Reply to ${email.senderName}...',
                          hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[500]),
                          border: InputBorder.none,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  IconButton(
                    icon: _isReplying
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF6C5CE7)),
                          )
                        : const Icon(Icons.send_rounded, color: Color(0xFF6C5CE7)),
                    onPressed: _isReplying
                        ? null
                        : () async {
                            final replyText = _replyController.text.trim();
                            if (replyText.isEmpty) return;

                            setState(() => _isReplying = true);
                            final res = await provider.sendEmail(
                              to: email.senderEmail,
                              subject: 'Re: ${email.subject}',
                              body: replyText,
                            );

                            if (!mounted) return;
                            setState(() => _isReplying = false);

                            if (res['success'] == true) {
                              _replyController.clear();
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Reply sent successfully! 🚀'),
                                  backgroundColor: Color(0xFF10B981),
                                ),
                              );
                            } else {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('Reply failed: ${res['message']}'),
                                  backgroundColor: const Color(0xFFEF4444),
                                ),
                              );
                            }
                          },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTonePill(String label, bool isSelected, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: isSelected
            ? const Color(0xFF4F46E5)
            : (isDark ? const Color(0xFF2C2554) : Colors.white),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isSelected ? const Color(0xFF4F46E5) : const Color(0xFFCBD5E1),
        ),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: isSelected ? Colors.white : (isDark ? Colors.grey[300] : const Color(0xFF475569)),
        ),
      ),
    );
  }
}
