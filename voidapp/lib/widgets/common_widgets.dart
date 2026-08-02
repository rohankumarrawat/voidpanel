import 'dart:math';
import 'package:flutter/material.dart';
import '../theme/void_theme.dart';

/// Animated circular progress ring used for quota display.
class QuotaRing extends StatefulWidget {
  final double percentage;
  final String label;
  final String used;
  final String total;
  final bool unlimited;
  final IconData icon;

  const QuotaRing({
    super.key,
    required this.percentage,
    required this.label,
    required this.used,
    required this.total,
    this.unlimited = false,
    required this.icon,
  });

  @override
  State<QuotaRing> createState() => _QuotaRingState();
}

class _QuotaRingState extends State<QuotaRing>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0, end: widget.percentage / 100)
        .animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));
    _controller.forward();
  }

  @override
  void didUpdateWidget(QuotaRing oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.percentage != widget.percentage) {
      _animation = Tween<double>(
        begin: _animation.value,
        end: widget.percentage / 100,
      ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));
      _controller
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _getColor() {
    if (widget.unlimited) return VoidTheme.accentSuccess;
    if (widget.percentage >= 80) return VoidTheme.accentDanger;
    if (widget.percentage >= 60) return VoidTheme.accentWarning;
    return VoidTheme.accentSuccess;
  }

  @override
  Widget build(BuildContext context) {
    final color = _getColor();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: VoidTheme.glassCard,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(widget.icon, size: 18, color: color),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  widget.label,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: VoidTheme.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: 70,
            height: 70,
            child: AnimatedBuilder(
              animation: _animation,
              builder: (context, child) {
                return CustomPaint(
                  painter: _RingPainter(
                    progress: _animation.value,
                    color: color,
                  ),
                  child: Center(
                    child: widget.unlimited
                        ? const Icon(Icons.all_inclusive, color: VoidTheme.accentSuccess, size: 22)
                        : Text(
                            '${widget.percentage.round()}%',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              color: color,
                            ),
                          ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 10),
          Text(
            widget.unlimited ? '${widget.used} / ∞' : '${widget.used} / ${widget.total}',
            style: const TextStyle(
              fontSize: 12,
              color: VoidTheme.textMuted,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  final double progress;
  final Color color;

  _RingPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 4;

    // Background ring
    final bgPaint = Paint()
      ..color = VoidTheme.border
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, bgPaint);

    // Progress ring
    final progressPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -pi / 2,
      2 * pi * progress,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) =>
      oldDelegate.progress != progress || oldDelegate.color != color;
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
