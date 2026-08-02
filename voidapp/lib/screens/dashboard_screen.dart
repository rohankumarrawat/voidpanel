import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _dashData;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    final api = context.read<ApiClient>();
    final res = await api.get('/dashboard/');

    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) {
          _dashData = res.data;
        } else {
          _error = res.error ?? 'Failed to load dashboard';
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: _loadDashboard,
            color: VoidTheme.accentPrimary,
            child: CustomScrollView(
              slivers: [
                // ── Header ─────────────────────────────────────────────
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
                    child: Row(
                      children: [
                        Container(
                          width: 46,
                          height: 46,
                          decoration: BoxDecoration(
                            gradient: VoidTheme.primaryGradient,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Center(
                            child: Text(
                              (auth.username.isNotEmpty
                                      ? auth.username[0]
                                      : '?')
                                  .toUpperCase(),
                              style: const TextStyle(
                                fontSize: 20,
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
                                'Welcome back,',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: VoidTheme.textMuted,
                                ),
                              ),
                              Text(
                                auth.username,
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w700,
                                  color: VoidTheme.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          onPressed: _loadDashboard,
                          icon: const Icon(Icons.refresh_rounded,
                              color: VoidTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                ),

                // ── Domain Info Card ───────────────────────────────────
                SliverToBoxAdapter(
                  child: _loading
                      ? _buildLoadingSkeleton()
                      : _error != null
                          ? _buildError()
                          : _buildDomainCard(),
                ),

                // ── Quotas Grid ────────────────────────────────────────
                if (!_loading && _error == null && _dashData != null) ...[
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 10),
                      child: Text(
                        'Resource Usage',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                  ),
                  SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    sliver: SliverGrid(
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        mainAxisSpacing: 12,
                        crossAxisSpacing: 12,
                        childAspectRatio: 0.92,
                      ),
                      delegate: SliverChildListDelegate(
                        _buildQuotaCards(),
                      ),
                    ),
                  ),

                  // ── Quick Actions ──────────────────────────────────────
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 10),
                      child: Text(
                        'Quick Actions',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                  ),
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(20, 0, 20, 40),
                    sliver: SliverGrid(
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 4,
                        mainAxisSpacing: 12,
                        crossAxisSpacing: 12,
                        childAspectRatio: 0.85,
                      ),
                      delegate: SliverChildListDelegate(
                        _buildQuickActions(),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDomainCard() {
    final domain = _dashData?['domain'] ?? 'N/A';
    final sslActive = _dashData?['ssl_active'] == true;
    final serverIp = _dashData?['server_ip'] ?? 'N/A';
    final packageName = _dashData?['package_name'] ?? 'N/A';

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF1A1F5C), Color(0xFF0C1030)],
          ),
          borderRadius: BorderRadius.circular(VoidTheme.radiusLarge),
          border: Border.all(color: VoidTheme.accentPrimary.withValues(alpha: 0.2)),
          boxShadow: VoidTheme.glowShadow(VoidTheme.accentPrimary),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.language_rounded,
                    size: 20, color: VoidTheme.accentPrimary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    domain.toString(),
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: VoidTheme.textPrimary,
                    ),
                  ),
                ),
                StatusBadge(
                  active: sslActive,
                  activeLabel: 'SSL',
                  inactiveLabel: 'No SSL',
                  activeIcon: Icons.lock_rounded,
                  inactiveIcon: Icons.lock_open_rounded,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                _infoChip(Icons.dns_rounded, 'IP: $serverIp'),
                _infoChip(Icons.inventory_2_rounded, 'Plan: $packageName'),
                _infoChip(Icons.email_rounded,
                    'Email: ${(_dashData?['quotas']?['email']?['used'] ?? 0)}/${(_dashData?['quotas']?['email']?['total'] ?? 0)}'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoChip(IconData icon, String text) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: VoidTheme.textMuted),
        const SizedBox(width: 5),
        Text(
          text,
          style: const TextStyle(fontSize: 12, color: VoidTheme.textSecondary),
        ),
      ],
    );
  }

  List<Widget> _buildQuotaCards() {
    final quotas = _dashData?['quotas'] as Map<String, dynamic>? ?? {};
    final storage = quotas['storage'] ?? {};
    final emails = quotas['email'] ?? {};
    final ftp = quotas['ftp'] ?? {};
    final databases = quotas['databases'] ?? {};

    double calcPct(Map q) {
      if (q['unlimited'] == true) return 0;
      final total = (q['total'] is num ? q['total'] : int.tryParse('${q['total']}') ?? 0);
      if (total == 0) return 0;
      final used = (q['used'] is num ? q['used'] : int.tryParse('${q['used']}') ?? 0);
      return ((used / total) * 100).clamp(0, 100).toDouble();
    }

    return [
      QuotaRing(
        percentage: calcPct(storage),
        label: 'Storage',
        used: '${storage['used'] ?? 0} MB',
        total: '${storage['total'] ?? 0} MB',
        unlimited: storage['unlimited'] == true,
        icon: Icons.storage_rounded,
      ),
      QuotaRing(
        percentage: calcPct(emails),
        label: 'Emails',
        used: '${emails['used'] ?? 0}',
        total: '${emails['total'] ?? 0}',
        unlimited: emails['unlimited'] == true,
        icon: Icons.email_rounded,
      ),
      QuotaRing(
        percentage: calcPct(ftp),
        label: 'FTP',
        used: '${ftp['used'] ?? 0}',
        total: '${ftp['total'] ?? 0}',
        unlimited: ftp['unlimited'] == true,
        icon: Icons.folder_shared_rounded,
      ),
      QuotaRing(
        percentage: calcPct(databases),
        label: 'Databases',
        used: '${databases['used'] ?? 0}',
        total: '${databases['total'] ?? 0}',
        unlimited: databases['unlimited'] == true,
        icon: Icons.view_column_rounded,
      ),
    ];
  }

  List<Widget> _buildQuickActions() {
    final actions = [
      _QuickAction(Icons.email_rounded, 'Email', VoidTheme.accentInfo, () {
        // Navigate handled by bottom nav parent
      }),
      _QuickAction(Icons.lock_rounded, 'SSL', VoidTheme.accentSuccess, () {
        Navigator.of(context).pushNamed('/ssl');
      }),
      _QuickAction(Icons.backup_rounded, 'Backup', VoidTheme.accentWarning, () {
        Navigator.of(context).pushNamed('/backup');
      }),
      _QuickAction(Icons.dns_rounded, 'DNS', VoidTheme.accentSecondary, () {
        Navigator.of(context).pushNamed('/dns');
      }),
    ];

    return actions.map((a) => _buildActionTile(a)).toList();
  }

  Widget _buildActionTile(_QuickAction action) {
    return GestureDetector(
      onTap: action.onTap,
      child: Container(
        decoration: VoidTheme.simpleCard,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: action.color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(action.icon, size: 20, color: action.color),
            ),
            const SizedBox(height: 8),
            Text(
              action.label,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: VoidTheme.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingSkeleton() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const Skeleton(height: 120),
          const SizedBox(height: 20),
          Row(
            children: const [
              Expanded(child: Skeleton(height: 160)),
              SizedBox(width: 12),
              Expanded(child: Skeleton(height: 160)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildError() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: VoidTheme.simpleCard,
        child: Column(
          children: [
            const Icon(Icons.error_outline_rounded,
                size: 48, color: VoidTheme.accentDanger),
            const SizedBox(height: 12),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: VoidTheme.textSecondary),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loadDashboard,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickAction {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  _QuickAction(this.icon, this.label, this.color, this.onTap);
}
