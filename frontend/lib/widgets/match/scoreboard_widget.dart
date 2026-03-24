import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/fairness_badge.dart';

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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xCC07131F),
        border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          _ScoreLine(
            viewState: viewState,
            frame: frame,
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              _ClockTag(frame: frame),
              FairnessBadge(viewState: viewState),
              if (activeEvent != null) _EventTag(event: activeEvent!),
            ],
          ),
        ],
      ),
    );
  }
}

class _ScoreLine extends StatelessWidget {
  const _ScoreLine({
    required this.viewState,
    required this.frame,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Row(
      mainAxisSize: MainAxisSize.max,
      children: <Widget>[
        _TeamBadge(team: viewState.homeTeam),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            viewState.homeTeam.shortName,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.labelLarge?.copyWith(
              color: Colors.white,
              letterSpacing: 1.1,
            ),
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
            style: theme.textTheme.titleLarge?.copyWith(color: Colors.white70),
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
        Expanded(
          child: Text(
            viewState.awayTeam.shortName,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.right,
            style: theme.textTheme.labelLarge?.copyWith(
              color: Colors.white,
              letterSpacing: 1.1,
            ),
          ),
        ),
        const SizedBox(width: 10),
        _TeamBadge(team: viewState.awayTeam),
      ],
    );
  }
}

class _ClockTag extends StatelessWidget {
  const _ClockTag({
    required this.frame,
  });

  final MatchTimelineFrame frame;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Column(
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
    );
  }
}

class _EventTag extends StatelessWidget {
  const _EventTag({
    required this.event,
  });

  final MatchEvent event;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: _accentColor(event.type).withValues(alpha: 0.2),
      ),
      child: Text(
        event.type.name.toUpperCase(),
        style: theme.textTheme.labelSmall?.copyWith(
          color: _accentColor(event.type),
          fontWeight: FontWeight.w700,
        ),
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
    case MatchViewerEventType.foul:
      return const Color(0xFFFDB022);
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
