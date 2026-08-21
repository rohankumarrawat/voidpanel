import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// VoidApp modern light theme matching VoidPanel mobile UI design system (Images 1 & 2).
class VoidTheme {
  // ── Core Colors (Clean Modern Light Mode) ──────────────────────────────────
  static const Color bgPrimary = Color(0xFFF5F7FB);   // Soft clean off-white background
  static const Color bgSurface = Color(0xFFFFFFFF);   // Pure white containers
  static const Color bgCard = Color(0xFFFFFFFF);      // Pure white card background
  static const Color bgGlass = Color(0xFFF1F5F9);     // Soft grey highlight
  static const Color bgElevated = Color(0xFFF8FAFC);  // Slightly elevated background

  // ── Accent Colors ──────────────────────────────────────────────────────────
  static const Color accentPrimary = Color(0xFF7C3AED);   // Vibrant Purple #7C3AED
  static const Color accentSecondary = Color(0xFF8B5CF6); // Soft Purple #8B5CF6
  static const Color accentSuccess = Color(0xFF10B981);   // Emerald Green #10B981
  static const Color accentWarning = Color(0xFFF59E0B);   // Amber Gold #F59E0B
  static const Color accentDanger = Color(0xFFEF4444);    // Coral Red #EF4444
  static const Color accentInfo = Color(0xFF3B82F6);      // Royal Blue #3B82F6

  // ── Text Colors ────────────────────────────────────────────────────────────
  static const Color textPrimary = Color(0xFF0F172A);     // Deep Slate Black
  static const Color textSecondary = Color(0xFF334155);   // Slate Dark
  static const Color textMuted = Color(0xFF64748B);       // Medium Muted Slate
  static const Color textDisabled = Color(0xFFCBD5E1);    // Light Slate

  // ── Border Colors ──────────────────────────────────────────────────────────
  static const Color border = Color(0xFFEEF2F6);         // Clean subtle border
  static const Color borderAccent = Color(0xFFDDD6FE);   // Lavender accent border

  // ── Gradients ──────────────────────────────────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF7C3AED), Color(0xFF9333EA)],
  );

  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFF3E8FF), Color(0xFFEDE9FE), Color(0xFFFAF5FF)],
  );

  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFFFFFF), Color(0xFFFAFAFA)],
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFF6F8FC), Color(0xFFF1F5F9)],
  );

  // ── Shadows ────────────────────────────────────────────────────────────────
  static List<BoxShadow> cardShadow = [
    BoxShadow(
      color: const Color(0x0C0F172A),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> glowShadow(Color color) => [
    BoxShadow(
      color: color.withValues(alpha: 0.18),
      blurRadius: 12,
      offset: const Offset(0, 4),
    ),
  ];

  // ── Border Radius ──────────────────────────────────────────────────────────
  static const double radiusSmall = 12;
  static const double radiusMedium = 16;
  static const double radiusLarge = 20;
  static const double radiusXLarge = 24;

  // ── Spacing ────────────────────────────────────────────────────────────────
  static const double spacingXS = 4;
  static const double spacingSM = 8;
  static const double spacingMD = 16;
  static const double spacingLG = 24;
  static const double spacingXL = 32;

  // ── Card Decorations ──────────────────────────────────────────────────────
  static BoxDecoration get glassCard => BoxDecoration(
    color: bgSurface,
    borderRadius: BorderRadius.circular(radiusLarge),
    border: Border.all(color: border, width: 1),
    boxShadow: cardShadow,
  );

  static BoxDecoration get heroCard => BoxDecoration(
    gradient: heroGradient,
    borderRadius: BorderRadius.circular(radiusXLarge),
    border: Border.all(color: borderAccent, width: 1),
    boxShadow: cardShadow,
  );

  static BoxDecoration get simpleCard => BoxDecoration(
    color: bgSurface,
    borderRadius: BorderRadius.circular(radiusMedium),
    border: Border.all(color: border, width: 1),
    boxShadow: [
      BoxShadow(
        color: const Color(0x06000000),
        blurRadius: 8,
        offset: const Offset(0, 2),
      ),
    ],
  );

  // ── ThemeData ──────────────────────────────────────────────────────────────
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: bgPrimary,
      colorScheme: const ColorScheme.light(
        primary: accentPrimary,
        secondary: accentSecondary,
        surface: bgSurface,
        error: accentDanger,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: textPrimary,
        onError: Colors.white,
      ),
      textTheme: GoogleFonts.interTextTheme(
        const TextTheme(
          headlineLarge: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w800,
            color: textPrimary,
            letterSpacing: -0.5,
          ),
          headlineMedium: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: textPrimary,
          ),
          headlineSmall: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: textPrimary,
          ),
          titleLarge: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: textPrimary,
          ),
          titleMedium: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: textSecondary,
          ),
          bodyLarge: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w400,
            color: textSecondary,
          ),
          bodyMedium: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w400,
            color: textMuted,
          ),
          bodySmall: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: textMuted,
          ),
          labelLarge: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: textPrimary,
            letterSpacing: 0.5,
          ),
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: bgPrimary,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.inter(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: textPrimary,
        ),
        iconTheme: const IconThemeData(color: textPrimary),
      ),
      cardTheme: CardThemeData(
        color: bgCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusMedium),
          side: const BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSmall),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSmall),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSmall),
          borderSide: const BorderSide(color: accentPrimary, width: 1.5),
        ),
        hintStyle: const TextStyle(color: textDisabled),
        labelStyle: const TextStyle(color: textMuted),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: accentPrimary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSmall),
          ),
          elevation: 0,
          textStyle: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: accentPrimary,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: bgSurface,
        selectedItemColor: accentPrimary,
        unselectedItemColor: textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: textPrimary,
        contentTextStyle: const TextStyle(color: Colors.white),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusSmall),
        ),
        behavior: SnackBarBehavior.floating,
      ),
      dividerTheme: const DividerThemeData(
        color: border,
        thickness: 1,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: bgCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusLarge),
        ),
      ),
    );
  }

  static ThemeData get darkTheme => lightTheme;
}
