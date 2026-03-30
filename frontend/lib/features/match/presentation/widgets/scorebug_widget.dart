import 'package:flutter/material.dart';

import '../broadcast_scene_director.dart';

class MatchScorebarWidget extends StatelessWidget {
  const MatchScorebarWidget({
    super.key,
    required this.homeName,
    required this.awayName,
    required this.homeScore,
    required this.awayScore,
    required this.clockLabel,
    required this.statusLabel,
    required this.cameraState,
    this.eventLabel,
  });

  final String homeName;
  final String awayName;
  final int? homeScore;
  final int? awayScore;
  final String clockLabel;
  final String statusLabel;
  final MatchSimCameraState cameraState;
  final String? eventLabel;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('broadcast-scorebug'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xE8091017),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Row(
              children: <Widget>[
                _TeamBlock(name: homeName, score: homeScore),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        clockLabel,
                        style: Theme.of(
                          context,
                        ).textTheme.headlineSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '$statusLabel | ${_cameraLabel(cameraState)}',
                        style: Theme.of(
                          context,
                        ).textTheme.labelMedium?.copyWith(
                          color: Colors.white70,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.6,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                _TeamBlock(name: awayName, score: awayScore, alignEnd: true),
              ],
            ),
            if (eventLabel != null &&
                eventLabel!.trim().isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: const Color(0xFF131E2C),
                ),
                child: Text(
                  eventLabel!,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: const Color(0xFFFDB022),
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

typedef ScorebugWidget = MatchScorebarWidget;

class _TeamBlock extends StatelessWidget {
  const _TeamBlock({
    required this.name,
    required this.score,
    this.alignEnd = false,
  });

  final String name;
  final int? score;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 92,
      child: Column(
        crossAxisAlignment:
            alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            name.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.white70,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            score?.toString() ?? '--',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

String _cameraLabel(MatchSimCameraState state) {
  switch (state) {
    case MatchSimCameraState.stadiumWide:
      return 'WIDE';
    case MatchSimCameraState.tunnelOrWalkout:
      return 'WALKOUT';
    case MatchSimCameraState.kickoffCenter:
      return 'KICKOFF';
    case MatchSimCameraState.tacticalTop:
      return 'TACTICAL';
    case MatchSimCameraState.attackingThird:
      return 'ATTACK';
    case MatchSimCameraState.setPieceLeft:
      return 'SET PIECE';
    case MatchSimCameraState.setPieceRight:
      return 'SET PIECE';
    case MatchSimCameraState.goalReplayAngle:
      return 'REPLAY';
    case MatchSimCameraState.halftimeBoard:
      return 'HALFTIME';
    case MatchSimCameraState.fulltimeBoard:
      return 'FULL TIME';
  }
}
