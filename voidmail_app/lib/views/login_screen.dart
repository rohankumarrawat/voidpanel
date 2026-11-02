import 'dart:async';
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

  // Sign Up & Onboarding State (Matching voidpanel_django web)
  bool _isSignUpMode = false;
  bool _isOtpStep = false;
  final _signUpUsernameController = TextEditingController();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _signUpPasswordController = TextEditingController();
  final _phoneController = TextEditingController();
  final _otpController = TextEditingController();
  bool _obscureSignUpPassword = true;

  bool _isCheckingUsername = false;
  bool _usernameAvailable = false;
  String _usernameHintMessage = '3-30 lowercase characters (letters, numbers, dots).';
  bool _isRequestingOtp = false;
  bool _isVerifyingOtp = false;
  Timer? _usernameDebounce;
  String? _otpTestHint;
  String _activeRegistrationPhone = '';

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

  @override
  void dispose() {
    _emailController.removeListener(_autoFillServerHosts);
    _emailController.dispose();
    _passwordController.dispose();
    _imapHostController.dispose();
    _imapPortController.dispose();
    _smtpHostController.dispose();
    _smtpPortController.dispose();
    _signUpUsernameController.dispose();
    _firstNameController.dispose();
    _lastNameController.dispose();
    _signUpPasswordController.dispose();
    _phoneController.dispose();
    _otpController.dispose();
    _usernameDebounce?.cancel();
    super.dispose();
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

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message, style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
        backgroundColor: const Color(0xFFEF4444),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  void _onUsernameChanged(String val) {
    _usernameDebounce?.cancel();
    final clean = val.trim().toLowerCase();
    if (clean.isEmpty) {
      setState(() {
        _isCheckingUsername = false;
        _usernameAvailable = false;
        _usernameHintMessage = '3-30 lowercase characters (letters, numbers, dots).';
      });
      return;
    }

    setState(() => _isCheckingUsername = true);

    _usernameDebounce = Timer(const Duration(milliseconds: 350), () async {
      final provider = Provider.of<MailProvider>(context, listen: false);
      final res = await provider.apiService.checkUsernameAvailability(clean, domain: 'voidonyx.com');
      if (mounted) {
        setState(() {
          _isCheckingUsername = false;
          _usernameAvailable = res['available'] == true;
          _usernameHintMessage = res['message'] ?? (_usernameAvailable ? '✓ $clean@voidonyx.com is available!' : 'Username taken');
        });
      }
    });
  }

  Future<void> _handleRequestOtp() async {
    final username = _signUpUsernameController.text.trim().toLowerCase();
    final firstName = _firstNameController.text.trim();
    final lastName = _lastNameController.text.trim();
    final password = _signUpPasswordController.text;
    final phone = _phoneController.text.trim();

    if (username.length < 3) {
      _showErrorSnackBar('Please choose a username with at least 3 characters.');
      return;
    }
    if (!_usernameAvailable) {
      _showErrorSnackBar(_usernameHintMessage.isNotEmpty ? _usernameHintMessage : 'Please choose an available username first.');
      return;
    }
    if (firstName.isEmpty || lastName.isEmpty) {
      _showErrorSnackBar('Please enter both First Name and Last Name.');
      return;
    }
    if (password.length < 8) {
      _showErrorSnackBar('Password must be at least 8 characters long.');
      return;
    }
    if (phone.length < 8) {
      _showErrorSnackBar('Please enter a valid WhatsApp phone number.');
      return;
    }

    final cleanPhone = phone.replaceAll(RegExp(r'[^0-9+]'), '').trim();
    final formattedPhone = cleanPhone.startsWith('+') ? cleanPhone : '+91$cleanPhone';

    setState(() => _isRequestingOtp = true);
    final provider = Provider.of<MailProvider>(context, listen: false);
    final res = await provider.apiService.sendRegistrationOtp(
      username: username,
      firstName: firstName,
      lastName: lastName,
      password: password,
      phoneNumber: formattedPhone,
      domain: 'voidonyx.com',
    );

    if (!mounted) return;
    setState(() => _isRequestingOtp = false);

    if (res['success'] == true) {
      setState(() {
        _isOtpStep = true;
        _activeRegistrationPhone = res['phone_number'] ?? formattedPhone;
        _otpTestHint = res['test_otp_hint'] ?? (res['test_mode'] == true ? '123456' : null);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(res['message'] ?? 'Verification code sent to WhatsApp!',
              style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
          backgroundColor: const Color(0xFF10B981),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
    } else {
      _showErrorSnackBar(res['message'] ?? 'Failed to send OTP. Please check your details.');
    }
  }

  Future<void> _handleVerifyOtpAndRegister() async {
    final rawOtp = _otpController.text;
    final cleanOtp = rawOtp.replaceAll(RegExp(r'[^0-9]'), '').trim();
    final phone = _activeRegistrationPhone.isNotEmpty ? _activeRegistrationPhone : _phoneController.text.trim();
    final username = _signUpUsernameController.text.trim().toLowerCase();
    final password = _signUpPasswordController.text;

    if (cleanOtp.length < 6) {
      _showErrorSnackBar('Please enter the 6-digit verification code.');
      return;
    }

    setState(() => _isVerifyingOtp = true);
    try {
      final provider = Provider.of<MailProvider>(context, listen: false);
      final res = await provider.apiService.verifyOtpAndRegister(
        username: username,
        phoneNumber: phone,
        otp: cleanOtp,
        domain: 'voidonyx.com',
      );

      if (!mounted) return;

      if (res['success'] == true) {
        final fullEmail = res['email'] ?? '$username@voidonyx.com';
        await provider.completeRegistrationLogin(
          email: fullEmail,
          password: password,
          domain: 'voidonyx.com',
        );

        if (!mounted) return;
        setState(() => _isVerifyingOtp = false);

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('🎉 Mailbox activated on mail.voidonyx.in! Welcome, $username.',
                style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );

        Navigator.pushReplacementNamed(context, '/main');
      } else {
        setState(() => _isVerifyingOtp = false);
        _showErrorSnackBar(res['message'] ?? 'Incorrect verification code. Please try again.');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isVerifyingOtp = false);
        _showErrorSnackBar('Verification error: $e');
      }
    }
  }

  void _showDomainRestrictedDialog(String customDomain) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            const Icon(Icons.shield_outlined, color: Color(0xFFFF7A00)),
            const SizedBox(width: 8),
            Text('VoidOnyx Primary Login', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 16)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Primary sign-in is reserved for sovereign VoidOnyx accounts (@voidonyx.com or @voidonyx.in).',
              style: GoogleFonts.inter(fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFF7A00).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFF7A00).withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.business_rounded, color: Color(0xFFFF7A00), size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Custom business emails ($customDomain) can be connected inside your VoidOnyx Cloud Workspace once logged in.',
                      style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: const Color(0xFFC2410C)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Back'),
          ),
          TextButton.icon(
            onPressed: () {
              Navigator.pop(ctx);
              _loginAsDemo();
            },
            icon: const Icon(Icons.explore_rounded, size: 16, color: Color(0xFF10B981)),
            label: const Text('Try Demo Account', style: TextStyle(color: Color(0xFF10B981))),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              setState(() {
                _isSignUpMode = true;
                _isOtpStep = false;
              });
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFFF7A00),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: const Text('Create @voidonyx.com Account'),
          ),
        ],
      ),
    );
  }

  Future<void> _loginAsDemo({String email = 'demo@voidonyx.com'}) async {
    setState(() => _showAuthProgress = true);
    await Future.delayed(const Duration(milliseconds: 100));
    var overlay = _authOverlayKey.currentState;
    if (overlay != null) {
      overlay.updateStep(AuthStep.validating);
      await Future.delayed(const Duration(milliseconds: 200));
      overlay.updateStep(AuthStep.connectingImap, serverHost: 'fast.voidpanel.com:993');
      await Future.delayed(const Duration(milliseconds: 200));
      overlay.updateStep(AuthStep.syncingMailbox);
      await Future.delayed(const Duration(milliseconds: 200));
    }

    if (!mounted) return;
    final provider = Provider.of<MailProvider>(context, listen: false);
    await provider.loginAsDemo(email: email);

    if (overlay != null) {
      overlay.setComplete(provider.filteredEmails.length);
      await Future.delayed(const Duration(milliseconds: 600));
    }

    if (!mounted) return;
    setState(() => _showAuthProgress = false);
    Navigator.pushReplacementNamed(context, '/main');
  }

  Future<void> _handleLogin() async {
    var email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      _showErrorSnackBar('Please enter your email and password');
      return;
    }

    // Instant bypass for App Store review demo credentials
    final cleanEmail = email.toLowerCase();
    final cleanPass = password.toLowerCase();
    if (cleanEmail == 'demo@voidonyx.com' ||
        cleanEmail == 'demo' ||
        cleanEmail.startsWith('demo@') ||
        cleanPass == 'voidmail2026!' ||
        cleanPass == 'demopassword2026!') {
      await _loginAsDemo(email: cleanEmail.contains('@') ? cleanEmail : '$cleanEmail@voidonyx.com');
      return;
    }

    final args = ModalRoute.of(context)?.settings.arguments;
    final isAddAccount = args is Map && args['addAccount'] == true;

    // If user enters username without @, automatically append @voidonyx.com
    if (!email.contains('@')) {
      email = '$email@voidonyx.com';
      _emailController.text = email;
    }

    final domain = email.split('@').last.toLowerCase();

    // Restrict root login to VoidOnyx Sovereign domains only
    if (!isAddAccount && domain != 'voidonyx.com' && domain != 'voidonyx.in') {
      _showDomainRestrictedDialog(domain);
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

    if (!mounted) return;
    final provider = Provider.of<MailProvider>(context, listen: false);
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();
    final domain = email.contains('@') ? email.split('@')[1] : '';

    try {
      // Step 1: Validating credentials
      overlay.updateStep(AuthStep.validating);
      await Future.delayed(const Duration(milliseconds: 300));

      // Step 2: Resolving mail server
      final isVoidOnyx = (domain == 'voidonyx.com' || domain == 'voidonyx.in' || domain == 'voidpanel.com');
      final defaultHost = isVoidOnyx ? 'fast.voidpanel.com' : 'mail.$domain';
      final imapHost = _showAdvancedSettings && _imapHostController.text.isNotEmpty
          ? _imapHostController.text.trim()
          : defaultHost;
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
            : defaultHost;
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
          providerName: isVoidOnyx ? 'VoidOnyx Sovereign Mail' : 'Custom IMAP/SMTP',
        );
      } else {
        result = await provider.loginWithCustomServer(
          email: email,
          password: password,
          imapHost: imapHost,
          imapPort: imapPort,
          imapSsl: true,
          smtpHost: defaultHost,
          smtpPort: 465,
          smtpSsl: true,
          providerName: isVoidOnyx ? 'VoidOnyx Sovereign Mail' : 'VoidPanel Auto',
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
        if (isAddAccount && Navigator.of(context).canPop()) {
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
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 480),
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
                              width: 92,
                              height: 92,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(28),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFFFF7A00).withValues(alpha: 0.35),
                                    blurRadius: 26,
                                    offset: const Offset(0, 10),
                                  ),
                                ],
                              ),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(28),
                                child: Image.asset(
                                  'assets/icon/google_console_icon.png',
                                  fit: BoxFit.contain,
                                  errorBuilder: (context, error, stackTrace) {
                                    return Container(
                                      decoration: const BoxDecoration(
                                        gradient: LinearGradient(
                                          colors: [Color(0xFFFF7A00), Color(0xFFFF9E3B)],
                                          begin: Alignment.topLeft,
                                          end: Alignment.bottomRight,
                                        ),
                                      ),
                                      child: const Icon(Icons.mail_rounded, size: 46, color: Colors.white),
                                    );
                                  },
                                ),
                              ),
                            ),
                            const SizedBox(height: 20),

                            // Main Title
                            Text(
                              isAddAccount
                                  ? 'Connect Business Email'
                                  : (_isSignUpMode ? 'Create your mailbox' : 'Welcome to VoidMail'),
                              textAlign: TextAlign.center,
                              style: GoogleFonts.outfit(
                                fontSize: 26,
                                fontWeight: FontWeight.bold,
                                color: isDark ? Colors.white : const Color(0xFF1C130D),
                                letterSpacing: -0.5,
                              ),
                            ),
                            const SizedBox(height: 6),

                            // Subtitle
                            Text(
                              isAddAccount
                                  ? 'Connect your custom domain business email via IMAP/SMTP'
                                  : (_isSignUpMode
                                      ? 'Get started with an encrypted, sovereign @voidonyx.com handle'
                                      : 'Sign in to access your sovereign emails, contacts & AI'),
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(
                                fontSize: 13.5,
                                color: isDark ? Colors.grey[400] : const Color(0xFF6B5E55),
                                fontWeight: FontWeight.w400,
                              ),
                            ),
                          ],
                        ),
                      ),

                      // Auth Switcher Pills (Sign in / Create account) matching web
                      if (!isAddAccount) ...[
                        const SizedBox(height: 14),
                        Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: isDark ? const Color(0xFF1C140D) : const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0),
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              _buildAuthSwitcherBtn(
                                label: 'Sign in',
                                icon: Icons.login_rounded,
                                isActive: !_isSignUpMode,
                                onTap: () => setState(() {
                                  _isSignUpMode = false;
                                  _isOtpStep = false;
                                }),
                                isDark: isDark,
                              ),
                              _buildAuthSwitcherBtn(
                                label: 'Create account',
                                icon: Icons.person_add_alt_1_rounded,
                                isActive: _isSignUpMode,
                                onTap: () => setState(() {
                                  _isSignUpMode = true;
                                }),
                                isDark: isDark,
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: 20),

                      // Main Form Container Card
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1C140D) : Colors.white,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(
                            color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFFED7AA).withValues(alpha: 0.5),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.04),
                              blurRadius: 20,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: _isSignUpMode
                            ? (_isOtpStep ? _buildOtpVerificationCard(isDark) : _buildSignUpForm(isDark))
                            : Column(
                                children: [
                                  // Email Input Field
                                  TextFormField(
                                    controller: _emailController,
                                    style: GoogleFonts.inter(fontSize: 14),
                                    decoration: InputDecoration(
                                      hintText: isAddAccount ? 'you@yourcompany.com' : 'username@voidonyx.com',
                                      hintStyle: GoogleFonts.inter(fontSize: 14, color: const Color(0xFF94A3B8)),
                                prefixIcon: Padding(
                                  padding: const EdgeInsets.all(8.0),
                                  child: Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFFF7A00),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: const Icon(Icons.mail_rounded, size: 16, color: Colors.white),
                                  ),
                                ),
                                filled: true,
                                fillColor: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
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
                                      color: const Color(0xFFFF7A00),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: const Icon(Icons.lock_rounded, size: 16, color: Colors.white),
                                  ),
                                ),
                                suffixIcon: IconButton(
                                  icon: Icon(
                                    _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                                    color: const Color(0xFFFF7A00),
                                    size: 20,
                                  ),
                                  onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                                ),
                                filled: true,
                                fillColor: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                  borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                ),
                              ),
                            ),

                            const SizedBox(height: 12),

                            // Remember me & Advanced Link Row
                            Wrap(
                              alignment: WrapAlignment.spaceBetween,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Checkbox(
                                      value: _rememberMe,
                                      onChanged: (val) => setState(() => _rememberMe = val ?? true),
                                      activeColor: const Color(0xFFFF7A00),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
                                    ),
                                    Text(
                                      'Remember me',
                                      style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500, color: const Color(0xFF475569)),
                                    ),
                                  ],
                                ),
                                GestureDetector(
                                  onTap: () {
                                    setState(() {
                                      _showAdvancedSettings = !_showAdvancedSettings;
                                    });
                                  },
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(vertical: 4),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        const Icon(Icons.tune_rounded, size: 15, color: Color(0xFFFF7A00)),
                                        const SizedBox(width: 4),
                                        Text(
                                          _showAdvancedSettings ? 'Hide Advanced' : 'Advanced (IMAP/SMTP)',
                                          style: GoogleFonts.inter(
                                            fontSize: 12,
                                            fontWeight: FontWeight.bold,
                                            color: const Color(0xFFFF7A00),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),

                            // Collapsible Advanced Settings (IMAP & SMTP)
                            AnimatedSize(
                              duration: const Duration(milliseconds: 300),
                              curve: Curves.easeInOut,
                              child: _showAdvancedSettings
                                ? Padding(
                                    padding: const EdgeInsets.only(top: 14),
                                    child: Container(
                                      padding: const EdgeInsets.all(16),
                                      decoration: BoxDecoration(
                                        color: isDark ? const Color(0xFF160E08) : const Color(0xFFFFFBF5),
                                        borderRadius: BorderRadius.circular(18),
                                        border: Border.all(color: const Color(0xFFFF7A00).withOpacity(0.25)),
                                        boxShadow: [
                                          BoxShadow(
                                            color: const Color(0xFFFF7A00).withOpacity(0.06),
                                            blurRadius: 12,
                                            offset: const Offset(0, 4),
                                          ),
                                        ],
                                      ),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          // Header
                                          Row(
                                            children: [
                                              Container(
                                                padding: const EdgeInsets.all(7),
                                                decoration: BoxDecoration(
                                                  gradient: LinearGradient(
                                                    colors: [const Color(0xFFFF7A00).withOpacity(0.2), const Color(0xFFFF9E3B).withOpacity(0.1)],
                                                  ),
                                                  borderRadius: BorderRadius.circular(10),
                                                ),
                                                child: const Icon(Icons.dns_rounded, size: 16, color: Color(0xFFFF7A00)),
                                              ),
                                              const SizedBox(width: 10),
                                              Expanded(
                                                child: Column(
                                                  crossAxisAlignment: CrossAxisAlignment.start,
                                                  children: [
                                                    Text(
                                                      'Custom Mail Server',
                                                      style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold, color: isDark ? Colors.white : const Color(0xFF0F172A)),
                                                    ),
                                                    Text(
                                                      'Configure IMAP & SMTP manually',
                                                      style: GoogleFonts.inter(fontSize: 10, color: const Color(0xFF94A3B8)),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 14),

                                          // ── 1. IMAP Incoming Server ──
                                          Container(
                                            padding: const EdgeInsets.all(14),
                                            decoration: BoxDecoration(
                                              color: isDark ? const Color(0xFF1F140C) : Colors.white,
                                              borderRadius: BorderRadius.circular(14),
                                              border: Border.all(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                            ),
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                // Section title row
                                                Row(
                                                  children: [
                                                    Container(
                                                      padding: const EdgeInsets.all(5),
                                                      decoration: BoxDecoration(
                                                        color: const Color(0xFF6366F1).withOpacity(0.12),
                                                        borderRadius: BorderRadius.circular(7),
                                                      ),
                                                      child: const Icon(Icons.move_to_inbox_rounded, size: 14, color: Color(0xFF6366F1)),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    Expanded(
                                                      child: Text(
                                                        'IMAP Incoming Server',
                                                        style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: isDark ? Colors.white : const Color(0xFF0F172A)),
                                                      ),
                                                    ),
                                                    // SSL Chip
                                                    GestureDetector(
                                                      onTap: () {
                                                        setState(() {
                                                          _imapSsl = !_imapSsl;
                                                          if (_imapSsl && _imapPortController.text == '143') {
                                                            _imapPortController.text = '993';
                                                          } else if (!_imapSsl && _imapPortController.text == '993') {
                                                            _imapPortController.text = '143';
                                                          }
                                                        });
                                                      },
                                                      child: Container(
                                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                        decoration: BoxDecoration(
                                                          color: _imapSsl
                                                              ? const Color(0xFF10B981).withOpacity(0.12)
                                                              : const Color(0xFFEF4444).withOpacity(0.12),
                                                          borderRadius: BorderRadius.circular(20),
                                                          border: Border.all(
                                                            color: _imapSsl
                                                                ? const Color(0xFF10B981).withOpacity(0.3)
                                                                : const Color(0xFFEF4444).withOpacity(0.3),
                                                          ),
                                                        ),
                                                        child: Row(
                                                          mainAxisSize: MainAxisSize.min,
                                                          children: [
                                                            Icon(
                                                              _imapSsl ? Icons.lock_rounded : Icons.lock_open_rounded,
                                                              size: 11,
                                                              color: _imapSsl ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                                            ),
                                                            const SizedBox(width: 3),
                                                            Text(
                                                              _imapSsl ? 'SSL' : 'Plain',
                                                              style: GoogleFonts.inter(
                                                                fontSize: 10,
                                                                fontWeight: FontWeight.bold,
                                                                color: _imapSsl ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                                              ),
                                                            ),
                                                          ],
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                                const SizedBox(height: 10),
                                                // Host & Port
                                                Row(
                                                  children: [
                                                    Expanded(
                                                      flex: 3,
                                                      child: TextFormField(
                                                        controller: _imapHostController,
                                                        style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500),
                                                        decoration: InputDecoration(
                                                          labelText: 'Hostname',
                                                          labelStyle: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8)),
                                                          hintText: 'mail.domain.com',
                                                          hintStyle: GoogleFonts.inter(fontSize: 12, color: const Color(0xFFCBD5E1)),
                                                          isDense: true,
                                                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                                                          filled: true,
                                                          fillColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF8FAFC),
                                                          border: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          enabledBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          focusedBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: const BorderSide(color: Color(0xFF6366F1), width: 1.5),
                                                          ),
                                                        ),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    SizedBox(
                                                      width: 64,
                                                      child: TextFormField(
                                                        controller: _imapPortController,
                                                        keyboardType: TextInputType.number,
                                                        textAlign: TextAlign.center,
                                                        style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600),
                                                        decoration: InputDecoration(
                                                          labelText: 'Port',
                                                          labelStyle: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8)),
                                                          isDense: true,
                                                          contentPadding: const EdgeInsets.symmetric(horizontal: 6, vertical: 11),
                                                          filled: true,
                                                          fillColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF8FAFC),
                                                          border: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          enabledBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          focusedBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: const BorderSide(color: Color(0xFF6366F1), width: 1.5),
                                                          ),
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ],
                                            ),
                                          ),

                                          const SizedBox(height: 10),

                                          // ── 2. SMTP Outgoing Server ──
                                          Container(
                                            padding: const EdgeInsets.all(14),
                                            decoration: BoxDecoration(
                                              color: isDark ? const Color(0xFF1F140C) : Colors.white,
                                              borderRadius: BorderRadius.circular(14),
                                              border: Border.all(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                            ),
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                // Section title row
                                                Row(
                                                  children: [
                                                    Container(
                                                      padding: const EdgeInsets.all(5),
                                                      decoration: BoxDecoration(
                                                        color: const Color(0xFF10B981).withOpacity(0.12),
                                                        borderRadius: BorderRadius.circular(7),
                                                      ),
                                                      child: const Icon(Icons.outbox_rounded, size: 14, color: Color(0xFF10B981)),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    Expanded(
                                                      child: Text(
                                                        'SMTP Outgoing Server',
                                                        style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: isDark ? Colors.white : const Color(0xFF0F172A)),
                                                      ),
                                                    ),
                                                    // SSL Chip
                                                    GestureDetector(
                                                      onTap: () {
                                                        setState(() {
                                                          _smtpSsl = !_smtpSsl;
                                                          if (_smtpSsl && (_smtpPortController.text == '587' || _smtpPortController.text == '25')) {
                                                            _smtpPortController.text = '465';
                                                          } else if (!_smtpSsl && _smtpPortController.text == '465') {
                                                            _smtpPortController.text = '587';
                                                          }
                                                        });
                                                      },
                                                      child: Container(
                                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                        decoration: BoxDecoration(
                                                          color: _smtpSsl
                                                              ? const Color(0xFF10B981).withOpacity(0.12)
                                                              : const Color(0xFFEF4444).withOpacity(0.12),
                                                          borderRadius: BorderRadius.circular(20),
                                                          border: Border.all(
                                                            color: _smtpSsl
                                                                ? const Color(0xFF10B981).withOpacity(0.3)
                                                                : const Color(0xFFEF4444).withOpacity(0.3),
                                                          ),
                                                        ),
                                                        child: Row(
                                                          mainAxisSize: MainAxisSize.min,
                                                          children: [
                                                            Icon(
                                                              _smtpSsl ? Icons.lock_rounded : Icons.lock_open_rounded,
                                                              size: 11,
                                                              color: _smtpSsl ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                                            ),
                                                            const SizedBox(width: 3),
                                                            Text(
                                                              _smtpSsl ? 'SSL' : 'Plain',
                                                              style: GoogleFonts.inter(
                                                                fontSize: 10,
                                                                fontWeight: FontWeight.bold,
                                                                color: _smtpSsl ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                                                              ),
                                                            ),
                                                          ],
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                                const SizedBox(height: 10),
                                                // Host & Port
                                                Row(
                                                  children: [
                                                    Expanded(
                                                      flex: 3,
                                                      child: TextFormField(
                                                        controller: _smtpHostController,
                                                        style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500),
                                                        decoration: InputDecoration(
                                                          labelText: 'Hostname',
                                                          labelStyle: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8)),
                                                          hintText: 'mail.domain.com',
                                                          hintStyle: GoogleFonts.inter(fontSize: 12, color: const Color(0xFFCBD5E1)),
                                                          isDense: true,
                                                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                                                          filled: true,
                                                          fillColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF8FAFC),
                                                          border: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          enabledBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          focusedBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: const BorderSide(color: Color(0xFF10B981), width: 1.5),
                                                          ),
                                                        ),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    SizedBox(
                                                      width: 64,
                                                      child: TextFormField(
                                                        controller: _smtpPortController,
                                                        keyboardType: TextInputType.number,
                                                        textAlign: TextAlign.center,
                                                        style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600),
                                                        decoration: InputDecoration(
                                                          labelText: 'Port',
                                                          labelStyle: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF94A3B8)),
                                                          isDense: true,
                                                          contentPadding: const EdgeInsets.symmetric(horizontal: 6, vertical: 11),
                                                          filled: true,
                                                          fillColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF8FAFC),
                                                          border: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          enabledBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
                                                          ),
                                                          focusedBorder: OutlineInputBorder(
                                                            borderRadius: BorderRadius.circular(10),
                                                            borderSide: const BorderSide(color: Color(0xFF10B981), width: 1.5),
                                                          ),
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  )
                                : const SizedBox.shrink(),
                            ),



                            const SizedBox(height: 20),

                            // Primary Sign In Button (Flame Orange Gradient Pill)
                            Container(
                              width: double.infinity,
                              height: 52,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFF7A00), Color(0xFFFF9E3B)],
                                ),
                                borderRadius: BorderRadius.circular(18),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFFFF7A00).withValues(alpha: 0.35),
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
                            const SizedBox(height: 12),

                            // Quick Demo / Reviewer Access Button
                            SizedBox(
                              width: double.infinity,
                              height: 48,
                              child: OutlinedButton.icon(
                                onPressed: _showAuthProgress ? null : () => _loginAsDemo(),
                                icon: const Icon(Icons.explore_rounded, color: Color(0xFF10B981), size: 18),
                                label: Text(
                                  'Explore with Demo Account',
                                  style: GoogleFonts.inter(
                                    color: const Color(0xFF10B981),
                                    fontWeight: FontWeight.w600,
                                    fontSize: 14,
                                  ),
                                ),
                                style: OutlinedButton.styleFrom(
                                  side: const BorderSide(color: Color(0xFF10B981), width: 1.4),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                  backgroundColor: const Color(0xFF10B981).withValues(alpha: isDark ? 0.08 : 0.04),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Auth Switcher Footer Link (matching web)
                      if (!isAddAccount)
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              _isSignUpMode ? 'Already have a sovereign mailbox? ' : "Don't have an address yet? ",
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: isDark ? Colors.grey[400] : const Color(0xFF6B5E55),
                              ),
                            ),
                            GestureDetector(
                              onTap: () => setState(() {
                                _isSignUpMode = !_isSignUpMode;
                                _isOtpStep = false;
                              }),
                              child: Text(
                                _isSignUpMode ? 'Sign in' : 'Get your @voidonyx.com email',
                                style: GoogleFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: const Color(0xFFFF7A00),
                                ),
                              ),
                            ),
                          ],
                        ),
                      const SizedBox(height: 16),

                      // Security Footer
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.verified_user_rounded, size: 16, color: Color(0xFFFF7A00)),
                          const SizedBox(width: 8),
                          Text(
                            'TLS 1.3 / SSL Encrypted • Direct IMAP & SMTP',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: isDark ? Colors.grey[500] : const Color(0xFF8C7A6B),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
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
              onDemoMode: () {
                setState(() => _showAuthProgress = false);
                _loginAsDemo();
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

  // ══════════════════════════════════════════════════════════════════════
  //  SIGN UP & ONBOARDING WIDGET BUILDERS (MATCHING WEB SIGNUP.HTML)
  // ══════════════════════════════════════════════════════════════════════

  Widget _buildAuthSwitcherBtn({
    required String label,
    required IconData icon,
    required bool isActive,
    required VoidCallback onTap,
    required bool isDark,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
        decoration: BoxDecoration(
          color: isActive ? const Color(0xFFFF7A00) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          boxShadow: isActive
              ? [
                  BoxShadow(
                    color: const Color(0xFFFF7A00).withValues(alpha: 0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color: isActive ? Colors.white : (isDark ? Colors.white60 : Colors.black54),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
                color: isActive ? Colors.white : (isDark ? Colors.white70 : Colors.black87),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSignUpEmailInput(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Choose Your Email Address',
          style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w600, color: isDark ? Colors.white70 : const Color(0xFF334155)),
        ),
        const SizedBox(height: 6),
        Container(
          height: 48,
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: _usernameAvailable
                  ? const Color(0xFF10B981)
                  : (_isCheckingUsername
                      ? const Color(0xFFFF7A00)
                      : (isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
              width: _usernameAvailable ? 1.5 : 1.0,
            ),
          ),
          child: Row(
            children: [
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12),
                child: Icon(
                  Icons.alternate_email_rounded,
                  size: 18,
                  color: Color(0xFFFF7A00),
                ),
              ),
              Expanded(
                child: TextField(
                  controller: _signUpUsernameController,
                  onChanged: _onUsernameChanged,
                  style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
                  decoration: const InputDecoration(
                    hintText: 'username',
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                margin: const EdgeInsets.only(right: 6),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFFFEDD5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '@voidonyx.com',
                  style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: const Color(0xFFFF7A00)),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 5),
        Row(
          children: [
            if (_isCheckingUsername) ...[
              const SizedBox(
                width: 10,
                height: 10,
                child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFFFF7A00)),
              ),
              const SizedBox(width: 6),
            ] else if (_usernameAvailable) ...[
              const Icon(Icons.check_circle_rounded, size: 12, color: Color(0xFF10B981)),
              const SizedBox(width: 4),
            ] else if (_signUpUsernameController.text.isNotEmpty) ...[
              const Icon(Icons.info_outline_rounded, size: 12, color: Color(0xFFEF4444)),
              const SizedBox(width: 4),
            ],
            Expanded(
              child: Text(
                _usernameHintMessage,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: _usernameAvailable
                      ? const Color(0xFF10B981)
                      : (_signUpUsernameController.text.isNotEmpty
                          ? const Color(0xFFEF4444)
                          : (isDark ? Colors.grey[500] : Colors.grey[600])),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSignUpForm(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSignUpEmailInput(isDark),
        const SizedBox(height: 14),

        // First Name & Last Name (2 columns)
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'First Name',
                    style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w600, color: isDark ? Colors.white70 : const Color(0xFF334155)),
                  ),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: _firstNameController,
                    style: GoogleFonts.inter(fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Rohan',
                      hintStyle: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF94A3B8)),
                      filled: true,
                      fillColor: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Last Name',
                    style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w600, color: isDark ? Colors.white70 : const Color(0xFF334155)),
                  ),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: _lastNameController,
                    style: GoogleFonts.inter(fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Rawat',
                      hintStyle: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF94A3B8)),
                      filled: true,
                      fillColor: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),

        const SizedBox(height: 14),

        // Set Password
        Text(
          'Set Password (min 8 chars)',
          style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w600, color: isDark ? Colors.white70 : const Color(0xFF334155)),
        ),
        const SizedBox(height: 6),
        TextFormField(
          controller: _signUpPasswordController,
          obscureText: _obscureSignUpPassword,
          style: GoogleFonts.inter(fontSize: 14),
          decoration: InputDecoration(
            hintText: '••••••••',
            hintStyle: GoogleFonts.inter(fontSize: 14, color: const Color(0xFF94A3B8)),
            prefixIcon: const Icon(Icons.lock_rounded, size: 18, color: Color(0xFFFF7A00)),
            suffixIcon: IconButton(
              icon: Icon(
                _obscureSignUpPassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                color: const Color(0xFFFF7A00),
                size: 20,
              ),
              onPressed: () => setState(() => _obscureSignUpPassword = !_obscureSignUpPassword),
            ),
            filled: true,
            fillColor: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
          ),
        ),

        const SizedBox(height: 14),

        // WhatsApp Phone
        Text(
          'WhatsApp Number (Instant Verification)',
          style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w600, color: isDark ? Colors.white70 : const Color(0xFF334155)),
        ),
        const SizedBox(height: 6),
        TextFormField(
          controller: _phoneController,
          keyboardType: TextInputType.phone,
          style: GoogleFonts.inter(fontSize: 14),
          decoration: InputDecoration(
            hintText: '+91 9876543210',
            hintStyle: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF94A3B8)),
            prefixIcon: const Icon(Icons.phone_iphone_rounded, size: 18, color: Color(0xFF10B981)),
            filled: true,
            fillColor: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0))),
          ),
        ),

        const SizedBox(height: 20),

        // Continue to Verification Button
        Container(
          width: double.infinity,
          height: 52,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFFF7A00), Color(0xFFFF9E3B)],
            ),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFFF7A00).withValues(alpha: 0.35),
                blurRadius: 14,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: ElevatedButton(
            onPressed: _isRequestingOtp ? null : _handleRequestOtp,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.transparent,
              shadowColor: Colors.transparent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            ),
            child: _isRequestingOtp
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'Continue to Verification',
                        style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                      ),
                      const SizedBox(width: 8),
                      const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 18),
                    ],
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildOtpVerificationCard(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back_rounded, size: 18),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
              onPressed: () => setState(() => _isOtpStep = false),
            ),
            const SizedBox(width: 8),
            Text(
              'Verify WhatsApp OTP',
              style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold, color: isDark ? Colors.white : const Color(0xFF0F172A)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'We sent a 6-digit verification code to ${_activeRegistrationPhone.isNotEmpty ? _activeRegistrationPhone : _phoneController.text.trim()}',
          style: GoogleFonts.inter(fontSize: 12.5, color: isDark ? Colors.grey[400] : const Color(0xFF64748B)),
        ),
        const SizedBox(height: 10),
        if (_otpTestHint != null) ...[
          InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: () {
              setState(() {
                _otpController.text = _otpTestHint!;
              });
              _handleVerifyOtpAndRegister();
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.touch_app_rounded, size: 14, color: Color(0xFF10B981)),
                  const SizedBox(width: 6),
                  Text(
                    'Test Mode: Tap to auto-fill $_otpTestHint',
                    style: GoogleFonts.inter(fontSize: 11.5, fontWeight: FontWeight.bold, color: const Color(0xFF065F46)),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
        TextField(
          controller: _otpController,
          keyboardType: TextInputType.number,
          maxLength: 6,
          textAlign: TextAlign.center,
          onChanged: (val) {
            final cleaned = val.replaceAll(RegExp(r'[^0-9]'), '');
            if (cleaned.length == 6 && !_isVerifyingOtp) {
              _handleVerifyOtpAndRegister();
            }
          },
          style: GoogleFonts.inter(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 8),
          decoration: InputDecoration(
            counterText: '',
            hintText: '••••••',
            hintStyle: GoogleFonts.inter(letterSpacing: 8, color: Colors.grey),
            filled: true,
            fillColor: isDark ? const Color(0xFF130D08) : const Color(0xFFFFFBF5),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: BorderSide(color: isDark ? const Color(0xFF2E1F14) : const Color(0xFFE2E8F0)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: const BorderSide(color: Color(0xFFFF7A00), width: 1.5),
            ),
          ),
        ),
        const SizedBox(height: 20),
        Container(
          width: double.infinity,
          height: 50,
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF10B981), Color(0xFF059669)]),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF10B981).withValues(alpha: 0.3),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ElevatedButton(
            onPressed: _isVerifyingOtp ? null : _handleVerifyOtpAndRegister,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.transparent,
              shadowColor: Colors.transparent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: _isVerifyingOtp
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.check_circle_rounded, color: Colors.white, size: 18),
                      const SizedBox(width: 8),
                      Text('Verify & Enter Mailbox', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white)),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: 12),
        Center(
          child: TextButton(
            onPressed: () => setState(() => _isOtpStep = false),
            child: Text('Edit registration details', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFFFF7A00))),
          ),
        ),
      ],
    );
  }
}
