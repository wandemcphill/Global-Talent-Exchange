import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/badge_preview_widget.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/widgets/clubs/reputation_tier_badge.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubHeaderCard extends StatelessWidget {
  const ClubHeaderCard({
    super.key,
    required this.data,
  });

  final ClubDashboardData data;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool stacked = constraints.maxWidth < 760;
          final Widget summary = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  ReputationTierBadge(tier: data.reputation.profile.currentPrestigeTier),
                  _Pill(label: _dynastyEraLabel(data.dynastyProfile.currentEraLabel)),
                  if (data.countryName != null) _Pill(label: data.countryName!),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                data.clubName,
                style: Theme.of(context).textTheme.displaySmall,
              ),
              const SizedBox(height: 8),
              Text(
                data.branding.motto,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 18),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  GteMetricChip(
                    label: 'Club reputation',
                    value: '${data.reputation.profile.currentScore}',
                  ),
                  GteMetricChip(
                    label: 'Trophy cabinet',
                    value: '${data.trophyCabinet.totalHonorsCount}',
                  ),
                  GteMetricChip(
                    label: 'Dynasty score',
                    value: '${data.dynastyProfile.dynastyScore}',
                  ),
                ],
              ),
            ],
          );

          final Widget badgeColumn = Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              BadgePreviewWidget(
                badge: data.identity.badgeProfile,
                size: 128,
              ),
              const SizedBox(height: 18),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: <Widget>[
                  _ColorChip(
                    label: 'Primary',
                    colorHex: data.identity.colorPalette.primaryColor,
                  ),
                  _ColorChip(
                    label: 'Secondary',
                    colorHex: data.identity.colorPalette.secondaryColor,
                  ),
                  _ColorChip(
                    label: 'Accent',
                    colorHex: data.identity.colorPalette.accentColor,
                  ),
                ],
              ),
            ],
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                badgeColumn,
                const SizedBox(height: 20),
                summary,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              badgeColumn,
              const SizedBox(width: 24),
              Expanded(child: summary),
            ],
          );
        },
      ),
    );
  }
}

String _dynastyEraLabel(DynastyEraType value) {
  switch (value) {
    case DynastyEraType.emergingPower:
      return 'Emerging Power';
    case DynastyEraType.dominantEra:
      return 'Dominant Era';
    case DynastyEraType.continentalDynasty:
      return 'Continental Dynasty';
    case DynastyEraType.globalDynasty:
      return 'Global Dynasty';
    case DynastyEraType.fallenGiant:
      return 'Fallen Giant';
    case DynastyEraType.none:
      return 'No Active Dynasty';
  }
}

class _ColorChip extends StatelessWidget {
  const _ColorChip({
    required this.label,
    required this.colorHex,
  });

  final String label;
  final String colorHex;

  @override
  Widget build(BuildContext context) {
    final Color color = identityColorFromHex(colorHex);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.94),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge,
      ),
    );
  }
}
