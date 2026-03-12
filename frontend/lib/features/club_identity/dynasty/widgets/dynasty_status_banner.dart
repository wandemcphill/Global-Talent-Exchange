import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_profile_dto.dart';
import '../data/dynasty_types.dart';
import 'era_label_chip.dart';

class DynastyStatusBanner extends StatelessWidget {
  const DynastyStatusBanner({
    super.key,
    required this.profile,
    this.onOpenTimeline,
    this.onOpenLeaderboard,
  });

  final DynastyProfileDto profile;
  final VoidCallback? onOpenTimeline;
  final VoidCallback? onOpenLeaderboard;

  @override
  Widget build(BuildContext context) {
    final List<Color> bannerColors = _bannerColors(profile.currentEraLabel);
    return GteSurfacePanel(
      emphasized: true,
      padding: EdgeInsets.zero,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: bannerColors,
          ),
        ),
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Wrap(
              spacing: 10,
              runSpacing: 10,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: <Widget>[
                EraLabelChip(
                  era: profile.currentEraLabel,
                  active: profile.activeDynastyFlag,
                ),
                _MiniFlag(
                  label: profile.dynastyStatus.label,
                  tone: profile.activeDynastyFlag
                      ? GteShellTheme.positive
                      : GteShellTheme.textMuted,
                ),
                _MiniFlag(
                  label: 'Score ${profile.dynastyScore}',
                  tone: GteShellTheme.accentWarm,
                ),
              ],
            ),
            const SizedBox(height: 18),
            Text(
              profile.clubName,
              style: Theme.of(context).textTheme.displaySmall,
            ),
            const SizedBox(height: 10),
            Text(
              profile.currentEraLabel.strapline,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 18),
            Text(
              _bannerBody(profile),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GteShellTheme.textPrimary.withValues(alpha: 0.82),
                  ),
            ),
            if (onOpenTimeline != null ||
                onOpenLeaderboard != null) ...<Widget>[
              const SizedBox(height: 22),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  if (onOpenTimeline != null)
                    FilledButton.tonalIcon(
                      onPressed: onOpenTimeline,
                      icon: const Icon(Icons.timeline_outlined),
                      label: const Text('Open timeline'),
                    ),
                  if (onOpenLeaderboard != null)
                    OutlinedButton.icon(
                      onPressed: onOpenLeaderboard,
                      icon: const Icon(Icons.leaderboard_outlined),
                      label: const Text('Compare dynasties'),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _bannerBody(DynastyProfileDto profile) {
    if (profile.currentEraLabel == DynastyEraType.globalDynasty) {
      return 'The club is no longer chasing legacy. It is defending one. '
          'Every new season is measured against a world-class standard.';
    }
    if (profile.currentEraLabel == DynastyEraType.fallenGiant) {
      return 'Supporters are living with a famous history and waiting for a new surge. '
          'The story is respected, not finished.';
    }
    if (profile.isRisingClub && !profile.hasRecognizedDynasty) {
      return 'There is momentum here, but the threshold is still strict. '
          'One strong cycle can become a statement. A second one becomes history.';
    }
    return 'Dynasty labels stay rare on purpose. The badge must keep winning, keep qualifying, '
        'and keep feeling inevitable.';
  }
}

class _MiniFlag extends StatelessWidget {
  const _MiniFlag({
    required this.label,
    required this.tone,
  });

  final String label;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: tone.withValues(alpha: 0.12),
        border: Border.all(color: tone.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: tone),
      ),
    );
  }
}

List<Color> _bannerColors(DynastyEraType era) {
  switch (era) {
    case DynastyEraType.globalDynasty:
      return const <Color>[
        Color(0xFF302107),
        Color(0xFF17120B),
        Color(0xFF111827),
      ];
    case DynastyEraType.continentalDynasty:
      return const <Color>[
        Color(0xFF2E1D04),
        Color(0xFF151313),
        Color(0xFF111827),
      ];
    case DynastyEraType.dominantEra:
      return const <Color>[
        Color(0xFF0D2C20),
        Color(0xFF111827),
        Color(0xFF0D1724),
      ];
    case DynastyEraType.emergingPower:
      return const <Color>[
        Color(0xFF08242A),
        Color(0xFF111827),
        Color(0xFF0D1724),
      ];
    case DynastyEraType.fallenGiant:
      return const <Color>[
        Color(0xFF231A12),
        Color(0xFF15181D),
        Color(0xFF101827),
      ];
    case DynastyEraType.none:
      return const <Color>[
        Color(0xFF111827),
        Color(0xFF101827),
        Color(0xFF0D1724),
      ];
  }
}
