import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'theme/app_theme.dart';
import 'providers/mail_provider.dart';
import 'services/notification_service.dart';
import 'views/splash_screen.dart';
import 'views/welcome_screen.dart';
import 'views/login_screen.dart';
import 'views/main_layout.dart';
import 'views/email_detail_view.dart';
import 'views/compose_view.dart';
import 'views/voidpanel_accounts_view.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  GoogleFonts.config.allowRuntimeFetching = true;

  // Initialize native notification channels safely
  try {
    await NotificationService().initialize();
  } catch (e) {
    debugPrint('[Main] Notification init notice: $e');
  }

  // Prevent GoogleFont asset exceptions from crashing the app
  FlutterError.onError = (FlutterErrorDetails details) {
    final errStr = details.exception.toString();
    if (errStr.contains('GoogleFonts') || errStr.contains('font') || errStr.contains('asset')) {
      debugPrint('UI/Asset load notice (using fallback): $errStr');
      return;
    }
    FlutterError.presentError(details);
  };

  // Catch unhandled async errors to prevent launch crashes
  PlatformDispatcher.instance.onError = (error, stack) {
    debugPrint('Caught async platform error (handled safely): $error');
    return true;
  };

  runApp(const VoidMailApp());
}

class VoidMailApp extends StatelessWidget {
  const VoidMailApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => MailProvider(),
      child: Consumer<MailProvider>(
        builder: (context, mailProvider, child) {
          return MaterialApp(
            title: 'VoidMail — Powered by VoidPanel',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.lightTheme(primaryColor: mailProvider.accentColor),
            darkTheme: AppTheme.darkTheme(primaryColor: mailProvider.accentColor),
            themeMode: mailProvider.themeMode,
            builder: (context, child) {
              return MediaQuery(
                data: MediaQuery.of(context).copyWith(
                  textScaler: TextScaler.linear(mailProvider.fontSizeScale),
                ),
                child: child ?? const SizedBox.shrink(),
              );
            },
            initialRoute: '/splash',
            routes: {
              '/splash': (context) => const SplashScreen(),
              '/welcome': (context) => const WelcomeScreen(),
              '/login': (context) => const LoginScreen(),
              '/main': (context) => const MainLayout(),
              '/email_detail': (context) => const EmailDetailView(),
              '/compose': (context) => const ComposeView(),
              '/voidpanel_accounts': (context) => const VoidPanelAccountsView(),
            },
          );
        },
      ),
    );
  }
}
