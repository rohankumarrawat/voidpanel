import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/mail_provider.dart';
import '../widgets/auth_progress_overlay.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController(text: '');
  final _passwordController = TextEditingController(text: '');

  // Advanced Server Settings (IMAP / SMTP like Outlook)
  bool _showAdvancedSettings = false;
  final _imapHostController = TextEditingController(text: '');
  final _imapPortController = TextEditingController(text: '993');
  bool _imapSsl = true;

  final _smtpHostController = TextEditingController(text: '');
  final _smtpPortController = TextEditingController(text: '465');
  bool _smtpSsl = true;

  bool _rememberMe = true;
  bool _obscurePassword = true;

  // Auth progress overlay
  bool _showAuthProgress = false;
  final GlobalKey<AuthProgressOverlayState> _authOverlayKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _emailController.addListener(_autoFillServerHosts);
  }

  void _autoFillServerHosts() {
    final email = _emailController.text.trim();
    if (email.contains('@')) {
      final domain = email.split('@')[1];
      if (domain.isNotEmpty) {
        if (!_showAdvancedSettings || _imapHostController.text.isEmpty || _imapHostController.text.contains('voidonyx')) {
          _imapHostController.text = 'mail.$domain';
          _smtpHostController.text = 'mail.$domain';
        }
      }
    }
  }

  Future<void> _handleLogin() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Please enter your email and password',
              style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
      return;
    }

    if (!email.contains('@')) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Please enter a valid email address',
              style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
      return;
    }

    // Show the animated auth progress overlay
    setState(() => _showAuthProgress = true);

    // Run the animated auth flow after overlay mounts
    await _runAuthFlow();
  }

  Future<void> _runAuthFlow() async {
    // Wait for the AuthProgressOverlay to mount in the widget tree
    await Future.delayed(const Duration(milliseconds: 100));

    var overlay = _authOverlayKey.currentState;
    if (overlay == null) {
      await Future.delayed(const Duration(milliseconds: 150));
      overlay = _authOverlayKey.currentState;
    }

    if (overlay == null) {
      // Fallback if overlay fails to mount
      setState(() => _showAuthProgress = false);
      return;
    }

    final provider = Provider.of<MailProvider>(context, listen: false);
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();
    final domain = email.contains('@') ? email.split('@')[1] : '';

    try {
      // Step 1: Validating credentials
      overlay.updateStep(AuthStep.validating);
      await Future.delayed(const Duration(milliseconds: 300));

      // Step 2: Resolving mail server
      final imapHost = _showAdvancedSettings && _imapHostController.text.isNotEmpty
          ? _imapHostController.text.trim()
          : 'mail.$domain';
      final imapPort = _showAdvancedSettings
          ? (int.tryParse(_imapPortController.text.trim()) ?? 993)
          : 993;

      overlay.updateStep(AuthStep.resolvingServer, serverHost: imapHost);
      await Future.delayed(const Duration(milliseconds: 300));

      // Step 3: Connecting to IMAP
      overlay.updateStep(AuthStep.connectingImap, serverHost: '$imapHost:$imapPort');
      await Future.delayed(const Duration(milliseconds: 200));

      // Step 4: Authenticating IMAP & Syncing Mailbox
      overlay.updateStep(AuthStep.authenticatingImap, serverHost: imapHost);
      await Future.delayed(const Duration(milliseconds: 200));

      overlay.updateStep(AuthStep.syncingMailbox, serverHost: imapHost);

      Map<String, dynamic> result;
      if (_showAdvancedSettings) {
        final smtpHost = _smtpHostController.text.trim().isNotEmpty
            ? _smtpHostController.text.trim()
            : 'mail.$domain';
        final smtpPort = int.tryParse(_smtpPortController.text.trim()) ?? 465;

        result = await provider.loginWithCustomServer(
          email: email,
          password: password,
          imapHost: imapHost,
          imapPort: imapPort,
          imapSsl: _imapSsl,
          smtpHost: smtpHost,
          smtpPort: smtpPort,
          smtpSsl: _smtpSsl,
          providerName: 'Custom IMAP/SMTP',
        );
      } else {
        result = await provider.loginWithCustomServer(
          email: email,
          password: password,
          imapHost: imapHost,
          imapPort: imapPort,
          imapSsl: true,
          smtpHost: 'mail.$domain',
          smtpPort: 465,
          smtpSsl: true,
          providerName: 'VoidPanel Auto',
        );
      }

      if (!mounted) return;

      if (result['success'] == true) {
        // Step 6: Connecting SMTP
        overlay.updateStep(AuthStep.connectingSmtp);
        await Future.delayed(const Duration(milliseconds: 200));

        // Step 7: Authenticating SMTP
        overlay.updateStep(AuthStep.authenticatingSmtp);
        await Future.delayed(const Duration(milliseconds: 200));

        // Complete!
        final emailCount = provider.filteredEmails.length;
        overlay.setComplete(emailCount);

        // Wait 1s to show success then navigate
        await Future.delayed(const Duration(milliseconds: 1000));
        if (!mounted) return;

        // Check if we're in add-account mode
        final args = ModalRoute.of(context)?.settings.arguments;
        final isAddAccount = args is Map && args['addAccount'] == true;
        if (isAddAccount) {
          Navigator.pop(context); // Go back to main layout
        } else {
          Navigator.pushReplacementNamed(context, '/main');
        }
      } else {
        // Parse the error for a friendly message
        final errMsg = result['message'] ?? 'Unknown error';
        String title = 'Authentication Failed';
        String detail = errMsg;

        if (errMsg.contains('AUTHENTICATIONFAILED') || errMsg.contains('Authentication failed') || errMsg.contains('Invalid password')) {
          title = 'Invalid Credentials';
          detail = 'The email password entered for $email is incorrect. Please check your credentials and try again.';
        } else if (errMsg.contains('SocketException') || errMsg.contains('TimeoutException') || errMsg.contains('Unable to connect')) {
          title = 'Server Unreachable';
          detail = 'Could not connect to $imapHost. Check your internet connection or server settings.';
        } else if (errMsg.contains('PRIVACYREQUIRED') || errMsg.contains('Plaintext')) {
          title = 'Security Error';
          detail = 'Server requires SSL/TLS connection. Please enable SSL in Advanced Settings.';
        }

        overlay.setError(title, detail: detail);
      }
    } catch (e) {
      if (!mounted) return;
      overlay.setError(
        'Connection Error',
        detail: e.toString(),
      );
    }
  }

  void _applyPreset(String name, String imap, int imapP, String smtp, int smtpP) {
    setState(() {
      _showAdvancedSettings = true;
      _imapHostController.text = imap;
      _imapPortController.text = imapP.toString();
      _smtpHostController.text = smtp;
      _smtpPortController.text = smtpP.toString();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Check if we're adding an account (vs first login)
    final args = ModalRoute.of(context)?.settings.arguments;
    final isAddAccount = args is Map && args['addAccount'] == true;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : Colors.white,
      body: Stack(
        children: [
          // Main login form
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Back button spacer when in add-account mode
                      if (isAddAccount) const SizedBox(height: 40),
                      // 1. Hero Logo Graphic & Header matching Design Image
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.only(top: 20, bottom: 10),
                        child: Column(
                          children: [
                            // 3D App Icon Badge
                            Container(
                              width: 90,
                              height: 90,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFF6366F1), Color(0xFF4F46E5)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                borderRadius: BorderRadius.circular(28),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFF6366F1).withOpacity(0.35),
                                    blurRadius: 24,
                                    offset: const Offset(0, 10),
                                  ),
                                ],
                              ),
                              child: Stack(
                                children: [
                                  const Center(
                                    child: Icon(
                                      Icons.mail_rounded,
                                      size: 46,
                                      color: Colors.white,
                                    ),
                                  ),
                                  Positioned(
                                    right: 20,
                                    top: 20,
                                    child: Container(
                                      width: 10,
                                      height: 10,
                                      decoration: const BoxDecoration(
                                        color: Colors.white,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 18),

                            Text(
                              'VoidOnyx',
                              style: GoogleFonts.outfit(
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                                letterSpacing: -0.5,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Universal Mobile Email Client',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 28),

                      // Welcome heading
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              isAddAccount ? 'Add Account ➕' : 'Welcome back! 👋',
                              style: GoogleFonts.outfit(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              isAddAccount
                                  ? 'Link another email account to VoidMail'
                                  : 'Sign in to continue to your account',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 20),

                      // Main Form Container Card
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1B1638) : Colors.white,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(
                            color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEF2FF),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.04),
                              blurRadius: 20,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Column(
                          children: [
                            // Email Input Field
                            TextFormField(
                              controller: _emailController,
                              style: GoogleFonts.inter(fontSize: 14),
                              decoration: InputDecoration(
                                hintText: 'you@domain.com',
                                hintStyle: GoogleFonts.inter(fontSize: 14, color: const Color(0xFF94A3B8)),
                                prefixIcon: Padding(
                                  padding: const EdgeInsets.all(8.0),
                                  child: Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF6366F1),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: const Icon(Icons.mail_rounded, size: 16, color: Colors.white),
                                  ),
                                ),
                                filled: true,
                                fillColor: isDark ? const Color(0xFF16122E) : const Color(0xFFF8F9FE),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                                ),
                              ),
                            ),

                            const SizedBox(height: 14),

                            // Password Input Field
                            TextFormField(
                              controller: _passwordController,
                              obscureText: _obscurePassword,
                              style: GoogleFonts.inter(fontSize: 14),
                              decoration: InputDecoration(
                                hintText: '••••••••',
                                hintStyle: GoogleFonts.inter(fontSize: 14, color: const Color(0xFF94A3B8)),
                                prefixIcon: Padding(
                                  padding: const EdgeInsets.all(8.0),
                                  child: Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF6366F1),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: const Icon(Icons.lock_rounded, size: 16, color: Colors.white),
                                  ),
                                ),
                                suffixIcon: IconButton(
                                  icon: Icon(
                                    _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                                    color: const Color(0xFF6366F1),
                                    size: 20,
                                  ),
                                  onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                                ),
                                filled: true,
                                fillColor: isDark ? const Color(0xFF16122E) : const Color(0xFFF8F9FE),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                                ),
                              ),
                            ),

                            const SizedBox(height: 12),

                            // Remember me & Advanced Link Row
                            Row(
                              children: [
                                Checkbox(
                                  value: _rememberMe,
                                  onChanged: (val) => setState(() => _rememberMe = val ?? true),
                                  activeColor: const Color(0xFF6366F1),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
                                ),
                                Text(
                                  'Remember me',
                                  style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500, color: const Color(0xFF475569)),
                                ),
                                const Spacer(),
                                GestureDetector(
                                  onTap: () {
                                    setState(() {
                                      _showAdvancedSettings = !_showAdvancedSettings;
                                    });
                                  },
                                  child: Row(
                                    children: [
                                      const Icon(Icons.tune_rounded, size: 15, color: Color(0xFF6366F1)),
                                      const SizedBox(width: 4),
                                      Text(
                                        _showAdvancedSettings ? 'Hide Advanced' : 'Advanced (IMAP/SMTP)',
                                        style: GoogleFonts.inter(
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold,
                                          color: const Color(0xFF6366F1),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),

                            // Collapsible Advanced Settings
                            if (_showAdvancedSettings) ...[
                              const SizedBox(height: 14),
                              Container(
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  color: isDark ? const Color(0xFF16122E) : const Color(0xFFF8F9FE),
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(color: const Color(0xFFC7D2FE)),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('IMAP Incoming Server', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                                    const SizedBox(height: 6),
                                    Row(
                                      children: [
                                        Expanded(
                                          flex: 3,
                                          child: TextFormField(
                                            controller: _imapHostController,
                                            decoration: InputDecoration(
                                              hintText: 'mail.domain.com',
                                              isDense: true,
                                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          flex: 1,
                                          child: TextFormField(
                                            controller: _imapPortController,
                                            keyboardType: TextInputType.number,
                                            decoration: InputDecoration(
                                              hintText: '993',
                                              isDense: true,
                                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 10),
                                    Text('SMTP Outgoing Server', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                                    const SizedBox(height: 6),
                                    Row(
                                      children: [
                                        Expanded(
                                          flex: 3,
                                          child: TextFormField(
                                            controller: _smtpHostController,
                                            decoration: InputDecoration(
                                              hintText: 'mail.domain.com',
                                              isDense: true,
                                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          flex: 1,
                                          child: TextFormField(
                                            controller: _smtpPortController,
                                            keyboardType: TextInputType.number,
                                            decoration: InputDecoration(
                                              hintText: '465',
                                              isDense: true,
                                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],

                            const SizedBox(height: 20),

                            // Primary Sign In Button (Gradient Pill with Login Icon)
                            Container(
                              width: double.infinity,
                              height: 52,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFF6366F1), Color(0xFF4F46E5)],
                                ),
                                borderRadius: BorderRadius.circular(18),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFF6366F1).withOpacity(0.35),
                                    blurRadius: 14,
                                    offset: const Offset(0, 6),
                                  ),
                                ],
                              ),
                              child: ElevatedButton(
                                onPressed: _showAuthProgress ? null : _handleLogin,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.transparent,
                                  shadowColor: Colors.transparent,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(Icons.login_rounded, color: Colors.white, size: 20),
                                    const SizedBox(width: 8),
                                    Text(
                                      'Sign In',
                                      style: GoogleFonts.inter(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 24),

                      // Social Sign-In Section
                      Row(
                        children: [
                          const Expanded(child: Divider(color: Color(0xFFE2E8F0))),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            child: Text(
                              'or continue with',
                              style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF94A3B8)),
                            ),
                          ),
                          const Expanded(child: Divider(color: Color(0xFFE2E8F0))),
                        ],
                      ),

                      const SizedBox(height: 18),

                      // Google & Microsoft Buttons
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _showAuthProgress
                                  ? null
                                  : () {
                                      _applyPreset('Gmail', 'imap.gmail.com', 993, 'smtp.gmail.com', 465);
                                      _handleLogin();
                                    },
                              icon: const Icon(Icons.g_mobiledata_rounded, color: Colors.redAccent, size: 24),
                              label: Text('Continue with Google', style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: const Color(0xFF1E293B))),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                side: const BorderSide(color: Color(0xFFE2E8F0)),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _showAuthProgress
                                  ? null
                                  : () {
                                      _applyPreset('Outlook', 'outlook.office365.com', 993, 'smtp.office365.com', 587);
                                      _handleLogin();
                                    },
                              icon: const Icon(Icons.window_rounded, color: Colors.blueAccent, size: 18),
                              label: Text('Continue with Microsoft', style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: const Color(0xFF1E293B))),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                side: const BorderSide(color: Color(0xFFE2E8F0)),
                              ),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 28),

                      // Security Footer
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.verified_user_rounded, size: 16, color: Color(0xFF6366F1)),
                          const SizedBox(width: 6),
                          Text(
                            'Your data is secure and encrypted',
                            style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: const Color(0xFF64748B)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Auth Progress Overlay
          if (_showAuthProgress)
            AuthProgressOverlay(
              key: _authOverlayKey,
              onDismiss: () {
                setState(() => _showAuthProgress = false);
              },
              onRetry: () {
                setState(() => _showAuthProgress = false);
                Future.delayed(const Duration(milliseconds: 200), () {
                  _handleLogin();
                });
              },
            ),

          // Back Button (only in add-account mode)
          if (isAddAccount)
            Positioned(
              top: 0,
              left: 0,
              child: SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => Navigator.pop(context),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: isDark
                              ? const Color(0xFF1B1638).withValues(alpha: 0.9)
                              : Colors.white.withValues(alpha: 0.9),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.arrow_back_rounded, size: 18,
                              color: isDark ? Colors.white : const Color(0xFF1E1B4B)),
                            const SizedBox(width: 6),
                            Text('Back to Mail',
                              style: GoogleFonts.inter(
                                fontSize: 13, fontWeight: FontWeight.w600,
                                color: isDark ? Colors.white : const Color(0xFF1E1B4B),
                              )),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
