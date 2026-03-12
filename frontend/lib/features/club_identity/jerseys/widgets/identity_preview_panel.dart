import 'package:flutter/material.dart';

import '../../../../widgets/gte_surface_panel.dart';
import '../data/club_identity_dto.dart';
import 'badge_preview_widget.dart';
import 'club_code_chip.dart';
import 'identity_color_utils.dart';

class IdentityPreviewPanel extends StatelessWidget {
  const IdentityPreviewPanel({
    super.key,
    required this.identity,
  });

  final ClubIdentityDto identity;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 860;
        return Wrap(
          spacing: 16,
          runSpacing: 16,
          children: <Widget>[
            SizedBox(
              width: stacked
                  ? constraints.maxWidth
                  : (constraints.maxWidth - 16) / 2,
              child: _StandingsPreview(identity: identity),
            ),
            SizedBox(
              width: stacked
                  ? constraints.maxWidth
                  : (constraints.maxWidth - 16) / 2,
              child: _MatchIntroPreview(identity: identity),
            ),
            SizedBox(
              width: stacked
                  ? constraints.maxWidth
                  : (constraints.maxWidth - 16) / 2,
              child: _ReplayCardPreview(identity: identity),
            ),
            SizedBox(
              width: stacked
                  ? constraints.maxWidth
                  : (constraints.maxWidth - 16) / 2,
              child: _FixtureCardPreview(identity: identity),
            ),
          ],
        );
      },
    );
  }
}

class _StandingsPreview extends StatelessWidget {
  const _StandingsPreview({
    required this.identity,
  });

  final ClubIdentityDto identity;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Standings row', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              BadgePreviewWidget(badge: identity.badgeProfile, size: 56),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(identity.clubName,
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 6),
                    ClubCodeChip(code: identity.shortClubCode),
                  ],
                ),
              ),
              _KitStrip(colors: identity.matchIdentity.homeKitColors),
            ],
          ),
        ],
      ),
    );
  }
}

class _MatchIntroPreview extends StatelessWidget {
  const _MatchIntroPreview({
    required this.identity,
  });

  final ClubIdentityDto identity;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Match intro card',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              gradient: LinearGradient(
                colors: <Color>[
                  identityColorFromHex(identity.jerseySet.home.primaryColor)
                      .withValues(alpha: 0.22),
                  identityColorFromHex(identity.jerseySet.away.primaryColor)
                      .withValues(alpha: 0.08),
                ],
              ),
            ),
            child: Row(
              children: <Widget>[
                BadgePreviewWidget(badge: identity.badgeProfile, size: 68),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(identity.clubName,
                          style: Theme.of(context).textTheme.headlineSmall),
                      const SizedBox(height: 6),
                      Text(
                        'Primary intro treatment with home strip emphasis and quick club-code recognition.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReplayCardPreview extends StatelessWidget {
  const _ReplayCardPreview({
    required this.identity,
  });

  final ClubIdentityDto identity;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Replay card', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              color: identityColorFromHex(identity.jerseySet.away.primaryColor)
                  .withValues(alpha: 0.14),
            ),
            child: Row(
              children: <Widget>[
                Container(
                  width: 6,
                  height: 64,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: <Color>[
                        identityColorFromHex(
                            identity.jerseySet.home.primaryColor),
                        identityColorFromHex(
                            identity.jerseySet.home.accentColor),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                BadgePreviewWidget(badge: identity.badgeProfile, size: 52),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Key moment',
                          style: Theme.of(context).textTheme.bodyMedium),
                      const SizedBox(height: 6),
                      Text(identity.clubName,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 4),
                      Text(
                        'Badge, code, and kit tone stay scannable in compact highlight stacks.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FixtureCardPreview extends StatelessWidget {
  const _FixtureCardPreview({
    required this.identity,
  });

  final ClubIdentityDto identity;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Fixture card', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              BadgePreviewWidget(badge: identity.badgeProfile, size: 48),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(identity.clubName,
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(
                      'Uses the away kit strip to distinguish future fixtures from live intro surfaces.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              _KitStrip(colors: identity.matchIdentity.awayKitColors),
            ],
          ),
        ],
      ),
    );
  }
}

class _KitStrip extends StatelessWidget {
  const _KitStrip({
    required this.colors,
  });

  final List<String> colors;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: colors.map((String color) {
        return Container(
          width: 18,
          height: 48,
          margin: const EdgeInsets.only(left: 4),
          decoration: BoxDecoration(
            color: identityColorFromHex(color),
            borderRadius: BorderRadius.circular(999),
          ),
        );
      }).toList(growable: false),
    );
  }
}
