import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../theme/void_theme.dart';

/// "More" / Tools screen with navigation to secondary features.
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              // Profile Header
              Container(
                padding: const EdgeInsets.all(18),
                decoration: VoidTheme.glassCard,
                child: Row(
                  children: [
                    Container(
                      width: 54,
                      height: 54,
                      decoration: BoxDecoration(
                        gradient: VoidTheme.primaryGradient,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Center(
                        child: Text(
                          (auth.username.isNotEmpty
                                  ? auth.username[0]
                                  : '?')
                              .toUpperCase(),
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            auth.username,
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              color: VoidTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            auth.domain,
                            style: const TextStyle(
                              fontSize: 13,
                              color: VoidTheme.textMuted,
                            ),
                          ),
                          Text(
                            'Plan: ${auth.hostingPackage}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: VoidTheme.textMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Management Section
              const _SectionTitle('Management'),
              const SizedBox(height: 8),
              _buildTile(
                context,
                icon: Icons.view_column_rounded,
                color: VoidTheme.accentWarning,
                title: 'Databases',
                subtitle: 'MySQL databases & users',
                route: '/databases',
              ),
              _buildTile(
                context,
                icon: Icons.language_rounded,
                color: VoidTheme.accentInfo,
                title: 'Subdomains',
                subtitle: 'Manage subdomains',
                route: '/subdomains',
              ),
              _buildTile(
                context,
                icon: Icons.lock_rounded,
                color: VoidTheme.accentSuccess,
                title: 'SSL Certificates',
                subtitle: "Let's Encrypt management",
                route: '/ssl',
              ),
              _buildTile(
                context,
                icon: Icons.schedule_rounded,
                color: const Color(0xFF8B5CF6),
                title: 'Cron Jobs',
                subtitle: 'Scheduled tasks',
                route: '/cron',
              ),

              const SizedBox(height: 20),
              const _SectionTitle('Data'),
              const SizedBox(height: 8),
              _buildTile(
                context,
                icon: Icons.backup_rounded,
                color: VoidTheme.accentWarning,
                title: 'Backups',
                subtitle: 'Full account backups',
                route: '/backup',
              ),
              _buildTile(
                context,
                icon: Icons.dns_rounded,
                color: VoidTheme.accentSecondary,
                title: 'DNS Zone',
                subtitle: 'DNS records management',
                route: '/dns',
              ),
              _buildTile(
                context,
                icon: Icons.history_rounded,
                color: VoidTheme.textMuted,
                title: 'Activity Log',
                subtitle: 'Account activity history',
                route: '/activity',
              ),

              const SizedBox(height: 24),

              // Logout
              Container(
                decoration: BoxDecoration(
                  color: VoidTheme.accentDanger.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(VoidTheme.radiusMedium),
                  border: Border.all(
                      color: VoidTheme.accentDanger.withValues(alpha: 0.15)),
                ),
                child: ListTile(
                  onTap: () async {
                    final confirmed = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('Logout'),
                        content: const Text('Are you sure you want to logout?',
                            style: TextStyle(color: VoidTheme.textSecondary)),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(ctx, false),
                            child: const Text('Cancel'),
                          ),
                          ElevatedButton(
                            onPressed: () => Navigator.pop(ctx, true),
                            style: ElevatedButton.styleFrom(
                                backgroundColor: VoidTheme.accentDanger),
                            child: const Text('Logout'),
                          ),
                        ],
                      ),
                    );
                    if (confirmed == true && context.mounted) {
                      await auth.logout();
                      if (context.mounted) {
                        Navigator.of(context).pushReplacementNamed('/login');
                      }
                    }
                  },
                  leading: const Icon(Icons.logout_rounded,
                      color: VoidTheme.accentDanger),
                  title: const Text('Logout',
                      style: TextStyle(
                          color: VoidTheme.accentDanger,
                          fontWeight: FontWeight.w600)),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(VoidTheme.radiusMedium),
                  ),
                ),
              ),

              const SizedBox(height: 30),
              const Center(
                child: Text(
                  'VoidApp v1.0.0',
                  style: TextStyle(fontSize: 12, color: VoidTheme.textDisabled),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTile(
    BuildContext context, {
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    required String route,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => Navigator.of(context).pushNamed(route),
          borderRadius: BorderRadius.circular(VoidTheme.radiusMedium),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: VoidTheme.simpleCard,
            child: Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, size: 22, color: color),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title,
                          style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: VoidTheme.textPrimary)),
                      const SizedBox(height: 2),
                      Text(subtitle,
                          style: const TextStyle(
                              fontSize: 12, color: VoidTheme.textMuted)),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right_rounded,
                    size: 22, color: VoidTheme.textDisabled),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Text(
      title.toUpperCase(),
      style: const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: VoidTheme.textMuted,
        letterSpacing: 1.2,
      ),
    );
  }
}
