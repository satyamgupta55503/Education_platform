import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:firebase_core/firebase_core.dart';

import 'theme/app_theme.dart';
import 'services/api_service.dart';
import 'screens/auth/phone_auth_screen.dart';
import 'screens/student/home_screen.dart';
import 'screens/student/chat_screen.dart';
import 'screens/student/profile_screen.dart';
import 'screens/student/leaderboard_screen.dart';

// ── Main ────────────────────────────────────────────────────────────────────
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp, DeviceOrientation.portraitDown]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent, statusBarIconBrightness: Brightness.dark));
  runApp(const ProviderScope(child: EduCatApp()));
}

// ── Router ──────────────────────────────────────────────────────────────────
final _routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const _SplashScreen()),
      GoRoute(path: '/auth',   builder: (_, __) => const PhoneAuthScreen()),

      // Student shell with bottom nav
      ShellRoute(
        builder: (ctx, state, child) => _StudentShell(child: child),
        routes: [
          GoRoute(path: '/home',         builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/leaderboard',  builder: (_, __) => const LeaderboardScreen()),
          GoRoute(path: '/profile',      builder: (_, __) => const ProfileScreen()),
        ],
      ),

      // Chat — no bottom nav
      GoRoute(
        path: '/chat/:subject/:grade/:lang',
        builder: (_, state) => ChatScreen(
          subject:  state.pathParameters['subject'] ?? 'science',
          grade:    int.tryParse(state.pathParameters['grade'] ?? '5') ?? 5,
          language: state.pathParameters['lang'] ?? 'hi',
        ),
      ),
    ],
  );
});

// ── App ─────────────────────────────────────────────────────────────────────
class EduCatApp extends ConsumerWidget {
  const EduCatApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(_routerProvider);
    return MaterialApp.router(
      title: 'EduCat AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: router,
    );
  }
}

// ── Splash Screen ────────────────────────────────────────────────────────────
class _SplashScreen extends ConsumerWidget {
  const _SplashScreen();
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Check auth on first render
    _checkAuth(context, ref);
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(gradient: AppDeco.primaryGradient),
        child: const Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('🐱', style: TextStyle(fontSize: 72)),
            SizedBox(height: 16),
            Text('EduCat AI', style: TextStyle(
              color: Colors.white, fontSize: 30, fontWeight: FontWeight.w800)),
            SizedBox(height: 8),
            Text('Smart Tutor for Classes 1–10',
              style: TextStyle(color: Colors.white70, fontSize: 14)),
            SizedBox(height: 40),
            CircularProgressIndicator(color: Colors.white54, strokeWidth: 2),
          ],
        )),
      ),
    );
  }

  Future<void> _checkAuth(BuildContext ctx, WidgetRef ref) async {
    await Future.delayed(const Duration(milliseconds: 800));
    if (!ctx.mounted) return;
    final loggedIn = await ref.read(apiProvider).isLoggedIn;
    if (ctx.mounted) {
      if (loggedIn) ctx.go('/home');
      else ctx.go('/auth');
    }
  }
}

// ── Student Shell (Bottom Nav) ────────────────────────────────────────────────
class _StudentShell extends StatelessWidget {
  final Widget child;
  const _StudentShell({required this.child});

  static const _tabs = ['/home', '/leaderboard', '/profile'];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    final idx = _tabs.indexWhere((t) => location.startsWith(t));

    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          boxShadow: [BoxShadow(color: Color(0x12000000), blurRadius: 12, offset: Offset(0, -2))],
        ),
        child: SafeArea(
          top: false,
          child: SizedBox(
            height: 60,
            child: Row(children: [
              _NavItem(icon: Icons.home_outlined, activeIcon: Icons.home_rounded,
                label: 'Home', active: idx == 0, onTap: () => context.go('/home')),
              _NavItem(icon: Icons.leaderboard_outlined, activeIcon: Icons.leaderboard_rounded,
                label: 'Rank', active: idx == 1, onTap: () => context.go('/leaderboard')),
              _NavItem(icon: Icons.person_outline_rounded, activeIcon: Icons.person_rounded,
                label: 'Profile', active: idx == 2, onTap: () => context.go('/profile')),
            ]),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon, activeIcon;
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _NavItem({required this.icon, required this.activeIcon,
    required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) => Expanded(
    child: GestureDetector(
      onTap: onTap, behavior: HitTestBehavior.opaque,
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 200),
          child: Icon(active ? activeIcon : icon, key: ValueKey(active),
            color: active ? AppColors.primary : AppColors.gray400, size: 22)),
        const SizedBox(height: 3),
        Text(label, style: TextStyle(
          fontSize: 10, fontWeight: active ? FontWeight.w700 : FontWeight.w500,
          color: active ? AppColors.primary : AppColors.gray400)),
        if (active) Container(
          margin: const EdgeInsets.only(top: 3),
          width: 4, height: 4,
          decoration: const BoxDecoration(color: AppColors.primary, shape: BoxShape.circle)),
      ]),
    ),
  );
}
