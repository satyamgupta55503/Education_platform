import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

// ── Brand colours ─────────────────────────────────────────────────────────────
class AppColors {
  AppColors._();

  static const primary      = Color(0xFF2563EB);
  static const primaryDark  = Color(0xFF1E3A5F);
  static const primaryLight = Color(0xFFDBEAFE);
  static const primaryGlow  = Color(0xFF60A5FA);

  static const surface  = Color(0xFFFFFFFF);
  static const bg       = Color(0xFFF0F4F8);
  static const cardBg   = Color(0xFFFFFFFF);

  static const success      = Color(0xFF059669);
  static const successLight = Color(0xFFD1FAE5);
  static const warning      = Color(0xFFD97706);
  static const warningLight = Color(0xFFFEF3C7);
  static const error        = Color(0xFFDC2626);
  static const errorLight   = Color(0xFFFEE2E2);
  static const info         = Color(0xFF0891B2);

  // Subjects
  static const Map<String, Color> subject = {
    'science': Color(0xFF059669),
    'maths':   Color(0xFF7C3AED),
    'hindi':   Color(0xFFDC2626),
    'english': Color(0xFF2563EB),
    'sst':     Color(0xFFD97706),
    'gk':      Color(0xFF0891B2),
  };
  static const Map<String, Color> subjectLight = {
    'science': Color(0xFFD1FAE5),
    'maths':   Color(0xFFEDE9FE),
    'hindi':   Color(0xFFFEE2E2),
    'english': Color(0xFFDBEAFE),
    'sst':     Color(0xFFFEF3C7),
    'gk':      Color(0xFFCCFBF1),
  };
  static const Map<String, String> subjectEmoji = {
    'science': '🔬', 'maths': '📐', 'hindi': '🔤',
    'english': '📖', 'sst': '🌍', 'gk': '🌟',
  };

  // Tiers
  static const tierFree   = Color(0xFF6B7280);
  static const tierSmart  = Color(0xFF2563EB);
  static const tierGenius = Color(0xFFD97706);

  // Neutrals
  static const white  = Color(0xFFFFFFFF);
  static const black  = Color(0xFF111827);
  static const gray50 = Color(0xFFF9FAFB);
  static const gray100= Color(0xFFF3F4F6);
  static const gray200= Color(0xFFE5E7EB);
  static const gray300= Color(0xFFD1D5DB);
  static const gray400= Color(0xFF9CA3AF);
  static const gray500= Color(0xFF6B7280);
  static const gray600= Color(0xFF4B5563);
  static const gray700= Color(0xFF374151);
  static const gray800= Color(0xFF1F2937);
  static const gray900= Color(0xFF111827);

  static Color forSubject(String s) => subject[s.toLowerCase()] ?? primary;
  static Color lightForSubject(String s) => subjectLight[s.toLowerCase()] ?? primaryLight;
  static String emojiForSubject(String s) => subjectEmoji[s.toLowerCase()] ?? '📚';

  static Color forTier(String t) {
    switch (t.toLowerCase()) {
      case 'genius': return tierGenius;
      case 'smart':  return tierSmart;
      default:       return tierFree;
    }
  }
}

// ── Typography ────────────────────────────────────────────────────────────────
class AppText {
  AppText._();
  static TextStyle heading1(BuildContext ctx) => GoogleFonts.poppins(
    fontSize: 26, fontWeight: FontWeight.w700, color: AppColors.gray900, height: 1.2);
  static TextStyle heading2(BuildContext ctx) => GoogleFonts.poppins(
    fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.gray900, height: 1.3);
  static TextStyle heading3(BuildContext ctx) => GoogleFonts.poppins(
    fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.gray800, height: 1.4);
  static TextStyle body(BuildContext ctx) => GoogleFonts.poppins(
    fontSize: 14, fontWeight: FontWeight.w400, color: AppColors.gray700, height: 1.5);
  static TextStyle bodySmall(BuildContext ctx) => GoogleFonts.poppins(
    fontSize: 12, fontWeight: FontWeight.w400, color: AppColors.gray500, height: 1.5);
  static TextStyle label(BuildContext ctx) => GoogleFonts.poppins(
    fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.gray500, letterSpacing: 0.8);
  static TextStyle button(BuildContext ctx) => GoogleFonts.poppins(
    fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.white);
  static TextStyle mono(BuildContext ctx) => const TextStyle(
    fontFamily: 'Courier New', fontSize: 13, fontWeight: FontWeight.w600);
}

// ── Theme ─────────────────────────────────────────────────────────────────────
class AppTheme {
  AppTheme._();

  static ThemeData get light {
    SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ));
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primary, brightness: Brightness.light,
      ),
      textTheme: GoogleFonts.poppinsTextTheme(),
      scaffoldBackgroundColor: AppColors.bg,
      cardTheme: CardThemeData(
        elevation: 0,
        color: AppColors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: EdgeInsets.zero,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.white,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        shadowColor: Colors.transparent,
        systemOverlayStyle: SystemUiOverlayStyle.dark,
        titleTextStyle: GoogleFonts.poppins(
          color: AppColors.gray900, fontSize: 17, fontWeight: FontWeight.w700),
        iconTheme: const IconThemeData(color: AppColors.gray700),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 15),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: GoogleFonts.poppins(fontWeight: FontWeight.w600, fontSize: 15),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true, fillColor: AppColors.gray100,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.primary, width: 2)),
        hintStyle: GoogleFonts.poppins(color: AppColors.gray400, fontSize: 14),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: AppColors.white,
        selectedItemColor: AppColors.primary,
        unselectedItemColor: AppColors.gray400,
        elevation: 0, type: BottomNavigationBarType.fixed,
      ),
    );
  }
}

// ── Decorations ────────────────────────────────────────────────────────────────
class AppDeco {
  AppDeco._();

  static BoxDecoration card({Color? color, double radius = 16, Color? border}) =>
    BoxDecoration(
      color: color ?? AppColors.white,
      borderRadius: BorderRadius.circular(radius),
      border: border != null ? Border.all(color: border, width: 1) : null,
      boxShadow: const [BoxShadow(
        color: Color(0x0A000000), blurRadius: 8, offset: Offset(0, 2))],
    );

  static BoxDecoration gradient({required List<Color> colors, double radius = 20}) =>
    BoxDecoration(
      gradient: LinearGradient(
        colors: colors, begin: Alignment.topLeft, end: Alignment.bottomRight),
      borderRadius: BorderRadius.circular(radius),
    );

  static LinearGradient primaryGradient = const LinearGradient(
    colors: [Color(0xFF1E3A5F), Color(0xFF2563EB)],
    begin: Alignment.topLeft, end: Alignment.bottomRight,
  );

  static LinearGradient subjectGradient(String subject) {
    final c = AppColors.forSubject(subject);
    return LinearGradient(
      colors: [c.withOpacity(0.9), c],
      begin: Alignment.topLeft, end: Alignment.bottomRight,
    );
  }
}
