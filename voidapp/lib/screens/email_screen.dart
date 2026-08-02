import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class EmailScreen extends StatefulWidget {
  const EmailScreen({super.key});

  @override
  State<EmailScreen> createState() => _EmailScreenState();
}

class _EmailScreenState extends State<EmailScreen> {
  List<dynamic> _emails = [];
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
    final res = await api.get('/emails/');
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) {
          _emails = res.data['emails'] ?? [];
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
    final nameController = TextEditingController();
    final passwordController = TextEditingController();
    final storageController = TextEditingController(text: '500');

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create Email'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(
                labelText: 'Email name (before @)',
                hintText: 'info',
              ),
              style: const TextStyle(color: VoidTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: passwordController,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Password'),
              style: const TextStyle(color: VoidTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: storageController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Storage (MB)',
                hintText: '500',
              ),
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
      final res = await api.post('/emails/create/', body: {
        'name': nameController.text.trim(),
        'password': passwordController.text,
        'storage': storageController.text.trim(),
      });
      if (!mounted) return;
      _showResult(res);
      if (res.success) _load();
    }
  }

  Future<void> _deleteEmail(String email) async {
    final confirmed = await _confirm('Delete $email?');
    if (!confirmed || !mounted) return;

    final api = context.read<ApiClient>();
    final res = await api.post('/emails/delete/', body: {'email': email});
    if (!mounted) return;
    _showResult(res);
    if (res.success) _load();
  }

  Future<bool> _confirm(String message) async {
    return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Confirm'),
            content: Text(message,
                style: const TextStyle(color: VoidTheme.textSecondary)),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel'),
              ),
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
  }

  void _showResult(ApiResponse res) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(res.success
            ? (res.data?['message'] ?? 'Success')
            : (res.error ?? 'Error')),
        backgroundColor:
            res.success ? VoidTheme.accentSuccess : VoidTheme.accentDanger,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: SafeArea(
          child: Column(
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: VoidTheme.accentInfo.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.email_rounded,
                          size: 20, color: VoidTheme.accentInfo),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Email Accounts',
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

              // List
              Expanded(
                child: _loading
                    ? const Center(
                        child: CircularProgressIndicator(
                            color: VoidTheme.accentPrimary))
                    : _emails.isEmpty
                        ? const EmptyState(
                            icon: Icons.email_outlined,
                            title: 'No email accounts',
                            subtitle:
                                'Create your first email account to get started',
                          )
                        : RefreshIndicator(
                            onRefresh: _load,
                            child: ListView.builder(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 20),
                              itemCount: _emails.length,
                              itemBuilder: (ctx, i) {
                                final e = _emails[i];
                                return GlassListItem(
                                  leading: Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: VoidTheme.accentInfo
                                          .withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: const Icon(Icons.mail_rounded,
                                        size: 20, color: VoidTheme.accentInfo),
                                  ),
                                  title: e['email'] ?? '',
                                  subtitle: e['storage'] != null
                                      ? 'Storage: ${e['storage']} MB'
                                      : null,
                                  trailing: IconButton(
                                    icon: const Icon(Icons.delete_outline,
                                        size: 20, color: VoidTheme.accentDanger),
                                    onPressed: () =>
                                        _deleteEmail(e['email'] ?? ''),
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
        heroTag: 'fab_email',
        onPressed: _showCreateDialog,
        icon: const Icon(Icons.add_rounded),
        label: const Text('New Email'),
      ),
    );
  }
}
