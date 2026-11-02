import 'dart:io';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Helper utility for safely validating and opening URLs and email hyperlinks.
class LinkLauncherHelper {
  /// Opens a URL in the device's default browser / external application.
  /// Handles http, https, mailto, tel, and relative or schemeless URLs.
  static Future<bool> openUrl(BuildContext? context, String rawUrl) async {
    var trimmed = rawUrl.trim();
    if (trimmed.isEmpty) return false;

    // Strip enclosing brackets or quotes if present (e.g. <https://example.com> or "https://...")
    if ((trimmed.startsWith('<') && trimmed.endsWith('>')) ||
        (trimmed.startsWith('(') && trimmed.endsWith(')')) ||
        (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
        (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
      trimmed = trimmed.substring(1, trimmed.length - 1).trim();
    }

    Uri? uri;
    try {
      String sanitized = trimmed;
      if (sanitized.startsWith('mailto:') || sanitized.startsWith('tel:')) {
        uri = Uri.tryParse(sanitized);
      } else if (sanitized.startsWith('http://') || sanitized.startsWith('https://')) {
        uri = Uri.tryParse(sanitized) ?? Uri.tryParse(Uri.encodeFull(sanitized));
      } else if (sanitized.contains('@') && !sanitized.contains('/')) {
        // Plain email address
        sanitized = 'mailto:$sanitized';
        uri = Uri.tryParse(sanitized);
      } else {
        // Assume https for web links without scheme
        sanitized = 'https://$sanitized';
        uri = Uri.tryParse(sanitized) ?? Uri.tryParse(Uri.encodeFull(sanitized));
      }

      if (uri == null) {
        _showError(context, 'Invalid URL format: $trimmed');
        return false;
      }

      bool launched = false;

      // Tier 1: Try platform default workspace handler
      try {
        if (await canLaunchUrl(uri)) {
          launched = await launchUrl(uri, mode: LaunchMode.platformDefault);
        }
      } catch (e) {
        debugPrint('[LinkLauncherHelper] Tier 1 launchUrl failed: $e');
      }

      // Tier 2: Try external application mode
      if (!launched) {
        try {
          launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
        } catch (e) {
          debugPrint('[LinkLauncherHelper] Tier 2 launchUrl failed: $e');
        }
      }

      // Tier 3: Try standard mode
      if (!launched) {
        try {
          launched = await launchUrl(uri);
        } catch (e) {
          debugPrint('[LinkLauncherHelper] Tier 3 launchUrl failed: $e');
        }
      }

      // Tier 4: Desktop OS native command fallback (macOS `open`, Linux `xdg-open`)
      if (!launched) {
        try {
          if (Platform.isMacOS) {
            final res = await Process.run('open', [uri.toString()]);
            launched = (res.exitCode == 0);
          } else if (Platform.isLinux) {
            final res = await Process.run('xdg-open', [uri.toString()]);
            launched = (res.exitCode == 0);
          }
        } catch (e) {
          debugPrint('[LinkLauncherHelper] Tier 4 OS command fallback error: $e');
        }
      }

      if (!launched) {
        if (context != null && context.mounted) {
          _showError(context, 'Could not open link: $trimmed');
        }
        return false;
      }

      return true;
    } catch (e) {
      debugPrint('[LinkLauncherHelper] Error opening URL ($trimmed): $e');
      if (context != null && context.mounted) {
        _showError(context, 'Unable to open link');
      }
      return false;
    }
  }

  /// Launch email compose via mailto URI
  static Future<bool> openMailto(
    BuildContext? context,
    String email, {
    String? subject,
    String? body,
  }) async {
    final queryParams = <String, String>{};
    if (subject != null && subject.isNotEmpty) queryParams['subject'] = subject;
    if (body != null && body.isNotEmpty) queryParams['body'] = body;

    final uri = Uri(
      scheme: 'mailto',
      path: email.trim(),
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );

    return openUrl(context, uri.toString());
  }

  /// Convert a plain text email into safe, styled HTML with auto-detected clickable hyperlinks.
  static String convertPlainTextToHtml(String plainText) {
    if (plainText.isEmpty) return '';

    // 1. Convert Markdown links [Label](URL) first so they aren't mangled by plain escaping
    var text = plainText;
    final mdLinkRegex = RegExp(
      r'\[([^\]]+)\]\(((?:https?:\/\/|mailto:|www\.)[^\s\)]+)\)',
      caseSensitive: false,
    );

    text = text.replaceAllMapped(mdLinkRegex, (match) {
      final label = match.group(1) ?? '';
      var href = match.group(2) ?? '';
      if (href.toLowerCase().startsWith('www.')) href = 'https://$href';
      return '<a href="$href" style="color: #4F46E5; text-decoration: underline; font-weight: 600; cursor: pointer;">$label</a>';
    });

    // 2. Escape HTML special characters (preserving any already injected tags)
    final lines = text.split(RegExp(r'\r\n|\n'));
    final processedLines = lines.map((line) {
      if (line.contains('<a href=')) return line;

      var escaped = line
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;')
          .replaceAll("'", '&#039;');

      // 3. Regex to detect raw HTTP/HTTPS/WWW URLs
      final urlRegex = RegExp(
        r'((https?:\/\/|www\.)[^\s<]+)',
        caseSensitive: false,
      );

      escaped = escaped.replaceAllMapped(urlRegex, (match) {
        var raw = match.group(1) ?? '';
        String trailing = '';
        while (raw.isNotEmpty && (raw.endsWith('.') || raw.endsWith(',') || raw.endsWith(';') || raw.endsWith(')') || raw.endsWith('!'))) {
          trailing = raw[raw.length - 1] + trailing;
          raw = raw.substring(0, raw.length - 1);
        }
        var href = raw;
        if (href.toLowerCase().startsWith('www.')) {
          href = 'https://$href';
        }
        return '<a href="$href" style="color: #4F46E5; text-decoration: underline; font-weight: 500; word-break: break-all; cursor: pointer;">$raw</a>$trailing';
      });

      // 4. Regex to detect raw email addresses
      final emailRegex = RegExp(
        r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b',
        caseSensitive: false,
      );

      escaped = escaped.replaceAllMapped(emailRegex, (match) {
        final email = match.group(1) ?? '';
        return '<a href="mailto:$email" style="color: #4F46E5; text-decoration: underline; font-weight: 500; cursor: pointer;">$email</a>';
      });

      return escaped;
    }).toList();

    return '<div style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; font-size: 14.5px; line-height: 1.65; color: #1E293B; word-break: break-word;">${processedLines.join('<br/>')}</div>';
  }

  static void _showError(BuildContext? context, String message) {
    if (context == null || !context.mounted) return;
    try {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 3),
        ),
      );
    } catch (_) {}
  }
}
