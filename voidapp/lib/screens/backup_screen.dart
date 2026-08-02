import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class BackupScreen extends StatefulWidget {
  const BackupScreen({super.key});

  @override
  State<BackupScreen> createState() => _BackupScreenState();
}

class _BackupScreenState extends State<BackupScreen> {
  List<dynamic> _backups = [];
  bool _loading = true;
  String _status = 'idle';
  int _percentage = 0;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _checkStatus();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final res = await api.get('/backups/');
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) _backups = res.data['backups'] ?? [];
      });
    }
  }

  Future<void> _checkStatus() async {
    final api = context.read<ApiClient>();
    final res = await api.get('/backups/status/');
    if (mounted && res.success) {
      final s = res.data['status'] ?? 'idle';
      setState(() {
        _status = s;
        _percentage = res.data['percentage'] ?? 0;
      });
      if (s == 'running') {
        _pollTimer?.cancel();
        _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) => _checkStatus());
      } else if (s == 'completed') {
        _pollTimer?.cancel();
        _load();
      }
    }
  }

  Future<void> _createBackup() async {
    final api = context.read<ApiClient>();
    final res = await api.post('/backups/create/');
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(res.success
            ? (res.data?['message'] ?? 'Backup started')
            : (res.error ?? 'Error')),
        backgroundColor: res.success ? VoidTheme.accentSuccess : VoidTheme.accentDanger,
      ));
      if (res.success) {
        setState(() => _status = 'running');
        _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) => _checkStatus());
      }
    }
  }

  Future<void> _deleteBackup(String filename) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Backup'),
        content: Text('Delete $filename?', style: const TextStyle(color: VoidTheme.textSecondary)),
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
    final res = await api.post('/backups/delete/', body: {'filename': filename});
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(res.success ? 'Backup deleted' : (res.error ?? 'Error')),
        backgroundColor: res.success ? VoidTheme.accentSuccess : VoidTheme.accentDanger,
      ));
      if (res.success) _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Backups'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: Column(
          children: [
            // Status banner
            if (_status == 'running')
              Container(
                margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: VoidTheme.accentWarning.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: VoidTheme.accentWarning.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const SizedBox(
                      width: 24, height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: VoidTheme.accentWarning,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Backup in progress...',
                              style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: VoidTheme.accentWarning)),
                          Text('$_percentage% complete',
                              style: const TextStyle(fontSize: 12, color: VoidTheme.textMuted)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator(color: VoidTheme.accentPrimary))
                  : _backups.isEmpty
                      ? const EmptyState(
                          icon: Icons.backup_outlined,
                          title: 'No backups',
                          subtitle: 'Create a full account backup',
                        )
                      : RefreshIndicator(
                          onRefresh: _load,
                          child: ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _backups.length,
                            itemBuilder: (ctx, i) {
                              final b = _backups[i];
                              return GlassListItem(
                                leading: Container(
                                  width: 40, height: 40,
                                  decoration: BoxDecoration(
                                    color: VoidTheme.accentWarning.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.archive_rounded, size: 20, color: VoidTheme.accentWarning),
                                ),
                                title: b['filename'] ?? '',
                                subtitle: '${b['size_mb']} MB • ${_formatDate(b['created'])}',
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete_outline, size: 20, color: VoidTheme.accentDanger),
                                  onPressed: () => _deleteBackup(b['filename'] ?? ''),
                                ),
                              );
                            },
                          ),
                        ),
            ),
          ],
        ),
      ),
      floatingActionButton: _status != 'running'
          ? FloatingActionButton.extended(
              heroTag: 'fab_backup',
              onPressed: _createBackup,
              icon: const Icon(Icons.backup_rounded),
              label: const Text('Create Backup'),
            )
          : null,
    );
  }

  String _formatDate(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }
}
