import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});
  @override ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  static const _subjects = ['science','maths','hindi','english','sst','gk'];

  @override
  void initState() {
    super.initState();
    // Update streak on app open
    Future.microtask(() => ref.read(apiProvider).updateStreak().catchError((_) {}));
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(profileProvider);
    final sessionsAsync = ref.watch(sessionsProvider(null));

    return Scaffold(
      backgroundColor: AppColors.bg,
      body: CustomScrollView(slivers: [

        // ── Hero AppBar ──────────────────────────────────────────────────────
        SliverAppBar(
          expandedHeight: 180,
          floating: false, pinned: true,
          backgroundColor: AppColors.primaryDark,
          elevation: 0,
          flexibleSpace: FlexibleSpaceBar(
            collapseMode: CollapseMode.parallax,
            background: profileAsync.when(
              loading: () => _HomeHeaderShimmer(),
              error:   (_, __) => _HomeHeaderShimmer(),
              data:    (p) => _HomeHeader(profile: p),
            ),
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.notifications_outlined, color: Colors.white),
              onPressed: () {},
            ),
          ],
        ),

        SliverPadding(
          padding: const EdgeInsets.fromLTRB(16, 20, 16, 0),
          sliver: SliverList(delegate: SliverChildListDelegate([

            // ── Subjects Grid ────────────────────────────────────────────────
            const SectionHeader(title: 'Choose Subject 📚'),
            const SizedBox(height: 14),
            GridView.count(
              crossAxisCount: 2, shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 12, mainAxisSpacing: 12,
              childAspectRatio: 1.45,
              children: List.generate(_subjects.length, (i) {
                final s = _subjects[i];
                return SubjectCard(
                  subject: s, index: i,
                  onTap: () async {
                    final api   = ref.read(apiProvider);
                    final grade = await api.cachedGrade;
                    final lang  = await api.cachedLang;
                    if (context.mounted) context.push('/chat/$s/$grade/$lang');
                  },
                );
              }),
            ),
            const SizedBox(height: 24),

            // ── Recent Sessions ──────────────────────────────────────────────
            SectionHeader(
              title: 'Recent Sessions 💬',
              actionLabel: 'See all',
              onAction: () => context.push('/sessions'),
            ),
            const SizedBox(height: 14),
            sessionsAsync.when(
              loading: () => _SessionsShimmer(),
              error:   (_, __) => const SizedBox(),
              data: (data) {
                final sessions = data['sessions'] as List<dynamic>? ?? [];
                if (sessions.isEmpty) return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: AppCard(child: const EmptyState(
                    emoji: '💬', title: 'No sessions yet',
                    subtitle: 'Pick a subject above to start!')),
                );
                return SizedBox(
                  height: 130,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: sessions.take(8).length,
                    separatorBuilder: (_, __) => const SizedBox(width: 10),
                    itemBuilder: (ctx, i) => _SessionChip(session: sessions[i] as Map<String, dynamic>),
                  ),
                );
              },
            ),
            const SizedBox(height: 24),

            // ── Quick Stats Row ──────────────────────────────────────────────
            profileAsync.when(
              loading: () => const SizedBox(),
              error:   (_, __) => const SizedBox(),
              data: (p) => _QuickStats(profile: p),
            ),
            const SizedBox(height: 28),
          ])),
        ),
      ]),
    );
  }
}

// ── Home Header ───────────────────────────────────────────────────────────────
class _HomeHeader extends StatelessWidget {
  final UserProfile profile;
  const _HomeHeader({required this.profile});
  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(gradient: AppDeco.primaryGradient),
    padding: const EdgeInsets.fromLTRB(20, 56, 20, 16),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Namaste, ${profile.displayName.split(' ').first}! 👋',
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700)),
          Text('Class ${profile.grade} · ${profile.language == "hi" ? "हिंदी" : "English"}',
            style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 13)),
        ])),
        TierBadge(tier: profile.tier),
      ]),
      const SizedBox(height: 16),
      Row(children: [
        _StatPill(emoji: '🧠', value: '${profile.brainCoins}', label: 'Coins'),
        const SizedBox(width: 12),
        _StatPill(emoji: '🔥', value: '${profile.streakDays}d', label: 'Streak'),
        const SizedBox(width: 12),
        _StatPill(emoji: '❓', value: '${profile.dailyRemaining}/${profile.dailyMax}', label: 'Today'),
      ]),
    ]),
  );
}

class _StatPill extends StatelessWidget {
  final String emoji, value, label;
  const _StatPill({required this.emoji, required this.value, required this.label});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
    decoration: BoxDecoration(
      color: Colors.white.withOpacity(0.15),
      borderRadius: BorderRadius.circular(20)),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Text(emoji, style: const TextStyle(fontSize: 13)),
      const SizedBox(width: 5),
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13)),
        Text(label, style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 9)),
      ]),
    ]),
  );
}

class _HomeHeaderShimmer extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
    color: AppColors.primaryDark,
    padding: const EdgeInsets.fromLTRB(20, 56, 20, 16),
    child: Shimmer.fromColors(
      baseColor: Colors.white.withOpacity(0.1),
      highlightColor: Colors.white.withOpacity(0.25),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(height: 20, width: 180, decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(6))),
        const SizedBox(height: 8),
        Container(height: 14, width: 120, decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(6))),
        const SizedBox(height: 20),
        Row(children: List.generate(3, (_) => Padding(
          padding: const EdgeInsets.only(right: 10),
          child: Container(height: 36, width: 80, decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)))),
        )),
      ]),
    ),
  );
}

// ── Session Chip ──────────────────────────────────────────────────────────────
class _SessionChip extends StatelessWidget {
  final Map<String, dynamic> session;
  const _SessionChip({required this.session});
  @override
  Widget build(BuildContext context) {
    final subject  = session['subject'] as String? ?? 'science';
    final msgs     = session['message_count'] ?? 0;
    final summary  = session['summary'] as String?;
    final color    = AppColors.forSubject(subject);
    final emoji    = AppColors.emojiForSubject(subject);
    return GestureDetector(
      onTap: () => context.push('/chat/$subject/${session['grade'] ?? 5}/${session['language'] ?? 'hi'}'),
      child: Container(
        width: 180,
        decoration: AppDeco.card(),
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 32, height: 32,
              decoration: BoxDecoration(color: AppColors.lightForSubject(subject), borderRadius: BorderRadius.circular(8)),
              child: Center(child: Text(emoji, style: const TextStyle(fontSize: 16)))),
            const SizedBox(width: 8),
            Text(subject.toUpperCase(), style: TextStyle(
              color: color, fontWeight: FontWeight.w700, fontSize: 11, letterSpacing: 0.8)),
          ]),
          const SizedBox(height: 8),
          Expanded(child: Text(summary ?? 'Continue learning...', maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 11, color: AppColors.gray600, height: 1.4))),
          Text('$msgs messages', style: const TextStyle(fontSize: 10, color: AppColors.gray400)),
        ]),
      ),
    ).animate().fadeIn().slideX(begin: 0.15);
  }
}

// ── Quick Stats ───────────────────────────────────────────────────────────────
class _QuickStats extends StatelessWidget {
  final UserProfile profile;
  const _QuickStats({required this.profile});
  @override
  Widget build(BuildContext context) => Column(children: [
    const SectionHeader(title: 'Your Progress 📊'),
    const SizedBox(height: 14),
    Row(children: [
      Expanded(child: _MiniStatCard(
        emoji: '📚', label: 'Sessions',
        value: '${profile.stats['total_sessions'] ?? 0}', color: AppColors.primary)),
      const SizedBox(width: 10),
      Expanded(child: _MiniStatCard(
        emoji: '❓', label: 'Questions',
        value: '${profile.stats['total_messages'] ?? 0}', color: AppColors.success)),
      const SizedBox(width: 10),
      Expanded(child: _MiniStatCard(
        emoji: '🏆', label: 'Avg Score',
        value: '${profile.stats['avg_score'] ?? 0}%', color: AppColors.warning)),
    ]),
  ]);
}

class _MiniStatCard extends StatelessWidget {
  final String emoji, label, value;
  final Color color;
  const _MiniStatCard({required this.emoji, required this.label, required this.value, required this.color});
  @override
  Widget build(BuildContext context) => AppCard(
    padding: const EdgeInsets.all(14),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(emoji, style: const TextStyle(fontSize: 22)),
      const SizedBox(height: 6),
      Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: color)),
      Text(label, style: const TextStyle(fontSize: 11, color: AppColors.gray400)),
    ]),
  ).animate().fadeIn().scale(begin: const Offset(0.95, 0.95));
}

class _SessionsShimmer extends StatelessWidget {
  @override
  Widget build(BuildContext context) => SizedBox(
    height: 130,
    child: ListView.separated(
      scrollDirection: Axis.horizontal,
      itemCount: 3,
      separatorBuilder: (_, __) => const SizedBox(width: 10),
      itemBuilder: (_, __) => const SkeletonCard(height: 130, width: 180),
    ),
  );
}
