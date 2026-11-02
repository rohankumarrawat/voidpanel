import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/whatsapp_rule.dart';
import '../providers/mail_provider.dart';

class WhatsAppAlertsView extends StatefulWidget {
  const WhatsAppAlertsView({super.key});

  @override
  State<WhatsAppAlertsView> createState() => _WhatsAppAlertsViewState();
}

class _WhatsAppAlertsViewState extends State<WhatsAppAlertsView> {
  bool _isLoading = true;
  List<WhatsAppAlertRule> _rules = [];
  String _selectedFilter = 'all'; // 'all', 'domain', 'email'
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadRules();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadRules() async {
    setState(() => _isLoading = true);
    final provider = Provider.of<MailProvider>(context, listen: false);
    final rules = await provider.apiService.fetchWhatsAppAlertRules();

    if (mounted) {
      setState(() {
        _isLoading = false;
        _rules = rules;
      });
    }
  }


  void _showAddRuleBottomSheet({String? initialType, String? initialPattern, String? initialNote}) {
    final patternController = TextEditingController(text: initialPattern ?? '');
    final noteController = TextEditingController(text: initialNote ?? '');
    final phoneController = TextEditingController(text: '+919876543210');
    String ruleType = initialType ?? 'domain';

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
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Handle Bar
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: isDark ? Colors.grey[700] : Colors.grey[300],
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),

                  // Title Header
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF059669), Color(0xFF10B981)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(12),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF10B981).withValues(alpha: 0.3),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: const Icon(Icons.mark_chat_unread_rounded, color: Colors.white, size: 22),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Create WhatsApp VIP Rule',
                              style: GoogleFonts.outfit(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                            Text(
                              'Dispatch instant mobile alerts for priority emails',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // Rule Type Segmented Selector
                  Text(
                    'RULE TRIGGER TYPE',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                      letterSpacing: 0.6,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: GestureDetector(
                            onTap: () => setDlgState(() => ruleType = 'domain'),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: ruleType == 'domain'
                                    ? (isDark ? const Color(0xFF1E293B) : Colors.white)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                                boxShadow: ruleType == 'domain'
                                    ? [
                                        BoxShadow(
                                          color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.06),
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
                                    Icons.domain_rounded,
                                    size: 16,
                                    color: ruleType == 'domain' ? const Color(0xFF10B981) : Colors.grey,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Company Domain',
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      fontWeight: ruleType == 'domain' ? FontWeight.bold : FontWeight.w500,
                                      color: ruleType == 'domain'
                                          ? (isDark ? Colors.white : const Color(0xFF0F172A))
                                          : Colors.grey,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        Expanded(
                          child: GestureDetector(
                            onTap: () => setDlgState(() => ruleType = 'email'),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: ruleType == 'email'
                                    ? (isDark ? const Color(0xFF1E293B) : Colors.white)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                                boxShadow: ruleType == 'email'
                                    ? [
                                        BoxShadow(
                                          color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.06),
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
                                    Icons.alternate_email_rounded,
                                    size: 16,
                                    color: ruleType == 'email' ? const Color(0xFF10B981) : Colors.grey,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Specific Sender',
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      fontWeight: ruleType == 'email' ? FontWeight.bold : FontWeight.w500,
                                      color: ruleType == 'email'
                                          ? (isDark ? Colors.white : const Color(0xFF0F172A))
                                          : Colors.grey,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Match Pattern Input
                  TextField(
                    controller: patternController,
                    autofocus: initialPattern == null,
                    decoration: InputDecoration(
                      labelText: ruleType == 'domain' ? 'Domain Match Pattern *' : 'Sender Email Address *',
                      hintText: ruleType == 'domain' ? '@apple.com or stripe.com' : 'elena@novafinance.io',
                      prefixIcon: Icon(
                        ruleType == 'domain' ? Icons.language_rounded : Icons.mail_outline_rounded,
                        size: 20,
                        color: const Color(0xFF10B981),
                      ),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                      filled: true,
                      fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Padding(
                    padding: const EdgeInsets.only(left: 4),
                    child: Text(
                      ruleType == 'domain'
                          ? '💡 Triggers whenever anyone from this entire company domain emails you.'
                          : '💡 Triggers only when this specific high-priority email sender writes to you.',
                      style: GoogleFonts.inter(fontSize: 11, color: Colors.grey[500]),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Label / Note Input
                  TextField(
                    controller: noteController,
                    decoration: InputDecoration(
                      labelText: 'Client or Company Name',
                      hintText: 'e.g. Acme Corp Enterprise Partner',
                      prefixIcon: const Icon(Icons.badge_outlined, size: 20),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                      filled: true,
                      fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Target WhatsApp Phone Number Input
                  TextField(
                    controller: phoneController,
                    keyboardType: TextInputType.phone,
                    decoration: InputDecoration(
                      labelText: 'Target WhatsApp Phone Number *',
                      hintText: '+91 98201 00291',
                      prefixIcon: const Icon(Icons.phone_iphone_rounded, size: 20, color: Color(0xFF10B981)),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                      filled: true,
                      fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Action Buttons
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(
                      onPressed: () async {
                        final pattern = patternController.text.trim();
                        final note = noteController.text.trim();
                        final phone = phoneController.text.trim();

                        if (pattern.isNotEmpty) {
                          Navigator.pop(ctx);
                          final provider = Provider.of<MailProvider>(context, listen: false);
                          await provider.apiService.addWhatsAppAlertRule(
                            ruleType: ruleType,
                            pattern: pattern,
                            targetPhone: phone,
                            note: note,
                          );
                          _loadRules();
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF10B981),
                        foregroundColor: Colors.white,
                        elevation: 3,
                        shadowColor: const Color(0xFF10B981).withValues(alpha: 0.4),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.check_circle_rounded, size: 18),
                          const SizedBox(width: 8),
                          Text(
                            'Activate VIP Rule',
                            style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  void _showTestAlertBottomSheet() {
    final phoneController = TextEditingController(text: '+919876543210');
    bool isSending = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setSheetState) {
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
                      color: isDark ? Colors.grey[700] : Colors.grey[300],
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Header
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.send_to_mobile_rounded, color: Color(0xFF10B981), size: 22),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Test WhatsApp Dispatch',
                            style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'Simulate a live VIP email notification on your device',
                            style: GoogleFonts.inter(fontSize: 12, color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Live WhatsApp Message Preview Bubble
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF0F172A) : const Color(0xFFE7F6EC),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
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
                                width: 8,
                                height: 8,
                                decoration: const BoxDecoration(
                                  color: Color(0xFF10B981),
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Text(
                                'WHATSAPP PRIORITY PREVIEW',
                                style: GoogleFonts.inter(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w800,
                                  color: const Color(0xFF059669),
                                  letterSpacing: 0.5,
                                ),
                              ),
                            ],
                          ),
                          Text(
                            'Just now',
                            style: GoogleFonts.inter(fontSize: 10, color: Colors.grey),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '🚨 VoidMail VIP Priority Alert',
                        style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'From: Sarah Jenkins (Acme Corp)\nSubject: Urgent: Enterprise Contract Signed\nSnippet: "Hi Rohan, we reviewed and approved the contract..."',
                        style: GoogleFonts.inter(fontSize: 12, height: 1.35, color: isDark ? Colors.white70 : const Color(0xFF1E293B)),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '↳ Reply directly to this WhatsApp message to email back.',
                        style: GoogleFonts.inter(fontSize: 11, fontStyle: FontStyle.italic, color: const Color(0xFF059669)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Phone Input
                TextField(
                  controller: phoneController,
                  keyboardType: TextInputType.phone,
                  decoration: InputDecoration(
                    labelText: 'Destination WhatsApp Number',
                    hintText: '+919876543210',
                    prefixIcon: const Icon(Icons.phone_rounded, size: 20),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                    filled: true,
                    fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                  ),
                ),
                const SizedBox(height: 18),

                // Dispatch Button
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: isSending
                        ? null
                        : () async {
                            final phone = phoneController.text.trim();
                            if (phone.isEmpty) return;

                            setSheetState(() => isSending = true);
                            final messenger = ScaffoldMessenger.of(context);
                            final provider = Provider.of<MailProvider>(context, listen: false);
                            final res = await provider.apiService.sendTestWhatsAppAlert(
                              phone: phone,
                              target: 'vip-client@example.com',
                            );
                            if (ctx.mounted) Navigator.pop(ctx);

                            if (mounted) {
                              messenger.showSnackBar(
                                SnackBar(
                                  content: Row(
                                    children: [
                                      const Icon(Icons.mark_chat_read_rounded, color: Colors.white, size: 20),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          res['message'] ?? 'Test alert dispatched to WhatsApp!',
                                          style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 13),
                                        ),
                                      ),
                                    ],
                                  ),
                                  backgroundColor: const Color(0xFF10B981),
                                  behavior: SnackBarBehavior.floating,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                ),
                              );
                            }
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      elevation: 2,
                    ),
                    child: isSending
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.send_rounded, size: 16),
                              const SizedBox(width: 8),
                              Text('Dispatch Test Ping to WhatsApp', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 14)),
                            ],
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

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final filteredRules = _rules.where((r) {
      final matchesFilter = _selectedFilter == 'all' || r.ruleType == _selectedFilter;
      if (!matchesFilter) return false;
      if (_searchQuery.isEmpty) return true;
      final q = _searchQuery.toLowerCase();
      return r.pattern.toLowerCase().contains(q) || r.note.toLowerCase().contains(q);
    }).toList();

    final activeRulesCount = _rules.where((r) => r.isActive).length;
    final totalTriggers = _rules.fold<int>(0, (sum, r) => sum + r.triggerCount);

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: isDark ? const Color(0xFF0F172A) : Colors.white,
        titleSpacing: 0,
        leading: IconButton(
          icon: Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: isDark ? Colors.white10 : const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              Icons.arrow_back_ios_new_rounded,
              size: 15,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
            ),
          ),
          onPressed: () => Navigator.pop(context),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                'WhatsApp VIP Alerts',
                style: GoogleFonts.outfit(
                  fontWeight: FontWeight.w800,
                  fontSize: 17,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                  letterSpacing: -0.3,
                ),
              ),
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    color: Color(0xFF10B981),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 5),
                Flexible(
                  child: Text(
                    'Enterprise Gateway • Instant Push',
                    style: GoogleFonts.inter(
                      fontSize: 10.5,
                      color: const Color(0xFF059669),
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
        actions: [
          IconButton(
            icon: Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.send_to_mobile_rounded, color: Color(0xFF059669), size: 17),
            ),
            tooltip: 'Send Test Alert',
            onPressed: _showTestAlertBottomSheet,
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12, left: 2),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => _showAddRuleBottomSheet(),
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF059669), Color(0xFF10B981)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(10),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF10B981).withValues(alpha: 0.3),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.add_rounded, color: Colors.white, size: 15),
                      const SizedBox(width: 3),
                      Text(
                        'Rule',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadRules,
          color: const Color(0xFF10B981),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
            children: [
              // 1. Executive WhatsApp Dispatch Gateway Hero Card
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF064E3B), Color(0xFF047857), Color(0xFF059669)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(22),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF064E3B).withValues(alpha: 0.35),
                      blurRadius: 14,
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
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.verified_rounded, size: 13, color: Color(0xFF6EE7B7)),
                              const SizedBox(width: 5),
                              Text(
                                'WHATSAPP CLOUD API',
                                style: GoogleFonts.inter(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                  letterSpacing: 0.6,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFF10B981),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            'READY',
                            style: GoogleFonts.inter(
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              color: Colors.white,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'Real-Time Priority Dispatch',
                      style: GoogleFonts.outfit(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Forward high-priority emails from enterprise clients and executives to your WhatsApp instantly. Reply directly via WhatsApp to respond as email.',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: Colors.white.withValues(alpha: 0.9),
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Feature Pill Badges (Responsive Wrap)
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _buildHeroFeatureBadge(Icons.bolt_rounded, '< 2s Delivery Latency'),
                        _buildHeroFeatureBadge(Icons.lock_outline_rounded, 'End-to-End Encrypted'),
                        _buildHeroFeatureBadge(Icons.reply_rounded, 'Two-Way Email Reply'),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // 2. Executive Linear-Style Telemetry Card
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.03),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: IntrinsicHeight(
                  child: Row(
                    children: [
                      Expanded(
                        child: _buildTelemetryCell(
                          label: 'ACTIVE RULES',
                          value: '$activeRulesCount',
                          subtext: '${_rules.length} configured',
                          icon: Icons.tune_rounded,
                          color: const Color(0xFF10B981),
                          isDark: isDark,
                        ),
                      ),
                      VerticalDivider(
                        width: 16,
                        thickness: 1,
                        color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                      ),
                      Expanded(
                        child: _buildTelemetryCell(
                          label: 'DELIVERED',
                          value: '$totalTriggers',
                          subtext: 'WhatsApp pings',
                          icon: Icons.send_rounded,
                          color: const Color(0xFF3B82F6),
                          isDark: isDark,
                        ),
                      ),
                      VerticalDivider(
                        width: 16,
                        thickness: 1,
                        color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                      ),
                      Expanded(
                        child: _buildTelemetryCell(
                          label: 'GATEWAY',
                          value: '100%',
                          subtext: 'Operational',
                          icon: Icons.speed_rounded,
                          color: const Color(0xFF8B5CF6),
                          isDark: isDark,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 18),

              // 3. One-Tap Preset Starter Rules (Chips)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'ONE-TAP STARTER TEMPLATES',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                      letterSpacing: 0.6,
                    ),
                  ),
                  Text(
                    'Tap to add',
                    style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                physics: const BouncingScrollPhysics(),
                child: Row(
                  children: [
                    _buildTemplateChip(
                      icon: Icons.domain_rounded,
                      title: '@acmecorp.com',
                      subtitle: 'Enterprise Client',
                      type: 'domain',
                      pattern: '@acmecorp.com',
                      note: 'Acme Corp Key Account',
                      isDark: isDark,
                    ),
                    const SizedBox(width: 8),
                    _buildTemplateChip(
                      icon: Icons.payments_rounded,
                      title: '@stripe.com',
                      subtitle: 'Payments & Billing',
                      type: 'domain',
                      pattern: '@stripe.com',
                      note: 'Payment Webhook Alerts',
                      isDark: isDark,
                    ),
                    const SizedBox(width: 8),
                    _buildTemplateChip(
                      icon: Icons.star_rounded,
                      title: 'ceo@investor.com',
                      subtitle: 'Executive Inquiries',
                      type: 'email',
                      pattern: 'ceo@investor.com',
                      note: 'Lead Investor Urgent',
                      isDark: isDark,
                    ),
                    const SizedBox(width: 8),
                    _buildTemplateChip(
                      icon: Icons.hub_rounded,
                      title: '@apple.com',
                      subtitle: 'Strategic Partner',
                      type: 'domain',
                      pattern: '@apple.com',
                      note: 'Apple Enterprise Integration',
                      isDark: isDark,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // 4. Filter & Search Bar
              LayoutBuilder(
                builder: (context, constraints) {
                  final searchBar = Container(
                    height: 42,
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E293B) : Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
                      ),
                    ),
                    child: Row(
                      children: [
                        const SizedBox(width: 10),
                        Icon(Icons.search_rounded, size: 18, color: isDark ? Colors.grey[400] : const Color(0xFF94A3B8)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                            controller: _searchController,
                            onChanged: (val) => setState(() => _searchQuery = val.trim()),
                            style: GoogleFonts.inter(fontSize: 12, color: isDark ? Colors.white : const Color(0xFF0F172A)),
                            decoration: InputDecoration(
                              hintText: 'Search rules or clients...',
                              hintStyle: GoogleFonts.inter(fontSize: 12, color: Colors.grey[400]),
                              border: InputBorder.none,
                              isDense: true,
                            ),
                          ),
                        ),
                        if (_searchQuery.isNotEmpty)
                          IconButton(
                            icon: const Icon(Icons.close_rounded, size: 16),
                            color: Colors.grey,
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _searchQuery = '');
                            },
                          ),
                      ],
                    ),
                  );

                  final filterTabs = Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _buildFilterTab('all', 'All', isDark),
                      const SizedBox(width: 4),
                      _buildFilterTab('domain', 'Domains', isDark),
                      const SizedBox(width: 4),
                      _buildFilterTab('email', 'Emails', isDark),
                    ],
                  );

                  if (constraints.maxWidth < 360) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        searchBar,
                        const SizedBox(height: 8),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          physics: const BouncingScrollPhysics(),
                          child: filterTabs,
                        ),
                      ],
                    );
                  }

                  return Row(
                    children: [
                      Expanded(child: searchBar),
                      const SizedBox(width: 6),
                      filterTabs,
                    ],
                  );
                },
              ),
              const SizedBox(height: 16),

              // 5. Active Alert Rules List or Illustrated Empty State
              if (_isLoading)
                const Padding(
                  padding: EdgeInsets.all(40),
                  child: Center(child: CircularProgressIndicator(color: Color(0xFF10B981))),
                )
              else if (filteredRules.isEmpty)
                _buildIllustratedEmptyState(isDark)
              else
                ...filteredRules.map((rule) => _buildRuleCard(rule, isDark)),
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ─── COMPONENT BUILDERS ───────────────────────────────────────────────
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildHeroFeatureBadge(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: const Color(0xFF6EE7B7)),
          const SizedBox(width: 5),
          Text(
            text,
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTelemetryCell({
    required String label,
    required String value,
    required String subtext,
    required IconData icon,
    required Color color,
    required bool isDark,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                  letterSpacing: 0.5,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 5),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            value,
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
              letterSpacing: -0.5,
            ),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          subtext,
          style: GoogleFonts.inter(
            fontSize: 10,
            color: isDark ? Colors.grey[500] : const Color(0xFF94A3B8),
            fontWeight: FontWeight.w500,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }

  Widget _buildTemplateChip({
    required IconData icon,
    required String title,
    required String subtitle,
    required String type,
    required String pattern,
    required String note,
    required bool isDark,
  }) {
    return InkWell(
      onTap: () {
        _showAddRuleBottomSheet(
          initialType: type,
          initialPattern: pattern,
          initialNote: note,
        );
      },
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E293B) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.25)),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF10B981).withValues(alpha: 0.05),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, size: 14, color: const Color(0xFF059669)),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold),
                ),
                Text(
                  subtitle,
                  style: GoogleFonts.inter(fontSize: 10, color: Colors.grey),
                ),
              ],
            ),
            const SizedBox(width: 6),
            const Icon(Icons.add_circle_outline_rounded, size: 14, color: Color(0xFF10B981)),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterTab(String filterId, String label, bool isDark) {
    final isSelected = _selectedFilter == filterId;

    return GestureDetector(
      onTap: () => setState(() => _selectedFilter = filterId),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0xFF10B981)
              : (isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9)),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            color: isSelected
                ? Colors.white
                : (isDark ? Colors.grey[400] : const Color(0xFF64748B)),
          ),
        ),
      ),
    );
  }

  Widget _buildRuleCard(WhatsAppAlertRule rule, bool isDark) {
    final isDomain = rule.ruleType == 'domain';
    final provider = Provider.of<MailProvider>(context, listen: false);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: rule.isActive
              ? (isDark ? Colors.white10 : const Color(0xFFE2E8F0))
              : Colors.grey.withValues(alpha: 0.2),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: Type Pill & Switch
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: isDomain
                            ? const Color(0xFF3B82F6).withValues(alpha: 0.12)
                            : const Color(0xFF10B981).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            isDomain ? Icons.domain_rounded : Icons.person_rounded,
                            size: 12,
                            color: isDomain ? const Color(0xFF2563EB) : const Color(0xFF059669),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            isDomain ? 'COMPANY DOMAIN' : 'SENDER EMAIL',
                            style: GoogleFonts.inter(
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                              color: isDomain ? const Color(0xFF2563EB) : const Color(0xFF059669),
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: rule.isActive
                            ? const Color(0xFF10B981).withValues(alpha: 0.1)
                            : Colors.grey.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        rule.isActive ? 'ACTIVE' : 'PAUSED',
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w800,
                          color: rule.isActive ? const Color(0xFF059669) : Colors.grey,
                        ),
                      ),
                    ),
                  ],
                ),
                Switch.adaptive(
                  value: rule.isActive,
                  activeColor: const Color(0xFF10B981),
                  onChanged: (val) async {
                    await provider.apiService.toggleWhatsAppAlertRule(rule.id);
                    _loadRules();
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Pattern Match
            Text(
              rule.pattern,
              style: GoogleFonts.outfit(
                fontSize: 17,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF0F172A),
                letterSpacing: -0.2,
              ),
            ),
            if (rule.note.isNotEmpty) ...[
              const SizedBox(height: 3),
              Text(
                rule.note,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                ),
              ),
            ],
            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 10),

            // Bottom Actions & Metadata
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Icon(Icons.bolt_rounded, size: 14, color: Colors.grey[500]),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          '${rule.triggerCount} pings • Last: ${rule.lastTriggered}',
                          style: GoogleFonts.inter(fontSize: 11, color: Colors.grey[500]),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, size: 18, color: Colors.redAccent),
                  tooltip: 'Delete Rule',
                  onPressed: () async {
                    await provider.apiService.deleteWhatsAppAlertRule(rule.id);
                    _loadRules();
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIllustratedEmptyState(bool isDark) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 30),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    const Color(0xFF10B981).withValues(alpha: 0.2),
                    const Color(0xFF059669).withValues(alpha: 0.05),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF10B981).withValues(alpha: 0.15),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: const Center(
                child: Icon(Icons.mark_chat_unread_rounded, color: Color(0xFF059669), size: 40),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              _searchQuery.isNotEmpty ? 'No Matching VIP Rules' : 'Never Miss a High-Stakes Email',
              style: GoogleFonts.outfit(
                fontSize: 19,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF0F172A),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              _searchQuery.isNotEmpty
                  ? 'No rules match "$_searchQuery". Try clearing your search.'
                  : 'Route important sender domains, enterprise clients, and investors straight to WhatsApp with real-time two-way reply.',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                height: 1.45,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 12,
              runSpacing: 10,
              children: [
                ElevatedButton(
                  onPressed: () => _showAddRuleBottomSheet(),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    elevation: 2,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.add_rounded, size: 16),
                      const SizedBox(width: 6),
                      Text(
                        'Create VIP Rule',
                        style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
