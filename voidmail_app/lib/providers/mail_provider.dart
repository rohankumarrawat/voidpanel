import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/email_item.dart';
import '../models/folder.dart';
import '../models/account.dart';
import '../models/voidpanel_config.dart';
import '../services/mail_service.dart';
import '../services/voidpanel_api_service.dart';
import '../services/imap_service.dart';
import '../services/voidonyx_ai_service.dart';
import '../services/notification_service.dart';

enum QuickFilter { all, unread, starred, attachments }

class MailProvider extends ChangeNotifier {
  final VoidPanelApiService apiService = VoidPanelApiService();

  String _currentEmail = 'social@voidonyx.in';
  String _currentDomain = 'voidonyx.in';
  bool _isLoggedIn = false;
  ThemeMode _themeMode = ThemeMode.light;

  ServerConfig? _config;
  FolderType _currentFolder = FolderType.inbox;
  QuickFilter _quickFilter = QuickFilter.all;
  String _searchQuery = '';

  bool _isLoading = false;
  List<EmailItem> _allEmails = [];
  List<EmailAccount> _managedAccounts = [];
  String? _lastError;

  // ── Multi-Account State ──
  List<ServerConfig> _accounts = [];
  int _activeAccountIndex = 0;
  bool _showUnifiedInbox = false;
  Map<String, List<EmailItem>> _emailsByAccount = {};
  Map<String, List<EmailItem>> _inboxByAccount = {}; // Persistent inbox cache for Primary Mail
  final Map<String, List<EmailItem>> _folderCache = {}; // Multi-folder cache for instant switching
  final List<EmailItem> _localSentEmails = []; // Locally sent emails cache
  final Set<String> _knownEmailIds = {}; // Tracks received email IDs to trigger incoming notifications
  Timer? _autoSyncTimer;

  // Multi-select state
  bool _isSelectionMode = false;
  final Set<String> _selectedEmailIds = {};

  // Appearance scaling & accent theme state
  double _fontSizeScale = 1.0;
  String _fontSizeName = 'Medium';
  Color _accentColor = const Color(0xFF6366F1);
  String _themeName = 'VoidOnyx Purple';

  // ── VoidMail AI Whitelist State ──
  bool _aiEnabled = false;
  String _voidonyxUrl = 'https://voidonyx.in';
  String _licenseKey = '';
  String _callerIp = '';
  final VoidOnyxAiService _aiService = VoidOnyxAiService();

  // Getters
  String get currentEmail => _currentEmail;
  String get currentDomain => _currentDomain;
  bool get isLoggedIn => _isLoggedIn;
  ThemeMode get themeMode => _themeMode;
  ServerConfig? get config => _config;
  FolderType get currentFolder => _currentFolder;
  QuickFilter get quickFilter => _quickFilter;
  String get searchQuery => _searchQuery;
  bool get isLoading => _isLoading;
  List<EmailAccount> get managedAccounts => _managedAccounts;
  bool get isSelectionMode => _isSelectionMode;
  Set<String> get selectedEmailIds => _selectedEmailIds;
  String? get lastError => _lastError;

  // Multi-account getters
  List<ServerConfig> get accounts => _accounts;
  int get activeAccountIndex => _activeAccountIndex;
  bool get showUnifiedInbox => _showUnifiedInbox;
  ServerConfig? get activeAccount => _accounts.isNotEmpty && _activeAccountIndex < _accounts.length
      ? _accounts[_activeAccountIndex] : _config;
  int get totalUnreadAllAccounts {
    int count = 0;
    for (final emails in _emailsByAccount.values) {
      count += emails.where((e) => !e.isRead && e.folder == FolderType.inbox).length;
    }
    return count;
  }

  double get fontSizeScale => _fontSizeScale;
  String get fontSizeName => _fontSizeName;
  Color get accentColor => _accentColor;
  String get themeName => _themeName;

  // AI Getters
  bool get aiEnabled => _aiEnabled;
  String get voidonyxUrl => _voidonyxUrl;
  String get callerIp => _callerIp;
  VoidOnyxAiService get aiService => _aiService;

  void setFontSize(String name, double scale) {
    _fontSizeName = name;
    _fontSizeScale = scale;
    notifyListeners();
  }

  void setAccentTheme(String name, Color color) {
    _themeName = name;
    _accentColor = color;
    notifyListeners();
  }

  MailProvider() {
    _initDemoData();
    _loadSavedAccounts();
  }

  @override
  void dispose() {
    _autoSyncTimer?.cancel();
    super.dispose();
  }

  void _startAutoSyncTimer() {
    _autoSyncTimer?.cancel();
    _autoSyncTimer = Timer.periodic(const Duration(seconds: 60), (_) async {
      if (_isLoggedIn && _config != null) {
        debugPrint('[MailProvider] Running periodic auto-sync...');
        await refreshMail(isBackground: true);
      }
    });
  }

  /// Load saved accounts and offline cached emails from SharedPreferences on startup
  Future<void> _loadSavedAccounts() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      // 1. Restore known email IDs
      final savedKnown = prefs.getStringList('voidmail_known_email_ids');
      if (savedKnown != null && savedKnown.isNotEmpty) {
        _knownEmailIds.addAll(savedKnown);
      }

      // 2. Restore saved accounts
      final saved = prefs.getString('voidmail_accounts');
      if (saved != null && saved.isNotEmpty) {
        _accounts = ServerConfig.decodeAccounts(saved);
        _activeAccountIndex = prefs.getInt('voidmail_active_index') ?? 0;
        if (_activeAccountIndex >= _accounts.length) _activeAccountIndex = 0;
        if (_accounts.isNotEmpty) {
          _config = _accounts[_activeAccountIndex];
          _currentEmail = _config!.email;
          _currentDomain = _config!.domain;
          _isLoggedIn = true;

          // 3. Immediately hydrate UI from offline cache for instant startup
          final activeAccId = _config!.id;
          final cachedInboxKey = 'voidmail_cache_${activeAccId}_inbox';
          final cachedRaw = prefs.getString(cachedInboxKey);
          if (cachedRaw != null && cachedRaw.isNotEmpty) {
            final cachedEmails = EmailItem.decodeList(cachedRaw);
            if (cachedEmails.isNotEmpty) {
              _allEmails = cachedEmails;
              _emailsByAccount[activeAccId] = cachedEmails;
              _inboxByAccount[activeAccId] = cachedEmails;
              _folderCache['$activeAccId-inbox'] = cachedEmails;
              _knownEmailIds.addAll(cachedEmails.map((e) => e.id));
              debugPrint('[MailProvider] Hydrated ${_allEmails.length} offline cached emails for $activeAccId');
            }
          }

          // Hydrate other cached folders
          for (final f in FolderType.values) {
            final fKey = 'voidmail_cache_${activeAccId}_${f.name}';
            final fRaw = prefs.getString(fKey);
            if (fRaw != null && fRaw.isNotEmpty) {
              final fEmails = EmailItem.decodeList(fRaw);
              if (fEmails.isNotEmpty) {
                _folderCache['$activeAccId-${f.name}'] = fEmails;
              }
            }
          }

          // Render cached data immediately
          notifyListeners();

          // Start periodic background auto-sync timer
          _startAutoSyncTimer();

          // Fetch fresh emails in background without blocking UI
          try {
            await refreshMail(isBackground: true);
          } catch (e) {
            debugPrint('[MailProvider] Background startup refresh notice: $e');
          }
          try {
            await checkAndSetAiStatus();
          } catch (e) {
            debugPrint('[MailProvider] Background AI status notice: $e');
          }
        }
      }
    } catch (e) {
      debugPrint('[MailProvider] Error loading saved accounts: $e');
    }
  }

  /// Persist accounts to SharedPreferences
  Future<void> _saveAccounts() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('voidmail_accounts', ServerConfig.encodeAccounts(_accounts));
      await prefs.setInt('voidmail_active_index', _activeAccountIndex);
    } catch (e) {
      debugPrint('[MailProvider] Error saving accounts: $e');
    }
  }

  /// Persist cached emails for a specific folder to disk
  Future<void> _saveCachedFolderEmails(String accountId, FolderType folder, List<EmailItem> emails) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = 'voidmail_cache_${accountId}_${folder.name}';
      await prefs.setString(key, EmailItem.encodeList(emails));
    } catch (e) {
      debugPrint('[MailProvider] Error saving cached emails: $e');
    }
  }

  /// Persist known email IDs to prevent duplicate notifications
  Future<void> _saveKnownEmailIds() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('voidmail_known_email_ids', _knownEmailIds.toList());
    } catch (e) {
      debugPrint('[MailProvider] Error saving known email IDs: $e');
    }
  }

  /// Add an account to the multi-account list (called after successful login)
  void _registerAccount(ServerConfig config) {
    // Don't add duplicate
    final exists = _accounts.any((a) => a.id == config.id);
    if (!exists) {
      _accounts.add(config);
      _activeAccountIndex = _accounts.length - 1;
      debugPrint('[MailProvider] Added new account: ${config.email} (total: ${_accounts.length})');
    } else {
      // Update existing
      final idx = _accounts.indexWhere((a) => a.id == config.id);
      _accounts[idx] = config;
      _activeAccountIndex = idx;
      debugPrint('[MailProvider] Updated existing account: ${config.email} (total: ${_accounts.length})');
    }
    _saveAccounts();
    _startAutoSyncTimer();
    notifyListeners();
  }

  /// Switch to a different linked account
  Future<void> switchAccount(int index) async {
    if (index < 0 || index >= _accounts.length) return;
    _activeAccountIndex = index;
    _config = _accounts[index];
    _currentEmail = _config!.email;
    _currentDomain = _config!.domain;
    _showUnifiedInbox = false;
    _currentFolder = FolderType.inbox;

    // Use cached emails if available, otherwise fetch
    if (_emailsByAccount.containsKey(_config!.id)) {
      _allEmails = _emailsByAccount[_config!.id]!;
    } else {
      _allEmails = [];
    }
    notifyListeners();
    await _saveAccounts();
    await refreshMail();
    await checkAndSetAiStatus();
  }

  /// Remove a linked account
  Future<void> removeAccount(int index) async {
    if (index < 0 || index >= _accounts.length) return;
    final removed = _accounts.removeAt(index);
    _emailsByAccount.remove(removed.id);
    _inboxByAccount.remove(removed.id);

    if (_accounts.isEmpty) {
      _isLoggedIn = false;
      _allEmails = [];
      _activeAccountIndex = 0;
    } else {
      if (_activeAccountIndex >= _accounts.length) {
        _activeAccountIndex = _accounts.length - 1;
      }
      _config = _accounts[_activeAccountIndex];
      _currentEmail = _config!.email;
      _currentDomain = _config!.domain;
      _allEmails = _emailsByAccount[_config!.id] ?? [];
    }
    await _saveAccounts();
    notifyListeners();
  }

  /// Toggle unified inbox view (all accounts merged)
  void toggleUnifiedInbox() {
    _showUnifiedInbox = !_showUnifiedInbox;
    _currentFolder = FolderType.inbox;
    if (_showUnifiedInbox) {
      // Merge all INBOX caches for Primary Mail
      _allEmails = [];
      for (final emails in _inboxByAccount.values) {
        _allEmails.addAll(emails);
      }
      // If any account is missing inbox cache, trigger a refresh
      if (_inboxByAccount.length < _accounts.length) {
        refreshMail();
      }
    } else if (_config != null) {
      _allEmails = _emailsByAccount[_config!.id] ?? _inboxByAccount[_config!.id] ?? [];
    }
    notifyListeners();
  }

  // ══════════════════════════════════════════════════════════════════════
  //  VOIDMAIL AI — Domain Whitelist Status & AI Query Methods
  // ══════════════════════════════════════════════════════════════════════

  /// Called after login — checks if the user's email domain is whitelisted
  /// for VoidMail AI features on VoidOnyx. If yes, enables AI features.
  Future<void> checkAndSetAiStatus() async {
    try {
      // Extract domain from current email (e.g. rohan@new.com → new.com)
      final domain = _currentEmail.contains('@')
          ? _currentEmail.split('@').last.toLowerCase()
          : _currentDomain.toLowerCase();

      final result = await apiService.checkAiStatus(domain: domain);
      _aiEnabled = result['ai_enabled'] == true;
      _voidonyxUrl = result['voidonyx_url'] ?? 'https://voidonyx.in';
      _licenseKey = result['license_key'] ?? '';
      _callerIp = result['caller_ip'] ?? domain;

      if (_aiEnabled) {
        _aiService.configure(
          voidonyxUrl: _voidonyxUrl,
          licenseKey: _licenseKey.isNotEmpty ? _licenseKey : 'domain-whitelisted',
          panelHost: apiService.baseUrl,
        );
        debugPrint('[MailProvider] AI ENABLED — Domain "$domain" is whitelisted');
      } else {
        debugPrint('[MailProvider] AI DISABLED — IP $_callerIp not whitelisted');
      }
      notifyListeners();
    } catch (e) {
      debugPrint('[MailProvider] AI status check failed: $e');
      _aiEnabled = false;
      notifyListeners();
    }
  }

  /// Force-enable AI for demo mode (when server is unreachable).
  void enableAiDemo() {
    _aiEnabled = true;
    _aiService.configure(
      voidonyxUrl: 'https://voidonyx.in',
      licenseKey: 'demo-key',
    );
    notifyListeners();
  }

  /// Send an AI query through VoidOnyx's AI Gateway.
  Future<Map<String, dynamic>> sendAiQuery(
    String message, {
    List<Map<String, String>> history = const [],
    String? systemPrompt,
  }) async {
    if (!_aiEnabled) {
      return {
        'success': false,
        'error': 'AI features are not enabled. Your IP is not whitelisted.',
      };
    }
    return await _aiService.chat(
      message: message,
      history: history,
      systemPrompt: systemPrompt,
    );
  }

  /// Get an AI-generated email reply suggestion.
  Future<Map<String, dynamic>> getAiReplySuggestion({
    required String originalEmail,
    required String senderName,
    String tone = 'professional',
  }) async {
    if (!_aiEnabled) {
      return {'success': false, 'error': 'AI not enabled'};
    }
    return await _aiService.suggestReply(
      originalEmail: originalEmail,
      senderName: senderName,
      tone: tone,
    );
  }

  void _initDemoData() {
    final now = DateTime.now();
    _allEmails = [
      EmailItem(
        id: 'email-1',
        senderName: 'Instagram',
        senderEmail: 'no-reply@mail.instagram.com',
        recipientEmail: 'parirawat@voidonyx.com',
        subject: 'New login to Instagram from Chrome...',
        snippet: 'Security alert for your Instagram account. If this was you, ignore this email...',
        body: '''Hi Pari,\n\nWe noticed a new login to your Instagram account from Chrome on macOS in New Delhi, India.\n\nIf this was you, you can ignore this message. If you did not log in, please secure your account immediately by resetting your password.''',
        timestamp: now.subtract(const Duration(minutes: 2)),
        isRead: false,
        isStarred: false,
        aiSummary: 'Security alert for your Instagram account. If this was...',
        isAiPriority: true,
        category: 'Social',
        avatarColor: const Color(0xFFE1306C),
      ),
      EmailItem(
        id: 'email-2',
        senderName: 'Rohan Kumar',
        senderEmail: 'rohan@voidonyx.com',
        recipientEmail: 'parirawat@voidonyx.com',
        subject: 'Project proposal for VoidMail AI',
        snippet: 'Hi Pari, please find the updated proposal with AI features, roadmap, and pricing...',
        body: '''Hi Pari,\n\nPlease find the updated proposal for VoidMail AI.\n\nI've included the AI features, roadmap, and pricing.\n\nLooking forward to your feedback.\n\nBest,\nRohan''',
        timestamp: now.subtract(const Duration(minutes: 25)),
        isRead: false,
        isStarred: true,
        aiSummary: 'Project proposal for VoidMail AI with features & pricing.',
        isAiPriority: true,
        category: 'AI Priority',
        avatarColor: const Color(0xFF4F46E5),
      ),
      EmailItem(
        id: 'email-3',
        senderName: 'Amazon.in',
        senderEmail: 'auto-confirm@amazon.in',
        recipientEmail: 'parirawat@voidonyx.com',
        subject: 'Your order #404-8791923-1234567',
        snippet: 'Your package will be delivered by 10 Aug, 2026. Track your package online...',
        body: '''Hello Pari,\n\nThank you for shopping with Amazon.in. Your order #404-8791923-1234567 has been dispatched and will be delivered by 10 Aug, 2026.\n\nTrack your order anytime in the Amazon app.''',
        timestamp: now.subtract(const Duration(hours: 2)),
        isRead: true,
        isStarred: false,
        aiSummary: 'Order shipped. Package delivery scheduled by 10 Aug.',
        isAiPriority: false,
        category: 'Promotions',
        avatarColor: const Color(0xFFFF9900),
      ),
      EmailItem(
        id: 'email-4',
        senderName: 'Notion Team',
        senderEmail: 'team@m.notion.so',
        recipientEmail: 'parirawat@voidonyx.com',
        subject: 'Updates to our Terms of Service',
        snippet: "We're updating our terms to give you more clarity and control over your data...",
        body: '''Hi Notion User,\n\nWe are updating our Terms of Service and Privacy Policy to provide greater transparency and incorporate new AI workspace capabilities.\n\nPlease review the updated terms at notion.so/terms.''',
        timestamp: now.subtract(const Duration(hours: 3)),
        isRead: true,
        isStarred: false,
        aiSummary: 'Updates to Terms of Service for AI workspace features.',
        isAiPriority: false,
        category: 'Primary',
        avatarColor: const Color(0xFF000000),
      ),
      EmailItem(
        id: 'email-5',
        senderName: 'LinkedIn',
        senderEmail: 'messages-noreply@linkedin.com',
        recipientEmail: 'parirawat@voidonyx.com',
        subject: 'Pari, people are looking at your profile',
        snippet: 'See who viewed your profile this week. 14 people searched for Product Designers...',
        body: '''Hi Pari,\n\n14 people viewed your profile this week on LinkedIn.\n\nSee who viewed your profile and connect with top founders and engineering leads in your network.''',
        timestamp: now.subtract(const Duration(hours: 5)),
        isRead: true,
        isStarred: false,
        aiSummary: 'Profile views summary: 14 people viewed your profile.',
        isAiPriority: false,
        category: 'Social',
        avatarColor: const Color(0xFF0A66C2),
      ),
      // Sent Folder Items
      EmailItem(
        id: 'sent-1',
        senderName: 'Pari Rawat',
        senderEmail: 'parirawat@voidonyx.com',
        recipientEmail: 'rohan@voidonyx.com',
        subject: 'Re: Project proposal for VoidMail AI',
        snippet: "Hi Rohan, Thanks for sharing the updated proposal. It looks great! I'll review it and get back to you with my feedback soon.",
        body: '''Hi Rohan,\n\nThanks for sharing the updated proposal. It looks great! I'll review it and get back to you with my feedback soon.\n\nBest,\nPari''',
        timestamp: now.subtract(const Duration(minutes: 10)),
        isRead: true,
        folder: FolderType.sent,
        avatarColor: const Color(0xFF6C5CE7),
      ),
      EmailItem(
        id: 'sent-2',
        senderName: 'Pari Rawat',
        senderEmail: 'parirawat@voidonyx.com',
        recipientEmail: 'client@techverse.com',
        subject: 'VoidOnyX Platform Onboarding Credentials',
        snippet: 'Dear Client, Please find attached your login credentials and API key for VoidPanel SaaS portal...',
        body: '''Dear Client,\n\nPlease find attached your login credentials and API key for VoidPanel SaaS portal.\n\nBest regards,\nPari''',
        timestamp: now.subtract(const Duration(hours: 4)),
        isRead: true,
        folder: FolderType.sent,
        avatarColor: const Color(0xFF6C5CE7),
      ),
      // Drafts Item
      EmailItem(
        id: 'draft-1',
        senderName: 'Pari Rawat',
        senderEmail: 'parirawat@voidonyx.com',
        recipientEmail: 'team@voidonyx.com',
        subject: '[Draft] Q3 Product Roadmap & VoidMail Release',
        snippet: 'Team, here is the draft roadmap for Q3 including VoidMail AI integration...',
        body: '''Team,\n\nHere is the draft roadmap for Q3 including VoidMail AI integration...''',
        timestamp: now.subtract(const Duration(hours: 1)),
        isRead: true,
        folder: FolderType.drafts,
        avatarColor: const Color(0xFFF59E0B),
      ),
      // Spam Item
      EmailItem(
        id: 'spam-1',
        senderName: 'Unclaimed Rewards',
        senderEmail: 'offers@promo-verify-online.com',
        recipientEmail: 'parirawat@voidonyx.com',
        subject: 'You have 1 unread reward gift card waiting',
        snippet: 'Claim your gift card within 24 hours to avoid expiration...',
        body: '''Claim your gift card within 24 hours to avoid expiration...''',
        timestamp: now.subtract(const Duration(hours: 12)),
        isRead: false,
        folder: FolderType.spam,
        avatarColor: const Color(0xFFEF4444),
      ),
    ];
    _config = ServerConfig.defaultForDomain(
      serverUrl: 'http://localhost:8000',
      username: 'parirawat@voidonyx.com',
      domain: 'voidonyx.com',
    );
  }

  // Auth & Connection via VoidPanel Server
  Future<Map<String, dynamic>> loginToVoidPanel({
    required String serverUrl,
    required String username,
    required String password,
  }) async {
    _isLoading = true;
    _lastError = null;
    notifyListeners();

    apiService.setBaseUrl(serverUrl);
    final result = await apiService.login(username, password);

    if (result['success'] == true) {
      _isLoggedIn = true;
      _currentDomain = result['domain'] ?? 'voidonyx.com';
      _currentEmail = username.contains('@') ? username : '$username@$_currentDomain';
      _config = ServerConfig.defaultForDomain(
        serverUrl: serverUrl,
        username: username,
        password: password,
        domain: _currentDomain,
      );

      // Attempt to fetch real IMAP emails from VoidPanel host
      try {
        final realEmails = await ImapService.fetchEmails(
          host: _config!.imapHost,
          port: _config!.imapPort,
          isSsl: _config!.imapSsl,
          username: _currentEmail,
          password: password,
          folderType: FolderType.inbox,
        );
        _allEmails = realEmails;
        _emailsByAccount[_config!.id] = realEmails;
        _inboxByAccount[_config!.id] = realEmails; // Cache inbox for Primary Mail
      } catch (e) {
        debugPrint('IMAP direct sync notice: $e');
        _allEmails = [];
        _lastError = e.toString();
      }

      // Register this account in multi-account list
      _registerAccount(_config!);

      await fetchManagedAccounts();

      // Check if user's domain is whitelisted for AI features
      await checkAndSetAiStatus();
    }

    _isLoading = false;
    notifyListeners();
    return result;
  }

  // Auth & Connection via Advanced Custom IMAP & SMTP Server (Outlook-style)
  Future<Map<String, dynamic>> loginWithCustomServer({
    required String email,
    required String password,
    required String imapHost,
    required int imapPort,
    required bool imapSsl,
    required String smtpHost,
    required int smtpPort,
    required bool smtpSsl,
    String? providerName,
  }) async {
    _isLoading = true;
    _lastError = null;
    notifyListeners();

    _config = ServerConfig.custom(
      email: email,
      password: password,
      imapHost: imapHost,
      imapPort: imapPort,
      imapSsl: imapSsl,
      smtpHost: smtpHost,
      smtpPort: smtpPort,
      smtpSsl: smtpSsl,
      providerName: providerName ?? 'Outlook / Custom IMAP',
    );

    try {
      final realEmails = await ImapService.fetchEmails(
        host: imapHost,
        port: imapPort,
        isSsl: imapSsl,
        username: email,
        password: password,
        folderType: FolderType.inbox,
      );

      _isLoading = false;
      _isLoggedIn = true;
      _currentEmail = email;
      final parts = email.split('@');
      _currentDomain = parts.length > 1 ? parts[1] : 'domain.com';
      _allEmails = realEmails;
      _emailsByAccount[_config!.id] = realEmails;
      _inboxByAccount[_config!.id] = realEmails; // Cache inbox for Primary Mail
      notifyListeners();

      // Register this account in multi-account list
      _registerAccount(_config!);

      // Check if user's domain is whitelisted for AI features
      await checkAndSetAiStatus();

      return {
        'success': true,
        'message': 'Connected to $imapHost (IMAP) & fetched ${realEmails.length} emails.',
        'domain': _currentDomain,
      };
    } catch (e) {
      _isLoading = false;
      _lastError = e.toString();
      notifyListeners();

      return {
        'success': false,
        'message': 'Failed to connect to IMAP server ($imapHost:$imapPort)\n\nError details: ${e.toString()}',
      };
    }
  }

  void updateServerConfig(ServerConfig newConfig) {
    _config = newConfig;
    notifyListeners();
  }

  void logout() {
    _isLoggedIn = false;
    _selectedEmailIds.clear();
    _isSelectionMode = false;
    notifyListeners();
  }

  void toggleTheme(bool isDark) {
    _themeMode = isDark ? ThemeMode.dark : ThemeMode.light;
    notifyListeners();
  }

  String _getCacheKey(FolderType folder) {
    final acc = _showUnifiedInbox ? 'primary' : (_config?.id ?? 'default');
    return '$acc-${folder.name}';
  }

  // Folder & Navigation
  void selectFolder(FolderType folder) {
    _currentFolder = folder;
    _clearSelection();

    final key = _getCacheKey(folder);
    if (_folderCache.containsKey(key) && _folderCache[key]!.isNotEmpty) {
      _allEmails = List.from(_folderCache[key]!);
      _isLoading = false;
      notifyListeners(); // Instant zero-latency UI update from cache
    } else {
      _isLoading = true;
      notifyListeners();
    }

    refreshMail(); // Sync fresh data in background
  }

  void setQuickFilter(QuickFilter filter) {
    _quickFilter = filter;
    notifyListeners();
  }

  void setSearchQuery(String query) {
    _searchQuery = query.trim().toLowerCase();
    notifyListeners();
  }

  // Email Retrieval & Filtering
  List<EmailItem> get filteredEmails {
    return _allEmails.where((email) {
      // 1. Folder filter
      if (_currentFolder == FolderType.starred) {
        if (!email.isStarred) return false;
      } else {
        if (email.folder != _currentFolder) return false;
      }

      // 2. Quick filter
      switch (_quickFilter) {
        case QuickFilter.unread:
          if (email.isRead) return false;
          break;
        case QuickFilter.starred:
          if (!email.isStarred) return false;
          break;
        case QuickFilter.attachments:
          if (!email.hasAttachments) return false;
          break;
        case QuickFilter.all:
          break;
      }

      // 3. Search query
      if (_searchQuery.isNotEmpty) {
        final matchesSubject = email.subject.toLowerCase().contains(_searchQuery);
        final matchesSender = email.senderName.toLowerCase().contains(_searchQuery) ||
            email.senderEmail.toLowerCase().contains(_searchQuery);
        final matchesBody = email.snippet.toLowerCase().contains(_searchQuery);
        if (!matchesSubject && !matchesSender && !matchesBody) return false;
      }

      return true;
    }).toList()
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
  }

  int getUnreadCount(FolderType folder) {
    if (folder == FolderType.starred) {
      return _allEmails.where((e) => e.isStarred && !e.isRead).length;
    }
    return _allEmails.where((e) => e.folder == folder && !e.isRead).length;
  }

  /// Extract unique contacts from all IMAP emails (senders).
  List<Map<String, String>> get extractedContacts {
    final seen = <String>{};
    final contacts = <Map<String, String>>[];

    for (final email in _allEmails) {
      final key = email.senderEmail.toLowerCase();
      if (key.isNotEmpty && !seen.contains(key)) {
        seen.add(key);
        contacts.add({
          'name': email.senderName.isNotEmpty ? email.senderName : key.split('@').first,
          'email': email.senderEmail,
        });
      }
    }

    contacts.sort((a, b) => (a['name'] ?? '').compareTo(b['name'] ?? ''));
    return contacts;
  }

  // Email Actions
  void toggleStar(String emailId) {
    final index = _allEmails.indexWhere((e) => e.id == emailId);
    if (index != -1) {
      _allEmails[index].isStarred = !_allEmails[index].isStarred;
      if (_config != null) {
        _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
      }
      notifyListeners();
    }
  }

  void toggleRead(String emailId) {
    final index = _allEmails.indexWhere((e) => e.id == emailId);
    if (index != -1) {
      _allEmails[index].isRead = !_allEmails[index].isRead;
      if (_config != null) {
        _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
      }
      notifyListeners();
    }
  }

  void markAsRead(String emailId) {
    final index = _allEmails.indexWhere((e) => e.id == emailId);
    if (index != -1 && !_allEmails[index].isRead) {
      _allEmails[index].isRead = true;
      if (_config != null) {
        _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
      }
      notifyListeners();
    }
  }

  void moveEmailToFolder(String emailId, FolderType targetFolder) {
    final index = _allEmails.indexWhere((e) => e.id == emailId);
    if (index != -1) {
      _allEmails[index].folder = targetFolder;
      if (_config != null) {
        _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
      }
      notifyListeners();
    }
  }

  void deleteEmail(String emailId) {
    final index = _allEmails.indexWhere((e) => e.id == emailId);
    if (index != -1) {
      if (_allEmails[index].folder == FolderType.trash) {
        _allEmails.removeAt(index);
      } else {
        _allEmails[index].folder = FolderType.trash;
      }
      if (_config != null) {
        _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
      }
      notifyListeners();
    }
  }

  // Background email dispatch with outbox & failure recovery
  EmailItem sendEmailInBackground({
    required String to,
    required String subject,
    required String body,
    List<String> attachments = const [],
  }) {
    final newEmail = EmailItem(
      id: 'email-${DateTime.now().millisecondsSinceEpoch}',
      senderName: 'Me',
      senderEmail: _currentEmail,
      recipientEmail: to,
      subject: subject.isEmpty ? '(No Subject)' : subject,
      snippet: body.length > 80 ? '${body.substring(0, 80)}...' : body,
      body: '$body\n\n--\nSent with VoidMail - Powered by VoidPanel',
      timestamp: DateTime.now(),
      isRead: true,
      isStarred: false,
      hasAttachments: attachments.isNotEmpty,
      attachmentNames: attachments,
      folder: FolderType.sent,
      avatarColor: const Color(0xFF4F46E5),
      isSendingStatus: true,
      sendFailed: false,
      accountEmail: _currentEmail,
    );

    _localSentEmails.removeWhere((e) => e.id == newEmail.id);
    _localSentEmails.insert(0, newEmail);

    _allEmails.removeWhere((e) => e.id == newEmail.id);
    _allEmails.insert(0, newEmail);
    notifyListeners();

    // Trigger async background SMTP dispatch
    _dispatchEmailSmtp(newEmail);

    return newEmail;
  }

  Future<void> _dispatchEmailSmtp(EmailItem email) async {
    if (_config != null && _config!.password.isNotEmpty) {
      try {
        final res = await ImapService.sendEmail(
          smtpHost: _config!.smtpHost,
          smtpPort: _config!.smtpPort,
          isSsl: _config!.smtpSsl,
          username: _currentEmail,
          password: _config!.password,
          recipientEmail: email.recipientEmail,
          subject: email.subject,
          body: email.body,
        );

        email.isSendingStatus = false;
        if (res['success'] == true) {
          email.sendFailed = false;
          email.sendErrorDetail = null;

          // Fire local notification on successful dispatch
          try {
            await NotificationService().showMailSentNotification(
              recipient: email.recipientEmail,
              subject: email.subject,
            );
          } catch (e) {
            debugPrint('[MailProvider] Notification notice: $e');
          }

          // Persist sent emails cache to disk
          if (_config != null) {
            _saveCachedFolderEmails(_config!.id, FolderType.sent, _allEmails);
          }

          // Attempt to append to IMAP Sent folder asynchronously
          ImapService.appendSentMessage(
            host: _config!.imapHost,
            port: _config!.imapPort,
            isSsl: _config!.imapSsl,
            username: _currentEmail,
            password: _config!.password,
            recipientEmail: email.recipientEmail,
            subject: email.subject,
            body: email.body,
          );
        } else {
          email.sendFailed = true;
          email.sendErrorDetail = res['message'] ?? 'Delivery failed';
        }
      } catch (e) {
        email.isSendingStatus = false;
        email.sendFailed = true;
        email.sendErrorDetail = e.toString();
      }
    } else {
      email.isSendingStatus = false;
      email.sendFailed = false;
    }
    notifyListeners();
  }

  void retrySendEmail(EmailItem email) {
    email.isSendingStatus = true;
    email.sendFailed = false;
    email.sendErrorDetail = null;
    notifyListeners();

    _dispatchEmailSmtp(email);
  }

  Future<Map<String, dynamic>> sendEmail({
    required String to,
    required String subject,
    required String body,
    List<String> attachments = const [],
  }) async {
    final email = sendEmailInBackground(
      to: to,
      subject: subject,
      body: body,
      attachments: attachments,
    );

    return {'success': true, 'message': 'Email queued for sending'};
  }

  // Multi-selection operations
  void toggleSelection(String id) {
    if (_selectedEmailIds.contains(id)) {
      _selectedEmailIds.remove(id);
      if (_selectedEmailIds.isEmpty) _isSelectionMode = false;
    } else {
      _selectedEmailIds.add(id);
      _isSelectionMode = true;
    }
    notifyListeners();
  }

  void _clearSelection() {
    _selectedEmailIds.clear();
    _isSelectionMode = false;
  }

  void bulkDelete() {
    for (final id in _selectedEmailIds) {
      deleteEmail(id);
    }
    _clearSelection();
  }

  void bulkMarkRead() {
    for (final id in _selectedEmailIds) {
      markAsRead(id);
    }
    _clearSelection();
  }

  void bulkArchive() {
    for (final id in _selectedEmailIds) {
      moveEmailToFolder(id, FolderType.archive);
    }
    _clearSelection();
  }

  // VoidPanel Accounts Management
  Future<void> fetchManagedAccounts() async {
    _managedAccounts = await apiService.fetchEmailAccounts(_currentDomain);
    notifyListeners();
  }

  Future<Map<String, dynamic>> createVoidPanelAccount(String username, String password) async {
    final res = await apiService.createEmailAccount(username, password);
    if (res['success'] == true) {
      await fetchManagedAccounts();
    }
    return res;
  }

  Future<void> refreshMail({bool isBackground = false}) async {
    final key = _getCacheKey(_currentFolder);
    if (!isBackground && (!_folderCache.containsKey(key) || _folderCache[key]!.isEmpty)) {
      _isLoading = true;
      notifyListeners();
    }

    if (_showUnifiedInbox) {
      // Refresh all accounts in parallel
      await _refreshAllAccounts();
    } else if (_config != null && _config!.password.isNotEmpty) {
      try {
        final realEmails = await ImapService.fetchEmails(
          host: _config!.imapHost,
          port: _config!.imapPort,
          isSsl: _config!.imapSsl,
          username: _currentEmail,
          password: _config!.password,
          folderType: _currentFolder,
        );

        // Check for new incoming unread emails in inbox and notify
        if (_currentFolder == FolderType.inbox && realEmails.isNotEmpty) {
          for (final em in realEmails) {
            if (!em.isRead && !_knownEmailIds.contains(em.id)) {
              NotificationService().showNewMailNotification(
                sender: em.senderName,
                subject: em.subject,
                snippet: em.snippet,
                accountEmail: em.accountEmail ?? _currentEmail,
              );
            }
          }
          _knownEmailIds.addAll(realEmails.map((e) => e.id));
          _saveKnownEmailIds();
        }

        _allEmails = realEmails;
        _emailsByAccount[_config!.id] = realEmails;
        // Also update inbox cache when viewing inbox
        if (_currentFolder == FolderType.inbox) {
          _inboxByAccount[_config!.id] = realEmails;
        }

        // Persist fresh emails to offline storage
        _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
      } catch (e) {
        debugPrint('IMAP refresh error: $e');
      }
    }

    // Merge locally sent emails if viewing Sent folder
    if (_currentFolder == FolderType.sent) {
      for (final localSent in _localSentEmails) {
        final matchesAccount = _showUnifiedInbox ||
            localSent.accountEmail?.toLowerCase() == _currentEmail.toLowerCase() ||
            localSent.senderEmail.toLowerCase() == _currentEmail.toLowerCase();
        if (matchesAccount) {
          final alreadyPresent = _allEmails.any((e) =>
              e.id == localSent.id ||
              (e.subject == localSent.subject && e.recipientEmail == localSent.recipientEmail));
          if (!alreadyPresent) {
            _allEmails.insert(0, localSent);
          }
        }
      }
    }

    // Save to folder cache for instant switching next time
    _folderCache[key] = List.from(_allEmails);

    _isLoading = false;
    notifyListeners();
  }

  /// Refresh all linked accounts in parallel (for Primary / unified mode)
  /// Fetches _currentFolder across ALL accounts in parallel
  Future<void> _refreshAllAccounts() async {
    final futures = <Future>[];
    final Map<String, List<EmailItem>> fetchedByAccount = {};

    for (final account in _accounts) {
      if (account.password.isNotEmpty) {
        futures.add(
          ImapService.fetchEmails(
            host: account.imapHost,
            port: account.imapPort,
            isSsl: account.imapSsl,
            username: account.email,
            password: account.password,
            folderType: _currentFolder,
          ).then((emails) {
            fetchedByAccount[account.id] = emails;
            if (_currentFolder == FolderType.inbox) {
              _inboxByAccount[account.id] = emails;
              // Check for new incoming unread emails in inbox and notify
              for (final em in emails) {
                if (!em.isRead && !_knownEmailIds.contains(em.id)) {
                  NotificationService().showNewMailNotification(
                    sender: em.senderName,
                    subject: em.subject,
                    snippet: em.snippet,
                    accountEmail: account.email,
                  );
                }
              }
              _knownEmailIds.addAll(emails.map((e) => e.id));
              _saveKnownEmailIds();
            }
            _saveCachedFolderEmails(account.id, _currentFolder, emails);
          }).catchError((e) {
            debugPrint('IMAP refresh error for ${account.email}: $e');
          }),
        );
      }
    }
    await Future.wait(futures);

    // Merge all fetched emails into _allEmails
    _allEmails = [];
    for (final emails in fetchedByAccount.values) {
      _allEmails.addAll(emails);
    }
  }
}
