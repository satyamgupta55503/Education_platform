import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:percent_indicator/percent_indicator.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});
  @override ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;

  @override
  void initState() { super.initState(); _tabs = TabController(length: 3, vsync: this); }
  @override
  void dispose() { _tabs.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(profileProvider);
    return Scaffold(
      backgroundColor: AppColors.bg,
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (p) => _ProfileBody(profile: p, tabs: _tabs),
      ),
    );
  }
}

class _ProfileBody extends StatelessWidget {
  final UserProfile profile;
  final TabController tabs;
  const _ProfileBody({required this.profile, required this.tabs});

  @override
  Widget build(BuildContext context) => NestedScrollView(
    headerSliverBuilder: (ctx, _) => [
      SliverAppBar(
        expandedHeight: 240, pinned: true,
        backgroundColor: AppColors.primaryDark,
        flexibleSpace: FlexibleSpaceBar(
          collapseMode: CollapseMode.parallax,
          background: _ProfileHero(profile: profile),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined, color: Colors.white),
            onPressed: () => _showEdit(ctx, profile),
          ),
        ],
      ),
      SliverToBoxAdapter(child: _EducatIdCard(id: profile.educatId)),
      SliverPersistentHeader(pinned: true, delegate: _TabBarDelegate(TabBar(
        controller: tabs, labelColor: AppColors.primary,
        unselectedLabelColor: AppColors.gray400,
        indicatorColor: AppColors.primary, indicatorWeight: 3,
        labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
        tabs: const [Tab(text: 'Overview'), Tab(text: 'Mastery'), Tab(text: 'Achievements')],
      ))),
    ],
    body: TabBarView(controller: tabs, children: [
      _OverviewTab(profile: profile),
      _MasteryTab(profile: profile),
      _AchievementsTab(achievements: profile.achievements),
    ]),
  );

  void _showEdit(BuildContext ctx, UserProfile p) {
    final ctrl = TextEditingController(text: p.displayName);
    showDialog(context: ctx, builder: (_) => AlertDialog(
      title: const Text('Edit Profile'),
      content: TextField(controller: ctrl, decoration: const InputDecoration(labelText: 'Display Name')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
        ElevatedButton(
          onPressed: () async {
            await ProviderScope.containerOf(ctx).read(apiProvider)
              .updateProfile({'display_name': ctrl.text.trim()});
            ProviderScope.containerOf(ctx).invalidate(profileProvider);
            if (ctx.mounted) Navigator.pop(ctx);
          },
          child: const Text('Save'),
        ),
      ],
    ));
  }
}

// ── Profile Hero ──────────────────────────────────────────────────────────────
class _ProfileHero extends StatelessWidget {
  final UserProfile profile;
  const _ProfileHero({required this.profile});
  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(gradient: AppDeco.primaryGradient),
    padding: const EdgeInsets.fromLTRB(20, 76, 20, 16),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        _Avatar(name: profile.displayName, tier: profile.tier),
        const SizedBox(width: 16),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(profile.displayName, style: const TextStyle(
            color: Colors.white, fontSize: 19, fontWeight: FontWeight.w800)),
          const SizedBox(height: 2),
          Text('Class ${profile.grade} · ${profile.language == "hi" ? "Hindi" : "English"}',
            style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 12)),
          const SizedBox(height: 8),
          TierBadge(tier: profile.tier),
        ])),
      ]),
      const SizedBox(height: 18),
      Row(children: [
        _HeroStat(emoji: '🧠', value: '${profile.brainCoins}', label: 'Brain Coins'),
        const SizedBox(width: 16),
        _HeroStat(emoji: '🔥', value: '${profile.streakDays}d', label: 'Streak'),
        const SizedBox(width: 16),
        _HeroStat(emoji: '📚', value: '${profile.stats['total_sessions'] ?? 0}', label: 'Sessions'),
      ]),
    ]),
  );
}

class _Avatar extends StatelessWidget {
  final String name, tier;
  const _Avatar({required this.name, required this.tier});
  @override
  Widget build(BuildContext context) {
    final color = AppColors.forTier(tier);
    return Container(
      width: 68, height: 68,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white.withOpacity(0.15),
        border: Border.all(color: Colors.white.withOpacity(0.6), width: 2.5),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 8)]),
      child: Center(child: Text(
        name.isNotEmpty ? name[0].toUpperCase() : '?',
        style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w800))),
    );
  }
}

class _HeroStat extends StatelessWidget {
  final String emoji, value, label;
  const _HeroStat({required this.emoji, required this.value, required this.label});
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Row(children: [
      Text(emoji, style: const TextStyle(fontSize: 14)),
      const SizedBox(width: 4),
      Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
    ]),
    Text(label, style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 10)),
  ]);
}

// ── EduCat ID Card ─────────────────────────────────────────────────────────────
class _EducatIdCard extends StatelessWidget {
  final String id;
  const _EducatIdCard({required this.id});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
    child: AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(children: [
        Container(padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(color: AppColors.primaryLight, borderRadius: BorderRadius.circular(10)),
          child: const Icon(Icons.badge_outlined, color: AppColors.primary, size: 20)),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Your EduCat Student ID',
            style: TextStyle(fontSize: 11, color: AppColors.gray400, fontWeight: FontWeight.w500)),
          const SizedBox(height: 2),
          Text(id, style: const TextStyle(
            fontSize: 15, fontWeight: FontWeight.w800, color: AppColors.primaryDark,
            letterSpacing: 1.2, fontFamily: 'Courier New')),
        ])),
        CopyIdWidget(id: id),
      ]),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.2),
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────────
class _OverviewTab extends StatelessWidget {
  final UserProfile profile;
  const _OverviewTab({required this.profile});

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(16), children: [
    // Stats grid
    GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12, mainAxisSpacing: 12, childAspectRatio: 1.4,
      children: [
        _StatCard(emoji: '💬', label: 'Sessions', value: '${profile.stats['total_sessions'] ?? 0}', color: AppColors.primary),
        _StatCard(emoji: '❓', label: 'Questions', value: '${profile.stats['total_messages'] ?? 0}', color: AppColors.success),
        _StatCard(emoji: '📝', label: 'Quizzes', value: '${profile.stats['total_quizzes'] ?? 0}', color: AppColors.warning),
        _StatCard(emoji: '⭐', label: 'Avg Score', value: '${profile.stats['avg_score'] ?? 0}%', color: AppColors.info),
      ]),
    const SizedBox(height: 20),

    // Quota card
    const Text('Monthly Quota', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
    const SizedBox(height: 10),
    _QuotaCard(profile: profile),
    const SizedBox(height: 20),

    // Activity chart
    if (profile.activity7d.isNotEmpty) ...[
      const Text('Activity (7 Days)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
      const SizedBox(height: 10),
      _ActivityChart(activity: profile.activity7d),
    ],
  ]);
}

class _StatCard extends StatelessWidget {
  final String emoji, label, value; final Color color;
  const _StatCard({required this.emoji, required this.label, required this.value, required this.color});
  @override Widget build(BuildContext context) => AppCard(
    padding: const EdgeInsets.all(14),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(emoji, style: const TextStyle(fontSize: 22)),
      const SizedBox(height: 6),
      Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: color)),
      Text(label, style: const TextStyle(fontSize: 11, color: AppColors.gray400)),
    ]),
  ).animate().fadeIn().scale(begin: const Offset(0.92, 0.92));
}

class _QuotaCard extends StatelessWidget {
  final UserProfile profile;
  const _QuotaCard({required this.profile});
  @override
  Widget build(BuildContext context) {
    final pct = profile.monthlyMax > 0 ? profile.monthlyRemaining / profile.monthlyMax : 0.0;
    final color = pct > 0.3 ? AppColors.success : pct > 0.1 ? AppColors.warning : AppColors.error;
    return AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text('${profile.monthlyRemaining} questions left',
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        TierBadge(tier: profile.tier, small: true),
      ]),
      const SizedBox(height: 10),
      ClipRRect(borderRadius: BorderRadius.circular(6),
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: pct),
          duration: const Duration(milliseconds: 900), curve: Curves.easeOut,
          builder: (_, val, __) => LinearProgressIndicator(
            value: val, minHeight: 10,
            backgroundColor: AppColors.gray100,
            valueColor: AlwaysStoppedAnimation(color)),
        )),
      const SizedBox(height: 6),
      Text('${profile.monthlyMax} per month on ${profile.tier.toUpperCase()} plan',
        style: const TextStyle(color: AppColors.gray400, fontSize: 12)),
    ]));
  }
}

class _ActivityChart extends StatelessWidget {
  final List<dynamic> activity;
  const _ActivityChart({required this.activity});
  @override
  Widget build(BuildContext context) {
    final spots = activity.asMap().entries.map((e) =>
      FlSpot(e.key.toDouble(), (e.value['messages'] as num?)?.toDouble() ?? 0)).toList();
    return AppCard(
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 8),
      child: SizedBox(height: 130, child: LineChart(LineChartData(
        gridData: FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(sideTitles: SideTitles(
            showTitles: true, reservedSize: 22,
            getTitlesWidget: (v, _) {
              const d = ['S','M','T','W','T','F','S'];
              return Text(d[v.toInt() % 7], style: const TextStyle(fontSize: 9, color: AppColors.gray400));
            },
          )),
        ),
        lineBarsData: [LineChartBarData(
          spots: spots, isCurved: true,
          color: AppColors.primary, barWidth: 2.5,
          dotData: FlDotData(show: false),
          belowBarData: BarAreaData(show: true,
            color: AppColors.primary.withOpacity(0.10)),
        )],
      ))),
    );
  }
}

// ── Mastery Tab ───────────────────────────────────────────────────────────────
class _MasteryTab extends StatelessWidget {
  final UserProfile profile;
  const _MasteryTab({required this.profile});
  @override
  Widget build(BuildContext context) {
    if (profile.subjectMastery.isEmpty) return const EmptyState(
      emoji: '📚', title: 'No mastery data yet', subtitle: 'Start studying to see progress!');
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: profile.subjectMastery.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (ctx, i) {
        final item    = profile.subjectMastery[i] as Map<String, dynamic>;
        final subject = item['subject'] as String;
        final pct     = (item['mastery_pct'] as num?)?.toDouble() ?? 0;
        final topics  = item['topics_covered'] ?? 0;
        final color   = AppColors.forSubject(subject);
        final emoji   = AppColors.emojiForSubject(subject);
        return AppCard(
          padding: const EdgeInsets.all(16),
          child: Column(children: [
            Row(children: [
              Container(width: 44, height: 44,
                decoration: BoxDecoration(color: AppColors.lightForSubject(subject), borderRadius: BorderRadius.circular(12)),
                child: Center(child: Text(emoji, style: const TextStyle(fontSize: 22)))),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(subject.toUpperCase(), style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 12, letterSpacing: 0.8)),
                Text('$topics topics covered', style: const TextStyle(color: AppColors.gray400, fontSize: 11)),
              ])),
              CircularPercentIndicator(
                radius: 28, lineWidth: 5,
                percent: (pct / 100).clamp(0.0, 1.0),
                center: Text('${pct.toStringAsFixed(0)}%',
                  style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 11)),
                progressColor: color, backgroundColor: color.withOpacity(0.12),
              ),
            ]),
            const SizedBox(height: 12),
            MasteryBar(pct: pct),
            const SizedBox(height: 6),
            Align(alignment: Alignment.centerRight, child: _MasteryLabel(pct: pct)),
          ]),
        ).animate(delay: (i * 70).ms).fadeIn().slideX(begin: 0.15);
      },
    );
  }
}

class _MasteryLabel extends StatelessWidget {
  final double pct;
  const _MasteryLabel({required this.pct});
  @override
  Widget build(BuildContext context) {
    String l; Color c;
    if (pct >= 85)      { l = '🏆 Mastered';    c = AppColors.success; }
    else if (pct >= 60) { l = '📈 Developing';   c = AppColors.primary; }
    else if (pct >= 30) { l = '🌱 Beginner';     c = AppColors.warning; }
    else                { l = '🔍 Just Started'; c = AppColors.gray400; }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: c.withOpacity(0.1), borderRadius: BorderRadius.circular(20)),
      child: Text(l, style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w700)));
  }
}

// ── Achievements Tab ──────────────────────────────────────────────────────────
class _AchievementsTab extends StatelessWidget {
  final List<dynamic> achievements;
  const _AchievementsTab({required this.achievements});
  @override
  Widget build(BuildContext context) {
    final unlocked = achievements.where((a) => a['unlocked'] == true).length;
    return Column(children: [
      Padding(padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFFF59E0B), Color(0xFFD97706)]),
            borderRadius: BorderRadius.circular(16)),
          child: Row(children: [
            const Text('🏆', style: TextStyle(fontSize: 36)),
            const SizedBox(width: 14),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('$unlocked/${achievements.length} Unlocked',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 17)),
              Text('Keep learning to unlock more!',
                style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 11)),
            ]),
          ]),
        )),
      Expanded(child: GridView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3, childAspectRatio: 0.88, crossAxisSpacing: 10, mainAxisSpacing: 10),
        itemCount: achievements.length,
        itemBuilder: (ctx, i) {
          final a = achievements[i] as Map<String, dynamic>;
          final u = a['unlocked'] as bool;
          return GestureDetector(
            onTap: () => showDialog(context: ctx, builder: (_) => AlertDialog(
              title: Text('${a['icon']} ${a['name']}'),
              content: Text(a['desc'] as String),
              actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK'))],
            )),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              decoration: BoxDecoration(
                color: u ? AppColors.primaryLight : AppColors.gray100,
                borderRadius: BorderRadius.circular(14),
                border: u ? Border.all(color: AppColors.primary.withOpacity(0.25)) : null),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Stack(alignment: Alignment.center, children: [
                  Text(a['icon'] as String, style: TextStyle(fontSize: 28,
                    color: u ? null : Colors.transparent)),
                  if (!u) const Icon(Icons.lock_rounded, size: 24, color: AppColors.gray300),
                ]),
                const SizedBox(height: 6),
                Text(a['name'] as String, textAlign: TextAlign.center, maxLines: 2,
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700,
                    color: u ? AppColors.primaryDark : AppColors.gray400)),
              ]),
            ),
          ).animate(delay: (i * 45).ms).fadeIn().scale(begin: const Offset(0.85, 0.85));
        },
      )),
    ]);
  }
}

class _TabBarDelegate extends SliverPersistentHeaderDelegate {
  final TabBar tb;
  const _TabBarDelegate(this.tb);
  @override Widget build(BuildContext c, double shrinkOffset, bool overlaps) =>
    Container(color: AppColors.white, child: tb);
  @override double get minExtent => tb.preferredSize.height;
  @override double get maxExtent => tb.preferredSize.height;
  @override bool shouldRebuild(_) => false;
}
