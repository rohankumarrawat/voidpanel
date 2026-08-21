import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/mail_provider.dart';
import '../services/notification_service.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeIn),
    );

    _scaleAnimation = Tween<double>(begin: 0.85, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutBack),
    );

    _controller.forward();

    // Request notification permissions after first frame is safely rendered
    WidgetsBinding.instance.addPostFrameCallback((_) {
      NotificationService().requestPermissions();
    });

    Future.delayed(const Duration(milliseconds: 2500), () async {
      if (!mounted) return;
      try {
        final provider = Provider.of<MailProvider>(context, listen: false);
        // Give saved accounts a moment to load
        if (!provider.isLoggedIn) {
          await Future.delayed(const Duration(milliseconds: 500));
        }
        if (!mounted) return;
        if (provider.isLoggedIn) {
          Navigator.pushReplacementNamed(context, '/main');
        } else {
          Navigator.pushReplacementNamed(context, '/welcome');
        }
      } catch (e) {
        debugPrint('[SplashScreen] Navigation notice: $e');
        if (mounted) {
          Navigator.pushReplacementNamed(context, '/welcome');
        }
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Center(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              return FadeTransition(
                opacity: _fadeAnimation,
                child: ScaleTransition(
                  scale: _scaleAnimation,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Spacer(),

                      // 3D Glassmorphism Mail Icon Asset
                      Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(32),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF6C5CE7).withValues(alpha: 0.18),
                              blurRadius: 30,
                              offset: const Offset(0, 12),
                            ),
                          ],
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(32),
                          child: Image.asset(
                            'assets/icon/google_console_icon.png',
                            width: 120,
                            height: 120,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) {
                              return Image.asset(
                                'assets/google_console_icon.png',
                                width: 120,
                                height: 120,
                                fit: BoxFit.cover,
                                errorBuilder: (context, e2, st2) {
                                  return Container(
                                    color: const Color(0xFF6366F1),
                                    child: const Icon(Icons.mark_email_unread_rounded, size: 64, color: Colors.white),
                                  );
                                },
                              );
                            },
                          ),
                        ),
                      ),
                      const SizedBox(height: 28),

                      // Title
                      Text(
                        'VoidOnyx Mail',
                        style: GoogleFonts.outfit(
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          color: const Color(0xFF0F172A),
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 8),

                      // Subtitle
                      Text(
                        'Universal Mobile Email Client',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: const Color(0xFF64748B),
                        ),
                      ),

                      const Spacer(),

                      // Bottom Branding Badge
                      Container(
                        margin: const EdgeInsets.only(bottom: 24),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                color: Color(0xFF10B981),
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Powered by ',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: const Color(0xFF64748B),
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            Text(
                              'VoidPanel Enterprise',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: const Color(0xFF0F172A),
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
