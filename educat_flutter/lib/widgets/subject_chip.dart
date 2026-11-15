// lib/widgets/subject_chip.dart
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

const Map<String, String> _subjectIcons = {
  'science': '🔬', 'maths': '📐', 'hindi': '🔤',
  'english': '📖', 'sst': '🌍', 'gk': '🌟',
};

class SubjectIcon extends StatelessWidget {
  final String subject;
  final double size;
  const SubjectIcon({super.key, required this.subject, this.size = 44});

  @override
  Widget build(BuildContext context) {
    final color = AppColors.forSubject(subject);
    final icon  = _subjectIcons[subject.toLowerCase()] ?? '📚';
    return Container(
      width: size, height: size,
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(size * 0.25),
      ),
      child: Center(
        child: Text(icon, style: TextStyle(fontSize: size * 0.44)),
      ),
    );
  }
}

class SubjectFilterChip extends StatelessWidget {
  final String subject;
  final bool selected;
  final VoidCallback onTap;
  const SubjectFilterChip({
    super.key, required this.subject,
    required this.selected, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppColors.forSubject(subject);
    final icon  = _subjectIcons[subject.toLowerCase()] ?? '📚';
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: selected ? color : AppColors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: selected ? color : AppColors.gray200),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(icon, style: const TextStyle(fontSize: 14)),
          const SizedBox(width: 5),
          Text(subject[0].toUpperCase() + subject.substring(1),
              style: TextStyle(
                  color: selected ? Colors.white : AppColors.gray600,
                  fontWeight: FontWeight.w500, fontSize: 13)),
        ]),
      ),
    );
  }
}
