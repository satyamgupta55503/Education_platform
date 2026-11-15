// lib/widgets/common.dart — Reusable professional UI components
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shimmer/shimmer.dart';
import '../theme/app_theme.dart';

// ── AppCard ────────────────────────────────────────────────────────────────────
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? color;
  final double radius;
  final Border? border;
  final VoidCallback? onTap;
  final Gradient? gradient;

  const AppCard({
    super.key, required this.child,
    this.padding, this.color, this.radius = 16,
    this.border, this.onTap, this.gradient,
  });

  @override
  Widget build(BuildContext context) {
    final box = Container(
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: gradient == null ? (color ?? AppColors.white) : null,
        gradient: gradient,
        borderRadius: BorderRadius.circular(radius),
        border: border,
        boxShadow: const [
          BoxShadow(color: Color(0x0D000000), blurRadius: 10, offset: Offset(0, 2)),
        ],
      ),
      child: child,
    );
    if (onTap != null) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap, borderRadius: BorderRadius.circular(radius),
          child: box,
        ),
      );
    }
    return box;
  }
}

// ── GradientButton ─────────────────────────────────────────────────────────────
class GradientButton extends StatelessWidget {
  final String label;
  final VoidCallback? onTap;
  final bool loading;
  final List<Color> colors;
  final double height;
  final Widget? icon;

  const GradientButton({
    super.key, required this.label, this.onTap, this.loading = false,
    this.colors = const [Color(0xFF2563EB), Color(0xFF1E3A5F)],
    this.height = 54, this.icon,
  });

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: loading ? null : onTap,
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      height: height,
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: colors, begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(14),
        boxShadow: onTap != null ? [BoxShadow(
          color: colors.first.withOpacity(0.35), blurRadius: 16, offset: const Offset(0, 6))] : [],
      ),
      child: Center(
        child: loading
          ? const SizedBox(width: 22, height: 22,
              child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
          : Row(mainAxisSize: MainAxisSize.min, children: [
              if (icon != null) ...[icon!, const SizedBox(width: 8)],
              Text(label, style: const TextStyle(
                color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
            ]),
      ),
    ),
  );
}

// ── SubjectCard ───────────────────────────────────────────────────────────────
class SubjectCard extends StatelessWidget {
  final String subject;
  final VoidCallback onTap;
  final int index;

  const SubjectCard({super.key, required this.subject, required this.onTap, required this.index});

  @override
  Widget build(BuildContext context) {
    final color = AppColors.forSubject(subject);
    final emoji = AppColors.emojiForSubject(subject);
    final label = subject[0].toUpperCase() + subject.substring(1);
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          gradient: AppDeco.subjectGradient(subject),
          borderRadius: BorderRadius.circular(18),
          boxShadow: [BoxShadow(
            color: color.withOpacity(0.30), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(emoji, style: const TextStyle(fontSize: 30)),
          const Spacer(),
          Text(label, style: const TextStyle(
            color: Colors.white, fontWeight: FontWeight.w700, fontSize: 15)),
          const SizedBox(height: 2),
          Text('Class notes →',
            style: TextStyle(color: Colors.white.withOpacity(0.75), fontSize: 11)),
        ]),
      ),
    ).animate(delay: (index * 55).ms).fadeIn(duration: 350.ms)
     .slideY(begin: 0.25, end: 0, duration: 350.ms, curve: Curves.easeOut);
  }
}

// ── MasteryBar ────────────────────────────────────────────────────────────────
class MasteryBar extends StatelessWidget {
  final double pct;
  final String? label;
  final double height;

  const MasteryBar({super.key, required this.pct, this.label, this.height = 8});

  @override
  Widget build(BuildContext context) {
    final color = pct >= 70 ? AppColors.success
      : pct >= 40 ? AppColors.warning : AppColors.error;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (label != null) ...[
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(label!, style: const TextStyle(fontSize: 12, color: AppColors.gray500, fontWeight: FontWeight.w500)),
          Text('${pct.toStringAsFixed(0)}%', style: TextStyle(
            fontSize: 12, fontWeight: FontWeight.w700, color: color)),
        ]),
        const SizedBox(height: 6),
      ],
      ClipRRect(
        borderRadius: BorderRadius.circular(99),
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: pct / 100),
          duration: const Duration(milliseconds: 800),
          curve: Curves.easeOut,
          builder: (_, val, __) => LinearProgressIndicator(
            value: val, minHeight: height,
            backgroundColor: AppColors.gray100,
            valueColor: AlwaysStoppedAnimation(color),
          ),
        ),
      ),
    ]);
  }
}

// ── SkeletonCard ──────────────────────────────────────────────────────────────
class SkeletonCard extends StatelessWidget {
  final double height;
  final double? width;
  final double radius;

  const SkeletonCard({super.key, this.height = 120, this.width, this.radius = 16});

  @override
  Widget build(BuildContext context) => Shimmer.fromColors(
    baseColor: AppColors.gray100, highlightColor: AppColors.gray50,
    child: Container(
      height: height, width: width,
      decoration: BoxDecoration(
        color: AppColors.gray100, borderRadius: BorderRadius.circular(radius)),
    ),
  );
}

// ── TierBadge ─────────────────────────────────────────────────────────────────
class TierBadge extends StatelessWidget {
  final String tier;
  final bool small;
  const TierBadge({super.key, required this.tier, this.small = false});

  @override
  Widget build(BuildContext context) {
    final color = AppColors.forTier(tier);
    final emoji = tier == 'genius' ? '✨' : tier == 'smart' ? '⚡' : '🆓';
    final label = '$emoji ${tier.toUpperCase()}';
    return Container(
      padding: EdgeInsets.symmetric(horizontal: small ? 8 : 12, vertical: small ? 3 : 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: color.withOpacity(0.30)),
      ),
      child: Text(label, style: TextStyle(
        color: color, fontSize: small ? 10 : 12, fontWeight: FontWeight.w700)),
    );
  }
}

// ── CopyId ───────────────────────────────────────────────────────────────────
class CopyIdWidget extends StatefulWidget {
  final String id;
  const CopyIdWidget({super.key, required this.id});
  @override State<CopyIdWidget> createState() => _CopyIdWidgetState();
}
class _CopyIdWidgetState extends State<CopyIdWidget> {
  bool _copied = false;
  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.id));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }
  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: _copy,
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: _copied ? AppColors.successLight : AppColors.primaryLight,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _copied ? AppColors.success.withOpacity(0.3) : AppColors.primary.withOpacity(0.2)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(_copied ? Icons.check_rounded : Icons.badge_outlined,
          size: 14, color: _copied ? AppColors.success : AppColors.primary),
        const SizedBox(width: 6),
        Text(widget.id, style: TextStyle(
          color: _copied ? AppColors.success : AppColors.primary,
          fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 1.0,
          fontFamily: 'Courier New')),
      ]),
    ),
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────
class EmptyState extends StatelessWidget {
  final String emoji, title, subtitle;
  const EmptyState({super.key, required this.emoji, required this.title, this.subtitle = ''});
  @override
  Widget build(BuildContext context) => Center(child: Column(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      Text(emoji, style: const TextStyle(fontSize: 56)),
      const SizedBox(height: 14),
      Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.gray700)),
      if (subtitle.isNotEmpty) ...[
        const SizedBox(height: 6),
        Text(subtitle, style: const TextStyle(fontSize: 13, color: AppColors.gray400), textAlign: TextAlign.center),
      ],
    ],
  ));
}

// ── SectionHeader ─────────────────────────────────────────────────────────────
class SectionHeader extends StatelessWidget {
  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;
  const SectionHeader({super.key, required this.title, this.actionLabel, this.onAction});
  @override
  Widget build(BuildContext context) => Row(children: [
    Expanded(child: Text(title, style: const TextStyle(
      fontSize: 17, fontWeight: FontWeight.w700, color: AppColors.gray900))),
    if (actionLabel != null)
      GestureDetector(onTap: onAction, child: Text(actionLabel!, style: const TextStyle(
        fontSize: 13, color: AppColors.primary, fontWeight: FontWeight.w600))),
  ]);
}
