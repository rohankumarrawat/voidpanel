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
    if (await api.isAuthenticated) {
      final res = await api.get('/auth/me/');
      if (res.success) {
        _user = res.data;
        _isLoggedIn = true;
        notifyListeners();
      } else {
        await api.clearToken();
      }
    }
  }

  /// Login with username and password
  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    final res = await api.post('/auth/login/', body: {
      'username': username,
      'password': password,
    });

    _isLoading = false;

    if (res.success) {
      await api.setToken(res.data['token']);
      _user = {
        'username': res.data['username'],
        'domain': res.data['domain'],
        'is_admin': res.data['is_admin'],
      };
      _isLoggedIn = true;

      // Fetch full profile
      final meRes = await api.get('/auth/me/');
      if (meRes.success) {
        _user = meRes.data;
      }
    } else {
      _error = res.error ?? 'Login failed';
    }

    notifyListeners();
    return res.success;
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
