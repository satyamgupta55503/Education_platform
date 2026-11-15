import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

class LeaderboardScreen extends ConsumerStatefulWidget {
  const LeaderboardScreen({super.key});
  @override ConsumerState<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends ConsumerState<LeaderboardScreen> {
  int? _grade;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(leaderboardProvider(_grade));

    return Scaffold(
      backgroundColor: AppColors.bg,
      appBar: AppBar(
        backgroundColor: AppColors.primaryDark,
        foregroundColor: Colors.white,
        title: const Text('🏆 Leaderboard', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        centerTitle: false,
        elevation: 0,
      ),
      body: Column(children: [
        // ── Grade filter ──────────────────────────────────────────────────────
        Container(color: AppColors.primaryDark,
          child: SingleChildScrollView(scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
            child: Row(children: [
              _GradeChip(label: 'All', selected: _grade == null, onTap: () => setState(() => _grade = null)),
              for (int g = 1; g <= 10; g++)
                Padding(padding: const EdgeInsets.only(left: 6),
                  child: _GradeChip(label: 'Cl.$g', selected: _grade == g,
                    onTap: () => setState(() => _grade = _grade == g ? null : g))),
            ]),
          )),

        Expanded(child: async.when(
          loading: () => ListView.separated(
            padding: const EdgeInsets.all(16), itemCount: 8,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, __) => const SkeletonCard(height: 68)),
          error: (e, _) => EmptyState(emoji: '😢', title: 'Failed to load', subtitle: '$e'),
          data: (data) {
            final board   = data['leaderboard'] as List<dynamic>? ?? [];
            final myRank  = data['my_rank'] as int?;

            if (board.isEmpty) return const EmptyState(
              emoji: '🏆', title: 'No players yet',
              subtitle: 'Start studying to appear here!');

            return CustomScrollView(slivers: [
              // My rank banner
              if (myRank != null) SliverToBoxAdapter(child: _MyRankBanner(rank: myRank)),

              // Top 3 podium
              if (board.length >= 3) SliverToBoxAdapter(child: _Podium(top3: board.take(3).toList())),

              // Rest
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                sliver: SliverList(delegate: SliverChildBuilderDelegate(
                  (ctx, i) {
                    final s    = board[i] as Map<String, dynamic>;
                    final rank = (s['rank'] as num?)?.toInt() ?? i + 1;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _BoardRow(student: s, rank: rank)
                          .animate(delay: (i * 30).ms).fadeIn().slideX(begin: 0.1),
                    );
                  },
                  childCount: board.length,
                )),
              ),
            ]);
          },
        )),
      ]),
    );
  }
}

class _GradeChip extends StatelessWidget {
  final String label; final bool selected; final VoidCallback onTap;
  const _GradeChip({required this.label, required this.selected, required this.onTap});
  @override Widget build(BuildContext context) => GestureDetector(
    onTap: onTap,
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
      decoration: BoxDecoration(
        color: selected ? Colors.white : Colors.white.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20)),
      child: Text(label, style: TextStyle(
        color: selected ? AppColors.primaryDark : Colors.white.withOpacity(0.8),
        fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
        fontSize: 12)),
    ),
  );
}

class _MyRankBanner extends StatelessWidget {
  final int rank;
  const _MyRankBanner({required this.rank});
  @override Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: AppDeco.gradient(colors: const [Color(0xFF2563EB), Color(0xFF7C3AED)]),
      child: Row(children: [
        const Text('🏅', style: TextStyle(fontSize: 28)),
        const SizedBox(width: 12),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Your Rank', style: TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.w500)),
          Text('#$rank', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 22)),
        ]),
      ]),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: -0.2),
  );
}

class _Podium extends StatelessWidget {
  final List<dynamic> top3;
  const _Podium({required this.top3});
  @override
  Widget build(BuildContext context) {
    final order = [1, 0, 2]; // silver left, gold centre, bronze right
    final heights = [90.0, 110.0, 70.0];
    final medals = ['🥈', '🥇', '🥉'];
    final podiumColors = [const Color(0xFFC0C0C0), const Color(0xFFFFD700), const Color(0xFFCD7F32)];

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      padding: const EdgeInsets.symmetric(vertical: 20),
      decoration: AppDeco.card(),
      child: Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List.generate(3, (pos) {
          final idx  = order[pos];
          if (idx >= top3.length) return const SizedBox(width: 80);
          final s    = top3[idx] as Map<String, dynamic>;
          final name = s['display_name'] as String? ?? 'Student';
          final coins= s['brain_coins'] ?? 0;

          return Column(mainAxisSize: MainAxisSize.min, children: [
            Text(medals[pos], style: const TextStyle(fontSize: 28)),
            const SizedBox(height: 4),
            CircleAvatar(radius: 22, backgroundColor: podiumColors[pos].withOpacity(0.2),
              child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?',
                style: TextStyle(color: podiumColors[pos], fontWeight: FontWeight.w800, fontSize: 16))),
            const SizedBox(height: 6),
            Text(name.length > 8 ? '${name.substring(0, 8)}…' : name,
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            Row(mainAxisSize: MainAxisSize.min, children: [
              const Text('🧠', style: TextStyle(fontSize: 11)),
              const SizedBox(width: 2),
              Text('$coins', style: TextStyle(fontSize: 11, color: podiumColors[pos], fontWeight: FontWeight.w800)),
            ]),
            const SizedBox(height: 8),
            AnimatedContainer(
              duration: const Duration(milliseconds: 600), curve: Curves.easeOut,
              width: 60, height: heights[pos],
              decoration: BoxDecoration(
                color: podiumColors[pos].withOpacity(0.15),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
                border: Border.all(color: podiumColors[pos].withOpacity(0.4), width: 1.5)),
              child: Center(child: Text('${idx + 1}', style: TextStyle(
                color: podiumColors[pos], fontWeight: FontWeight.w800, fontSize: 18))),
            ),
          ]);
        }),
      ).animate().fadeIn(duration: 600.ms),
    );
  }
}

class _BoardRow extends StatelessWidget {
  final Map<String, dynamic> student;
  final int rank;
  const _BoardRow({required this.student, required this.rank});
  @override
  Widget build(BuildContext context) {
    final name   = student['display_name'] as String? ?? 'Student';
    final coins  = student['brain_coins'] ?? 0;
    final streak = student['streak_days'] ?? 0;
    final grade  = student['grade'];
    final tier   = student['tier'] as String? ?? 'free';
    final tc     = AppColors.forTier(tier);

    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(children: [
        // Rank
        SizedBox(width: 32, child: rank <= 3
          ? Text(['🥇','🥈','🥉'][rank-1], style: const TextStyle(fontSize: 22), textAlign: TextAlign.center)
          : Text('$rank', style: const TextStyle(fontSize: 13, color: AppColors.gray400, fontWeight: FontWeight.w700), textAlign: TextAlign.center)),
        const SizedBox(width: 10),
        // Avatar
        CircleAvatar(radius: 18, backgroundColor: tc.withOpacity(0.15),
          child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?',
            style: TextStyle(color: tc, fontWeight: FontWeight.w800))),
        const SizedBox(width: 10),
        // Info
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          Row(children: [
            Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(color: AppColors.primaryLight, borderRadius: BorderRadius.circular(6)),
              child: Text('Cl.$grade', style: const TextStyle(color: AppColors.primary, fontSize: 10, fontWeight: FontWeight.w700))),
            const SizedBox(width: 6),
            const Text('🔥', style: TextStyle(fontSize: 11)),
            Text('$streak d', style: const TextStyle(color: AppColors.gray400, fontSize: 11)),
          ]),
        ])),
        // Coins
        Row(children: [
          const Text('🧠', style: TextStyle(fontSize: 16)),
          const SizedBox(width: 4),
          Text('$coins', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.gray800)),
        ]),
      ]),
    );
  }
}
