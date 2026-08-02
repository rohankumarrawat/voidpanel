import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/void_theme.dart';

/// First-run screen to configure the VoidPanel server URL.
class ServerConfigScreen extends StatefulWidget {
  final void Function(String url) onConfigured;

  const ServerConfigScreen({super.key, required this.onConfigured});

  @override
  State<ServerConfigScreen> createState() => _ServerConfigScreenState();
}

class _ServerConfigScreenState extends State<ServerConfigScreen>
    with SingleTickerProviderStateMixin {
  final _urlController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _testing = false;
  String? _error;

  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    _fadeCtrl.forward();
  }

  @override
  void dispose() {
    _urlController.dispose();
    _fadeCtrl.dispose();
    super.dispose();
  }

  Future<void> _connect() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _testing = true;
      _error = null;
    });

    String url = _urlController.text.trim();

    // Normalize URL
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://$url';
    }
    if (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }

    // Save and proceed (we'll validate on login)
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('server_url', url);
      widget.onConfigured(url);
    } catch (e) {
      setState(() {
        _testing = false;
        _error = 'Failed to save: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: VoidTheme.backgroundGradient),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: FadeTransition(
                opacity: _fadeAnim,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Icon
                    Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        gradient: VoidTheme.primaryGradient,
                        borderRadius: BorderRadius.circular(22),
                        boxShadow: VoidTheme.glowShadow(VoidTheme.accentPrimary),
                      ),
                      child: const Icon(
                        Icons.dns_rounded,
                        size: 38,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 24),

                    Text(
                      'Connect to Server',
                      style: Theme.of(context).textTheme.headlineLarge,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Enter your VoidPanel server URL to get started',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 14, color: VoidTheme.textMuted),
                    ),
                    const SizedBox(height: 36),

                    // Form
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: VoidTheme.glassCard,
                      child: Form(
                        key: _formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (_error != null) ...[
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: VoidTheme.accentDanger.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(
                                      color: VoidTheme.accentDanger.withValues(alpha: 0.3)),
                                ),
                                child: Text(
                                  _error!,
                                  style: const TextStyle(
                                      fontSize: 13, color: VoidTheme.accentDanger),
                                ),
                              ),
                              const SizedBox(height: 16),
                            ],

                            TextFormField(
                              controller: _urlController,
                              style: const TextStyle(color: VoidTheme.textPrimary),
                              decoration: const InputDecoration(
                                labelText: 'Server URL',
                                hintText: 'panel.yourdomain.com:8082',
                                prefixIcon: Icon(Icons.link_rounded,
                                    size: 20, color: VoidTheme.textMuted),
                              ),
                              keyboardType: TextInputType.url,
                              validator: (v) {
                                if (v == null || v.trim().isEmpty) {
                                  return 'Server URL is required';
                                }
                                return null;
                              },
                              onFieldSubmitted: (_) => _connect(),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Example: https://fast.voidpanel.com:8082',
                              style: TextStyle(fontSize: 12, color: VoidTheme.textDisabled),
                            ),
                            const SizedBox(height: 24),

                            SizedBox(
                              height: 50,
                              child: ElevatedButton(
                                onPressed: _testing ? null : _connect,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: VoidTheme.accentPrimary,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                child: _testing
                                    ? const SizedBox(
                                        width: 22,
                                        height: 22,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2.5,
                                          color: Colors.white,
                                        ),
                                      )
                                    : const Text(
                                        'Connect',
                                        style: TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: 30),
                    const Text(
                      'VoidApp connects to your self-hosted VoidPanel',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 12, color: VoidTheme.textDisabled),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
