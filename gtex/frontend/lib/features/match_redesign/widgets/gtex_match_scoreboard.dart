import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexMatchScoreboard extends StatelessWidget {
  const GtexMatchScoreboard({super.key, required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        color: GtexMatchVisualTokens.surfaceRaised,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        children: [
          Row(
            children: [
              _LiveStatusBadge(match: match),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  '${match.home.name.toUpperCase()} VS ${match.away.name.toUpperCase()}',
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: GtexMatchVisualTokens.textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                  ),
                ),
              ),
              Text(
                _phaseLabel(match.phase).toUpperCase(),
                style: const TextStyle(
                  color: GtexMatchVisualTokens.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  letterSpacing: .8,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _TeamBlock(team: match.home, alignEnd: false)),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                child: Text(
                  '${match.home.score} - ${match.away.score}',
                  style: theme.textTheme.displaySmall?.copyWith(
                    color: GtexMatchVisualTokens.textPrimary,
                    fontWeight: FontWeight.w900,
                    fontFamily: 'Barlow Condensed',
                    letterSpacing: 0,
                  ),
                ),
              ),
              Expanded(child: _TeamBlock(team: match.away, alignEnd: true)),
            ],
          ),
        ],
      ),
    );
  }

  String _phaseLabel(GtexMatchPhase phase) {
    switch (phase) {
      case GtexMatchPhase.scheduled:
        return 'Scheduled';
      case GtexMatchPhase.firstHalf:
        return '1st Half';
      case GtexMatchPhase.halfTime:
        return 'Half Time';
      case GtexMatchPhase.secondHalf:
        return '2nd Half';
      case GtexMatchPhase.extraTime:
        return 'Extra Time';
      case GtexMatchPhase.penalties:
        return 'Pens';
      case GtexMatchPhase.fullTime:
        return 'Full Time';
    }
  }
}

class _LiveStatusBadge extends StatelessWidget {
  const _LiveStatusBadge({required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final bool live = match.isLive;
    final String clock =
        match.phase == GtexMatchPhase.scheduled
            ? 'PRE'
            : match.phase == GtexMatchPhase.fullTime
            ? 'FT'
            : '${match.minute}\'';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color:
            live
                ? const Color(0x2200E87A)
                : GtexMatchVisualTokens.surfaceOverlay,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color:
              live
                  ? const Color(0x6600E87A)
                  : GtexMatchVisualTokens.borderStrong,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (live) ...[
            Container(
              width: 7,
              height: 7,
              decoration: const BoxDecoration(
                color: GtexMatchVisualTokens.live,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 7),
          ],
          Text(
            live ? 'LIVE $clock' : clock,
            style: const TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontFamily: 'JetBrains Mono',
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _TeamBlock extends StatelessWidget {
  const _TeamBlock({required this.team, required this.alignEnd});
  final GtexMatchTeam team;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final children = [
      Container(
        width: 36,
        height: 36,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: GtexMatchVisualTokens.surfaceOverlay,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: GtexMatchVisualTokens.borderStrong),
        ),
        child: Text(
          team.shortName.characters.first,
          style: const TextStyle(
            color: GtexMatchVisualTokens.live,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
      const SizedBox(width: 12),
      Flexible(
        child: Column(
          crossAxisAlignment:
              alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Text(
              team.shortName,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: GtexMatchVisualTokens.textPrimary,
                fontWeight: FontWeight.w900,
                fontSize: 18,
                letterSpacing: .4,
              ),
            ),
            Text(
              '${team.name}  |  ${team.formation}',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: GtexMatchVisualTokens.textSecondary,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    ];
    return Row(
      mainAxisAlignment:
          alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
      children: alignEnd ? children.reversed.toList() : children,
    );
  }
}
