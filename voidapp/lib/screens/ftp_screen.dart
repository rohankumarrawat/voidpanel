import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class FtpScreen extends StatefulWidget {
  const FtpScreen({super.key});

  @override
  State<FtpScreen> createState() => _FtpScreenState();
}

class _FtpScreenState extends State<FtpScreen> {
  List<dynamic> _accounts = [];
  bool _loading = true;
  Map<String, dynamic>? _quota;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final res = await api.get('/ftp/');
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) {
          _accounts = res.data['accounts'] ?? [];
          _quota = {
            'used': res.data['used'] ?? 0,
            'total': res.data['total'] ?? 0,
            'unlimited': res.data['unlimited'] ?? false,
          };
        }
      });
    }
  }

  Future<void> _showCreateDialog() async {
    final usernameCtrl = TextEditingController();
    final passwordCtrl = TextEditingController();
    final storageCtrl = TextEditingController(text: '500');

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create FTP Account'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: usernameCtrl,
              decoration: const InputDecoration(labelText: 'Username'),
              style: const TextStyle(color: VoidTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: passwordCtrl,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Password'),
              style: const TextStyle(color: VoidTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: storageCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                  labelText: 'Storage Limit (MB)', hintText: '500'),
              style: const TextStyle(color: VoidTheme.textPrimary),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Create'),
          ),
        ],
      ),
    );

    if (result == true && mounted) {
      final api = context.read<ApiClient>();
      final res = await api.post('/ftp/create/', body: {
        'username': usernameCtrl.text.trim(),
        'password': passwordCtrl.text,
        'storage': storageCtrl.text.trim(),
      });
      if (!mounted) return;
      _showResult(res);
      if (res.success) _load();
    }
  }

  Future<void> _deleteAccount(String username) async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Delete FTP Account'),
            content: Text('Delete $username?',
                style: const TextStyle(color: VoidTheme.textSecondary)),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(ctx, false),
                  child: const Text('Cancel')),
              ElevatedButton(
                onPressed: () => Navigator.pop(ctx, true),
                style: ElevatedButton.styleFrom(
                    backgroundColor: VoidTheme.accentDanger),
                child: const Text('Delete'),
              ),
            ],
          ),
        ) ??
        false;

    if (!confirmed || !mounted) return;
    final api = context.read<ApiClient>();
    final res = await api.post('/ftp/delete/', body: {'username': username});
    if (!mounted) return;
    _showResult(res);
    if (res.success) _load();
  }

  void _showResult(ApiResponse res) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(res.success
          ? (res.data?['message'] ?? 'Success')
          : (res.error ?? 'Error')),
      backgroundColor:
          res.success ? VoidTheme.accentSuccess : VoidTheme.accentDanger,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: VoidTheme.accentSuccess.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.folder_shared_rounded,
                          size: 20, color: VoidTheme.accentSuccess),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('FTP Accounts',
                              style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w700,
                                  color: VoidTheme.textPrimary)),
                          if (_quota != null)
                            Text(
                              _quota!['unlimited'] == true
                                  ? '${_quota!['used']} accounts'
                                  : '${_quota!['used']} / ${_quota!['total']}',
                              style: const TextStyle(
                                  fontSize: 12, color: VoidTheme.textMuted),
                            ),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: _load,
                      icon: const Icon(Icons.refresh_rounded,
                          color: VoidTheme.textMuted),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: _loading
                    ? const Center(
                        child: CircularProgressIndicator(
                            color: VoidTheme.accentPrimary))
                    : _accounts.isEmpty
                        ? const EmptyState(
                            icon: Icons.folder_shared_outlined,
                            title: 'No FTP accounts',
                            subtitle: 'Create an FTP account for file access',
                          )
                        : RefreshIndicator(
                            onRefresh: _load,
                            child: ListView.builder(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 20),
                              itemCount: _accounts.length,
                              itemBuilder: (ctx, i) {
                                final a = _accounts[i];
                                return GlassListItem(
                                  leading: Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: VoidTheme.accentSuccess
                                          .withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: const Icon(
                                        Icons.person_rounded,
                                        size: 20,
                                        color: VoidTheme.accentSuccess),
                                  ),
                                  title: a['username'] ?? '',
                                  subtitle:
                                      'Storage: ${a['storage'] ?? 'N/A'} MB',
                                  trailing: IconButton(
                                    icon: const Icon(Icons.delete_outline,
                                        size: 20,
                                        color: VoidTheme.accentDanger),
                                    onPressed: () =>
                                        _deleteAccount(a['username'] ?? ''),
                                  ),
                                );
                              },
                            ),
                          ),
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'fab_ftp',
        onPressed: _showCreateDialog,
        icon: const Icon(Icons.add_rounded),
        label: const Text('New FTP'),
      ),
    );
  }
}
