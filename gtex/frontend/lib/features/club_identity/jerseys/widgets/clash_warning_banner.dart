import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';

class ClashWarningBanner extends StatelessWidget {
  const ClashWarningBanner({
    super.key,
    required this.warnings,
    this.title = 'Identity check',
  });

  final List<String> warnings;
  final String title;

  @override
  Widget build(BuildContext context) {
    if (warnings.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: GteShellTheme.positive.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: GteShellTheme.positive.withValues(alpha: 0.35),
          ),
        ),
        child: Row(
          children: <Widget>[
            const Icon(
              Icons.check_circle_outline,
              color: GteShellTheme.positive,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'Home and away kits read clearly across standings, intros, and replay cards.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: GteShellTheme.textPrimary,
                    ),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: GteShellTheme.accentWarm.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: GteShellTheme.accentWarm.withValues(alpha: 0.35),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(
                Icons.warning_amber_rounded,
                color: GteShellTheme.accentWarm,
              ),
              const SizedBox(width: 10),
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...warnings.map(
            (String warning) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                '- $warning',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: GteShellTheme.textPrimary,
                    ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
