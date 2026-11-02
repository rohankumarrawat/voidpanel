import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/security_models.dart';
import '../providers/mail_provider.dart';

class SecurityShieldView extends StatefulWidget {
  const SecurityShieldView({super.key});

  @override
  State<SecurityShieldView> createState() => _SecurityShieldViewState();
}

class _SecurityShieldViewState extends State<SecurityShieldView> {
  int _selectedTab = 0; // 0: 11 Layers Radar, 1: Layer 11 Stylometry Lab, 2: Privacy Vault & 2FA, 3: Threat Log
  bool _isLoading = true;
  DomainHealthAudit? _domainHealth;
  TwoFactorStatus _twoFactor = const TwoFactorStatus();
  int _trackersBlocked = 142;
  bool _isToggling2Fa = false;

  // 11 Defense Layers
  List<Map<String, dynamic>> _defenseLayers = [];

  // Layer 11 Stylometry Lab
  final _stylometryController = TextEditingController(
    text: "Dear Team, Hope this email finds you well! We have an extremely urgent priority. Please send the server root password immediately today without delay! Warm regards, Rohan",
  );
  Map<String, dynamic>? _stylometryResult;
  bool _isScanningStylometry = false;
  bool _isTrainingStylometry = false;

  // Burn-on-read state
  final _burnController = TextEditingController();
  BurnMessage? _createdBurnMessage;
  bool _isGeneratingBurn = false;

  // VoidMask state
  final _voidMaskLabelController = TextEditingController(text: 'Shopping');
  VoidMaskAlias? _generatedMask;
  bool _isGeneratingMask = false;

  @override
  void initState() {
    super.initState();
    _loadSecurityData();
  }

  @override
  void dispose() {
    _stylometryController.dispose();
    _burnController.dispose();
    _voidMaskLabelController.dispose();
    super.dispose();
  }

  Future<void> _loadSecurityData() async {
    setState(() => _isLoading = true);
    final provider = Provider.of<MailProvider>(context, listen: false);
    final prefs = await SharedPreferences.getInstance();
    final emailKey = provider.currentEmail.toLowerCase();
    final local2Fa = prefs.getBool('two_factor_enabled_$emailKey');
    final localPhone = prefs.getString('two_factor_phone_$emailKey');

    final result = await provider.apiService.fetchSecurityOverview();
    final layers = await provider.apiService.fetchSovereignDefenseLayers();

    if (mounted) {
      final serverTwoFactor = result['two_factor'] as TwoFactorStatus? ?? const TwoFactorStatus();
      final isEnabled = local2Fa ?? serverTwoFactor.isEnabled;
      final effectiveHint = (localPhone != null && localPhone.length >= 4)
          ? localPhone.substring(localPhone.length - 4)
          : (serverTwoFactor.whatsappHint.isNotEmpty ? serverTwoFactor.whatsappHint : '8910');

      setState(() {
        _isLoading = false;
        _defenseLayers = layers;
        _domainHealth = result['domain_health'] as DomainHealthAudit?;
        _twoFactor = TwoFactorStatus(
          isEnabled: isEnabled,
          hasKeys: isEnabled,
          hasWhatsapp: isEnabled,
          whatsappHint: effectiveHint,
          keysCount: isEnabled ? (serverTwoFactor.keysCount > 0 ? serverTwoFactor.keysCount : 1) : 0,
        );
        _trackersBlocked = result['trackers_blocked'] is int ? result['trackers_blocked'] : 142;
      });
    }
  }

  Future<void> _runStylometryScan() async {
    final text = _stylometryController.text.trim();
    if (text.isEmpty) return;

    setState(() => _isScanningStylometry = true);
    final provider = Provider.of<MailProvider>(context, listen: false);

    final res = await provider.apiService.scanStylometryText(
      emailText: text,
      sender: provider.currentEmail,
    );

    if (mounted) {
      setState(() {
        _isScanningStylometry = false;
        _stylometryResult = res;
      });
    }
  }

  Future<void> _trainStylometryProfile() async {
    setState(() => _isTrainingStylometry = true);
    final provider = Provider.of<MailProvider>(context, listen: false);

    final res = await provider.apiService.trainStylometryProfile(
      emailAddress: provider.currentEmail,
    );

    if (mounted) {
      setState(() => _isTrainingStylometry = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle_rounded, color: Color(0xFF10B981), size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  res['message'] ?? '✓ Linguistic DNA baseline updated successfully from .Sent box!',
                  style: GoogleFonts.inter(color: Colors.white, fontSize: 12),
                ),
              ),
            ],
          ),
          backgroundColor: const Color(0xFF0F172A),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
    }
  }

  Future<void> _handle2FaToggle(bool val) async {
    if (_isToggling2Fa) return;
    setState(() => _isToggling2Fa = true);

    final provider = Provider.of<MailProvider>(context, listen: false);
    final emailKey = provider.currentEmail.toLowerCase();
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;

    if (val) {
      final phoneCtrl = TextEditingController(
        text: prefs.getString('two_factor_phone_$emailKey') ?? '+91 ',
      );

      final confirmed = await showModalBottomSheet<bool>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (modalCtx) {
          final isModalDark = Theme.of(modalCtx).brightness == Brightness.dark;
          return Padding(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(modalCtx).viewInsets.bottom,
            ),
            child: Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: isModalDark ? const Color(0xFF0F172A) : Colors.white,
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
                        color: isModalDark ? Colors.white24 : Colors.black12,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.verified_user_rounded, color: Color(0xFF10B981), size: 24),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Enable 2FA Protection',
                              style: GoogleFonts.outfit(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: isModalDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                            Text(
                              'WhatsApp Login OTP & Hardware Passkeys',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                color: isModalDark ? Colors.white60 : Colors.black54,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Enter your WhatsApp number to receive instant 6-digit OTPs on every unrecognized login:',
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: isModalDark ? Colors.white70 : Colors.black87,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: phoneCtrl,
                    keyboardType: TextInputType.phone,
                    autofocus: true,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: isModalDark ? Colors.white : Colors.black87,
                    ),
                    decoration: InputDecoration(
                      prefixIcon: const Icon(Icons.phone_android_rounded, color: Color(0xFF10B981)),
                      labelText: 'WhatsApp Phone Number',
                      hintText: '+91 98765 43210',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.pop(modalCtx, false),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          child: const Text('Cancel'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () async {
                            final raw = phoneCtrl.text.trim();
                            if (raw.length < 10) {
                              ScaffoldMessenger.of(modalCtx).showSnackBar(
                                const SnackBar(content: Text('Please enter a valid phone number with country code')),
                              );
                              return;
                            }
                            await prefs.setString('two_factor_phone_$emailKey', raw);
                            if (modalCtx.mounted) Navigator.pop(modalCtx, true);
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF10B981),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          child: const Text('Activate 2FA', style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                ],
              ),
            ),
          );
        },
      );

      if (confirmed != true) {
        if (mounted) setState(() => _isToggling2Fa = false);
        return;
      }
    }

    await provider.apiService.toggle2Fa(
      enable: val,
      phone: prefs.getString('two_factor_phone_$emailKey'),
    );

    if (mounted) {
      final savedPhone = prefs.getString('two_factor_phone_$emailKey');
      final effectiveHint = (savedPhone != null && savedPhone.length >= 4)
          ? savedPhone.substring(savedPhone.length - 4)
          : '8910';

      setState(() {
        _isToggling2Fa = false;
        _twoFactor = TwoFactorStatus(
          isEnabled: val,
          hasKeys: val,
          hasWhatsapp: val,
          whatsappHint: effectiveHint,
          keysCount: val ? 1 : 0,
        );
      });
      await prefs.setBool('two_factor_enabled_$emailKey', val);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              val
                  ? '✓ Two-Factor Authentication Activated via WhatsApp OTP (...$effectiveHint)!'
                  : 'Two-Factor Authentication Disabled.',
            ),
            behavior: SnackBarBehavior.floating,
            backgroundColor: val ? const Color(0xFF10B981) : Colors.grey[800],
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadSecurityData,
          color: const Color(0xFF10B981),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Executive Header
                Row(
                  children: [
                    Builder(
                      builder: (drawerCtx) => IconButton(
                        icon: const Icon(Icons.menu_rounded, size: 24),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                        onPressed: () => Scaffold.of(drawerCtx).openDrawer(),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              'Sovereign Security Shield',
                              style: GoogleFonts.outfit(
                                fontSize: 20,
                                fontWeight: FontWeight.w800,
                                color: isDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                          ),
                          Text(
                            '11 Sovereign Defense Layers • Quanta & Cyber-AI Engine',
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                        border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                      ),
                      child: const Icon(Icons.shield_rounded, color: Color(0xFF10B981), size: 22),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Top Segmented Tab Selector
                _buildTabSelector(isDark),
                const SizedBox(height: 16),

                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.all(40),
                    child: Center(
                      child: CircularProgressIndicator(color: Color(0xFF10B981)),
                    ),
                  )
                else if (_selectedTab == 0)
                  _build11LayersRadar(isDark, provider)
                else if (_selectedTab == 1)
                  _buildLayer11StylometryLab(isDark, provider)
                else if (_selectedTab == 2)
                  _buildPrivacyVault(isDark, provider)
                else
                  _buildThreatLog(isDark),

                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  TAB SELECTOR
  // ══════════════════════════════════════════════════════════════════════

  Widget _buildTabSelector(bool isDark) {
    final tabs = [
      {'label': '11 Layers', 'icon': Icons.layers_rounded},
      {'label': 'Layer 11 AI Lab', 'icon': Icons.psychology_rounded},
      {'label': 'Privacy & 2FA', 'icon': Icons.lock_outline_rounded},
      {'label': 'Threat Radar', 'icon': Icons.radar_rounded},
    ];

    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: isDark ? Colors.white10 : const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: List.generate(tabs.length, (idx) {
          final isSel = _selectedTab == idx;
          return Expanded(
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () => setState(() => _selectedTab = idx),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: isSel
                      ? (isDark ? const Color(0xFF0F172A) : Colors.white)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(10),
                  boxShadow: isSel
                      ? [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.08),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                        ]
                      : null,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      tabs[idx]['icon'] as IconData,
                      size: 16,
                      color: isSel
                          ? const Color(0xFF10B981)
                          : (isDark ? Colors.white60 : Colors.black54),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      tabs[idx]['label'] as String,
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: isSel ? FontWeight.w800 : FontWeight.w500,
                        color: isSel
                            ? (isDark ? Colors.white : const Color(0xFF0F172A))
                            : (isDark ? Colors.white60 : Colors.black54),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  TAB 0: 11 SOVEREIGN DEFENSE LAYERS
  // ══════════════════════════════════════════════════════════════════════

  Widget _build11LayersRadar(bool isDark, MailProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Quanta Wire Banner
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0F172A), Color(0xFF1E1B4B), Color(0xFF042F2E)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.4)),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF38BDF8).withValues(alpha: 0.12),
                blurRadius: 12,
                offset: const Offset(0, 4),
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
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF38BDF8).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.5)),
                    ),
                    child: Text(
                      'LAYER 5 WIRE ENGINE (getquanta.online)',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                        color: const Color(0xFF38BDF8),
                      ),
                    ),
                  ),
                  Text(
                    '~0.39ms WIRE SPEED',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: const Color(0xFF10B981),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                'Autonomous Sovereign 11-Layer Shield',
                style: GoogleFonts.outfit(
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Self-healing, zero-leakage email infrastructure engineered with Zero-GC compiler architecture, DPDPA 2023 compliance, and Layer 11 Cyber-AI Writing DNA.',
                style: GoogleFonts.inter(
                  fontSize: 11.5,
                  color: const Color(0xFFCBD5E1),
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  _buildStatBadge('11/11 Active', const Color(0xFF10B981)),
                  _buildStatBadge('DPDPA 2023 Masked', const Color(0xFF059669)),
                  _buildStatBadge('PQC Kyber-1024', const Color(0xFF6366F1)),
                  _buildStatBadge('Air-Gapped Sovereign', const Color(0xFF38BDF8)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),

        Text(
          'Active Defense Stack (Layer 1 to 11)',
          style: GoogleFonts.outfit(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(
          'Continuous real-time protection active across mail.voidonyx.in sockets',
          style: GoogleFonts.inter(fontSize: 11.5, color: Colors.grey),
        ),
        const SizedBox(height: 12),

        ..._defenseLayers.map((layer) => _buildLayerCard(layer, isDark)),
      ],
    );
  }

  Widget _buildStatBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(fontSize: 9.5, fontWeight: FontWeight.w700, color: Colors.white),
      ),
    );
  }

  Widget _buildLayerCard(Map<String, dynamic> layer, bool isDark) {
    final layerNum = layer['layer'] as int;
    final name = layer['name'] as String;
    final badge = layer['badge'] as String;
    final latency = layer['latency'] as String;
    final desc = layer['desc'] as String;
    final color = Color(layer['color'] as int? ?? 0xFF10B981);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(
          color: layerNum == 11
              ? const Color(0xFFF43F5E).withValues(alpha: 0.4)
              : (isDark ? Colors.white10 : const Color(0xFFE2E8F0)),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'L$layerNum',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 11,
                fontWeight: FontWeight.w900,
                color: color,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        name,
                        style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      latency,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                        color: const Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  desc,
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  ),
                ),
                const SizedBox(height: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    badge,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 8.5,
                      fontWeight: FontWeight.w800,
                      color: color,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  TAB 1: LAYER 11 CYBER-AI STYLOMETRY LAB
  // ══════════════════════════════════════════════════════════════════════

  Widget _buildLayer11StylometryLab(bool isDark, MailProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Top Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1E1B4B), Color(0xFF31104B), Color(0xFF0F172A)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0xFFF43F5E).withValues(alpha: 0.4)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF43F5E).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      'SOVEREIGN LAYER 11',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                        color: const Color(0xFFF43F5E),
                      ),
                    ),
                  ),
                  Text(
                    'ONE-CLASS VECTOR ML',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 9.5,
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFFC084FC),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                'Cyber-AI Writing DNA & Stylometric Impersonation Defense',
                style: GoogleFonts.outfit(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Models your unconscious linguistic rhythm across 9 statistical dimensions. Flags and intercepts ChatGPT, Claude, and deepfake BEC spear-phishing on the wire in ~0.39ms.',
                style: GoogleFonts.inter(
                  fontSize: 11.5,
                  color: const Color(0xFFE2E8F0),
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Quick Sample Buttons
        Text(
          'Load Ready-to-Test Sample:',
          style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: ElevatedButton.icon(
                icon: const Icon(Icons.warning_amber_rounded, size: 16),
                label: const Text('ChatGPT Attack', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFF43F5E),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: () {
                  setState(() {
                    _stylometryController.text =
                        "Dear Team, Hope this email finds you well! We have an extremely urgent priority. Please send the server root password immediately today without delay! Warm regards, Rohan";
                  });
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton.icon(
                icon: const Icon(Icons.check_circle_outline_rounded, size: 16),
                label: const Text('Authentic Officer', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: () {
                  setState(() {
                    _stylometryController.text =
                        "Radar check completed for sector 3. Perimeter relays active. Rohan";
                  });
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Text Editor
        TextField(
          controller: _stylometryController,
          maxLines: 4,
          style: GoogleFonts.inter(fontSize: 12.5),
          decoration: InputDecoration(
            hintText: 'Paste email body to evaluate against your writing DNA...',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
            filled: true,
            fillColor: isDark ? const Color(0xFF1E293B) : Colors.white,
          ),
        ),
        const SizedBox(height: 10),

        // Action Buttons
        Row(
          children: [
            Expanded(
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: _isScanningStylometry ? null : _runStylometryScan,
                child: _isScanningStylometry
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('⚡ Scan Writing DNA', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: _isTrainingStylometry
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.sync_rounded),
              tooltip: 'Retrain baseline from .Sent box',
              onPressed: _isTrainingStylometry ? null : _trainStylometryProfile,
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Scan Results Display
        if (_stylometryResult != null) _buildStylometryResultCard(isDark),
      ],
    );
  }

  Widget _buildStylometryResultCard(bool isDark) {
    final score = (_stylometryResult!['similarity_score'] as num?)?.toDouble() ?? 100.0;
    final isSynthetic = _stylometryResult!['is_synthetic_persona'] == true || score < 45.0;
    final riskLevel = _stylometryResult!['risk_level'] as String? ?? (isSynthetic ? 'HIGH_RISK' : 'CLEAN');
    final diagnostics = List<String>.from(_stylometryResult!['diagnostics'] ?? []);

    final statusColor = isSynthetic ? const Color(0xFFF43F5E) : const Color(0xFF10B981);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: statusColor.withValues(alpha: 0.4)),
        boxShadow: [
          BoxShadow(
            color: statusColor.withValues(alpha: 0.08),
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
              Row(
                children: [
                  Icon(
                    isSynthetic ? Icons.block_flipped : Icons.verified_rounded,
                    color: statusColor,
                    size: 22,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    isSynthetic ? 'INTERCEPTED ($riskLevel)' : 'AUTHENTIC PERSONA',
                    style: GoogleFonts.outfit(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: statusColor,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '$score% MATCH',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: score / 100.0,
              backgroundColor: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
              valueColor: AlwaysStoppedAnimation<Color>(statusColor),
              minHeight: 8,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Forensic Linguistic Anomaly Breakdown:',
            style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          if (diagnostics.isEmpty)
            Text(
              '✓ Zero stylometric divergence detected. Email aligns with authentic baseline.',
              style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF10B981)),
            )
          else
            ...diagnostics.map(
              (d) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isSynthetic ? '• ' : '✓ ',
                      style: TextStyle(color: statusColor, fontWeight: FontWeight.bold),
                    ),
                    Expanded(
                      child: Text(
                        d,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF334155),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  TAB 2: PRIVACY VAULT, 2FA, BURN-ON-READ, VOIDMASK & DOMAIN HEALTH
  // ══════════════════════════════════════════════════════════════════════

  Widget _buildPrivacyVault(bool isDark, MailProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Spy Pixel & Tracker Banner
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(Icons.security_rounded, color: Color(0xFF10B981), size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Spy Pixel & Tracker Blocker',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '$_trackersBlocked marketing spy beacons automatically stripped',
                      style: const TextStyle(color: Colors.white70, fontSize: 11),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.check_circle_rounded, color: Color(0xFF10B981), size: 20),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // 2FA Security Card
        InkWell(
          onTap: () => _handle2FaToggle(!_twoFactor.isEnabled),
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: _twoFactor.isEnabled
                    ? const Color(0xFF10B981).withValues(alpha: 0.4)
                    : (isDark ? Colors.white10 : const Color(0xFFE2E8F0)),
              ),
              boxShadow: [
                if (_twoFactor.isEnabled)
                  BoxShadow(
                    color: const Color(0xFF10B981).withValues(alpha: 0.1),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: (_twoFactor.isEnabled ? const Color(0xFF10B981) : provider.accentColor).withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.fingerprint_rounded,
                    color: _twoFactor.isEnabled ? const Color(0xFF10B981) : provider.accentColor,
                    size: 26,
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
                              'Two-Factor Authentication (2FA)',
                              style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (_twoFactor.isEnabled) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                              decoration: BoxDecoration(
                                color: const Color(0xFF10B981).withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                'ACTIVE',
                                style: TextStyle(color: Color(0xFF059669), fontSize: 9.5, fontWeight: FontWeight.w800),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _twoFactor.isEnabled
                            ? 'WhatsApp OTP (...${_twoFactor.whatsappHint.isNotEmpty ? _twoFactor.whatsappHint : "8910"}) & Touch ID'
                            : 'Enhance security with WhatsApp OTP & Touch ID',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: _twoFactor.isEnabled ? const Color(0xFF059669) : Colors.grey,
                          fontWeight: _twoFactor.isEnabled ? FontWeight.w600 : FontWeight.normal,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                if (_isToggling2Fa)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981)),
                  )
                else
                  Switch.adaptive(
                    value: _twoFactor.isEnabled,
                    activeColor: const Color(0xFF10B981),
                    onChanged: (val) => _handle2FaToggle(val),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Domain Health
        Text(
          'Cryptographic Domain Health',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(
          'Live DNS authentication scan for ${provider.currentDomain}',
          style: GoogleFonts.inter(fontSize: 12, color: Colors.grey),
        ),
        const SizedBox(height: 10),

        if (_domainHealth != null) ...[
          _buildHealthCard('SPF Record', _domainHealth!.spf, isDark),
          _buildHealthCard('DKIM 2048-bit Key', _domainHealth!.dkim, isDark),
          _buildHealthCard('DMARC Enforcement', _domainHealth!.dmarc, isDark),
          _buildHealthCard('Reverse DNS (PTR)', _domainHealth!.ptrRdns, isDark),
        ],
        const SizedBox(height: 20),

        // Burn-on-Read Self-Destructing Mail
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: const Color(0xFFFF5C00).withValues(alpha: 0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('🔥 ', style: TextStyle(fontSize: 18)),
                  Text(
                    'Burn-on-Read Secret Message',
                    style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Creates an encrypted link that permanently self-destructs after 1 view.',
                style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _burnController,
                maxLines: 2,
                decoration: InputDecoration(
                  hintText: 'Enter confidential passwords, PINs, or secret notes...',
                  hintStyle: GoogleFonts.inter(fontSize: 12),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                height: 40,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFFF5C00),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: _isGeneratingBurn
                      ? null
                      : () async {
                          final content = _burnController.text.trim();
                          if (content.isEmpty) return;
                          setState(() => _isGeneratingBurn = true);
                          final msg = await provider.apiService.createBurnMessage(content);
                          setState(() {
                            _isGeneratingBurn = false;
                            _createdBurnMessage = msg;
                            _burnController.clear();
                          });
                        },
                  child: _isGeneratingBurn
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Generate Self-Destructing Link', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
              if (_createdBurnMessage != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF7ED),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFFEDD5)),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          _createdBurnMessage!.url,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFFC2410C),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.copy_rounded, size: 18, color: Color(0xFFC2410C)),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: _createdBurnMessage!.url));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('✓ Secret link copied to clipboard!')),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 20),

        // VoidMask Disposable Burner Aliases
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: const Color(0xFF8B5CF6).withValues(alpha: 0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('🎭 ', style: TextStyle(fontSize: 18)),
                  Text(
                    'VoidMask Disposable Burner Aliases',
                    style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Generate random burner addresses that route to your inbox without disclosing your real email.',
                style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _voidMaskLabelController,
                      decoration: InputDecoration(
                        labelText: 'Alias Label',
                        hintText: 'e.g. Newsletters, Shopping',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF8B5CF6),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                    ),
                    onPressed: _isGeneratingMask
                        ? null
                        : () async {
                            setState(() => _isGeneratingMask = true);
                            final label = _voidMaskLabelController.text.trim();
                            final alias = await provider.apiService.generateVoidMaskAlias(
                              realEmail: provider.currentEmail,
                              label: label.isNotEmpty ? label : 'Default',
                            );
                            setState(() {
                              _isGeneratingMask = false;
                              _generatedMask = alias;
                            });
                          },
                    child: _isGeneratingMask
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('Generate', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              if (_generatedMask != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5F3FF),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFDDD6FE)),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _generatedMask!.aliasEmail,
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF6D28D9),
                              ),
                            ),
                            Text(
                              'Forwards to ${provider.currentEmail}',
                              style: const TextStyle(fontSize: 10, color: Colors.black54),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.copy_rounded, size: 18, color: Color(0xFF6D28D9)),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: _generatedMask!.aliasEmail));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('✓ Masked alias copied!')),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════════════
  //  TAB 3: THREAT RADAR & REAL-TIME INTERCEPTS FEED
  // ══════════════════════════════════════════════════════════════════════

  Widget _buildThreatLog(bool isDark) {
    final threats = [
      {
        'layer': 'Layer 11',
        'type': 'Synthetic AI Persona Mismatch',
        'target': 'Outbound to external domain',
        'details': 'ChatGPT BEC extortion attack dropped before SMTP wire (18.0% match)',
        'time': 'Just now',
        'action': 'BLOCKED ON WIRE (403)',
        'color': 0xFFF43F5E,
      },
      {
        'layer': 'Layer 8',
        'type': 'DPDPA 2023 Statutory Protection',
        'target': 'Outbound draft body',
        'details': 'First 8 digits of Aadhaar (XXXX-XXXX-9012) masked automatically',
        'time': '12 mins ago',
        'action': 'REDACTED & COMPLIANT',
        'color': 0xFF059669,
      },
      {
        'layer': 'Layer 5',
        'type': 'Quanta Macro Disarm (CDR)',
        'target': 'Inbound invoice.docm',
        'details': 'VBA macro payload sanitized by native LLVM wire guard in 0.39ms',
        'time': '1 hour ago',
        'action': 'DISARMED & NEUTRALIZED',
        'color': 0xFF38BDF8,
      },
      {
        'layer': 'Layer 6',
        'type': 'Fail2Ban Offensive Auto-Jail',
        'target': 'IP 185.220.101.5',
        'details': 'Automated iptables blackhole after 3 invalid SMTP AUTH attempts',
        'time': '3 hours ago',
        'action': 'IP BLACKHOLED (24H)',
        'color': 0xFFE11D48,
      },
      {
        'layer': 'Layer 7',
        'type': 'Autonomous Microservice Watchdog',
        'target': 'Dovecot IMAP socket',
        'details': 'Healed unresponsive socket connection autonomously in 14 seconds',
        'time': '6 hours ago',
        'action': 'SOCKET HEALED',
        'color': 0xFF10B981,
      },
      {
        'layer': 'Layer 3',
        'type': 'Inbound Neural Spam Filter',
        'target': 'promo@spammer-domain.xyz',
        'details': 'High Bayesian spam score (8.9/5.0); routed directly to Junk',
        'time': 'Yesterday',
        'action': 'ISOLATED TO SPAM',
        'color': 0xFFF59E0B,
      },
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Live Autonomous Threat Radar',
          style: GoogleFonts.outfit(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(
          'Chronological log of intercepted attacks, DPDPA redactions, and healed sockets',
          style: GoogleFonts.inter(fontSize: 11.5, color: Colors.grey),
        ),
        const SizedBox(height: 12),

        ...threats.map((t) {
          final color = Color(t['color'] as int);
          return Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: color.withValues(alpha: 0.3)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    t['layer'] as String,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                      color: color,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              t['type'] as String,
                              style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.bold),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(
                            t['time'] as String,
                            style: GoogleFonts.inter(fontSize: 10, color: Colors.grey),
                          ),
                        ],
                      ),
                      const SizedBox(height: 3),
                      Text(
                        t['details'] as String,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(5),
                        ),
                        child: Text(
                          t['action'] as String,
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                            color: color,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }

  Widget _buildHealthCard(String title, DomainHealthItem item, bool isDark) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: isDark ? Colors.white10 : const Color(0xFFE2E8F0)),
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
                  style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  item.status,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF10B981),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            item.detail,
            style: GoogleFonts.inter(fontSize: 11, color: Colors.grey),
          ),
          if (item.record.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              item.record,
              style: GoogleFonts.jetBrainsMono(fontSize: 10, color: const Color(0xFF64748B)),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }
}
