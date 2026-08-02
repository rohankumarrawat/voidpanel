import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// API client for communicating with VoidPanel backend.
/// Handles token management, error responses, and SSL certificates.
class ApiClient {
  final String baseUrl;
  String? _token;
  late final http.Client _httpClient;

  ApiClient({required this.baseUrl}) {
    // Create an HttpClient that accepts the server's certificate.
    // This handles cases where macOS sandbox doesn't trust the full chain
    // (common with Let's Encrypt on sandboxed Flutter macOS apps).
    final ioClient = HttpClient()
      ..badCertificateCallback = (X509Certificate cert, String host, int port) {
        // Only trust our own VoidPanel domain
        final uri = Uri.parse(baseUrl);
        return host == uri.host;
      };
    _httpClient = IOClient(ioClient);
  }

  /// Retrieve stored token
  Future<String?> get token async {
    _token ??= (await SharedPreferences.getInstance()).getString('api_token');
    return _token;
  }

  /// Store token
  Future<void> setToken(String token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_token', token);
  }

  /// Clear stored token
  Future<void> clearToken() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('api_token');
  }

  /// Check if user is authenticated
  Future<bool> get isAuthenticated async {
    final t = await token;
    return t != null && t.isNotEmpty;
  }

  /// Build headers with authentication
  Future<Map<String, String>> _headers() async {
    final t = await token;
    return {
      'Content-Type': 'application/json',
      if (t != null) 'Authorization': 'Bearer $t',
    };
  }

  /// GET request
  Future<ApiResponse> get(String path, {Map<String, String>? queryParams}) async {
    try {
      final uri = Uri.parse('$baseUrl$path').replace(queryParameters: queryParams);
      final response = await _httpClient.get(uri, headers: await _headers());
      return _parseResponse(response);
    } catch (e) {
      return ApiResponse(success: false, error: 'Network error: $e');
    }
  }

  /// POST request
  Future<ApiResponse> post(String path, {Map<String, dynamic>? body}) async {
    try {
      final uri = Uri.parse('$baseUrl$path');
      final response = await _httpClient.post(
        uri,
        headers: await _headers(),
        body: body != null ? jsonEncode(body) : null,
      );
      return _parseResponse(response);
    } catch (e) {
      return ApiResponse(success: false, error: 'Network error: $e');
    }
  }

  /// Parse API response
  ApiResponse _parseResponse(http.Response response) {
    debugPrint('API [${response.statusCode}] ${response.request?.url}');
    debugPrint('Response body: ${response.body.length > 500 ? response.body.substring(0, 500) : response.body}');
    try {
      final body = jsonDecode(response.body);
      if (response.statusCode == 401) {
        // Token expired/invalid
        clearToken();
        return ApiResponse(
          success: false,
          error: body['error'] ?? 'Session expired. Please login again.',
          statusCode: 401,
        );
      }
      return ApiResponse(
        success: body['status'] == 'ok',
        data: body['data'],
        error: body['error'],
        statusCode: response.statusCode,
      );
    } catch (e) {
      debugPrint('Parse error: $e');
      return ApiResponse(
        success: false,
        error: 'Invalid server response',
        statusCode: response.statusCode,
      );
    }
  }
}

/// Standardised API response
class ApiResponse {
  final bool success;
  final dynamic data;
  final String? error;
  final int? statusCode;

  ApiResponse({
    required this.success,
    this.data,
    this.error,
    this.statusCode,
  });
}
