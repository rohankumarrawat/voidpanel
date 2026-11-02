import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/crm_models.dart';
import '../providers/mail_provider.dart';
import 'compose_view.dart';

class CrmView extends StatefulWidget {
  const CrmView({super.key});

  @override
  State<CrmView> createState() => _CrmViewState();
}

class _CrmViewState extends State<CrmView> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();
  bool _isLoading = true;
  String _selectedStage = 'all'; // 'all', 'lead', 'contacted', 'proposal', 'negotiation', 'won'
  String _searchQuery = '';

  CrmSummary _summary = const CrmSummary();
  List<CrmContact> _contacts = [];
  List<CrmDeal> _deals = [];
  List<CrmCompany> _companies = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (mounted) setState(() {});
    });
    _loadCrmData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadCrmData() async {
    setState(() => _isLoading = true);
    final provider = Provider.of<MailProvider>(context, listen: false);
    final result = await provider.apiService.fetchCrmOverview();

    if (mounted) {
      setState(() {
        _isLoading = false;
        _summary = result['summary'] as CrmSummary? ?? const CrmSummary();
        _contacts = result['contacts'] as List<CrmContact>? ?? [];
        _deals = result['deals'] as List<CrmDeal>? ?? [];
        _companies = result['companies'] as List<CrmCompany>? ?? [];
      });
    }
  }


  Color _getStageColor(String stage) {
    switch (stage.toLowerCase()) {
      case 'lead':
        return const Color(0xFF64748B);
      case 'contacted':
        return const Color(0xFF2563EB);
      case 'proposal':
        return const Color(0xFF7C3AED);
      case 'negotiation':
        return const Color(0xFFFF7A00);
      case 'won':
        return const Color(0xFF10B981);
      case 'lost':
        return const Color(0xFFEF4444);
      default:
        return const Color(0xFF64748B);
    }
  }

  IconData _getStageIcon(String stage) {
    switch (stage.toLowerCase()) {
      case 'lead':
        return Icons.inbox_rounded;
      case 'contacted':
        return Icons.phone_in_talk_rounded;
      case 'proposal':
        return Icons.description_rounded;
      case 'negotiation':
        return Icons.handshake_rounded;
      case 'won':
        return Icons.emoji_events_rounded;
      default:
        return Icons.label_outline_rounded;
    }
  }

  void _showAddDealModal() {
    final titleController = TextEditingController();
    final companyController = TextEditingController();
    final contactController = TextEditingController();
    final amountController = TextEditingController();
    String stage = 'lead';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) {
          final isDark = Theme.of(context).brightness == Brightness.dark;

          return Container(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              top: 16,
              left: 20,
              right: 20,
            ),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : Colors.white,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
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
                        color: Colors.grey[300],
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
                          color: const Color(0xFF10B981).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(Icons.add_business_rounded, color: Color(0xFF10B981), size: 20),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        'Create Pipeline Deal',
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
                    controller: titleController,
                    decoration: InputDecoration(
                      labelText: 'Deal Opportunity Title *',
                      hintText: 'e.g. Acme 500-Seat Sovereign Cluster',
                      prefixIcon: const Icon(Icons.business_center_outlined, size: 20),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                      filled: true,
                      fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: companyController,
                          decoration: InputDecoration(
                            labelText: 'Company / Client',
                            hintText: 'e.g. Acme Corp',
                            prefixIcon: const Icon(Icons.domain_rounded, size: 20),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                          controller: contactController,
                          decoration: InputDecoration(
                            labelText: 'Contact Person',
                            hintText: 'e.g. Sarah Jenkins',
                            prefixIcon: const Icon(Icons.person_outline_rounded, size: 20),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: amountController,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: InputDecoration(
                            labelText: 'Deal Value (₹) *',
                            prefixText: '₹ ',
                            prefixStyle: const TextStyle(fontWeight: FontWeight.bold),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: stage,
                          decoration: InputDecoration(
                            labelText: 'Stage',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'lead', child: Text('Lead')),
                            DropdownMenuItem(value: 'contacted', child: Text('Contacted')),
                            DropdownMenuItem(value: 'proposal', child: Text('Proposal')),
                            DropdownMenuItem(value: 'negotiation', child: Text('Negotiation')),
                            DropdownMenuItem(value: 'won', child: Text('Closed Won')),
                          ],
                          onChanged: (val) {
                            if (val != null) setDlgState(() => stage = val);
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      onPressed: () async {
                        final title = titleController.text.trim();
                        final company = companyController.text.trim();
                        final contact = contactController.text.trim();
                        final amt = double.tryParse(amountController.text.trim()) ?? 0.0;

                        if (title.isNotEmpty) {
                          Navigator.pop(ctx);
                          final provider = Provider.of<MailProvider>(context, listen: false);
                          await provider.apiService.saveCrmDeal({
                            'title': title,
                            'company_name': company,
                            'contact_name': contact,
                            'amount': amt,
                            'stage': stage,
                          });
                          _loadCrmData();
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF10B981),
                        foregroundColor: Colors.white,
                        elevation: 2,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      child: Text(
                        'Create Deal',
                        style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 15),
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

  void _showAddContactModal() {
    final nameController = TextEditingController();
    final emailController = TextEditingController();
    final companyController = TextEditingController();
    final phoneController = TextEditingController();
    final titleController = TextEditingController();
    String status = 'Lead';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) {
          final isDark = Theme.of(context).brightness == Brightness.dark;

          return Container(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              top: 16,
              left: 20,
              right: 20,
            ),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : Colors.white,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
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
                        color: Colors.grey[300],
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
                          color: const Color(0xFF3B82F6).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(Icons.person_add_rounded, color: Color(0xFF3B82F6), size: 20),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        'Add Client Contact',
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
                    controller: nameController,
                    decoration: InputDecoration(
                      labelText: 'Full Name *',
                      hintText: 'e.g. Sarah Jenkins',
                      prefixIcon: const Icon(Icons.badge_outlined, size: 20),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                      filled: true,
                      fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: emailController,
                    keyboardType: TextInputType.emailAddress,
                    decoration: InputDecoration(
                      labelText: 'Email Address *',
                      hintText: 'e.g. sarah@acmecorp.com',
                      prefixIcon: const Icon(Icons.mail_outline_rounded, size: 20),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                      filled: true,
                      fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: companyController,
                          decoration: InputDecoration(
                            labelText: 'Company',
                            hintText: 'Acme Corp',
                            prefixIcon: const Icon(Icons.domain_rounded, size: 20),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                          controller: titleController,
                          decoration: InputDecoration(
                            labelText: 'Job Title',
                            hintText: 'VP Tech',
                            prefixIcon: const Icon(Icons.work_outline_rounded, size: 20),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: phoneController,
                          keyboardType: TextInputType.phone,
                          decoration: InputDecoration(
                            labelText: 'Phone Number',
                            hintText: '+91 98201...',
                            prefixIcon: const Icon(Icons.phone_outlined, size: 20),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: status,
                          decoration: InputDecoration(
                            labelText: 'Status',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            filled: true,
                            fillColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFF8FAFC),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'Lead', child: Text('Lead')),
                            DropdownMenuItem(value: 'Opportunity', child: Text('Opportunity')),
                            DropdownMenuItem(value: 'Customer', child: Text('Customer')),
                          ],
                          onChanged: (val) {
                            if (val != null) setDlgState(() => status = val);
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      onPressed: () async {
                        final name = nameController.text.trim();
                        final email = emailController.text.trim();
                        final company = companyController.text.trim();
                        final phone = phoneController.text.trim();
                        final title = titleController.text.trim();

                        if (name.isNotEmpty && email.isNotEmpty) {
                          Navigator.pop(ctx);
                          final provider = Provider.of<MailProvider>(context, listen: false);
                          await provider.apiService.saveCrmContact({
                            'name': name,
                            'email': email,
                            'company_name': company,
                            'phone': phone,
                            'job_title': title,
                            'status': status,
                          });
                          _loadCrmData();
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF3B82F6),
                        foregroundColor: Colors.white,
                        elevation: 2,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      child: Text(
                        'Save Contact',
                        style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 15),
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final provider = Provider.of<MailProvider>(context);

    // Filter deals by search and stage
    final filteredDeals = _deals.where((d) {
      final matchesStage = _selectedStage == 'all' || d.stage.toLowerCase() == _selectedStage;
      if (!matchesStage) return false;
      if (_searchQuery.isEmpty) return true;
      final q = _searchQuery.toLowerCase();
      return d.title.toLowerCase().contains(q) ||
          d.companyName.toLowerCase().contains(q) ||
          d.contactName.toLowerCase().contains(q);
    }).toList();

    final filteredContacts = _contacts.where((c) {
      if (_searchQuery.isEmpty) return true;
      final q = _searchQuery.toLowerCase();
      return c.name.toLowerCase().contains(q) ||
          c.email.toLowerCase().contains(q) ||
          c.companyName.toLowerCase().contains(q);
    }).toList();

    final filteredCompanies = _companies.where((co) {
      if (_searchQuery.isEmpty) return true;
      final q = _searchQuery.toLowerCase();
      return co.name.toLowerCase().contains(q) ||
          co.domain.toLowerCase().contains(q) ||
          co.industry.toLowerCase().contains(q);
    }).toList();

    return ColoredBox(
      color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadCrmData,
          color: provider.accentColor,
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
                title: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(7),
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
                        child: const Icon(Icons.leaderboard_rounded, color: Colors.white, size: 18),
                      ),
                      const SizedBox(width: 10),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Commercial Pipeline',
                            style: GoogleFonts.outfit(
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                              letterSpacing: -0.3,
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
                              Text(
                                'Deals & Intelligence',
                                style: GoogleFonts.inter(
                                  fontSize: 10,
                                  color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                                  fontWeight: FontWeight.w600,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                actions: [
                  IconButton(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                    icon: Icon(Icons.person_add_rounded, size: 19, color: isDark ? Colors.white70 : const Color(0xFF475569)),
                    tooltip: 'Add Contact',
                    onPressed: _showAddContactModal,
                  ),
                  Padding(
                    padding: const EdgeInsets.only(right: 12, left: 4),
                    child: InkWell(
                      onTap: _showAddDealModal,
                      borderRadius: BorderRadius.circular(20),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF059669), Color(0xFF10B981)],
                          ),
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF10B981).withValues(alpha: 0.35),
                              blurRadius: 6,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.add_rounded, size: 15, color: Colors.white),
                            const SizedBox(width: 3),
                            Text(
                              'Deal',
                              style: GoogleFonts.inter(
                                fontSize: 11,
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
              //  2. EXECUTIVE KPI SHOWCASE CARDS & FILTERS
              // ══════════════════════════════════════════════════════════════
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [

                      // 2. Executive KPI Cards (Grid Showcase)
                      Builder(
                        builder: (context) {
                          final isWide = MediaQuery.of(context).size.width >= 800;
                          final card1 = _buildModernKpiCard(
                            title: 'ACTIVE PIPELINE',
                            amount: _summary.formattedPipeline,
                            subtext: '${_summary.activeDealsCount} active deals',
                            icon: Icons.trending_up_rounded,
                            gradientColors: [const Color(0xFF4F46E5), const Color(0xFF6366F1)],
                            isDark: isDark,
                            width: isWide ? null : 170,
                          );
                          final card2 = _buildModernKpiCard(
                            title: 'WON REVENUE',
                            amount: _summary.formattedWon,
                            subtext: '${_summary.wonDealsCount} closed won',
                            icon: Icons.verified_rounded,
                            gradientColors: [const Color(0xFF059669), const Color(0xFF10B981)],
                            isDark: isDark,
                            width: isWide ? null : 170,
                          );
                          final card3 = _buildModernKpiCard(
                            title: 'CONVERSION',
                            amount: '${_summary.winRate.toStringAsFixed(1)}%',
                            subtext: '${_summary.totalDeals} total opportunities',
                            icon: Icons.pie_chart_rounded,
                            gradientColors: [const Color(0xFFEA580C), const Color(0xFFFF7A00)],
                            isDark: isDark,
                            width: isWide ? null : 170,
                          );

                          if (isWide) {
                            return Row(
                              children: [
                                Expanded(child: card1),
                                const SizedBox(width: 14),
                                Expanded(child: card2),
                                const SizedBox(width: 14),
                                Expanded(child: card3),
                              ],
                            );
                          }

                          return SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            physics: const BouncingScrollPhysics(),
                            child: Row(
                              children: [
                                card1,
                                const SizedBox(width: 10),
                                card2,
                                const SizedBox(width: 10),
                                card3,
                              ],
                            ),
                          );
                        },
                      ),
                      const SizedBox(height: 14),

                      // 3. Search & Filter Bar
                      Container(
                        height: 44,
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1E293B) : Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.03),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Row(
                          children: [
                            const SizedBox(width: 12),
                            Icon(Icons.search_rounded, size: 20, color: isDark ? Colors.grey[400] : const Color(0xFF94A3B8)),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _searchController,
                                onChanged: (val) => setState(() => _searchQuery = val.trim()),
                                style: GoogleFonts.inter(
                                  fontSize: 13,
                                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                                ),
                                decoration: InputDecoration(
                                  hintText: 'Search deals, clients & companies...',
                                  hintStyle: GoogleFonts.inter(
                                    fontSize: 13,
                                    color: isDark ? Colors.grey[500] : const Color(0xFF94A3B8),
                                  ),
                                  border: InputBorder.none,
                                  isDense: true,
                                ),
                              ),
                            ),
                            if (_searchQuery.isNotEmpty)
                              IconButton(
                                icon: const Icon(Icons.close_rounded, size: 18),
                                color: Colors.grey,
                                onPressed: () {
                                  _searchController.clear();
                                  setState(() => _searchQuery = '');
                                },
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),

                      // 4. Apple-style Segmented Capsule Tabs
                      Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1E293B) : const Color(0xFFE2E8F0).withValues(alpha: 0.6),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Row(
                          children: [
                            _buildSegmentTab(0, 'Deals', _deals.length, isDark),
                            _buildSegmentTab(1, 'Contacts', _contacts.length, isDark),
                            _buildSegmentTab(2, 'Companies', _companies.length, isDark),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // 5. Active Tab Body Content
              if (_tabController.index == 0) ...[
                // Stage Horizontal Chips (Deals Tab Only)
                SliverToBoxAdapter(
                  child: Container(
                    height: 38,
                    margin: const EdgeInsets.only(bottom: 12),
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      physics: const BouncingScrollPhysics(),
                      children: [
                        _buildFilterStageChip('all', 'All Deals', _deals.length, const Color(0xFF059669), isDark),
                        _buildFilterStageChip('lead', 'Leads', _deals.where((d) => d.stage.toLowerCase() == 'lead').length, const Color(0xFF64748B), isDark),
                        _buildFilterStageChip('contacted', 'Contacted', _deals.where((d) => d.stage.toLowerCase() == 'contacted').length, const Color(0xFF2563EB), isDark),
                        _buildFilterStageChip('proposal', 'Proposal', _deals.where((d) => d.stage.toLowerCase() == 'proposal').length, const Color(0xFF7C3AED), isDark),
                        _buildFilterStageChip('negotiation', 'Negotiation', _deals.where((d) => d.stage.toLowerCase() == 'negotiation').length, const Color(0xFFFF7A00), isDark),
                        _buildFilterStageChip('won', 'Won', _deals.where((d) => d.stage.toLowerCase() == 'won').length, const Color(0xFF10B981), isDark),
                      ],
                    ),
                  ),
                ),

                // Deals List / Empty State
                if (_isLoading)
                  const SliverFillRemaining(child: Center(child: CircularProgressIndicator()))
                else if (filteredDeals.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _buildEmptyState(
                      icon: Icons.handshake_rounded,
                      iconColor: const Color(0xFF4F46E5),
                      title: _searchQuery.isNotEmpty ? 'No Matching Deals' : 'Your Pipeline is Empty',
                      subtitle: _searchQuery.isNotEmpty
                          ? 'No deals match "$_searchQuery". Try clearing your search.'
                          : 'Create your first commercial deal to track enterprise contracts, values, and sales stages.',
                      primaryBtnLabel: '+ Create First Deal',
                      onPrimaryPressed: _showAddDealModal,
                      isDark: isDark,
                    ),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, idx) => _buildDealCard(filteredDeals[idx], isDark),
                        childCount: filteredDeals.length,
                      ),
                    ),
                  ),
              ] else if (_tabController.index == 1) ...[
                // Tab 2: Contacts List
                if (_isLoading)
                  const SliverFillRemaining(child: Center(child: CircularProgressIndicator()))
                else if (filteredContacts.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _buildEmptyState(
                      icon: Icons.people_alt_rounded,
                      iconColor: const Color(0xFF059669),
                      title: _searchQuery.isNotEmpty ? 'No Matching Contacts' : 'No Contacts Recorded',
                      subtitle: _searchQuery.isNotEmpty
                          ? 'No contacts match "$_searchQuery".'
                          : 'Build your client address book with company roles, verified emails, and direct phone numbers.',
                      primaryBtnLabel: '+ Add First Contact',
                      onPrimaryPressed: _showAddContactModal,
                      isDark: isDark,
                    ),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, idx) => _buildContactCard(filteredContacts[idx], isDark),
                        childCount: filteredContacts.length,
                      ),
                    ),
                  ),
              ] else ...[
                // Tab 3: Companies Directory
                if (_isLoading)
                  const SliverFillRemaining(child: Center(child: CircularProgressIndicator()))
                else if (filteredCompanies.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _buildEmptyState(
                      icon: Icons.apartment_rounded,
                      iconColor: const Color(0xFF7C3AED),
                      title: _searchQuery.isNotEmpty ? 'No Matching Companies' : 'No Companies Directory',
                      subtitle: _searchQuery.isNotEmpty
                          ? 'No company accounts match "$_searchQuery".'
                          : 'Companies associated with your deals and contacts will automatically appear here.',
                      primaryBtnLabel: '+ Create Deal for Company',
                      onPrimaryPressed: _showAddDealModal,
                      isDark: isDark,
                    ),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, idx) => _buildCompanyCard(filteredCompanies[idx], isDark),
                        childCount: filteredCompanies.length,
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ─── COMPONENT BUILDERS ───────────────────────────────────────────────
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildModernKpiCard({
    required String title,
    required String amount,
    required String subtext,
    required IconData icon,
    required List<Color> gradientColors,
    required bool isDark,
    double? width = 170,
  }) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.04),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                    color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: gradientColors,
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: Colors.white, size: 16),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            amount,
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
              letterSpacing: -0.5,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          Text(
            subtext,
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildSegmentTab(int index, String label, int count, bool isDark) {
    final isSelected = _tabController.index == index;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() {
            _tabController.animateTo(index);
          });
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected
                ? (isDark ? const Color(0xFF334155) : Colors.white)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.06),
                      blurRadius: 6,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  label,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                    color: isSelected
                        ? (isDark ? Colors.white : const Color(0xFF0F172A))
                        : (isDark ? Colors.grey[400] : const Color(0xFF64748B)),
                  ),
                ),
                const SizedBox(width: 5),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? (const Color(0xFF10B981).withValues(alpha: 0.15))
                        : (isDark ? Colors.white10 : const Color(0xFFCBD5E1).withValues(alpha: 0.5)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '$count',
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: isSelected
                          ? const Color(0xFF10B981)
                          : (isDark ? Colors.grey[400] : const Color(0xFF64748B)),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFilterStageChip(String stageId, String label, int count, Color color, bool isDark) {
    final isSelected = _selectedStage == stageId;

    return GestureDetector(
      onTap: () => setState(() => _selectedStage = stageId),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected
              ? (isDark ? const Color(0xFF1E293B) : Colors.white)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected
                ? color
                : (isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
            width: isSelected ? 1.5 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: color.withValues(alpha: 0.15),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              '$label ($count)',
              style: GoogleFonts.inter(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                color: isSelected
                    ? (isDark ? Colors.white : const Color(0xFF0F172A))
                    : (isDark ? Colors.grey[400] : const Color(0xFF64748B)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDealCard(CrmDeal deal, bool isDark) {
    final stageColor = _getStageColor(deal.stage);
    final stageIcon = _getStageIcon(deal.stage);
    final provider = Provider.of<MailProvider>(context, listen: false);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.03),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: Company Name & Amount
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Container(
                        width: 26,
                        height: 26,
                        decoration: BoxDecoration(
                          color: stageColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(Icons.domain_rounded, size: 14, color: stageColor),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          deal.companyName.isNotEmpty ? deal.companyName : 'Direct Client',
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    deal.formattedAmount,
                    style: GoogleFonts.outfit(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: const Color(0xFF059669),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Deal Title
            Text(
              deal.title,
              style: GoogleFonts.outfit(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF0F172A),
                letterSpacing: -0.2,
              ),
            ),
            const SizedBox(height: 6),

            // Contact Person Chip
            if (deal.contactName.isNotEmpty)
              Row(
                children: [
                  CircleAvatar(
                    radius: 9,
                    backgroundColor: const Color(0xFF4F46E5),
                    child: Text(
                      deal.contactName[0].toUpperCase(),
                      style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      deal.contactName,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 10),

            // Bottom Actions: Stage Pill & Move Forward Button
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: stageColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(stageIcon, size: 12, color: stageColor),
                      const SizedBox(width: 5),
                      Text(
                        deal.stage.toUpperCase(),
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: stageColor,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),

                if (deal.stage != 'won')
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: () async {
                        final stages = ['lead', 'contacted', 'proposal', 'negotiation', 'won'];
                        final currIdx = stages.indexOf(deal.stage.toLowerCase());
                        if (currIdx != -1 && currIdx < stages.length - 1) {
                          final nextStage = stages[currIdx + 1];
                          await provider.apiService.moveDealStage(deal.id, nextStage);
                          _loadCrmData();
                        }
                      },
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF4F46E5).withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Text(
                              'Advance Stage',
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: const Color(0xFF4F46E5),
                              ),
                            ),
                            const SizedBox(width: 4),
                            const Icon(Icons.arrow_forward_rounded, size: 12, color: Color(0xFF4F46E5)),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContactCard(CrmContact contact, bool isDark) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Monogram Avatar
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF059669), Color(0xFF10B981)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF10B981).withValues(alpha: 0.3),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Center(
              child: Text(
                contact.name.isNotEmpty ? contact.name[0].toUpperCase() : 'C',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
          ),
          const SizedBox(width: 14),

          // Contact Details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        contact.name,
                        style: GoogleFonts.outfit(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        contact.status,
                        style: const TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF059669),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  '${contact.jobTitle.isNotEmpty ? "${contact.jobTitle} · " : ""}${contact.companyName}',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  contact.email,
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    color: const Color(0xFF4F46E5),
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),

          // Action: 1-Click Send Email
          IconButton(
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFF4F46E5).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.mail_outline_rounded, color: Color(0xFF4F46E5), size: 18),
            ),
            tooltip: 'Send Email',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ComposeView(initialTo: contact.email),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildCompanyCard(CrmCompany company, bool isDark) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: const Color(0xFF7C3AED).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.domain_rounded, color: Color(0xFF7C3AED), size: 22),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  company.name,
                  style: GoogleFonts.outfit(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (company.domain.isNotEmpty)
                  Text(
                    company.domain,
                    style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF3B82F6)),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                Text(
                  '${company.industry} · ${company.size} employees',
                  style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          if (company.totalDealsVal > 0)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFECFDF5),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '₹${company.totalDealsVal.toStringAsFixed(0)}',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF059669),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildEmptyState({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required String primaryBtnLabel,
    required VoidCallback onPrimaryPressed,
    required bool isDark,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    iconColor.withValues(alpha: 0.15),
                    iconColor.withValues(alpha: 0.05),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                shape: BoxShape.circle,
                border: Border.all(color: iconColor.withValues(alpha: 0.2)),
              ),
              child: Center(
                child: Icon(icon, color: iconColor, size: 36),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              style: GoogleFonts.outfit(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF0F172A),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: GoogleFonts.inter(
                fontSize: 13,
                color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                height: 1.4,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: onPrimaryPressed,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF059669),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                elevation: 2,
              ),
              child: Text(
                primaryBtnLabel,
                style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
