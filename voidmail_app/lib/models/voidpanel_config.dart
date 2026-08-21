import 'dart:convert';

class ServerConfig {
  final String providerName; // 'VoidPanel', 'Outlook / Office 365', 'Gmail', 'Custom IMAP/SMTP'
  final String serverUrl;
  final String username;
  final String password;
  final String email;
  final String domain;
  final String imapHost;
  final int imapPort;
  final bool imapSsl;
  final String smtpHost;
  final int smtpPort;
  final bool smtpSsl;
  final String smtpUsername;

  ServerConfig({
    this.providerName = 'VoidPanel',
    required this.serverUrl,
    required this.username,
    this.password = '',
    required this.email,
    required this.domain,
    required this.imapHost,
    this.imapPort = 993,
    this.imapSsl = true,
    required this.smtpHost,
    this.smtpPort = 465,
    this.smtpSsl = true,
    String? smtpUsername,
  }) : smtpUsername = smtpUsername ?? username;

  /// Unique ID for this account based on email
  String get id => email.toLowerCase().trim();

  factory ServerConfig.custom({
    required String email,
    required String password,
    required String imapHost,
    int imapPort = 993,
    bool imapSsl = true,
    required String smtpHost,
    int smtpPort = 465,
    bool smtpSsl = true,
    String? providerName,
  }) {
    final parts = email.split('@');
    final domain = parts.length > 1 ? parts[1] : 'domain.com';
    return ServerConfig(
      providerName: providerName ?? 'Custom IMAP/SMTP',
      serverUrl: 'https://$domain',
      username: email,
      password: password,
      email: email,
      domain: domain,
      imapHost: imapHost,
      imapPort: imapPort,
      imapSsl: imapSsl,
      smtpHost: smtpHost,
      smtpPort: smtpPort,
      smtpSsl: smtpSsl,
      smtpUsername: email,
    );
  }

  factory ServerConfig.defaultForDomain({
    required String serverUrl,
    required String username,
    String password = '',
    required String domain,
  }) {
    final host = domain.isNotEmpty ? 'mail.$domain' : 'mail.voidpanel.com';
    final email = username.contains('@') ? username : '$username@$domain';
    return ServerConfig(
      providerName: 'VoidPanel Host',
      serverUrl: serverUrl,
      username: username,
      password: password,
      email: email,
      domain: domain,
      imapHost: host,
      imapPort: 993,
      imapSsl: true,
      smtpHost: host,
      smtpPort: 465,
      smtpSsl: true,
      smtpUsername: email,
    );
  }

  // ── JSON Serialization for multi-account persistence ──

  Map<String, dynamic> toJson() => {
    'providerName': providerName,
    'serverUrl': serverUrl,
    'username': username,
    'password': password,
    'email': email,
    'domain': domain,
    'imapHost': imapHost,
    'imapPort': imapPort,
    'imapSsl': imapSsl,
    'smtpHost': smtpHost,
    'smtpPort': smtpPort,
    'smtpSsl': smtpSsl,
    'smtpUsername': smtpUsername,
  };

  factory ServerConfig.fromJson(Map<String, dynamic> json) => ServerConfig(
    providerName: json['providerName'] ?? 'Custom',
    serverUrl: json['serverUrl'] ?? '',
    username: json['username'] ?? '',
    password: json['password'] ?? '',
    email: json['email'] ?? '',
    domain: json['domain'] ?? '',
    imapHost: json['imapHost'] ?? '',
    imapPort: json['imapPort'] ?? 993,
    imapSsl: json['imapSsl'] ?? true,
    smtpHost: json['smtpHost'] ?? '',
    smtpPort: json['smtpPort'] ?? 465,
    smtpSsl: json['smtpSsl'] ?? true,
    smtpUsername: json['smtpUsername'],
  );

  /// Encode a list of accounts to a JSON string for SharedPreferences
  static String encodeAccounts(List<ServerConfig> accounts) =>
      jsonEncode(accounts.map((a) => a.toJson()).toList());

  /// Decode a JSON string from SharedPreferences to a list of accounts
  static List<ServerConfig> decodeAccounts(String jsonStr) {
    try {
      final decoded = jsonDecode(jsonStr);
      if (decoded is List) {
        return decoded
            .whereType<Map>()
            .map((item) => ServerConfig.fromJson(Map<String, dynamic>.from(item)))
            .toList();
      }
    } catch (e) {
      // Ignored - fallback to empty list
    }
    return [];
  }
}
