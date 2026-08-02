import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class SslScreen extends StatefulWidget {
  const SslScreen({super.key});

  @override
  State<SslScreen> createState() => _SslScreenState();
}

class _SslScreenState extends State<SslScreen> {
  List<dynamic> _statuses = [];
  List<String> _logs = [];
  bool _loading = true;
  bool _installing = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final results = await Future.wait([
      api.get('/ssl/status/'),
      api.get('/ssl/log/'),
    ]);
    if (mounted) {
      setState(() {
        _loading = false;
        if (results[0].success) _statuses = results[0].data['statuses'] ?? [];
        if (results[1].success) _logs = List<String>.from(results[1].data['logs'] ?? []);
      });
    }
  }

  Future<void> _installSsl(String domain) async {
    setState(() => _installing = true);
    final api = context.read<ApiClient>();
    final res = await api.post('/ssl/install/', body: {'domain': domain});
    if (mounted) {
      setState(() => _installing = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(res.success ? (res.data?['message'] ?? 'SSL started') : (res.error ?? 'Error')),
        backgroundColor: res.success ? VoidTheme.accentSuccess : VoidTheme.accentDanger,
      ));
      if (res.success) {
        // Wait a bit and refresh
        Future.delayed(const Duration(seconds: 3), _load);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SSL Certificates'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: VoidTheme.accentPrimary))
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    // SSL Status Cards
                    ..._statuses.map((s) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: VoidTheme.simpleCard,
                        child: Row(
                          children: [
                            Container(
                              width: 44, height: 44,
                              decoration: BoxDecoration(
                                color: (s['ssl_active'] == true
                                        ? VoidTheme.accentSuccess
                                        : VoidTheme.accentDanger)
                                    .withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(
                                s['ssl_active'] == true
                                    ? Icons.lock_rounded
                                    : Icons.lock_open_rounded,
                                size: 22,
                                color: s['ssl_active'] == true
                                    ? VoidTheme.accentSuccess
                                    : VoidTheme.accentDanger,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    s['name'] ?? '',
                                    style: const TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                      color: VoidTheme.textPrimary,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    s['is_subdomain'] == true ? 'Subdomain' : 'Primary Domain',
                                    style: const TextStyle(fontSize: 12, color: VoidTheme.textMuted),
                                  ),
                                ],
                              ),
                            ),
                            StatusBadge(
                              active: s['ssl_active'] == true,
                              activeLabel: 'Secured',
                              inactiveLabel: 'No SSL',
                            ),
                            const SizedBox(width: 8),
                            if (s['ssl_active'] != true)
                              SizedBox(
                                height: 34,
                                child: ElevatedButton(
                                  onPressed: _installing ? null : () => _installSsl(s['name']),
                                  style: ElevatedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(horizontal: 12),
                                    textStyle: const TextStyle(fontSize: 12),
                                  ),
                                  child: _installing
                                      ? const SizedBox(
                                          width: 16, height: 16,
                                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                        )
                                      : const Text('Install'),
                                ),
                              ),
                          ],
                        ),
                      ),
                    )),

                    if (_logs.isNotEmpty) ...[
                      const SizedBox(height: 20),
                      const Text('Installation Log',
                          style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: VoidTheme.textPrimary)),
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0A0E18),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: VoidTheme.border),
                        ),
                        constraints: const BoxConstraints(maxHeight: 300),
                        child: SingleChildScrollView(
                          child: SelectableText(
                            _logs.join('\n'),
                            style: const TextStyle(
                              fontSize: 12,
                              fontFamily: 'monospace',
                              color: VoidTheme.accentSuccess,
                              height: 1.6,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
      ),
    );
  }
}
