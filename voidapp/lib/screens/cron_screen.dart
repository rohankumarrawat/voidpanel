import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class CronScreen extends StatefulWidget {
  const CronScreen({super.key});

  @override
  State<CronScreen> createState() => _CronScreenState();
}

class _CronScreenState extends State<CronScreen> {
  List<dynamic> _crons = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final res = await api.get('/cron/');
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) _crons = res.data['cron_jobs'] ?? [];
      });
    }
  }

  Future<void> _create() async {
    final scheduleCtrl = TextEditingController();
    final commandCtrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create Cron Job'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: scheduleCtrl,
              decoration: const InputDecoration(
                labelText: 'Schedule',
                hintText: '*/5 * * * *',
                helperText: 'min hour dom month dow',
              ),
              style: const TextStyle(color: VoidTheme.textPrimary, fontFamily: 'monospace'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: commandCtrl,
              decoration: const InputDecoration(
                labelText: 'Command',
                hintText: '/usr/bin/php /home/user/cron.php',
              ),
              style: const TextStyle(color: VoidTheme.textPrimary),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Create')),
        ],
      ),
    );
    if (result == true && mounted) {
      final api = context.read<ApiClient>();
      final res = await api.post('/cron/create/', body: {
        'schedule': scheduleCtrl.text.trim(),
        'command': commandCtrl.text.trim(),
      });
      if (!mounted) return;
      _showSnack(res);
      if (res.success) _load();
    }
  }

  Future<void> _delete(int id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Cron Job'),
        content: const Text('Are you sure?', style: TextStyle(color: VoidTheme.textSecondary)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: VoidTheme.accentDanger),
            child: const Text('Delete'),
          ),
        ],
      ),
    ) ?? false;
    if (!confirmed || !mounted) return;
    final api = context.read<ApiClient>();
    final res = await api.post('/cron/delete/', body: {'id': id});
    if (!mounted) return;
    _showSnack(res);
    if (res.success) _load();
  }

  void _showSnack(ApiResponse res) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(res.success ? (res.data?['message'] ?? 'Done') : (res.error ?? 'Error')),
      backgroundColor: res.success ? VoidTheme.accentSuccess : VoidTheme.accentDanger,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cron Jobs'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: VoidTheme.accentPrimary))
            : _crons.isEmpty
                ? const EmptyState(
                    icon: Icons.schedule_outlined,
                    title: 'No cron jobs',
                    subtitle: 'Create scheduled tasks',
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _crons.length,
                      itemBuilder: (ctx, i) {
                        final c = _crons[i];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: VoidTheme.simpleCard,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: VoidTheme.accentSecondary.withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: Text(
                                        c['schedule'] ?? '',
                                        style: const TextStyle(
                                          fontSize: 13,
                                          fontFamily: 'monospace',
                                          fontWeight: FontWeight.w600,
                                          color: VoidTheme.accentSecondary,
                                        ),
                                      ),
                                    ),
                                    const Spacer(),
                                    IconButton(
                                      icon: const Icon(Icons.delete_outline, size: 20, color: VoidTheme.accentDanger),
                                      onPressed: () => _delete(c['id']),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  c['command'] ?? '',
                                  style: const TextStyle(
                                    fontSize: 13,
                                    color: VoidTheme.textSecondary,
                                    fontFamily: 'monospace',
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'fab_cron',
        onPressed: _create,
        icon: const Icon(Icons.add_rounded),
        label: const Text('New Cron'),
      ),
    );
  }
}
