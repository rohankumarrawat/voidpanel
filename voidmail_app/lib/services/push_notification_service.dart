import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'notification_service.dart';
import 'voidpanel_api_service.dart';

/// Top-level background message handler for FCM.
/// Executed in an isolated Dart environment when the app is in the background or killed.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  debugPrint('[FCM Background] Received message ID: ${message.messageId}');
  try {
    // Ensure native notification plugin is initialized
    await NotificationService().initialize();

    final data = message.data;
    final sender = data['sender_name'] ?? message.notification?.title ?? 'New Email';
    final subject = data['subject'] ?? message.notification?.body ?? 'New message received';
    final snippet = data['snippet'] ?? '';
    final accountEmail = data['account_email'];

    await NotificationService().showNewMailNotification(
      sender: sender,
      subject: subject,
      snippet: snippet,
      accountEmail: accountEmail,
    );
  } catch (e) {
    debugPrint('[FCM Background] Notification error: $e');
  }
}

class PushNotificationService {
  static final PushNotificationService _instance = PushNotificationService._internal();
  factory PushNotificationService() => _instance;
  PushNotificationService._internal();

  FirebaseMessaging? _messaging;
  String? _fcmToken;
  bool _isFirebaseAvailable = false;
  bool _isInitialized = false;

  String? get fcmToken => _fcmToken;
  bool get isFirebaseAvailable => _isFirebaseAvailable;

  /// Initialize Firebase Core and Firebase Messaging safely.
  Future<void> initialize() async {
    if (_isInitialized) return;
    _isInitialized = true;

    // FCM is supported on mobile (Android & iOS). On desktop/web, skip isolate registration.
    if (kIsWeb || (!Platform.isAndroid && !Platform.isIOS)) {
      debugPrint('[PushNotification] Desktop platform detected — skipping FCM background isolate.');
      return;
    }

    try {
      // 1. Initialize Firebase Core with timeout
      await Firebase.initializeApp().timeout(const Duration(seconds: 3));
      _isFirebaseAvailable = true;
      _messaging = FirebaseMessaging.instance;

      // 2. Register Background Handler
      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

      // 3. Request permissions on Android 13+ and iOS

      final settings = await _messaging!.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        carPlay: false,
        criticalAlert: false,
        provisional: false,
        sound: true,
      );
      debugPrint('[PushNotification] Permission status: ${settings.authorizationStatus}');

      // 4. Retrieve FCM Device Token
      try {
        _fcmToken = await _messaging!.getToken();
        debugPrint('[PushNotification] FCM Device Token: ${_fcmToken?.substring(0, 20)}...');
      } catch (e) {
        debugPrint('[PushNotification] Could not retrieve FCM token: $e');
      }

      // 5. Listen to Token Refreshes
      _messaging!.onTokenRefresh.listen((newToken) {
        _fcmToken = newToken;
        debugPrint('[PushNotification] FCM Token refreshed: ${newToken.substring(0, 20)}...');
      });

      // 6. Handle Foreground Push Messages
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        debugPrint('[PushNotification Foreground] Message data: ${message.data}');
        final data = message.data;
        final sender = data['sender_name'] ?? message.notification?.title ?? 'New Email';
        final subject = data['subject'] ?? message.notification?.body ?? 'New message received';
        final snippet = data['snippet'] ?? '';
        final accountEmail = data['account_email'];

        NotificationService().showNewMailNotification(
          sender: sender,
          subject: subject,
          snippet: snippet,
          accountEmail: accountEmail,
        );
      });

      // 7. Handle Notification Tap when App was in Background
      FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
        debugPrint('[PushNotification] App opened via notification: ${message.data}');
      });

      // 8. Handle Notification Tap when App was Terminated
      final initialMessage = await _messaging!.getInitialMessage();
      if (initialMessage != null) {
        debugPrint('[PushNotification] App launched from terminated state via notification: ${initialMessage.data}');
      }

      _isInitialized = true;
      debugPrint('[PushNotification] FCM Service initialized successfully.');
    } catch (e) {
      _isFirebaseAvailable = false;
      debugPrint('[PushNotification] Notice: Firebase not configured on this device/environment ($e). Local notifications remain active.');
    }
  }

  /// Register current device token with VoidPanel server for the given email account.
  Future<void> syncTokenWithServer({
    required String email,
    String? panelBaseUrl,
  }) async {
    if (_fcmToken == null || _fcmToken!.isEmpty) {
      // Try retrieving token again if not yet loaded
      if (_messaging != null) {
        try {
          _fcmToken = await _messaging!.getToken();
        } catch (_) {}
      }
    }

    if (_fcmToken == null || _fcmToken!.isEmpty) {
      debugPrint('[PushNotification] No FCM token available to register.');
      return;
    }

    final platformName = kIsWeb
        ? 'web'
        : Platform.isIOS
            ? 'ios'
            : 'android';

    final api = VoidPanelApiService();
    if (panelBaseUrl != null && panelBaseUrl.isNotEmpty) {
      api.setBaseUrl(panelBaseUrl);
    }

    final result = await api.registerDeviceToken(
      email: email,
      fcmToken: _fcmToken!,
      platform: platformName,
      deviceName: kIsWeb ? 'Web Browser' : (Platform.isIOS ? 'Apple iPhone' : 'Android Device'),
    );

    debugPrint('[PushNotification] Token sync for $email: ${result['message'] ?? result}');
  }

  /// Unregister device token on logout or account removal.
  Future<void> unregisterToken({
    required String email,
    String? panelBaseUrl,
  }) async {
    if (_fcmToken == null || _fcmToken!.isEmpty) return;

    final api = VoidPanelApiService();
    if (panelBaseUrl != null && panelBaseUrl.isNotEmpty) {
      api.setBaseUrl(panelBaseUrl);
    }

    await api.unregisterDeviceToken(
      email: email,
      fcmToken: _fcmToken!,
    );
  }
}
