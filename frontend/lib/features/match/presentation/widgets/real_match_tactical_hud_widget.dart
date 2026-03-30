import 'package:flutter/material.dart';

import '../../../../models/real_match_engine_presentation.dart';
import '../broadcast_package_models.dart';

class RealMatchTacticalHudWidget extends StatelessWidget {
  const RealMatchTacticalHudWidget({
    super.key,
    required this.package,
    required this.presentation,
  });

  final MatchPresentationPackage package;
  final MatchEnginePresentationState presentation;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('real-match-tactical-hud'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        color: const Color(0xEA0A121B),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Tactical HUD',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: <Widget>[
                Expanded(
                  child: _ShapeCard(
                    team: package.home,
                    shape: presentation.homeShape,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _ShapeCard(
                    team: package.away,
                    shape: presentation.awayShape,
                    alignEnd: true,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              presentation.activeEventContext?.hasPrimaryPlayer == true
                  ? 'Possession focus: ${presentation.activeEventContext!.primaryPlayerName}'
                  : 'Possession: ${presentation.possessionSide.name.toUpperCase()}',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: const Color(0xFF7DD3FC),
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              package.home.instructionSummary.isEmpty &&
                      package.away.instructionSummary.isEmpty
                  ? 'Instruction detail hidden until the payload exposes it.'
                  : '${package.home.teamName}: ${package.home.instructionSummary.take(2).join(' | ')}'
                      '${package.away.instructionSummary.isEmpty ? '' : '  •  ${package.away.teamName}: ${package.away.instructionSummary.take(2).join(' | ')}'}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.white70,
                height: 1.35,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ShapeCard extends StatelessWidget {
  const _ShapeCard({
    required this.team,
    required this.shape,
    this.alignEnd = false,
  });

  final MatchPresentationTeam team;
  final MatchEngineTeamShape shape;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
      ),
      child: Column(
        crossAxisAlignment:
            alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            team.shortName,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${shape.formation} • ${shape.compactnessLabel}',
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.white70),
          ),
          const SizedBox(height: 8),
          Text(
            'Width ${shape.width.toStringAsFixed(1)} • ${shape.widthLabel}',
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: const Color(0xFFFDB022),
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Depth ${shape.depth.toStringAsFixed(1)} • ${shape.inPossession ? 'On ball' : 'Without ball'}',
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.white60),
          ),
        ],
      ),
    );
  }
}
