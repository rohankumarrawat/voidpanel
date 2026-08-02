import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../theme/void_theme.dart';
import '../widgets/common_widgets.dart';

class ActivityScreen extends StatefulWidget {
  const ActivityScreen({super.key});

  @override
  State<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends State<ActivityScreen> {
  List<dynamic> _entries = [];
  bool _loading = true;
  int _page = 1;
  int _totalPages = 1;
  String? _levelFilter;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    final params = <String, String>{
      'page': _page.toString(),
      'limit': '30',
    };
    if (_levelFilter != null) params['level'] = _levelFilter!;

    final res = await api.get('/activity/', queryParams: params);
    if (mounted) {
      setState(() {
        _loading = false;
        if (res.success) {
          _entries = res.data['entries'] ?? [];
          _totalPages = res.data['pages'] ?? 1;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Activity Log'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          PopupMenuButton<String?>(
            icon: const Icon(Icons.filter_list_rounded, color: VoidTheme.textMuted),
            onSelected: (v) {
              _levelFilter = v;
              _page = 1;
              _load();
            },
            itemBuilder: (_) => [
              const PopupMenuItem(value: null, child: Text('All')),
              const PopupMenuItem(value: 'success', child: Text('Success')),
              const PopupMenuItem(value: 'error', child: Text('Errors')),
              const PopupMenuItem(value: 'warning', child: Text('Warnings')),
              const PopupMenuItem(value: 'info', child: Text('Info')),
            ],
          ),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: VoidTheme.accentPrimary))
            : _entries.isEmpty
                ? const EmptyState(
                    icon: Icons.history_outlined,
                    title: 'No activity',
                    subtitle: 'Activity log is empty',
                  )
                : Column(
                    children: [
                      Expanded(
                        child: RefreshIndicator(
                          onRefresh: _load,
                          child: ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _entries.length,
                            itemBuilder: (ctx, i) {
                              final e = _entries[i];
                              final level = e['level'] ?? 'info';
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Container(
                                  padding: const EdgeInsets.all(14),
                                  decoration: VoidTheme.simpleCard,
                                  child: Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        width: 34, height: 34,
                                        decoration: BoxDecoration(
                                          color: _levelColor(level).withValues(alpha: 0.12),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Icon(_levelIcon(level), size: 18, color: _levelColor(level)),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              e['action'] ?? '',
                                              style: const TextStyle(
                                                fontSize: 13,
                                                fontWeight: FontWeight.w600,
                                                color: VoidTheme.textPrimary,
                                              ),
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                            if (e['detail'] != null && e['detail'].toString().isNotEmpty) ...[
                                              const SizedBox(height: 3),
                                              Text(
                                                e['detail'],
                                                style: const TextStyle(fontSize: 12, color: VoidTheme.textMuted),
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ],
                                            const SizedBox(height: 4),
                                            Row(
                                              children: [
                                                Text(
                                                  _formatTime(e['timestamp']),
                                                  style: const TextStyle(fontSize: 11, color: VoidTheme.textDisabled),
                                                ),
                                                if (e['category'] != null) ...[
                                                  const SizedBox(width: 8),
                                                  Container(
                                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                    decoration: BoxDecoration(
                                                      color: VoidTheme.bgElevated,
                                                      borderRadius: BorderRadius.circular(4),
                                                    ),
                                                    child: Text(
                                                      e['category'].toString().toUpperCase(),
                                                      style: const TextStyle(
                                                          fontSize: 10,
                                                          fontWeight: FontWeight.w600,
                                                          color: VoidTheme.textMuted),
                                                    ),
                                                  ),
                                                ],
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                      // Pagination
                      if (_totalPages > 1)
                        Container(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          color: VoidTheme.bgSurface,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              IconButton(
                                onPressed: _page > 1
                                    ? () {
                                        _page--;
                                        _load();
                                      }
                                    : null,
                                icon: const Icon(Icons.chevron_left_rounded),
                              ),
                              Text('$_page / $_totalPages',
                                  style: const TextStyle(color: VoidTheme.textSecondary)),
                              IconButton(
                                onPressed: _page < _totalPages
                                    ? () {
                                        _page++;
                                        _load();
                                      }
                                    : null,
                                icon: const Icon(Icons.chevron_right_rounded),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
      ),
    );
  }

  Color _levelColor(String level) {
    switch (level) {
      case 'success': return VoidTheme.accentSuccess;
      case 'error': return VoidTheme.accentDanger;
      case 'warning': return VoidTheme.accentWarning;
      default: return VoidTheme.accentInfo;
    }
  }

  IconData _levelIcon(String level) {
    switch (level) {
      case 'success': return Icons.check_circle_rounded;
      case 'error': return Icons.error_rounded;
      case 'warning': return Icons.warning_rounded;
      default: return Icons.info_rounded;
    }
  }

  String _formatTime(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }
}
