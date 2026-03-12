import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/badge_preview_widget.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/widgets/clubs/reputation_tier_badge.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubHubHeaderCard extends StatelessWidget {
  const ClubHubHeaderCard({
    super.key,
    required this.data,
    required this.currentLeagueLabel,
  });

  final ClubDashboardData data;
  final String currentLeagueLabel;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool stacked = constraints.maxWidth < 760;
          final Widget badge = Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              BadgePreviewWidget(
                badge: data.identity.badgeProfile,
                size: stacked ? 112 : 132,
              ),
              const SizedBox(height: 14),
              _HeaderCodePill(code: data.identity.shortClubCode),
            ],
          );

          final Widget summary = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  ReputationTierBadge(
                    tier: data.reputation.profile.currentPrestigeTier,
                  ),
                  _HeaderMetaPill(
                    icon: Icons.stadium_outlined,
                    label: currentLeagueLabel,
                  ),
                  _HeaderMetaPill(
                    icon: Icons.emoji_events_outlined,
                    label: '${data.trophyCabinet.majorHonorsCount} major honors',
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                data.clubName,
                style: Theme.of(context).textTheme.displaySmall,
              ),
              const SizedBox(height: 8),
              Text(
                data.countryName ?? 'Global club profile',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              Wrap(
                spacing: 14,
                runSpacing: 14,
                children: <Widget>[
                  _HeaderFactTile(
                    label: 'Club code',
                    value: data.identity.shortClubCode,
                    icon: Icons.badge_outlined,
                  ),
                  _HeaderFactTile(
                    label: 'Current league',
                    value: currentLeagueLabel,
                    icon: Icons.route_outlined,
                  ),
                  _HeaderFactTile(
                    label: 'Major honors',
                    value: '${data.trophyCabinet.majorHonorsCount}',
                    icon: Icons.workspace_premium_outlined,
                  ),
                ],
              ),
            ],
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(child: badge),
                const SizedBox(height: 20),
                summary,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              badge,
              const SizedBox(width: 24),
              Expanded(child: summary),
            ],
          );
        },
      ),
    );
  }
}

class _HeaderCodePill extends StatelessWidget {
  const _HeaderCodePill({
    required this.code,
  });

  final String code;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.94),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Text(
        code.toUpperCase(),
        style: Theme.of(context).textTheme.labelLarge,
      ),
    );
  }
}

class _HeaderMetaPill extends StatelessWidget {
  const _HeaderMetaPill({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
        color: GteShellTheme.panel.withValues(alpha: 0.86),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 16, color: GteShellTheme.accentWarm),
          const SizedBox(width: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.labelLarge,
          ),
        ],
      ),
    );
  }
}

class _HeaderFactTile extends StatelessWidget {
  const _HeaderFactTile({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(minWidth: 180, maxWidth: 220),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          color: GteShellTheme.panel.withValues(alpha: 0.82),
          border: Border.all(color: GteShellTheme.stroke),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, color: GteShellTheme.accent),
            const SizedBox(height: 14),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
