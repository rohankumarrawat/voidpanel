import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../providers/mail_provider.dart';

class ContactsView extends StatefulWidget {
  const ContactsView({super.key});

  @override
  State<ContactsView> createState() => _ContactsViewState();
}

class _ContactsViewState extends State<ContactsView> {
  final List<Map<String, String>> _manualContacts = [];
  String _searchQuery = '';
  String _activeFilter = 'ALL';
  bool _showSearch = false;
  final _searchController = TextEditingController();

  static const List<String> _letterFilters = ['ALL', 'A-C', 'D-F', 'G-I', 'J-L', 'M-O', 'P-R', 'S-U', 'V-Z'];

  void _showAddContactDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final emailCtrl = TextEditingController();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        backgroundColor: isDark ? const Color(0xFF1B1638) : Colors.white,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFF6C5CE7).withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.person_add_rounded, color: Color(0xFF6C5CE7), size: 20),
            ),
            const SizedBox(width: 10),
            Text('Add Contact', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 18)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              decoration: InputDecoration(
                hintText: 'Full Name',
                hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[400]),
                prefixIcon: const Icon(Icons.person_rounded, color: Color(0xFF6C5CE7), size: 20),
                filled: true,
                fillColor: isDark ? const Color(0xFF16122E) : const Color(0xFFF8F9FE),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              ),
              style: GoogleFonts.inter(fontSize: 14),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: emailCtrl,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(
                hintText: 'Email Address',
                hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[400]),
                prefixIcon: const Icon(Icons.email_rounded, color: Color(0xFF6C5CE7), size: 20),
                filled: true,
                fillColor: isDark ? const Color(0xFF16122E) : const Color(0xFFF8F9FE),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              ),
              style: GoogleFonts.inter(fontSize: 14),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Cancel', style: GoogleFonts.inter(color: Colors.grey)),
          ),
          ElevatedButton(
            onPressed: () {
              final name = nameCtrl.text.trim();
              final email = emailCtrl.text.trim();
              if (name.isNotEmpty && email.isNotEmpty && email.contains('@')) {
                setState(() {
                  _manualContacts.insert(0, {'name': name, 'email': email});
                });
                Navigator.pop(ctx);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('$name added to contacts ✅', style: GoogleFonts.inter()),
                    backgroundColor: const Color(0xFF10B981),
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF6C5CE7),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            ),
            child: Text('Save', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  bool _matchesFilter(String name) {
    if (_activeFilter == 'ALL') return true;
    final parts = _activeFilter.split('-');
    if (parts.length != 2) return true;
    final firstChar = name.isNotEmpty ? name[0].toUpperCase() : '';
    return firstChar.compareTo(parts[0]) >= 0 && firstChar.compareTo(parts[1]) <= 0;
  }

  Color _getAvatarColor(int index) {
    const colors = [
      Color(0xFF6C5CE7), Color(0xFF00B894), Color(0xFFE17055),
      Color(0xFF0984E3), Color(0xFFEC4899), Color(0xFFF59E0B),
      Color(0xFF8B5CF6), Color(0xFF06B6D4), Color(0xFFEF4444),
    ];
    return colors[index % colors.length];
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Merge real IMAP contacts + manually added contacts
    final imapContacts = provider.extractedContacts;
    final allContacts = <Map<String, String>>[];

    // Add manual contacts first
    allContacts.addAll(_manualContacts);

    // Then add IMAP-extracted contacts (skip duplicates)
    final seenEmails = _manualContacts.map((c) => c['email']?.toLowerCase()).toSet();
    for (final c in imapContacts) {
      if (!seenEmails.contains(c['email']?.toLowerCase())) {
        allContacts.add(c);
      }
    }

    // Apply search filter
    var filteredContacts = allContacts.where((c) {
      final name = c['name'] ?? '';
      final email = c['email'] ?? '';
      final matchesSearch = _searchQuery.isEmpty ||
          name.toLowerCase().contains(_searchQuery) ||
          email.toLowerCase().contains(_searchQuery);
      final matchesLetter = _matchesFilter(name);
      return matchesSearch && matchesLetter;
    }).toList();

    final today = DateFormat('EEEE, MMMM d, y').format(DateTime.now());

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFFAFAFC),
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Contacts', style: GoogleFonts.outfit(fontSize: 26, fontWeight: FontWeight.bold, color: isDark ? Colors.white : const Color(0xFF0F172A))),
                        const SizedBox(height: 2),
                        Text(today, style: GoogleFonts.inter(fontSize: 12, color: Colors.grey)),
                      ],
                    ),
                  ),
                  // Search Toggle
                  GestureDetector(
                    onTap: () => setState(() {
                      _showSearch = !_showSearch;
                      if (!_showSearch) {
                        _searchQuery = '';
                        _searchController.clear();
                      }
                    }),
                    child: Container(
                      width: 40, height: 40,
                      decoration: BoxDecoration(
                        color: _showSearch ? const Color(0xFF6C5CE7).withOpacity(0.1) : (isDark ? const Color(0xFF1B1638) : Colors.white),
                        shape: BoxShape.circle,
                        border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFE2E8F0)),
                      ),
                      child: Icon(Icons.search_rounded, color: _showSearch ? const Color(0xFF6C5CE7) : const Color(0xFF475569), size: 20),
                    ),
                  ),
                  const SizedBox(width: 10),
                  // Add Contact
                  GestureDetector(
                    onTap: () => _showAddContactDialog(context),
                    child: Container(
                      width: 40, height: 40,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(colors: [Color(0xFF6C5CE7), Color(0xFF5A49E3)]),
                        shape: BoxShape.circle,
                        boxShadow: [BoxShadow(color: const Color(0xFF6C5CE7).withOpacity(0.3), blurRadius: 8, offset: const Offset(0, 2))],
                      ),
                      child: const Icon(Icons.add_rounded, color: Colors.white, size: 22),
                    ),
                  ),
                ],
              ),
            ),

            // Search Bar (Animated)
            if (_showSearch)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                child: Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1B1638) : const Color(0xFFF3F4F6),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.search_rounded, size: 18, color: Color(0xFF9CA3AF)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          autofocus: true,
                          decoration: InputDecoration(
                            hintText: 'Search contacts...',
                            hintStyle: GoogleFonts.inter(fontSize: 13, color: Colors.grey[400]),
                            border: InputBorder.none,
                            isDense: true,
                          ),
                          style: GoogleFonts.inter(fontSize: 14),
                          onChanged: (val) => setState(() => _searchQuery = val.toLowerCase()),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            const SizedBox(height: 12),

            // Letter Filter
            SizedBox(
              height: 38,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 20),
                itemCount: _letterFilters.length,
                itemBuilder: (context, index) {
                  final filter = _letterFilters[index];
                  final isActive = _activeFilter == filter;
                  return GestureDetector(
                    onTap: () => setState(() => _activeFilter = filter),
                    child: Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: isActive
                            ? const Color(0xFF6C5CE7)
                            : (isDark ? const Color(0xFF1B1638) : const Color(0xFFF1F5F9)),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        filter,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: isActive ? Colors.white : (isDark ? Colors.grey[300] : const Color(0xFF64748B)),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),

            const SizedBox(height: 8),

            // Contact Count
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
              child: Row(
                children: [
                  Text(
                    '${filteredContacts.length} contacts',
                    style: GoogleFonts.inter(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.w500),
                  ),
                  if (imapContacts.isNotEmpty) ...[
                    const SizedBox(width: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Auto-synced from emails',
                        style: GoogleFonts.inter(fontSize: 10, color: const Color(0xFF10B981), fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Contact List
            Expanded(
              child: filteredContacts.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 80, height: 80,
                            decoration: BoxDecoration(
                              color: const Color(0xFF6C5CE7).withOpacity(0.1),
                              borderRadius: BorderRadius.circular(24),
                            ),
                            child: const Icon(Icons.people_outline_rounded, size: 40, color: Color(0xFF6C5CE7)),
                          ),
                          const SizedBox(height: 16),
                          Text('No contacts found', style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 4),
                          Text(
                            _searchQuery.isNotEmpty
                                ? 'Try a different search term'
                                : 'Send or receive emails to see contacts here',
                            style: GoogleFonts.inter(fontSize: 13, color: Colors.grey),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      itemCount: filteredContacts.length,
                      itemBuilder: (context, index) {
                        final c = filteredContacts[index];
                        final name = c['name'] ?? 'Contact';
                        final email = c['email'] ?? '';
                        final isManual = _manualContacts.any((m) => m['email'] == email);
                        final avatarColor = _getAvatarColor(index);

                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isDark ? const Color(0xFF1B1638) : Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEEFF5)),
                          ),
                          child: Row(
                            children: [
                              CircleAvatar(
                                radius: 20,
                                backgroundColor: avatarColor,
                                child: Text(
                                  name.isNotEmpty ? name[0].toUpperCase() : 'C',
                                  style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Flexible(
                                          child: Text(
                                            name,
                                            style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                        if (isManual) ...[
                                          const SizedBox(width: 6),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                            decoration: BoxDecoration(
                                              color: const Color(0xFFF59E0B).withOpacity(0.1),
                                              borderRadius: BorderRadius.circular(6),
                                            ),
                                            child: Text('Manual', style: GoogleFonts.inter(fontSize: 9, color: const Color(0xFFF59E0B), fontWeight: FontWeight.bold)),
                                          ),
                                        ],
                                      ],
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      email,
                                      style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              // Compose email to contact
                              GestureDetector(
                                onTap: () {
                                  Navigator.pushNamed(context, '/compose', arguments: {'to': email});
                                },
                                child: Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF6C5CE7).withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.mail_outline_rounded, color: Color(0xFF6C5CE7), size: 18),
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
