import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class DnsScreen extends StatefulWidget {
  const DnsScreen({super.key});

  @override
  State<DnsScreen> createState() => _DnsScreenState();
}

class _DnsScreenState extends State<DnsScreen> {
  List<dynamic> _records = [];
  bool _loading = true;
  String _domain = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final res = await api.get('/dns/records/');
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) {
          _records = res.data['records'] ?? [];
          _domain = res.data['domain'] ?? '';
        }
      });
    }
  }

  Future<void> _addRecord() async {
    final typeCtrl = TextEditingController(text: 'A');
    final nameCtrl = TextEditingController();
    final valueCtrl = TextEditingController();
    final ttlCtrl = TextEditingController(text: '3600');

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add DNS Record'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                value: 'A',
                items: ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'NS']
                    .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                    .toList(),
                onChanged: (v) => typeCtrl.text = v ?? 'A',
                decoration: const InputDecoration(labelText: 'Type'),
                dropdownColor: VoidTheme.bgCard,
                style: const TextStyle(color: VoidTheme.textPrimary),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'Name', hintText: 'www'),
                style: const TextStyle(color: VoidTheme.textPrimary),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: valueCtrl,
                decoration: const InputDecoration(labelText: 'Value', hintText: '1.2.3.4'),
                style: const TextStyle(color: VoidTheme.textPrimary),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: ttlCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'TTL', hintText: '3600'),
                style: const TextStyle(color: VoidTheme.textPrimary),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Add')),
        ],
      ),
    );

    if (result == true && mounted) {
      final api = context.read<ApiClient>();
      final res = await api.post('/dns/records/create/', body: {
        'type': typeCtrl.text,
        'name': nameCtrl.text.trim(),
        'value': valueCtrl.text.trim(),
        'ttl': ttlCtrl.text.trim(),
      });
      if (!mounted) return;
      _showSnack(res);
      if (res.success) _load();
    }
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
        title: Text(_domain.isNotEmpty ? 'DNS: $_domain' : 'DNS Zone'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: VoidTheme.accentPrimary))
            : _records.isEmpty
                ? const EmptyState(
                    icon: Icons.dns_outlined,
                    title: 'No DNS records',
                    subtitle: 'Add DNS records for your domain',
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _records.length,
                      itemBuilder: (ctx, i) {
                        final r = _records[i];
                        final rType = r is Map ? (r['type'] ?? '') : r.toString();
                        final rName = r is Map ? (r['name'] ?? '') : '';
                        final rValue = r is Map ? (r['value'] ?? '') : '';
                        final rTtl = r is Map ? (r['ttl'] ?? '') : '';

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: VoidTheme.simpleCard,
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: _typeColor(rType.toString()).withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    rType.toString(),
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                      color: _typeColor(rType.toString()),
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(rName.toString(),
                                          style: const TextStyle(
                                              fontSize: 14,
                                              fontWeight: FontWeight.w600,
                                              color: VoidTheme.textPrimary)),
                                      Text(rValue.toString(),
                                          style: const TextStyle(
                                              fontSize: 12,
                                              color: VoidTheme.textMuted,
                                              fontFamily: 'monospace'),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis),
                                    ],
                                  ),
                                ),
                                Text('TTL: $rTtl',
                                    style: const TextStyle(fontSize: 11, color: VoidTheme.textDisabled)),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'fab_dns',
        onPressed: _addRecord,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Add Record'),
      ),
    );
  }

  Color _typeColor(String type) {
    switch (type.toUpperCase()) {
      case 'A':
        return VoidTheme.accentSuccess;
      case 'AAAA':
        return VoidTheme.accentInfo;
      case 'CNAME':
        return VoidTheme.accentWarning;
      case 'MX':
        return VoidTheme.accentSecondary;
      case 'TXT':
        return VoidTheme.accentPrimary;
      default:
        return VoidTheme.textMuted;
    }
  }
}
