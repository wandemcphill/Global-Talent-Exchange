import 'package:flutter/material.dart';

import '../constants/app_spacing.dart';

class BadgeIcon extends StatelessWidget {
  const BadgeIcon({
    super.key,
    this.icon = Icons.local_fire_department_rounded,
    this.color = Colors.orange,
    this.size = 16,
  });

  final IconData icon;
  final Color color;
  final double size;

  const BadgeIcon.fire({super.key})
      : icon = Icons.local_fire_department_rounded,
        color = Colors.orange,
        size = 16;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Icon(icon, color: color, size: size),
    );
  }
}
