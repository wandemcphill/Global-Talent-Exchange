import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexMatchLineups extends StatelessWidget {
  const GtexMatchLineups({super.key, required this.home, required this.away});

  final GtexMatchTeam home;
  final GtexMatchTeam away;

  @override
  Widget build(BuildContext context) {
    if (home.players.isEmpty && away.players.isEmpty) {
      return const GtexMatchEmptyFeed(
        icon: Icons.format_list_numbered_rtl_rounded,
        title: 'Lineups unavailable',
        message:
            'The match authority has not supplied player lineups for this fixture.',
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _LineupTeam(team: home),
        const SizedBox(height: 14),
        _LineupTeam(team: away),
      ],
    );
  }
}

class _LineupTeam extends StatelessWidget {
  const _LineupTeam({required this.team});

  final GtexMatchTeam team;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: GtexMatchVisualTokens.panelDecoration(
        background: GtexMatchVisualTokens.surfaceOverlay,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 4,
                height: 28,
                decoration: BoxDecoration(
                  color: team.primaryColor ?? GtexMatchVisualTokens.live,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      team.name,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textPrimary,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      team.formation.toUpperCase(),
                      style: GtexMatchVisualTokens.labelStyle,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (team.players.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'No lineup records returned for this club.',
                style: TextStyle(color: GtexMatchVisualTokens.textSecondary),
              ),
            )
          else
            for (final GtexLineupPlayer player in team.players)
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: GtexMatchVisualTokens.surfaceRaised,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: GtexMatchVisualTokens.border),
                ),
                child: Row(
                  children: [
                    SizedBox(
                      width: 34,
                      child: Text(
                        '#${player.shirtNumber}',
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.live,
                          fontFamily: 'JetBrains Mono',
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        player.name,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.textPrimary,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    if (player.isRegen) ...[
                      const SizedBox(width: 8),
                      const _MicroTag(
                        label: 'REGEN',
                        color: GtexMatchVisualTokens.regen,
                      ),
                    ],
                    const SizedBox(width: 8),
                    _MicroTag(
                      label: player.position,
                      color: GtexMatchVisualTokens.textSecondary,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      player.rating > 0
                          ? player.rating.toStringAsFixed(1)
                          : '--',
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textPrimary,
                        fontFamily: 'JetBrains Mono',
                        fontWeight: FontWeight.w900,
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

class _MicroTag extends StatelessWidget {
  const _MicroTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(.28)),
      ),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w900,
          letterSpacing: .5,
        ),
      ),
    );
  }
}

extension on GtexMatchTeam {
  Color? get primaryColor {
    final String? raw = primaryColorHex;
    if (raw == null || raw.trim().isEmpty) {
      return null;
    }
    final String normalized = raw.replaceFirst('#', '');
    final int? value = int.tryParse(normalized, radix: 16);
    if (value == null) {
      return null;
    }
    return Color(0xFF000000 | value);
  }
}
