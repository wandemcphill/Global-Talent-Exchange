import 'package:flutter/material.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class SponsorshipContractCard extends StatelessWidget {
  const SponsorshipContractCard({
    super.key,
    required this.contract,
    this.onOpen,
  });

  final SponsorshipContract contract;
  final VoidCallback? onOpen;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onOpen,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(contract.sponsorName,
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(contract.packageName,
                        style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              Chip(label: Text(_statusLabel(contract.status))),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            '${clubOpsFormatCurrency(contract.totalValue)} · ${clubOpsFormatDate(contract.startDate)} to ${clubOpsFormatDate(contract.endDate)}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 6),
          Text(contract.renewalWindowLabel,
              style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          Text(
            'Moderation: ${_moderationLabel(contract.moderationState)}',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: _moderationColor(contract.moderationState),
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Visibility: ${contract.visibilityLabel}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }

  String _statusLabel(SponsorshipContractStatus status) {
    switch (status) {
      case SponsorshipContractStatus.active:
        return 'Active';
      case SponsorshipContractStatus.renewalDue:
        return 'Renewal due';
      case SponsorshipContractStatus.pendingApproval:
        return 'Pending approval';
      case SponsorshipContractStatus.completed:
        return 'Completed';
    }
  }

  String _moderationLabel(SponsorModerationState state) {
    switch (state) {
      case SponsorModerationState.approved:
        return 'Approved';
      case SponsorModerationState.underReview:
        return 'Under review';
      case SponsorModerationState.needsChanges:
        return 'Needs changes';
      case SponsorModerationState.blocked:
        return 'Blocked';
    }
  }

  Color _moderationColor(SponsorModerationState state) {
    switch (state) {
      case SponsorModerationState.approved:
        return GteShellTheme.positive;
      case SponsorModerationState.underReview:
        return GteShellTheme.accentWarm;
      case SponsorModerationState.needsChanges:
        return GteShellTheme.accentWarm;
      case SponsorModerationState.blocked:
        return GteShellTheme.negative;
    }
  }
}
