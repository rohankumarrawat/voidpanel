import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'services/api_client.dart';
import 'services/auth_service.dart';
import 'theme/void_theme.dart';
import 'screens/login_screen.dart';
import 'screens/home_shell.dart';
import 'screens/database_screen.dart';
import 'screens/subdomain_screen.dart';
import 'screens/ssl_screen.dart';
import 'screens/cron_screen.dart';
import 'screens/backup_screen.dart';
import 'screens/dns_screen.dart';
import 'screens/activity_screen.dart';
import 'screens/server_config_screen.dart';

/// Override to handle SSL certificate verification in macOS sandbox.
/// The macOS app sandbox doesn't always have access to the full system
/// certificate store, causing CERTIFICATE_VERIFY_FAILED errors.
class VoidHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    return super.createHttpClient(context)
      ..badCertificateCallback = (X509Certificate cert, String host, int port) => true;
  }
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  HttpOverrides.global = VoidHttpOverrides();
  runApp(const VoidApp());
}

class VoidApp extends StatefulWidget {
  const VoidApp({super.key});

  @override
  State<VoidApp> createState() => _VoidAppState();
}

class _VoidAppState extends State<VoidApp> {
  String? _serverUrl;
  bool _checkingConfig = true;

  @override
  void initState() {
    super.initState();
    _loadServerUrl();
  }

  Future<void> _loadServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    var url = prefs.getString('server_url');
    // One-time migration: clear URL if it doesn't have the correct port
    if (url != null && !url.contains(':8082')) {
      await prefs.remove('server_url');
      url = null;
    }
    setState(() {
      _serverUrl = url;
      _checkingConfig = false;
    });
  }

  void _onServerConfigured(String url) {
    setState(() {
      _serverUrl = url;
    });
  }

  @override
  Widget build(BuildContext context) {
    // Show loading while checking config
    if (_checkingConfig) {
      return MaterialApp(
        theme: VoidTheme.darkTheme,
        debugShowCheckedModeBanner: false,
        home: const Scaffold(
          body: Center(
            child: CircularProgressIndicator(color: VoidTheme.accentPrimary),
          ),
        ),
      );
    }

    // Show server config if no URL saved
    if (_serverUrl == null || _serverUrl!.isEmpty) {
      return MaterialApp(
        title: 'VoidApp',
        theme: VoidTheme.darkTheme,
        debugShowCheckedModeBanner: false,
        home: ServerConfigScreen(onConfigured: _onServerConfigured),
      );
    }

    // Main app with providers
    final apiClient = ApiClient(baseUrl: '$_serverUrl/api/v1');
    final authService = AuthService(api: apiClient);

    return MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: apiClient),
        ChangeNotifierProvider<AuthService>.value(value: authService),
      ],
      child: MaterialApp(
        title: 'VoidApp',
        theme: VoidTheme.darkTheme,
        debugShowCheckedModeBanner: false,
        home: _AuthGate(authService: authService),
        routes: {
          '/login': (_) => const LoginScreen(),
          '/home': (_) => const HomeShell(),
          '/databases': (_) => const DatabaseScreen(),
          '/subdomains': (_) => const SubdomainScreen(),
          '/ssl': (_) => const SslScreen(),
          '/cron': (_) => const CronScreen(),
          '/backup': (_) => const BackupScreen(),
          '/dns': (_) => const DnsScreen(),
          '/activity': (_) => const ActivityScreen(),
        },
      ),
    );
  }
}

/// Checks auth state on startup and routes accordingly.
class _AuthGate extends StatefulWidget {
  final AuthService authService;
  const _AuthGate({required this.authService});

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  bool _checking = true;

  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    await widget.authService.checkAuth();
    if (mounted) {
      setState(() => _checking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(color: VoidTheme.accentPrimary),
              SizedBox(height: 20),
              Text(
                'Connecting...',
                style: TextStyle(color: VoidTheme.textMuted, fontSize: 14),
              ),
            ],
          ),
        ),
      );
    }

    return widget.authService.isLoggedIn
        ? const HomeShell()
        : const LoginScreen();
  }
}
