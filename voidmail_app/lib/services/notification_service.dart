import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _notificationsPlugin = FlutterLocalNotificationsPlugin();
  bool _isInitialized = false;

  Future<void> initialize() async {
    if (_isInitialized) return;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const darwinSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: darwinSettings,
      macOS: darwinSettings,
    );

    try {
      await _notificationsPlugin.initialize(
        initSettings,
        onDidReceiveNotificationResponse: (NotificationResponse response) {
          debugPrint('[NotificationService] Notification tapped: ${response.payload}');
        },
      );
      _isInitialized = true;
      debugPrint('[NotificationService] Initialized successfully.');
    } catch (e) {
      debugPrint('[NotificationService] Initialization error: $e');
    }
  }

  Future<void> requestPermissions() async {
    try {
      final androidImplementation =
          _notificationsPlugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      if (androidImplementation != null) {
        await androidImplementation.requestNotificationsPermission();
      }
    } catch (e) {
      debugPrint('[NotificationService] Request permission error: $e');
    }
  }

  Future<void> showNewMailNotification({
    required String sender,
    required String subject,
    required String snippet,
    String? accountEmail,
  }) async {
    try {
      final id = DateTime.now().millisecondsSinceEpoch.remainder(100000);

      const androidDetails = AndroidNotificationDetails(
        'voidmail_incoming_channel',
        'Incoming Mail Alerts',
        channelDescription: 'Notifications for new incoming emails',
        importance: Importance.high,
        priority: Priority.high,
        showWhen: true,
        icon: '@mipmap/ic_launcher',
        enableVibration: true,
        playSound: true,
      );

      const darwinDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      );

      const notificationDetails = NotificationDetails(
        android: androidDetails,
        iOS: darwinDetails,
      );

      final title = accountEmail != null && accountEmail.isNotEmpty
          ? '$sender ($accountEmail)'
          : sender;

      await _notificationsPlugin.show(
        id,
        title,
        '$subject — $snippet',
        notificationDetails,
        payload: accountEmail,
      );
    } catch (e) {
      debugPrint('[NotificationService] showNewMailNotification error: $e');
    }
  }

  Future<void> showMailSentNotification({
    required String recipient,
    required String subject,
  }) async {
    try {
      final id = DateTime.now().millisecondsSinceEpoch.remainder(100000);

      const androidDetails = AndroidNotificationDetails(
        'voidmail_activity_channel',
        'Mail Activity',
        channelDescription: 'Confirmations for sent emails and outbox activity',
        importance: Importance.defaultImportance,
        priority: Priority.defaultPriority,
        icon: '@mipmap/ic_launcher',
      );

      const darwinDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: false,
        presentSound: false,
      );

      const notificationDetails = NotificationDetails(
        android: androidDetails,
        iOS: darwinDetails,
      );

      await _notificationsPlugin.show(
        id,
        'Email Sent Successfully 🚀',
        'To: $recipient — "$subject"',
        notificationDetails,
      );
    } catch (e) {
      debugPrint('[NotificationService] showMailSentNotification error: $e');
    }
  }
}
