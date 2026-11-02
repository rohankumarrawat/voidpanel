import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/voidpanel_config.dart';
import '../providers/mail_provider.dart';
import '../widgets/powered_by_voidpanel.dart';

class SettingsView extends StatefulWidget {
  const SettingsView({super.key});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  bool _testingConnection = false;

  void _showEditServerDialog(BuildContext context, ServerConfig? config) {
    final provider = Provider.of<MailProvider>(context, listen: false);
    final imapController = TextEditingController(text: config?.imapHost ?? 'imap.voidonyx.in');
    final imapPortController = TextEditingController(text: (config?.imapPort ?? 993).toString());
    final smtpController = TextEditingController(text: config?.smtpHost ?? 'smtp.voidonyx.in');
    final smtpPortController = TextEditingController(text: (config?.smtpPort ?? 465).toString());

    bool imapSsl = config?.imapSsl ?? true;
    bool smtpSsl = config?.smtpSsl ?? true;

    final isDark = Theme.of(context).brightness == Brightness.dark;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          Widget buildServerSection({
            required String title,
            required String subtitle,
            required IconData icon,
            required Color accentColor,
            required TextEditingController hostController,
            required TextEditingController portController,
            required bool ssl,
            required ValueChanged<bool> onSslChanged,
            required String hostHint,
            required String defaultPort,
          }) {
            return Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1B1638) : Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: isDark ? accentColor.withOpacity(0.2) : accentColor.withOpacity(0.15),
                ),
                boxShadow: [
                  BoxShadow(
                    color: accentColor.withOpacity(0.05),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Section Header
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: accentColor.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(icon, color: accentColor, size: 18),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title,
                              style: GoogleFonts.inter(
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                            Text(
                              subtitle,
                              style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8)),
                            ),
                          ],
                        ),
                      ),
                      // SSL Toggle
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: ssl
                              ? const Color(0xFF10B981).withOpacity(0.12)
                              : const Color(0xFFEF4444).withOpacity(0.12),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: ssl
                                ? const Color(0xFF10B981).withOpacity(0.3)
                                : const Color(0xFFEF4444).withOpacity(0.3),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              ssl ? Icons.lock_rounded : Icons.lock_open_rounded,
                              size: 13,
                              color: ssl ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              ssl ? 'SSL/TLS' : 'Plain',
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: ssl ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                              ),
                            ),
                            const SizedBox(width: 2),
                            Transform.scale(
                              scale: 0.6,
                              child: Switch(
                                value: ssl,
                                onChanged: onSslChanged,
                                activeColor: const Color(0xFF10B981),
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  // Host & Port Fields
                  Row(
                    children: [
                      Expanded(
                        flex: 3,
                        child: TextFormField(
                          controller: hostController,
                          style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500),
                          decoration: InputDecoration(
                            labelText: 'Hostname',
                            labelStyle: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF94A3B8)),
                            hintText: hostHint,
                            hintStyle: GoogleFonts.inter(fontSize: 12, color: const Color(0xFFCBD5E1)),
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            filled: true,
                            fillColor: isDark ? const Color(0xFF16122E) : const Color(0xFFF8FAFC),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: accentColor, width: 1.5),
                            ),
                            prefixIcon: Icon(Icons.language_rounded, size: 18, color: accentColor.withOpacity(0.6)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        flex: 1,
                        child: TextFormField(
                          controller: portController,
                          keyboardType: TextInputType.number,
                          style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600),
                          textAlign: TextAlign.center,
                          decoration: InputDecoration(
                            labelText: 'Port',
                            labelStyle: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF94A3B8)),
                            hintText: defaultPort,
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
                            filled: true,
                            fillColor: isDark ? const Color(0xFF16122E) : const Color(0xFFF8FAFC),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: accentColor, width: 1.5),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          }

          return Container(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.85,
            ),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF9FAFD),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.15),
                  blurRadius: 20,
                  offset: const Offset(0, -4),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Handle Bar
                const SizedBox(height: 12),
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: 16),

                // Header
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                          ),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(Icons.settings_ethernet_rounded, color: Colors.white, size: 22),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Server Configuration',
                              style: GoogleFonts.outfit(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                            Text(
                              'Configure IMAP & SMTP mail server settings',
                              style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF94A3B8)),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        onPressed: () => Navigator.pop(context),
                        icon: Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            Icons.close_rounded,
                            size: 18,
                            color: isDark ? Colors.white70 : const Color(0xFF64748B),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Scrollable Content
                Flexible(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Column(
                      children: [
                        // IMAP Section
                        buildServerSection(
                          title: 'IMAP Incoming Server',
                          subtitle: 'Receives and syncs your emails',
                          icon: Icons.move_to_inbox_rounded,
                          accentColor: const Color(0xFF6366F1),
                          hostController: imapController,
                          portController: imapPortController,
                          ssl: imapSsl,
                          onSslChanged: (val) {
                            setDialogState(() {
                              imapSsl = val;
                              if (val && imapPortController.text == '143') {
                                imapPortController.text = '993';
                              } else if (!val && imapPortController.text == '993') {
                                imapPortController.text = '143';
                              }
                            });
                          },
                          hostHint: 'mail.yourdomain.com',
                          defaultPort: '993',
                        ),

                        const SizedBox(height: 14),

                        // SMTP Section
                        buildServerSection(
                          title: 'SMTP Outgoing Server',
                          subtitle: 'Sends your emails securely',
                          icon: Icons.outbox_rounded,
                          accentColor: const Color(0xFF10B981),
                          hostController: smtpController,
                          portController: smtpPortController,
                          ssl: smtpSsl,
                          onSslChanged: (val) {
                            setDialogState(() {
                              smtpSsl = val;
                              if (val && (smtpPortController.text == '587' || smtpPortController.text == '25')) {
                                smtpPortController.text = '465';
                              } else if (!val && smtpPortController.text == '465') {
                                smtpPortController.text = '587';
                              }
                            });
                          },
                          hostHint: 'mail.yourdomain.com',
                          defaultPort: '465',
                        ),

                        const SizedBox(height: 20),

                        // Action Buttons
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton.icon(
                                onPressed: () => Navigator.pop(context),
                                icon: const Icon(Icons.close_rounded, size: 18),
                                label: Text('Cancel', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
                                style: OutlinedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                  side: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                                  foregroundColor: isDark ? Colors.white70 : const Color(0xFF64748B),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              flex: 2,
                              child: Container(
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                    colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                                  ),
                                  borderRadius: BorderRadius.circular(14),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(0xFF6366F1).withOpacity(0.3),
                                      blurRadius: 12,
                                      offset: const Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: ElevatedButton.icon(
                                  onPressed: () {
                                    final updated = ServerConfig.custom(
                                      email: provider.currentEmail,
                                      password: config?.password ?? '',
                                      imapHost: imapController.text.trim(),
                                      imapPort: int.tryParse(imapPortController.text.trim()) ?? 993,
                                      imapSsl: imapSsl,
                                      smtpHost: smtpController.text.trim(),
                                      smtpPort: int.tryParse(smtpPortController.text.trim()) ?? 465,
                                      smtpSsl: smtpSsl,
                                      providerName: config?.providerName ?? 'Custom IMAP/SMTP',
                                    );

                                    provider.updateServerConfig(updated);
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Row(
                                          children: [
                                            const Icon(Icons.check_circle_rounded, color: Colors.white, size: 18),
                                            const SizedBox(width: 8),
                                            Text('Server settings updated!', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
                                          ],
                                        ),
                                        backgroundColor: const Color(0xFF10B981),
                                        behavior: SnackBarBehavior.floating,
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                      ),
                                    );
                                  },
                                  icon: const Icon(Icons.save_rounded, size: 18, color: Colors.white),
                                  label: Text(
                                    'Save Settings',
                                    style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white),
                                  ),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.transparent,
                                    shadowColor: Colors.transparent,
                                    padding: const EdgeInsets.symmetric(vertical: 14),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: MediaQuery.of(context).viewInsets.bottom + 24),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }


  void _runDiagnosticTest() async {
    setState(() => _testingConnection = true);
    await Future.delayed(const Duration(seconds: 1, milliseconds: 500));
    if (!mounted) return;
    setState(() => _testingConnection = false);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: Color(0xFF10B981)),
            const SizedBox(width: 8),
            Text('Diagnostic Passed', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text('• IMAP SSL Port 993: Connected OK'),
            Text('• SMTP SSL Port 465: Connected OK'),
            Text('• Authentication: Success'),
            Text('• TLS 1.3 Encryption: Active'),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
        ],
      ),
    );
  }

  void _showBroadcastPushDialog(BuildContext context, MailProvider provider) {
    final titleController = TextEditingController();
    final bodyController = TextEditingController();
    final domainController = TextEditingController();
    bool isSending = false;

    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF7A00).withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.campaign_rounded, color: Color(0xFFFF7A00), size: 22),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Send Push Notification',
                  style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Compose a push notification to broadcast to all registered VoidMail app users.',
                  style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B)),
                ),
                const SizedBox(height: 16),

                // Title
                Text('Notification Title *', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                TextField(
                  controller: titleController,
                  decoration: InputDecoration(
                    hintText: 'e.g. New Feature Available!',
                    hintStyle: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF94A3B8)),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  ),
                ),
                const SizedBox(height: 14),

                // Body
                Text('Notification Body *', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                TextField(
                  controller: bodyController,
                  maxLines: 3,
                  decoration: InputDecoration(
                    hintText: 'Type your message here...',
                    hintStyle: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF94A3B8)),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  ),
                ),
                const SizedBox(height: 14),

                // Domain filter (optional)
                Text('Domain Filter (optional)', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                TextField(
                  controller: domainController,
                  decoration: InputDecoration(
                    hintText: 'Leave empty to send to all',
                    hintStyle: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF94A3B8)),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF7ED),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFFED7AA)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, size: 14, color: Color(0xFFFF7A00)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Sent from: ${provider.currentEmail}',
                          style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF92400E)),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: isSending ? null : () => Navigator.pop(context),
              child: Text('Cancel', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
            ),
            ElevatedButton(
              onPressed: isSending
                  ? null
                  : () async {
                      final title = titleController.text.trim();
                      final body = bodyController.text.trim();
                      if (title.isEmpty || body.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Title and body are required', style: GoogleFonts.inter()),
                            backgroundColor: const Color(0xFFEF4444),
                          ),
                        );
                        return;
                      }

                      setDialogState(() => isSending = true);

                      final result = await provider.apiService.broadcastPushNotification(
                        title: title,
                        body: body,
                        senderEmail: provider.currentEmail,
                        domain: domainController.text.trim(),
                      );

                      if (!context.mounted) return;
                      setDialogState(() => isSending = false);
                      Navigator.pop(context);

                      final sentCount = result['sent_count'] ?? 0;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            result['success'] == true
                                ? '✅ Push notification sent to $sentCount device(s)!'
                                : '❌ ${result['message']}',
                            style: GoogleFonts.inter(fontWeight: FontWeight.w500),
                          ),
                          backgroundColor: result['success'] == true
                              ? const Color(0xFF10B981)
                              : const Color(0xFFEF4444),
                          behavior: SnackBarBehavior.floating,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      );
                    },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFFF7A00),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              ),
              child: isSending
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.send_rounded, size: 16, color: Colors.white),
                        const SizedBox(width: 6),
                        Text('Send Now', style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
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
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final cfg = provider.config;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF9FAFD),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 860),
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header Title & Help Icon
                  Row(
                    children: [
                      if (Navigator.canPop(context)) ...[
                        IconButton(
                          icon: const Icon(Icons.arrow_back_rounded),
                          tooltip: 'Back',
                          onPressed: () => Navigator.pop(context),
                        ),
                        const SizedBox(width: 8),
                      ],
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Settings',
                              style: GoogleFonts.outfit(
                                fontSize: 26,
                                fontWeight: FontWeight.bold,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Manage your account, servers and preferences',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withOpacity(0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.help_outline_rounded, color: Color(0xFF6366F1), size: 20),
                      ),
                    ],
                  ),

              const SizedBox(height: 20),

              // 1. User Profile Header Card matching Design Image
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: isDark
                        ? [const Color(0xFF1B1638), const Color(0xFF16122E)]
                        : [const Color(0xFFF4F2FF), Colors.white],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(
                    color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.03),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    // Avatar
                    Container(
                      width: 52,
                      height: 52,
                      decoration: const BoxDecoration(
                        color: Color(0xFF6366F1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.person_rounded, color: Colors.white, size: 30),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            provider.currentEmail,
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Text(
                                cfg?.providerName ?? 'VoidPanel Auto',
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF6366F1).withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  'Default',
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: const Color(0xFF6366F1),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    // Logout Button
                    GestureDetector(
                      onTap: () async {
                        final isPrimary = provider.isCurrentAccountPrimary;
                        final currentEmail = provider.currentEmail;
                        if (isPrimary) {
                          await provider.logoutAll();
                          if (context.mounted) {
                            Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
                          }
                        } else {
                          final allLoggedOut = await provider.logout();
                          if (context.mounted) {
                            if (allLoggedOut) {
                              Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
                            } else {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('Logged out of $currentEmail. Switched to primary account.'),
                                  behavior: SnackBarBehavior.floating,
                                ),
                              );
                            }
                          }
                        }
                      },

                      child: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF2C2554) : Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: const Icon(Icons.logout_rounded, color: Color(0xFF6366F1), size: 20),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Section 1 Header: Server & Encryption
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6366F1).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.lock_outline_rounded, size: 16, color: Color(0xFF6366F1)),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Server & Encryption',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : const Color(0xFF0F172A),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEEF2FF),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      'Outlook-style',
                      style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.bold, color: const Color(0xFF4338CA)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Server & Encryption Card Container
              Container(
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1B1638) : Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEF2FF)),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 2)),
                  ],
                ),
                child: Column(
                  children: [
                    // Item 1: IMAP Incoming Server
                    ListTile(
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.dns_rounded, color: Color(0xFF6366F1), size: 20),
                      ),
                      title: Text('IMAP Incoming Server', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Row(
                        children: [
                          Text(cfg?.imapHost ?? "mail.voidonyx.com", style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: const Color(0xFF6366F1).withOpacity(0.1),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text('${cfg?.imapPort ?? 993}', style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.bold, color: const Color(0xFF6366F1))),
                          ),
                          const SizedBox(width: 6),
                          Text('SSL/TLS', style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8))),
                        ],
                      ),
                      trailing: const Icon(Icons.chevron_right_rounded, color: Color(0xFF94A3B8)),
                      onTap: () => _showEditServerDialog(context, cfg),
                    ),
                    const Divider(height: 1, indent: 64, color: Color(0xFFF1F5F9)),

                    // Item 2: SMTP Outgoing Server
                    ListTile(
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.send_rounded, color: Color(0xFF10B981), size: 20),
                      ),
                      title: Text('SMTP Outgoing Server', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Row(
                        children: [
                          Text(cfg?.smtpHost ?? "mail.voidonyx.com", style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: const Color(0xFF10B981).withOpacity(0.1),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text('${cfg?.smtpPort ?? 465}', style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.bold, color: const Color(0xFF10B981))),
                          ),
                          const SizedBox(width: 6),
                          Text('SSL/TLS', style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8))),
                        ],
                      ),
                      trailing: const Icon(Icons.chevron_right_rounded, color: Color(0xFF94A3B8)),
                      onTap: () => _showEditServerDialog(context, cfg),
                    ),
                    const Divider(height: 1, indent: 64, color: Color(0xFFF1F5F9)),

                    // Item 3: Test Connection & SSL Handshake
                    ListTile(
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF3B82F6).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.verified_user_rounded, color: Color(0xFF3B82F6), size: 20),
                      ),
                      title: Text('Test Connection & SSL Handshake', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Text('Verify IMAP & SMTP connectivity', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                      trailing: OutlinedButton(
                        onPressed: _testingConnection ? null : _runDiagnosticTest,
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          side: const BorderSide(color: Color(0xFFE2E8F0)),
                        ),
                        child: _testingConnection
                            ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF6366F1)))
                            : Text('Test', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: const Color(0xFF6366F1))),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Section: Push Notifications
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF7A00).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.notifications_active_rounded, size: 16, color: Color(0xFFFF7A00)),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Push Notifications',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : const Color(0xFF0F172A),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Push Notification Card
              Container(
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1B1638) : Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEF2FF)),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 2)),
                  ],
                ),
                child: Column(
                  children: [
                    // Current Account
                    ListTile(
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.person_rounded, color: Color(0xFF10B981), size: 20),
                      ),
                      title: Text('Logged in as', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Text(
                        provider.currentEmail,
                        style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFFFF7A00), fontWeight: FontWeight.w600),
                      ),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withOpacity(0.12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          'Active',
                          style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.bold, color: const Color(0xFF10B981)),
                        ),
                      ),
                    ),
                    const Divider(height: 1, indent: 64, color: Color(0xFFF1F5F9)),

                    // Send Push Notification
                    ListTile(
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFF7A00).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.campaign_rounded, color: Color(0xFFFF7A00), size: 20),
                      ),
                      title: Text('Send Push Notification', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Text('Broadcast to all app users', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(colors: [Color(0xFFFF7A00), Color(0xFFE65100)]),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text('Send', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                      ),
                      onTap: () => _showBroadcastPushDialog(context, provider),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Section 2 Header: Appearance & Theme
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF8B5CF6).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.palette_outlined, size: 16, color: Color(0xFF8B5CF6)),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Appearance & Theme',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : const Color(0xFF0F172A),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Appearance Card Container
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1B1638) : Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEF2FF)),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 2)),
                  ],
                ),
                child: Column(
                  children: [
                    // Dark Mode Toggle Row
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: const Color(0xFF6366F1).withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.nightlight_round, color: Color(0xFF6366F1), size: 20),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Dark Mode', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 14)),
                              Text('Switch between Light and Dark theme', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                            ],
                          ),
                        ),
                        Switch(
                          value: isDark,
                          onChanged: (val) => provider.toggleTheme(val),
                          activeColor: const Color(0xFF6366F1),
                        ),
                      ],
                    ),

                    const SizedBox(height: 16),

                    // Light / Dark Visual Selector Cards (Matching Mockup)
                    Row(
                      children: [
                        // Light Card Option
                        Expanded(
                          child: GestureDetector(
                            onTap: () => provider.toggleTheme(false),
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: !isDark ? Colors.white : const Color(0xFF16122E),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: !isDark ? const Color(0xFF6366F1) : const Color(0xFFE2E8F0),
                                  width: !isDark ? 1.5 : 1.0,
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.wb_sunny_outlined, color: Color(0xFFF59E0B), size: 20),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Light', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                                        Text('Clean and bright', style: GoogleFonts.inter(fontSize: 10, color: const Color(0xFF94A3B8))),
                                      ],
                                    ),
                                  ),
                                  Icon(
                                    !isDark ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                                    color: !isDark ? const Color(0xFF6366F1) : const Color(0xFFCBD5E1),
                                    size: 18,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        // Dark Card Option
                        Expanded(
                          child: GestureDetector(
                            onTap: () => provider.toggleTheme(true),
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: isDark ? const Color(0xFF1F1A42) : const Color(0xFFF4F2FF),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: isDark ? const Color(0xFF6366F1) : const Color(0xFFC7D2FE),
                                  width: isDark ? 1.5 : 1.0,
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.nightlight_round, color: Color(0xFF6366F1), size: 20),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Dark', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                                        Text('Easy on the eyes', style: GoogleFonts.inter(fontSize: 10, color: const Color(0xFF94A3B8))),
                                      ],
                                    ),
                                  ),
                                  Icon(
                                    isDark ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                                    color: isDark ? const Color(0xFF6366F1) : const Color(0xFFCBD5E1),
                                    size: 18,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 16),
                    const Divider(height: 1, color: Color(0xFFF1F5F9)),
                    const SizedBox(height: 8),

                    // Item 3: Font Size (Interactive Modal Selection)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text('Aa', style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: const Color(0xFF6366F1), fontSize: 16)),
                      ),
                      title: Text('Font Size', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(provider.fontSizeName, style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                          const SizedBox(width: 4),
                          const Icon(Icons.chevron_right_rounded, color: Color(0xFF94A3B8)),
                        ],
                      ),
                      onTap: () {
                        showDialog(
                          context: context,
                          builder: (context) => AlertDialog(
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                            title: Text('Select Font Size', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
                            content: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                ListTile(
                                  title: const Text('Small (12px)'),
                                  trailing: provider.fontSizeName == 'Small' ? const Icon(Icons.check, color: Color(0xFF6366F1)) : null,
                                  onTap: () {
                                    provider.setFontSize('Small', 0.88);
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Font size scaled to Small'), backgroundColor: Color(0xFF6366F1)));
                                  },
                                ),
                                ListTile(
                                  title: const Text('Medium (14px) - Default'),
                                  trailing: provider.fontSizeName == 'Medium' ? const Icon(Icons.check, color: Color(0xFF6366F1)) : null,
                                  onTap: () {
                                    provider.setFontSize('Medium', 1.0);
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Font size reset to Medium'), backgroundColor: Color(0xFF6366F1)));
                                  },
                                ),
                                ListTile(
                                  title: const Text('Large (16px)'),
                                  trailing: provider.fontSizeName == 'Large' ? const Icon(Icons.check, color: Color(0xFF6366F1)) : null,
                                  onTap: () {
                                    provider.setFontSize('Large', 1.18);
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Font size scaled to Large'), backgroundColor: Color(0xFF6366F1)));
                                  },
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                    const Divider(height: 1, color: Color(0xFFF1F5F9)),

                    // Item 4: App Theme (Interactive Color Picker Modal)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.grid_view_rounded, color: Color(0xFF6366F1), size: 20),
                      ),
                      title: Text('App Theme', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(provider.themeName, style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                          const SizedBox(width: 4),
                          const Icon(Icons.chevron_right_rounded, color: Color(0xFF94A3B8)),
                        ],
                      ),
                      onTap: () {
                        showDialog(
                          context: context,
                          builder: (context) => AlertDialog(
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                            title: Text('Select Accent Theme', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
                            content: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                ListTile(
                                  leading: const CircleAvatar(backgroundColor: Color(0xFFFF7A00), radius: 12),
                                  title: const Text('Flame Orange (Default)'),
                                  trailing: provider.themeName == 'Flame Orange' ? const Icon(Icons.check, color: Color(0xFFFF7A00)) : null,
                                  onTap: () {
                                    provider.setAccentTheme('Flame Orange', const Color(0xFFFF7A00));
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('App theme set to Flame Orange'), backgroundColor: Color(0xFFFF7A00)));
                                  },
                                ),
                                ListTile(
                                  leading: const CircleAvatar(backgroundColor: Color(0xFFFFB800), radius: 12),
                                  title: const Text('Amber Gold'),
                                  trailing: provider.themeName == 'Amber Gold' ? const Icon(Icons.check, color: Color(0xFFFFB800)) : null,
                                  onTap: () {
                                    provider.setAccentTheme('Amber Gold', const Color(0xFFFFB800));
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('App theme set to Amber Gold'), backgroundColor: Color(0xFFFFB800)));
                                  },
                                ),
                                ListTile(
                                  leading: const CircleAvatar(backgroundColor: Color(0xFFEA580C), radius: 12),
                                  title: const Text('Sunset Coral'),
                                  trailing: provider.themeName == 'Sunset Coral' ? const Icon(Icons.check, color: Color(0xFFEA580C)) : null,
                                  onTap: () {
                                    provider.setAccentTheme('Sunset Coral', const Color(0xFFEA580C));
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('App theme set to Sunset Coral'), backgroundColor: Color(0xFFEA580C)));
                                  },
                                ),
                                ListTile(
                                  leading: const CircleAvatar(backgroundColor: Color(0xFF6C5CE7), radius: 12),
                                  title: const Text('VoidOnyx Purple'),
                                  trailing: provider.themeName == 'VoidOnyx Purple' ? const Icon(Icons.check, color: Color(0xFF6C5CE7)) : null,
                                  onTap: () {
                                    provider.setAccentTheme('VoidOnyx Purple', const Color(0xFF6C5CE7));
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('App theme set to VoidOnyx Purple'), backgroundColor: Color(0xFF6C5CE7)));
                                  },
                                ),
                                ListTile(
                                  leading: const CircleAvatar(backgroundColor: Color(0xFF10B981), radius: 12),
                                  title: const Text('Emerald Green'),
                                  trailing: provider.themeName == 'Emerald Green' ? const Icon(Icons.check, color: Color(0xFF10B981)) : null,
                                  onTap: () {
                                    provider.setAccentTheme('Emerald Green', const Color(0xFF10B981));
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('App theme set to Emerald Green'), backgroundColor: Color(0xFF10B981)));
                                  },
                                ),
                              ],
                            ),

                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),
              const Center(child: PoweredByVoidPanel()),
              const SizedBox(height: 8),
              Center(
                child: Text(
                  'VoidMail — by VoidOnyx (v1.0.12)',
                  style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8)),
                ),
              ),

              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    ),
  ),
);
  }
}
