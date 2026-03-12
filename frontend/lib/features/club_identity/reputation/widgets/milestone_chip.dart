import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import '../data/reputation_models.dart';

class MilestoneChip extends StatelessWidget {
  const MilestoneChip({
    super.key,
    required this.milestone,
  });

  final ReputationMilestoneDto milestone;

  @override
  Widget build(BuildContext context) {
    final bool positive = milestone.delta >= 0;
    final Color tone =
        positive ? GteShellTheme.accentWarm : GteShellTheme.negative;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: tone.withValues(alpha: 0.28)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(
            positive ? Icons.workspace_premium : Icons.history_toggle_off,
            size: 16,
            color: tone,
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              milestone.title,
              style:
                  Theme.of(context).textTheme.labelLarge?.copyWith(color: tone),
            ),
          ),
        ],
      ),
    );
  }
}
