import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class Gtex2dPitch extends StatefulWidget {
  const Gtex2dPitch({
    super.key,
    required this.match,
    required this.onPlayerSelected,
  });

  final GtexLiveMatchState match;
  final ValueChanged<String> onPlayerSelected;

  @override
  State<Gtex2dPitch> createState() => _Gtex2dPitchState();
}

class _HeatmapSample {
  const _HeatmapSample({
    required this.x,
    required this.y,
    required this.isHome,
    required this.weight,
  });

  final double x;
  final double y;
  final bool isHome;
  final double weight;
}

class _Gtex2dPitchState extends State<Gtex2dPitch> {
  bool _showTacticsOverlay = true;
  bool _showPassingLanes = true;
  bool _showHeatmap = false;
  double _playbackSpeed = 1.0;
  bool _isPaused = false;
  bool _isAudioAtmosphereOn = false;
  final List<_HeatmapSample> _historicalHeatmapSamples = [];

  @override
  void initState() {
    super.initState();
    _recordHeatmapSamples();
  }

  @override
  void didUpdateWidget(Gtex2dPitch oldWidget) {
    super.didUpdateWidget(oldWidget);
    _recordHeatmapSamples();
  }

  void _recordHeatmapSamples() {
    if (widget.match.pitchPlayers.isEmpty) return;
    for (final p in widget.match.pitchPlayers) {
      _historicalHeatmapSamples.add(
        _HeatmapSample(
          x: p.x,
          y: p.y,
          isHome: p.isHome,
          weight: p.hasBall ? 1.5 : 1.0,
        ),
      );
    }
    if (_historicalHeatmapSamples.length > 400) {
      _historicalHeatmapSamples.removeRange(0, _historicalHeatmapSamples.length - 400);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.match.pitchPlayers.isEmpty) {
      return const AspectRatio(
        aspectRatio: 16 / 9,
        child: GtexMatchEmptyFeed(
          icon: Icons.grid_on_rounded,
          title: 'Pitch feed unavailable',
          message:
              'Player positions have not been supplied by the live match authority.',
        ),
      );
    }

    final int markerDurationMs = _isPaused ? 9999999 : (380 / _playbackSpeed).toInt();

    return LayoutBuilder(
      builder: (context, outerConstraints) {
        final bool compact = outerConstraints.maxWidth < 620;
        return AspectRatio(
          aspectRatio: 16 / 9,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final double pitchWidth = constraints.maxWidth;
              final double pitchHeight = constraints.maxHeight;
              final double markerWidth = compact ? 116.0 : 104.0;
              final double maxMarkerLeft =
                  (pitchWidth - markerWidth).clamp(0.0, double.infinity).toDouble();
              final double maxMarkerTop =
                  (pitchHeight - 58.0).clamp(0.0, double.infinity).toDouble();

              // Compute ball position
              final GtexPitchPlayer? ballOwner = widget.match.pitchPlayers
                  .cast<GtexPitchPlayer?>()
                  .firstWhere(
                    (p) => p?.hasBall ?? false,
                    orElse: () => null,
                  );

              final double ballX = widget.match.ball?.x ??
                  (ballOwner != null ? ballOwner.x : 0.5);
              final double ballY = widget.match.ball?.y ??
                  (ballOwner != null ? ballOwner.y : 0.5);
              final double ballZ = widget.match.ball?.z ?? 0.0;
              final bool isInFlight = widget.match.ball?.isInFlight ?? false;

              // Selected player for passing lanes
              final GtexPitchPlayer? selectedPlayer = widget.match.pitchPlayers
                  .cast<GtexPitchPlayer?>()
                  .firstWhere(
                    (p) => p?.playerId == widget.match.selectedPlayerId,
                    orElse: () => null,
                  );

              return Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF0F2E1A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: GtexMatchVisualTokens.borderStrong),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x66000000),
                      blurRadius: 16,
                      offset: Offset(0, 8),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Stack(
                    children: [
                      // Base pitch turf and lines
                      const Positioned.fill(child: _PitchPainterLayer()),

                      // Positional Heatmap Layer
                      if (_showHeatmap)
                        Positioned.fill(
                          child: CustomPaint(
                            painter: _PitchHeatmapPainter(
                              players: widget.match.pitchPlayers,
                              ballX: ballX,
                              ballY: ballY,
                              historicalSamples: _historicalHeatmapSamples,
                            ),
                          ),
                        ),

                      // Tactical overlay: defensive lines, team compactness, passing lanes
                      if (_showTacticsOverlay)
                        Positioned.fill(
                          child: CustomPaint(
                            painter: _TacticsPitchOverlayPainter(
                              players: widget.match.pitchPlayers,
                              selectedPlayer: _showPassingLanes ? selectedPlayer : null,
                              ballX: ballX,
                              ballY: ballY,
                            ),
                          ),
                        ),

                      // Player Markers
                      for (final GtexPitchPlayer player in widget.match.pitchPlayers)
                        AnimatedPositioned(
                          key: ValueKey<String>(player.playerId),
                          duration: Duration(milliseconds: markerDurationMs),
                          curve: Curves.easeInOutCubic,
                          width: markerWidth,
                          height: 58,
                          left: (player.x * pitchWidth - markerWidth / 2)
                              .clamp(0.0, maxMarkerLeft)
                              .toDouble(),
                          top: (player.y * pitchHeight - 18)
                              .clamp(0.0, maxMarkerTop)
                              .toDouble(),
                          child: _PitchPlayerMarker(
                            player: player,
                            selected: widget.match.selectedPlayerId == player.playerId,
                            compact: compact,
                            onTap: () => widget.onPlayerSelected(player.playerId),
                          ),
                        ),

                      // 2.5D Animated Ball Physics
                      _DynamicBallLayer(
                        ballX: ballX,
                        ballY: ballY,
                        ballZ: ballZ,
                        isInFlight: isInFlight,
                        pitchWidth: pitchWidth,
                        pitchHeight: pitchHeight,
                        isPaused: _isPaused,
                        playbackSpeed: _playbackSpeed,
                      ),

                      // Freeze Frame Notification Banner
                      if (_isPaused)
                        Positioned(
                          bottom: 12,
                          left: 0,
                          right: 0,
                          child: Center(
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                              decoration: BoxDecoration(
                                color: const Color(0xE60F172A),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: const Color(0xFFFFB800), width: 1.0),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.pause_circle_filled_rounded, size: 14, color: Color(0xFFFFB800)),
                                  SizedBox(width: 6),
                                  Text(
                                    'TACTICAL FREEZE FRAME · TAP PLAY TO RESUME',
                                    style: TextStyle(
                                      color: Color(0xFFFFB800),
                                      fontSize: 10,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 0.6,
                                      fontFamily: 'JetBrains Mono',
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),

                      // Header Toolbar: feed tag + tactical toggles
                      Positioned(
                        left: 10,
                        top: 10,
                        right: 10,
                        child: Wrap(
                          alignment: WrapAlignment.spaceBetween,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          spacing: 8,
                          runSpacing: 6,
                          children: [
                            _PitchFeedTag(matchId: widget.match.matchId),
                            _TacticalToolbar(
                              compact: compact,
                              showTactics: _showTacticsOverlay,
                              showLanes: _showPassingLanes,
                              showHeatmap: _showHeatmap,
                              playbackSpeed: _playbackSpeed,
                              isPaused: _isPaused,
                              isAudioAtmosphereOn: _isAudioAtmosphereOn,
                              onToggleTactics: () => setState(() {
                                _showTacticsOverlay = !_showTacticsOverlay;
                              }),
                              onToggleLanes: () => setState(() {
                                _showPassingLanes = !_showPassingLanes;
                              }),
                              onToggleHeatmap: () => setState(() {
                                _showHeatmap = !_showHeatmap;
                              }),
                              onCycleSpeed: () => setState(() {
                                if (_playbackSpeed == 0.5) {
                                  _playbackSpeed = 1.0;
                                } else if (_playbackSpeed == 1.0) {
                                  _playbackSpeed = 2.0;
                                } else {
                                  _playbackSpeed = 0.5;
                                }
                              }),
                              onTogglePause: () => setState(() {
                                _isPaused = !_isPaused;
                              }),
                              onToggleAudio: () => setState(() {
                                _isAudioAtmosphereOn = !_isAudioAtmosphereOn;
                              }),
                              ballOwner: ballOwner,
                              isInFlight: isInFlight,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }
}

class _DynamicBallLayer extends StatelessWidget {
  const _DynamicBallLayer({
    required this.ballX,
    required this.ballY,
    required this.ballZ,
    required this.isInFlight,
    required this.pitchWidth,
    required this.pitchHeight,
    this.isPaused = false,
    this.playbackSpeed = 1.0,
  });

  final double ballX;
  final double ballY;
  final double ballZ;
  final bool isInFlight;
  final double pitchWidth;
  final double pitchHeight;
  final bool isPaused;
  final double playbackSpeed;

  @override
  Widget build(BuildContext context) {
    final int ballDurationMs = isPaused ? 9999999 : (140 / playbackSpeed).toInt().clamp(40, 350);
    final double groundPixelX = (ballX * pitchWidth).clamp(8.0, pitchWidth - 8.0);
    final double groundPixelY = (ballY * pitchHeight).clamp(8.0, pitchHeight - 8.0);
    final double elevationOffset = (ballZ * 48.0).clamp(0.0, 36.0);
    final double ballPixelY = groundPixelY - elevationOffset;

    final double shadowScale = (1.0 + ballZ * 1.8).clamp(1.0, 2.5);
    final double shadowOpacity = (0.65 / (1.0 + ballZ * 4.0)).clamp(0.12, 0.65);
    final double ballSize = (9.0 + ballZ * 2.5).clamp(9.0, 14.0);

    return IgnorePointer(
      child: Stack(
        children: [
          // Ground drop shadow
          AnimatedPositioned(
            duration: Duration(milliseconds: ballDurationMs),
            curve: Curves.easeOutQuad,
            left: groundPixelX - (6.0 * shadowScale),
            top: groundPixelY + 2.0,
            width: 12.0 * shadowScale,
            height: 6.0 * shadowScale,
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Color.fromRGBO(0, 0, 0, shadowOpacity),
                borderRadius: BorderRadius.all(
                  Radius.elliptical(12.0 * shadowScale, 6.0 * shadowScale),
                ),
              ),
            ),
          ),

          // The physical ball token
          AnimatedPositioned(
            duration: Duration(milliseconds: ballDurationMs),
            curve: Curves.easeOutQuad,
            left: groundPixelX - (ballSize / 2),
            top: ballPixelY - (ballSize / 2),
            width: ballSize,
            height: ballSize,
            child: Stack(
              clipBehavior: Clip.none,
              alignment: Alignment.center,
              children: [
                Container(
                  width: ballSize,
                  height: ballSize,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const RadialGradient(
                      center: Alignment(-0.35, -0.4),
                      radius: 0.8,
                      colors: [
                        Color(0xFFFFFFFF),
                        Color(0xFFF0F4F8),
                        Color(0xFFB0BAC5),
                        Color(0xFF1E293B),
                      ],
                      stops: [0.0, 0.45, 0.85, 1.0],
                    ),
                    border: Border.all(
                      color: const Color(0xFF0F172A),
                      width: 1.0,
                    ),
                    boxShadow: [
                      if (isInFlight)
                        BoxShadow(
                          color: const Color(0x8000E87A),
                          blurRadius: 8 + ballZ * 6,
                          spreadRadius: 1,
                        ),
                    ],
                  ),
                ),

                // Height elevation badge when ball is airborne
                if (ballZ > 0.08)
                  Positioned(
                    top: -16,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                      decoration: BoxDecoration(
                        color: const Color(0xE60F172A),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: const Color(0x8000E87A),
                          width: 0.8,
                        ),
                      ),
                      child: Text(
                        '${(ballZ * 12).toStringAsFixed(1)}m',
                        style: const TextStyle(
                          color: Color(0xFF00E87A),
                          fontSize: 8,
                          fontWeight: FontWeight.w900,
                          fontFamily: 'JetBrains Mono',
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TacticsPitchOverlayPainter extends CustomPainter {
  const _TacticsPitchOverlayPainter({
    required this.players,
    required this.selectedPlayer,
    required this.ballX,
    required this.ballY,
  });

  final List<GtexPitchPlayer> players;
  final GtexPitchPlayer? selectedPlayer;
  final double ballX;
  final double ballY;

  @override
  void paint(Canvas canvas, Size size) {
    if (players.isEmpty) return;

    final homePlayers = players.where((p) => p.isHome).toList();
    final awayPlayers = players.where((p) => !p.isHome).toList();

    // 1. Draw Defensive Lines (Home Cyan, Away Amber)
    _drawDefensiveLines(canvas, size, homePlayers, awayPlayers);

    // 2. Draw Compactness Zone (Translucent team hulls)
    _drawTeamCompactness(canvas, size, homePlayers, const Color(0x1200E87A));
    _drawTeamCompactness(canvas, size, awayPlayers, const Color(0x12FFB800));

    // 3. Draw Passing Lanes from selected player
    if (selectedPlayer != null) {
      _drawPassingLanes(canvas, size, selectedPlayer!, players);
    }
  }

  void _drawDefensiveLines(
    Canvas canvas,
    Size size,
    List<GtexPitchPlayer> homePlayers,
    List<GtexPitchPlayer> awayPlayers,
  ) {
    if (homePlayers.isEmpty || awayPlayers.isEmpty) return;

    // Home defensive line: average X of defenders (excluding GK if possible)
    final homeOutfield = homePlayers.where((p) => p.role != 'GK').toList();
    final homeDefenders = (homeOutfield.isNotEmpty ? homeOutfield : homePlayers)
        .take(4)
        .toList();
    final double homeLineX = homeDefenders.map((p) => p.x).reduce((a, b) => a + b) /
        homeDefenders.length *
        size.width;

    // Away defensive line: average X of defenders (excluding GK if possible)
    final awayOutfield = awayPlayers.where((p) => p.role != 'GK').toList();
    final awayDefenders = (awayOutfield.isNotEmpty ? awayOutfield : awayPlayers)
        .take(4)
        .toList();
    final double awayLineX = awayDefenders.map((p) => p.x).reduce((a, b) => a + b) /
        awayDefenders.length *
        size.width;

    // Draw Home line
    final Paint homePaint = Paint()
      ..color = const Color(0x6600E87A)
      ..strokeWidth = 1.4
      ..style = PaintingStyle.stroke;
    _drawDashedLine(canvas, Offset(homeLineX, 16), Offset(homeLineX, size.height - 16), homePaint, 6, 4);

    // Draw Away line
    final Paint awayPaint = Paint()
      ..color = const Color(0x66FFB800)
      ..strokeWidth = 1.4
      ..style = PaintingStyle.stroke;
    _drawDashedLine(canvas, Offset(awayLineX, 16), Offset(awayLineX, size.height - 16), awayPaint, 6, 4);
  }

  void _drawTeamCompactness(
    Canvas canvas,
    Size size,
    List<GtexPitchPlayer> team,
    Color fillColor,
  ) {
    if (team.length < 3) return;

    final List<Offset> points = team
        .where((p) => p.role != 'GK')
        .map((p) => Offset(p.x * size.width, p.y * size.height))
        .toList();
    if (points.length < 3) return;

    final Path path = Path();
    path.moveTo(points.first.dx, points.first.dy);
    for (int i = 1; i < points.length; i++) {
      path.lineTo(points[i].dx, points[i].dy);
    }
    path.close();

    final Paint fill = Paint()
      ..color = fillColor
      ..style = PaintingStyle.fill;
    canvas.drawPath(path, fill);
  }

  void _drawPassingLanes(
    Canvas canvas,
    Size size,
    GtexPitchPlayer passer,
    List<GtexPitchPlayer> allPlayers,
  ) {
    final Offset origin = Offset(passer.x * size.width, passer.y * size.height);
    final teammates = allPlayers.where((p) => p.isHome == passer.isHome && p.playerId != passer.playerId);

    final Paint lanePaint = Paint()
      ..color = const Color(0xAA00E87A)
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;

    for (final mate in teammates) {
      final Offset target = Offset(mate.x * size.width, mate.y * size.height);
      final double distance = (origin - target).distance;

      // Only draw lanes within sensible pass distance
      if (distance < size.width * 0.42) {
        _drawDashedLine(canvas, origin, target, lanePaint, 5, 4);

        // Small indicator dot near the teammate
        final Offset mid = Offset(
          origin.dx + (target.dx - origin.dx) * 0.75,
          origin.dy + (target.dy - origin.dy) * 0.75,
        );
        canvas.drawCircle(mid, 2.0, Paint()..color = const Color(0xCC00E87A));
      }
    }
  }

  void _drawDashedLine(
    Canvas canvas,
    Offset p1,
    Offset p2,
    Paint paint,
    double dashWidth,
    double dashSpace,
  ) {
    final double dx = p2.dx - p1.dx;
    final double dy = p2.dy - p1.dy;
    final double distance = math.sqrt(dx * dx + dy * dy);
    if (distance <= 0) return;

    final double ux = dx / distance;
    final double uy = dy / distance;
    double current = 0.0;

    while (current < distance) {
      final double next = math.min(current + dashWidth, distance);
      canvas.drawLine(
        Offset(p1.dx + ux * current, p1.dy + uy * current),
        Offset(p1.dx + ux * next, p1.dy + uy * next),
        paint,
      );
      current += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant _TacticsPitchOverlayPainter oldDelegate) {
    return oldDelegate.players != players ||
        oldDelegate.selectedPlayer != selectedPlayer ||
        oldDelegate.ballX != ballX ||
        oldDelegate.ballY != ballY;
  }
}

class _PitchPainterLayer extends StatelessWidget {
  const _PitchPainterLayer();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _PitchPainter());
  }
}

class _PitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint line = Paint()
      ..color = const Color(0xFFE8EDF4).withOpacity(.64)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    final Paint grid = Paint()
      ..color = const Color(0xFFE8EDF4).withOpacity(.08)
      ..strokeWidth = .8;
    final Paint band = Paint()..style = PaintingStyle.fill;

    // Grass alternating stripes
    for (var i = 0; i < 8; i++) {
      band.color = Color(i.isEven ? 0xFF12371F : 0xFF0F301B);
      canvas.drawRect(
        Rect.fromLTWH(size.width * i / 8, 0, size.width / 8, size.height),
        band,
      );
    }
    for (var i = 1; i < 8; i++) {
      final double x = size.width * i / 8;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
    }
    for (var i = 1; i < 6; i++) {
      final double y = size.height * i / 6;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }

    // Outer pitch boundary
    canvas.drawRect(
      Rect.fromLTWH(16, 16, size.width - 32, size.height - 32),
      line,
    );

    // Halfway line
    canvas.drawLine(
      Offset(size.width / 2, 16),
      Offset(size.width / 2, size.height - 16),
      line,
    );

    // Center circle
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      size.height * .14,
      line,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      3,
      Paint()..color = const Color(0xFFE8EDF4),
    );

    // Left Penalty box
    canvas.drawRect(
      Rect.fromLTWH(16, size.height * .30, size.width * .13, size.height * .40),
      line,
    );
    // Right Penalty box
    canvas.drawRect(
      Rect.fromLTWH(
        size.width - 16 - size.width * .13,
        size.height * .30,
        size.width * .13,
        size.height * .40,
      ),
      line,
    );

    // Left Goal area
    canvas.drawRect(
      Rect.fromLTWH(16, size.height * .40, size.width * .045, size.height * .20),
      line,
    );
    // Right Goal area
    canvas.drawRect(
      Rect.fromLTWH(
        size.width - 16 - size.width * .045,
        size.height * .40,
        size.width * .045,
        size.height * .20,
      ),
      line,
    );

    // Penalty spots
    canvas.drawCircle(
      Offset(16 + size.width * .095, size.height / 2),
      2.5,
      Paint()..color = const Color(0xFFE8EDF4),
    );
    canvas.drawCircle(
      Offset(size.width - 16 - size.width * .095, size.height / 2),
      2.5,
      Paint()..color = const Color(0xFFE8EDF4),
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _PitchPlayerMarker extends StatelessWidget {
  const _PitchPlayerMarker({
    required this.player,
    required this.selected,
    required this.compact,
    required this.onTap,
  });

  final GtexPitchPlayer player;
  final bool selected;
  final bool compact;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color teamColor = player.isHome
        ? GtexMatchVisualTokens.live
        : GtexMatchVisualTokens.amber;

    final bool isPressing = player.state.toLowerCase() == 'pressing';
    final bool isSprint = player.animationState.toLowerCase() == 'sprint' ||
        player.state.toLowerCase() == 'sprint';

    final Widget marker = Stack(
      alignment: Alignment.center,
      children: [
        // Pressing Radar Pulse
        if (isPressing)
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFFFF4D4D).withOpacity(0.7),
                width: 1.8,
              ),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x66FF4D4D),
                  blurRadius: 10,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),

        // Stamina gauge ring
        CustomPaint(
          size: Size(selected ? 34 : 26, selected ? 34 : 26),
          painter: _StaminaRingPainter(staminaPct: player.staminaPct),
        ),

        // Core kit circle
        AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          width: selected ? 28 : 22,
          height: selected ? 28 : 22,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: teamColor,
            border: Border.all(
              color: player.hasBall
                  ? GtexMatchVisualTokens.textPrimary
                  : const Color(0xFF0F172A),
              width: player.hasBall ? 2.5 : 1.2,
            ),
            boxShadow: [
              if (selected || player.hasBall)
                BoxShadow(
                  color: teamColor.withOpacity(0.55),
                  blurRadius: 14,
                  spreadRadius: 2,
                ),
            ],
          ),
          child: Center(
            child: Text(
              '${player.shirtNumber}',
              style: const TextStyle(
                color: Color(0xFF0A0C0F),
                fontWeight: FontWeight.w900,
                fontSize: 9.5,
                fontFamily: 'JetBrains Mono',
              ),
            ),
          ),
        ),
      ],
    );

    final bool nameplateVisible = !compact || player.hasBall || selected || isPressing;
    final String nameplate = player.hasBall || selected
        ? player.name
        : _surname(player.name);

    return Tooltip(
      message: '${player.name} #${player.shirtNumber} (${player.role ?? 'Player'}) · ${player.staminaPct.toInt()}% STA',
      child: GestureDetector(
        onTap: onTap,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            marker,
            if (nameplateVisible) ...[
              const SizedBox(height: 2),
              Container(
                constraints: BoxConstraints(maxWidth: compact ? 104 : 92),
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1.5),
                decoration: BoxDecoration(
                  color: player.hasBall
                      ? const Color(0xF507111D)
                      : (isPressing ? const Color(0xEE2A0808) : const Color(0xDD0A0C0F)),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: player.hasBall
                        ? GtexMatchVisualTokens.amber
                        : (isPressing
                            ? const Color(0xFFFF4D4D)
                            : (selected
                                ? const Color(0xFF00E87A)
                                : Colors.white.withOpacity(.12))),
                    width: 0.8,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    if (isPressing) ...[
                      const Icon(Icons.bolt, size: 8, color: Color(0xFFFF4D4D)),
                      const SizedBox(width: 2),
                    ] else if (isSprint) ...[
                      const Icon(Icons.speed, size: 8, color: Color(0xFF00E87A)),
                      const SizedBox(width: 2),
                    ],
                    Flexible(
                      child: Text(
                        nameplate.toUpperCase(),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: player.hasBall
                              ? GtexMatchVisualTokens.amber
                              : (isPressing
                                  ? const Color(0xFFFF4D4D)
                                  : GtexMatchVisualTokens.textPrimary),
                          fontSize: 8.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: .2,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _surname(String name) {
    final List<String> parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty) {
      return name;
    }
    return parts.last;
  }
}

class _StaminaRingPainter extends CustomPainter {
  const _StaminaRingPainter({required this.staminaPct});

  final double staminaPct;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    final backgroundPaint = Paint()
      ..color = Colors.white.withOpacity(0.12)
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
    canvas.drawCircle(center, radius, backgroundPaint);

    final sweep = (staminaPct.clamp(0.0, 100.0) / 100.0) * 2 * math.pi;
    final ringColor = staminaPct > 68
        ? const Color(0xFF00E87A)
        : (staminaPct > 38 ? const Color(0xFFFFB800) : const Color(0xFFFF4D4D));

    final staminaPaint = Paint()
      ..color = ringColor
      ..strokeWidth = 1.6
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      sweep,
      false,
      staminaPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _StaminaRingPainter oldDelegate) {
    return oldDelegate.staminaPct != staminaPct;
  }
}

class _TacticalToolbar extends StatelessWidget {
  const _TacticalToolbar({
    required this.compact,
    required this.showTactics,
    required this.showLanes,
    required this.showHeatmap,
    required this.playbackSpeed,
    required this.isPaused,
    required this.isAudioAtmosphereOn,
    required this.onToggleTactics,
    required this.onToggleLanes,
    required this.onToggleHeatmap,
    required this.onCycleSpeed,
    required this.onTogglePause,
    required this.onToggleAudio,
    required this.ballOwner,
    required this.isInFlight,
  });

  final bool compact;
  final bool showTactics;
  final bool showLanes;
  final bool showHeatmap;
  final double playbackSpeed;
  final bool isPaused;
  final bool isAudioAtmosphereOn;
  final VoidCallback onToggleTactics;
  final VoidCallback onToggleLanes;
  final VoidCallback onToggleHeatmap;
  final VoidCallback onCycleSpeed;
  final VoidCallback onTogglePause;
  final VoidCallback onToggleAudio;
  final GtexPitchPlayer? ballOwner;
  final bool isInFlight;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Possession Pill
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
          decoration: BoxDecoration(
            color: const Color(0xCC0A0C0F),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(
              color: isInFlight
                  ? const Color(0x6600E87A)
                  : (ballOwner?.isHome ?? true
                      ? const Color(0x6600E87A)
                      : const Color(0x66FFB800)),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isInFlight
                      ? const Color(0xFFFFF8E7)
                      : (ballOwner?.isHome ?? true
                          ? GtexMatchVisualTokens.live
                          : GtexMatchVisualTokens.amber),
                ),
              ),
              const SizedBox(width: 5),
              Text(
                isInFlight
                    ? 'IN FLIGHT'
                    : (ballOwner != null
                        ? (ballOwner!.isHome ? 'HOME POSS' : 'AWAY POSS')
                        : 'OPEN PLAY'),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 5),

        // Tactics Overlay Toggle
        InkWell(
          onTap: onToggleTactics,
          borderRadius: BorderRadius.circular(4),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: showTactics ? const Color(0xE60A2E1A) : const Color(0xCC0A0C0F),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: showTactics ? const Color(0xFF00E87A) : Colors.white24,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.layers_rounded,
                  size: 11,
                  color: showTactics ? const Color(0xFF00E87A) : Colors.white60,
                ),
                if (!compact) ...[
                  const SizedBox(width: 4),
                  Text(
                    'TACTICS',
                    style: TextStyle(
                      color: showTactics ? const Color(0xFF00E87A) : Colors.white70,
                      fontSize: 9,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(width: 4),

        // Passing Lanes Toggle
        InkWell(
          onTap: onToggleLanes,
          borderRadius: BorderRadius.circular(4),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: showLanes ? const Color(0xE60A2E1A) : const Color(0xCC0A0C0F),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: showLanes ? const Color(0xFF00E87A) : Colors.white24,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.alt_route_rounded,
                  size: 11,
                  color: showLanes ? const Color(0xFF00E87A) : Colors.white60,
                ),
                if (!compact) ...[
                  const SizedBox(width: 4),
                  Text(
                    'LANES',
                    style: TextStyle(
                      color: showLanes ? const Color(0xFF00E87A) : Colors.white70,
                      fontSize: 9,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(width: 4),

        // Live Positional Heatmap Toggle
        InkWell(
          onTap: onToggleHeatmap,
          borderRadius: BorderRadius.circular(4),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: showHeatmap ? const Color(0xE67C2D12) : const Color(0xCC0A0C0F),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: showHeatmap ? const Color(0xFFFF5722) : Colors.white24,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.whatshot_rounded,
                  size: 11,
                  color: showHeatmap ? const Color(0xFFFF5722) : Colors.white60,
                ),
                if (!compact) ...[
                  const SizedBox(width: 4),
                  Text(
                    'HEATMAP',
                    style: TextStyle(
                      color: showHeatmap ? const Color(0xFFFF5722) : Colors.white70,
                      fontSize: 9,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(width: 4),

        // Pause / Resume Toggle
        InkWell(
          onTap: onTogglePause,
          borderRadius: BorderRadius.circular(4),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: isPaused ? const Color(0xE678350F) : const Color(0xCC0A0C0F),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: isPaused ? const Color(0xFFFFB800) : Colors.white24,
              ),
            ),
            child: Icon(
              isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
              size: 11,
              color: isPaused ? const Color(0xFFFFB800) : Colors.white70,
            ),
          ),
        ),
        const SizedBox(width: 4),

        // Speed Cycle Pill (0.5x, 1.0x, 2.0x)
        InkWell(
          onTap: onCycleSpeed,
          borderRadius: BorderRadius.circular(4),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xCC0A0C0F),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: const Color(0x6600E87A)),
            ),
            child: Text(
              '${playbackSpeed.toStringAsFixed(1)}x',
              style: const TextStyle(
                color: Color(0xFF00E87A),
                fontSize: 9,
                fontWeight: FontWeight.w900,
                fontFamily: 'JetBrains Mono',
              ),
            ),
          ),
        ),
        const SizedBox(width: 4),

        // Stadium Audio Atmosphere Toggle
        Tooltip(
          message: isAudioAtmosphereOn
              ? 'SYNTHESIZED STADIUM ATMOSPHERE (ACTIVE)'
              : 'SYNTHESIZED STADIUM ATMOSPHERE (MUTED)',
          child: InkWell(
            onTap: onToggleAudio,
            borderRadius: BorderRadius.circular(4),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              decoration: BoxDecoration(
                color: isAudioAtmosphereOn ? const Color(0xE61E3A8A) : const Color(0xCC0A0C0F),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(
                  color: isAudioAtmosphereOn ? const Color(0xFF60A5FA) : Colors.white24,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isAudioAtmosphereOn ? Icons.volume_up_rounded : Icons.volume_off_rounded,
                    size: 11,
                    color: isAudioAtmosphereOn ? const Color(0xFF60A5FA) : Colors.white60,
                  ),
                  if (isAudioAtmosphereOn) ...[
                    const SizedBox(width: 4),
                    const _AtmosphereEqualizerIndicator(),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _PitchHeatmapPainter extends CustomPainter {
  const _PitchHeatmapPainter({
    required this.players,
    required this.ballX,
    required this.ballY,
    required this.historicalSamples,
  });

  final List<GtexPitchPlayer> players;
  final double ballX;
  final double ballY;
  final List<_HeatmapSample> historicalSamples;

  @override
  void paint(Canvas canvas, Size size) {
    if (players.isEmpty && historicalSamples.isEmpty) return;

    final Paint radialPaint = Paint()..blendMode = BlendMode.screen;

    // Draw historical accumulated spatial coverage
    for (final sample in historicalSamples) {
      final double sx = sample.x * size.width;
      final double sy = sample.y * size.height;
      final double radius = size.width * 0.08 * sample.weight;

      final Color centerColor = sample.isHome
          ? const Color(0x1500E87A)
          : const Color(0x15FFB800);

      radialPaint.shader = RadialGradient(
        colors: [
          centerColor,
          Colors.transparent,
        ],
        stops: const [0.0, 1.0],
      ).createShader(Rect.fromCircle(center: Offset(sx, sy), radius: radius));

      canvas.drawCircle(Offset(sx, sy), radius, radialPaint);
    }

    // Draw player presence heat zones
    for (final player in players) {
      final double px = player.x * size.width;
      final double py = player.y * size.height;
      final double radius = size.width * 0.13;

      final Color centerColor = player.isHome
          ? const Color(0x4400E87A)
          : const Color(0x44FFB800);

      radialPaint.shader = RadialGradient(
        colors: [
          centerColor,
          centerColor.withAlpha(25),
          Colors.transparent,
        ],
        stops: const [0.0, 0.45, 1.0],
      ).createShader(Rect.fromCircle(center: Offset(px, py), radius: radius));

      canvas.drawCircle(Offset(px, py), radius, radialPaint);
    }

    // Ball heat epicenter (high intensity hot spot)
    final double bx = ballX * size.width;
    final double by = ballY * size.height;
    final double ballRadius = size.width * 0.16;

    radialPaint.shader = RadialGradient(
      colors: const [
        Color(0x66FF4500),
        Color(0x33FFA500),
        Colors.transparent,
      ],
      stops: const [0.0, 0.5, 1.0],
    ).createShader(Rect.fromCircle(center: Offset(bx, by), radius: ballRadius));

    canvas.drawCircle(Offset(bx, by), ballRadius, radialPaint);
  }

  @override
  bool shouldRepaint(covariant _PitchHeatmapPainter oldDelegate) {
    return oldDelegate.ballX != ballX ||
        oldDelegate.ballY != ballY ||
        oldDelegate.players != players ||
        oldDelegate.historicalSamples.length != historicalSamples.length;
  }
}

class _AtmosphereEqualizerIndicator extends StatefulWidget {
  const _AtmosphereEqualizerIndicator();

  @override
  State<_AtmosphereEqualizerIndicator> createState() => _AtmosphereEqualizerIndicatorState();
}

class _AtmosphereEqualizerIndicatorState extends State<_AtmosphereEqualizerIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final double t = _controller.value;
        return Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            _buildBar(2.5 + (t * 5.0)),
            const SizedBox(width: 1.5),
            _buildBar(7.5 - (t * 4.5)),
            const SizedBox(width: 1.5),
            _buildBar(3.5 + (t * 5.5)),
          ],
        );
      },
    );
  }

  Widget _buildBar(double height) {
    return Container(
      width: 2,
      height: height.clamp(2.0, 9.0),
      decoration: BoxDecoration(
        color: const Color(0xFF60A5FA),
        borderRadius: BorderRadius.circular(1),
      ),
    );
  }
}

class _PitchFeedTag extends StatelessWidget {
  const _PitchFeedTag({required this.matchId});

  final String matchId;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xCC0A0C0F),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: const Color(0x6600E87A)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: GtexMatchVisualTokens.live,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            'SPATIAL 2D  ${_shortMatchId(matchId)}',
            style: const TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontSize: 10,
              fontWeight: FontWeight.w900,
              letterSpacing: .7,
            ),
          ),
        ],
      ),
    );
  }

  static String _shortMatchId(String matchId) {
    if (matchId.length <= 8) {
      return matchId.toUpperCase();
    }
    return matchId.substring(0, 8).toUpperCase();
  }
}
