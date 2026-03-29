import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../models/data_source_status.dart';

class DataSourceBadge extends StatelessWidget {
  const DataSourceBadge({super.key, required this.status});

  final DataSourceStatus status;

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return const SizedBox.shrink();
    }
    final ColorScheme colors = Theme.of(context).colorScheme;
    final Color color = switch (status) {
      DataSourceStatus.live => colors.primary,
      DataSourceStatus.blocked => colors.error,
      DataSourceStatus.demo => colors.tertiary,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: spacingSM, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        status.label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
