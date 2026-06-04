import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class TacticalHudWidget extends StatelessWidget {
  const TacticalHudWidget({super.key, required this.package});

  final MatchPresentationPackage package;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('tactical-hud'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        color: const Color(0xE90B131B),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Tactical HUD',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: <Widget>[
                Expanded(child: _TeamHud(team: package.home)),
                const SizedBox(width: 12),
                Expanded(child: _TeamHud(team: package.away, alignEnd: true)),
              ],
            ),
            const SizedBox(height: 14),
            Text(
              'Ratings strip',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Colors.white70,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 10),
            if (package.ratingLeaders.isEmpty)
              Text(
                'Ratings pending live data.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.white60),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: package.ratingLeaders
                    .take(8)
                    .map(
                      (MatchPresentationPlayer player) => Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.05),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Text(
                          '${player.playerName} | ${player.rating?.toStringAsFixed(1) ?? '--'}',
                          style: Theme.of(
                            context,
                          ).textTheme.labelMedium?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
          ],
        ),
      ),
    );
  }
}

class _TeamHud extends StatelessWidget {
  const _TeamHud({required this.team, this.alignEnd = false});

  final MatchPresentationTeam team;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          team.teamName,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '${team.formation}'
          '${team.mentality == null ? '' : ' | ${team.mentality}'}'
          '${team.coachName == null ? '' : ' | ${team.coachName}'}',
          textAlign: alignEnd ? TextAlign.right : TextAlign.left,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: Colors.white70),
        ),
        const SizedBox(height: 6),
        Text(
          team.instructionSummary.isEmpty
              ? 'Instructions pending live data'
              : team.instructionSummary.take(2).join(' | '),
          textAlign: alignEnd ? TextAlign.right : TextAlign.left,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: const Color(0xFF7DD3FC),
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
