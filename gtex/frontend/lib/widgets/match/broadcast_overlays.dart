import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/widgets/match/fairness_badge.dart';

class BroadcastScoreboardWidget extends StatelessWidget {
  const BroadcastScoreboardWidget({
    super.key,
    required this.viewState,
    required this.clockLabel,
    required this.homeScore,
    required this.awayScore,
    required this.scoreMasked,
    required this.statusLabel,
    required this.cameraPreset,
  });

  final MatchViewState viewState;
  final String clockLabel;
  final int? homeScore;
  final int? awayScore;
  final bool scoreMasked;
  final String statusLabel;
  final BroadcastCameraPreset cameraPreset;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xF00A1828),
            Color(0xE0122033),
          ],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.26),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 14,
        runSpacing: 10,
        children: <Widget>[
          _StatusChip(label: statusLabel),
          _TeamCluster(
            badge: _TeamBadge(team: viewState.homeTeam),
            shortName: viewState.homeTeam.shortName,
            scoreLabel: scoreMasked ? '--' : '${homeScore ?? 0}',
            alignEnd: false,
          ),
          Text(
            ':',
            style: theme.textTheme.titleLarge?.copyWith(
              color: Colors.white70,
              fontWeight: FontWeight.w700,
            ),
          ),
          _TeamCluster(
            badge: _TeamBadge(team: viewState.awayTeam),
            shortName: viewState.awayTeam.shortName,
            scoreLabel: scoreMasked ? '--' : '${awayScore ?? 0}',
            alignEnd: true,
          ),
          Container(
            width: 1,
            height: 26,
            color: Colors.white.withValues(alpha: 0.12),
          ),
          Text(
            clockLabel,
            style: theme.textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.6,
            ),
          ),
          FairnessBadge(viewState: viewState),
          if (cameraPreset == BroadcastCameraPreset.replayCamera)
            const _StatusChip(
              label: 'REPLAY',
              backgroundColor: Color(0x33F79009),
              foregroundColor: Color(0xFFFDB022),
            ),
        ],
      ),
    );
  }
}

class BroadcastCommentaryOverlay extends StatelessWidget {
  const BroadcastCommentaryOverlay({
    super.key,
    required this.headline,
    required this.subtitle,
    required this.focusEvent,
    required this.isVarChecking,
  });

  final String? headline;
  final String? subtitle;
  final MatchEvent? focusEvent;
  final bool isVarChecking;

  @override
  Widget build(BuildContext context) {
    if (headline == null || headline!.trim().isEmpty) {
      return const SizedBox.shrink();
    }
    final Color accent = isVarChecking
        ? const Color(0xFFFDB022)
        : _accentForEventType(focusEvent?.type);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            const Color(0xF0101E31),
            accent.withValues(alpha: 0.22),
          ],
        ),
        border: Border.all(color: accent.withValues(alpha: 0.55)),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: accent.withValues(alpha: 0.18),
            ),
            child: Icon(
              isVarChecking
                  ? Icons.search_outlined
                  : (focusEvent?.icon ?? Icons.mic_none_outlined),
              color: accent,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  headline!,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                if (subtitle != null &&
                    subtitle!.trim().isNotEmpty) ...<Widget>[
                  const SizedBox(height: 4),
                  Text(
                    subtitle!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.white70,
                        ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class BroadcastStartingBanner extends StatelessWidget {
  const BroadcastStartingBanner({
    super.key,
    required this.opacity,
  });

  final double opacity;

  @override
  Widget build(BuildContext context) {
    if (opacity <= 0.01) {
      return const SizedBox.shrink();
    }
    return IgnorePointer(
      child: Opacity(
        opacity: opacity.clamp(0, 1),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xF0101E31),
                Color(0xE0192740),
              ],
            ),
            border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.28),
                blurRadius: 28,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: Text(
            'Match starting...',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.4,
                ),
          ),
        ),
      ),
    );
  }
}

class BroadcastLineupBoard extends StatelessWidget {
  const BroadcastLineupBoard({
    super.key,
    required this.viewState,
    required this.opacity,
  });

  final MatchViewState viewState;
  final double opacity;

  @override
  Widget build(BuildContext context) {
    if (opacity <= 0.01) {
      return const SizedBox.shrink();
    }
    final List<dynamic> homePlayers = viewState.firstFrame.players
        .where((dynamic player) => player.side == MatchViewerSide.home)
        .take(11)
        .toList(growable: false);
    final List<dynamic> awayPlayers = viewState.firstFrame.players
        .where((dynamic player) => player.side == MatchViewerSide.away)
        .take(11)
        .toList(growable: false);
    return IgnorePointer(
      child: Opacity(
        opacity: opacity.clamp(0, 1),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 760),
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(28),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xF0101E31),
                Color(0xE0162438),
              ],
            ),
            border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.24),
                blurRadius: 30,
                offset: const Offset(0, 16),
              ),
            ],
          ),
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool stacked = constraints.maxWidth < 560;
              final List<Widget> columns = <Widget>[
                Expanded(
                  child: _LineupColumn(
                    team: viewState.homeTeam,
                    players: homePlayers,
                    alignEnd: false,
                  ),
                ),
                Expanded(
                  child: _LineupColumn(
                    team: viewState.awayTeam,
                    players: awayPlayers,
                    alignEnd: true,
                  ),
                ),
              ];
              return stacked
                  ? Column(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        columns.first,
                        const SizedBox(height: 16),
                        columns.last,
                      ],
                    )
                  : Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        columns.first,
                        Container(
                          width: 1,
                          height: 176,
                          margin: const EdgeInsets.symmetric(horizontal: 18),
                          color: Colors.white.withValues(alpha: 0.1),
                        ),
                        columns.last,
                      ],
                    );
            },
          ),
        ),
      ),
    );
  }
}

class BroadcastStadiumFade extends StatelessWidget {
  const BroadcastStadiumFade({
    super.key,
    required this.opacity,
  });

  final double opacity;

  @override
  Widget build(BuildContext context) {
    if (opacity <= 0.01) {
      return const SizedBox.shrink();
    }
    return IgnorePointer(
      child: Opacity(
        opacity: opacity.clamp(0, 1),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0, -0.05),
              radius: 0.98,
              colors: <Color>[
                Colors.transparent,
                Colors.black.withValues(alpha: 0.16),
                Colors.black.withValues(alpha: 0.56),
              ],
              stops: const <double>[0.42, 0.78, 1],
            ),
          ),
          child: const SizedBox.expand(),
        ),
      ),
    );
  }
}

class _LineupColumn extends StatelessWidget {
  const _LineupColumn({
    required this.team,
    required this.players,
    required this.alignEnd,
  });

  final MatchViewerTeam team;
  final List<dynamic> players;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final CrossAxisAlignment alignment =
        alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    return Column(
      crossAxisAlignment: alignment,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Row(
          mainAxisAlignment:
              alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
          children: <Widget>[
            if (alignEnd) ...<Widget>[
              Text(
                team.teamName,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(width: 10),
              _TeamBadge(team: team),
            ] else ...<Widget>[
              _TeamBadge(team: team),
              const SizedBox(width: 10),
              Text(
                team.teamName,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 10),
        Text(
          'Formation ${team.formation}',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF98A2B3),
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 12),
        ...players.map(
          (dynamic player) => Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text(
              _lineupPlayerLabel(player),
              textAlign: alignEnd ? TextAlign.end : TextAlign.start,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white.withValues(alpha: 0.92),
                  ),
            ),
          ),
        ),
      ],
    );
  }
}

String _lineupPlayerLabel(dynamic player) {
  final int? shirtNumber = player.shirtNumber as int?;
  final String label = (player.label as String?)?.trim().isNotEmpty == true
      ? (player.label as String).trim()
      : '?';
  return shirtNumber == null ? label : '$shirtNumber  $label';
}

class _TeamCluster extends StatelessWidget {
  const _TeamCluster({
    required this.badge,
    required this.shortName,
    required this.scoreLabel,
    required this.alignEnd,
  });

  final Widget badge;
  final String shortName;
  final String scoreLabel;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final Widget score = Text(
      scoreLabel,
      style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w800,
          ),
    );
    final Widget name = Text(
      shortName,
      style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: Colors.white,
            letterSpacing: 1,
          ),
    );
    final List<Widget> row = alignEnd
        ? <Widget>[
            score,
            const SizedBox(width: 10),
            name,
            const SizedBox(width: 10),
            badge
          ]
        : <Widget>[
            badge,
            const SizedBox(width: 10),
            name,
            const SizedBox(width: 10),
            score
          ];
    return Row(mainAxisSize: MainAxisSize.min, children: row);
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    this.backgroundColor = const Color(0x3322C55E),
    this.foregroundColor = const Color(0xFF86EFAC),
  });

  final String label;
  final Color backgroundColor;
  final Color foregroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: backgroundColor,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: foregroundColor,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.8,
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
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: _parseColor(team.primaryColorHex),
        border: Border.all(color: _parseColor(team.accentColorHex), width: 1.5),
      ),
    );
  }
}

Color _accentForEventType(MatchViewerEventType? type) {
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
      return const Color(0xFF98A2B3);
  }
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}
