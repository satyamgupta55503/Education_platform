// lib/widgets/kpi_card.dart
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class KPICard extends StatelessWidget {
  final String icon, label, value;
  final Color color;
  const KPICard({
    super.key, required this.icon, required this.label,
    required this.value, required this.color,
  });

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    decoration: BoxDecoration(
      color: color.withOpacity(0.08),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: color.withOpacity(0.25)),
    ),
    child: Column(mainAxisSize: MainAxisSize.min, children: [
      Text(icon, style: const TextStyle(fontSize: 20)),
      const SizedBox(height: 4),
      Text(value, style: TextStyle(
          color: color, fontWeight: FontWeight.bold, fontSize: 17)),
      Text(label, style: const TextStyle(
          color: AppColors.gray400, fontSize: 10)),
    ]),
  );
}
