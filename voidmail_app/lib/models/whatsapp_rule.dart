class WhatsAppAlertRule {
  final int id;
  final String ruleType; // 'domain', 'email', 'keyword'
  final String pattern;
  final String targetPhone;
  final String note;
  final bool isActive;
  final int triggerCount;
  final String lastTriggered;

  const WhatsAppAlertRule({
    required this.id,
    required this.ruleType,
    required this.pattern,
    this.targetPhone = '',
    this.note = '',
    this.isActive = true,
    this.triggerCount = 0,
    this.lastTriggered = 'Never',
  });

  factory WhatsAppAlertRule.fromJson(Map<String, dynamic> json) {
    return WhatsAppAlertRule(
      id: json['id'] is int ? json['id'] : int.tryParse('${json['id']}') ?? 0,
      ruleType: json['rule_type'] ?? 'domain',
      pattern: json['pattern'] ?? '',
      targetPhone: json['target_phone'] ?? '',
      note: json['note'] ?? '',
      isActive: json['is_active'] == true,
      triggerCount: json['trigger_count'] is int ? json['trigger_count'] : int.tryParse('${json['trigger_count']}') ?? 0,
      lastTriggered: json['last_triggered_at'] ?? json['last_triggered'] ?? 'Never',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'rule_type': ruleType,
    'pattern': pattern,
    'target_phone': targetPhone,
    'note': note,
    'is_active': isActive,
    'trigger_count': triggerCount,
    'last_triggered_at': lastTriggered,
  };
}
