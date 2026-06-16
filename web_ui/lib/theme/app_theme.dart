import 'package:flutter/material.dart';

class AppTheme {
  static const primaryColor = Color(0xFF00D4AA);
  static const secondaryColor = Color(0xFF6366F1);
  static const backgroundColor = Color(0xFF0B0E17);
  static const surfaceColor = Color(0xFF161B28);
  static const textPrimaryColor = Color(0xFFF1F5F9);
  static const mutedTextColor = Color(0xFF94A3B8);

  // Platform type colors
  static const adsColor = Color(0xFFF59E0B);       // Amber
  static const organicColor = Color(0xFF10B981);    // Emerald
  static const analyticsColor = Color(0xFF3B82F6);  // Blue
  static const appStoreColor = Color(0xFFA855F7);   // Purple

  static Color colorForPlatformType(String type) {
    switch (type) {
      case 'ads': return adsColor;
      case 'organic': return organicColor;
      case 'analytics': return analyticsColor;
      case 'app_store': return appStoreColor;
      default: return mutedTextColor;
    }
  }

  static IconData iconForPlatformType(String type) {
    switch (type) {
      case 'ads': return Icons.campaign;
      case 'organic': return Icons.trending_up;
      case 'analytics': return Icons.analytics;
      case 'app_store': return Icons.phone_android;
      default: return Icons.hub;
    }
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: backgroundColor,
      colorScheme: const ColorScheme.dark(
        primary: primaryColor,
        secondary: secondaryColor,
        surface: surfaceColor,
        onSurface: textPrimaryColor,
        onPrimary: backgroundColor,
        onSecondary: textPrimaryColor,
      ),
      textTheme: const TextTheme(
        bodyLarge: TextStyle(color: textPrimaryColor),
        bodyMedium: TextStyle(color: textPrimaryColor),
        bodySmall: TextStyle(color: mutedTextColor),
        headlineLarge: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.bold),
        headlineMedium: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.bold),
        titleLarge: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.w500),
      ),
      cardTheme: CardThemeData(
        color: surfaceColor,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: const EdgeInsets.only(bottom: 16),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceColor,
        selectedColor: primaryColor.withOpacity(0.2),
        checkmarkColor: primaryColor,
        labelStyle: const TextStyle(color: textPrimaryColor, fontSize: 13),
        secondaryLabelStyle: const TextStyle(color: mutedTextColor, fontSize: 13),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: BorderSide(color: mutedTextColor.withOpacity(0.2)),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF2E364F)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primaryColor, width: 2),
        ),
        labelStyle: const TextStyle(color: mutedTextColor),
        hintStyle: const TextStyle(color: mutedTextColor),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: backgroundColor,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: secondaryColor,
          side: const BorderSide(color: secondaryColor),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: backgroundColor,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: textPrimaryColor),
        titleTextStyle: TextStyle(color: textPrimaryColor, fontSize: 20, fontWeight: FontWeight.bold),
      ),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: surfaceColor,
        contentTextStyle: TextStyle(color: textPrimaryColor),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.only(topLeft: Radius.circular(8), topRight: Radius.circular(8))),
      )
    );
  }
}
