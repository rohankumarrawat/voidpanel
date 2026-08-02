import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class DatabaseScreen extends StatefulWidget {
  const DatabaseScreen({super.key});

  @override
  State<DatabaseScreen> createState() => _DatabaseScreenState();
}

class _DatabaseScreenState extends State<DatabaseScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<dynamic> _databases = [];
  List<dynamic> _users = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final res = await api.get('/databases/');
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) {
          _databases = res.data['databases'] ?? [];
          _users = res.data['users'] ?? [];
        }
      });
    }
  }

  Future<void> _createDb() async {
    final ctrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create Database'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(
            labelText: 'Database name',
            hintText: 'mydb',
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
      final res = await api.post('/databases/create/', body: {'name': ctrl.text.trim()});
      if (!mounted) return;
      _showResult(res);
      if (res.success) _load();
    }
  }

  Future<void> _deleteDb(String name) async {
    final confirmed = await _confirm('Delete database $name?');
    if (!confirmed || !mounted) return;
    final api = context.read<ApiClient>();
    final res = await api.post('/databases/delete/', body: {'name': name});
    if (!mounted) return;
    _showResult(res);
    if (res.success) _load();
  }

  Future<void> _createUser() async {
    final userCtrl = TextEditingController();
    final passCtrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create DB User'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: userCtrl,
              decoration: const InputDecoration(labelText: 'Username'),
              style: const TextStyle(color: VoidTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: passCtrl,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Password'),
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
      final res = await api.post('/databases/users/create/', body: {
        'username': userCtrl.text.trim(),
        'password': passCtrl.text,
      });
      if (!mounted) return;
      _showResult(res);
      if (res.success) _load();
    }
  }

  Future<bool> _confirm(String msg) async {
    return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Confirm'),
            content: Text(msg, style: const TextStyle(color: VoidTheme.textSecondary)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
              ElevatedButton(
                onPressed: () => Navigator.pop(ctx, true),
                style: ElevatedButton.styleFrom(backgroundColor: VoidTheme.accentDanger),
                child: const Text('Delete'),
              ),
            ],
          ),
        ) ??
        false;
  }

  void _showResult(ApiResponse res) {
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
        title: const Text('Databases'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: VoidTheme.accentPrimary,
          labelColor: VoidTheme.accentPrimary,
          unselectedLabelColor: VoidTheme.textMuted,
          tabs: const [
            Tab(text: 'Databases'),
            Tab(text: 'Users'),
          ],
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: VoidTheme.accentPrimary))
            : TabBarView(
                controller: _tabController,
                children: [
                  // Databases tab
                  _databases.isEmpty
                      ? const EmptyState(
                          icon: Icons.view_column_outlined,
                          title: 'No databases',
                          subtitle: 'Create your first MySQL database',
                        )
                      : RefreshIndicator(
                          onRefresh: _load,
                          child: ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _databases.length,
                            itemBuilder: (ctx, i) {
                              final db = _databases[i] is String ? _databases[i] : _databases[i].toString();
                              return GlassListItem(
                                leading: Container(
                                  width: 40, height: 40,
                                  decoration: BoxDecoration(
                                    color: VoidTheme.accentWarning.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.storage_rounded, size: 20, color: VoidTheme.accentWarning),
                                ),
                                title: db,
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete_outline, size: 20, color: VoidTheme.accentDanger),
                                  onPressed: () => _deleteDb(db),
                                ),
                              );
                            },
                          ),
                        ),
                  // Users tab
                  _users.isEmpty
                      ? const EmptyState(
                          icon: Icons.person_outline,
                          title: 'No database users',
                          subtitle: 'Create a database user',
                        )
                      : RefreshIndicator(
                          onRefresh: _load,
                          child: ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _users.length,
                            itemBuilder: (ctx, i) {
                              final u = _users[i] is String ? _users[i] : _users[i].toString();
                              return GlassListItem(
                                leading: Container(
                                  width: 40, height: 40,
                                  decoration: BoxDecoration(
                                    color: VoidTheme.accentInfo.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.person_rounded, size: 20, color: VoidTheme.accentInfo),
                                ),
                                title: u,
                              );
                            },
                          ),
                        ),
                ],
              ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'fab_database',
        onPressed: () {
          if (_tabController.index == 0) {
            _createDb();
          } else {
            _createUser();
          }
        },
        icon: const Icon(Icons.add_rounded),
        label: const Text('Create'),
      ),
    );
  }
}
