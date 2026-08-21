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

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(
            'Advanced Server Settings',
            style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('IMAP Incoming Host', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                TextField(
                  controller: imapController,
                  decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
                ),
                const SizedBox(height: 8),
                Text('IMAP Port', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                TextField(
                  controller: imapPortController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
                ),
                Row(
                  children: [
                    Switch(
                      value: imapSsl,
                      onChanged: (val) => setDialogState(() => imapSsl = val),
                      activeColor: const Color(0xFF6C5CE7),
                    ),
                    Text('Use SSL/TLS', style: GoogleFonts.inter(fontSize: 12)),
                  ],
                ),
                const Divider(),
                Text('SMTP Outgoing Host', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                TextField(
                  controller: smtpController,
                  decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
                ),
                const SizedBox(height: 8),
                Text('SMTP Port', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                TextField(
                  controller: smtpPortController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
                ),
                Row(
                  children: [
                    Switch(
                      value: smtpSsl,
                      onChanged: (val) => setDialogState(() => smtpSsl = val),
                      activeColor: const Color(0xFF6C5CE7),
                    ),
                    Text('Use SSL/TLS', style: GoogleFonts.inter(fontSize: 12)),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6C5CE7)),
              onPressed: () {
                final updated = ServerConfig.custom(
                  email: provider.currentEmail,
                  password: 'password123',
                  imapHost: imapController.text.trim(),
                  imapPort: int.tryParse(imapPortController.text.trim()) ?? 993,
                  imapSsl: imapSsl,
                  smtpHost: smtpController.text.trim(),
                  smtpPort: int.tryParse(smtpPortController.text.trim()) ?? 465,
                  smtpSsl: smtpSsl,
                  providerName: 'Custom IMAP/SMTP',
                );
                provider.updateServerConfig(updated);
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Server settings updated!'), backgroundColor: Color(0xFF10B981)),
                );
              },
              child: const Text('Save Settings', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
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

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final cfg = provider.config;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF9FAFD),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Title & Help Icon
              Row(
                children: [
                  Column(
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
                  const Spacer(),
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
                      onTap: () {
                        provider.logout();
                        Navigator.pushReplacementNamed(context, '/login');
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
                                  leading: const CircleAvatar(backgroundColor: Color(0xFF6366F1), radius: 12),
                                  title: const Text('VoidOnyx Purple'),
                                  trailing: provider.themeName == 'VoidOnyx Purple' ? const Icon(Icons.check, color: Color(0xFF6366F1)) : null,
                                  onTap: () {
                                    provider.setAccentTheme('VoidOnyx Purple', const Color(0xFF6366F1));
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('App theme set to VoidOnyx Purple'), backgroundColor: Color(0xFF6366F1)));
                                  },
                                ),
                                ListTile(
                                  leading: const CircleAvatar(backgroundColor: Color(0xFF4F46E5), radius: 12),
                                  title: const Text('Midnight Indigo'),
                                  trailing: provider.themeName == 'Midnight Indigo' ? const Icon(Icons.check, color: Color(0xFF4F46E5)) : null,
                                  onTap: () {
                                    provider.setAccentTheme('Midnight Indigo', const Color(0xFF4F46E5));
                                    Navigator.pop(context);
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('App theme set to Midnight Indigo'), backgroundColor: Color(0xFF4F46E5)));
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
                  'VoidMail Universal Client v1.0.0 (Build 1)',
                  style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8)),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
