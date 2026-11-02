import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/mail_provider.dart';
import '../theme/app_theme.dart';

import 'package:shared_preferences/shared_preferences.dart';

class UpgradeLeadModal extends StatefulWidget {
  const UpgradeLeadModal({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => const UpgradeLeadModal(),
    );
  }

  @override
  State<UpgradeLeadModal> createState() => _UpgradeLeadModalState();
}

class _UpgradeLeadModalState extends State<UpgradeLeadModal> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  late TextEditingController _emailController;

  bool _isSubmitting = false;
  bool _isSubmitted = false;
  String _successMessage = '';

  @override
  void initState() {
    super.initState();
    final currentEmail = Provider.of<MailProvider>(context, listen: false).currentEmail;
    _emailController = TextEditingController(text: currentEmail);
    _checkIfAlreadyRequested(currentEmail);
  }

  Future<void> _checkIfAlreadyRequested(String email) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final alreadyRequested = prefs.getBool('upgrade_requested_${email.toLowerCase()}') ?? false;
      if (alreadyRequested && mounted) {
        final domain = email.contains('@') ? email.split('@').last : 'your domain';
        setState(() {
          _isSubmitted = true;
          _successMessage = 'Your AI upgrade request for @$domain is already under review by VoidOnyx Superadmin! We will activate it shortly.';
        });
      }
    } catch (_) {}
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    try {
      final email = _emailController.text.trim();
      final provider = Provider.of<MailProvider>(context, listen: false);
      final result = await provider.submitAiUpgradeLead(
        name: _nameController.text.trim(),
        phone: _phoneController.text.trim(),
      );

      // Save locally to enforce 1-time submission
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool('upgrade_requested_${email.toLowerCase()}', true);
      } catch (_) {}

      if (mounted) {
        setState(() {
          _isSubmitting = false;
          _isSubmitted = true;
          _successMessage = result['message'] ??
              'Upgrade request submitted successfully! Your domain will be enabled in Superadmin.';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSubmitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Submission failed: $e'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    final email = _emailController.text;
    final domain = email.contains('@') ? email.split('@').last : 'your domain';

    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF16120E) : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          border: Border.all(
            color: isDark ? const Color(0x33FF7A00) : const Color(0x22FF7A00),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primaryOrange.withValues(alpha: 0.15),
              blurRadius: 30,
              spreadRadius: 2,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: _isSubmitted
              ? _buildSuccessView(context, domain, isDark)
              : _buildFormView(context, domain, isDark),
        ),
      ),
    );
  }

  Widget _buildFormView(BuildContext context, String domain, bool isDark) {
    return Form(
      key: _formKey,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Drag Handle
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: isDark ? Colors.white24 : Colors.black12,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 18),

            // Sparkle Header Badge
            Center(
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFFF7A00), Color(0xFFFF9E00)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFFFF7A00).withValues(alpha: 0.4),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.auto_awesome,
                  color: Colors.white,
                  size: 30,
                ),
              ),
            ),
            const SizedBox(height: 14),

            // Title & Subtitle
            Text(
              'Unlock VoidMail AI ✨',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.5,
                color: isDark ? Colors.white : Colors.black87,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Request free instant access to Next-Gen AI features for @$domain.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13.5,
                color: isDark ? Colors.white70 : Colors.black54,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 16),

            // Feature Highlights Pills
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                _buildFeatureBadge('⚡ Inbox Digest', isDark),
                _buildFeatureBadge('✍️ AI Email Writer', isDark),
                _buildFeatureBadge('🔍 Smart Search', isDark),
                _buildFeatureBadge('↩️ 1-Tap Replies', isDark),
              ],
            ),
            const SizedBox(height: 20),

            // Name Field
            _buildTextField(
              controller: _nameController,
              label: 'Full Name',
              hint: 'e.g. John Doe',
              icon: Icons.person_outline_rounded,
              isDark: isDark,
              validator: (val) =>
                  (val == null || val.trim().isEmpty) ? 'Please enter your name' : null,
            ),
            const SizedBox(height: 12),

            // Email Field (Read-only / verified)
            _buildTextField(
              controller: _emailController,
              label: 'Email Address',
              hint: 'your@domain.com',
              icon: Icons.email_outlined,
              isDark: isDark,
              readOnly: true,
            ),
            const SizedBox(height: 12),

            // Phone Number Field
            _buildTextField(
              controller: _phoneController,
              label: 'Phone / WhatsApp Number',
              hint: 'e.g. +91 98765 43210',
              icon: Icons.phone_outlined,
              keyboardType: TextInputType.phone,
              isDark: isDark,
              validator: (val) => (val == null || val.trim().length < 7)
                  ? 'Please enter a valid phone number'
                  : null,
            ),
            const SizedBox(height: 22),

            // Submit Button
            Container(
              height: 52,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFFF7A00), Color(0xFFFF9E00)],
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFFFF7A00).withValues(alpha: 0.35),
                    blurRadius: 18,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: ElevatedButton(
                onPressed: _isSubmitting ? null : _handleSubmit,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  shadowColor: Colors.transparent,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                child: _isSubmitting
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2.5,
                        ),
                      )
                    : const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.bolt_rounded, color: Colors.white, size: 22),
                          SizedBox(width: 8),
                          Text(
                            'Request Free AI Upgrade',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
            const SizedBox(height: 10),

            // Free & Secure Badge
            Center(
              child: Text(
                '🔒 100% Free • Saved securely to VoidOnyx Superadmin',
                style: TextStyle(
                  fontSize: 11.5,
                  color: isDark ? Colors.white38 : Colors.black38,
                ),
              ),
            ),
            const SizedBox(height: 10),
          ],
        ),
      ),
    );
  }

  Widget _buildSuccessView(BuildContext context, String domain, bool isDark) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const SizedBox(height: 20),
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: const Color(0xFF10B981).withValues(alpha: 0.15),
            shape: BoxShape.circle,
            border: Border.all(color: const Color(0xFF10B981), width: 2),
          ),
          child: const Icon(
            Icons.check_circle_outline_rounded,
            color: Color(0xFF10B981),
            size: 38,
          ),
        ),
        const SizedBox(height: 18),
        Text(
          'Request Received! 🎉',
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w800,
            color: isDark ? Colors.white : Colors.black87,
          ),
        ),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            _successMessage.isNotEmpty
                ? _successMessage
                : 'Your upgrade request for @$domain has been saved in VoidOnyx Superadmin. Once approved, VoidMail AI features will unlock automatically!',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: isDark ? Colors.white70 : Colors.black54,
              height: 1.4,
            ),
          ),
        ),

        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: ElevatedButton(
            onPressed: () => Navigator.pop(context),
            style: ElevatedButton.styleFrom(
              backgroundColor: isDark ? const Color(0xFF2A2018) : const Color(0xFFF3F4F6),
              foregroundColor: isDark ? Colors.white : Colors.black87,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              elevation: 0,
            ),
            child: const Text(
              'Got It',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
            ),
          ),
        ),
        const SizedBox(height: 12),
      ],
    );
  }

  Widget _buildFeatureBadge(String label, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: isDark ? const Color(0x22FF7A00) : const Color(0x14FF7A00),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: const Color(0xFFFF7A00).withValues(alpha: 0.3),
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11.5,
          fontWeight: FontWeight.w600,
          color: isDark ? const Color(0xFFFF9E00) : const Color(0xFFE65100),
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    required bool isDark,
    TextInputType keyboardType = TextInputType.text,
    bool readOnly = false,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      readOnly: readOnly,
      keyboardType: keyboardType,
      validator: validator,
      style: TextStyle(
        fontSize: 14.5,
        color: isDark ? Colors.white : Colors.black87,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Icon(icon, color: const Color(0xFFFF7A00), size: 20),
        filled: true,
        fillColor: isDark ? const Color(0xFF1E1712) : const Color(0xFFF9FAFB),
        labelStyle: TextStyle(
          fontSize: 13,
          color: isDark ? Colors.white60 : Colors.black54,
        ),
        hintStyle: TextStyle(
          fontSize: 13,
          color: isDark ? Colors.white30 : Colors.black26,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(
            color: isDark ? Colors.white12 : Colors.black12,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(
            color: isDark ? Colors.white12 : Colors.black12,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(
            color: Color(0xFFFF7A00),
            width: 1.5,
          ),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }
}
