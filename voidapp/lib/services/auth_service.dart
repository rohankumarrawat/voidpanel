import 'package:flutter/material.dart';
import 'api_client.dart';

/// Authentication service that manages login state and user profile.
class AuthService extends ChangeNotifier {
  final ApiClient api;

  bool _isLoading = false;
  bool _isLoggedIn = false;
  Map<String, dynamic>? _user;
  String? _error;

  AuthService({required this.api});

  bool get isLoading => _isLoading;
  bool get isLoggedIn => _isLoggedIn;
  Map<String, dynamic>? get user => _user;
  String? get error => _error;
  String get username => _user?['username'] ?? '';
  String get domain => _user?['domain'] ?? '';
  String get hostingPackage => _user?['hosting_package'] ?? '';

  /// Check if already authenticated on app start
  Future<void> checkAuth() async {
    try {
      if (await api.isAuthenticated) {
        final res = await api.get('/auth/me/');
        if (res.success && res.data is Map) {
          _user = Map<String, dynamic>.from(res.data);
          _isLoggedIn = true;
          notifyListeners();
        } else if (res.statusCode == 401) {
          await api.clearToken();
        }
      }
    } catch (_) {
      // Ignore network errors on startup check
    }
  }

  /// Login with username and password
  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final res = await api.post('/auth/login/', body: {
        'username': username,
        'password': password,
      });

      _isLoading = false;

      if (res.success && res.data is Map) {
        final data = Map<String, dynamic>.from(res.data);
        final token = data['token'];
        if (token != null) {
          await api.setToken(token.toString());
        }
        _user = {
          'username': data['username'] ?? username,
          'domain': data['domain'] ?? '',
          'is_admin': data['is_admin'] ?? false,
        };
        _isLoggedIn = true;

        // Fetch full profile
        try {
          final meRes = await api.get('/auth/me/');
          if (meRes.success && meRes.data is Map) {
            _user = Map<String, dynamic>.from(meRes.data);
          }
        } catch (_) {}
      } else {
        _error = res.error ?? 'Login failed';
      }
    } catch (e) {
      _isLoading = false;
      _error = 'Connection error: $e';
    }

    notifyListeners();
    return _isLoggedIn;
  }

  /// Logout
  Future<void> logout() async {
    await api.post('/auth/logout/');
    await api.clearToken();
    _isLoggedIn = false;
    _user = null;
    notifyListeners();
  }
}
