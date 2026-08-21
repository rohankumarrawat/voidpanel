import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Service that communicates with VoidOnyx's central AI Gateway
/// at /api/ai/chat/ to provide real AI features in VoidMail.
///
/// The gateway routes requests to whichever AI model (Gemini, Claude,
/// OpenAI, HuggingFace) is configured by the super admin.
class VoidOnyxAiService {
  String _voidonyxUrl = 'https://voidonyx.in';
  String _licenseKey = '';
  String _panelHost = '';

  bool get isConfigured => _licenseKey.isNotEmpty;

  void configure({
    required String voidonyxUrl,
    required String licenseKey,
    String panelHost = '',
  }) {
    _voidonyxUrl = voidonyxUrl.endsWith('/')
        ? voidonyxUrl.substring(0, voidonyxUrl.length - 1)
        : voidonyxUrl;
    _licenseKey = licenseKey;
    _panelHost = panelHost;
    debugPrint('[VoidOnyxAI] Configured → $_voidonyxUrl (license: ${_licenseKey.substring(0, 8)}...)');
  }

  /// Send a chat message to VoidOnyx AI Gateway.
  ///
  /// Returns a map with:
  /// - `success`: bool
  /// - `response`: AI response text
  /// - `tool_calls`: list of tool calls (if any)
  /// - `error`: error message (if failed)
  Future<Map<String, dynamic>> chat({
    required String message,
    List<Map<String, String>> history = const [],
    String? systemPrompt,
    Map<String, dynamic>? serverContext,
  }) async {
    if (!isConfigured) {
      return {
        'success': false,
        'error': 'AI service not configured. License key missing.',
      };
    }

    final endpoint = Uri.parse('$_voidonyxUrl/api/ai/chat/');

    final defaultSystemPrompt = '''You are VoidMail AI Assistant — a smart, friendly email productivity helper.
You help users:
- Summarize their inbox and individual emails
- Draft professional email replies
- Organize and prioritize emails
- Suggest calendar events from email content
- Answer questions about their email workflow

Keep responses concise, helpful, and formatted with markdown.
Always be professional and respect email privacy.''';

    final payload = {
      'message': message,
      'history': history,
      'system_prompt': systemPrompt ?? defaultSystemPrompt,
      'server_context': serverContext ?? {
        'app': 'VoidMail',
        'version': '1.0.0',
      },
      'tools': [],
    };

    try {
      final response = await http.post(
        endpoint,
        headers: {
          'Content-Type': 'application/json',
          'X-License-Key': _licenseKey,
          'X-Panel-Host': _panelHost,
        },
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 45));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['status'] == 'success') {
          return {
            'success': true,
            'response': data['response'] ?? 'No response from AI.',
            'tool_calls': data['tool_calls'] ?? [],
          };
        } else {
          return {
            'success': false,
            'error': data['message'] ?? 'AI request failed.',
          };
        }
      } else if (response.statusCode == 402) {
        return {
          'success': false,
          'error': '💳 AI credits exhausted. Please recharge your chips at voidonyx.in.',
        };
      } else if (response.statusCode == 403) {
        return {
          'success': false,
          'error': '🔒 License not valid for AI features. Contact support.',
        };
      } else {
        final body = response.body;
        String errMsg = 'AI Gateway error (${response.statusCode})';
        try {
          final data = jsonDecode(body);
          errMsg = data['message'] ?? errMsg;
        } catch (_) {}
        return {'success': false, 'error': errMsg};
      }
    } catch (e) {
      debugPrint('[VoidOnyxAI] Error: $e');
      return {
        'success': false,
        'error': 'Unable to reach VoidOnyx AI Gateway. Check your connection.',
      };
    }
  }

  /// Generate an AI-powered email reply suggestion.
  Future<Map<String, dynamic>> suggestReply({
    required String originalEmail,
    required String senderName,
    String tone = 'professional',
  }) {
    return chat(
      message: 'Generate a $tone reply to this email from $senderName:\n\n"$originalEmail"\n\nWrite ONLY the reply body, no subject line.',
      systemPrompt: 'You are a professional email reply assistant. Generate concise, well-written email replies. Output ONLY the reply text.',
    );
  }

  /// Summarize inbox emails.
  Future<Map<String, dynamic>> summarizeInbox({
    required List<Map<String, String>> emailSnippets,
  }) {
    final emailText = emailSnippets.map((e) =>
      '• From: ${e['sender']} — Subject: ${e['subject']}'
    ).join('\n');

    return chat(
      message: 'Summarize these inbox emails in 3-5 bullet points:\n\n$emailText',
      systemPrompt: 'You are an email inbox summarizer. Be concise and highlight important items.',
    );
  }
}
