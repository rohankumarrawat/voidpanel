import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';
import '../models/drive_item.dart';
import '../providers/mail_provider.dart';

class DriveView extends StatefulWidget {
  const DriveView({super.key});

  @override
  State<DriveView> createState() => _DriveViewState();
}

class _DriveViewState extends State<DriveView> {
  String _activeView = 'my_drive'; // 'my_drive', 'recent', 'starred', 'trash'
  int? _currentFolderId;
  String _currentFolderName = 'My Drive';
  bool _isLoading = true;
  bool _isUploading = false;
  bool _isGridView = false;
  String _searchQuery = '';
  String _selectedCategory = 'all'; // 'all', 'document', 'spreadsheet', 'image', 'media', 'archive', 'code'
  final TextEditingController _searchController = TextEditingController();

  List<DriveFolder> _folders = [];
  List<DriveFile> _files = [];
  List<DriveBreadcrumb> _breadcrumbs = [];
  StorageQuotaInfo _quota = const StorageQuotaInfo();

  @override
  void initState() {
    super.initState();
    _loadDriveData();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadDriveData() async {
    setState(() => _isLoading = true);
    final provider = Provider.of<MailProvider>(context, listen: false);
    final result = await provider.apiService.fetchDriveFiles(
      view: _activeView,
      folderId: _currentFolderId,
    );

    if (mounted) {
      setState(() {
        _isLoading = false;
        _folders = result['folders'] as List<DriveFolder>? ?? [];
        _files = result['files'] as List<DriveFile>? ?? [];
        _breadcrumbs = result['breadcrumbs'] as List<DriveBreadcrumb>? ?? [];
        _quota = result['quota'] as StorageQuotaInfo? ?? const StorageQuotaInfo();
      });
    }
  }

  Color _parseColor(String colorHex) {
    try {
      final hex = colorHex.replaceAll('#', '');
      return Color(int.parse('FF$hex', radix: 16));
    } catch (_) {
      return const Color(0xFF4F46E5);
    }
  }

  IconData _getFileIcon(String category) {
    switch (category.toLowerCase()) {
      case 'document':
        return Icons.description_rounded;
      case 'spreadsheet':
        return Icons.table_chart_rounded;
      case 'image':
        return Icons.image_rounded;
      case 'media':
        return Icons.play_circle_rounded;
      case 'archive':
        return Icons.folder_zip_rounded;
      case 'code':
        return Icons.code_rounded;
      default:
        return Icons.insert_drive_file_rounded;
    }
  }

  Color _getFileColor(String category) {
    switch (category.toLowerCase()) {
      case 'document':
        return const Color(0xFF2563EB);
      case 'spreadsheet':
        return const Color(0xFF10B981);
      case 'image':
        return const Color(0xFFEC4899);
      case 'media':
        return const Color(0xFF8B5CF6);
      case 'archive':
        return const Color(0xFFF59E0B);
      case 'code':
        return const Color(0xFF06B6D4);
      default:
        return const Color(0xFF64748B);
    }
  }



  // ══════════════════════════════════════════════════════════════════════
  //  MODAL: NEW FOLDER CREATION
  // ══════════════════════════════════════════════════════════════════════
  void _showNewFolderModal() {
    final controller = TextEditingController();
    String selectedColor = '#4F46E5';
    final colors = ['#4F46E5', '#10B981', '#FF7A00', '#EC4899', '#3B82F6', '#64748B'];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) {
          final isDark = Theme.of(context).brightness == Brightness.dark;

          return Container(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom + 24,
              top: 16,
              left: 20,
              right: 20,
            ),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : Colors.white,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.25),
                  blurRadius: 20,
                  offset: const Offset(0, -4),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: isDark ? Colors.white24 : Colors.grey[300],
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF4F46E5).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.create_new_folder_rounded, color: Color(0xFF4F46E5), size: 22),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      'Create New Folder',
                      style: GoogleFonts.outfit(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white : const Color(0xFF0F172A),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: controller,
                  autofocus: true,
                  decoration: InputDecoration(
                    labelText: 'Folder Name',
                    hintText: 'e.g. Project Assets, Q4 Invoices',
                    prefixIcon: const Icon(Icons.folder_outlined, size: 20),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                    filled: true,
                    fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Folder Color Theme',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: isDark ? Colors.white70 : const Color(0xFF475569),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: colors.map((c) {
                    final isSel = selectedColor == c;
                    return GestureDetector(
                      onTap: () => setDlgState(() => selectedColor = c),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: _parseColor(c),
                          shape: BoxShape.circle,
                          border: isSel ? Border.all(color: Colors.white, width: 3) : null,
                          boxShadow: isSel
                              ? [
                                  BoxShadow(
                                    color: _parseColor(c).withValues(alpha: 0.5),
                                    blurRadius: 8,
                                    spreadRadius: 2,
                                  ),
                                ]
                              : null,
                        ),
                        child: isSel ? const Icon(Icons.check_rounded, color: Colors.white, size: 20) : null,
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: () async {
                      final name = controller.text.trim();
                      if (name.isNotEmpty) {
                        Navigator.pop(ctx);
                        final provider = Provider.of<MailProvider>(context, listen: false);
                        await provider.apiService.createDriveFolder(
                          name,
                          color: selectedColor,
                          parentId: _currentFolderId,
                        );
                        _loadDriveData();
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF4F46E5),
                      foregroundColor: Colors.white,
                      elevation: 2,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    child: Text(
                      'Create Folder',
                      style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 15),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  MODAL: UPLOAD FILE
  // ══════════════════════════════════════════════════════════════════════
  void _showUploadModal() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final isDark = Theme.of(context).brightness == Brightness.dark;

        return Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.25),
                blurRadius: 20,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white24 : Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.cloud_upload_rounded, color: Color(0xFF10B981), size: 22),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Upload to Sovereign Cloud',
                    style: GoogleFonts.outfit(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : const Color(0xFF0F172A),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                'Files are stored with client-side zero-knowledge encryption.',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: isDark ? Colors.white60 : Colors.black54,
                ),
              ),
              const SizedBox(height: 20),
              // Option 1: Device File Picker
              InkWell(
                onTap: () async {
                  Navigator.pop(ctx);
                  try {
                    final result = await FilePicker.platform.pickFiles(
                      allowMultiple: false,
                      type: FileType.any,
                      withData: true,
                    );
                    if (result != null && result.files.isNotEmpty) {
                      final picked = result.files.first;
                      setState(() => _isUploading = true);
                      if (mounted) {
                        final provider = Provider.of<MailProvider>(context, listen: false);
                        await provider.apiService.uploadDriveFile(
                          filename: picked.name,
                          bytes: picked.bytes ?? [],
                          folderId: _currentFolderId,
                        );
                        if (mounted) {
                          setState(() => _isUploading = false);
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('✓ "${picked.name}" uploaded successfully!'),
                              behavior: SnackBarBehavior.floating,
                              backgroundColor: const Color(0xFF059669),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                          );
                          _loadDriveData();
                        }
                      }
                    }
                  } catch (e) {
                    if (mounted) {
                      setState(() => _isUploading = false);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Upload notice: $e'),
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                    }
                  }
                },
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF4F46E5).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.folder_open_rounded, color: Color(0xFF4F46E5), size: 24),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Browse Device Files',
                              style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Select documents, spreadsheets, images or archives',
                              style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, color: Colors.grey),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  MODAL: RENAME ITEM
  // ══════════════════════════════════════════════════════════════════════
  void _showRenameModal(int id, String type, String currentName) {
    final controller = TextEditingController(text: currentName);

    showDialog(
      context: context,
      builder: (ctx) {
        final isDark = Theme.of(ctx).brightness == Brightness.dark;
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
          title: Text(
            'Rename ${type == 'folder' ? 'Folder' : 'File'}',
            style: GoogleFonts.outfit(fontWeight: FontWeight.bold),
          ),
          content: TextField(
            controller: controller,
            autofocus: true,
            decoration: InputDecoration(
              hintText: 'Enter new name',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final newName = controller.text.trim();
                if (newName.isNotEmpty && newName != currentName) {
                  Navigator.pop(ctx);
                  final provider = Provider.of<MailProvider>(context, listen: false);
                  await provider.apiService.renameDriveItem(id, type, newName);
                  _loadDriveData();
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4F46E5),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Rename'),
            ),
          ],
        );
      },
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  MODAL: FILE OPTIONS SHEET
  // ══════════════════════════════════════════════════════════════════════
  void _showFileOptionsSheet(DriveFile file) {
    final fileColor = _getFileColor(file.category);
    final fileIcon = _getFileIcon(file.category);
    final provider = Provider.of<MailProvider>(context, listen: false);

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final isDark = Theme.of(context).brightness == Brightness.dark;

        return Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.25),
                blurRadius: 20,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: isDark ? Colors.white24 : Colors.grey[300],
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                // File Header
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: fileColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(fileIcon, color: fileColor, size: 28),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            file.filename,
                            style: GoogleFonts.inter(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: fileColor.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  file.extension.toUpperCase(),
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                    color: fileColor,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 6),
                              Text(
                                '${file.formattedSize} • ${file.createdAt}',
                                style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                const Divider(height: 1),
                const SizedBox(height: 12),
                // Fast Actions
                if (_activeView != 'trash') ...[
                  // Copy Share Link
                  ListTile(
                    leading: const Icon(Icons.share_rounded, color: Color(0xFF4F46E5)),
                    title: Text('Copy Share Link', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14)),
                    subtitle: Text('Generate sovereign access token', style: GoogleFonts.inter(fontSize: 11, color: Colors.grey)),
                    onTap: () async {
                      Navigator.pop(ctx);
                      final res = await provider.apiService.toggleShareDriveItem(file.id);
                      if (mounted) {
                        final shareUrl = res['share_url'] ?? 'https://voidonyx.in/drive/share/${file.shareToken}/';
                        Clipboard.setData(ClipboardData(text: shareUrl));
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: const Row(
                              children: [
                                Icon(Icons.check_circle_rounded, color: Colors.white, size: 18),
                                SizedBox(width: 8),
                                Text('✓ Sovereign share link copied to clipboard!'),
                              ],
                            ),
                            behavior: SnackBarBehavior.floating,
                            backgroundColor: const Color(0xFF059669),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                        );
                      }
                    },
                  ),
                  // Star / Unstar
                  ListTile(
                    leading: Icon(
                      file.isStarred ? Icons.star_rounded : Icons.star_border_rounded,
                      color: Colors.amber,
                    ),
                    title: Text(
                      file.isStarred ? 'Remove from Starred' : 'Add to Starred',
                      style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14),
                    ),
                    onTap: () async {
                      Navigator.pop(ctx);
                      await provider.apiService.toggleStarDriveItem(file.id, 'file');
                      _loadDriveData();
                    },
                  ),
                  // Rename
                  ListTile(
                    leading: const Icon(Icons.edit_outlined, color: Color(0xFF3B82F6)),
                    title: Text('Rename File', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14)),
                    onTap: () {
                      Navigator.pop(ctx);
                      _showRenameModal(file.id, 'file', file.filename);
                    },
                  ),
                  // Move to Trash
                  ListTile(
                    leading: const Icon(Icons.delete_outline_rounded, color: Colors.red),
                    title: Text('Move to Trash', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14, color: Colors.red)),
                    onTap: () async {
                      Navigator.pop(ctx);
                      await provider.apiService.trashDriveItem(file.id, 'file');
                      _loadDriveData();
                    },
                  ),
                ] else ...[
                  // In Trash: Restore or Delete Permanently
                  ListTile(
                    leading: const Icon(Icons.restore_from_trash_rounded, color: Color(0xFF10B981)),
                    title: Text('Restore from Trash', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14, color: const Color(0xFF10B981))),
                    onTap: () async {
                      Navigator.pop(ctx);
                      await provider.apiService.restoreDriveItem(file.id, 'file');
                      _loadDriveData();
                    },
                  ),
                  ListTile(
                    leading: const Icon(Icons.delete_forever_rounded, color: Colors.red),
                    title: Text('Delete Permanently', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14, color: Colors.red)),
                    onTap: () async {
                      Navigator.pop(ctx);
                      await provider.apiService.permanentDeleteDriveItem(file.id, 'file');
                      _loadDriveData();
                    },
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  MODAL: FOLDER OPTIONS SHEET
  // ══════════════════════════════════════════════════════════════════════
  void _showFolderOptionsSheet(DriveFolder folder) {
    final folderColor = _parseColor(folder.color);
    final provider = Provider.of<MailProvider>(context, listen: false);

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final isDark = Theme.of(context).brightness == Brightness.dark;

        return Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white24 : Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: folderColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(Icons.folder_rounded, color: folderColor, size: 26),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          folder.name,
                          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          '${folder.fileCount} files inside',
                          style: GoogleFonts.inter(fontSize: 12, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(height: 1),
              const SizedBox(height: 8),
              if (_activeView != 'trash') ...[
                ListTile(
                  leading: const Icon(Icons.folder_open_rounded, color: Color(0xFF4F46E5)),
                  title: Text('Open Folder', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
                  onTap: () {
                    Navigator.pop(ctx);
                    setState(() {
                      _currentFolderId = folder.id;
                      _currentFolderName = folder.name;
                    });
                    _loadDriveData();
                  },
                ),
                ListTile(
                  leading: Icon(
                    folder.isStarred ? Icons.star_rounded : Icons.star_border_rounded,
                    color: Colors.amber,
                  ),
                  title: Text(
                    folder.isStarred ? 'Remove from Starred' : 'Add to Starred',
                    style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                  ),
                  onTap: () async {
                    Navigator.pop(ctx);
                    await provider.apiService.toggleStarDriveItem(folder.id, 'folder');
                    _loadDriveData();
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.edit_outlined, color: Color(0xFF3B82F6)),
                  title: Text('Rename Folder', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
                  onTap: () {
                    Navigator.pop(ctx);
                    _showRenameModal(folder.id, 'folder', folder.name);
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.delete_outline_rounded, color: Colors.red),
                  title: Text('Move to Trash', style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: Colors.red)),
                  onTap: () async {
                    Navigator.pop(ctx);
                    await provider.apiService.trashDriveItem(folder.id, 'folder');
                    _loadDriveData();
                  },
                ),
              ] else ...[
                ListTile(
                  leading: const Icon(Icons.restore_from_trash_rounded, color: Color(0xFF10B981)),
                  title: Text('Restore Folder', style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF10B981))),
                  onTap: () async {
                    Navigator.pop(ctx);
                    await provider.apiService.restoreDriveItem(folder.id, 'folder');
                    _loadDriveData();
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.delete_forever_rounded, color: Colors.red),
                  title: Text('Delete Permanently', style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: Colors.red)),
                  onTap: () async {
                    Navigator.pop(ctx);
                    await provider.apiService.permanentDeleteDriveItem(folder.id, 'folder');
                    _loadDriveData();
                  },
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  CONFIRM: EMPTY TRASH
  // ══════════════════════════════════════════════════════════════════════
  void _confirmEmptyTrash() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('Empty Trash?', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
        content: Text(
          'All items in trash will be permanently purged from your sovereign storage. This action cannot be undone.',
          style: GoogleFonts.inter(fontSize: 13),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final provider = Provider.of<MailProvider>(context, listen: false);
              await provider.apiService.emptyDriveTrash();
              _loadDriveData();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('Empty Trash Forever'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final provider = Provider.of<MailProvider>(context);
    final screenWidth = MediaQuery.of(context).size.width;
    final gridCrossAxisCount = screenWidth >= 1350
        ? 5
        : (screenWidth >= 1050
            ? 4
            : (screenWidth >= 720
                ? 3
                : 2));

    // Filter files by search and category
    final filteredFiles = _files.where((f) {
      if (_selectedCategory != 'all' && f.category.toLowerCase() != _selectedCategory) {
        return false;
      }
      if (_searchQuery.isEmpty) return true;
      final q = _searchQuery.toLowerCase();
      return f.filename.toLowerCase().contains(q) || f.extension.toLowerCase().contains(q);
    }).toList();

    return ColoredBox(
      color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadDriveData,
          color: const Color(0xFF4F46E5),
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
            slivers: [
              // ══════════════════════════════════════════════════════════════
              //  1. EXECUTIVE SLIVER APPBAR (ZERO DUPLICATION)
              // ══════════════════════════════════════════════════════════════
              SliverAppBar(
                floating: true,
                pinned: true,
                snap: false,
                elevation: 0,
                backgroundColor: isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
                surfaceTintColor: Colors.transparent,
                leading: Builder(
                  builder: (drawerCtx) => IconButton(
                    icon: const Icon(Icons.menu_rounded),
                    tooltip: 'Navigation Menu',
                    onPressed: () => Scaffold.of(drawerCtx).openDrawer(),
                  ),
                ),
                titleSpacing: 0,
                title: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF4F46E5), Color(0xFF7C3AED)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF4F46E5).withValues(alpha: 0.35),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: const Icon(Icons.cloud_done_rounded, color: Colors.white, size: 18),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              'VoidDrive',
                              style: GoogleFonts.outfit(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                                letterSpacing: -0.3,
                              ),
                            ),
                          ),
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 5,
                                height: 5,
                                decoration: const BoxDecoration(
                                  color: Color(0xFF10B981),
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 4),
                              Flexible(
                                child: Text(
                                  'Zero Knowledge • Client E2EE',
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                                    fontWeight: FontWeight.w600,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                actions: [
                  IconButton(
                    icon: Icon(
                      _isGridView ? Icons.view_agenda_rounded : Icons.grid_view_rounded,
                      size: 20,
                      color: isDark ? Colors.white70 : const Color(0xFF475569),
                    ),
                    tooltip: _isGridView ? 'Switch to List' : 'Switch to Grid',
                    onPressed: () => setState(() => _isGridView = !_isGridView),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(right: 12, left: 4),
                    child: InkWell(
                      onTap: _showUploadModal,
                      borderRadius: BorderRadius.circular(20),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF4F46E5), Color(0xFF6366F1)],
                          ),
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF4F46E5).withValues(alpha: 0.35),
                              blurRadius: 6,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.cloud_upload_rounded, size: 14, color: Colors.white),
                            const SizedBox(width: 4),
                            Text(
                              'Upload',
                              style: GoogleFonts.inter(
                                fontSize: 11.5,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),

              // ══════════════════════════════════════════════════════════════
              //  2. STORAGE QUOTA & TELEMETRY HERO CARD
              // ══════════════════════════════════════════════════════════════
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // ══════════════════════════════════════════════════════
                      //  2. STORAGE QUOTA & TELEMETRY HERO CARD
                      // ══════════════════════════════════════════════════════
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: isDark
                                ? [const Color(0xFF1E1B4B), const Color(0xFF0F172A)]
                                : [const Color(0xFFEEF2FF), const Color(0xFFE0E7FF)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: const Color(0xFF6366F1).withValues(alpha: isDark ? 0.35 : 0.25),
                            width: 1,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF4F46E5).withValues(alpha: 0.08),
                              blurRadius: 16,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(6),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF4F46E5).withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: const Icon(Icons.pie_chart_rounded, color: Color(0xFF4F46E5), size: 16),
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      'Storage Quota',
                                      style: GoogleFonts.inter(
                                        fontSize: 13,
                                        fontWeight: FontWeight.bold,
                                        color: isDark ? Colors.white : const Color(0xFF1E1B4B),
                                      ),
                                    ),
                                  ],
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF4F46E5).withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    '${_quota.usedPercent.toStringAsFixed(1)}% CAPACITY',
                                    style: GoogleFonts.inter(
                                      fontSize: 10,
                                      fontWeight: FontWeight.w800,
                                      color: const Color(0xFF4F46E5),
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  '${_quota.usedFormatted} used',
                                  style: GoogleFonts.outfit(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w800,
                                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                                  ),
                                ),
                                Text(
                                  'of ${_quota.quotaFormatted} total',
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: isDark ? Colors.white60 : Colors.black54,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: LinearProgressIndicator(
                                value: (_quota.usedPercent / 100.0).clamp(0.0, 1.0),
                                minHeight: 7,
                                backgroundColor: isDark ? Colors.white12 : Colors.black12,
                                valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF6366F1)),
                              ),
                            ),
                            const SizedBox(height: 12),
                            // Quick telemetry badges
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                _buildTelemetryPill(Icons.folder_rounded, '${_folders.length} Folders', isDark),
                                _buildTelemetryPill(Icons.insert_drive_file_rounded, '${_files.length} Files', isDark),
                                _buildTelemetryPill(Icons.storage_rounded, '${_quota.freeFormatted} Free', isDark),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),

                      // ══════════════════════════════════════════════════════
                      //  3. SEARCH INPUT
                      // ══════════════════════════════════════════════════════
                      Container(
                        height: 44,
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1E293B) : Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isDark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.03),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: TextField(
                          controller: _searchController,
                          onChanged: (val) => setState(() => _searchQuery = val),
                          style: GoogleFonts.inter(fontSize: 13),
                          decoration: InputDecoration(
                            hintText: 'Search files, folders or extensions...',
                            hintStyle: GoogleFonts.inter(fontSize: 12, color: Colors.grey),
                            prefixIcon: const Icon(Icons.search_rounded, size: 18, color: Colors.grey),
                            suffixIcon: _searchQuery.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.close_rounded, size: 16),
                                    onPressed: () {
                                      _searchController.clear();
                                      setState(() => _searchQuery = '');
                                    },
                                  )
                                : null,
                            border: InputBorder.none,
                            contentPadding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),

                      // ══════════════════════════════════════════════════════
                      //  4. APPLE-STYLE VIEW SWITCHER TABS
                      // ══════════════════════════════════════════════════════
                      Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1E293B) : const Color(0xFFE2E8F0).withValues(alpha: 0.6),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Row(
                          children: [
                            _buildCapsuleTab('my_drive', 'My Drive', Icons.folder_rounded),
                            _buildCapsuleTab('recent', 'Recent', Icons.schedule_rounded),
                            _buildCapsuleTab('starred', 'Starred', Icons.star_rounded),
                            _buildCapsuleTab('trash', 'Trash', Icons.delete_outline_rounded),
                          ],
                        ),
                      ),

                      // If in trash, show "Empty Trash" trigger
                      if (_activeView == 'trash') ...[
                        const SizedBox(height: 10),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                'Items in trash may be permanently deleted',
                                style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 8),
                            InkWell(
                              onTap: _confirmEmptyTrash,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                decoration: BoxDecoration(
                                  color: Colors.red.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.delete_forever_rounded, color: Colors.red, size: 14),
                                    const SizedBox(width: 4),
                                    Text(
                                      'Empty Trash',
                                      style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.red),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],

                      const SizedBox(height: 12),

                      // ══════════════════════════════════════════════════════
                      //  5. FAST CATEGORY FILTER CHIPS
                      // ══════════════════════════════════════════════════════
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        physics: const BouncingScrollPhysics(),
                        child: Row(
                          children: [
                            _buildCategoryChip('all', 'All Files', Icons.grid_view_rounded, const Color(0xFF4F46E5)),
                            _buildCategoryChip('document', 'Docs', Icons.description_rounded, const Color(0xFF2563EB)),
                            _buildCategoryChip('spreadsheet', 'Sheets', Icons.table_chart_rounded, const Color(0xFF10B981)),
                            _buildCategoryChip('image', 'Images', Icons.image_rounded, const Color(0xFFEC4899)),
                            _buildCategoryChip('media', 'Media', Icons.play_circle_rounded, const Color(0xFF8B5CF6)),
                            _buildCategoryChip('archive', 'Archives', Icons.folder_zip_rounded, const Color(0xFFF59E0B)),
                            _buildCategoryChip('code', 'Code', Icons.code_rounded, const Color(0xFF06B6D4)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // Uploading Banner if in progress
              if (_isUploading)
                SliverToBoxAdapter(
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF4F46E5).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFF4F46E5).withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      children: [
                        const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF4F46E5)),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          'Uploading file to sovereign node...',
                          style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: const Color(0xFF4F46E5)),
                        ),
                      ],
                    ),
                  ),
                ),

              // ══════════════════════════════════════════════════════════════
              //  6. SUBFOLDER BREADCRUMBS
              // ══════════════════════════════════════════════════════════════
              if (_currentFolderId != null || _breadcrumbs.isNotEmpty)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1E293B) : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
                      ),
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: [
                            InkWell(
                              onTap: () {
                                setState(() {
                                  _currentFolderId = null;
                                  _currentFolderName = 'My Drive';
                                });
                                _loadDriveData();
                              },
                              child: Row(
                                children: [
                                  const Icon(Icons.home_rounded, size: 16, color: Color(0xFF4F46E5)),
                                  const SizedBox(width: 4),
                                  Text(
                                    'My Drive',
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: const Color(0xFF4F46E5),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            if (_breadcrumbs.isEmpty && _currentFolderId != null) ...[
                              const Padding(
                                padding: EdgeInsets.symmetric(horizontal: 6),
                                child: Icon(Icons.chevron_right_rounded, size: 14, color: Colors.grey),
                              ),
                              Text(
                                _currentFolderName,
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                                ),
                              ),
                            ],
                            ..._breadcrumbs.map(
                              (bc) => Row(
                                children: [
                                  const Padding(
                                    padding: EdgeInsets.symmetric(horizontal: 6),
                                    child: Icon(Icons.chevron_right_rounded, size: 14, color: Colors.grey),
                                  ),
                                  InkWell(
                                    onTap: () {
                                      setState(() {
                                        _currentFolderId = bc.id;
                                        _currentFolderName = bc.name;
                                      });
                                      _loadDriveData();
                                    },
                                    child: Text(
                                      bc.name,
                                      style: GoogleFonts.inter(
                                        fontSize: 12,
                                        fontWeight: bc.id == _currentFolderId ? FontWeight.bold : FontWeight.w500,
                                        color: bc.id == _currentFolderId
                                            ? (isDark ? Colors.white : const Color(0xFF0F172A))
                                            : Colors.grey,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

              // ══════════════════════════════════════════════════════════════
              //  7. FOLDERS SHELF
              // ══════════════════════════════════════════════════════════════
              if (_folders.isNotEmpty && _activeView != 'trash') ...[
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'FOLDERS (${_folders.length})',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.6,
                            color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                          ),
                        ),
                        InkWell(
                          onTap: _showNewFolderModal,
                          child: Text(
                            '+ New Folder',
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: const Color(0xFF4F46E5),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: SizedBox(
                    height: 104,
                    child: ListView.builder(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemCount: _folders.length,
                      itemBuilder: (context, idx) {
                        final folder = _folders[idx];
                        final folderColor = _parseColor(folder.color);

                        return GestureDetector(
                          onTap: () {
                            setState(() {
                              _currentFolderId = folder.id;
                              _currentFolderName = folder.name;
                            });
                            _loadDriveData();
                          },
                          onLongPress: () => _showFolderOptionsSheet(folder),
                          child: Container(
                            width: 155,
                            margin: const EdgeInsets.only(right: 12),
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            decoration: BoxDecoration(
                              color: isDark ? const Color(0xFF1E293B) : Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: isDark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0),
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.03),
                                  blurRadius: 6,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(5),
                                      decoration: BoxDecoration(
                                        color: folderColor.withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Icon(Icons.folder_rounded, color: folderColor, size: 18),
                                    ),
                                    const Spacer(),
                                    if (folder.isStarred)
                                      const Padding(
                                        padding: EdgeInsets.only(right: 4),
                                        child: Icon(Icons.star_rounded, color: Colors.amber, size: 14),
                                      ),
                                    GestureDetector(
                                      onTap: () => _showFolderOptionsSheet(folder),
                                      child: const Icon(Icons.more_vert_rounded, color: Colors.grey, size: 16),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  folder.name,
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '${folder.fileCount} files',
                                  style: GoogleFonts.inter(fontSize: 10.5, color: Colors.grey),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ],

              // ══════════════════════════════════════════════════════════════
              //  8. FILES SECTION HEADER
              // ══════════════════════════════════════════════════════════════
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'FILES (${filteredFiles.length})',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.6,
                          color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                        ),
                      ),
                      Text(
                        _isGridView ? 'Grid layout' : 'List layout',
                        style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ),

              // ══════════════════════════════════════════════════════════════
              //  9. FILES DISPLAY: LOADING / EMPTY / GRID / LIST
              // ══════════════════════════════════════════════════════════════
              if (_isLoading)
                const SliverToBoxAdapter(
                  child: Center(
                    child: Padding(
                      padding: EdgeInsets.all(48),
                      child: CircularProgressIndicator(color: Color(0xFF4F46E5)),
                    ),
                  ),
                )
              else if (filteredFiles.isEmpty)
                SliverToBoxAdapter(
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(24, 32, 24, 48),
                      child: Column(
                        children: [
                          Container(
                            width: 80,
                            height: 80,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: RadialGradient(
                                colors: [
                                  const Color(0xFF4F46E5).withValues(alpha: 0.2),
                                  const Color(0xFF4F46E5).withValues(alpha: 0.02),
                                ],
                              ),
                            ),
                            child: const Icon(
                              Icons.cloud_done_outlined,
                              size: 44,
                              color: Color(0xFF4F46E5),
                            ),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            _searchQuery.isNotEmpty
                                ? 'No matching files found'
                                : _activeView == 'starred'
                                    ? 'No starred files yet'
                                    : _activeView == 'trash'
                                        ? 'Trash is clean'
                                        : 'Sovereign Drive is Empty',
                            style: GoogleFonts.outfit(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _searchQuery.isNotEmpty
                                ? 'Try refining your search query or reset the filter.'
                                : 'Store sovereign documents, contracts, and media with zero-knowledge AES-256 cloud encryption.',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: isDark ? Colors.white60 : Colors.black54,
                            ),
                          ),
                          const SizedBox(height: 20),
                          Wrap(
                            spacing: 10,
                            runSpacing: 10,
                            alignment: WrapAlignment.center,
                            children: [
                              ElevatedButton.icon(
                                onPressed: _showUploadModal,
                                icon: const Icon(Icons.cloud_upload_rounded, size: 16),
                                label: const Text('Upload File'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF4F46E5),
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                                ),
                              ),
                              OutlinedButton.icon(
                                onPressed: _showNewFolderModal,
                                icon: const Icon(Icons.create_new_folder_rounded, size: 16),
                                label: const Text('New Folder'),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: isDark ? Colors.white : const Color(0xFF0F172A),
                                  side: BorderSide(color: isDark ? Colors.white24 : const Color(0xFFCBD5E1)),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                )
              else if (_isGridView)
                // ─── GRID VIEW ───
                SliverPadding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  sliver: SliverGrid(
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: gridCrossAxisCount,
                      mainAxisSpacing: 12,
                      crossAxisSpacing: 12,
                      childAspectRatio: 0.95,
                    ),
                    delegate: SliverChildBuilderDelegate(
                      (context, index) {
                        final file = filteredFiles[index];
                        final fileColor = _getFileColor(file.category);
                        final fileIcon = _getFileIcon(file.category);

                        return GestureDetector(
                          onTap: () => _showFileOptionsSheet(file),
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: isDark ? const Color(0xFF1E293B) : Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: isDark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0),
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.03),
                                  blurRadius: 6,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(8),
                                      decoration: BoxDecoration(
                                        color: fileColor.withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: Icon(fileIcon, color: fileColor, size: 22),
                                    ),
                                    const Spacer(),
                                    if (file.isStarred)
                                      const Icon(Icons.star_rounded, color: Colors.amber, size: 16),
                                    GestureDetector(
                                      onTap: () => _showFileOptionsSheet(file),
                                      child: const Icon(Icons.more_vert_rounded, color: Colors.grey, size: 16),
                                    ),
                                  ],
                                ),
                                const Spacer(),
                                Text(
                                  file.filename,
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 6),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: fileColor.withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        file.extension.toUpperCase(),
                                        style: GoogleFonts.inter(
                                          fontSize: 9,
                                          fontWeight: FontWeight.w800,
                                          color: fileColor,
                                        ),
                                      ),
                                    ),
                                    Text(
                                      file.formattedSize,
                                      style: GoogleFonts.inter(fontSize: 10, color: Colors.grey),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                      childCount: filteredFiles.length,
                    ),
                  ),
                )
              else
                // ─── LIST VIEW ───
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final file = filteredFiles[index];
                      final fileColor = _getFileColor(file.category);
                      final fileIcon = _getFileIcon(file.category);

                      return Container(
                        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1E293B) : Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: isDark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.02),
                              blurRadius: 4,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: InkWell(
                          onTap: () => _showFileOptionsSheet(file),
                          borderRadius: BorderRadius.circular(16),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: fileColor.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Icon(fileIcon, color: fileColor, size: 22),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      file.filename,
                                      style: GoogleFonts.inter(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                        color: isDark ? Colors.white : const Color(0xFF0F172A),
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 3),
                                    Row(
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                          decoration: BoxDecoration(
                                            color: fileColor.withValues(alpha: 0.12),
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            file.extension.toUpperCase(),
                                            style: GoogleFonts.inter(
                                              fontSize: 9,
                                              fontWeight: FontWeight.w800,
                                              color: fileColor,
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        Text(
                                          file.formattedSize,
                                          style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                                        ),
                                        if (file.createdAt.isNotEmpty) ...[
                                          const Text(' • ', style: TextStyle(color: Colors.grey)),
                                          Text(
                                            file.createdAt,
                                            style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                              // Fast 1-tap star
                              IconButton(
                                icon: Icon(
                                  file.isStarred ? Icons.star_rounded : Icons.star_border_rounded,
                                  color: file.isStarred ? Colors.amber : Colors.grey,
                                  size: 18,
                                ),
                                onPressed: () async {
                                  await provider.apiService.toggleStarDriveItem(file.id, 'file');
                                  _loadDriveData();
                                },
                              ),
                              // More options
                              IconButton(
                                icon: const Icon(Icons.more_vert_rounded, size: 18, color: Colors.grey),
                                onPressed: () => _showFileOptionsSheet(file),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                    childCount: filteredFiles.length,
                  ),
                ),
              const SliverToBoxAdapter(child: SizedBox(height: 80)),
            ],
          ),
        ),
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  UI HELPERS
  // ══════════════════════════════════════════════════════════════════════
  Widget _buildTelemetryPill(IconData icon, String label, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: isDark ? Colors.white.withValues(alpha: 0.05) : Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isDark ? Colors.white10 : const Color(0xFFCBD5E1)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: const Color(0xFF6366F1)),
          const SizedBox(width: 5),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: isDark ? Colors.white70 : const Color(0xFF334155),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCapsuleTab(String id, String label, IconData icon) {
    final isSelected = _activeView == id;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() {
            _activeView = id;
            _currentFolderId = null;
          });
          _loadDriveData();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF4F46E5) : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: const Color(0xFF4F46E5).withValues(alpha: 0.35),
                      blurRadius: 6,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 13,
                color: isSelected ? Colors.white : (isDark ? Colors.white60 : const Color(0xFF64748B)),
              ),
              const SizedBox(width: 5),
              Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                  color: isSelected ? Colors.white : (isDark ? Colors.white60 : const Color(0xFF64748B)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCategoryChip(String id, String label, IconData icon, Color badgeColor) {
    final isSelected = _selectedCategory == id;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTap: () => setState(() => _selectedCategory = id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected
              ? badgeColor
              : (isDark ? const Color(0xFF1E293B) : Colors.white),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected
                ? badgeColor
                : (isDark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0)),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.02),
              blurRadius: 4,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 13,
              color: isSelected
                  ? Colors.white
                  : (isDark ? Colors.white70 : badgeColor),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                color: isSelected
                    ? Colors.white
                    : (isDark ? Colors.white70 : const Color(0xFF334155)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
