import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Represents a single step in the authentication process
enum AuthStep {
  validating,
  resolvingServer,
  connectingImap,
  authenticatingImap,
  syncingMailbox,
  connectingSmtp,
  authenticatingSmtp,
  complete,
  failed,
}

/// Model for each step's display properties
class AuthStepInfo {
  final AuthStep step;
  final IconData icon;
  final String title;
  final String subtitle;

  const AuthStepInfo({
    required this.step,
    required this.icon,
    required this.title,
    required this.subtitle,
  });
}

/// Beautiful animated authentication progress overlay with scroll support
class AuthProgressOverlay extends StatefulWidget {
  final VoidCallback? onDismiss;
  final VoidCallback? onRetry;

  const AuthProgressOverlay({
    super.key,
    this.onDismiss,
    this.onRetry,
  });

  @override
  State<AuthProgressOverlay> createState() => AuthProgressOverlayState();
}

class AuthProgressOverlayState extends State<AuthProgressOverlay>
    with TickerProviderStateMixin {
  AuthStep _currentStep = AuthStep.validating;
  String? _errorMessage;
  String? _errorDetail;
  int _emailCount = 0;
  String _serverHost = '';

  late AnimationController _pulseController;
  late AnimationController _fadeController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _fadeAnimation;

  static const _steps = <AuthStepInfo>[
    AuthStepInfo(
      step: AuthStep.validating,
      icon: Icons.verified_user_rounded,
      title: 'Validating credentials',
      subtitle: 'Checking email format & password...',
    ),
    AuthStepInfo(
      step: AuthStep.resolvingServer,
      icon: Icons.dns_rounded,
      title: 'Resolving mail server',
      subtitle: 'Discovering IMAP & SMTP endpoints...',
    ),
    AuthStepInfo(
      step: AuthStep.connectingImap,
      icon: Icons.cloud_outlined,
      title: 'Connecting to IMAP',
      subtitle: 'Establishing secure TLS connection...',
    ),
    AuthStepInfo(
      step: AuthStep.authenticatingImap,
      icon: Icons.lock_open_rounded,
      title: 'Authenticating IMAP',
      subtitle: 'Verifying inbox access...',
    ),
    AuthStepInfo(
      step: AuthStep.syncingMailbox,
      icon: Icons.sync_rounded,
      title: 'Syncing mailbox',
      subtitle: 'Fetching your latest emails...',
    ),
    AuthStepInfo(
      step: AuthStep.connectingSmtp,
      icon: Icons.outgoing_mail,
      title: 'Connecting to SMTP',
      subtitle: 'Setting up outgoing mail server...',
    ),
    AuthStepInfo(
      step: AuthStep.authenticatingSmtp,
      icon: Icons.mark_email_read_rounded,
      title: 'Authenticating SMTP',
      subtitle: 'Verifying send permission...',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.6, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _fadeController, curve: Curves.easeOut),
    );
    _fadeController.forward();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  void updateStep(AuthStep step, {String? serverHost}) {
    if (!mounted) return;
    setState(() {
      _currentStep = step;
      if (serverHost != null) _serverHost = serverHost;
    });
  }

  void setComplete(int emailCount) {
    if (!mounted) return;
    _pulseController.stop();
    setState(() {
      _currentStep = AuthStep.complete;
      _emailCount = emailCount;
    });
  }

  void setError(String message, {String? detail}) {
    if (!mounted) return;
    _pulseController.stop();
    setState(() {
      _currentStep = AuthStep.failed;
      _errorMessage = message;
      _errorDetail = detail;
    });
  }

  int _stepIndex(AuthStep step) {
    return _steps.indexWhere((s) => s.step == step);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return FadeTransition(
      opacity: _fadeAnimation,
      child: Container(
        color: (isDark ? Colors.black : Colors.white).withValues(alpha: 0.92),
        child: Center(
          child: Container(
            width: 360,
            constraints: const BoxConstraints(maxHeight: 560),
            margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF16122E) : Colors.white,
              borderRadius: BorderRadius.circular(28),
              border: Border.all(
                color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEFEFF6),
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF6C5CE7).withValues(alpha: 0.12),
                  blurRadius: 40,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Header icon
                  _buildHeaderIcon(isDark),
                  const SizedBox(height: 16),

                  // Title
                  Text(
                    _currentStep == AuthStep.complete
                        ? 'Connected! 🎉'
                        : _currentStep == AuthStep.failed
                            ? 'Connection Failed'
                            : 'Connecting...',
                    style: GoogleFonts.inter(
                      fontSize: 19,
                      fontWeight: FontWeight.w800,
                      color: _currentStep == AuthStep.failed
                          ? const Color(0xFFEF4444)
                          : (isDark ? Colors.white : const Color(0xFF1E1B4B)),
                    ),
                  ),
                  const SizedBox(height: 4),

                  if (_serverHost.isNotEmpty && _currentStep != AuthStep.failed)
                    Text(
                      _serverHost,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: isDark ? Colors.grey[400] : const Color(0xFF9CA3AF),
                      ),
                    ),

                  const SizedBox(height: 16),

                  // Steps timeline
                  if (_currentStep != AuthStep.complete && _currentStep != AuthStep.failed)
                    _buildStepsList(isDark),

                  // Success state
                  if (_currentStep == AuthStep.complete)
                    _buildSuccessState(isDark),

                  // Error state
                  if (_currentStep == AuthStep.failed)
                    _buildErrorState(isDark),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderIcon(bool isDark) {
    final Color iconBg;
    final IconData iconData;
    final Color iconColor;

    if (_currentStep == AuthStep.complete) {
      iconBg = const Color(0xFF10B981);
      iconData = Icons.check_circle_rounded;
      iconColor = Colors.white;
    } else if (_currentStep == AuthStep.failed) {
      iconBg = const Color(0xFFEF4444);
      iconData = Icons.error_rounded;
      iconColor = Colors.white;
    } else {
      iconBg = const Color(0xFF6C5CE7);
      iconData = Icons.shield_rounded;
      iconColor = Colors.white;
    }

    return AnimatedBuilder(
      listenable: _pulseAnimation,
      builder: (context, child) {
        final scale = _currentStep == AuthStep.complete || _currentStep == AuthStep.failed
            ? 1.0
            : _pulseAnimation.value * 0.15 + 0.85;
        return Transform.scale(
          scale: scale,
          child: Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: iconBg,
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(
                  color: iconBg.withValues(alpha: 0.35),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Icon(iconData, size: 28, color: iconColor),
          ),
        );
      },
    );
  }

  Widget _buildStepsList(bool isDark) {
    final currentIdx = _stepIndex(_currentStep);

    return Column(
      children: List.generate(_steps.length, (i) {
        final info = _steps[i];
        final isActive = i == currentIdx;
        final isDone = i < currentIdx;
        final isPending = i > currentIdx;

        return AnimatedContainer(
          duration: const Duration(milliseconds: 350),
          curve: Curves.easeOut,
          margin: const EdgeInsets.only(bottom: 2),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: isActive
                ? const Color(0xFF6C5CE7).withValues(alpha: isDark ? 0.15 : 0.08)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            children: [
              // Status icon
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: 26,
                height: 26,
                decoration: BoxDecoration(
                  color: isDone
                      ? const Color(0xFF10B981)
                      : isActive
                          ? const Color(0xFF6C5CE7)
                          : (isDark ? const Color(0xFF2C2554) : const Color(0xFFE5E7EB)),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: isDone
                    ? const Icon(Icons.check_rounded, size: 15, color: Colors.white)
                    : isActive
                        ? AnimatedBuilder(
                            listenable: _pulseAnimation,
                            builder: (context, child) {
                              return Opacity(
                                opacity: _pulseAnimation.value,
                                child: Icon(info.icon, size: 14, color: Colors.white),
                              );
                            },
                          )
                        : Icon(info.icon, size: 13,
                            color: isDark ? Colors.grey[600] : const Color(0xFFD1D5DB)),
              ),
              const SizedBox(width: 10),

              // Text
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      info.title,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
                        color: isPending
                            ? (isDark ? Colors.grey[600] : const Color(0xFFD1D5DB))
                            : isDone
                                ? const Color(0xFF10B981)
                                : (isDark ? Colors.white : const Color(0xFF1E1B4B)),
                      ),
                    ),
                    if (isActive)
                      Text(
                        info.subtitle,
                        style: GoogleFonts.inter(
                          fontSize: 10,
                          color: isDark ? Colors.grey[400] : const Color(0xFF9CA3AF),
                        ),
                      ),
                  ],
                ),
              ),

              // Active spinner
              if (isActive)
                SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: const Color(0xFF6C5CE7).withValues(alpha: 0.7),
                  ),
                ),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildSuccessState(bool isDark) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF10B981).withValues(alpha: isDark ? 0.12 : 0.06),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              const Icon(Icons.inbox_rounded, color: Color(0xFF10B981), size: 26),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$_emailCount emails synced',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: const Color(0xFF059669),
                      ),
                    ),
                    Text(
                      'IMAP & SMTP ready',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Text(
          'Redirecting to inbox...',
          style: GoogleFonts.inter(
            fontSize: 11,
            color: isDark ? Colors.grey[500] : const Color(0xFF9CA3AF),
          ),
        ),
      ],
    );
  }

  Widget _buildErrorState(bool isDark) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFFEF4444).withValues(alpha: isDark ? 0.12 : 0.06),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Color(0xFFEF4444), size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage ?? 'Authentication failed',
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: const Color(0xFFDC2626),
                      ),
                    ),
                  ),
                ],
              ),
              if (_errorDetail != null) ...[
                const SizedBox(height: 6),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1B1638) : const Color(0xFFFEF2F2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    _errorDetail!,
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      color: isDark ? Colors.grey[400] : const Color(0xFF991B1B),
                    ),
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: widget.onDismiss,
                icon: const Icon(Icons.arrow_back_rounded, size: 16),
                label: Text('Go Back', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600)),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  side: BorderSide(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE5E7EB)),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF6C5CE7), Color(0xFF8C7CFF)],
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: ElevatedButton.icon(
                  onPressed: widget.onRetry,
                  icon: const Icon(Icons.refresh_rounded, size: 16, color: Colors.white),
                  label: Text('Retry',
                      style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.transparent,
                    shadowColor: Colors.transparent,
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Custom AnimatedBuilder helper to avoid framework name clash
class AnimatedBuilder extends StatelessWidget {
  final Listenable listenable;
  final Widget Function(BuildContext context, Widget? child) builder;
  final Widget? child;

  const AnimatedBuilder({
    super.key,
    required this.listenable,
    required this.builder,
    this.child,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedWidget(
      listenable: listenable,
      builder: builder,
      child: child,
    );
  }
}

/// Simple AnimatedWidget wrapper
class AnimatedWidget extends StatefulWidget {
  final Listenable listenable;
  final Widget Function(BuildContext context, Widget? child) builder;
  final Widget? child;

  const AnimatedWidget({
    super.key,
    required this.listenable,
    required this.builder,
    this.child,
  });

  @override
  State<AnimatedWidget> createState() => _AnimatedWidgetState();
}

class _AnimatedWidgetState extends State<AnimatedWidget> {
  @override
  void initState() {
    super.initState();
    widget.listenable.addListener(_handleChange);
  }

  @override
  void dispose() {
    widget.listenable.removeListener(_handleChange);
    super.dispose();
  }

  void _handleChange() {
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return widget.builder(context, widget.child);
  }
}
