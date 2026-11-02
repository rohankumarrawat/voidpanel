import 'package:flutter/material.dart';

class AppTheme {
  // VoidMail Exact Flame Orange & Amber Glow Palette (Matching App Icon)
  static const Color primaryOrange = Color(0xFFFF7A00);       // Vibrant Electric Flame Orange
  static const Color primaryOrangeDark = Color(0xFFE65100);   // Deep Ember Orange
  static const Color primaryOrangeLight = Color(0xFFFF9E3B);  // Radiant Amber Glow
  static const Color accentAmber = Color(0xFFFFB800);         // Gold Amber Accent
  static const Color orangeBgTint = Color(0xFFFFF7ED);        // Soft warm cream highlight
  static const Color orangeSurfaceTint = Color(0xFFFFFBF5);   // Pure warm surface tint

  // Backward-compatibility aliases
  static const Color primaryPurple = primaryOrange;
  static const Color primaryPurpleDark = primaryOrangeDark;
  static const Color primaryPurpleLight = primaryOrangeLight;
  static const Color purpleBgTint = orangeBgTint;
  static const Color purpleSurfaceTint = orangeSurfaceTint;

  // Dark Mode Palette (Rich Obsidian with Warm Amber Ember Glow)
  static const Color darkBg = Color(0xFF100B07);
  static const Color darkCardBg = Color(0xFF1C140D);
  static const Color darkCardBorder = Color(0xFF2E1F14);

  // Light Mode Palette
  static const Color lightBg = Color(0xFFFAFAFA);
  static const Color lightCardBg = Color(0xFFFFFFFF);
  static const Color lightCardBorder = Color(0xFFF1EDE8);

  // Text Colors
  static const Color textPrimary = Color(0xFF1C130D);
  static const Color textSecondary = Color(0xFF6B5E55);
  static const Color textMuted = Color(0xFF9C8F85);

  // Gradient definitions matching the glowing 3D app icon
  static const LinearGradient orangeGradient = LinearGradient(
    colors: [Color(0xFFFF7A00), Color(0xFFFF9E3B)],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );

  static const LinearGradient flameGradient = LinearGradient(
    colors: [Color(0xFFFF6B00), Color(0xFFFFA500)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient purpleGradient = orangeGradient;

  static const LinearGradient heroCardGradient = LinearGradient(
    colors: [Color(0xFF1E1106), Color(0xFF331B09), Color(0xFF180D05)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static ThemeData lightTheme({Color? primaryColor}) {
    final activePrimary = primaryColor ?? primaryOrange;

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
