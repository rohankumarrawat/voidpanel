import 'package:flutter/material.dart';

class PoweredByVoidPanel extends StatelessWidget {
  final bool compact;
  final Color? textColor;

  const PoweredByVoidPanel({
    super.key,
    this.compact = false,
    this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    if (compact) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF4F46E5), Color(0xFF06B6D4)],
              ),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              'VP',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 10,
              ),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            'Powered by VoidPanel',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: textColor ?? (isDark ? Colors.grey[400] : Colors.grey[600]),
            ),
          ),
        ],
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
        ),
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
            'POWERED BY ',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: textColor ?? (isDark ? Colors.grey[400] : Colors.grey[600]),
            ),
          ),
          Text(
            'VOIDPANEL',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.5,
              foreground: Paint()
                ..shader = const LinearGradient(
                  colors: [Color(0xFF4F46E5), Color(0xFF06B6D4)],
                ).createShader(const Rect.fromLTWH(0, 0, 100, 20)),
            ),
          ),
        ],
      ),
    );
  }
}
