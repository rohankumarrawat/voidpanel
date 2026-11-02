import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voidmail_app/models/voidpanel_config.dart';
import 'package:voidmail_app/providers/mail_provider.dart';
import 'package:voidmail_app/services/voidpanel_api_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('VoidMail Live Sovereign & Aliases Verification', () {
    setUp(() {
      HttpOverrides.global = null;
      SharedPreferences.setMockInitialValues({});
    });

    test('Live backend returns inbox emails and aliases for sovereign account', () async {
      final api = VoidPanelApiService();
      api.setBaseUrl('https://mail.voidonyx.in');

      // 1. Authenticate with live sovereign account
      final loginRes = await api.loginStep1('testuser_void_99@voidonyx.com', 'Password@123');
      expect(loginRes['success'], isTrue);

      // 2. Fetch sovereign inbox emails
      final inboxRes = await api.fetchInboxEmails(target: 'testuser_void_99@voidonyx.com');
      expect(inboxRes['status'], equals('success'));
      final emails = inboxRes['emails'] as List;
      expect(emails.length, greaterThanOrEqualTo(2));
      final subjects = emails.map((e) => e['subject'].toString()).toList();
      expect(subjects.any((s) => s.contains('Sovereign Business Mailbox')), isTrue);
      expect(subjects.any((s) => s.contains('AI Writing Assistant')), isTrue);

      // 3. Fetch linked aliases
      final aliases = await api.fetchAliases();
      expect(aliases, isNotEmpty);
      final aliasEmails = aliases.map((a) => a['source_email'].toString()).toList();
      expect(aliasEmails.any((e) => e.contains('contact_test@voidonyx.com') || e.contains('alex_test@voidonyx.com')), isTrue);
    });

    test('MailProvider correctly populates emails and aliases on login', () async {
      final provider = MailProvider();
      await provider.initialized;

      final loginRes = await provider.loginToVoidPanel(
        serverUrl: 'https://mail.voidonyx.in',
        username: 'testuser_void_99@voidonyx.com',
        password: 'Password@123',
      );

      expect(loginRes['success'], isTrue);
      expect(provider.isLoggedIn, isTrue);
      expect(provider.currentEmail, equals('testuser_void_99@voidonyx.com'));
      expect(provider.filteredEmails.length, greaterThanOrEqualTo(2));
      expect(provider.userAliases.length, greaterThanOrEqualTo(2));
      expect(provider.availableSenderEmails.length, greaterThanOrEqualTo(3)); // primary + 2 aliases

      // Test alias filter
      final firstAlias = provider.userAliases.first['source_email'] as String;
      provider.filterByAlias(firstAlias);
      expect(provider.selectedAliasFilter, equals(firstAlias));

      provider.filterByAlias(null);
      expect(provider.selectedAliasFilter, isNull);
    });

    test('Zero demo data on fresh startup', () async {
      SharedPreferences.setMockInitialValues({});
      final provider = MailProvider();
      await provider.initialized;

      expect(provider.isLoggedIn, isFalse);
      expect(provider.emails, isEmpty);
      expect(provider.accounts, isEmpty);
      expect(provider.currentEmail, isEmpty);
    });

    test('Professional email logout keeps primary logged in; primary logout logs out all', () async {
      SharedPreferences.setMockInitialValues({});
      final provider = MailProvider();
      await provider.initialized;

      // Add primary account
      final primaryCfg = ServerConfig.custom(
        email: 'primary@voidonyx.in',
        password: 'pass',
        imapHost: 'mail.voidonyx.in',
        smtpHost: 'mail.voidonyx.in',
      );
      provider.registerAccount(primaryCfg);
      expect(provider.isLoggedIn, isTrue);
      expect(provider.isCurrentAccountPrimary, isTrue);

      // Add professional account
      final proCfg = ServerConfig.custom(
        email: 'sales@companycorp.com',
        password: 'pass',
        imapHost: 'mail.companycorp.com',
        smtpHost: 'mail.companycorp.com',
        providerName: 'Company Pro Mail',
      );
      provider.registerAccount(proCfg);
      expect(provider.accounts.length, equals(2));

      // Switch to professional account
      provider.switchAccount(1);
      expect(provider.currentEmail, equals('sales@companycorp.com'));
      expect(provider.isCurrentAccountPrimary, isFalse);

      // Logout professional email
      final proLogoutResult = await provider.logout();
      // Should return false (meaning do NOT navigate to /login)
      expect(proLogoutResult, isFalse);
      expect(provider.isLoggedIn, isTrue);
      expect(provider.currentEmail, equals('primary@voidonyx.in'));
      expect(provider.isCurrentAccountPrimary, isTrue);
      expect(provider.accounts.length, equals(1));

      // Logout primary email
      final primaryLogoutResult = await provider.logout();
      // Should return true (meaning navigate to /login)
      expect(primaryLogoutResult, isTrue);
      expect(provider.isLoggedIn, isFalse);
      expect(provider.accounts, isEmpty);
    });
  });
}
