import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_command_center_tokens.dart';
import '../theme/gtex_spacing.dart';
import 'gtex_command_center.dart';

/// Production lane hero for the signed-in Flutter shell.
///
/// Wraps [GtexCommandCenterMasthead] so Home, Club HQ, Market, and Capital
/// share one floodlit ownership language instead of grey metric dashboards.
class GtexShellLaneHero extends StatelessWidget {
  const GtexShellLaneHero({
    super.key,
    required this.eyebrow,
    required this.identity,
    required this.title,
    required this.summary,
    required this.statusLabel,
    required this.status,
    required this.metrics,
    this.identityDetail,
    this.primaryAction,
    this.secondaryAction,
    this.compact = false,
  });

  final String eyebrow;
  final String identity;
  final String? identityDetail;
  final String title;
  final String summary;
  final String statusLabel;
  final GtexCommandStatus status;
  final List<GtexCommandMetric> metrics;
  final Widget? primaryAction;
  final Widget? secondaryAction;

  /// When true, drops to a thinner strip for nested desks with limited height.
  final bool compact;

  factory GtexShellLaneHero.compactStrip({
    Key? key,
    required String eyebrow,
    required String title,
    required String summary,
    Color accent = GtexFloodlit.pitch,
  }) {
    return GtexShellLaneHero(
      key: key,
      eyebrow: eyebrow,
      identity: 'GTEX',
      title: title,
      summary: summary,
      statusLabel: 'LIVE',
      status: GtexCommandStatus.live,
      compact: true,
      metrics: <GtexCommandMetric>[
        GtexCommandMetric(
          label: 'Lane',
          value: eyebrow,
          detail: 'Shell',
          accent: accent,
          icon: Icons.sports_soccer_rounded,
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return Container(
        key: const Key('gtex-shell-lane-hero-compact'),
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(
          GtexSpacing.md,
          GtexSpacing.sm,
          GtexSpacing.md,
          GtexSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: GtexFloodlit.turf,
          borderRadius: BorderRadius.circular(GtexCommandTokens.panelRadius),
          border: Border.all(color: GtexFloodlit.line),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              eyebrow.toUpperCase(),
              style: const TextStyle(
                color: GtexFloodlit.gold,
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.4,
                fontFamily: GtexFloodlit.display,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: const TextStyle(
                color: GtexFloodlit.chalk,
                fontSize: 22,
                fontWeight: FontWeight.w900,
                height: 1.05,
                fontFamily: GtexFloodlit.display,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              summary,
              style: const TextStyle(
                color: GtexFloodlit.chalkMuted,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      );
    }

    return GtexCommandCenterMasthead(
      key: const Key('gtex-shell-lane-hero'),
      eyebrow: eyebrow,
      identity: identity,
      identityDetail: identityDetail,
      title: title,
      summary: summary,
      statusLabel: statusLabel,
      status: status,
      metrics: metrics,
      primaryAction: primaryAction,
      secondaryAction: secondaryAction,
    );
  }
}
