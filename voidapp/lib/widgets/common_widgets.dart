import 'package:flutter/material.dart';
import '../theme/void_theme.dart';

/// Modern Quota Display Card matching Image 2 reference design.
class QuotaRing extends StatelessWidget {
  final double percentage;
  final String label;
  final String used;
  final String total;
  final bool unlimited;
  final IconData icon;
  final Color? color;
  final Color? bgColor;

  const QuotaRing({
    super.key,
    required this.percentage,
    required this.label,
    required this.used,
    required this.total,
    this.unlimited = false,
    required this.icon,
    this.color,
    this.bgColor,
  });

  Color _getItemColor() {
    if (color != null) return color!;
    if (label.contains('Storage')) return const Color(0xFF6366F1);
    if (label.contains('Email')) return const Color(0xFF10B981);
    if (label.contains('Database')) return const Color(0xFFF59E0B);
    return const Color(0xFFEC4899);
  }

  Color _getItemBgColor() {
    if (bgColor != null) return bgColor!;
    if (label.contains('Storage')) return const Color(0xFFEEF2FF);
    if (label.contains('Email')) return const Color(0xFFECFDF5);
    if (label.contains('Database')) return const Color(0xFFFEF3C7);
    return const Color(0xFFFCE7F3);
  }

  @override
  Widget build(BuildContext context) {
    final activeColor = _getItemColor();
    final iconBgColor = _getItemBgColor();
    final pct = percentage.clamp(0.0, 100.0);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(VoidTheme.radiusLarge),
        border: Border.all(color: VoidTheme.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x06000000),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: iconBgColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, size: 20, color: activeColor),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: VoidTheme.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      unlimited ? '$used / ∞' : '$used / $total',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: VoidTheme.textPrimary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Sleek progress bar
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: unlimited ? 0.05 : (pct / 100.0),
              minHeight: 6,
              backgroundColor: const Color(0xFFF1F5F9),
              valueColor: AlwaysStoppedAnimation<Color>(activeColor),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            unlimited ? 'Unlimited' : '${pct.toStringAsFixed(pct % 1 == 0 ? 0 : 1)}% used',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: VoidTheme.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}


/// Shimmer loading skeleton
class Skeleton extends StatefulWidget {
  final double width;
  final double height;
  final double borderRadius;

  const Skeleton({
    super.key,
    this.width = double.infinity,
    required this.height,
    this.borderRadius = 10,
  });

  @override
  State<Skeleton> createState() => _SkeletonState();
}

class _SkeletonState extends State<Skeleton>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.borderRadius),
            gradient: LinearGradient(
              begin: Alignment(-1.5 + 3 * _controller.value, 0),
              end: Alignment(-0.5 + 3 * _controller.value, 0),
              colors: const [
                VoidTheme.bgCard,
                VoidTheme.bgElevated,
                VoidTheme.bgCard,
              ],
            ),
          ),
        );
      },
    );
  }
}

/// Status badge (SSL, live/down)
class StatusBadge extends StatelessWidget {
  final bool active;
  final String activeLabel;
  final String inactiveLabel;
  final IconData? activeIcon;
  final IconData? inactiveIcon;

  const StatusBadge({
    super.key,
    required this.active,
    this.activeLabel = 'Active',
    this.inactiveLabel = 'Inactive',
    this.activeIcon,
    this.inactiveIcon,
  });

  @override
  Widget build(BuildContext context) {
    final color = active ? VoidTheme.accentSuccess : VoidTheme.accentDanger;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            active
                ? (activeIcon ?? Icons.check_circle_rounded)
                : (inactiveIcon ?? Icons.cancel_rounded),
            size: 14,
            color: color,
          ),
          const SizedBox(width: 5),
          Text(
            active ? activeLabel : inactiveLabel,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

/// Empty state widget
class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: VoidTheme.accentPrimary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Icon(icon, size: 36, color: VoidTheme.textMuted),
          ),
          const SizedBox(height: 20),
          Text(
            title,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: VoidTheme.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 13,
              color: VoidTheme.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}

/// Glassmorphic list item card
class GlassListItem extends StatelessWidget {
  final Widget leading;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const GlassListItem({
    super.key,
    required this.leading,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.onLongPress,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          onLongPress: onLongPress,
          borderRadius: BorderRadius.circular(VoidTheme.radiusMedium),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: VoidTheme.simpleCard,
            child: Row(
              children: [
                leading,
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: VoidTheme.textPrimary,
                        ),
                      ),
                      if (subtitle != null) ...[
                        const SizedBox(height: 3),
                        Text(
                          subtitle!,
                          style: const TextStyle(
                            fontSize: 12,
                            color: VoidTheme.textMuted,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (trailing != null) trailing!,
              ],
            ),
          ),
        ),
      ),
    );
  }
}
