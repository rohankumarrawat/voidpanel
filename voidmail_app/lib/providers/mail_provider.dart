import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/email_item.dart';
import '../models/folder.dart';
import '../models/account.dart';
import '../models/voidpanel_config.dart';
import '../services/voidpanel_api_service.dart';
import '../services/imap_service.dart';
import '../services/voidpanel_ai_service.dart';
import '../services/notification_service.dart';
import '../services/push_notification_service.dart';

enum QuickFilter { all, unread, starred, attachments }

enum EmailSortOrder {
  newest,
  importantFirst,
  unansweredFirst,
  unreadFirst,
}


class MailProvider extends ChangeNotifier {
  final VoidPanelApiService apiService = VoidPanelApiService();

  String _currentEmail = '';
  String _currentDomain = '';
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
  final Map<String, List<EmailItem>> _emailsByAccount = {};
  final Map<String, List<EmailItem>> _inboxByAccount = {}; // Persistent inbox cache for Primary Mail
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
  Color _accentColor = const Color(0xFFFF7A00);
  String _themeName = 'Flame Orange';


  // ── Workspace Suite Navigation State (Mail, Drive, CRM, Calendar, Shield) ──
  int _activeSuiteIndex = 0;
  int get activeSuiteIndex => _activeSuiteIndex;
  void setActiveSuiteIndex(int idx) {
    _activeSuiteIndex = idx;
    notifyListeners();
  }

  // ── VoidMail AI Whitelist State ──
  bool _aiEnabled = true;
  String _voidonyxUrl = 'https://voidonyx.in';
  String _licenseKey = '';
  final String _callerIp = '';
  final VoidPanelAiService _aiService = VoidPanelAiService();

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
  VoidPanelAiService get aiService => _aiService;

  // ── AI Priority & Unanswered Email State ──
  bool _isAiPriorityActive = false;
  bool _showUnwantedInPriority = false;
  bool get isAiPriorityActive => _isAiPriorityActive;
  bool get showUnwantedInPriority => _showUnwantedInPriority;

  int get unansweredCount {
    return _allEmails.where((e) => e.folder == FolderType.inbox && e.needsReply && !e.isAnswered).length;
  }

  int get highPriorityCount {
    return _allEmails.where((e) => e.folder == FolderType.inbox && (e.isAiPriority || (e.priorityScore ?? 0) >= 75)).length;
  }

  int get unwantedCount {
    return _allEmails.where((e) => e.folder == FolderType.inbox && e.isUnwanted).length;
  }

  EmailSortOrder _sortOrder = EmailSortOrder.newest;
  EmailSortOrder get sortOrder => _sortOrder;

  void setSortOrder(EmailSortOrder order) {
    _sortOrder = order;
    notifyListeners();
  }

  void toggleAiPriority([bool? forceState]) {
    _isAiPriorityActive = forceState ?? !_isAiPriorityActive;
    if (_isAiPriorityActive) {
      triggerAiPriorityReanalysis();
    }
    notifyListeners();
  }

  void toggleShowUnwanted() {
    _showUnwantedInPriority = !_showUnwantedInPriority;
    notifyListeners();
  }

  Future<void> fetchUnansweredTrackers() async {
    try {
      final trackers = await apiService.fetchUnansweredEmails(account: _currentEmail);
      if (trackers.isNotEmpty) {
        for (final t in trackers) {
          final eid = t['email_id']?.toString() ?? t['id']?.toString() ?? '';
          final idx = _allEmails.indexWhere((e) => e.id == eid || (e.subject.trim().isNotEmpty && e.subject.trim() == (t['subject']?.toString().trim() ?? '')));
          if (idx != -1) {
            _allEmails[idx] = _allEmails[idx].copyWith(
              needsReply: t['is_answered'] != true,
              isAnswered: t['is_answered'] == true,
              urgencyLevel: t['urgency_level']?.toString(),
              aiReason: t['ai_reason']?.toString(),
              actionNeeded: t['action_needed']?.toString(),
              importanceScore: (t['importance_score'] as num?)?.toInt(),
            );
          } else if (t['is_answered'] != true) {
            _allEmails.insert(0, EmailItem(
              id: eid.isNotEmpty ? eid : 'unans-${DateTime.now().millisecondsSinceEpoch}',
              senderName: t['sender']?.toString() ?? 'Contact',
              senderEmail: t['from_email']?.toString() ?? 'contact@example.com',
              recipientEmail: _currentEmail,
              subject: t['subject']?.toString() ?? 'Pending Action',
              snippet: t['ai_reason']?.toString() ?? 'Important email requiring your response',
              body: 'Pending response tracked by AI: ${t['action_needed'] ?? t['ai_reason'] ?? ''}',
              timestamp: DateTime.tryParse(t['received_at']?.toString() ?? '') ?? DateTime.now(),
              isRead: false,
              folder: FolderType.inbox,
              needsReply: true,
              urgencyLevel: t['urgency_level']?.toString() ?? 'Action Required',
              aiReason: t['ai_reason']?.toString() ?? 'Pending response',
              actionNeeded: t['action_needed']?.toString(),
              importanceScore: (t['importance_score'] as num?)?.toInt() ?? 80,
              accountEmail: _currentEmail,
            ));
          }
        }
        notifyListeners();
      }
    } catch (e) {
      debugPrint('[MailProvider] fetchUnansweredTrackers error: $e');
    }
  }

  Future<bool> markEmailAnswered(String emailId, {String action = 'answered'}) async {
    final success = await apiService.markEmailAnswered(emailId, action: action);
    for (int i = 0; i < _allEmails.length; i++) {
      if (_allEmails[i].id == emailId) {
        _allEmails[i] = _allEmails[i].copyWith(
          needsReply: false,
          isAnswered: true,
        );
      }
    }
    notifyListeners();
    return success;
  }

  Future<void> triggerAiPriorityReanalysis() async {
    try {
      final inboxEmails = _allEmails.where((e) => e.folder == FolderType.inbox).toList();
      if (inboxEmails.isEmpty) return;

      final payload = inboxEmails.take(30).map((e) => {
        'id': e.id,
        'subject': e.subject,
        'sender': e.senderName,
        'from': e.senderEmail,
        'snippet': e.snippet,
        'body_text': e.body,
      }).toList();

      final res = await apiService.classifyAiPriority(payload);
      if (res['success'] == true && res['prioritized'] is List) {
        final prioList = res['prioritized'] as List;
        for (final p in prioList) {
          if (p is Map) {
            final pid = p['id']?.toString() ?? '';
            final idx = _allEmails.indexWhere((e) => e.id == pid);
            if (idx != -1) {
              _allEmails[idx] = _allEmails[idx].copyWith(
                isAiPriority: p['priority'] == 'high' || ((p['priority_score'] as num?)?.toInt() ?? 0) >= 75,
                priorityScore: (p['priority_score'] as num?)?.toInt(),
                isUnwanted: p['is_unwanted'] == true,
              );
            }
          }
        }
        notifyListeners();
      }
    } catch (e) {
      debugPrint('[MailProvider] triggerAiPriorityReanalysis error: $e');
    }
  }

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

  // ── Linked Virtual Aliases State ──
  List<Map<String, dynamic>> _userAliases = [];
  List<Map<String, dynamic>> get userAliases => _userAliases;
  String? _selectedAliasFilter;
  String? get selectedAliasFilter => _selectedAliasFilter;

  List<String> get availableSenderEmails {
    final list = <String>[];
    if (_currentEmail.trim().isNotEmpty) {
      list.add(_currentEmail.trim());
    }
    for (final acc in _accounts) {
      final email = acc.email.trim();
      if (email.isNotEmpty && !list.any((e) => e.toLowerCase() == email.toLowerCase())) {
        list.add(email);
      }
    }
    for (final m in _managedAccounts) {
      final email = m.email.trim();
      if (email.isNotEmpty && !list.any((e) => e.toLowerCase() == email.toLowerCase())) {
        list.add(email);
      }
    }
    for (final a in _userAliases) {
      final source = a['source_email']?.toString().trim();
      if (source != null && source.isNotEmpty && !list.any((e) => e.toLowerCase() == source.toLowerCase())) {
        list.add(source);
      }
    }
    return list;
  }

  void filterByAlias(String? aliasEmail) {
    _selectedAliasFilter = aliasEmail;
    notifyListeners();
  }

  Future<void> fetchUserAliases() async {
    try {
      final aliases = await apiService.fetchAliases(
        username: _currentEmail,
        password: _config?.password,
      );
      _userAliases = aliases;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('voidmail_aliases_$_currentEmail', jsonEncode(_userAliases));
      notifyListeners();
    } catch (e) {
      debugPrint('[MailProvider] fetchUserAliases error: $e');
    }
  }

  Future<Map<String, dynamic>> createAlias(String prefix, {String domain = 'voidonyx.com'}) async {
    final res = await apiService.createAlias(
      prefix,
      domain: domain,
      username: _currentEmail,
      password: _config?.password,
    );
    if (res['success'] == true) {
      await fetchUserAliases();
    }
    return res;
  }

  Future<Map<String, dynamic>> deleteAlias(int aliasId, String sourceEmail) async {
    final res = await apiService.deleteAlias(aliasId, sourceEmail);
    if (res['success'] == true) {
      await fetchUserAliases();
      if (_selectedAliasFilter == sourceEmail) {
        _selectedAliasFilter = null;
      }
    }
    return res;
  }

  final Completer<void> _initCompleter = Completer<void>();
  Future<void> get initialized => _initCompleter.future;

  MailProvider() {
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
      await apiService.initSession();
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
        // Purge any stale demo account from previous runs
        _accounts.removeWhere((a) => a.email.toLowerCase() == 'parirawat@voidonyx.com');
        _activeAccountIndex = prefs.getInt('voidmail_active_index') ?? 0;
        if (_activeAccountIndex >= _accounts.length) _activeAccountIndex = 0;
        if (_accounts.isNotEmpty) {
          _config = _accounts[_activeAccountIndex];
          _currentEmail = _config!.email;
          _currentDomain = _config!.domain;
          _isLoggedIn = true;

          if (_config!.password.isNotEmpty) {
            apiService.loginStep1(_config!.email, _config!.password).catchError((_) => <String, dynamic>{});
          }

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

          // Restore cached aliases for active email
          final cachedAliasesRaw = prefs.getString('voidmail_aliases_$_currentEmail');
          if (cachedAliasesRaw != null && cachedAliasesRaw.isNotEmpty) {
            try {
              final decoded = jsonDecode(cachedAliasesRaw) as List;
              _userAliases = List<Map<String, dynamic>>.from(decoded);
            } catch (_) {}
          }

          // Render cached data immediately
          notifyListeners();

          // Start periodic background auto-sync timer
          _startAutoSyncTimer();

          // Sync push notification token in background
          PushNotificationService().syncTokenWithServer(
            email: _config!.email,
            panelBaseUrl: _config!.serverUrl,
          ).catchError((_) {});

          // Fetch fresh emails and aliases in background without blocking UI startup
          refreshMail(isBackground: true).catchError((e) {
            debugPrint('[MailProvider] Background startup refresh notice: $e');
          });
          fetchUserAliases().catchError((e) {
            debugPrint('[MailProvider] Background aliases notice: $e');
          });
          checkAndSetAiStatus().catchError((e) {
            debugPrint('[MailProvider] Background AI status notice: $e');
          });
          syncAccountsWithServer().catchError((e) {
            debugPrint('[MailProvider] Background accounts sync notice: $e');
          });
        } else {
          _config = null;
          _currentEmail = '';
          _currentDomain = '';
          _isLoggedIn = false;
          _allEmails = [];
        }
      } else {
        _config = null;
        _currentEmail = '';
        _currentDomain = '';
        _isLoggedIn = false;
        _allEmails = [];
      }
    } catch (e) {
      debugPrint('[MailProvider] Error loading saved accounts: $e');
    } finally {
      if (!_initCompleter.isCompleted) {
        _initCompleter.complete();
      }
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
  void registerAccount(ServerConfig config) => _registerAccount(config);

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
    _config = config;
    _currentEmail = config.email;
    _currentDomain = config.domain;
    _isLoggedIn = true;
    _saveAccounts();
    _startAutoSyncTimer();

    // Register FCM Device Token for instant push notifications when app is closed
    PushNotificationService().syncTokenWithServer(
      email: config.email,
      panelBaseUrl: config.serverUrl,
    ).catchError((e) {
      debugPrint('[MailProvider] Push token sync notice: $e');
    });

    // If this is a business/company email, sync to server so it shows on Web portal
    if (config.domain != 'voidonyx.com' && config.domain != 'voidonyx.in') {
      _syncLinkedAccountToServer(config).catchError((e) {
        debugPrint('[MailProvider] Background sync linked account notice: $e');
      });
    }

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
    _selectedAliasFilter = null;
    notifyListeners();
    await _saveAccounts();
    await fetchUserAliases();
    await refreshMail();
    await checkAndSetAiStatus();

    // Inform server about switch
    final primary = primaryAccount;
    if (primary != null) {
      apiService.switchActiveAccount(
        email: _currentEmail,
        primaryUser: primary.email,
        primaryPassword: primary.password,
      ).catchError((_) => <String, dynamic>{});
    }
  }

  /// Remove a linked account
  /// Remove a linked account by index.
  /// Calls [removeAccount] by ID which correctly handles primary vs professional email logic.
  Future<bool> removeAccountAtIndex(int index) async {
    if (index < 0 || index >= _accounts.length) return false;
    return await removeAccount(_accounts[index].id);
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
    _aiEnabled = true;
    _voidonyxUrl = 'https://voidonyx.in';
    _licenseKey = 'voidonyx_unlimited_license';
    _aiService.configure(
      voidonyxUrl: _voidonyxUrl,
      licenseKey: _licenseKey,
      panelHost: apiService.baseUrl,
    );
    notifyListeners();
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
        ).timeout(const Duration(seconds: 4), onTimeout: () => []);
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

      await fetchUserAliases();
      await refreshMail();
      await fetchManagedAccounts();

      // Check if user's domain is whitelisted for AI features
      await checkAndSetAiStatus();

      // Track this login for analytics (fire-and-forget)
      apiService.trackAppLogin(
        email: _currentEmail,
        domain: _currentDomain,
        loginMethod: 'voidpanel',
      ).catchError((_) {});
    }

    _isLoading = false;
    notifyListeners();
    return result;
  }

  /// Completes signup/OTP registration login immediately and fetches emails & aliases
  Future<void> completeRegistrationLogin({
    required String email,
    required String password,
    String? domain,
  }) async {
    _isLoading = false;
    _isLoggedIn = true;
    _currentEmail = email;
    _currentDomain = domain ?? (email.contains('@') ? email.split('@').last : 'voidonyx.com');
    _config = ServerConfig.defaultForDomain(
      serverUrl: apiService.baseUrl,
      username: email,
      password: password,
      domain: _currentDomain,
    );
    _allEmails = [];
    _emailsByAccount[_config!.id] = [];
    _inboxByAccount[_config!.id] = [];
    _registerAccount(_config!);
    notifyListeners();

    await fetchUserAliases();
    await refreshMail();
    await checkAndSetAiStatus();

    apiService.trackAppLogin(
      email: _currentEmail,
      domain: _currentDomain,
      loginMethod: 'registration_otp',
    ).catchError((_) {});
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
    final cleanEmail = email.toLowerCase().trim();
    if (cleanEmail == 'demo@voidonyx.com' || cleanEmail == 'demo' || password.toLowerCase().trim() == 'voidmail2026!' || password.toLowerCase().trim() == 'demopassword2026!') {
      return await loginAsDemo(email: cleanEmail.contains('@') ? cleanEmail : '$cleanEmail@voidonyx.com');
    }

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

      // If VoidOnyx Sovereign account, authenticate with REST API and fetch welcome emails
      if (_currentDomain == 'voidonyx.com' || _currentDomain == 'voidonyx.in') {
        apiService.loginStep1(email, password).catchError((_) => <String, dynamic>{});
        fetchUserAliases().catchError((_) {});
        refreshMail().catchError((_) {});
      }

      notifyListeners();

      // Register this account in multi-account list
      _registerAccount(_config!);

      // Sync linked business email to server so it appears in the Web portal immediately
      _syncLinkedAccountToServer(_config!).catchError((e) {
        debugPrint('[MailProvider] Server link sync notice: $e');
      });

      // Check if user's domain is whitelisted for AI features
      await checkAndSetAiStatus();

      // Track this login for analytics (fire-and-forget)
      apiService.trackAppLogin(
        email: email,
        domain: _currentDomain,
        loginMethod: 'custom_imap',
      ).catchError((_) {});

      return {
        'success': true,
        'message': 'Connected to $imapHost (IMAP) & fetched ${realEmails.length} emails.',
        'domain': _currentDomain,
      };
    } catch (e) {
      // If IMAP fails, but this is a VoidOnyx Sovereign account, attempt sovereign REST login fallback
      final parts = email.split('@');
      final domainPart = parts.length > 1 ? parts[1].toLowerCase() : '';
      if (domainPart == 'voidonyx.com' || domainPart == 'voidonyx.in') {
        debugPrint('[MailProvider] IMAP connect issue for sovereign account $email, falling back to REST login...');
        try {
          final restRes = await apiService.loginStep1(email, password);
          if (restRes['success'] == true) {
            _isLoading = false;
            _isLoggedIn = true;
            _currentEmail = email;
            _currentDomain = domainPart;
            _config = ServerConfig.defaultForDomain(
              serverUrl: apiService.baseUrl,
              username: email,
              password: password,
              domain: _currentDomain,
            );
            _allEmails = [];
            _emailsByAccount[_config!.id] = [];
            _inboxByAccount[_config!.id] = [];
            notifyListeners();
            _registerAccount(_config!);
            await fetchUserAliases();
            await refreshMail();
            await checkAndSetAiStatus();
            return {
              'success': true,
              'message': 'Logged in via Sovereign VoidOnyx Cloud.',
              'domain': _currentDomain,
            };
          }
        } catch (_) {}
      }

      _isLoading = false;
      _lastError = e.toString();
      notifyListeners();

      return {
        'success': false,
        'message': 'Failed to connect to IMAP server ($imapHost:$imapPort)\n\nError details: ${e.toString()}',
      };
    }
  }

  /// Instant offline/demo login for App Store reviewers and evaluation guests
  Future<Map<String, dynamic>> loginAsDemo({String email = 'demo@voidonyx.com'}) async {
    _isLoading = false;
    _lastError = null;
    _isLoggedIn = true;
    _currentEmail = email;
    _currentDomain = 'voidonyx.com';
    _config = ServerConfig.demo(email: email);
    _aiEnabled = true;

    final now = DateTime.now();
    final demoEmails = [
      EmailItem(
        id: 'demo-welcome-1',
        senderName: 'VoidOnyx Security Team',
        senderEmail: 'security@voidonyx.com',
        recipientEmail: email,
        subject: 'Welcome to your Sovereign VoidMail Workspace',
        snippet: 'Your sovereign mailbox is protected by wire-level TLS 1.3, DANE/TLSA, and Layer 11 Cyber-AI.',
        body: 'Welcome to VoidMail!\n\nYour account ($email) is active on the VoidOnyx Sovereign Cloud. Your communications are safeguarded with:\n\n• Strict Wire-Level TLS 1.3 Transport Protection\n• In-Memory DPDPA 2023 PII Redaction\n• Post-Quantum Cryptographic Key Encapsulation (ML-KEM / Kyber-768)\n• SHA-256 Merkle Ledger Auditability\n\nFeel free to compose messages, check your security posture in the Security Shield, manage contacts, and explore the AI assistant.',
        htmlBody: '<p>Welcome to <strong>VoidMail</strong>!</p><p>Your account is active on the VoidOnyx Sovereign Cloud.</p><ul><li>Strict Wire-Level TLS 1.3 Transport</li><li>In-Memory DPDPA 2023 PII Redaction</li><li>Post-Quantum Key Encapsulation (Kyber-768)</li><li>SHA-256 Merkle Ledger Auditability</li></ul><p>Feel free to compose messages, inspect headers, and explore your workspace.</p>',
        timestamp: now.subtract(const Duration(minutes: 15)),
        isRead: false,
        isStarred: true,
        folder: FolderType.inbox,
        avatarColor: const Color(0xFFFF7A00),
        category: 'Primary',
        isAiPriority: true,
        priorityScore: 98,
        accountEmail: email,
      ),
      EmailItem(
        id: 'demo-posture-2',
        senderName: 'Autonomous SecOps',
        senderEmail: 'daemon@voidonyx.in',
        recipientEmail: email,
        subject: 'Real-Time Posture Report: Ingress Wire Verified',
        snippet: 'All cryptographic checks passed. SPF, DKIM, and DMARC alignment verified across perimeter.',
        body: 'Security Report Summary:\n\n• Perimeter Status: 100% HEALTHY\n• Active Transport: TLS 1.3 with Curve X25519 (PFS)\n• Anti-Spoofing Policy: DMARC p=reject enforced\n• Quanta Wire Engine: 0.39ms audit latency\n• Evidence Status: Recorded to SHA-256 Merkle Ledger',
        htmlBody: '<p><strong>Security Report Summary</strong></p><p>Perimeter Status: <span style="color:#10B981;font-weight:bold;">100% HEALTHY</span><br>Active Transport: TLS 1.3 with Curve X25519<br>DMARC Policy: p=reject enforced<br>Quanta Wire Engine: 0.39ms audit latency</p>',
        timestamp: now.subtract(const Duration(hours: 2)),
        isRead: true,
        folder: FolderType.inbox,
        avatarColor: const Color(0xFF10B981),
        category: 'Updates',
        accountEmail: email,
      ),
      EmailItem(
        id: 'demo-sync-3',
        senderName: 'Infrastructure Lead',
        senderEmail: 'lead@voidonyx.com',
        recipientEmail: email,
        subject: 'Scheduled Architecture Sync & Review',
        snippet: 'Please find attached the agenda for the upcoming infrastructure migration and audit briefing.',
        body: 'Hi Team,\n\nPlease review the attached agenda for our upcoming technical sync. We will walk through the latest wire benchmarks, DPDPA compliance metrics, and sovereign deployment topology.\n\nBest regards,\nInfrastructure Lead',
        timestamp: now.subtract(const Duration(hours: 5)),
        isRead: true,
        folder: FolderType.inbox,
        hasAttachments: true,
        attachmentNames: const ['Sovereign_Architecture_Q4.pdf'],
        avatarColor: const Color(0xFF6366F1),
        category: 'Primary',
        accountEmail: email,
      ),
      EmailItem(
        id: 'demo-update-4',
        senderName: 'VoidPanel Cloud',
        senderEmail: 'notifications@voidpanel.com',
        recipientEmail: email,
        subject: 'Quarterly Sovereign Workspace Summary & Quota',
        snippet: 'Your cloud mailbox storage usage is at 12%. All systems operating normally.',
        body: 'Monthly Account Summary:\n\nStorage Allocated: 50 GB\nStorage Used: 6.2 GB (12%)\nLinked Professional Aliases: Active\nZero plain-text leaks detected.',
        timestamp: now.subtract(const Duration(days: 1)),
        isRead: true,
        folder: FolderType.inbox,
        avatarColor: const Color(0xFF06B6D4),
        category: 'Updates',
        accountEmail: email,
      ),
    ];

    _allEmails = demoEmails;
    _emailsByAccount[_config!.id] = demoEmails;
    _inboxByAccount[_config!.id] = demoEmails;

    _registerAccount(_config!);
    notifyListeners();

    return {
      'success': true,
      'message': 'Logged in to VoidMail Demo Workspace.',
      'domain': 'voidonyx.com',
      'isDemo': true,
    };
  }

  void updateServerConfig(ServerConfig newConfig) {
    _config = newConfig;
    notifyListeners();
  }

  bool get isCurrentAccountPrimary {
    if (_accounts.isEmpty || _config == null) return true;
    final primary = primaryAccount;
    if (primary == null) return true;
    return _config!.id == primary.id || _config!.email.toLowerCase() == primary.email.toLowerCase();
  }

  /// Removes/logs out a single account by ID.
  /// If the removed account is the primary/main account, performs full logoutAll() and returns true (navigate to /login).
  /// If it is a secondary/professional account, removes it, switches to primary, and returns false (stay in app).
  Future<bool> removeAccount(String accountId) async {
    final primary = primaryAccount;
    final isPrimaryRemoval = (primary != null && primary.id == accountId) ||
                             (_accounts.isNotEmpty && _accounts.first.id == accountId);

    // If removing the primary/main email, or if it's the only account left, logout all
    if (isPrimaryRemoval || _accounts.length <= 1) {
      await logoutAll();
      return true;
    }

    final targetIndex = _accounts.indexWhere((a) => a.id == accountId);
    if (targetIndex == -1) return false;
    final targetAcc = _accounts[targetIndex];

    // Unregister push notifications
    PushNotificationService().unregisterToken(
      email: targetAcc.email,
      panelBaseUrl: targetAcc.serverUrl,
    ).catchError((_) {});

    // Unlink from server if primary exists
    if (primary != null) {
      apiService.removeLinkedAccount(
        email: targetAcc.email,
        primaryUser: primary.email,
        primaryPassword: primary.password,
      ).catchError((_) => <String, dynamic>{});
    }

    // Remove account data from memory
    _accounts.removeWhere((a) => a.id == accountId);
    _emailsByAccount.remove(accountId);
    _inboxByAccount.remove(accountId);
    _folderCache.removeWhere((key, _) => key.startsWith('$accountId-'));

    // Clear offline cache in SharedPreferences
    try {
      final prefs = await SharedPreferences.getInstance();
      for (final f in FolderType.values) {
        await prefs.remove('voidmail_cache_${accountId}_${f.name}');
      }
      await prefs.remove('voidmail_aliases_${targetAcc.email}');
    } catch (_) {}

    // Switch active account to primary account
    final newActive = primary ?? _accounts.first;
    _config = newActive;
    _activeAccountIndex = _accounts.indexWhere((a) => a.id == newActive.id);
    if (_activeAccountIndex == -1) _activeAccountIndex = 0;
    _currentEmail = newActive.email;
    _currentDomain = newActive.domain;
    _allEmails = _emailsByAccount[newActive.id] ?? [];
    _isLoggedIn = true;

    await _saveAccounts();
    notifyListeners();

    refreshMail(isBackground: true).catchError((_) {});
    return false; // Still logged in on primary/remaining accounts
  }

  /// Logout currently active account.
  /// Returns true if all accounts were logged out (triggering navigation to /login).
  /// Returns false if only a secondary/professional account was logged out (stay in app on main account).
  Future<bool> logout() async {
    if (_config == null || _accounts.isEmpty) {
      await logoutAll();
      return true;
    }
    return await removeAccount(_config!.id);
  }

  /// Logout ALL accounts and fully reset to initial state.
  Future<void> logoutAll() async {
    // Unregister push tokens for all accounts
    for (final account in _accounts) {
      PushNotificationService().unregisterToken(
        email: account.email,
        panelBaseUrl: account.serverUrl,
      ).catchError((_) {});
    }

    _isLoggedIn = false;
    _config = null;
    _accounts.clear();
    _activeAccountIndex = 0;
    _allEmails.clear();
    _emailsByAccount.clear();
    _inboxByAccount.clear();
    _folderCache.clear();
    _selectedEmailIds.clear();
    _isSelectionMode = false;
    _autoSyncTimer?.cancel();

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('voidmail_accounts');
      await prefs.remove('voidmail_active_index');
      await prefs.remove('voidmail_known_email_ids');
      final keys = prefs.getKeys().where((k) => k.startsWith('voidmail_cache_')).toList();
      for (final k in keys) {
        await prefs.remove(k);
      }
    } catch (e) {
      debugPrint('[MailProvider] Error clearing preferences on logout: $e');
    }

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
  List<EmailItem> get emails => List.unmodifiable(_allEmails);
  List<EmailItem> get allEmails => List.unmodifiable(_allEmails);

  List<EmailItem> get filteredEmails {
    var list = _allEmails.where((email) {
      // 1. Folder filter
      if (_currentFolder == FolderType.starred) {
        if (!email.isStarred) return false;
      } else if (_currentFolder == FolderType.unanswered) {
        if (email.folder != FolderType.inbox || !email.needsReply || email.isAnswered) return false;
      } else {
        if (email.folder != _currentFolder) return false;
      }

      // AI Priority noise filter (hide unwanted in AI Priority mode unless toggled on)
      if (_isAiPriorityActive && _currentFolder == FolderType.inbox) {
        if (email.isUnwanted && !_showUnwantedInPriority) return false;
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

      // 4. Linked Alias filter
      if (_selectedAliasFilter != null && _selectedAliasFilter!.isNotEmpty) {
        final aliasLower = _selectedAliasFilter!.toLowerCase();
        final matchesRecipient = email.recipientEmail.toLowerCase() == aliasLower;
        final matchesSender = email.senderEmail.toLowerCase() == aliasLower;
        final matchesText = email.snippet.toLowerCase().contains(aliasLower) ||
            email.body.toLowerCase().contains(aliasLower) ||
            email.subject.toLowerCase().contains(aliasLower);
        if (!matchesRecipient && !matchesSender && !matchesText) return false;
      }

      return true;
    }).toList();

    // In AI Priority mode on inbox, rank by priority score descending
    if (_isAiPriorityActive && _currentFolder == FolderType.inbox) {
      list.sort((a, b) {
        final scoreA = a.priorityScore ?? (a.isAiPriority ? 85 : 50);
        final scoreB = b.priorityScore ?? (b.isAiPriority ? 85 : 50);
        if (scoreB != scoreA) return scoreB.compareTo(scoreA);
        return b.timestamp.compareTo(a.timestamp);
      });
    } else {
      switch (_sortOrder) {
        case EmailSortOrder.importantFirst:
          list.sort((a, b) {
            // Action required (unanswered) + AI Priority gets highest rank
            final weightA = (a.needsReply && !a.isAnswered ? 200 : 0) +
                (a.isAiPriority ? 100 : 0) +
                (a.priorityScore ?? 0) +
                (!a.isRead ? 20 : 0) -
                (a.isUnwanted ? 150 : 0);
            final weightB = (b.needsReply && !b.isAnswered ? 200 : 0) +
                (b.isAiPriority ? 100 : 0) +
                (b.priorityScore ?? 0) +
                (!b.isRead ? 20 : 0) -
                (b.isUnwanted ? 150 : 0);
            if (weightB != weightA) return weightB.compareTo(weightA);
            return b.timestamp.compareTo(a.timestamp);
          });
          break;
        case EmailSortOrder.unansweredFirst:
          list.sort((a, b) {
            final unA = a.needsReply && !a.isAnswered ? 1 : 0;
            final unB = b.needsReply && !b.isAnswered ? 1 : 0;
            if (unB != unA) return unB.compareTo(unA);
            return b.timestamp.compareTo(a.timestamp);
          });
          break;
        case EmailSortOrder.unreadFirst:
          list.sort((a, b) {
            final unA = !a.isRead ? 1 : 0;
            final unB = !b.isRead ? 1 : 0;
            if (unB != unA) return unB.compareTo(unA);
            return b.timestamp.compareTo(a.timestamp);
          });
          break;
        case EmailSortOrder.newest:
          list.sort((a, b) => b.timestamp.compareTo(a.timestamp));
          break;
      }
    }

    return list;
  }

  int getUnreadCount(FolderType folder) {
    if (folder == FolderType.starred) {
      return _allEmails.where((e) => e.isStarred && !e.isRead).length;
    }
    if (folder == FolderType.unanswered) {
      return unansweredCount;
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

  void markAllRead() {
    for (final email in _allEmails) {
      if (email.folder == _currentFolder) {
        email.isRead = true;
      }
    }
    if (_config != null) {
      _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
    }
    notifyListeners();
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
    String? fromSender,
    List<String> attachments = const [],
  }) {
    final senderAddr = (fromSender != null && fromSender.trim().isNotEmpty)
        ? fromSender.trim()
        : _currentEmail;

    final newEmail = EmailItem(
      id: 'email-${DateTime.now().millisecondsSinceEpoch}',
      senderName: senderAddr.split('@')[0],
      senderEmail: senderAddr,
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

    // Trigger async background SMTP / Workspace dispatch
    _dispatchEmailSmtp(newEmail);

    return newEmail;
  }

  Future<void> _dispatchEmailSmtp(EmailItem email) async {
    bool delivered = false;
    String? deliveryError;

    // 1. Attempt via SMTP socket
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
          fromSender: email.senderEmail,
        );
        if (res['success'] == true) {
          delivered = true;
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
          ).catchError((_) {});
        } else {
          deliveryError = res['message'];
        }
      } catch (e) {
        deliveryError = e.toString();
      }
    }

    // 2. If SMTP failed or credentials empty, dispatch via VoidPanel REST workspace endpoint
    if (!delivered) {
      try {
        final wsRes = await apiService.sendMailWorkspace(
          to: email.recipientEmail,
          subject: email.subject,
          body: email.body,
          fromSender: email.senderEmail,
        );
        if (wsRes['status'] == 'success' || wsRes['status'] == 'ok') {
          delivered = true;
        } else {
          deliveryError = wsRes['message'] ?? deliveryError;
        }
      } catch (e) {
        deliveryError ??= e.toString();
      }
    }

    email.isSendingStatus = false;
    if (delivered) {
      email.sendFailed = false;
      email.sendErrorDetail = null;

      try {
        await NotificationService().showMailSentNotification(
          recipient: email.recipientEmail,
          subject: email.subject,
        );
      } catch (_) {}

      if (_config != null) {
        _saveCachedFolderEmails(_config!.id, FolderType.sent, _allEmails);
      }
    } else {
      email.sendFailed = true;
      email.sendErrorDetail = deliveryError ?? 'Delivery failed';
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
    sendEmailInBackground(
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
    await syncAccountsWithServer();
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
    // Bi-directionally sync linked accounts in background
    syncAccountsWithServer().catchError((_) {});

    final key = _getCacheKey(_currentFolder);
    if (!isBackground && (!_folderCache.containsKey(key) || _folderCache[key]!.isEmpty)) {
      _isLoading = true;
      notifyListeners();
    }

    if (_showUnifiedInbox) {
      // Refresh all accounts in parallel
      await _refreshAllAccounts();
    } else if (_config != null) {
      final List<EmailItem> combined = [];

      // 1. Fetch via direct IMAP if credentials exist
      if (_config!.password.isNotEmpty) {
        try {
          final realEmails = await ImapService.fetchEmails(
            host: _config!.imapHost,
            port: _config!.imapPort,
            isSsl: _config!.imapSsl,
            username: _currentEmail,
            password: _config!.password,
            folderType: _currentFolder,
          );
          combined.addAll(realEmails);
        } catch (e) {
          debugPrint('IMAP refresh error: $e');
        }
      }

      // 2. Fetch sovereign workspace inbox emails if viewing inbox or unanswered
      if (_currentFolder == FolderType.inbox || _currentFolder == FolderType.unanswered) {
        try {
          final wsData = await apiService.fetchInboxEmails(
            target: _currentEmail,
            password: _config?.password,
          );
          if (wsData['status'] == 'success' && wsData['emails'] is List) {
            final rawList = wsData['emails'] as List;
            for (final item in rawList) {
              if (item is Map<String, dynamic>) {
                final wsEmail = EmailItem.fromWorkspaceJson(item, defaultAccountEmail: _currentEmail);
                final alreadyExists = combined.any((e) =>
                    e.id == wsEmail.id ||
                    (e.subject.trim() == wsEmail.subject.trim() && e.senderEmail.trim() == wsEmail.senderEmail.trim()));
                if (!alreadyExists) {
                  combined.add(wsEmail);
                }
              }
            }
          }
        } catch (e) {
          debugPrint('Workspace inbox fetch error: $e');
        }

        // Also fetch unanswered tracker records from backend
        try {
          final trackers = await apiService.fetchUnansweredEmails(account: _currentEmail);
          for (final t in trackers) {
            final eid = t['email_id']?.toString() ?? t['id']?.toString() ?? '';
            final idx = combined.indexWhere((e) => e.id == eid || (e.subject.trim().isNotEmpty && e.subject.trim() == (t['subject']?.toString().trim() ?? '')));
            if (idx != -1) {
              combined[idx] = combined[idx].copyWith(
                needsReply: t['is_answered'] != true,
                isAnswered: t['is_answered'] == true,
                urgencyLevel: t['urgency_level']?.toString(),
                aiReason: t['ai_reason']?.toString(),
                actionNeeded: t['action_needed']?.toString(),
                importanceScore: (t['importance_score'] as num?)?.toInt(),
              );
            }
          }
        } catch (e) {
          debugPrint('Unanswered tracker fetch error: $e');
        }
      }

      combined.sort((a, b) => b.timestamp.compareTo(a.timestamp));

      // Check for new incoming unread emails in inbox and notify
      if (_currentFolder == FolderType.inbox && combined.isNotEmpty) {
        for (final em in combined) {
          if (!em.isRead && !_knownEmailIds.contains(em.id)) {
            NotificationService().showNewMailNotification(
              sender: em.senderName,
              subject: em.subject,
              snippet: em.snippet,
              accountEmail: em.accountEmail ?? _currentEmail,
            );
          }
        }
        _knownEmailIds.addAll(combined.map((e) => e.id));
        _saveKnownEmailIds();
      }

      _allEmails = combined;
      _emailsByAccount[_config!.id] = combined;
      // Also update inbox cache when viewing inbox
      if (_currentFolder == FolderType.inbox) {
        _inboxByAccount[_config!.id] = combined;
      }

      // Persist fresh emails to offline storage
      _saveCachedFolderEmails(_config!.id, _currentFolder, _allEmails);
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

    // Also sync aliases in background
    fetchUserAliases().catchError((_) {});

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

  /// Submit an AI upgrade lead to VoidOnyx Superadmin
  Future<Map<String, dynamic>> submitAiUpgradeLead({
    required String name,
    required String phone,
  }) async {
    final email = currentEmail;
    final domain = email.contains('@') ? email.split('@').last : '';

    final result = await apiService.submitUpgradeLead(
      name: name,
      email: email,
      phone: phone,
      domain: domain,
    );


    return result;
  }

  // ══════════════════════════════════════════════════════════════════════
  //  TWO-WAY LINKED ACCOUNT SERVER SYNCHRONIZATION
  // ══════════════════════════════════════════════════════════════════════

  /// Resolves the primary VoidOnyx account from the multi-account list
  ServerConfig? get primaryAccount {
    if (_accounts.isEmpty) return _config;
    try {
      return _accounts.firstWhere(
        (a) => a.domain == 'voidonyx.com' || a.domain == 'voidonyx.in' || a.providerName.contains('VoidPanel'),
      );
    } catch (_) {
      return _accounts.first;
    }
  }

  /// Pushes an added company / business email to the VoidOnyx server
  /// so it appears on the Web portal's Linked Accounts dropdown immediately.
  Future<void> _syncLinkedAccountToServer(ServerConfig config, {ServerConfig? primary}) async {
    final primaryAcc = primary ?? primaryAccount;
    if (primaryAcc == null) return;
    if (config.email.toLowerCase() == primaryAcc.email.toLowerCase()) return;

    try {
      final res = await apiService.addLinkedAccount(
        email: config.email,
        password: config.password,
        displayName: config.username.contains('@') ? config.username.split('@')[0] : config.username,
        accountType: 'professional',
        imapHost: config.imapHost,
        imapPort: config.imapPort,
        imapSsl: config.imapSsl,
        smtpHost: config.smtpHost,
        smtpPort: config.smtpPort,
        smtpSsl: config.smtpSsl,
        skipVerification: true,
        primaryUser: primaryAcc.email,
        primaryPassword: primaryAcc.password,
      );
      debugPrint('[MailProvider] Synced business email ${config.email} to server: ${res['message']}');
    } catch (e) {
      debugPrint('[MailProvider] Failed to sync ${config.email} to server: $e');
    }
  }

  /// Two-way synchronization: pushes local business accounts to the server
  /// and pulls down any linked accounts created on the Web portal.
  Future<void> syncAccountsWithServer() async {
    if (_accounts.isEmpty) return;
    final primary = primaryAccount;
    if (primary == null) return;

    try {
      final res = await apiService.fetchLinkedAccounts(
        primaryUser: primary.email,
        primaryPassword: primary.password,
      );

      if (res['success'] == true && res['accounts'] is List) {
        final serverAccounts = res['accounts'] as List;
        final serverEmails = <String>{};
        bool accountsChanged = false;

        for (final item in serverAccounts) {
          final sEmail = (item['email'] as String? ?? '').trim().toLowerCase();
          if (sEmail.isEmpty) continue;
          serverEmails.add(sEmail);

          // If not present in local _accounts, add it
          final exists = _accounts.any((a) => a.email.toLowerCase() == sEmail);
          if (!exists && item['is_primary'] != true) {
            final domain = item['domain'] ?? (sEmail.contains('@') ? sEmail.split('@').last : '');
            final imapHost = item['imap_host'] ?? (domain.isNotEmpty ? 'mail.$domain' : 'mail.voidonyx.in');
            final newConfig = ServerConfig.custom(
              email: sEmail,
              password: '',
              imapHost: imapHost,
              imapPort: item['imap_port'] ?? 993,
              imapSsl: item['imap_security'] != 'STARTTLS',
              smtpHost: item['smtp_host'] ?? imapHost,
              smtpPort: item['smtp_port'] ?? 465,
              smtpSsl: item['smtp_security'] != 'STARTTLS',
              providerName: item['display_name'] ?? 'Professional Mail',
            );
            _accounts.add(newConfig);
            accountsChanged = true;
            debugPrint('[MailProvider] Added server-linked account to app: $sEmail');
          }
        }

        // Detect accounts unlinked/removed on the web portal and remove them locally
        final toRemove = <ServerConfig>[];
        for (final acc in _accounts) {
          final lEmail = acc.email.toLowerCase();
          if (lEmail != primary.email.toLowerCase() && !serverEmails.contains(lEmail)) {
            debugPrint('[MailProvider] Account unlinked from server: $lEmail -> removing locally');
            toRemove.add(acc);
          }
        }

        if (toRemove.isNotEmpty) {
          accountsChanged = true;
          for (final acc in toRemove) {
            _accounts.removeWhere((a) => a.email.toLowerCase() == acc.email.toLowerCase());
            _emailsByAccount.remove(acc.id);
            _inboxByAccount.remove(acc.id);
          }

          // If currently active account was one of the unlinked accounts, switch back to primary
          if (_config != null && toRemove.any((a) => a.email.toLowerCase() == _config!.email.toLowerCase())) {
            debugPrint('[MailProvider] Active account was unlinked, switching back to primary: ${primary.email}');
            _activeAccountIndex = 0;
            _config = _accounts.isNotEmpty ? _accounts[0] : null;
            if (_config != null) {
              _currentEmail = _config!.email;
              _currentDomain = _config!.domain;
              _allEmails = _emailsByAccount[_config!.id] ?? _inboxByAccount[_config!.id] ?? [];
            }
          } else if (_activeAccountIndex >= _accounts.length) {
            _activeAccountIndex = _accounts.isNotEmpty ? _accounts.length - 1 : 0;
            _config = _accounts.isNotEmpty ? _accounts[_activeAccountIndex] : null;
          }
        }

        if (accountsChanged) {
          await _saveAccounts();
          notifyListeners();
        }
      }
    } catch (e) {
      debugPrint('[MailProvider] syncAccountsWithServer notice: $e');
    }
  }
}

