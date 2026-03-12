import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import '../data/reputation_models.dart';

class ReputationProgressBar extends StatelessWidget {
  const ReputationProgressBar({
    super.key,
    required this.progress,
  });

  final PrestigeTierProgress progress;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                progress.nextTier == null
                    ? 'Top prestige band reached'
                    : '${progress.pointsToNextTier} pts to ${progress.nextTier!.label}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            Text(
              '${progress.currentScore}',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: GteShellTheme.textPrimary,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            minHeight: 12,
            value: progress.normalizedProgress,
            backgroundColor: GteShellTheme.panelStrong,
            valueColor:
                const AlwaysStoppedAnimation<Color>(GteShellTheme.accent),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: <Widget>[
            Text(
              '${progress.floorScore}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            Text(
              progress.ceilingScore?.toString() ?? 'MAX',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ],
    );
  }
}
