import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import '../providers/mail_provider.dart';

class ComposeView extends StatefulWidget {
  final String? initialTo;
  final String? initialSubject;
  final String? initialBody;

  const ComposeView({
    super.key,
    this.initialTo,
    this.initialSubject,
    this.initialBody,
  });

  @override
  State<ComposeView> createState() => _ComposeViewState();
}

class _ComposeViewState extends State<ComposeView> with SingleTickerProviderStateMixin {
  final List<String> _recipients = [];
  late final TextEditingController _toController;
  late final TextEditingController _subjectController;
  late final TextEditingController _bodyController;

  bool _showCcBcc = false;
  final _ccController = TextEditingController();
  final _bccController = TextEditingController();
  bool _isSending = false;

  // Attachments
  final List<PlatformFile> _attachments = [];

  // AI Compose
  bool _showAiPanel = false;
  bool _aiGenerating = false;
  final _aiPromptController = TextEditingController();

  // Formatting
  bool _isBold = false;
  bool _isItalic = false;

  // Emoji picker
  bool _showEmojiPicker = false;

  static const List<String> _quickEmojis = [
    '😊', '👍', '🎉', '❤️', '🔥', '✅', '⭐', '💡',
    '📎', '📧', '🙏', '👋', '💪', '🚀', '✨', '😄',
    '🤝', '💼', '📋', '🎯', '💬', '📌', '⚡', '🌟',
  ];

  @override
  void initState() {
    super.initState();
    _toController = TextEditingController();
    _subjectController = TextEditingController(text: widget.initialSubject ?? '');
    _bodyController = TextEditingController(text: widget.initialBody ?? '');

    if (widget.initialTo != null && widget.initialTo!.trim().isNotEmpty) {
      _addRecipient(widget.initialTo!.trim());
    }
  }

  @override
  void dispose() {
    _toController.dispose();
    _subjectController.dispose();
    _bodyController.dispose();
    _ccController.dispose();
    _bccController.dispose();
    _aiPromptController.dispose();
    super.dispose();
  }

  void _addRecipient(String text) {
    final cleaned = text.replaceAll(',', '').replaceAll(' ', '').trim();
    if (cleaned.isNotEmpty && cleaned.contains('@') && !_recipients.contains(cleaned)) {
      setState(() {
        _recipients.add(cleaned);
        _toController.clear();
      });
    }
  }

  void _pickAttachment() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.any,
    );
    if (result != null) {
      setState(() {
        _attachments.addAll(result.files);
      });
    }
  }

  void _pickImage() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.image,
    );
    if (result != null) {
      setState(() {
        _attachments.addAll(result.files);
      });
    }
  }

  void _insertLink() {
    final linkController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('Insert Link', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
        content: TextField(
          controller: linkController,
          decoration: InputDecoration(
            hintText: 'https://example.com',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            prefixIcon: const Icon(Icons.link_rounded),
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              final link = linkController.text.trim();
              if (link.isNotEmpty) {
                final cursorPos = _bodyController.selection.baseOffset;
                final text = _bodyController.text;
                if (cursorPos >= 0) {
                  _bodyController.text = '${text.substring(0, cursorPos)}$link${text.substring(cursorPos)}';
                } else {
                  _bodyController.text = '${_bodyController.text}\n$link';
                }
              }
              Navigator.pop(ctx);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF6C5CE7),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('Insert', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  void _insertEmoji(String emoji) {
    final cursorPos = _bodyController.selection.baseOffset;
    final text = _bodyController.text;
    if (cursorPos >= 0) {
      _bodyController.text = '${text.substring(0, cursorPos)}$emoji${text.substring(cursorPos)}';
      _bodyController.selection = TextSelection.collapsed(offset: cursorPos + emoji.length);
    } else {
      _bodyController.text = '${_bodyController.text}$emoji';
    }
  }

  void _aiCompose() async {
    final prompt = _aiPromptController.text.trim();
    if (prompt.isEmpty) return;

    final provider = Provider.of<MailProvider>(context, listen: false);
    if (!provider.aiEnabled) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('AI features are not enabled. Your domain is not whitelisted.', style: GoogleFonts.inter()),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
      return;
    }

    setState(() => _aiGenerating = true);

    final result = await provider.sendAiQuery(
      'Write an email based on this instruction: "$prompt"\n\n'
      '${_subjectController.text.isNotEmpty ? "Subject: ${_subjectController.text}\n" : ""}'
      '${_recipients.isNotEmpty ? "To: ${_recipients.join(", ")}\n" : ""}'
      '\nWrite ONLY the email body text. Be professional and concise.',
      systemPrompt: 'You are a professional email writing assistant. Write clear, concise, and well-structured emails. Output ONLY the email body text, no subject line or headers.',
    );

    if (!mounted) return;
    setState(() {
      _aiGenerating = false;
      if (result['success'] == true) {
        final aiText = result['response'] ?? '';
        if (aiText.isNotEmpty) {
          _bodyController.text = aiText;
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('AI Error: ${result['error'] ?? "Failed to generate"}', style: GoogleFonts.inter()),
            backgroundColor: const Color(0xFFEF4444),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    });
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1048576) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / 1048576).toStringAsFixed(1)} MB';
  }

  IconData _getFileIcon(String ext) {
    switch (ext.toLowerCase()) {
      case 'pdf': return Icons.picture_as_pdf_rounded;
      case 'doc': case 'docx': return Icons.description_rounded;
      case 'xls': case 'xlsx': return Icons.table_chart_rounded;
      case 'png': case 'jpg': case 'jpeg': case 'gif': case 'webp': return Icons.image_rounded;
      case 'mp4': case 'mov': case 'avi': return Icons.movie_rounded;
      case 'zip': case 'rar': case '7z': return Icons.folder_zip_rounded;
      default: return Icons.insert_drive_file_rounded;
    }
  }

  void _handleSend() {
    // Capture any un-chipped recipient text remaining in the field
    final rawTo = _toController.text.trim();
    if (rawTo.isNotEmpty) {
      _addRecipient(rawTo);
    }

    if (_recipients.isEmpty && rawTo.isNotEmpty && rawTo.contains('@')) {
      _recipients.add(rawTo);
    }

    if (_recipients.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Please add a recipient email address', style: GoogleFonts.inter()),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
      return;
    }

    final provider = Provider.of<MailProvider>(context, listen: false);
    final recipientStr = _recipients.join(', ');
    final subject = _subjectController.text.trim();
    final body = _bodyController.text.trim();

    provider.sendEmailInBackground(
      to: recipientStr,
      subject: subject,
      body: body,
    );

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.send_rounded, color: Colors.white, size: 16),
            const SizedBox(width: 8),
            Text('Sending to $recipientStr...', style: GoogleFonts.inter(color: Colors.white)),
          ],
        ),
        backgroundColor: const Color(0xFF6C5CE7),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );

    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final provider = Provider.of<MailProvider>(context);

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFFAFAFC),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: isDark ? const Color(0xFF0F0C20) : Colors.white,
        surfaceTintColor: Colors.transparent,
        leading: IconButton(
          icon: Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: isDark ? Colors.white10 : const Color(0xFFF3F4F6),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(Icons.close_rounded, size: 18, color: isDark ? Colors.white : const Color(0xFF374151)),
          ),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'New Message',
          style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 20),
        ),
        centerTitle: true,
        actions: [
          if (_isSending)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Center(
                child: SizedBox(
                  width: 20, height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF6C5CE7)),
                ),
              ),
            )
          else
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: GestureDetector(
                onTap: _handleSend,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6C5CE7), Color(0xFF5A49E3)],
                    ),
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF6C5CE7).withOpacity(0.3),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.send_rounded, size: 14, color: Colors.white),
                      const SizedBox(width: 6),
                      Text('Send', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white)),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Header Fields Card
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1B1638) : Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
              ),
              child: Column(
                children: [
                  // To Row
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFF6C5CE7).withOpacity(0.08),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text('To', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: const Color(0xFF6C5CE7))),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: [
                                ..._recipients.map((email) {
                                  return Container(
                                    margin: const EdgeInsets.only(right: 6),
                                    padding: const EdgeInsets.only(left: 10, right: 4, top: 4, bottom: 4),
                                    decoration: BoxDecoration(
                                      gradient: LinearGradient(
                                        colors: [
                                          const Color(0xFF6C5CE7).withOpacity(0.1),
                                          const Color(0xFF6C5CE7).withOpacity(0.05),
                                        ],
                                      ),
                                      borderRadius: BorderRadius.circular(20),
                                      border: Border.all(color: const Color(0xFF6C5CE7).withOpacity(0.2)),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        CircleAvatar(
                                          radius: 10,
                                          backgroundColor: const Color(0xFF6C5CE7),
                                          child: Text(
                                            email[0].toUpperCase(),
                                            style: const TextStyle(fontSize: 9, color: Colors.white, fontWeight: FontWeight.bold),
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        Text(email, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: isDark ? Colors.white : const Color(0xFF4C1D95))),
                                        const SizedBox(width: 4),
                                        GestureDetector(
                                          onTap: () => setState(() => _recipients.remove(email)),
                                          child: const Icon(Icons.close_rounded, size: 14, color: Color(0xFF9CA3AF)),
                                        ),
                                      ],
                                    ),
                                  );
                                }),
                                IntrinsicWidth(
                                  child: TextField(
                                    controller: _toController,
                                    keyboardType: TextInputType.emailAddress,
                                    decoration: InputDecoration(
                                      hintText: _recipients.isEmpty ? 'recipient@domain.com' : 'Add more...',
                                      hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[400]),
                                      border: InputBorder.none,
                                      isDense: true,
                                      contentPadding: const EdgeInsets.symmetric(vertical: 8),
                                    ),
                                    style: GoogleFonts.inter(fontWeight: FontWeight.w500, fontSize: 13),
                                    onSubmitted: (text) => _addRecipient(text),
                                    onChanged: (text) {
                                      if (text.endsWith(' ') || text.endsWith(',')) {
                                        _addRecipient(text);
                                      }
                                    },
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        GestureDetector(
                          onTap: () => setState(() => _showCcBcc = !_showCcBcc),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: _showCcBcc ? const Color(0xFF6C5CE7).withOpacity(0.1) : Colors.transparent,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: const Color(0xFF6C5CE7).withOpacity(0.3)),
                            ),
                            child: Text('Cc/Bcc', style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF6C5CE7), fontWeight: FontWeight.bold)),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Cc/Bcc
                  if (_showCcBcc) ...[
                    Divider(height: 1, color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                    _buildHeaderField('Cc', _ccController, 'cc@domain.com', isDark),
                    Divider(height: 1, color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                    _buildHeaderField('Bcc', _bccController, 'bcc@domain.com', isDark),
                  ],

                  Divider(height: 1, color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),

                  // Subject
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF59E0B).withOpacity(0.08),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text('Subject', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: const Color(0xFFF59E0B))),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: TextField(
                            controller: _subjectController,
                            decoration: InputDecoration(
                              hintText: 'Enter subject...',
                              hintStyle: GoogleFonts.inter(fontSize: 14, color: Colors.grey[400]),
                              border: InputBorder.none,
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 8),
                            ),
                            style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Attachments Preview
            if (_attachments.isNotEmpty)
              Container(
                height: 70,
                margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: _attachments.length,
                  itemBuilder: (context, index) {
                    final file = _attachments[index];
                    final ext = file.extension ?? '';
                    return Container(
                      width: 180,
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1B1638) : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: const Color(0xFF6C5CE7).withOpacity(0.1),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(_getFileIcon(ext), size: 18, color: const Color(0xFF6C5CE7)),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  file.name,
                                  style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600),
                                  overflow: TextOverflow.ellipsis,
                                ),
                                Text(
                                  _formatFileSize(file.size),
                                  style: GoogleFonts.inter(fontSize: 10, color: Colors.grey),
                                ),
                              ],
                            ),
                          ),
                          GestureDetector(
                            onTap: () => setState(() => _attachments.removeAt(index)),
                            child: const Icon(Icons.close_rounded, size: 16, color: Color(0xFF9CA3AF)),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),

            // AI Compose Panel
            if (_showAiPanel)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      const Color(0xFF6C5CE7).withOpacity(0.05),
                      const Color(0xFF818CF8).withOpacity(0.05),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF6C5CE7).withOpacity(0.2)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.auto_awesome_rounded, size: 16, color: Color(0xFF6C5CE7)),
                        const SizedBox(width: 6),
                        Text('AI Email Writer', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold, color: const Color(0xFF6C5CE7))),
                        const Spacer(),
                        GestureDetector(
                          onTap: () => setState(() => _showAiPanel = false),
                          child: const Icon(Icons.close_rounded, size: 16, color: Color(0xFF9CA3AF)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1B1638) : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _aiPromptController,
                              decoration: InputDecoration(
                                hintText: 'e.g. "Write a follow-up email about the project deadline"',
                                hintStyle: GoogleFonts.inter(fontSize: 12, color: Colors.grey[400]),
                                border: InputBorder.none,
                                isDense: true,
                                contentPadding: const EdgeInsets.symmetric(vertical: 10),
                              ),
                              style: GoogleFonts.inter(fontSize: 13),
                              maxLines: 2,
                              minLines: 1,
                              onSubmitted: (_) => _aiCompose(),
                            ),
                          ),
                          const SizedBox(width: 8),
                          _aiGenerating
                            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF6C5CE7)))
                            : GestureDetector(
                                onTap: _aiCompose,
                                child: Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    gradient: const LinearGradient(colors: [Color(0xFF6C5CE7), Color(0xFF818CF8)]),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.auto_awesome_rounded, size: 16, color: Colors.white),
                                ),
                              ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      children: [
                        _buildAiQuickChip('📝 Professional'),
                        _buildAiQuickChip('👋 Friendly'),
                        _buildAiQuickChip('🤝 Follow-up'),
                        _buildAiQuickChip('📋 Meeting Request'),
                        _buildAiQuickChip('🙏 Thank You'),
                      ],
                    ),
                  ],
                ),
              ),

            // Body Area
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1B1638) : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                ),
                child: TextField(
                  controller: _bodyController,
                  maxLines: null,
                  expands: true,
                  textAlignVertical: TextAlignVertical.top,
                  decoration: InputDecoration(
                    hintText: 'Write your message here...',
                    hintStyle: GoogleFonts.inter(color: Colors.grey[400], fontSize: 14),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.all(16),
                  ),
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    height: 1.6,
                    fontWeight: _isBold ? FontWeight.bold : FontWeight.normal,
                    fontStyle: _isItalic ? FontStyle.italic : FontStyle.normal,
                  ),
                ),
              ),
            ),

            // Emoji Picker
            if (_showEmojiPicker)
              Container(
                height: 110,
                margin: const EdgeInsets.symmetric(horizontal: 12),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1B1638) : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                ),
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 8,
                    mainAxisSpacing: 4,
                    crossAxisSpacing: 4,
                  ),
                  itemCount: _quickEmojis.length,
                  itemBuilder: (context, index) {
                    return GestureDetector(
                      onTap: () => _insertEmoji(_quickEmojis[index]),
                      child: Center(
                        child: Text(_quickEmojis[index], style: const TextStyle(fontSize: 22)),
                      ),
                    );
                  },
                ),
              ),

            // Bottom Toolbar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF0F0C20) : Colors.white,
                border: Border(
                  top: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                ),
              ),
              child: Row(
                children: [
                  // Attachment
                  _buildToolbarButton(
                    icon: Icons.attach_file_rounded,
                    tooltip: 'Attach File',
                    onTap: _pickAttachment,
                    badge: _attachments.isNotEmpty ? '${_attachments.length}' : null,
                    isDark: isDark,
                  ),
                  const SizedBox(width: 4),
                  // Image
                  _buildToolbarButton(
                    icon: Icons.image_outlined,
                    tooltip: 'Attach Image',
                    onTap: _pickImage,
                    isDark: isDark,
                  ),
                  const SizedBox(width: 4),
                  // Link
                  _buildToolbarButton(
                    icon: Icons.link_rounded,
                    tooltip: 'Insert Link',
                    onTap: _insertLink,
                    isDark: isDark,
                  ),
                  const SizedBox(width: 4),
                  // Emoji
                  _buildToolbarButton(
                    icon: Icons.sentiment_satisfied_alt_rounded,
                    tooltip: 'Emoji',
                    onTap: () => setState(() => _showEmojiPicker = !_showEmojiPicker),
                    isActive: _showEmojiPicker,
                    isDark: isDark,
                  ),
                  const SizedBox(width: 4),

                  // Divider
                  Container(width: 1, height: 24, color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                  const SizedBox(width: 4),

                  // AI Writer
                  if (provider.aiEnabled)
                    _buildToolbarButton(
                      icon: Icons.auto_awesome_rounded,
                      tooltip: 'AI Write',
                      onTap: () => setState(() => _showAiPanel = !_showAiPanel),
                      isActive: _showAiPanel,
                      color: const Color(0xFF6C5CE7),
                      isDark: isDark,
                    ),

                  const Spacer(),

                  // Send Button
                  GestureDetector(
                    onTap: _isSending ? null : _handleSend,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF6C5CE7), Color(0xFF5A49E3)],
                        ),
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF6C5CE7).withOpacity(0.3),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.send_rounded, size: 15, color: Colors.white),
                          const SizedBox(width: 6),
                          Text('Send', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white)),
                        ],
                      ),
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

  Widget _buildHeaderField(String label, TextEditingController controller, String hint, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF6C5CE7).withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(label, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: const Color(0xFF6C5CE7))),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: TextField(
              controller: controller,
              decoration: InputDecoration(
                hintText: hint,
                hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[400]),
                border: InputBorder.none,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
              ),
              style: GoogleFonts.inter(fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToolbarButton({
    required IconData icon,
    required String tooltip,
    required VoidCallback onTap,
    bool isActive = false,
    Color? color,
    String? badge,
    required bool isDark,
  }) {
    return Tooltip(
      message: tooltip,
      child: GestureDetector(
        onTap: onTap,
        child: Stack(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isActive
                    ? const Color(0xFF6C5CE7).withOpacity(0.1)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                icon,
                size: 20,
                color: isActive
                    ? const Color(0xFF6C5CE7)
                    : (color ?? (isDark ? Colors.grey[400] : Colors.grey[600])),
              ),
            ),
            if (badge != null)
              Positioned(
                right: 0,
                top: 0,
                child: Container(
                  padding: const EdgeInsets.all(3),
                  decoration: const BoxDecoration(
                    color: Color(0xFF6C5CE7),
                    shape: BoxShape.circle,
                  ),
                  child: Text(badge, style: const TextStyle(fontSize: 8, color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildAiQuickChip(String label) {
    return GestureDetector(
      onTap: () {
        _aiPromptController.text = label.substring(2).trim();
        _aiCompose();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFF6C5CE7).withOpacity(0.2)),
        ),
        child: Text(label, style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w500, color: const Color(0xFF4C1D95))),
      ),
    );
  }
}
