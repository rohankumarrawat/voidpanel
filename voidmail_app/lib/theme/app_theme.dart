import 'package:flutter/material.dart';

class AppTheme {
  // VoidOnyx / VoidPanel Exact Purple Palette from Screenshot
  static const Color primaryPurple = Color(0xFF6C5CE7);
  static const Color primaryPurpleDark = Color(0xFF5A49E3);
  static const Color primaryPurpleLight = Color(0xFF8C7CFF);
  static const Color purpleBgTint = Color(0xFFF4F0FF);
  static const Color purpleSurfaceTint = Color(0xFFFAF8FF);

  // Dark Mode Palette
  static const Color darkBg = Color(0xFF0F0C20);
  static const Color darkCardBg = Color(0xFF1B1638);
  static const Color darkCardBorder = Color(0xFF2C2554);

  // Light Mode Palette
  static const Color lightBg = Color(0xFFFFFFFF);
  static const Color lightCardBg = Color(0xFFFFFFFF);
  static const Color lightCardBorder = Color(0xFFEFEFF6);

  // Text Colors
  static const Color textPrimary = Color(0xFF1E1B4B);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color textMuted = Color(0xFF9CA3AF);

  // Gradient definitions matching screenshot buttons & hero cards
  static const LinearGradient purpleGradient = LinearGradient(
    colors: [Color(0xFF6C5CE7), Color(0xFF8C7CFF)],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );

  static const LinearGradient heroCardGradient = LinearGradient(
    colors: [Color(0xFF0F0C20), Color(0xFF2E1C59), Color(0xFF1B1638)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static ThemeData lightTheme({Color? primaryColor}) {
    final activePrimary = primaryColor ?? primaryPurple;
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: lightBg,
      colorScheme: ColorScheme.light(
        primary: activePrimary,
        secondary: activePrimary.withOpacity(0.8),
        surface: lightCardBg,
        error: const Color(0xFFEF4444),
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: lightCardBg,
        elevation: 0,
        scrolledUnderElevation: 1,
        surfaceTintColor: Colors.transparent,
        iconTheme: IconThemeData(color: textPrimary),
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.bold,
        ),
      ),
      cardTheme: CardThemeData(
        color: lightCardBg,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: lightCardBorder, width: 1),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: activePrimary,
        foregroundColor: Colors.white,
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: lightCardBg,
        selectedItemColor: activePrimary,
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 10,
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 11),
      ),
    );
  }

  static ThemeData darkTheme({Color? primaryColor}) {
    final activePrimary = primaryColor ?? primaryPurple;
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBg,
      colorScheme: ColorScheme.dark(
        primary: activePrimary,
        secondary: activePrimary.withOpacity(0.8),
        surface: darkCardBg,
        error: const Color(0xFFEF4444),
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: Colors.white,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: darkCardBg,
        elevation: 0,
        scrolledUnderElevation: 1,
        surfaceTintColor: Colors.transparent,
        iconTheme: IconThemeData(color: Colors.white),
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 18,
          fontWeight: FontWeight.bold,
        ),
      ),
      cardTheme: CardThemeData(
        color: darkCardBg,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: darkCardBorder, width: 1),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: activePrimary,
        foregroundColor: Colors.white,
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: darkCardBg,
        selectedItemColor: activePrimary,
        unselectedItemColor: Colors.grey[400],
        type: BottomNavigationBarType.fixed,
        elevation: 10,
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 11),
      ),
    );
  }
}
