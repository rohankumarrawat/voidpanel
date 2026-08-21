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
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
                    child: Row(
                      children: [
                        IconButton(
                          onPressed: () {},
                          icon: const Icon(Icons.menu_rounded, color: VoidTheme.textPrimary, size: 24),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Row(
                            children: [
                              RichText(
                                text: const TextSpan(
                                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, letterSpacing: -0.3),
                                  children: [
                                    TextSpan(text: 'Void', style: TextStyle(color: VoidTheme.textPrimary)),
                                    TextSpan(text: 'Panel', style: TextStyle(color: VoidTheme.accentPrimary)),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 6),
                              Container(
                                width: 6,
                                height: 6,
                                decoration: const BoxDecoration(
                                  color: VoidTheme.accentSuccess,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  auth.domain.isNotEmpty ? auth.domain : 'voidonyx.com',
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontSize: 12, color: VoidTheme.textMuted, fontWeight: FontWeight.w500),
                                ),
                              ),
                            ],
                          ),
                        ),
                        // Bell Icon with notification badge
                        Stack(
                          children: [
                            Container(
                              width: 38,
                              height: 38,
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: VoidTheme.border),
                              ),
                              child: IconButton(
                                onPressed: _loadDashboard,
                                padding: EdgeInsets.zero,
                                icon: const Icon(Icons.notifications_none_rounded, color: VoidTheme.textPrimary, size: 20),
                              ),
                            ),
                            Positioned(
                              right: 2,
                              top: 2,
                              child: Container(
                                padding: const EdgeInsets.all(4),
                                decoration: const BoxDecoration(
                                  color: VoidTheme.accentPrimary,
                                  shape: BoxShape.circle,
                                ),
                                child: const Text('3', style: TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(width: 10),
                        // User Avatar
                        Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                            gradient: VoidTheme.primaryGradient,
                            borderRadius: BorderRadius.circular(14),
                            boxShadow: VoidTheme.glowShadow(VoidTheme.accentPrimary),
                          ),
                          child: Center(
                            child: Text(
                              (auth.username.isNotEmpty ? auth.username[0] : '?').toUpperCase(),
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.white),
                            ),
                          ),
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
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                      child: Row(
                        children: [
                          Text(
                            'Resource Usage',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const Spacer(),
                          Text(
                            '0% Used',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: VoidTheme.textMuted,
                            ),
                          ),
                        ],
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

                  // ── Quick Access ──────────────────────────────────────
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                      child: Row(
                        children: [
                          Text(
                            'Quick Access',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const Spacer(),
                          const Text(
                            'Edit',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: VoidTheme.accentPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
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

                  // ── Live Website Preview Card ─────────────────────────
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                      child: Text(
                        'Live Website Preview',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: _buildLivePreviewCard(),
                  ),

                  // ── Recent System Activity ────────────────────────────
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                      child: Row(
                        children: [
                          Text(
                            'Recent Activity',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const Spacer(),
                          GestureDetector(
                            onTap: () => Navigator.of(context).pushNamed('/activity'),
                            child: const Text(
                              'View All',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: VoidTheme.accentPrimary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 40),
                      child: _buildRecentActivityList(),
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
    final domain = _dashData?['domain'] ?? 'voidonyx.com';
    final auth = context.watch<AuthService>();

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: VoidTheme.heroCard,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Robot / User Avatar box
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: VoidTheme.primaryGradient,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: VoidTheme.glowShadow(VoidTheme.accentPrimary),
                  ),
                  child: const Center(
                    child: Icon(Icons.smart_toy_rounded, size: 28, color: Colors.white),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Welcome back,',
                        style: TextStyle(fontSize: 14, color: VoidTheme.textSecondary, fontWeight: FontWeight.w500),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${auth.username.isNotEmpty ? auth.username : "voidonyx1"} 👋',
                        style: const TextStyle(
                          fontSize: 18,
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
            const Text(
              'Manage your hosting, domains, email & more — all in one place.',
              style: TextStyle(fontSize: 13, color: VoidTheme.textMuted, height: 1.4),
            ),
            const SizedBox(height: 16),
            // Pill Badges Row
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  // Secure domain pill
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.language_rounded, size: 14, color: VoidTheme.accentPrimary),
                        const SizedBox(width: 6),
                        Text(
                          domain.toString(),
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: VoidTheme.textPrimary),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFFD1FAE5),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Row(
                            children: const [
                              Icon(Icons.lock_rounded, size: 10, color: Color(0xFF047857)),
                              SizedBox(width: 3),
                              Text('Secure', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF047857))),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Live Status Pill
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: VoidTheme.accentSuccess,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 6),
                        const Text('Live Status', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: VoidTheme.textPrimary)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  // View Site Pill
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      children: const [
                        Text('View Site', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: VoidTheme.accentPrimary)),
                        SizedBox(width: 4),
                        Icon(Icons.chevron_right_rounded, size: 16, color: VoidTheme.accentPrimary),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }


  List<Widget> _buildQuotaCards() {
    final quotas = _dashData?['quotas'] as Map<String, dynamic>? ?? {};
    final storage = quotas['storage'] ?? {};
    final emails = quotas['email'] ?? {};
    final ftp = quotas['ftp'] ?? {};
    final databases = quotas['databases'] ?? {};

    double calcPct(dynamic q) {
      if (q is! Map) return 0;
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
      _QuickAction(Icons.language_rounded, 'DNS', const Color(0xFF6366F1), const Color(0xFFEEF2FF), () {
        Navigator.of(context).pushNamed('/dns');
      }),
      _QuickAction(Icons.lock_rounded, 'SSL', const Color(0xFF10B981), const Color(0xFFECFDF5), () {
        Navigator.of(context).pushNamed('/ssl');
      }),
      _QuickAction(Icons.restore_rounded, 'Cron Jobs', const Color(0xFFD97706), const Color(0xFFFEF3C7), () {
        Navigator.of(context).pushNamed('/cron');
      }),
      _QuickAction(Icons.cloud_download_rounded, 'Backup', const Color(0xFF0284C7), const Color(0xFFE0F2FE), () {
        Navigator.of(context).pushNamed('/backup');
      }),
      _QuickAction(Icons.folder_rounded, 'File Manager', const Color(0xFFDB2777), const Color(0xFFFCE7F3), () {
        // Nav to FTP
        Navigator.of(context).pushNamed('/home');
      }),
      _QuickAction(Icons.code_rounded, 'Web Config', const Color(0xFF9333EA), const Color(0xFFF3E8FF), () {
        Navigator.of(context).pushNamed('/subdomains');
      }),
      _QuickAction(Icons.storage_rounded, 'Databases', const Color(0xFFEA580C), const Color(0xFFFFEDD5), () {
        Navigator.of(context).pushNamed('/databases');
      }),
      _QuickAction(Icons.dns_rounded, 'phpMyAdmin', const Color(0xFF4F46E5), const Color(0xFFE0E7FF), () {
        Navigator.of(context).pushNamed('/databases');
      }),
    ];

    return actions.map((a) => _buildActionTile(a)).toList();
  }

  Widget _buildActionTile(_QuickAction action) {
    return GestureDetector(
      onTap: action.onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(VoidTheme.radiusMedium),
          border: Border.all(color: VoidTheme.border),
          boxShadow: const [
            BoxShadow(
              color: Color(0x06000000),
              blurRadius: 8,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: action.bgColor,
                shape: BoxShape.circle,
              ),
              child: Icon(action.icon, size: 22, color: action.color),
            ),
            const SizedBox(height: 8),
            Text(
              action.label,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: VoidTheme.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLivePreviewCard() {
    final domain = _dashData?['domain'] ?? 'voidonyx.com';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(VoidTheme.radiusLarge),
          border: Border.all(color: VoidTheme.border),
          boxShadow: const [
            BoxShadow(
              color: Color(0x06000000),
              blurRadius: 10,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top URL bar header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: const BoxDecoration(
                color: Color(0xFFF8FAFC),
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                border: Border(bottom: BorderSide(color: VoidTheme.border)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: VoidTheme.accentSuccess,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'https://$domain',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: VoidTheme.textPrimary,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: _loadDashboard,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    icon: const Icon(Icons.refresh_rounded, size: 18, color: VoidTheme.textMuted),
                  ),
                ],
              ),
            ),
            // Mock website preview content
            Padding(
              padding: const EdgeInsets.all(16),
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFFFFBEB), Color(0xFFFEF3C7)],
                  ),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFFDE68A)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        Text(
                          'VoidOnyx',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w900,
                            color: VoidTheme.textPrimary,
                          ),
                        ),
                        Spacer(),
                        Icon(Icons.menu_rounded, size: 16, color: VoidTheme.textPrimary),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'One Platform for Every Digital Business Need.',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: VoidTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Web hosting, domain registration, HRMS, professional email, digital marketing suites.',
                      style: TextStyle(fontSize: 11, color: VoidTheme.textSecondary),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            gradient: VoidTheme.primaryGradient,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'Get Started Free',
                            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: VoidTheme.border),
                          ),
                          child: const Text(
                            'View Plans',
                            style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: VoidTheme.textPrimary),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentActivityList() {
    final activities = [
      {
        'icon': Icons.lock_rounded,
        'color': VoidTheme.accentSuccess,
        'title': 'AutoSSL Certificate Active',
        'subtitle': 'Let\'s Encrypt SSL renewed for voidonyx.com',
        'time': '2m ago',
      },
      {
        'icon': Icons.storage_rounded,
        'color': VoidTheme.accentPrimary,
        'title': 'Database Backup Completed',
        'subtitle': 'Automatic snapshot created successfully',
        'time': '1h ago',
      },
      {
        'icon': Icons.dns_rounded,
        'color': VoidTheme.accentInfo,
        'title': 'DNS Zone Synchronized',
        'subtitle': 'A Record updated for 207.180.209.216',
        'time': '3h ago',
      },
    ];

    return Column(
      children: activities.map((item) {
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(VoidTheme.radiusMedium),
            border: Border.all(color: VoidTheme.border),
          ),
          child: Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: (item['color'] as Color).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(item['icon'] as IconData, size: 20, color: item['color'] as Color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item['title'] as String,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: VoidTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      item['subtitle'] as String,
                      style: const TextStyle(
                        fontSize: 11,
                        color: VoidTheme.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                item['time'] as String,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: VoidTheme.textMuted,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildLoadingSkeleton() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: const [
          Skeleton(height: 120),
          SizedBox(height: 20),
          Row(
            children: [
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
  final Color bgColor;
  final VoidCallback onTap;

  _QuickAction(this.icon, this.label, this.color, this.bgColor, this.onTap);
}

