import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../widgets/gte_shell_theme.dart';
import '../models/data_source_status.dart';

class DataSourceBadge extends StatelessWidget {
  const DataSourceBadge({super.key, required this.status});

  final DataSourceStatus status;

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return const SizedBox.shrink();
    }
    final tokens = GteShellTheme.tokensOf(context);
    final theme = GteShellTheme.definitionOf(context);
    final Color color = switch (status) {
      DataSourceStatus.live => theme.primaryColor,
      DataSourceStatus.blocked => tokens.negative,
      DataSourceStatus.demo => theme.secondaryColor,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: spacingSM, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(tokens.radiusPill),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(shape: BoxShape.circle, color: color),
          ),
          const SizedBox(width: spacingXS),
          Text(
            status.label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
