import 'package:flutter/material.dart';

import '../match_scene_director.dart';

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
  });

  final String homeName;
  final String awayName;
  final int? homeScore;
  final int? awayScore;
  final String clockLabel;
  final String statusLabel;
  final MatchSimCameraState cameraState;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('match-scorebar'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xE80A1118),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: <Widget>[
            _TeamBlock(name: homeName, score: homeScore),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    '$clockLabel | $statusLabel',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _cameraLabel(cameraState),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: Colors.white70,
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
      ),
    );
  }
}

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
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          name.toUpperCase(),
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
    );
  }
}

String _cameraLabel(MatchSimCameraState state) {
  switch (state) {
    case MatchSimCameraState.stadiumWide:
      return 'STADIUM WIDE';
    case MatchSimCameraState.tunnelOrWalkout:
      return 'WALKOUT';
    case MatchSimCameraState.kickoffCenter:
      return 'KICKOFF';
    case MatchSimCameraState.tacticalTop:
      return 'TACTICAL TOP';
    case MatchSimCameraState.attackingThird:
      return 'ATTACKING THIRD';
    case MatchSimCameraState.setPieceLeft:
      return 'SET PIECE LEFT';
    case MatchSimCameraState.setPieceRight:
      return 'SET PIECE RIGHT';
    case MatchSimCameraState.goalReplayAngle:
      return 'GOAL REPLAY';
    case MatchSimCameraState.halftimeBoard:
      return 'HALFTIME BOARD';
    case MatchSimCameraState.fulltimeBoard:
      return 'FULLTIME BOARD';
  }
}
