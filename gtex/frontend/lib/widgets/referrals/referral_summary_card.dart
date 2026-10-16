import 'package:flutter/material.dart';

import '../../models/referral_models.dart';
import '../gte_surface_panel.dart';

class ReferralSummaryCard extends StatelessWidget {
  const ReferralSummaryCard({
    super.key,
    required this.summary,
    required this.creatorHandle,
  });

  final ReferralSummary summary;
  final String creatorHandle;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Community reward summary',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Invite attribution for $creatorHandle stays tied to qualified platform milestones and contest participation.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              Expanded(
                child: _SummaryMetric(
                  label: 'Invites sent',
                  value: '${summary.invitesSent}',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _SummaryMetric(
                  label: 'Qualified referrals',
                  value: '${summary.qualifiedReferrals}',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              Expanded(
                child: _SummaryMetric(
                  label: 'Invite attribution',
                  value: '${summary.inviteAttributions}',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _SummaryMetric(
                  label: 'Reward balance',
                  value: summary.rewardBalanceLabel,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            summary.rewardDetail,
            style: Theme.of(context).textTheme.labelLarge,
          ),
        ],
      ),
    );
  }
}

class _SummaryMetric extends StatelessWidget {
  const _SummaryMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontSize: 21,
              ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    );
  }
}
