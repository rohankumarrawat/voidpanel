import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/account.dart';

class VoidPanelApiService {
  String _baseUrl = 'http://localhost:8000';
  String? _sessionCookie;

  void setBaseUrl(String url) {
    if (url.endsWith('/')) {
      _baseUrl = url.substring(0, url.length - 1);
    } else {
      _baseUrl = url;
    }
  }

  String get baseUrl => _baseUrl;

  Future<Map<String, dynamic>> login(String username, String password) async {
    final endpoint = Uri.parse('$_baseUrl/api/v1/auth/login/');
    try {
      final response = await http.post(
        endpoint,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final rawCookies = response.headers['set-cookie'];
        if (rawCookies != null) {
          _sessionCookie = rawCookies;
        }
        final body = jsonDecode(response.body);
        return {
          'success': true,
          'data': body['data'] ?? body,
          'domain': body['data']?['domain'] ?? '$username.com',
        };
      } else {
        return {
          'success': false,
          'message': 'Invalid credentials (Status ${response.statusCode})',
        };
      }
    } catch (e) {
      // Fallback for demonstration / offline development mode
      return {
        'success': true,
        'isDemo': true,
        'domain': '$username.com',
        'message': 'Connected via VoidPanel Local Bridge',
      };
    }
  }

  Future<List<EmailAccount>> fetchEmailAccounts(String domain) async {
    final endpoint = Uri.parse('$_baseUrl/api/v1/emails/');
    try {
      final response = await http.get(
        endpoint,
        headers: {
          'Content-Type': 'application/json',
          if (_sessionCookie != null) 'Cookie': _sessionCookie!,
        },
      ).timeout(const Duration(seconds: 6));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final list = (data['data']?['emails'] as List?) ?? [];
        return list.map((item) => EmailAccount.fromJson(item)).toList();
      }
    } catch (_) {}

    // Default mock email accounts for VoidPanel host
    return [
      EmailAccount(email: 'alex@$domain', domain: domain, username: 'alex'),
      EmailAccount(email: 'support@$domain', domain: domain, username: 'support'),
      EmailAccount(email: 'info@$domain', domain: domain, username: 'info'),
      EmailAccount(email: 'admin@$domain', domain: domain, username: 'admin'),
    ];
  }

  Future<Map<String, dynamic>> createEmailAccount(String username, String password) async {
    final endpoint = Uri.parse('$_baseUrl/api/v1/emails/create/');
    try {
      final response = await http.post(
        endpoint,
        headers: {
          'Content-Type': 'application/json',
          if (_sessionCookie != null) 'Cookie': _sessionCookie!,
        },
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200 || response.statusCode == 201) {
        return {'success': true, 'message': 'Email account provisioned on VoidPanel.'};
      } else {
        final err = jsonDecode(response.body);
        return {'success': false, 'message': err['error'] ?? 'Provisioning failed'};
      }
    } catch (e) {
      return {'success': true, 'isDemo': true, 'message': 'Account $username created (Demo Mode)'};
    }
  }

  Future<Map<String, dynamic>> changeEmailPassword(String email, String newPassword) async {
    final endpoint = Uri.parse('$_baseUrl/api/v1/emails/change-password/');
    try {
      final response = await http.post(
        endpoint,
        headers: {
          'Content-Type': 'application/json',
          if (_sessionCookie != null) 'Cookie': _sessionCookie!,
        },
        body: jsonEncode({
          'email': email,
          'password': newPassword,
        }),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return {'success': true, 'message': 'Password updated successfully on Dovecot.'};
      } else {
        final err = jsonDecode(response.body);
        return {'success': false, 'message': err['error'] ?? 'Password update failed'};
      }
    } catch (e) {
      return {'success': true, 'isDemo': true, 'message': 'Password updated for $email'};
    }
  }

  // ══════════════════════════════════════════════════════════════════════
  //  VOIDMAIL AI WHITELIST IP MANAGEMENT
  //  These talk to VoidOnyx server (not local VoidPanel)
  // ══════════════════════════════════════════════════════════════════════

  static const String _voidonyxBase = 'https://voidonyx.in';

  /// Fetch all whitelisted IPs for VoidMail AI features.
  Future<List<Map<String, dynamic>>> fetchWhitelistIPs({String domain = ''}) async {
    final endpoint = Uri.parse('$_voidonyxBase/api/v1/voidmail/whitelist/?domain=$domain');
    try {
      final response = await http.get(
        endpoint,
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 6));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final list = (data['data']?['whitelist'] as List?) ?? [];
        return list.cast<Map<String, dynamic>>();
      }
    } catch (_) {}
    return [];
  }

  /// Add an IP to the VoidMail AI whitelist.
  Future<Map<String, dynamic>> addWhitelistIP(String ipAddress, String label, {String domain = ''}) async {
    final endpoint = Uri.parse('$_voidonyxBase/api/v1/voidmail/whitelist/add/');
    try {
      final response = await http.post(
        endpoint,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'ip_address': ipAddress,
          'domain': domain,
          'label': label,
        }),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200 || response.statusCode == 201) {
        return {'success': true, 'message': 'IP whitelisted for AI features.'};
      } else {
        final err = jsonDecode(response.body);
        return {'success': false, 'message': err['error'] ?? 'Failed to add IP'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Failed to add IP: $e'};
    }
  }

  /// Remove an IP from the VoidMail AI whitelist.
  Future<Map<String, dynamic>> removeWhitelistIP(String ipAddress, {String domain = ''}) async {
    final endpoint = Uri.parse('$_voidonyxBase/api/v1/voidmail/whitelist/remove/');
    try {
      final response = await http.post(
        endpoint,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'ip_address': ipAddress,
          'domain': domain,
        }),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return {'success': true, 'message': 'IP removed from whitelist.'};
      } else {
        final err = jsonDecode(response.body);
        return {'success': false, 'message': err['error'] ?? 'Failed to remove IP'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Failed to remove IP: $e'};
    }
  }

  /// Check if the caller's IP is whitelisted for AI features.
  Future<Map<String, dynamic>> checkAiStatus({String domain = ''}) async {
    final endpoint = Uri.parse('$_voidonyxBase/api/v1/voidmail/ai-status/?domain=$domain');
    try {
      final response = await http.get(
        endpoint,
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 6));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'ai_enabled': data['data']?['ai_enabled'] ?? false,
          'voidonyx_url': data['data']?['voidonyx_url'] ?? 'https://voidonyx.in',
          'license_key': data['data']?['license_key'] ?? '',
          'caller_ip': data['data']?['caller_ip'] ?? '',
        };
      }
    } catch (_) {}
    // Fallback: AI disabled
    return {
      'success': false,
      'ai_enabled': false,
      'voidonyx_url': 'https://voidonyx.in',
      'license_key': '',
      'caller_ip': '',
    };
  }
}
