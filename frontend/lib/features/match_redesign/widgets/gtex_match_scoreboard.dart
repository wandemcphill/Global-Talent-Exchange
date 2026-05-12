import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class GtexMatchScoreboard extends StatelessWidget {
  const GtexMatchScoreboard({super.key, required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF07130E),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF18FF88).withOpacity(.24)),
        boxShadow: const [BoxShadow(blurRadius: 24, color: Colors.black45)],
      ),
      child: Row(
        children: [
          Expanded(child: _TeamBlock(team: match.home, alignEnd: false)),
          Column(
            children: [
              Text('${match.home.score}  -  ${match.away.score}', style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w900, color: Colors.white)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(color: const Color(0xFF18FF88).withOpacity(.12), borderRadius: BorderRadius.circular(999)),
                child: Text('${match.minute}\'  ${_phaseLabel(match.phase)}', style: const TextStyle(color: Color(0xFF18FF88), fontWeight: FontWeight.w800)),
              ),
            ],
          ),
          Expanded(child: _TeamBlock(team: match.away, alignEnd: true)),
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

class _TeamBlock extends StatelessWidget {
  const _TeamBlock({required this.team, required this.alignEnd});
  final GtexMatchTeam team;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final children = [
      CircleAvatar(
        backgroundColor: const Color(0xFF18FF88).withOpacity(.16),
        child: Text(team.shortName.characters.first, style: const TextStyle(color: Color(0xFF18FF88), fontWeight: FontWeight.w900)),
      ),
      const SizedBox(width: 12),
      Flexible(
        child: Column(
          crossAxisAlignment: alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Text(team.name, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
            Text(team.formation, style: TextStyle(color: Colors.white.withOpacity(.58), fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    ];
    return Row(
      mainAxisAlignment: alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
      children: alignEnd ? children.reversed.toList() : children,
    );
  }
}
