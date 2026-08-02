import 'package:flutter/material.dart';
import '../theme/void_theme.dart';
import 'dashboard_screen.dart';
import 'email_screen.dart';
import 'ftp_screen.dart';
import 'more_screen.dart';

/// Main app shell with bottom navigation.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _currentIndex = 0;

  final _screens = const [
    DashboardScreen(),
    EmailScreen(),
    FtpScreen(),
    MoreScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: VoidTheme.bgSurface,
          border: Border(
            top: BorderSide(color: VoidTheme.border, width: 1),
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildNavItem(0, Icons.dashboard_rounded, 'Dashboard'),
                _buildNavItem(1, Icons.email_rounded, 'Email'),
                _buildNavItem(2, Icons.folder_shared_rounded, 'FTP'),
                _buildNavItem(3, Icons.more_horiz_rounded, 'More'),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(int index, IconData icon, String label) {
    final isSelected = _currentIndex == index;
    return GestureDetector(
      onTap: () => setState(() => _currentIndex = index),
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        decoration: isSelected
            ? BoxDecoration(
                color: VoidTheme.accentPrimary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(20),
              )
            : null,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 22,
              color: isSelected ? VoidTheme.accentPrimary : VoidTheme.textMuted,
            ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                color: isSelected ? VoidTheme.accentPrimary : VoidTheme.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
