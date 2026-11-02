class DomainHealthItem {
  final String status;
  final String grade;
  final String record;
  final String detail;

  const DomainHealthItem({
    this.status = 'PASS',
    this.grade = '100% Compliant',
    this.record = '',
    this.detail = '',
  });

  factory DomainHealthItem.fromJson(Map<String, dynamic> json) {
    return DomainHealthItem(
      status: json['status'] ?? 'PASS',
      grade: json['grade'] ?? '100% Compliant',
      record: json['record'] ?? '',
      detail: json['detail'] ?? '',
    );
  }
}

class DomainHealthAudit {
  final String domain;
  final DomainHealthItem spf;
  final DomainHealthItem dkim;
  final DomainHealthItem dmarc;
  final DomainHealthItem ptrRdns;

  const DomainHealthAudit({
    required this.domain,
    required this.spf,
    required this.dkim,
    required this.dmarc,
    required this.ptrRdns,
  });

  factory DomainHealthAudit.fromJson(Map<String, dynamic> json) {
    return DomainHealthAudit(
      domain: json['domain'] ?? 'voidonyx.com',
      spf: DomainHealthItem.fromJson(json['spf'] ?? {}),
      dkim: DomainHealthItem.fromJson(json['dkim'] ?? {}),
      dmarc: DomainHealthItem.fromJson(json['dmarc'] ?? {}),
      ptrRdns: DomainHealthItem.fromJson(json['ptr_rdns'] ?? {}),
    );
  }
}

class TwoFactorStatus {
  final bool isEnabled;
  final bool hasKeys;
  final bool hasWhatsapp;
  final String whatsappHint;
  final int keysCount;

  const TwoFactorStatus({
    this.isEnabled = false,
    this.hasKeys = false,
    this.hasWhatsapp = false,
    this.whatsappHint = '',
    this.keysCount = 0,
  });

  factory TwoFactorStatus.fromJson(Map<String, dynamic> json) {
    return TwoFactorStatus(
      isEnabled: json['is_enabled'] == true || json['is_2fa_enabled'] == true,
      hasKeys: json['has_keys'] == true,
      hasWhatsapp: json['has_whatsapp'] == true,
      whatsappHint: json['whatsapp_hint'] ?? '',
      keysCount: json['keys_count'] is int ? json['keys_count'] : int.tryParse('${json['keys_count']}') ?? 0,
    );
  }
}

class BurnMessage {
  final String token;
  final String url;
  final String content;
  final bool isBurned;

  const BurnMessage({
    required this.token,
    required this.url,
    this.content = '',
    this.isBurned = false,
  });

  factory BurnMessage.fromJson(Map<String, dynamic> json) {
    return BurnMessage(
      token: json['token'] ?? '',
      url: json['url'] ?? '',
      content: json['content'] ?? '',
      isBurned: json['is_burned'] == true || json['status'] == 'burned',
    );
  }
}

class VoidMaskAlias {
  final String aliasEmail;
  final String realDestination;
  final String label;

  const VoidMaskAlias({
    required this.aliasEmail,
    required this.realDestination,
    this.label = 'Default',
  });

  factory VoidMaskAlias.fromJson(Map<String, dynamic> json) {
    return VoidMaskAlias(
      aliasEmail: json['alias_email'] ?? '',
      realDestination: json['real_destination'] ?? '',
      label: json['label'] ?? 'Default',
    );
  }
}
