// lib/widgets/stat_card.dart
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class StatCard extends StatelessWidget {
  final String icon, label, value;
  final Color color;
  const StatCard({
    super.key, required this.icon, required this.label,
    required this.value, required this.color,
  });

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: color.withOpacity(0.08),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: color.withOpacity(0.2)),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(icon, style: const TextStyle(fontSize: 22)),
      const SizedBox(height: 6),
      Text(value, style: TextStyle(
          color: color, fontWeight: FontWeight.bold, fontSize: 18)),
      Text(label, style: const TextStyle(
          color: AppColors.gray400, fontSize: 11)),
    ]),
  );
}
