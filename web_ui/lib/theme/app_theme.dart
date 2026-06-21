import 'package:flutter/material.dart';

class AppTheme {
  // Main colors
  static const primaryColor = Color(0xFFFFFFFF); // White main
  static const secondaryColor = Color(0xFFFFD700); // Gold
  static const tertiaryColor = Color(0xFFC0C0C0); // Silver
  static const backgroundColor = Color(0xFF000000); // Obsidian Black base
  static const surfaceColor = Color(0x1CFFFFFF); // Frosted Glass container (11% white overlay)
  static const textPrimaryColor = Color(0xFFFFFFFF);
  static const mutedTextColor = Color(0xFF888888);

  // Platform type colors
  static const adsColor = Color(0xFFFFD700);       // Gold
  static const organicColor = Color(0xFFC0C0C0);    // Silver
  static const analyticsColor = Color(0xFF3B82F6);  // Blue
  static const appStoreColor = Color(0xFFA855F7);   // Purple

  // Accent and Indicator Colors
  static const neonRed = Color(0xFFFF3333);
  static const neonBlue = Color(0xFF3399FF);
  static const neonOrange = Color(0xFFFF9933);
  static const neonGreen = Color(0xFF33FF99);
  static const neonYellow = Color(0xFFFFFF33);

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
        tertiary: tertiaryColor,
        surface: surfaceColor,
        onSurface: textPrimaryColor,
        onPrimary: backgroundColor,
        onSecondary: backgroundColor,
      ),
      textTheme: const TextTheme(
        bodyLarge: TextStyle(color: textPrimaryColor, fontFamily: 'Sora'),
        bodyMedium: TextStyle(color: textPrimaryColor, fontFamily: 'Sora'),
        bodySmall: TextStyle(color: mutedTextColor, fontFamily: 'Sora'),
        headlineLarge: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.bold, fontFamily: 'Syne'),
        headlineMedium: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.bold, fontFamily: 'Syne'),
        titleLarge: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.w600, fontFamily: 'Syne'),
        titleMedium: TextStyle(color: textPrimaryColor, fontWeight: FontWeight.w500, fontFamily: 'Syne'),
      ),
      cardTheme: const CardThemeData(
        color: surfaceColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          side: BorderSide(color: Color(0x33FFFFFF), width: 1.0), // Silver/white border overlay
        ),
        margin: EdgeInsets.only(bottom: 16),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceColor,
        selectedColor: secondaryColor.withOpacity(0.2),
        checkmarkColor: secondaryColor,
        labelStyle: const TextStyle(color: textPrimaryColor, fontSize: 13, fontFamily: 'Sora'),
        secondaryLabelStyle: const TextStyle(color: mutedTextColor, fontSize: 13, fontFamily: 'Sora'),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: Color(0x22FFFFFF)),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x22FFFFFF)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x33FFFFFF)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: secondaryColor, width: 1.5), // Gold focus
        ),
        labelStyle: const TextStyle(color: mutedTextColor, fontFamily: 'Sora'),
        hintStyle: const TextStyle(color: mutedTextColor, fontFamily: 'Sora'),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: secondaryColor, // Gold button
          foregroundColor: backgroundColor,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, fontFamily: 'Sora'),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primaryColor,
          side: const BorderSide(color: Color(0x44FFFFFF)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, fontFamily: 'Sora'),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: backgroundColor,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: textPrimaryColor),
        titleTextStyle: TextStyle(color: textPrimaryColor, fontSize: 20, fontWeight: FontWeight.bold, fontFamily: 'Syne'),
      ),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: Color(0xFF101010),
        contentTextStyle: TextStyle(color: textPrimaryColor, fontFamily: 'Sora'),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.only(topLeft: Radius.circular(8), topRight: Radius.circular(8))),
      )
    );
  }

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: const Color(0xFFFFFFFF),
      colorScheme: const ColorScheme.light(
        primary: Color(0xFF000000),
        secondary: secondaryColor,
        tertiary: tertiaryColor,
        surface: Color(0x0A000000), // Glassmorphic light overlay (4% black)
        onSurface: Color(0xFF000000),
        onPrimary: Color(0xFFFFFFFF),
        onSecondary: Color(0xFF000000),
      ),
      textTheme: const TextTheme(
        bodyLarge: TextStyle(color: Color(0xFF000000), fontFamily: 'Sora'),
        bodyMedium: TextStyle(color: Color(0xFF000000), fontFamily: 'Sora'),
        bodySmall: TextStyle(color: Color(0xFF666666), fontFamily: 'Sora'),
        headlineLarge: TextStyle(color: Color(0xFF000000), fontWeight: FontWeight.bold, fontFamily: 'Syne'),
        headlineMedium: TextStyle(color: Color(0xFF000000), fontWeight: FontWeight.bold, fontFamily: 'Syne'),
        titleLarge: TextStyle(color: Color(0xFF000000), fontWeight: FontWeight.w600, fontFamily: 'Syne'),
        titleMedium: TextStyle(color: Color(0xFF000000), fontWeight: FontWeight.w500, fontFamily: 'Syne'),
      ),
      cardTheme: const CardThemeData(
        color: Color(0x0C000000), // Frosted glass light
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          side: BorderSide(color: Color(0x1F000000), width: 1.0), // Silver border outline
        ),
        margin: EdgeInsets.only(bottom: 16),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: const Color(0x08000000),
        selectedColor: secondaryColor.withOpacity(0.3),
        checkmarkColor: Color(0xFF000000),
        labelStyle: const TextStyle(color: Color(0xFF000000), fontSize: 13, fontFamily: 'Sora'),
        secondaryLabelStyle: const TextStyle(color: Color(0xFF666666), fontSize: 13, fontFamily: 'Sora'),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: Color(0x14000000)),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0x08000000),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x14000000)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x1A000000)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF000000), width: 1.5),
        ),
        labelStyle: const TextStyle(color: Color(0xFF666666), fontFamily: 'Sora'),
        hintStyle: const TextStyle(color: Color(0xFF666666), fontFamily: 'Sora'),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: Color(0xFF000000),
          foregroundColor: Color(0xFFFFFFFF),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, fontFamily: 'Sora'),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: Color(0xFF000000),
          side: const BorderSide(color: Color(0x26000000)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, fontFamily: 'Sora'),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFFFFFFFF),
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: Color(0xFF000000)),
        titleTextStyle: TextStyle(color: Color(0xFF000000), fontSize: 20, fontWeight: FontWeight.bold, fontFamily: 'Syne'),
      ),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: Color(0xFFF0F0F0),
        contentTextStyle: TextStyle(color: Color(0xFF000000), fontFamily: 'Sora'),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.only(topLeft: Radius.circular(8), topRight: Radius.circular(8))),
      )
    );
  }
}
