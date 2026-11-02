import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import '../providers/mail_provider.dart';
import '../widgets/upgrade_lead_modal.dart';

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

class _ComposeViewState extends State<ComposeView> {
  final List<String> _recipients = [];
  final List<String> _ccRecipients = [];
  final List<String> _bccRecipients = [];

  late final TextEditingController _toController;
  late final TextEditingController _ccController;
  late final TextEditingController _bccController;
  late final TextEditingController _subjectController;
  late final TextEditingController _bodyController;
  late final TextEditingController _aiPromptController;

  String? _selectedSenderEmail;

  bool _showCc = false;
  bool _showBcc = false;
  bool _isSending = false;
  bool _isHtmlMode = false;

  // Attachments
  final List<PlatformFile> _attachments = [];

  // AI & Subject Generation
  bool _showAiPanel = false;
  bool _aiGenerating = false;
  bool _isPolishing = false;
  bool _isGeneratingSubject = false;

  @override
  void initState() {
    super.initState();
    _toController = TextEditingController();
    _ccController = TextEditingController();
    _bccController = TextEditingController();
    _subjectController = TextEditingController(text: widget.initialSubject ?? '');
    _bodyController = TextEditingController(text: widget.initialBody ?? '');
    _aiPromptController = TextEditingController();

    if (widget.initialTo != null && widget.initialTo!.trim().isNotEmpty) {
      _addRecipient(widget.initialTo!.trim());
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        final provider = Provider.of<MailProvider>(context, listen: false);
        provider.syncAccountsWithServer().catchError((_) {});
        provider.fetchUserAliases().catchError((_) {});
      }
    });
  }

  @override
  void dispose() {
    _toController.dispose();
    _ccController.dispose();
    _bccController.dispose();
    _subjectController.dispose();
    _bodyController.dispose();
    _aiPromptController.dispose();
    super.dispose();
  }

  void _addRecipient(String text, {String field = 'to'}) {
    final cleaned = text.replaceAll(',', '').replaceAll(' ', '').trim();
    if (cleaned.isNotEmpty && cleaned.contains('@')) {
      setState(() {
        if (field == 'to' && !_recipients.contains(cleaned)) {
          _recipients.add(cleaned);
          _toController.clear();
        } else if (field == 'cc' && !_ccRecipients.contains(cleaned)) {
          _ccRecipients.add(cleaned);
          _ccController.clear();
        } else if (field == 'bcc' && !_bccRecipients.contains(cleaned)) {
          _bccRecipients.add(cleaned);
          _bccController.clear();
        }
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

  void _wrapSelection(String prefix, String suffix) {
    final text = _bodyController.text;
    final sel = _bodyController.selection;
    if (sel.isValid && !sel.isCollapsed) {
      final selectedText = text.substring(sel.start, sel.end);
      final newText = text.replaceRange(sel.start, sel.end, '$prefix$selectedText$suffix');
      _bodyController.text = newText;
      _bodyController.selection = TextSelection(
        baseOffset: sel.start,
        extentOffset: sel.end + prefix.length + suffix.length,
      );
    } else {
      final pos = sel.isValid ? sel.baseOffset : text.length;
      final newText = text.replaceRange(pos, pos, '$prefix$suffix');
      _bodyController.text = newText;
      _bodyController.selection = TextSelection.collapsed(offset: pos + prefix.length);
    }
  }

  void _insertPrefix(String prefix) {
    final text = _bodyController.text;
    final sel = _bodyController.selection;
    final pos = sel.isValid ? sel.baseOffset : text.length;
    final newText = text.replaceRange(pos, pos, '\n$prefix');
    _bodyController.text = newText;
    _bodyController.selection = TextSelection.collapsed(offset: pos + prefix.length + 1);
  }

  void _generateAiSubject() async {
    final bodyText = _bodyController.text.trim();
    if (bodyText.isEmpty && _aiPromptController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Please write email body or enter a prompt first to generate subject.', style: GoogleFonts.inter()),
          behavior: SnackBarBehavior.floating,
          backgroundColor: const Color(0xFFFF7A00),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
      return;
    }

    setState(() => _isGeneratingSubject = true);
    final provider = Provider.of<MailProvider>(context, listen: false);
    final subject = await provider.apiService.generateSubjectLine(
      body: bodyText,
      prompt: _aiPromptController.text.trim(),
    );

    if (mounted) {
      setState(() {
        _isGeneratingSubject = false;
        _subjectController.text = subject;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.auto_awesome_rounded, color: Colors.white, size: 16),
              const SizedBox(width: 8),
              Text('✨ AI Subject generated!', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
            ],
          ),
          behavior: SnackBarBehavior.floating,
          backgroundColor: const Color(0xFF10B981),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
    }
  }

  void _aiCompose() async {
    final prompt = _aiPromptController.text.trim();
    if (prompt.isEmpty) return;

    final provider = Provider.of<MailProvider>(context, listen: false);
    if (!provider.aiEnabled) {
      UpgradeLeadModal.show(context);
      return;
    }

    setState(() => _aiGenerating = true);

    final result = await provider.sendAiQuery(
      'Write an email based on this instruction: "$prompt"\n\n'
      '${_subjectController.text.isNotEmpty ? "Subject: ${_subjectController.text}\n" : ""}'
      '${_recipients.isNotEmpty ? "To: ${_recipients.join(", ")}\n" : ""}'
      '\nWrite ONLY the email body text. Be professional, clear and well-structured.',
      systemPrompt: 'You are Gemini AI for VoidMail. Write concise, executive-grade business emails. Output ONLY the email body text without commentary.',
    );

    if (!mounted) return;
    setState(() {
      _aiGenerating = false;
      if (result['success'] == true) {
        final aiText = result['response'] ?? '';
        if (aiText.isNotEmpty) {
          _bodyController.text = aiText;
          if (_subjectController.text.trim().isEmpty) {
            provider.apiService.generateSubjectLine(body: aiText).then((subj) {
              if (mounted && _subjectController.text.trim().isEmpty && subj.isNotEmpty) {
                setState(() => _subjectController.text = subj);
              }
            });
          }
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

  void _polishDraft() async {
    final draft = _bodyController.text.trim();
    if (draft.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please write draft text before asking AI to polish it.')),
      );
      return;
    }

    setState(() => _isPolishing = true);
    final provider = Provider.of<MailProvider>(context, listen: false);
    final polished = await provider.apiService.polishEmailDraft(draft: draft);
    if (mounted) {
      setState(() {
        _isPolishing = false;
        _bodyController.text = polished;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✨ Draft polished with VoidOnyx AI Engine!')),
      );
    }
  }

  void _openAiTemplateStudio() {
    final controller = TextEditingController();
    bool isGenerating = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Container(
          padding: EdgeInsets.only(
            left: 20, right: 20, top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          decoration: BoxDecoration(
            color: Theme.of(context).brightness == Brightness.dark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6366F1).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.auto_awesome_rounded, color: Color(0xFF6366F1), size: 20),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('AI HTML Template Studio', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 16)),
                        Text('Generate responsive, executive HTML email templates', style: GoogleFonts.inter(fontSize: 11, color: Colors.grey)),
                      ],
                    ),
                  ),
                  IconButton(icon: const Icon(Icons.close_rounded), onPressed: () => Navigator.pop(ctx)),
                ],
              ),
              const SizedBox(height: 14),
              TextField(
                controller: controller,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: 'e.g. "Create a product milestone launch announcement with an orange action button"...',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFFF7A00), width: 1.5)),
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                height: 46,
                child: ElevatedButton.icon(
                  onPressed: isGenerating ? null : () async {
                    final prompt = controller.text.trim();
                    if (prompt.isEmpty) return;
                    setModalState(() => isGenerating = true);
                    final provider = Provider.of<MailProvider>(context, listen: false);
                    final html = await provider.apiService.generateHtmlTemplate(prompt: prompt);
                    if (ctx.mounted) {
                      Navigator.pop(ctx);
                    }
                    if (mounted && html.isNotEmpty) {
                      setState(() {
                        _bodyController.text = html;
                        _isHtmlMode = true;
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('✨ AI HTML Template inserted into editor!')),
                      );
                    }
                  },
                  icon: isGenerating
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.auto_awesome_rounded, size: 16),
                  label: Text(isGenerating ? 'Generating Template...' : 'Generate HTML Template'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFFF7A00),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Map<String, dynamic> _getSenderInfo(String email, MailProvider provider) {
    final cleanEmail = email.trim().toLowerCase();
    final primaryEmail = (provider.primaryAccount?.email ?? provider.currentEmail).trim().toLowerCase();

    if (cleanEmail == primaryEmail) {
      return {
        'type': 'PRIMARY',
        'label': 'Primary Sovereign Mailbox',
        'color': const Color(0xFF10B981),
        'icon': Icons.verified_user_rounded,
        'isPrimary': true,
      };
    }

    final isAlias = provider.userAliases.any(
      (a) => (a['source_email']?.toString() ?? '').trim().toLowerCase() == cleanEmail,
    );
    if (isAlias) {
      return {
        'type': 'ALIAS',
        'label': 'Virtual Sovereign Alias',
        'color': const Color(0xFFF59E0B),
        'icon': Icons.shield_rounded,
        'isPrimary': false,
      };
    }

    return {
      'type': 'BUSINESS',
      'label': 'Linked Business Account',
      'color': const Color(0xFF3B82F6),
      'icon': Icons.business_center_rounded,
      'isPrimary': false,
    };
  }

  void _showSenderPickerSheet(BuildContext context, List<String> availableSenders, MailProvider provider) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.75,
          ),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.3),
                blurRadius: 20,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Drag Handle
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 10, bottom: 6),
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white24 : Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 14),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6366F1).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.alternate_email_rounded, color: Color(0xFF6366F1), size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Select Sending Mailbox',
                            style: GoogleFonts.outfit(
                              fontSize: 16.5,
                              fontWeight: FontWeight.w700,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                          ),
                          Text(
                            'Choose account or sovereign alias for outbound dispatch',
                            style: GoogleFonts.inter(
                              fontSize: 11.5,
                              color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: Icon(Icons.close_rounded, size: 20, color: isDark ? Colors.grey[400] : Colors.grey[600]),
                    ),
                  ],
                ),
              ),

              const Divider(height: 1),

              // Accounts List
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  itemCount: availableSenders.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, idx) {
                    final email = availableSenders[idx];
                    final info = _getSenderInfo(email, provider);
                    final isSelected = (_selectedSenderEmail ?? provider.currentEmail).toLowerCase() == email.toLowerCase();
                    final Color typeColor = info['color'] as Color;

                    return InkWell(
                      onTap: () {
                        setState(() => _selectedSenderEmail = email);
                        Navigator.pop(ctx);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Sending mailbox set to: $email', style: GoogleFonts.inter()),
                            backgroundColor: typeColor,
                            duration: const Duration(seconds: 2),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      },
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? typeColor.withValues(alpha: isDark ? 0.15 : 0.08)
                              : (isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC)),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isSelected ? typeColor : (isDark ? Colors.white10 : const Color(0xFFE2E8F0)),
                            width: isSelected ? 1.5 : 1.0,
                          ),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 38,
                              height: 38,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: LinearGradient(
                                  colors: [typeColor, typeColor.withValues(alpha: 0.75)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                (email.isNotEmpty ? email[0] : 'U').toUpperCase(),
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          email,
                                          style: GoogleFonts.inter(
                                            fontSize: 13.5,
                                            fontWeight: FontWeight.w700,
                                            color: isDark ? Colors.white : const Color(0xFF0F172A),
                                          ),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      const SizedBox(width: 6),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: typeColor.withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(5),
                                          border: Border.all(color: typeColor.withValues(alpha: 0.35)),
                                        ),
                                        child: Text(
                                          info['type'] as String,
                                          style: GoogleFonts.inter(
                                            fontSize: 9.5,
                                            fontWeight: FontWeight.w800,
                                            color: typeColor,
                                            letterSpacing: 0.3,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    info['label'] as String,
                                    style: GoogleFonts.inter(
                                      fontSize: 11,
                                      color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 10),
                            if (isSelected)
                              Icon(Icons.check_circle_rounded, color: typeColor, size: 22)
                            else
                              Icon(Icons.radio_button_unchecked_rounded, color: isDark ? Colors.grey[600] : Colors.grey[400], size: 20),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),

              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.shield_outlined, size: 14, color: Color(0xFF10B981)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'SPF, DKIM, and DMARC sovereign certificates are automatically authenticated per selected sender mailbox.',
                          style: GoogleFonts.inter(fontSize: 10.5, color: isDark ? Colors.grey[400] : const Color(0xFF475569)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _showInsertLinkDialog() {
    final sel = _bodyController.selection;
    String initialText = '';
    if (sel.isValid && !sel.isCollapsed && sel.start < _bodyController.text.length && sel.end <= _bodyController.text.length) {
      initialText = _bodyController.text.substring(sel.start, sel.end).trim();
    }

    final textCtrl = TextEditingController(text: initialText);
    final urlCtrl = TextEditingController();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(
                  color: const Color(0xFF4F46E5).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.link_rounded, color: Color(0xFF4F46E5), size: 20),
              ),
              const SizedBox(width: 10),
              Text(
                'Insert Hyperlink',
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w700),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Display Text',
                  style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey[600]),
                ),
                const SizedBox(height: 6),
                TextField(
                  controller: textCtrl,
                  decoration: InputDecoration(
                    hintText: 'e.g., Click here or Visit our website',
                    hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[400]),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    filled: true,
                    fillColor: isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(color: isDark ? Colors.grey[800]! : const Color(0xFFE2E8F0)),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  'Web Address (URL)',
                  style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey[600]),
                ),
                const SizedBox(height: 6),
                TextField(
                  controller: urlCtrl,
                  keyboardType: TextInputType.url,
                  decoration: InputDecoration(
                    hintText: 'https://example.com or mailto:user@domain.com',
                    hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[400]),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    filled: true,
                    fillColor: isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(color: isDark ? Colors.grey[800]! : const Color(0xFFE2E8F0)),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Quick Presets:',
                  style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.grey[500]),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _buildLinkPresetChip('https://', 'https://', textCtrl, urlCtrl),
                    _buildLinkPresetChip('mailto:', 'mailto:', textCtrl, urlCtrl),
                    _buildLinkPresetChip('Company Website', 'https://voidonyx.in', textCtrl, urlCtrl),
                    _buildLinkPresetChip('Google Meet', 'https://meet.google.com/new', textCtrl, urlCtrl),
                    _buildLinkPresetChip('Drive Files', 'https://voidonyx.in/drive', textCtrl, urlCtrl),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text('Cancel', style: GoogleFonts.inter(color: Colors.grey[600])),
            ),
            ElevatedButton(
              onPressed: () {
                var url = urlCtrl.text.trim();
                var label = textCtrl.text.trim();
                if (url.isEmpty) return;

                if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('mailto:')) {
                  if (url.contains('@') && !url.contains('/')) {
                    url = 'mailto:$url';
                  } else {
                    url = 'https://$url';
                  }
                }
                if (label.isEmpty) {
                  label = url;
                }

                final linkMarkdown = '[$label]($url)';
                final text = _bodyController.text;
                if (sel.isValid && !sel.isCollapsed && sel.start < text.length && sel.end <= text.length) {
                  final newText = text.replaceRange(sel.start, sel.end, linkMarkdown);
                  _bodyController.text = newText;
                  _bodyController.selection = TextSelection.collapsed(offset: sel.start + linkMarkdown.length);
                } else {
                  final pos = sel.isValid ? sel.baseOffset : text.length;
                  final newText = text.replaceRange(pos, pos, linkMarkdown);
                  _bodyController.text = newText;
                  _bodyController.selection = TextSelection.collapsed(offset: pos + linkMarkdown.length);
                }

                Navigator.pop(ctx);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Hyperlink inserted: $label', style: GoogleFonts.inter()),
                    backgroundColor: const Color(0xFF4F46E5),
                    duration: const Duration(seconds: 2),
                    behavior: SnackBarBehavior.floating,
                  ),
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4F46E5),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: Text('Insert Link', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLinkPresetChip(String label, String url, TextEditingController textCtrl, TextEditingController urlCtrl) {
    return InkWell(
      onTap: () {
        if (url == 'https://' || url == 'mailto:') {
          if (!urlCtrl.text.startsWith(url)) {
            urlCtrl.text = url;
            urlCtrl.selection = TextSelection.collapsed(offset: url.length);
          }
          return;
        }
        if (textCtrl.text.trim().isEmpty) {
          textCtrl.text = label;
        }
        urlCtrl.text = url;
        urlCtrl.selection = TextSelection.collapsed(offset: url.length);
      },
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: const Color(0xFFEEF2FF),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: const Color(0xFFC7D2FE)),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600, color: const Color(0xFF4338CA)),
        ),
      ),
    );
  }

  void _showSnippetsPicker() async {
    final provider = Provider.of<MailProvider>(context, listen: false);
    final snippets = await provider.apiService.fetchSnippets();
    if (!mounted) return;

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.bolt_rounded, color: Color(0xFFFF7A00)),
                const SizedBox(width: 8),
                Text('Quick Operations & Snippets', style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            ...snippets.map((snip) => ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF7A00).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(snip.shortcut, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFFFF7A00))),
              ),
              title: Text(snip.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              subtitle: Text(snip.content, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
              onTap: () {
                Navigator.pop(ctx);
                final current = _bodyController.text;
                _bodyController.text = current.isEmpty ? snip.content : '$current\n\n${snip.content}';
              },
            )),
          ],
        ),
      ),
    );
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

  Future<void> _handleSend() async {
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
          content: Text('Please add at least one recipient email address', style: GoogleFonts.inter()),
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

    setState(() => _isSending = true);

    // Pre-send Quanta & Layer 11 Cyber-AI Writing DNA wire guard check
    if (body.length > 25) {
      final senderAddr = _selectedSenderEmail ?? provider.currentEmail;
      final stylometry = await provider.apiService.scanStylometryText(
        emailText: body,
        sender: senderAddr,
      );

      final isBlocked = stylometry['is_synthetic_persona'] == true ||
          (stylometry['risk_level'] == 'HIGH_RISK' &&
              ((stylometry['similarity_score'] as num?)?.toDouble() ?? 100.0) < 45.0);

      if (isBlocked) {
        if (!mounted) return;
        setState(() => _isSending = false);
        _showSecurityInterceptDialog(
          layer: 'Layer 11 (Cyber-AI Defense)',
          score: ((stylometry['similarity_score'] as num?)?.toDouble() ?? 18.0),
          reason: 'Synthetic AI Persona detected. Outbound dispatch dropped on the wire to protect executive credentials.',
          diagnostics: List<String>.from(stylometry['diagnostics'] ?? []),
        );
        return;
      }
    }

    if (!mounted) return;

    provider.sendEmailInBackground(
      to: recipientStr,
      subject: subject,
      body: body,
      fromSender: _selectedSenderEmail,
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
        backgroundColor: const Color(0xFFFF5C00),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );

    Navigator.pop(context);
  }

  void _showSecurityInterceptDialog({
    required String layer,
    required double score,
    required String reason,
    required List<String> diagnostics,
  }) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dlgCtx) {
        final isDark = Theme.of(dlgCtx).brightness == Brightness.dark;
        return Dialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          backgroundColor: isDark ? const Color(0xFF0F172A) : Colors.white,
          child: Padding(
            padding: const EdgeInsets.all(22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.shield_rounded, color: Color(0xFFEF4444), size: 26),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '🛡️ Outbound Intercepted',
                            style: GoogleFonts.outfit(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              color: const Color(0xFFEF4444),
                            ),
                          ),
                          Text(
                            layer,
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: const Color(0xFFF97316),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Persona Match: $score%',
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                          color: const Color(0xFFEF4444),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF4444),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text(
                          'BLOCKED (403)',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  reason,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF334155),
                    height: 1.4,
                  ),
                ),
                if (diagnostics.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    'Forensic Anomalies Triggered:',
                    style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  ...diagnostics.map((d) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('• ', style: TextStyle(color: Color(0xFFEF4444), fontWeight: FontWeight.bold)),
                            Expanded(
                              child: Text(
                                d,
                                style: GoogleFonts.inter(fontSize: 11, color: isDark ? Colors.white70 : Colors.black87),
                              ),
                            ),
                          ],
                        ),
                      )),
                ],
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  height: 42,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF0F172A),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: () => Navigator.pop(dlgCtx),
                    child: const Text('Review & Revise Draft', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final provider = Provider.of<MailProvider>(context);
    final availableSenders = provider.availableSenderEmails;
    if (_selectedSenderEmail == null || !availableSenders.contains(_selectedSenderEmail)) {
      _selectedSenderEmail = availableSenders.isNotEmpty ? availableSenders.first : provider.currentEmail;
    }
    final currentSender = _selectedSenderEmail ?? (availableSenders.isNotEmpty ? availableSenders.first : provider.currentEmail);
    final senderInfo = _getSenderInfo(currentSender, provider);

    return CallbackShortcuts(
      bindings: <ShortcutActivator, VoidCallback>{
        const SingleActivator(LogicalKeyboardKey.keyK, control: true): _showInsertLinkDialog,
        const SingleActivator(LogicalKeyboardKey.keyK, meta: true): _showInsertLinkDialog,
        const SingleActivator(LogicalKeyboardKey.keyB, control: true): () => _wrapSelection('**', '**'),
        const SingleActivator(LogicalKeyboardKey.keyB, meta: true): () => _wrapSelection('**', '**'),
        const SingleActivator(LogicalKeyboardKey.keyI, control: true): () => _wrapSelection('*', '*'),
        const SingleActivator(LogicalKeyboardKey.keyI, meta: true): () => _wrapSelection('*', '*'),
        const SingleActivator(LogicalKeyboardKey.keyU, control: true): () => _wrapSelection('<u>', '</u>'),
        const SingleActivator(LogicalKeyboardKey.keyU, meta: true): () => _wrapSelection('<u>', '</u>'),
        const SingleActivator(LogicalKeyboardKey.enter, control: true): () { if (!_isSending) _handleSend(); },
        const SingleActivator(LogicalKeyboardKey.enter, meta: true): () { if (!_isSending) _handleSend(); },
      },
      child: Focus(
        autofocus: true,
        child: Scaffold(
          backgroundColor: isDark ? const Color(0xFF0F172A) : Colors.white,
          body: SafeArea(
        child: Column(
          children: [
            // ══════════════════════════════════════════════════════════════
            // 1. EXECUTIVE COMPOSE HEADER BAR (matching workspace.html)
            // ══════════════════════════════════════════════════════════════
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                border: Border(bottom: BorderSide(color: Colors.white10)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: Color(0xFFFF5C00),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(color: Color(0xFFFF5C00), blurRadius: 6, spreadRadius: 1),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'New Message',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 14.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Flexible(
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'SUPERHUMAN • GEMINI AI',
                          style: GoogleFonts.inter(
                            color: const Color(0xFF94A3B8),
                            fontSize: 9.5,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const Spacer(),
                  InkWell(
                    onTap: () => Navigator.pop(context),
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Icon(Icons.close_rounded, size: 18, color: Colors.white70),
                    ),
                  ),
                ],
              ),
            ),

            // ══════════════════════════════════════════════════════════════
            // 2. FROM STRIP WITH BESPOKE SENDER SELECT & AI BADGE
            // ══════════════════════════════════════════════════════════════
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC),
                border: Border(bottom: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFE2E8F0))),
              ),
              child: Row(
                children: [
                  Text(
                    'FROM:',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: InkWell(
                      onTap: () => _showSenderPickerSheet(context, availableSenders, provider),
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF0F172A) : Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: isDark ? Colors.white12 : const Color(0xFFCBD5E1)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 20,
                              height: 20,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: (senderInfo['color'] as Color).withValues(alpha: 0.9),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                (currentSender.isNotEmpty ? currentSender[0] : 'U').toUpperCase(),
                                style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: Colors.white),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                currentSender,
                                style: GoogleFonts.inter(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w700,
                                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                              decoration: BoxDecoration(
                                color: (senderInfo['color'] as Color).withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: (senderInfo['color'] as Color).withValues(alpha: 0.3)),
                              ),
                              child: Text(
                                senderInfo['type'] as String,
                                style: GoogleFonts.inter(
                                  fontSize: 9,
                                  fontWeight: FontWeight.w800,
                                  color: senderInfo['color'] as Color,
                                  letterSpacing: 0.3,
                                ),
                              ),
                            ),
                            const SizedBox(width: 4),
                            Icon(Icons.keyboard_arrow_down_rounded, size: 18, color: isDark ? Colors.grey[400] : const Color(0xFF64748B)),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3.5),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.auto_awesome_rounded, size: 12, color: Color(0xFF059669)),
                        const SizedBox(width: 4),
                        Text(
                          'AI Enabled',
                          style: GoogleFonts.inter(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w700,
                            color: const Color(0xFF059669),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // ══════════════════════════════════════════════════════════════
            // 3. TO / CC / BCC ROWS WITH EDITABLE CHIPS
            // ══════════════════════════════════════════════════════════════
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFF1F5F9))),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    'TO:',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        ..._recipients.map((email) => _buildRecipientChip(email, () {
                          setState(() => _recipients.remove(email));
                        }, isDark)),
                        ConstrainedBox(
                          constraints: const BoxConstraints(minWidth: 140, maxWidth: 300),
                          child: TextField(
                            controller: _toController,
                            decoration: InputDecoration(
                              hintText: _recipients.isEmpty ? 'Recipients (press Enter or comma)...' : '',
                              hintStyle: GoogleFonts.inter(fontSize: 12.5, color: isDark ? Colors.grey[500] : const Color(0xFF94A3B8)),
                              border: InputBorder.none,
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 4),
                            ),
                            style: GoogleFonts.inter(fontSize: 13, color: isDark ? Colors.white : const Color(0xFF0F172A)),
                            onSubmitted: (val) => _addRecipient(val, field: 'to'),
                            onChanged: (val) {
                              if (val.contains(',') || val.contains(' ')) {
                                _addRecipient(val, field: 'to');
                              }
                            },
                          ),
                        ),
                      ],
                    ),
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _buildRecipientToggleBtn('Cc', _showCc, () => setState(() => _showCc = !_showCc), isDark),
                      const SizedBox(width: 4),
                      _buildRecipientToggleBtn('Bcc', _showBcc, () => setState(() => _showBcc = !_showBcc), isDark),
                    ],
                  ),
                ],
              ),
            ),

            if (_showCc)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
                decoration: BoxDecoration(
                  border: Border(bottom: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFF1F5F9))),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Text(
                      'CC:',
                      style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w800, color: const Color(0xFF64748B)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          ..._ccRecipients.map((email) => _buildRecipientChip(email, () {
                            setState(() => _ccRecipients.remove(email));
                          }, isDark)),
                          ConstrainedBox(
                            constraints: const BoxConstraints(minWidth: 120, maxWidth: 280),
                            child: TextField(
                              controller: _ccController,
                              decoration: InputDecoration(
                                hintText: _ccRecipients.isEmpty ? 'Cc recipients...' : '',
                                hintStyle: GoogleFonts.inter(fontSize: 12.5, color: const Color(0xFF94A3B8)),
                                border: InputBorder.none,
                                isDense: true,
                                contentPadding: const EdgeInsets.symmetric(vertical: 4),
                              ),
                              style: GoogleFonts.inter(fontSize: 13),
                              onSubmitted: (val) => _addRecipient(val, field: 'cc'),
                              onChanged: (val) {
                                if (val.contains(',') || val.contains(' ')) {
                                  _addRecipient(val, field: 'cc');
                                }
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                    InkWell(
                      onTap: () => setState(() => _showCc = false),
                      child: const Icon(Icons.close_rounded, size: 16, color: Colors.grey),
                    ),
                  ],
                ),
              ),

            if (_showBcc)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
                decoration: BoxDecoration(
                  border: Border(bottom: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFF1F5F9))),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Text(
                      'BCC:',
                      style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w800, color: const Color(0xFF64748B)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          ..._bccRecipients.map((email) => _buildRecipientChip(email, () {
                            setState(() => _bccRecipients.remove(email));
                          }, isDark)),
                          ConstrainedBox(
                            constraints: const BoxConstraints(minWidth: 120, maxWidth: 280),
                            child: TextField(
                              controller: _bccController,
                              decoration: InputDecoration(
                                hintText: _bccRecipients.isEmpty ? 'Bcc recipients...' : '',
                                hintStyle: GoogleFonts.inter(fontSize: 12.5, color: const Color(0xFF94A3B8)),
                                border: InputBorder.none,
                                isDense: true,
                                contentPadding: const EdgeInsets.symmetric(vertical: 4),
                              ),
                              style: GoogleFonts.inter(fontSize: 13),
                              onSubmitted: (val) => _addRecipient(val, field: 'bcc'),
                              onChanged: (val) {
                                if (val.contains(',') || val.contains(' ')) {
                                  _addRecipient(val, field: 'bcc');
                                }
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                    InkWell(
                      onTap: () => setState(() => _showBcc = false),
                      child: const Icon(Icons.close_rounded, size: 16, color: Colors.grey),
                    ),
                  ],
                ),
              ),

            // ══════════════════════════════════════════════════════════════
            // 4. SUBJECT FIELD WITH AI SUBJECT GENERATOR
            // ══════════════════════════════════════════════════════════════
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFF1F5F9))),
              ),
              child: Row(
                children: [
                  Text(
                    'SUBJECT:',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: TextField(
                      controller: _subjectController,
                      decoration: InputDecoration(
                        hintText: 'Type email subject...',
                        hintStyle: GoogleFonts.inter(fontSize: 13.5, color: isDark ? Colors.grey[500] : const Color(0xFF94A3B8)),
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(vertical: 6),
                      ),
                      style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: isDark ? Colors.white : const Color(0xFF0F172A)),
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: _isGeneratingSubject ? null : _generateAiSubject,
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6366F1).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF6366F1).withValues(alpha: 0.28)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_isGeneratingSubject)
                            const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF6366F1)))
                          else
                            const Icon(Icons.auto_awesome_rounded, size: 12, color: Color(0xFF6366F1)),
                          const SizedBox(width: 4),
                          Text(
                            'AI Subject',
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: const Color(0xFF6366F1),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (_isHtmlMode) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE0F2FE),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFFBAE6FD)),
                      ),
                      child: Text('</> HTML MODE', style: GoogleFonts.robotoMono(fontSize: 10, fontWeight: FontWeight.w800, color: const Color(0xFF0284C7))),
                    ),
                  ],
                ],
              ),
            ),

            // ══════════════════════════════════════════════════════════════
            // 5. FORMATTING & QUICK OPERATIONS STRIP (Superhuman Grade)
            // ══════════════════════════════════════════════════════════════
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC),
                border: Border(bottom: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFE2E8F0))),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      child: Row(
                        children: [
                          _buildFormatBtn(Icons.format_bold_rounded, 'Bold (Ctrl+B)', () => _wrapSelection('**', '**'), isDark),
                          _buildFormatBtn(Icons.format_italic_rounded, 'Italic (Ctrl+I)', () => _wrapSelection('*', '*'), isDark),
                          _buildFormatBtn(Icons.format_underlined_rounded, 'Underline (Ctrl+U)', () => _wrapSelection('<u>', '</u>'), isDark),
                          _buildFormatBtn(Icons.strikethrough_s_rounded, 'Strikethrough', () => _wrapSelection('~~', '~~'), isDark),
                          _buildToolbarDivider(isDark),
                          _buildFormatBtn(Icons.link_rounded, 'Insert Link (Ctrl+K)', _showInsertLinkDialog, isDark, highlight: true),
                          _buildToolbarDivider(isDark),
                          _buildFormatBtn(Icons.format_list_bulleted_rounded, 'Bullet List', () => _insertPrefix('• '), isDark),
                          _buildFormatBtn(Icons.format_list_numbered_rounded, 'Numbered List', () => _insertPrefix('1. '), isDark),
                          _buildFormatBtn(Icons.format_quote_rounded, 'Quote Block', () => _insertPrefix('> '), isDark),
                          _buildFormatBtn(Icons.code_rounded, 'Code Block', () => _wrapSelection('`', '`'), isDark),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: _showSnippetsPicker,
                    borderRadius: BorderRadius.circular(7),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4.5),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(colors: [Color(0xFFFEF3C7), Color(0xFFFDE68A)]),
                        borderRadius: BorderRadius.circular(7),
                        border: Border.all(color: const Color(0xFFFCD34D)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.bolt_rounded, size: 13, color: Color(0xFFD97706)),
                          const SizedBox(width: 4),
                          Text('Quick Operations', style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w700, color: const Color(0xFF92400E))),
                          const SizedBox(width: 3),
                          const Icon(Icons.add_rounded, size: 10, color: Color(0xFF92400E)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // ══════════════════════════════════════════════════════════════
            // 6. GEMINI AI ASSISTANT PANEL
            // ══════════════════════════════════════════════════════════════
            if (_showAiPanel)
              Container(
                margin: const EdgeInsets.fromLTRB(16, 10, 16, 4),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFF6366F1).withValues(alpha: 0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.auto_awesome_rounded, size: 15, color: Color(0xFF6366F1)),
                        const SizedBox(width: 6),
                        Text('Gemini AI Assistant', style: GoogleFonts.outfit(fontWeight: FontWeight.w700, fontSize: 13, color: const Color(0xFF6366F1))),
                        const Spacer(),
                        GestureDetector(
                          onTap: () => setState(() => _showAiPanel = false),
                          child: Icon(Icons.close_rounded, size: 16, color: isDark ? Colors.grey[400] : const Color(0xFF94A3B8)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF0F172A) : Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: isDark ? Colors.white12 : const Color(0xFFCBD5E1)),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _aiPromptController,
                              decoration: InputDecoration(
                                hintText: 'e.g. "Write a follow-up email about the enterprise proposal"...',
                                hintStyle: GoogleFonts.inter(fontSize: 12, color: Colors.grey[400]),
                                border: InputBorder.none,
                                isDense: true,
                                contentPadding: const EdgeInsets.symmetric(vertical: 10),
                              ),
                              style: GoogleFonts.inter(fontSize: 13),
                              onSubmitted: (_) => _aiCompose(),
                            ),
                          ),
                          const SizedBox(width: 8),
                          _aiGenerating
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF6366F1)))
                              : InkWell(
                                  onTap: _aiCompose,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF4F46E5)]),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Row(
                                      children: [
                                        const Icon(Icons.auto_awesome_rounded, size: 12, color: Colors.white),
                                        const SizedBox(width: 4),
                                        Text('Generate', style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                                      ],
                                    ),
                                  ),
                                ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      child: Row(
                        children: [
                          _buildAiQuickChip('📝 Professional', isDark: isDark),
                          const SizedBox(width: 5),
                          _buildAiQuickChip('🤝 Follow-up', isDark: isDark),
                          const SizedBox(width: 5),
                          _buildAiQuickChip('📋 Meeting Request', isDark: isDark),
                          const SizedBox(width: 5),
                          _buildAiQuickChip('🙏 Thank You', isDark: isDark),
                          const SizedBox(width: 5),
                          _buildAiQuickChip('💡 Sales Pitch', isDark: isDark),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

            // ══════════════════════════════════════════════════════════════
            // 7. MESSAGE CANVAS (Full height, spacious)
            // ══════════════════════════════════════════════════════════════
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: TextField(
                  controller: _bodyController,
                  maxLines: null,
                  expands: true,
                  textAlignVertical: TextAlignVertical.top,
                  decoration: InputDecoration(
                    hintText: 'Write your message here...',
                    hintStyle: GoogleFonts.inter(color: isDark ? Colors.grey[500] : const Color(0xFF94A3B8), fontSize: 14),
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.zero,
                  ),
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    height: 1.65,
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                  ),
                ),
              ),
            ),

            // ══════════════════════════════════════════════════════════════
            // 8. ATTACHMENTS TRAY (matching compose-attachments-tray)
            // ══════════════════════════════════════════════════════════════
            if (_attachments.isNotEmpty)
              Container(
                height: 52,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC),
                  border: Border(top: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFF1F5F9))),
                ),
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: _attachments.length,
                  itemBuilder: (context, idx) {
                    final file = _attachments[idx];
                    return Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF0F172A) : Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(_getFileIcon(file.extension ?? ''), size: 14, color: const Color(0xFF6366F1)),
                          const SizedBox(width: 6),
                          Text(file.name, style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600)),
                          const SizedBox(width: 4),
                          Text('(${_formatFileSize(file.size)})', style: GoogleFonts.inter(fontSize: 9.5, color: Colors.grey)),
                          const SizedBox(width: 4),
                          InkWell(
                            onTap: () => setState(() => _attachments.removeAt(idx)),
                            child: const Icon(Icons.close_rounded, size: 14, color: Colors.grey),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),

            // ══════════════════════════════════════════════════════════════
            // 9. COMPOSE ACTIONS FOOTER BAR (matching compose-footer-bar)
            // ══════════════════════════════════════════════════════════════
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF0F172A) : const Color(0xFFFAFAFA),
                border: Border(top: BorderSide(color: isDark ? Colors.white10 : const Color(0xFFE2E8F0))),
              ),
              child: Row(
                children: [
                  // Left Actions
                  Expanded(
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      child: Row(
                        children: [
                          // High-Contrast Orange Send Button
                          InkWell(
                            onTap: _isSending ? null : _handleSend,
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFF5C00), Color(0xFFEA580C)],
                                ),
                                borderRadius: BorderRadius.circular(10),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFFFF5C00).withValues(alpha: 0.35),
                                    blurRadius: 10,
                                    offset: const Offset(0, 3),
                                  ),
                                ],
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  if (_isSending)
                                    const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                  else ...[
                                    const Icon(Icons.send_rounded, size: 13, color: Colors.white),
                                    const SizedBox(width: 6),
                                    Text('Send', style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.white)),
                                    const SizedBox(width: 6),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: Colors.black.withValues(alpha: 0.22),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text('⌘↵', style: GoogleFonts.inter(fontSize: 10, color: Colors.white70)),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          // Attach Button
                          _buildFooterActionBtn(
                            icon: Icons.attach_file_rounded,
                            label: 'Attach',
                            onTap: _pickAttachment,
                            isDark: isDark,
                            badge: _attachments.isNotEmpty ? '${_attachments.length}' : null,
                          ),
                          const SizedBox(width: 6),
                          // Link Button (Prominent)
                          _buildFooterActionBtn(
                            icon: Icons.link_rounded,
                            label: 'Link',
                            onTap: _showInsertLinkDialog,
                            color: const Color(0xFF3B82F6),
                            isDark: isDark,
                          ),
                          const SizedBox(width: 6),
                          _buildToolbarDivider(isDark),
                          const SizedBox(width: 6),
                          // AI Templates Button
                          _buildFooterActionBtn(
                            icon: Icons.auto_awesome_rounded,
                            label: 'AI Templates',
                            onTap: _openAiTemplateStudio,
                            color: const Color(0xFF6366F1),
                            isDark: isDark,
                          ),
                          const SizedBox(width: 6),
                          // AI Polish Button
                          _buildFooterActionBtn(
                            icon: _isPolishing ? Icons.hourglass_top_rounded : Icons.auto_fix_high_rounded,
                            label: _isPolishing ? 'Polishing...' : 'AI Polish',
                            onTap: _isPolishing ? () {} : _polishDraft,
                            color: const Color(0xFF8B5CF6),
                            isDark: isDark,
                          ),
                          const SizedBox(width: 6),
                          // Gemini Writer Toggle
                          _buildFooterActionBtn(
                            icon: Icons.psychology_rounded,
                            label: 'Gemini AI',
                            onTap: () {
                              if (provider.aiEnabled) {
                                setState(() => _showAiPanel = !_showAiPanel);
                              } else {
                                UpgradeLeadModal.show(context);
                              }
                            },
                            isActive: _showAiPanel,
                            color: const Color(0xFFFF7A00),
                            isDark: isDark,
                          ),
                          const SizedBox(width: 6),
                          // HTML Mode Toggle
                          _buildFooterActionBtn(
                            icon: Icons.code_rounded,
                            label: 'HTML',
                            isActive: _isHtmlMode,
                            onTap: () => setState(() => _isHtmlMode = !_isHtmlMode),
                            isDark: isDark,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  // Discard Draft Button
                  InkWell(
                    onTap: () {
                      _bodyController.clear();
                      _subjectController.clear();
                      _recipients.clear();
                      Navigator.pop(context);
                    },
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        color: isDark ? Colors.white10 : const Color(0xFFF1F5F9),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(Icons.delete_outline_rounded, size: 18, color: isDark ? Colors.grey[400] : const Color(0xFF94A3B8)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  ),
);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // REUSABLE SUB-COMPONENTS MATCHING WORKSPACE.HTML
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildRecipientChip(String email, VoidCallback onRemove, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(email, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(width: 4),
          InkWell(
            onTap: onRemove,
            child: const Icon(Icons.close_rounded, size: 14, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  Widget _buildRecipientToggleBtn(String label, bool isActive, VoidCallback onTap, bool isDark) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: isActive
              ? (const Color(0xFFFF7A00).withValues(alpha: 0.12))
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 12,
            fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
            color: isActive ? const Color(0xFFFF7A00) : const Color(0xFF94A3B8),
          ),
        ),
      ),
    );
  }

  Widget _buildFormatBtn(
    IconData icon,
    String tooltip,
    VoidCallback onTap,
    bool isDark, {
    bool highlight = false,
  }) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.all(5),
          margin: const EdgeInsets.symmetric(horizontal: 1.5),
          decoration: highlight
              ? BoxDecoration(
                  color: const Color(0xFF6366F1).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: const Color(0xFF6366F1).withValues(alpha: 0.35),
                  ),
                )
              : null,
          child: Icon(
            icon,
            size: 16,
            color: highlight
                ? const Color(0xFF6366F1)
                : (isDark ? Colors.grey[300] : const Color(0xFF475569)),
          ),
        ),
      ),
    );
  }

  Widget _buildToolbarDivider(bool isDark) {
    return Container(
      width: 1,
      height: 16,
      color: isDark ? Colors.white12 : const Color(0xFFCBD5E1),
      margin: const EdgeInsets.symmetric(horizontal: 4),
    );
  }

  Widget _buildFooterActionBtn({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    bool isActive = false,
    Color? color,
    String? badge,
    required bool isDark,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
        decoration: BoxDecoration(
          color: isActive
              ? (color ?? const Color(0xFFFF7A00)).withValues(alpha: 0.12)
              : (isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF1F5F9)),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isActive
                ? (color ?? const Color(0xFFFF7A00)).withValues(alpha: 0.4)
                : (isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: isActive
                  ? (color ?? const Color(0xFFFF7A00))
                  : (color ?? (isDark ? Colors.grey[300] : const Color(0xFF475569))),
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: isActive
                    ? (color ?? const Color(0xFFFF7A00))
                    : (isDark ? Colors.white70 : const Color(0xFF334155)),
              ),
            ),
            if (badge != null) ...[
              const SizedBox(width: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: const BoxDecoration(
                  color: Color(0xFFFF7A00),
                  shape: BoxShape.circle,
                ),
                child: Text(badge, style: const TextStyle(fontSize: 8, color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAiQuickChip(String label, {bool isDark = false}) {
    return GestureDetector(
      onTap: () {
        setState(() => _showAiPanel = true);
        final promptText = label.length > 2 ? label.substring(2).trim() : label;
        _aiPromptController.text = 'Write a $promptText email';
        _aiCompose();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF0F172A) : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFF6366F1).withValues(alpha: 0.3)),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: const Color(0xFF6366F1),
          ),
        ),
      ),
    );
  }
}
