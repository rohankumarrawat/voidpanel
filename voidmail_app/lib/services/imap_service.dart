import 'package:flutter/foundation.dart';
import 'package:enough_mail/enough_mail.dart';
import '../models/email_item.dart';
import '../models/folder.dart';

class ImapService {
  static String _unescapeHtmlEntities(String text) {
    return text
        .replaceAll('&#039;', "'")
        .replaceAll('&#39;', "'")
        .replaceAll('&apos;', "'")
        .replaceAll('&quot;', '"')
        .replaceAll('&amp;', '&')
        .replaceAll('&lt;', '<')
        .replaceAll('&gt;', '>')
        .replaceAll('&nbsp;', ' ');
  }

  /// Extract clean plain text body from email message parts (HTML or Plain)
  static String _extractBodyText(MimeMessage message, String fallbackSubject) {
    // 1. Try plain text part
    final plainPart = message.decodeTextPlainPart();
    if (plainPart != null && plainPart.trim().isNotEmpty) {
      return _unescapeHtmlEntities(plainPart.trim());
    }

    // 2. Try HTML text part
    final htmlPart = message.decodeTextHtmlPart();
    if (htmlPart != null && htmlPart.trim().isNotEmpty) {
      final stripped = htmlPart
          .replaceAll(RegExp(r'<style[^>]*>[\s\S]*?<\/style>', caseSensitive: false), '')
          .replaceAll(RegExp(r'<script[^>]*>[\s\S]*?<\/script>', caseSensitive: false), '')
          .replaceAll(RegExp(r'<[^>]*>'), '\n')
          .replaceAll(RegExp(r'\n\s*\n'), '\n\n')
          .trim();
      if (stripped.isNotEmpty) {
        return _unescapeHtmlEntities(stripped);
      }
    }

    return fallbackSubject;
  }

  static Future<List<EmailItem>> fetchEmails({
    required String host,
    required int port,
    required bool isSsl,
    required String username,
    required String password,
    FolderType folderType = FolderType.inbox,
    int maxCount = 20,
  }) async {
    final domain = username.contains('@') ? username.split('@')[1] : '';

    final candidateHosts = <String>[host];
    if (domain.isNotEmpty) {
      if (!candidateHosts.contains('mail.$domain')) candidateHosts.add('mail.$domain');
      if (!candidateHosts.contains(domain)) candidateHosts.add(domain);
      if (!candidateHosts.contains('fast.voidpanel.com')) candidateHosts.add('fast.voidpanel.com');
      if (!candidateHosts.contains('mail.voidonyx.com')) candidateHosts.add('mail.voidonyx.com');
      if (!candidateHosts.contains('mail.voidonyx.in')) candidateHosts.add('mail.voidonyx.in');
    }

    final candidateConfigs = <Map<String, dynamic>>[];
    for (final h in candidateHosts) {
      candidateConfigs.add({'host': h, 'port': port, 'isSsl': isSsl});
      if (port == 993) {
        candidateConfigs.add({'host': h, 'port': 143, 'isSsl': false});
      }
    }

    Object? lastException;

    for (final cfg in candidateConfigs) {
      final tryHost = cfg['host'] as String;
      final tryPort = cfg['port'] as int;
      final trySsl = cfg['isSsl'] as bool;

      final client = ImapClient(isLogEnabled: false);
      try {
        await client.connectToServer(tryHost, tryPort, isSecure: trySsl).timeout(
          const Duration(seconds: 3),
        );

        if (!trySsl) {
          try {
            await client.startTls();
          } catch (_) {}
        }

        await client.login(username, password);

        String folderName = 'INBOX';
        if (folderType == FolderType.sent) {
          folderName = 'Sent';
        } else if (folderType == FolderType.drafts) {
          folderName = 'Drafts';
        } else if (folderType == FolderType.spam) {
          folderName = 'Junk';
        } else if (folderType == FolderType.trash) {
          folderName = 'Trash';
        } else if (folderType == FolderType.archive) {
          folderName = 'Archive';
        } else if (folderType == FolderType.notes) {
          folderName = 'Notes';
        }

        // Try the primary folder name, then common alternates
        bool folderOpened = false;
        final alternatePaths = <String>[];
        if (folderType == FolderType.sent) {
          alternatePaths.addAll(['Sent', 'Sent Messages', 'Sent Items', 'INBOX.Sent']);
        } else if (folderType == FolderType.spam) {
          alternatePaths.addAll(['Junk', 'Spam', 'Junk E-mail', 'INBOX.Junk']);
        } else if (folderType == FolderType.trash) {
          alternatePaths.addAll(['Trash', 'Deleted Messages', 'Deleted Items', 'INBOX.Trash']);
        } else if (folderType == FolderType.drafts) {
          alternatePaths.addAll(['Drafts', 'Draft', 'INBOX.Drafts']);
        } else if (folderType == FolderType.archive) {
          alternatePaths.addAll(['Archive', 'Archives', 'INBOX.Archive']);
        } else if (folderType == FolderType.notes) {
          alternatePaths.addAll(['Notes', 'INBOX.Notes']);
        } else {
          alternatePaths.add(folderName);
        }

        for (final path in alternatePaths) {
          try {
            await client.selectMailboxByPath(path);
            folderOpened = true;
            debugPrint('[IMAP] Opened folder: $path');
            break;
          } catch (_) {
            continue;
          }
        }

        // If no matching folder was found, return empty list instead of
        // falling back to INBOX (which causes inbox emails to show as sent)
        if (!folderOpened) {
          debugPrint('[IMAP] Folder "$folderName" not found on server — returning empty');
          try { await client.logout(); } catch (_) { client.disconnect(); }
          return [];
        }

        final fetchResult = await client.fetchRecentMessages(
          messageCount: maxCount,
          criteria: 'BODY.PEEK[]',
        );

        final items = <EmailItem>[];

        for (final message in fetchResult.messages.reversed) {
          final from = message.from?.isNotEmpty == true ? message.from!.first : null;
          final senderName = (from?.personalName?.isNotEmpty == true)
              ? from!.personalName!
              : (from?.email ?? 'Unknown Sender');
          final senderEmail = from?.email ?? 'unknown';

          // Extract actual recipient from To: header
          final toList = message.to;
          final recipientEmail = (toList != null && toList.isNotEmpty)
              ? toList.map((addr) => addr.email).where((e) => e != null && e.isNotEmpty).join(', ')
              : username;

          final subject = message.decodeSubject() ?? '(No Subject)';
          final bodyText = _extractBodyText(message, subject);
          final snippet = bodyText.replaceAll('\n', ' ').trim();

          // Preserve raw HTML for proper rendering
          final rawHtml = message.decodeTextHtmlPart();

          items.add(
            EmailItem(
              id: message.sequenceId?.toString() ?? DateTime.now().millisecondsSinceEpoch.toString(),
              senderName: senderName,
              senderEmail: senderEmail,
              recipientEmail: recipientEmail,
              subject: subject,
              snippet: snippet.length > 120 ? '${snippet.substring(0, 120)}...' : snippet,
              body: bodyText,
              htmlBody: rawHtml,
              timestamp: message.decodeDate() ?? DateTime.now(),
              isRead: message.isSeen,
              isStarred: message.isFlagged,
              hasAttachments: message.hasAttachments(),
              folder: folderType,
              accountEmail: username,
            ),
          );
        }

        try {
          await client.logout();
        } catch (_) {
          client.disconnect();
        }
        return items;
      } catch (e) {
        lastException = e;
        try {
          client.disconnect();
        } catch (_) {}
      }
    }

    final errStr = (lastException ?? '').toString();
    if (errStr.contains('AUTHENTICATIONFAILED') || errStr.contains('Authentication failed') || errStr.contains('Invalid credentials')) {
      throw Exception('Invalid email or password for $username. Please check your credentials.');
    }
    if (errStr.contains('StreamSink') || errStr.contains('Bad state') || errStr.contains('SocketException') || errStr.contains('TimeoutException')) {
      throw Exception('Could not establish connection to IMAP server for $username. Check your internet connection or server settings.');
    }

    throw lastException ?? Exception('Unable to connect to IMAP server for $username');
  }

  /// Send email via SMTP server with optimized host discovery & strict step timeouts
  static Future<Map<String, dynamic>> sendEmail({
    required String smtpHost,
    required int smtpPort,
    required bool isSsl,
    required String username,
    required String password,
    required String recipientEmail,
    required String subject,
    required String body,
  }) async {
    final domain = username.contains('@') ? username.split('@')[1] : '';

    final candidateHosts = <String>[smtpHost];
    if (domain.isNotEmpty) {
      if (!candidateHosts.contains('mail.$domain')) candidateHosts.add('mail.$domain');
      if (!candidateHosts.contains(domain)) candidateHosts.add(domain);
      if (!candidateHosts.contains('fast.voidpanel.com')) candidateHosts.add('fast.voidpanel.com');
      if (!candidateHosts.contains('mail.voidonyx.com')) candidateHosts.add('mail.voidonyx.com');
    }

    final candidateConfigs = <Map<String, dynamic>>[];
    for (final h in candidateHosts) {
      candidateConfigs.add({'host': h, 'port': smtpPort, 'isSsl': isSsl});
      if (smtpPort == 465) {
        candidateConfigs.add({'host': h, 'port': 587, 'isSsl': false});
      } else if (smtpPort == 587) {
        candidateConfigs.add({'host': h, 'port': 465, 'isSsl': true});
      }
    }

    Object? lastException;

    for (final cfg in candidateConfigs) {
      final tryHost = cfg['host'] as String;
      final tryPort = cfg['port'] as int;
      final trySsl = cfg['isSsl'] as bool;

      final client = SmtpClient('enough_mail');
      try {
        await client.connectToServer(tryHost, tryPort, isSecure: trySsl).timeout(
          const Duration(milliseconds: 2500),
        );

        if (!trySsl) {
          try {
            await client.startTls().timeout(const Duration(seconds: 2));
          } catch (_) {}
        }

        bool authSuccess = false;
        try {
          final res = await client.authenticate(username, password, AuthMechanism.plain).timeout(const Duration(seconds: 3));
          authSuccess = res.isOkStatus;
        } catch (_) {}

        if (!authSuccess || !client.isConnected) {
          try { await client.disconnect(); } catch (_) {}
          continue;
        }

        final builder = MessageBuilder.prepareMultipartAlternativeMessage();
        builder.from = [MailAddress(username, username)];
        builder.to = [MailAddress('', recipientEmail)];
        builder.subject = subject.isEmpty ? '(No Subject)' : subject;
        builder.text = body;

        final mimeMessage = builder.buildMimeMessage();
        bool sendOk = false;
        String responseMsg = '';
        try {
          final sendResult = await client.sendMessage(mimeMessage).timeout(const Duration(seconds: 4));
          sendOk = sendResult.isOkStatus;
          responseMsg = sendResult.toString();
        } catch (e) {
          sendOk = false;
          responseMsg = e.toString();
        }

        try {
          await client.disconnect();
        } catch (_) {}

        if (sendOk) {
          return {
            'success': true,
            'message': 'Sent via $tryHost',
          };
        }
      } catch (e) {
        lastException = e;
        try {
          await client.disconnect();
        } catch (_) {}
      }
    }

    return {
      'success': false,
      'message': lastException != null ? lastException.toString() : 'SMTP connection attempted for $username',
    };
  }

  /// Append a sent email to the server's Sent mailbox via IMAP APPEND command
  static Future<void> appendSentMessage({
    required String host,
    required int port,
    required bool isSsl,
    required String username,
    required String password,
    required String recipientEmail,
    required String subject,
    required String body,
  }) async {
    final candidateHosts = <String>[host];
    final domain = username.contains('@') ? username.split('@')[1] : '';
    if (domain.isNotEmpty) {
      if (!candidateHosts.contains('mail.$domain')) candidateHosts.add('mail.$domain');
      if (!candidateHosts.contains(domain)) candidateHosts.add(domain);
      if (!candidateHosts.contains('fast.voidpanel.com')) candidateHosts.add('fast.voidpanel.com');
    }

    for (final tryHost in candidateHosts) {
      final client = ImapClient(isLogEnabled: false);
      try {
        await client.connectToServer(tryHost, port, isSecure: isSsl).timeout(
          const Duration(seconds: 3),
        );
        if (!isSsl) {
          try { await client.startTls(); } catch (_) {}
        }
        await client.login(username, password);

        final alternatePaths = ['Sent', 'Sent Messages', 'Sent Items', 'INBOX.Sent'];
        for (final path in alternatePaths) {
          try {
            final builder = MessageBuilder.prepareMultipartAlternativeMessage();
            builder.from = [MailAddress(username, username)];
            builder.to = [MailAddress('', recipientEmail)];
            builder.subject = subject.isEmpty ? '(No Subject)' : subject;
            builder.text = body;
            final mimeMessage = builder.buildMimeMessage();

            await client.appendMessage(mimeMessage, targetMailboxPath: path);
            debugPrint('[IMAP] Appended sent message to $path on $tryHost');
            break;
          } catch (e) {
            continue;
          }
        }
        try { await client.logout(); } catch (_) { client.disconnect(); }
        return;
      } catch (e) {
        debugPrint('[IMAP] appendSentMessage error on $tryHost: $e');
        try { client.disconnect(); } catch (_) {}
      }
    }
  }
}
