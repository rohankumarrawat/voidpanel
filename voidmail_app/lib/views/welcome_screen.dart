import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/mail_provider.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<Map<String, dynamic>> _slides = [
    {
      'title1': 'Smart Email.',
      'title2': 'Simplified.',
      'subtitle': 'All your emails, contacts and productivity tools in one powerful app.',
      'type': 'main',
    },
    {
      'title1': 'VoidOnyx AI.',
      'title2': 'Write Faster.',
      'subtitle': 'Draft, reply and summarize emails automatically with built-in AI assistance.',
      'type': 'ai',
    },
    {
      'title1': 'Primary Inbox.',
      'title2': 'Unified View.',
      'subtitle': 'Connect Gmail, Outlook, VoidPanel & custom IMAP accounts in one place.',
      'type': 'unified',
    },
    {
      'title1': 'Privacy First.',
      'title2': 'Zero Latency.',
      'subtitle': 'Direct server connectivity with instant cache-first performance and security.',
      'type': 'security',
    },
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF100B07) : const Color(0xFFFAFAFA),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 16),

            // Top App Logo Header
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: Image.asset(
                    'assets/icon/google_console_icon.png',
                    width: 44,
                    height: 44,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) {
                      return Image.asset(
                        'assets/google_console_icon.png',
                        width: 44,
                        height: 44,
                        fit: BoxFit.contain,
                        errorBuilder: (context, e2, st2) {
                          return Container(
                            width: 44,
                            height: 44,
                            color: const Color(0xFFFF7A00),
                            child: const Icon(Icons.mark_email_unread_rounded, size: 24, color: Colors.white),
                          );
                        },
                      );
                    },
                  ),
                ),
                const SizedBox(width: 10),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'VOIDMAIL',
                      style: GoogleFonts.outfit(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: isDark ? Colors.white : const Color(0xFF1C130D),
                        letterSpacing: 2.0,
                      ),
                    ),
                    Row(
                      children: [
                        Container(width: 10, height: 1, color: const Color(0xFFFF7A00)),
                        const SizedBox(width: 4),
                        Text(
                          'BY VOIDONYX',
                          style: GoogleFonts.inter(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            color: const Color(0xFFFF7A00),
                            letterSpacing: 1.8,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Container(width: 10, height: 1, color: const Color(0xFFFF7A00)),
                      ],
                    ),
                  ],
                ),
              ],
            ),

            const SizedBox(height: 16),

            // Main Carousel PageView
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (index) {
                  setState(() {
                    _currentPage = index;
                  });
                },
                itemCount: _slides.length,
                itemBuilder: (context, index) {
                  final slide = _slides[index];
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        // Headline Text
                        Text(
                          slide['title1'],
                          textAlign: TextAlign.center,
                          style: GoogleFonts.outfit(
                            fontSize: 32,
                            fontWeight: FontWeight.w800,
                            color: isDark ? Colors.white : const Color(0xFF1C130D),
                            height: 1.15,
                          ),
                        ),
                        ShaderMask(
                          shaderCallback: (bounds) => const LinearGradient(
                            colors: [Color(0xFFFF7A00), Color(0xFFFF9E3B), Color(0xFFFFB800)],
                          ).createShader(bounds),
                          child: Text(
                            slide['title2'],
                            textAlign: TextAlign.center,
                            style: GoogleFonts.outfit(
                              fontSize: 32,
                              fontWeight: FontWeight.w800,
                              color: Colors.white,
                              height: 1.15,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),

                        // Subtitle
                        Text(
                          slide['subtitle'],
                          textAlign: TextAlign.center,
                          style: GoogleFonts.inter(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w400,
                            color: isDark ? Colors.grey[400] : const Color(0xFF6B5E55),
                            height: 1.45,
                          ),
                        ),

                        const SizedBox(height: 32),

                        // Center Graphic Container
                        Expanded(
                          child: Center(
                            child: _buildGraphicForSlide(slide['type'], isDark),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),

            // Dot Indicator
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(_slides.length, (index) {
                final isActive = _currentPage == index;
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  width: isActive ? 22 : 7,
                  height: 7,
                  decoration: BoxDecoration(
                    color: isActive
                        ? const Color(0xFFFF7A00)
                        : (isDark ? Colors.grey[800] : const Color(0xFFFED7AA)),
                    borderRadius: BorderRadius.circular(4),
                  ),
                );
              }),
            ),

            const SizedBox(height: 24),

            // Action Buttons
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  // Get Started Primary Button
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pushNamed(context, '/login');
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFFF7A00),
                        foregroundColor: Colors.white,
                        elevation: 4,
                        shadowColor: const Color(0xFFFF7A00).withValues(alpha: 0.4),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: Text(
                        'Get Started',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Login Secondary Button
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: OutlinedButton(
                      onPressed: () {
                        Navigator.pushNamed(context, '/login');
                      },
                      style: OutlinedButton.styleFrom(
                        backgroundColor: isDark ? const Color(0xFF1C140D) : Colors.white,
                        foregroundColor: const Color(0xFFFF7A00),
                        side: BorderSide(
                          color: isDark
                              ? const Color(0xFF432818)
                              : const Color(0xFFFF7A00).withValues(alpha: 0.35),
                          width: 1.5,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: Text(
                        'Log In to Existing Account',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: const Color(0xFFFF7A00),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Reviewer / Guest Demo Mode
                  TextButton.icon(
                    onPressed: () async {
                      final provider = Provider.of<MailProvider>(context, listen: false);
                      await provider.loginAsDemo();
                      if (context.mounted) {
                        Navigator.pushReplacementNamed(context, '/main');
                      }
                    },
                    icon: const Icon(Icons.explore_rounded, size: 16, color: Color(0xFF10B981)),
                    label: Text(
                      'Explore Demo Workspace',
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: const Color(0xFF10B981),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGraphicForSlide(String type, bool isDark) {
    return Stack(
      alignment: Alignment.center,
      children: [
        // Background soft gradient glow circle
        Container(
          width: 240,
          height: 240,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                const Color(0xFFFF7A00).withValues(alpha: isDark ? 0.25 : 0.15),
                const Color(0xFFFF9E3B).withValues(alpha: 0.03),
                Colors.transparent,
              ],
            ),
          ),
        ),

        // Floating 3D Mail Graphic
        Container(
          width: 175,
          height: 155,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFFF7A00), Color(0xFFE65100)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFFF7A00).withValues(alpha: 0.35),
                blurRadius: 28,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: Stack(
            children: [
              // Inner White Email Document
              Positioned(
                top: 18,
                left: 20,
                right: 20,
                bottom: 24,
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.08),
                        blurRadius: 10,
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 40,
                        height: 6,
                        decoration: BoxDecoration(
                          color: const Color(0xFFFF7A00),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        width: double.infinity,
                        height: 4,
                        decoration: BoxDecoration(
                          color: Colors.grey[300],
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        width: 70,
                        height: 4,
                        decoration: BoxDecoration(
                          color: Colors.grey[200],
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // Front Envelope Flap Highlight
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                height: 70,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        const Color(0xFF818CF8).withOpacity(0.9),
                        const Color(0xFF4F46E5),
                      ],
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                    ),
                    borderRadius: const BorderRadius.only(
                      bottomLeft: Radius.circular(24),
                      bottomRight: Radius.circular(24),
                      topLeft: Radius.circular(16),
                      topRight: Radius.circular(16),
                    ),
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.mark_email_read_rounded,
                      color: Colors.white,
                      size: 28,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),

        // Floating Badges Surrounding Graphic (matching user screenshot)
        Positioned(
          top: 15,
          left: 10,
          child: _buildFloatingBadge(
            icon: Icons.shield_rounded,
            color: const Color(0xFF4F46E5),
          ),
        ),
        Positioned(
          top: 30,
          right: 15,
          child: _buildFloatingBadge(
            icon: Icons.auto_awesome_rounded,
            color: const Color(0xFF6366F1),
          ),
        ),
        Positioned(
          bottom: 25,
          left: 20,
          child: _buildFloatingBadge(
            icon: Icons.people_alt_rounded,
            color: const Color(0xFF10B981),
          ),
        ),
        Positioned(
          bottom: 35,
          right: 25,
          child: _buildFloatingBadge(
            icon: Icons.calendar_today_rounded,
            color: const Color(0xFF06B6D4),
          ),
        ),
        Positioned(
          top: 5,
          left: 55,
          child: _buildFloatingBadge(
            icon: Icons.near_me_rounded,
            color: const Color(0xFF818CF8),
            size: 34,
            iconSize: 18,
          ),
        ),
      ],
    );
  }

  Widget _buildFloatingBadge({
    required IconData icon,
    required Color color,
    double size = 42,
    double iconSize = 20,
  }) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.4),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Center(
        child: Icon(
          icon,
          size: iconSize,
          color: Colors.white,
        ),
      ),
    );
  }
}
