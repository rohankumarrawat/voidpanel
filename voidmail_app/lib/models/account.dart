class EmailAccount {
  final String email;
  final String domain;
  final String username;
  final bool isVoidPanelManaged;

  EmailAccount({
    required this.email,
    required this.domain,
    required this.username,
    this.isVoidPanelManaged = true,
  });

  factory EmailAccount.fromJson(Map<String, dynamic> json) {
    final email = json['email'] ?? '';
    final parts = email.split('@');
    return EmailAccount(
      email: email,
      domain: json['domain'] ?? (parts.length > 1 ? parts[1] : ''),
      username: parts.isNotEmpty ? parts[0] : '',
      isVoidPanelManaged: json['isVoidPanelManaged'] ?? true,
    );
  }
}
