import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class StatBar extends StatelessWidget {
  const StatBar(this.value, {super.key});

  final double value;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(999),
      child: LinearProgressIndicator(
        value: value.clamp(0, 1),
        minHeight: 6,
        backgroundColor: Colors.grey[800],
        valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
      ),
    );
  }
}
