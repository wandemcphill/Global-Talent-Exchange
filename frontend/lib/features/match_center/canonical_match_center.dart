import 'package:flutter/material.dart';

import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';

enum CanonicalMatchSurfaceState { confirmed, blocked, degraded, empty, syncing }

class CanonicalOverlayStatus {
  const CanonicalOverlayStatus({
    required this.mode,
    required this.state,
    required this.label,
    required this.detail,
  });

  final LiveMatchOverlayMode mode;
  final CanonicalMatchSurfaceState state;
  final String label;
  final String detail;
}

List<CanonicalOverlayStatus> canonicalOverlayStatuses(
  LiveMatchSnapshot snapshot,
) {
  return LiveMatchOverlayMode.values
      .map((LiveMatchOverlayMode mode) {
        final bool supported = snapshot.stats?.supportsOverlay(mode) ?? false;
        final bool hasLineups =
            snapshot.homeLineup.isNotEmpty || snapshot.awayLineup.isNotEmpty;
        final CanonicalMatchSurfaceState state =
            mode == LiveMatchOverlayMode.shape
                ? hasLineups
                    ? CanonicalMatchSurfaceState.confirmed
                    : CanonicalMatchSurfaceState.blocked
                : supported
                ? CanonicalMatchSurfaceState.confirmed
                : CanonicalMatchSurfaceState.blocked;
        return CanonicalOverlayStatus(
          mode: mode,
          state: state,
          label: canonicalOverlayLabel(mode),
          detail:
              state == CanonicalMatchSurfaceState.confirmed
                  ? 'Backend payload available'
                  : 'Backend payload missing',
        );
      })
      .toList(growable: false);
}

String canonicalOverlayLabel(LiveMatchOverlayMode mode) {
  switch (mode) {
    case LiveMatchOverlayMode.shape:
      return 'Shape';
    case LiveMatchOverlayMode.pressure:
      return 'Pressure';
    case LiveMatchOverlayMode.shots:
      return 'Shots';
    case LiveMatchOverlayMode.xg:
      return 'xG';
    case LiveMatchOverlayMode.territory:
      return 'Territory';
    case LiveMatchOverlayMode.market:
      return 'Market';
  }
}

class CanonicalLiveScorebug extends StatelessWidget {
  const CanonicalLiveScorebug({
    super.key,
    required this.snapshot,
    this.hasBackendSnapshotTruth = true,
    this.unconfirmedLabel = 'Syncing',
    this.unconfirmedDetail =
        'Awaiting backend score and clock truth before showing match state.',
  });

  final LiveMatchSnapshot snapshot;
  final bool hasBackendSnapshotTruth;
  final String unconfirmedLabel;
  final String unconfirmedDetail;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).dividerColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: <Widget>[
            Expanded(
              child: _TeamScore(
                name: snapshot.homeTeam,
                scoreLabel:
                    hasBackendSnapshotTruth ? '${snapshot.homeScore}' : '--',
              ),
            ),
            Text(
              hasBackendSnapshotTruth
                  ? _phaseLabel(snapshot)
                  : unconfirmedLabel,
              style: Theme.of(context).textTheme.labelLarge,
            ),
            Expanded(
              child: _TeamScore(
                name: snapshot.awayTeam,
                scoreLabel:
                    hasBackendSnapshotTruth ? '${snapshot.awayScore}' : '--',
                alignEnd: true,
              ),
            ),
            if (!hasBackendSnapshotTruth) ...<Widget>[
              const SizedBox(width: 12),
              Flexible(
                child: Text(
                  unconfirmedDetail,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _phaseLabel(LiveMatchSnapshot snapshot) {
    if (snapshot.phase == LiveMatchPhase.preMatch) {
      return 'Pre-match';
    }
    if (snapshot.phase == LiveMatchPhase.halftime) {
      return 'HT';
    }
    if (snapshot.phase == LiveMatchPhase.fullTime) {
      return 'FT';
    }
    return '${snapshot.minute} min';
  }
}

class _TeamScore extends StatelessWidget {
  const _TeamScore({
    required this.name,
    required this.scoreLabel,
    this.alignEnd = false,
  });

  final String name;
  final String scoreLabel;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          name,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.labelLarge,
        ),
        Text(scoreLabel, style: Theme.of(context).textTheme.headlineSmall),
      ],
    );
  }
}

class CanonicalOverlayRail extends StatelessWidget {
  const CanonicalOverlayRail({
    super.key,
    required this.snapshot,
    required this.selectedMode,
    required this.onModeChanged,
  });

  final LiveMatchSnapshot snapshot;
  final LiveMatchOverlayMode selectedMode;
  final ValueChanged<LiveMatchOverlayMode> onModeChanged;

  @override
  Widget build(BuildContext context) {
    final List<CanonicalOverlayStatus> statuses = canonicalOverlayStatuses(
      snapshot,
    );
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: statuses
          .map((CanonicalOverlayStatus status) {
            return ChoiceChip(
              selected: status.mode == selectedMode,
              label: Text(status.label),
              avatar: Icon(
                status.state == CanonicalMatchSurfaceState.confirmed
                    ? Icons.check_circle_outline
                    : Icons.block_outlined,
                size: 18,
              ),
              onSelected: (_) => onModeChanged(status.mode),
            );
          })
          .toList(growable: false),
    );
  }
}

class CanonicalPitch2D extends StatelessWidget {
  const CanonicalPitch2D({
    super.key,
    required this.snapshot,
    required this.overlayMode,
  });

  final LiveMatchSnapshot snapshot;
  final LiveMatchOverlayMode overlayMode;

  @override
  Widget build(BuildContext context) {
    final CanonicalOverlayStatus status = canonicalOverlayStatuses(
      snapshot,
    ).singleWhere((CanonicalOverlayStatus item) => item.mode == overlayMode);
    if (status.state != CanonicalMatchSurfaceState.confirmed) {
      return _StatePanel(
        title: '${status.label} overlay blocked',
        detail: status.detail,
        state: status.state,
      );
    }
    return AspectRatio(
      aspectRatio: 16 / 10,
      child: CustomPaint(
        painter: _CanonicalPitchPainter(snapshot.stats, overlayMode),
        child: Stack(
          children: <Widget>[
            ..._markers(snapshot.homeLineup, isHome: true),
            ..._markers(snapshot.awayLineup, isHome: false),
          ],
        ),
      ),
    );
  }

  List<Widget> _markers(
    List<LiveMatchLineupPlayer> players, {
    required bool isHome,
  }) {
    return players
        .take(11)
        .toList(growable: false)
        .asMap()
        .entries
        .map((MapEntry<int, LiveMatchLineupPlayer> entry) {
          final Offset offset = _lineupOffset(entry.key, isHome: isHome);
          return Positioned(
            left: offset.dx * 100,
            top: offset.dy * 100,
            child: FractionalTranslation(
              translation: const Offset(-0.5, -0.5),
              child: _PitchMarker(player: entry.value, isHome: isHome),
            ),
          );
        })
        .toList(growable: false);
  }

  Offset _lineupOffset(int index, {required bool isHome}) {
    const List<Offset> shape = <Offset>[
      Offset(0.08, 0.50),
      Offset(0.20, 0.22),
      Offset(0.20, 0.44),
      Offset(0.20, 0.66),
      Offset(0.20, 0.82),
      Offset(0.40, 0.30),
      Offset(0.43, 0.50),
      Offset(0.40, 0.70),
      Offset(0.62, 0.28),
      Offset(0.68, 0.50),
      Offset(0.62, 0.72),
    ];
    final Offset base = shape[index.clamp(0, shape.length - 1).toInt()];
    return Offset(isHome ? base.dx : 1 - base.dx, base.dy);
  }
}

class _PitchMarker extends StatelessWidget {
  const _PitchMarker({required this.player, required this.isHome});

  final LiveMatchLineupPlayer player;
  final bool isHome;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 28,
      height: 28,
      child: DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isHome ? Colors.greenAccent : Colors.amberAccent,
        ),
        child: Center(
          child: Text(
            player.position,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelSmall,
          ),
        ),
      ),
    );
  }
}

class _CanonicalPitchPainter extends CustomPainter {
  const _CanonicalPitchPainter(this.stats, this.mode);

  final LiveMatchStatsSnapshot? stats;
  final LiveMatchOverlayMode mode;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect bounds = Offset.zero & size;
    canvas.drawRect(bounds, Paint()..color = const Color(0xFF0B5A38));
    final Paint line =
        Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2;
    final Rect pitch = bounds.deflate(10);
    _paintOverlay(canvas, pitch, size);
    canvas.drawRect(pitch, line);
    canvas.drawLine(
      Offset(size.width / 2, pitch.top),
      Offset(size.width / 2, pitch.bottom),
      line,
    );
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 28, line);
  }

  void _paintOverlay(Canvas canvas, Rect pitch, Size size) {
    switch (mode) {
      case LiveMatchOverlayMode.pressure:
        _paintSplit(canvas, pitch, stats?.pressure, Colors.orangeAccent);
        break;
      case LiveMatchOverlayMode.territory:
        _paintSplit(canvas, pitch, stats?.territory, Colors.lightBlueAccent);
        break;
      case LiveMatchOverlayMode.shots:
      case LiveMatchOverlayMode.xg:
        for (final LiveMatchShotMarker shot
            in stats?.shotMap ?? const <LiveMatchShotMarker>[]) {
          final double radius =
              mode == LiveMatchOverlayMode.xg
                  ? 5 + shot.xg.clamp(0, 1) * 18
                  : 8;
          canvas.drawCircle(
            Offset(shot.x * size.width, shot.y * size.height),
            radius,
            Paint()
              ..color =
                  shot.isHome
                      ? Colors.lightGreenAccent.withValues(alpha: 0.55)
                      : Colors.amberAccent.withValues(alpha: 0.55),
          );
        }
        break;
      case LiveMatchOverlayMode.market:
        canvas.drawRRect(
          RRect.fromRectAndRadius(pitch.deflate(22), const Radius.circular(8)),
          Paint()..color = Colors.blueAccent.withValues(alpha: 0.18),
        );
        break;
      case LiveMatchOverlayMode.shape:
        break;
    }
  }

  void _paintSplit(
    Canvas canvas,
    Rect pitch,
    LiveMatchStatPair? pair,
    Color color,
  ) {
    if (pair == null) {
      return;
    }
    canvas.drawRect(
      Rect.fromLTWH(
        pitch.left,
        pitch.top,
        pitch.width * pair.homeShare,
        pitch.height,
      ),
      Paint()..color = color.withValues(alpha: 0.18),
    );
  }

  @override
  bool shouldRepaint(covariant _CanonicalPitchPainter oldDelegate) {
    return oldDelegate.stats != stats || oldDelegate.mode != mode;
  }
}

class CanonicalLiveIntelligenceRail extends StatelessWidget {
  const CanonicalLiveIntelligenceRail({super.key, required this.snapshot});

  final LiveMatchSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final LiveMatchLiveIntelligence? intelligence = snapshot.liveIntelligence;
    if (intelligence == null) {
      return const _StatePanel(
        title: 'Live intelligence blocked',
        detail: 'Backend intelligence payload missing',
        state: CanonicalMatchSurfaceState.blocked,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Live intelligence',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        if (intelligence.summary != null) Text(intelligence.summary!),
        const SizedBox(height: 8),
        ...intelligence.signals.map(
          (LiveMatchIntelligenceSignal signal) => ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.insights_outlined),
            title: Text(signal.title),
            subtitle: Text(signal.detail),
            trailing: signal.severity == null ? null : Text(signal.severity!),
          ),
        ),
      ],
    );
  }
}

class CanonicalTimelineList extends StatelessWidget {
  const CanonicalTimelineList({super.key, required this.events});

  final List<LiveMatchEvent> events;

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) {
      return const _StatePanel(
        title: 'Timeline empty',
        detail: 'Backend event payload missing',
        state: CanonicalMatchSurfaceState.empty,
      );
    }
    return Column(
      children: events
          .map(
            (LiveMatchEvent event) => ListTile(
              leading: Text('${event.minute} min'),
              title: Text(event.title),
              subtitle: Text(event.detail),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _StatePanel extends StatelessWidget {
  const _StatePanel({
    required this.title,
    required this.detail,
    required this.state,
  });

  final String title;
  final String detail;
  final CanonicalMatchSurfaceState state;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).dividerColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: <Widget>[
            Icon(
              state == CanonicalMatchSurfaceState.confirmed
                  ? Icons.check_circle_outline
                  : Icons.block_outlined,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[Text(title), Text(detail)],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
