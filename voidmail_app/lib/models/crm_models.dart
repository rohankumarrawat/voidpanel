class CrmContact {
  final int id;
  final String name;
  final String email;
  final String companyName;
  final String phone;
  final String jobTitle;
  final String status;
  final String notes;
  final int totalEmails;
  final String lastContacted;

  const CrmContact({
    required this.id,
    required this.name,
    required this.email,
    this.companyName = '',
    this.phone = '',
    this.jobTitle = '',
    this.status = 'Lead',
    this.notes = '',
    this.totalEmails = 1,
    this.lastContacted = 'Recent',
  });

  factory CrmContact.fromJson(Map<String, dynamic> json) {
    return CrmContact(
      id: json['id'] is int ? json['id'] : int.tryParse('${json['id']}') ?? 0,
      name: json['name'] ?? '',
      email: json['email'] ?? '',
      companyName: json['company_name'] ?? '',
      phone: json['phone'] ?? '',
      jobTitle: json['job_title'] ?? '',
      status: json['status'] ?? 'Lead',
      notes: json['notes'] ?? '',
      totalEmails: json['total_emails'] is int ? json['total_emails'] : int.tryParse('${json['total_emails']}') ?? 1,
      lastContacted: json['last_contacted'] ?? 'Recent',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'email': email,
    'company_name': companyName,
    'phone': phone,
    'job_title': jobTitle,
    'status': status,
    'notes': notes,
    'total_emails': totalEmails,
    'last_contacted': lastContacted,
  };
}

class CrmDeal {
  final int id;
  final String title;
  final String companyName;
  final String contactName;
  final String contactEmail;
  final String stage; // 'lead', 'contacted', 'proposal', 'negotiation', 'won', 'lost'
  final double amount;
  final String formattedAmount;
  final String closeDate;
  final String notes;
  final String createdAt;

  const CrmDeal({
    required this.id,
    required this.title,
    this.companyName = '',
    this.contactName = '',
    this.contactEmail = '',
    this.stage = 'lead',
    this.amount = 0.0,
    this.formattedAmount = '₹0.00',
    this.closeDate = '',
    this.notes = '',
    this.createdAt = '',
  });

  factory CrmDeal.fromJson(Map<String, dynamic> json) {
    final amt = (json['amount'] is num) ? (json['amount'] as num).toDouble() : double.tryParse('${json['amount']}') ?? 0.0;
    String formatted = (json['formatted_amount'] ?? '₹${amt.toStringAsFixed(2)}').toString();
    if (formatted.contains(r'$')) {
      formatted = formatted.replaceAll(r'$', '₹');
    }
    return CrmDeal(
      id: json['id'] is int ? json['id'] : int.tryParse('${json['id']}') ?? 0,
      title: json['title'] ?? 'Deal Opportunity',
      companyName: json['company_name'] ?? '',
      contactName: json['contact_name'] ?? '',
      contactEmail: json['contact_email'] ?? '',
      stage: json['stage'] ?? 'lead',
      amount: amt,
      formattedAmount: formatted,
      closeDate: json['close_date'] ?? '',
      notes: json['notes'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'company_name': companyName,
    'contact_name': contactName,
    'contact_email': contactEmail,
    'stage': stage,
    'amount': amount,
    'formatted_amount': formattedAmount,
    'close_date': closeDate,
    'notes': notes,
    'created_at': createdAt,
  };
}

class CrmCompany {
  final int id;
  final String name;
  final String domain;
  final String industry;
  final String website;
  final String size;
  final int contactsCount;
  final double totalDealsVal;

  const CrmCompany({
    required this.id,
    required this.name,
    required this.domain,
    this.industry = 'Technology',
    this.website = '',
    this.size = '1-50',
    this.contactsCount = 0,
    this.totalDealsVal = 0.0,
  });

  factory CrmCompany.fromJson(Map<String, dynamic> json) {
    return CrmCompany(
      id: json['id'] is int ? json['id'] : int.tryParse('${json['id']}') ?? 0,
      name: json['name'] ?? '',
      domain: json['domain'] ?? '',
      industry: json['industry'] ?? 'Technology',
      website: json['website'] ?? '',
      size: json['size'] ?? '1-50',
      contactsCount: json['contacts_count'] is int ? json['contacts_count'] : int.tryParse('${json['contacts_count']}') ?? 0,
      totalDealsVal: (json['total_deals_val'] is num) ? (json['total_deals_val'] as num).toDouble() : double.tryParse('${json['total_deals_val']}') ?? 0.0,
    );
  }
}

class CrmSummary {
  final int totalContacts;
  final int totalCompanies;
  final int totalDeals;
  final int activeDealsCount;
  final int wonDealsCount;
  final double pipelineValue;
  final String formattedPipeline;
  final double wonValue;
  final String formattedWon;
  final double winRate;

  const CrmSummary({
    this.totalContacts = 0,
    this.totalCompanies = 0,
    this.totalDeals = 0,
    this.activeDealsCount = 0,
    this.wonDealsCount = 0,
    this.pipelineValue = 0.0,
    this.formattedPipeline = '₹0.00',
    this.wonValue = 0.0,
    this.formattedWon = '₹0.00',
    this.winRate = 0.0,
  });

  factory CrmSummary.fromJson(Map<String, dynamic> json) {
    final pVal = (json['pipeline_value'] is num) ? (json['pipeline_value'] as num).toDouble() : double.tryParse('${json['pipeline_value']}') ?? 0.0;
    final wVal = (json['won_value'] is num) ? (json['won_value'] as num).toDouble() : double.tryParse('${json['won_value']}') ?? 0.0;

    String fPipeline = (json['formatted_pipeline'] ?? '₹${pVal.toStringAsFixed(2)}').toString();
    if (fPipeline.contains(r'$')) {
      fPipeline = fPipeline.replaceAll(r'$', '₹');
    }

    String fWon = (json['formatted_won'] ?? '₹${wVal.toStringAsFixed(2)}').toString();
    if (fWon.contains(r'$')) {
      fWon = fWon.replaceAll(r'$', '₹');
    }

    return CrmSummary(
      totalContacts: json['total_contacts'] is int ? json['total_contacts'] : int.tryParse('${json['total_contacts']}') ?? 0,
      totalCompanies: json['total_companies'] is int ? json['total_companies'] : int.tryParse('${json['total_companies']}') ?? 0,
      totalDeals: json['total_deals'] is int ? json['total_deals'] : int.tryParse('${json['total_deals']}') ?? 0,
      activeDealsCount: json['active_deals_count'] is int ? json['active_deals_count'] : int.tryParse('${json['active_deals_count']}') ?? 0,
      wonDealsCount: json['won_deals_count'] is int ? json['won_deals_count'] : int.tryParse('${json['won_deals_count']}') ?? 0,
      pipelineValue: pVal,
      formattedPipeline: fPipeline,
      wonValue: wVal,
      formattedWon: fWon,
      winRate: (json['win_rate'] is num) ? (json['win_rate'] as num).toDouble() : double.tryParse('${json['win_rate']}') ?? 0.0,
    );
  }
}
