import 'package:flutter/material.dart';

import '../../models/referral_models.dart';
import '../gte_shell_theme.dart';
import '../gte_surface_panel.dart';

class MilestoneProgressCard extends StatelessWidget {
  const MilestoneProgressCard({
    super.key,
    required this.milestones,
  });

  final List<MilestoneProgress> milestones;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Milestone progress',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          for (int index = 0; index < milestones.length; index++) ...<Widget>[
            _MilestoneTile(milestone: milestones[index]),
            if (index < milestones.length - 1) const SizedBox(height: 16),
          ],
        ],
      ),
    );
  }
}

class _MilestoneTile extends StatelessWidget {
  const _MilestoneTile({
    required this.milestone,
  });

  final MilestoneProgress milestone;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                milestone.title,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            Text(
              '${milestone.currentValue}/${milestone.targetValue}',
              style: Theme.of(context).textTheme.labelLarge,
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          milestone.detail,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: milestone.progress,
            minHeight: 10,
            backgroundColor: GteShellTheme.stroke,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          milestone.rewardLabel,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: milestone.unlocked
                    ? GteShellTheme.positive
                    : GteShellTheme.accentWarm,
              ),
        ),
      ],
    );
  }
}
