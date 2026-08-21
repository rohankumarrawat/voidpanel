import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/mail_provider.dart';

class AiAssistantDrawer extends StatefulWidget {
  final VoidCallback onClose;
  final Function(String)? onActionTap;

  const AiAssistantDrawer({
    super.key,
    required this.onClose,
    this.onActionTap,
  });

  @override
  State<AiAssistantDrawer> createState() => _AiAssistantDrawerState();
}

class _AiAssistantDrawerState extends State<AiAssistantDrawer> {
  final TextEditingController _promptController = TextEditingController();
  final List<Map<String, dynamic>> _chatMessages = [];
  bool _isThinking = false;

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  void _sendQuery(String query) async {
    if (query.trim().isEmpty) return;
    setState(() {
      _chatMessages.add({'sender': 'user', 'text': query});
      _isThinking = true;
    });
    _promptController.clear();

    final provider = Provider.of<MailProvider>(context, listen: false);

    if (provider.aiEnabled) {
      // ── Real VoidOnyx AI Gateway call ──
      final result = await provider.sendAiQuery(query);
      if (!mounted) return;

      setState(() {
        _isThinking = false;
        if (result['success'] == true) {
          _chatMessages.add({'sender': 'ai', 'text': result['response'] ?? 'No response.'});
        } else {
          _chatMessages.add({'sender': 'ai', 'text': '⚠️ ${result['error'] ?? "AI request failed."}'});
        }
      });
    } else {
      // ── Fallback mock responses (AI not enabled) ──
      Future.delayed(const Duration(milliseconds: 800), () {
        if (!mounted) return;
        String response = "🔒 AI features are not enabled. Please whitelist your IP in Settings → VoidMail AI Whitelist.";
        if (query.toLowerCase().contains('summar')) {
          response = "✨ **Inbox Summary** (Demo):\n• Instagram security login alert.\n• Rohan sent a project proposal for VoidMail AI.\n• Amazon package arriving on 10 Aug.\n\n_Note: Enable AI via IP whitelist for live responses._";
        } else if (query.toLowerCase().contains('draft')) {
          response = "✍️ Draft (Demo):\n\n'Hi Rohan, thanks for sending the proposal. I'll review and get back to you shortly!'\n\n_Enable AI via IP whitelist for real drafts._";
        }
        setState(() {
          _isThinking = false;
          _chatMessages.add({'sender': 'ai', 'text': response});
        });
      });
    }
  }

  Widget _buildQuickActionCard(IconData icon, String title, String subtitle, Color color) {
    return GestureDetector(
      onTap: () => _sendQuery(title),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFEFEFF6)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.02),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, size: 20, color: color),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF1E1B4B),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      color: const Color(0xFF6B7280),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final drawerWidth = screenWidth < 420 ? screenWidth * 0.85 : 380.0;

    return Container(
      width: drawerWidth,
      decoration: const BoxDecoration(
        color: Color(0xFFF9FAFD),
        border: Border(left: BorderSide(color: Color(0xFFEFEFF6))),
      ),
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Row(
              children: [
                Text(
                  'AI Assistant',
                  style: GoogleFonts.outfit(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF1E1B4B),
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20, color: Color(0xFF6B7280)),
                  onPressed: widget.onClose,
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: Color(0xFFEFEFF6)),

          // Body
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  // Glowing AI Orb Graphic
                  Container(
                    width: 90,
                    height: 90,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const RadialGradient(
                        colors: [Color(0xFF818CF8), Color(0xFF4F46E5), Color(0xFF1E1B4B)],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF6366F1).withOpacity(0.4),
                          blurRadius: 24,
                          spreadRadius: 4,
                        ),
                      ],
                    ),
                    child: Center(
                      child: Container(
                        width: 32,
                        height: 32,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  Text(
                    'Hi Pari! 👋',
                    style: GoogleFonts.outfit(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF1E1B4B),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'How can I help you today?',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      color: const Color(0xFF6B7280),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Chat Messages Stream (If user asked something)
                  if (_chatMessages.isNotEmpty) ...[
                    ..._chatMessages.map((msg) {
                      final isUser = msg['sender'] == 'user';
                      return Align(
                        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: isUser ? const Color(0xFF4F46E5) : Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            border: isUser ? null : Border.all(color: const Color(0xFFEFEFF6)),
                          ),
                          child: Text(
                            msg['text'] ?? '',
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              color: isUser ? Colors.white : const Color(0xFF1E1B4B),
                              height: 1.4,
                            ),
                          ),
                        ),
                      );
                    }),
                    if (_isThinking)
                      const Padding(
                        padding: EdgeInsets.all(12.0),
                        child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF4F46E5)),
                      ),
                    const SizedBox(height: 16),
                  ],

                  // Quick Action Cards matching Screenshot 4
                  _buildQuickActionCard(
                    Icons.summarize_outlined,
                    'Summarize Inbox',
                    'Get a summary of unread emails',
                    const Color(0xFF6366F1),
                  ),
                  _buildQuickActionCard(
                    Icons.edit_note_rounded,
                    'Draft Email',
                    'Write an email with AI',
                    const Color(0xFF8B5CF6),
                  ),
                  _buildQuickActionCard(
                    Icons.search_rounded,
                    'Find Anything',
                    'Search emails, docs, people...',
                    const Color(0xFF3B82F6),
                  ),
                  _buildQuickActionCard(
                    Icons.cleaning_services_outlined,
                    'Clean Inbox',
                    'Organize and declutter',
                    const Color(0xFF10B981),
                  ),
                  _buildQuickActionCard(
                    Icons.reply_all_rounded,
                    'Smart Reply',
                    'Reply to emails with AI',
                    const Color(0xFFEC4899),
                  ),
                ],
              ),
            ),
          ),

          // Bottom Query Input
          Padding(
            padding: const EdgeInsets.all(16),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: const Color(0xFFEFEFF6)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _promptController,
                      style: GoogleFonts.inter(fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'Ask anything...',
                        hintStyle: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF9CA3AF)),
                        border: InputBorder.none,
                      ),
                      onSubmitted: _sendQuery,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.mic_none_rounded, color: Color(0xFF6B7280), size: 20),
                    onPressed: () {},
                  ),
                  GestureDetector(
                    onTap: () => _sendQuery(_promptController.text),
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: LinearGradient(
                          colors: [Color(0xFF6366F1), Color(0xFF4F46E5)],
                        ),
                      ),
                      child: const Icon(Icons.send_rounded, color: Colors.white, size: 16),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
