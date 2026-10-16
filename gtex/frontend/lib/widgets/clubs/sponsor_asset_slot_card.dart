import 'package:flutter/material.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class SponsorAssetSlotCard extends StatelessWidget {
  const SponsorAssetSlotCard({
    super.key,
    required this.slot,
  });

  final SponsorAssetSlot slot;

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
                  slot.surfaceName,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              Chip(label: Text(_moderationLabel(slot.moderationState))),
            ],
          ),
          const SizedBox(height: 8),
          Text(slot.placementLabel, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(slot.visibilityLabel, style: Theme.of(context).textTheme.bodyMedium),
          if (slot.sponsorName != null) ...<Widget>[
            const SizedBox(height: 8),
            Text('Sponsor: ${slot.sponsorName}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: _moderationColor(slot.moderationState),
                    )),
          ],
          if (slot.note != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(slot.note!, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ],
      ),
    );
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
