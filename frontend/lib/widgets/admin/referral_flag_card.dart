import 'package:flutter/material.dart';

import '../../models/referral_models.dart';
import '../gte_shell_theme.dart';
import '../gte_surface_panel.dart';

class ReferralFlagCard extends StatelessWidget {
  const ReferralFlagCard({
    super.key,
    required this.flag,
  });

  final ReferralFlagEntry flag;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  flag.issueLabel,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              Chip(
                label: Text(flag.severity.label),
                backgroundColor: _severityColor(flag.severity).withValues(alpha: 0.18),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '${flag.creatorHandle} · ${flag.shareCode}',
            style: Theme.of(context).textTheme.labelLarge,
          ),
          const SizedBox(height: 8),
          Text(
            flag.riskSignal,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          Text(
            flag.qualifiedParticipationLabel,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Review status: ${flag.reviewStatus}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Text(
            flag.recommendedAction,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GteShellTheme.accentWarm,
                ),
          ),
        ],
      ),
    );
  }
}

Color _severityColor(ReferralRiskSeverity severity) {
  switch (severity) {
    case ReferralRiskSeverity.low:
      return GteShellTheme.positive;
    case ReferralRiskSeverity.medium:
      return GteShellTheme.accentWarm;
    case ReferralRiskSeverity.high:
      return GteShellTheme.negative;
  }
}
