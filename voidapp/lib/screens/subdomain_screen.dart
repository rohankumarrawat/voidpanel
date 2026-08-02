import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class SubdomainScreen extends StatefulWidget {
  const SubdomainScreen({super.key});

  @override
  State<SubdomainScreen> createState() => _SubdomainScreenState();
}

class _SubdomainScreenState extends State<SubdomainScreen> {
  List<dynamic> _subs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final res = await api.get('/subdomains/');
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) _subs = res.data['subdomains'] ?? [];
      });
    }
  }

  Future<void> _create() async {
    final ctrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create Subdomain'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(
            labelText: 'Subdomain name',
            hintText: 'blog',
            helperText: 'Will create blog.yourdomain.com',
          ),
          style: const TextStyle(color: VoidTheme.textPrimary),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Create')),
        ],
      ),
    );
    if (result == true && mounted) {
      final api = context.read<ApiClient>();
      final res = await api.post('/subdomains/create/', body: {'name': ctrl.text.trim()});
      if (!mounted) return;
      _showSnack(res);
      if (res.success) _load();
    }
  }

  Future<void> _delete(String subdomain) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Subdomain'),
        content: Text('Delete $subdomain?', style: const TextStyle(color: VoidTheme.textSecondary)),
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
    final res = await api.post('/subdomains/delete/', body: {'subdomain': subdomain});
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
        title: const Text('Subdomains'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: VoidTheme.accentPrimary))
            : _subs.isEmpty
                ? const EmptyState(
                    icon: Icons.language_outlined,
                    title: 'No subdomains',
                    subtitle: 'Create a subdomain for your site',
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _subs.length,
                      itemBuilder: (ctx, i) {
                        final s = _subs[i];
                        return GlassListItem(
                          leading: Container(
                            width: 40, height: 40,
                            decoration: BoxDecoration(
                              color: VoidTheme.accentInfo.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Icon(Icons.language_rounded, size: 20, color: VoidTheme.accentInfo),
                          ),
                          title: s['subdomain'] ?? '',
                          subtitle: s['ssl_active'] == true ? '🔒 SSL Active' : '🔓 No SSL',
                          trailing: IconButton(
                            icon: const Icon(Icons.delete_outline, size: 20, color: VoidTheme.accentDanger),
                            onPressed: () => _delete(s['subdomain'] ?? ''),
                          ),
                        );
                      },
                    ),
                  ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'fab_subdomain',
        onPressed: _create,
        icon: const Icon(Icons.add_rounded),
        label: const Text('New Subdomain'),
      ),
    );
  }
}
