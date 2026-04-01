import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';

class ScoreboardWidget extends StatelessWidget {
  const ScoreboardWidget({
    super.key,
    required this.viewState,
    required this.frame,
    required this.activeEvent,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xCC07131F),
        border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          _TeamBadge(team: viewState.homeTeam),
          const SizedBox(width: 10),
          Text(
            viewState.homeTeam.shortName,
            style: theme.textTheme.labelLarge?.copyWith(
              color: Colors.white,
              letterSpacing: 1.1,
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '${frame.homeScore}',
            style: theme.textTheme.titleLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Text(
              ':',
              style:
                  theme.textTheme.titleLarge?.copyWith(color: Colors.white70),
            ),
          ),
          Text(
            '${frame.awayScore}',
            style: theme.textTheme.titleLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 10),
          Text(
            viewState.awayTeam.shortName,
            style: theme.textTheme.labelLarge?.copyWith(
              color: Colors.white,
              letterSpacing: 1.1,
            ),
          ),
          const SizedBox(width: 10),
          _TeamBadge(team: viewState.awayTeam),
          const SizedBox(width: 14),
          Container(
            width: 1,
            height: 26,
            color: Colors.white.withValues(alpha: 0.14),
          ),
          const SizedBox(width: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                _periodLabel(frame),
                style: theme.textTheme.labelSmall?.copyWith(
                  color: Colors.white70,
                  letterSpacing: 1,
                ),
              ),
              Text(
                "${frame.clockMinute.floor()}'",
                style: theme.textTheme.titleMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          if (activeEvent != null) ...<Widget>[
            const SizedBox(width: 14),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(999),
                color: _accentColor(activeEvent!.type).withValues(alpha: 0.2),
              ),
              child: Text(
                activeEvent!.type.name.toUpperCase(),
                style: theme.textTheme.labelSmall?.copyWith(
                  color: _accentColor(activeEvent!.type),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TeamBadge extends StatelessWidget {
  const _TeamBadge({required this.team});

  final MatchViewerTeam team;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 26,
      height: 26,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: _parseColor(team.primaryColorHex),
        border: Border.all(color: _parseColor(team.accentColorHex), width: 1.5),
      ),
    );
  }
}

String _periodLabel(MatchTimelineFrame frame) {
  switch (frame.phase) {
    case MatchViewerPhase.kickoff:
      return 'KO';
    case MatchViewerPhase.halftime:
      return 'HT';
    case MatchViewerPhase.fulltime:
      return 'FT';
    case MatchViewerPhase.setPiece:
      return 'SP';
    case MatchViewerPhase.openPlay:
      return frame.clockMinute >= 45 ? '2H' : '1H';
  }
}

Color _accentColor(MatchViewerEventType type) {
  switch (type) {
    case MatchViewerEventType.goal:
      return const Color(0xFF17B26A);
    case MatchViewerEventType.save:
      return const Color(0xFF53B1FD);
    case MatchViewerEventType.miss:
      return const Color(0xFFF79009);
    case MatchViewerEventType.offside:
      return const Color(0xFFF97066);
    case MatchViewerEventType.redCard:
      return const Color(0xFFF04438);
    default:
      return const Color(0xFFD0D5DD);
  }
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}
