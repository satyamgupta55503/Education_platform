// lib/screens/teacher/school_dashboard_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:percent_indicator/percent_indicator.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/stat_card.dart';
import '../../widgets/kpi_card.dart';
import '../../widgets/subject_chip.dart';

// ── Providers ────────────────────────────────────────────────────────────────
final schoolOverviewProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.read(apiServiceProvider).getSchoolOverview();
});

final schoolStudentsProvider = StateNotifierProvider<StudentsNotifier,
    AsyncValue<Map<String, dynamic>>>((ref) => StudentsNotifier(ref));

class StudentsNotifier extends StateNotifier<AsyncValue<Map<String, dynamic>>> {
  final Ref ref;
  int? _grade;
  String _sortBy = 'brain_coins';
  int _page = 1;

  StudentsNotifier(this.ref) : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load({int? grade, String? sortBy, int page = 1}) async {
    _grade  = grade ?? _grade;
    _sortBy = sortBy ?? _sortBy;
    _page   = page;
    state   = const AsyncValue.loading();
    try {
      final data = await ref.read(apiServiceProvider).getSchoolStudents(
        grade: _grade, sortBy: _sortBy, page: _page,
      );
      state = AsyncValue.data(data);
    } catch (e, s) {
      state = AsyncValue.error(e, s);
    }
  }
}

final schoolSubjectsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.read(apiServiceProvider).getSchoolSubjects();
});

final weakStudentsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.read(apiServiceProvider).getWeakStudents(threshold: 0.4);
});

// ── Screen ───────────────────────────────────────────────────────────────────
class SchoolDashboardScreen extends ConsumerStatefulWidget {
  const SchoolDashboardScreen({super.key});
  @override
  ConsumerState<SchoolDashboardScreen> createState() => _SchoolDashboardState();
}

class _SchoolDashboardState extends ConsumerState<SchoolDashboardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;
  int? _selectedGrade;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final overviewAsync = ref.watch(schoolOverviewProvider);

    return Scaffold(
      backgroundColor: AppColors.gray50,
      body: overviewAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorView(message: e.toString()),
        data: (overview) => _buildDashboard(overview),
      ),
    );
  }

  Widget _buildDashboard(Map<String, dynamic> overview) {
    final workspace = overview['workspace'] as Map<String, dynamic>;
    final team      = overview['team']      as Map<String, dynamic>;
    final today     = overview['today']     as Map<String, dynamic>;
    final cache     = overview['cache']     as Map<String, dynamic>;
    final subjects  = overview['subject_engagement'] as List<dynamic>;
    final activity  = overview['activity_30d'] as List<dynamic>;

    return NestedScrollView(
      headerSliverBuilder: (ctx, _) => [
        // ── AppBar ──────────────────────────────────────────────────────────
        SliverAppBar(
          expandedHeight: 200,
          pinned: true,
          backgroundColor: AppColors.primaryDark,
          flexibleSpace: FlexibleSpaceBar(
            background: _SchoolHeader(workspace: workspace, team: team),
          ),
          title: Text(workspace['school_name'] as String? ?? 'School',
              style: const TextStyle(color: Colors.white, fontSize: 16,
                  fontWeight: FontWeight.bold)),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh_rounded, color: Colors.white),
              onPressed: () => ref.invalidate(schoolOverviewProvider),
            ),
          ],
        ),

        // ── Today KPI row ────────────────────────────────────────────────────
        SliverToBoxAdapter(
          child: _TodayKPIs(today: today, cache: cache).animate().fadeIn(),
        ),

        // ── Tab Bar ──────────────────────────────────────────────────────────
        SliverPersistentHeader(
          pinned: true,
          delegate: _SliverTabDelegate(
            TabBar(
              controller: _tabs,
              isScrollable: true,
              labelColor: AppColors.primary,
              unselectedLabelColor: AppColors.gray400,
              indicatorColor: AppColors.primary,
              tabAlignment: TabAlignment.start,
              tabs: const [
                Tab(text: '👥 Students'),
                Tab(text: '📚 Subjects'),
                Tab(text: '⚠️ Needs Help'),
                Tab(text: '📈 Activity'),
              ],
            ),
          ),
        ),
      ],
      body: TabBarView(
        controller: _tabs,
        children: [
          _StudentsTab(selectedGrade: _selectedGrade,
              onGradeChanged: (g) => setState(() => _selectedGrade = g)),
          _SubjectsTab(),
          _WeakStudentsTab(),
          _ActivityTab(activity: activity),
        ],
      ),
    );
  }
}

// ── School Header ────────────────────────────────────────────────────────────
class _SchoolHeader extends StatelessWidget {
  final Map<String, dynamic> workspace;
  final Map<String, dynamic> team;
  const _SchoolHeader({required this.workspace, required this.team});

  @override
  Widget build(BuildContext context) {
    final quotaPct  = (workspace['quota_used_pct'] as num?)?.toDouble() ?? 0;
    final planType  = workspace['plan_type'] as String? ?? 'classroom';

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [AppColors.primaryDark, Color(0xFF1D4ED8)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      padding: const EdgeInsets.fromLTRB(20, 80, 20, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(planType.toUpperCase(),
                    style: const TextStyle(color: Colors.white70,
                        fontSize: 11, letterSpacing: 1)),
              ),
              const Spacer(),
              Text('${workspace['school_code']}',
                  style: const TextStyle(color: Colors.white60, fontSize: 12)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Monthly Quota',
                        style: TextStyle(color: Colors.white70, fontSize: 11)),
                    const SizedBox(height: 4),
                    LinearProgressIndicator(
                      value: quotaPct / 100,
                      backgroundColor: Colors.white24,
                      color: quotaPct > 80 ? AppColors.error
                          : quotaPct > 60 ? AppColors.warning : Colors.white,
                      minHeight: 6,
                      borderRadius: BorderRadius.circular(3),
                    ),
                    const SizedBox(height: 4),
                    Text('$quotaPct% used',
                        style: const TextStyle(color: Colors.white60, fontSize: 11)),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Column(children: [
                Text('${team['teacher_count']}',
                    style: const TextStyle(color: Colors.white,
                        fontWeight: FontWeight.bold, fontSize: 22)),
                const Text('Teachers', style: TextStyle(color: Colors.white60, fontSize: 11)),
              ]),
              const SizedBox(width: 16),
              Column(children: [
                Text('${team['content_pieces']}',
                    style: const TextStyle(color: Colors.white,
                        fontWeight: FontWeight.bold, fontSize: 22)),
                const Text('Content', style: TextStyle(color: Colors.white60, fontSize: 11)),
              ]),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Today KPIs ────────────────────────────────────────────────────────────────
class _TodayKPIs extends StatelessWidget {
  final Map<String, dynamic> today;
  final Map<String, dynamic> cache;
  const _TodayKPIs({required this.today, required this.cache});

  @override
  Widget build(BuildContext context) {
    final cacheHitRates = cache['hit_rates_7d'] as Map<String, dynamic>? ?? {};
    final l2Pct = (cacheHitRates['l2'] as Map?)?['pct'] ?? 0;

    return Container(
      color: AppColors.white,
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(
          children: [
            KPICard(icon: '👥', label: 'Active Today',
                value: '${today['active_users'] ?? 0}', color: AppColors.primary),
            const SizedBox(width: 10),
            KPICard(icon: '💬', label: 'Sessions Today',
                value: '${today['sessions'] ?? 0}', color: AppColors.success),
            const SizedBox(width: 10),
            KPICard(icon: '❓', label: 'Questions Today',
                value: '${today['messages'] ?? 0}', color: AppColors.warning),
            const SizedBox(width: 10),
            KPICard(icon: '⚡', label: 'L2 Cache Hit',
                value: '$l2Pct%', color: AppColors.info),
          ],
        ),
      ),
    );
  }
}

// ── Students Tab ─────────────────────────────────────────────────────────────
class _StudentsTab extends ConsumerWidget {
  final int? selectedGrade;
  final ValueChanged<int?> onGradeChanged;
  const _StudentsTab({required this.selectedGrade, required this.onGradeChanged});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final studentsAsync = ref.watch(schoolStudentsProvider);

    return Column(
      children: [
        // Grade filter chips
        _GradeFilter(selected: selectedGrade, onChanged: (g) {
          onGradeChanged(g);
          ref.read(schoolStudentsProvider.notifier).load(grade: g);
        }),

        // Student list
        Expanded(
          child: studentsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => _ErrorView(message: e.toString()),
            data: (data) {
              final students = data['students'] as List<dynamic>;
              final total    = data['total'] as int? ?? 0;
              final pages    = data['pages'] as int? ?? 1;
              final page     = data['page']  as int? ?? 1;

              if (students.isEmpty) {
                return const _EmptyState(
                  icon: '👥', message: 'No students found');
              }

              return Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      children: [
                        Text('$total students',
                            style: const TextStyle(
                                color: AppColors.gray400, fontSize: 13)),
                        const Spacer(),
                        // Sort options
                        DropdownButton<String>(
                          value: 'brain_coins',
                          underline: const SizedBox(),
                          items: const [
                            DropdownMenuItem(value: 'brain_coins',   child: Text('By Coins')),
                            DropdownMenuItem(value: 'streak_days',   child: Text('By Streak')),
                            DropdownMenuItem(value: 'last_active',   child: Text('By Activity')),
                            DropdownMenuItem(value: 'created_at',    child: Text('By Joined')),
                          ],
                          onChanged: (v) {
                            if (v != null) {
                              ref.read(schoolStudentsProvider.notifier)
                                  .load(sortBy: v);
                            }
                          },
                          style: const TextStyle(
                              color: AppColors.primary, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                      itemCount: students.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, i) {
                        final s = students[i] as Map<String, dynamic>;
                        return _StudentCard(student: s, rank: i + 1)
                            .animate(delay: (i * 40).ms)
                            .fadeIn().slideX(begin: 0.1);
                      },
                    ),
                  ),
                  // Pagination
                  if (pages > 1)
                    _Pagination(
                      page: page, pages: pages,
                      onPrev: () => ref.read(schoolStudentsProvider.notifier)
                          .load(page: page - 1),
                      onNext: () => ref.read(schoolStudentsProvider.notifier)
                          .load(page: page + 1),
                    ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _StudentCard extends StatelessWidget {
  final Map<String, dynamic> student;
  final int rank;
  const _StudentCard({required this.student, required this.rank});

  @override
  Widget build(BuildContext context) {
    final name       = student['display_name'] as String? ?? 'Student';
    final grade      = student['grade'];
    final coins      = student['brain_coins'] ?? 0;
    final streak     = student['streak_days'] ?? 0;
    final mastery    = (student['overall_mastery_pct'] as num?)?.toDouble() ?? 0;
    final sessions   = student['total_sessions'] ?? 0;
    final educatId   = student['educat_id'] as String? ?? '';
    final tier       = student['tier'] as String? ?? 'free';
    final tierColor  = AppColors.forTier(tier);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            // Rank badge
            Container(
              width: 32, height: 32,
              decoration: BoxDecoration(
                color: rank <= 3
                    ? [AppColors.accent, AppColors.gray400,
                       const Color(0xFFCD7F32)][rank - 1]
                    : AppColors.gray100,
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text('$rank',
                    style: TextStyle(
                        color: rank <= 3 ? Colors.white : AppColors.gray600,
                        fontWeight: FontWeight.bold,
                        fontSize: 12)),
              ),
            ),
            const SizedBox(width: 12),

            // Avatar
            CircleAvatar(
              radius: 20,
              backgroundColor: tierColor.withOpacity(0.15),
              child: Text(
                name.isNotEmpty ? name[0].toUpperCase() : '?',
                style: TextStyle(color: tierColor, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(width: 12),

            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Flexible(
                      child: Text(name,
                          style: const TextStyle(fontWeight: FontWeight.w600,
                              fontSize: 14),
                          maxLines: 1, overflow: TextOverflow.ellipsis),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.primaryLight,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text('Cl.$grade',
                          style: const TextStyle(color: AppColors.primary,
                              fontSize: 10, fontWeight: FontWeight.w600)),
                    ),
                  ]),
                  const SizedBox(height: 2),
                  Text(educatId,
                      style: const TextStyle(
                          color: AppColors.gray400, fontSize: 10,
                          letterSpacing: 0.5)),
                  const SizedBox(height: 6),
                  // Mastery bar
                  LinearProgressIndicator(
                    value: mastery / 100,
                    backgroundColor: AppColors.gray100,
                    color: mastery >= 70 ? AppColors.success
                        : mastery >= 40 ? AppColors.warning : AppColors.error,
                    minHeight: 4,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),

            // Stats column
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Row(children: [
                  const Text('🧠', style: TextStyle(fontSize: 12)),
                  Text('$coins',
                      style: const TextStyle(fontWeight: FontWeight.bold,
                          fontSize: 13)),
                ]),
                const SizedBox(height: 2),
                Text('🔥 $streak days',
                    style: const TextStyle(color: AppColors.gray400,
                        fontSize: 11)),
                const SizedBox(height: 2),
                Text('${mastery.toStringAsFixed(0)}% mastery',
                    style: TextStyle(
                        fontSize: 11,
                        color: mastery >= 70 ? AppColors.success : AppColors.gray400)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ── Subjects Tab ─────────────────────────────────────────────────────────────
class _SubjectsTab extends ConsumerWidget {
  const _SubjectsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subjectsAsync = ref.watch(schoolSubjectsProvider);
    return subjectsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:   (e, _) => _ErrorView(message: e.toString()),
      data: (data) {
        final subjects = data['subjects'] as List<dynamic>;
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: subjects.length,
          separatorBuilder: (_, __) => const SizedBox(height: 10),
          itemBuilder: (context, i) {
            final s = subjects[i] as Map<String, dynamic>;
            return _SubjectStatCard(subject: s)
                .animate(delay: (i * 60).ms).fadeIn().slideY(begin: 0.2);
          },
        );
      },
    );
  }
}

class _SubjectStatCard extends StatelessWidget {
  final Map<String, dynamic> subject;
  const _SubjectStatCard({required this.subject});

  @override
  Widget build(BuildContext context) {
    final name       = subject['subject'] as String;
    final mastery    = (subject['avg_mastery_pct'] as num?)?.toDouble() ?? 0;
    final sessions   = subject['total_sessions'] ?? 0;
    final students   = subject['unique_students'] ?? 0;
    final messages   = subject['total_messages'] ?? 0;
    final chunks     = subject['total_chunks'] ?? 0;
    final videos     = subject['videos'] ?? 0;
    final pdfs       = subject['pdfs'] ?? 0;
    final color      = AppColors.forSubject(name);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border(left: BorderSide(color: color, width: 4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            SubjectIcon(subject: name, size: 40),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name.toUpperCase(),
                      style: TextStyle(color: color, fontWeight: FontWeight.bold,
                          fontSize: 14, letterSpacing: 1)),
                  Text('$students students • $sessions sessions',
                      style: const TextStyle(color: AppColors.gray400, fontSize: 12)),
                ],
              ),
            ),
            CircularPercentIndicator(
              radius: 30,
              lineWidth: 5,
              percent: mastery / 100,
              center: Text('${mastery.toStringAsFixed(0)}%',
                  style: TextStyle(color: color, fontWeight: FontWeight.bold,
                      fontSize: 11)),
              progressColor: color,
              backgroundColor: color.withOpacity(0.1),
            ),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            _SubjectStat(label: 'Chunks', value: '$chunks'),
            _SubjectStat(label: 'Videos', value: '$videos'),
            _SubjectStat(label: 'PDFs', value: '$pdfs'),
            _SubjectStat(label: 'Messages', value: '$messages'),
          ]),
        ],
      ),
    );
  }
}

class _SubjectStat extends StatelessWidget {
  final String label, value;
  const _SubjectStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) => Expanded(
    child: Column(
      children: [
        Text(value, style: const TextStyle(
            fontWeight: FontWeight.bold, fontSize: 15)),
        Text(label, style: const TextStyle(
            color: AppColors.gray400, fontSize: 10)),
      ],
    ),
  );
}

// ── Weak Students Tab ─────────────────────────────────────────────────────────
class _WeakStudentsTab extends ConsumerWidget {
  const _WeakStudentsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final weakAsync = ref.watch(weakStudentsProvider);
    return weakAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:   (e, _) => _ErrorView(message: e.toString()),
      data: (data) {
        final students = data['weak_students'] as List<dynamic>;
        if (students.isEmpty) {
          return const _EmptyState(icon: '🎉',
              message: 'All students are doing well!');
        }
        return Column(
          children: [
            Container(
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.error.withOpacity(0.3)),
              ),
              child: Row(children: [
                const Icon(Icons.warning_amber_rounded,
                    color: AppColors.error),
                const SizedBox(width: 10),
                Text('${students.length} students need extra attention',
                    style: const TextStyle(color: AppColors.error,
                        fontWeight: FontWeight.w600)),
              ]),
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                itemCount: students.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (context, i) {
                  final s = students[i] as Map<String, dynamic>;
                  final mastery = (s['avg_mastery_pct'] as num?)?.toDouble() ?? 0;
                  final weakTopics = s['weak_topics_count'] ?? 0;
                  final name = s['display_name'] as String? ?? 'Student';
                  final educatId = s['educat_id'] as String? ?? '';

                  return Card(
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: AppColors.error.withOpacity(0.1),
                        child: Text(name.isNotEmpty ? name[0] : '?',
                            style: const TextStyle(color: AppColors.error,
                                fontWeight: FontWeight.bold)),
                      ),
                      title: Text(name,
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text('$educatId • $weakTopics weak topics',
                          style: const TextStyle(fontSize: 11,
                              color: AppColors.gray400)),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: AppColors.error.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text('${mastery.toStringAsFixed(0)}%',
                            style: const TextStyle(color: AppColors.error,
                                fontWeight: FontWeight.bold)),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

// ── Activity Tab ─────────────────────────────────────────────────────────────
class _ActivityTab extends StatelessWidget {
  final List<dynamic> activity;
  const _ActivityTab({required this.activity});

  @override
  Widget build(BuildContext context) {
    if (activity.isEmpty) {
      return const _EmptyState(icon: '📈', message: 'No activity data yet');
    }

    final maxMessages = activity
        .map((a) => (a['messages'] as num?)?.toDouble() ?? 0)
        .fold<double>(0, (a, b) => a > b ? a : b);

    final barGroups = activity.asMap().entries.map((e) {
      final msgs = (e.value['messages'] as num?)?.toDouble() ?? 0;
      return BarChartGroupData(x: e.key, barRods: [
        BarChartRodData(
          toY: msgs,
          color: AppColors.primary,
          width: 10,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
        ),
      ]);
    }).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Messages per Day (Last 30 Days)',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
          const SizedBox(height: 16),
          Container(
            height: 220,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(16),
            ),
            child: BarChart(
              BarChartData(
                maxY: maxMessages * 1.2,
                barGroups: barGroups,
                gridData: FlGridData(
                  horizontalInterval: maxMessages / 4,
                  getDrawingHorizontalLine: (_) => FlLine(
                    color: AppColors.gray100, strokeWidth: 1),
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true, interval: 5,
                      getTitlesWidget: (v, _) => Text(
                        '${v.toInt() + 1}',
                        style: const TextStyle(
                            fontSize: 9, color: AppColors.gray400),
                      ),
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true, reservedSize: 32,
                      getTitlesWidget: (v, _) => Text(
                        v.toInt().toString(),
                        style: const TextStyle(
                            fontSize: 9, color: AppColors.gray400),
                      ),
                    ),
                  ),
                  topTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  rightTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Summary cards
          Row(children: [
            Expanded(child: _SummaryCard(
              label: 'Total Messages',
              value: '${activity.fold<int>(0, (s, a) => s + ((a['messages'] as num?)?.toInt() ?? 0))}',
              icon: '💬', color: AppColors.primary,
            )),
            const SizedBox(width: 10),
            Expanded(child: _SummaryCard(
              label: 'Total Sessions',
              value: '${activity.fold<int>(0, (s, a) => s + ((a['sessions'] as num?)?.toInt() ?? 0))}',
              icon: '📖', color: AppColors.success,
            )),
          ]),
        ],
      ),
    );
  }
}

// ── Admin Dashboard Screen ────────────────────────────────────────────────────
class AdminDashboardScreen extends ConsumerStatefulWidget {
  const AdminDashboardScreen({super.key});
  @override
  ConsumerState<AdminDashboardScreen> createState() => _AdminDashboardState();
}

class _AdminDashboardState extends ConsumerState<AdminDashboardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 5, vsync: this);
  }

  @override
  void dispose() { _tabs.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final overviewAsync = ref.watch(
        FutureProvider<Map<String, dynamic>>((ref) =>
            ref.read(apiServiceProvider).getAdminOverview()).future.asFuture());

    return Scaffold(
      backgroundColor: AppColors.gray50,
      appBar: AppBar(
        title: const Text('Admin Dashboard'),
        backgroundColor: AppColors.primaryDark,
        foregroundColor: Colors.white,
        actions: [
          FutureBuilder<Map<String, dynamic>>(
            future: ref.read(apiServiceProvider).getSystemAlerts(),
            builder: (context, snap) {
              final count = snap.data?['critical'] ?? 0;
              return Stack(children: [
                IconButton(
                  icon: const Icon(Icons.notifications_outlined, color: Colors.white),
                  onPressed: () => _showAlerts(context),
                ),
                if (count > 0) Positioned(
                  right: 8, top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                        color: AppColors.error, shape: BoxShape.circle),
                    child: Text('$count',
                        style: const TextStyle(color: Colors.white, fontSize: 9)),
                  ),
                ),
              ]);
            },
          ),
        ],
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white54,
          indicatorColor: AppColors.accent,
          tabAlignment: TabAlignment.start,
          tabs: const [
            Tab(text: '🏠 Overview'),
            Tab(text: '🏫 Schools'),
            Tab(text: '💰 Revenue'),
            Tab(text: '⚡ Cache'),
            Tab(text: '⚠️ Alerts'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: const [
          _AdminOverviewTab(),
          _AdminSchoolsTab(),
          _AdminRevenueTab(),
          _AdminCacheTab(),
          _AdminAlertsTab(),
        ],
      ),
    );
  }

  void _showAlerts(BuildContext context) {
    showModalBottomSheet(
      context: context, isScrollControlled: true,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => const _AlertsSheet(),
    );
  }
}

// ── Admin Overview Tab ────────────────────────────────────────────────────────
class _AdminOverviewTab extends ConsumerWidget {
  const _AdminOverviewTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overviewAsync = ref.watch(
      FutureProvider<Map<String, dynamic>>((ref) =>
          ref.read(apiServiceProvider).getAdminOverview()),
    );

    return overviewAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => _ErrorView(message: e.toString()),
      data: (data) {
        final users   = data['users']   as Map<String, dynamic>;
        final today   = data['today']   as Map<String, dynamic>;
        final schools = data['schools'] as Map<String, dynamic>;
        final cache   = data['cache']   as Map<String, dynamic>;
        final content = data['content'] as Map<String, dynamic>;

        final byTier = users['by_tier'] as Map<String, dynamic>;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Platform KPIs
              _SectionTitle('📊 Platform Overview'),
              GridView.count(
                crossAxisCount: 2, shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisSpacing: 12, mainAxisSpacing: 12,
                childAspectRatio: 1.4,
                children: [
                  StatCard(icon: '👥', label: 'Total Users',
                      value: '${users['total'] ?? 0}', color: AppColors.primary),
                  StatCard(icon: '🏫', label: 'Active Schools',
                      value: '${schools['total'] ?? 0}', color: AppColors.success),
                  StatCard(icon: '💬', label: 'DAU',
                      value: '${today['dau'] ?? 0}', color: AppColors.warning),
                  StatCard(icon: '📚', label: 'Content Pieces',
                      value: '${content['total_pieces'] ?? 0}', color: AppColors.info),
                ],
              ).animate().fadeIn(),
              const SizedBox(height: 20),

              // Users by tier
              _SectionTitle('👑 Users by Tier'),
              _TierBreakdown(byTier: byTier).animate().fadeIn(delay: 200.ms),
              const SizedBox(height: 20),

              // Cache health
              _SectionTitle('⚡ Cache Performance (7d)'),
              _CacheOverviewCard(cache: cache).animate().fadeIn(delay: 300.ms),
              const SizedBox(height: 20),

              // User growth chart
              _SectionTitle('📈 User Growth (30 Days)'),
              _UserGrowthChart(growth: users['growth_30d'] as List<dynamic>)
                  .animate().fadeIn(delay: 400.ms),
            ],
          ),
        );
      },
    );
  }
}

class _TierBreakdown extends StatelessWidget {
  final Map<String, dynamic> byTier;
  const _TierBreakdown({required this.byTier});

  @override
  Widget build(BuildContext context) {
    final total = (byTier.values.fold<int>(0, (a, b) => a + (b as int)));
    final tiers = ['free', 'smart', 'genius'];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: tiers.map((tier) {
          final count  = (byTier[tier] as int?) ?? 0;
          final pct    = total > 0 ? count / total : 0.0;
          final color  = AppColors.forTier(tier);
          final label  = tier == 'genius' ? '✨ GENIUS'
              : tier == 'smart' ? '⚡ SMART' : '🆓 FREE';
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(children: [
              SizedBox(width: 80,
                  child: Text(label, style: TextStyle(color: color,
                      fontWeight: FontWeight.w600, fontSize: 12))),
              Expanded(child: LinearProgressIndicator(
                value: pct.toDouble(),
                backgroundColor: color.withOpacity(0.1),
                color: color, minHeight: 8,
                borderRadius: BorderRadius.circular(4),
              )),
              const SizedBox(width: 12),
              SizedBox(width: 50,
                  child: Text('$count', textAlign: TextAlign.right,
                      style: const TextStyle(fontWeight: FontWeight.bold))),
            ]),
          );
        }).toList(),
      ),
    );
  }
}

class _CacheOverviewCard extends StatelessWidget {
  final Map<String, dynamic> cache;
  const _CacheOverviewCard({required this.cache});

  @override
  Widget build(BuildContext context) {
    final hitRates = cache['hit_rates_7d'] as Map<String, dynamic>? ?? {};
    final l1 = (hitRates['l1'] as Map?)?['pct'] ?? 0;
    final l2 = (hitRates['l2'] as Map?)?['pct'] ?? 0;
    final l3 = (hitRates['l3'] as Map?)?['pct'] ?? 0;
    final cacheSize = cache['semantic_cache_size'] ?? 0;
    final redis = cache['redis_memory'] as Map? ?? {};

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(children: [
        _CacheRow(label: 'L1 Redis (Exact)', pct: l1.toDouble(),
            color: AppColors.success),
        _CacheRow(label: 'L2 Semantic', pct: l2.toDouble(),
            color: AppColors.primary),
        _CacheRow(label: 'L3 Personal', pct: l3.toDouble(),
            color: AppColors.info),
        const Divider(height: 20),
        Row(children: [
          Text('Semantic cache: $cacheSize entries',
              style: const TextStyle(color: AppColors.gray400, fontSize: 12)),
          const Spacer(),
          Text('Redis: ${redis['used_memory_mb'] ?? 0}MB',
              style: const TextStyle(color: AppColors.gray400, fontSize: 12)),
        ]),
      ]),
    );
  }
}

class _CacheRow extends StatelessWidget {
  final String label;
  final double pct;
  final Color color;
  const _CacheRow({required this.label, required this.pct, required this.color});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(children: [
      SizedBox(width: 130, child: Text(label,
          style: const TextStyle(fontSize: 13))),
      Expanded(child: LinearProgressIndicator(
        value: pct / 100, color: color,
        backgroundColor: color.withOpacity(0.1),
        minHeight: 8, borderRadius: BorderRadius.circular(4),
      )),
      const SizedBox(width: 10),
      Text('$pct%', style: TextStyle(color: color,
          fontWeight: FontWeight.bold, fontSize: 13)),
    ]),
  );
}

class _UserGrowthChart extends StatelessWidget {
  final List<dynamic> growth;
  const _UserGrowthChart({required this.growth});

  @override
  Widget build(BuildContext context) {
    if (growth.isEmpty) return const SizedBox();
    final spots = growth.asMap().entries.map((e) =>
        FlSpot(e.key.toDouble(),
            (e.value['new_users'] as num?)?.toDouble() ?? 0)).toList();

    return Container(
      height: 160, padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.white, borderRadius: BorderRadius.circular(16)),
      child: LineChart(LineChartData(
        gridData: FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          leftTitles: AxisTitles(sideTitles: SideTitles(
            showTitles: true, reservedSize: 28,
            getTitlesWidget: (v, _) => Text(v.toInt().toString(),
                style: const TextStyle(fontSize: 9, color: AppColors.gray400)),
          )),
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        lineBarsData: [LineChartBarData(
          spots: spots, isCurved: true,
          color: AppColors.primary, barWidth: 3,
          dotData: FlDotData(show: false),
          belowBarData: BarAreaData(
            show: true, color: AppColors.primary.withOpacity(0.1)),
        )],
      )),
    );
  }
}

class _AdminSchoolsTab extends ConsumerWidget {
  const _AdminSchoolsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final schoolsAsync = ref.watch(
      FutureProvider<Map<String, dynamic>>((ref) =>
          ref.read(apiServiceProvider).getAdminSchools()),
    );
    return schoolsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:   (e, _) => _ErrorView(message: e.toString()),
      data: (data) {
        final schools = data['schools'] as List<dynamic>;
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: schools.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, i) {
            final s = schools[i] as Map<String, dynamic>;
            final quotaPct = (s['quota_used_pct'] as num?)?.toDouble() ?? 0;
            return Card(child: ListTile(
              leading: Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: AppColors.primaryLight,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(child: Text(
                  (s['school_name'] as String? ?? 'S')[0].toUpperCase(),
                  style: const TextStyle(color: AppColors.primary,
                      fontWeight: FontWeight.bold, fontSize: 18),
                )),
              ),
              title: Text(s['school_name'] as String? ?? '',
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text(
                '${s['school_code']} • ${s['plan_type']} • '
                '${s['teachers']} teachers',
                style: const TextStyle(fontSize: 11, color: AppColors.gray400),
              ),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('$quotaPct%',
                      style: TextStyle(
                          color: quotaPct > 80 ? AppColors.error
                              : quotaPct > 60 ? AppColors.warning
                              : AppColors.success,
                          fontWeight: FontWeight.bold)),
                  const Text('quota used',
                      style: TextStyle(color: AppColors.gray400, fontSize: 10)),
                ],
              ),
            ));
          },
        );
      },
    );
  }
}

class _AdminRevenueTab extends ConsumerWidget {
  const _AdminRevenueTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final revenueAsync = ref.watch(
      FutureProvider<Map<String, dynamic>>((ref) =>
          ref.read(apiServiceProvider).getAdminRevenue()),
    );
    return revenueAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:   (e, _) => _ErrorView(message: e.toString()),
      data: (data) {
        final monthly = data['monthly_revenue'] as List<dynamic>;
        final total   = data['total_active']    as Map<String, dynamic>;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Expanded(child: _SummaryCard(
                  label: 'Active Subscriptions',
                  value: '${total['total_subs'] ?? 0}',
                  icon: '🎫', color: AppColors.primary,
                )),
                const SizedBox(width: 10),
                Expanded(child: _SummaryCard(
                  label: 'Total Revenue',
                  value: '₹${total['total_inr'] ?? 0}',
                  icon: '💰', color: AppColors.success,
                )),
              ]),
              const SizedBox(height: 20),
              const Text('Monthly Breakdown',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
              const SizedBox(height: 10),
              ...monthly.map((m) {
                final month   = m['month'] as String? ?? '';
                final tier    = m['tier']  as String? ?? '';
                final subs    = m['subscriptions'] ?? 0;
                final revenue = m['revenue_inr'] ?? 0;
                return Card(child: ListTile(
                  leading: Text(
                    tier == 'genius' ? '✨' : tier == 'smart' ? '⚡' : '🆓',
                    style: const TextStyle(fontSize: 24),
                  ),
                  title: Text(month.substring(0, 7),
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text('$subs subscribers',
                      style: const TextStyle(fontSize: 12)),
                  trailing: Text('₹$revenue',
                      style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          color: AppColors.success, fontSize: 15)),
                ));
              }),
            ],
          ),
        );
      },
    );
  }
}

class _AdminCacheTab extends ConsumerWidget {
  const _AdminCacheTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cacheAsync = ref.watch(
      FutureProvider<Map<String, dynamic>>((ref) =>
          ref.read(apiServiceProvider).getCacheHealth()),
    );
    return cacheAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:   (e, _) => _ErrorView(message: e.toString()),
      data: (data) {
        final l1     = data['l1_redis']    as Map<String, dynamic>;
        final l2     = data['l2_semantic'] as Map<String, dynamic>;
        final audio  = data['audio_cache'] as Map<String, dynamic>;
        final l2Data = l2['by_subject_grade'] as List<dynamic>;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Expanded(child: _SummaryCard(
                  label: 'L1 Redis Keys',
                  value: '${l1['key_count'] ?? 0}',
                  icon: '⚡', color: AppColors.success,
                )),
                const SizedBox(width: 10),
                Expanded(child: _SummaryCard(
                  label: 'L2 Entries',
                  value: '${l2Data.fold<int>(0, (s, r) => s + ((r['entries'] as int?) ?? 0))}',
                  icon: '🧠', color: AppColors.primary,
                )),
              ]),
              const SizedBox(height: 16),
              const Text('Semantic Cache by Subject',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
              const SizedBox(height: 10),
              ...l2Data.map((r) {
                final subj  = r['subject'] as String? ?? '';
                final grade = r['grade'];
                final hits  = r['total_hits'] ?? 0;
                final entries = r['entries'] ?? 0;
                final color = AppColors.forSubject(subj);
                return Card(child: ListTile(
                  leading: SubjectIcon(subject: subj, size: 36),
                  title: Text('${subj.toUpperCase()} • Class $grade',
                      style: const TextStyle(fontWeight: FontWeight.w600,
                          fontSize: 13)),
                  subtitle: Text('$entries entries',
                      style: const TextStyle(fontSize: 11)),
                  trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.bolt, color: AppColors.warning, size: 14),
                    Text('$hits hits',
                        style: const TextStyle(fontWeight: FontWeight.bold,
                            color: AppColors.warning)),
                  ]),
                ));
              }),
            ],
          ),
        );
      },
    );
  }
}

class _AdminAlertsTab extends ConsumerWidget {
  const _AdminAlertsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertsAsync = ref.watch(
      FutureProvider<Map<String, dynamic>>((ref) =>
          ref.read(apiServiceProvider).getSystemAlerts()),
    );
    return alertsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:   (e, _) => _ErrorView(message: e.toString()),
      data: (data) {
        final alerts = data['alerts'] as List<dynamic>;
        if (alerts.isEmpty) {
          return const _EmptyState(icon: '✅',
              message: 'All systems healthy!');
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: alerts.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, i) {
            final a     = alerts[i] as Map<String, dynamic>;
            final level = a['level'] as String? ?? 'info';
            final color = level == 'critical' ? AppColors.error
                : level == 'warning' ? AppColors.warning : AppColors.info;
            final icon  = level == 'critical' ? '🚨'
                : level == 'warning' ? '⚠️' : 'ℹ️';
            return Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: color.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: color.withOpacity(0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text(icon), const SizedBox(width: 8),
                    Expanded(child: Text(a['message'] as String? ?? '',
                        style: TextStyle(fontWeight: FontWeight.w600,
                            color: color))),
                  ]),
                  const SizedBox(height: 6),
                  Text(a['action'] as String? ?? '',
                      style: const TextStyle(color: AppColors.gray400,
                          fontSize: 12)),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _AlertsSheet extends StatelessWidget {
  const _AlertsSheet();
  @override
  Widget build(BuildContext context) =>
      const SizedBox(height: 400, child: _AdminAlertsTab());
}

// ── Shared Widgets ─────────────────────────────────────────────────────────────
class _GradeFilter extends StatelessWidget {
  final int? selected;
  final ValueChanged<int?> onChanged;
  const _GradeFilter({required this.selected, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(children: [
        _GradeChip(label: 'All', value: null, selected: selected == null,
            onTap: () => onChanged(null)),
        ...List.generate(10, (i) => _GradeChip(
          label: 'Cl.${i + 1}', value: i + 1,
          selected: selected == i + 1,
          onTap: () => onChanged(i + 1),
        )),
      ]),
    );
  }
}

class _GradeChip extends StatelessWidget {
  final String label;
  final int? value;
  final bool selected;
  final VoidCallback onTap;
  const _GradeChip({
    required this.label, required this.value,
    required this.selected, required this.onTap,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(right: 6),
    child: GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: selected ? AppColors.primary : AppColors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
              color: selected ? AppColors.primary : AppColors.gray200),
        ),
        child: Text(label, style: TextStyle(
            color: selected ? Colors.white : AppColors.gray600,
            fontWeight: FontWeight.w500, fontSize: 13)),
      ),
    ),
  );
}

class _Pagination extends StatelessWidget {
  final int page, pages;
  final VoidCallback onPrev, onNext;
  const _Pagination({
    required this.page, required this.pages,
    required this.onPrev, required this.onNext,
  });

  @override
  Widget build(BuildContext context) => Container(
    color: AppColors.white,
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
      IconButton(
        onPressed: page > 1 ? onPrev : null,
        icon: const Icon(Icons.chevron_left_rounded),
      ),
      Text('Page $page of $pages',
          style: const TextStyle(fontWeight: FontWeight.w500)),
      IconButton(
        onPressed: page < pages ? onNext : null,
        icon: const Icon(Icons.chevron_right_rounded),
      ),
    ]),
  );
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle(this.title);
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Text(title, style: const TextStyle(
        fontWeight: FontWeight.w600, fontSize: 15)),
  );
}

class _SummaryCard extends StatelessWidget {
  final String label, value, icon;
  final Color color;
  const _SummaryCard({
    required this.label, required this.value,
    required this.icon, required this.color,
  });

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: color.withOpacity(0.08),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: color.withOpacity(0.2)),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(icon, style: const TextStyle(fontSize: 24)),
      const SizedBox(height: 8),
      Text(value, style: TextStyle(
          color: color, fontWeight: FontWeight.bold, fontSize: 20)),
      Text(label, style: const TextStyle(
          color: AppColors.gray400, fontSize: 12)),
    ]),
  );
}

class _ErrorView extends StatelessWidget {
  final String message;
  const _ErrorView({required this.message});
  @override
  Widget build(BuildContext context) => Center(child: Column(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      const Icon(Icons.error_outline, color: AppColors.error, size: 48),
      const SizedBox(height: 12),
      Text('Error loading data', style: const TextStyle(
          fontWeight: FontWeight.w600, fontSize: 16)),
      const SizedBox(height: 6),
      Text(message, style: const TextStyle(color: AppColors.gray400,
          fontSize: 12), textAlign: TextAlign.center),
    ],
  ));
}

class _EmptyState extends StatelessWidget {
  final String icon, message;
  const _EmptyState({required this.icon, required this.message});
  @override
  Widget build(BuildContext context) => Center(child: Column(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      Text(icon, style: const TextStyle(fontSize: 48)),
      const SizedBox(height: 12),
      Text(message, style: const TextStyle(color: AppColors.gray400,
          fontSize: 14)),
    ],
  ));
}

class _SliverTabDelegate extends SliverPersistentHeaderDelegate {
  final TabBar tabBar;
  const _SliverTabDelegate(this.tabBar);
  @override
  Widget build(BuildContext c, double shrinkOffset, bool overlapsContent) =>
      Container(color: AppColors.white, child: tabBar);
  @override double get minExtent => tabBar.preferredSize.height;
  @override double get maxExtent => tabBar.preferredSize.height;
  @override bool shouldRebuild(_) => false;
}

// Extensions
extension FutureExt<T> on Future<T> {
  Future<T> asFuture() => this;
}
