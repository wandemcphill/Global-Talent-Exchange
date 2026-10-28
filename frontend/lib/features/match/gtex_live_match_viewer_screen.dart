import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../data/live_match_repository.dart';
import '../owner_console/widgets/gtex_cinema_3d_stage.dart';

const Color _bg = Color(0xFF06090E);
const Color _panel = Color(0xFF0E141D);
const Color _border = Color(0xFF243040);
const Color _text = Color(0xFFF4F6F8);
const Color _textSecondary = Color(0xFF9AA7B4);
const Color _textMuted = Color(0xFF7F8C99);
const Color _green = Color(0xFF00E87A);
const Color _amber = Color(0xFFFFB800);
const Color _cyan = Color(0xFF38BDF8);
const String _condensed = 'BarlowCondensed';
const List<String> _formations = <String>['4-3-3', '4-4-2', '4-2-3-1', '4-5-1', '5-3-2', '3-5-2'];
const List<String> _mentalities = <String>['attacking', 'balanced', 'defensive'];

/// Live (tick-based) match viewer upgraded with a 60fps 2D/2.5D Spatial Match
/// Engine, Voronoi Territory Shaders, Lofted Pass Arcs, and Strategic 3D
/// Broadcast Cut-Ins (Pre-Match Stadium, Goal Walkout, Full-Time MOTM Gala).
class GtexLiveMatchViewerScreen extends StatefulWidget {
  const GtexLiveMatchViewerScreen({
    super.key,
    required this.matchId,
    required this.side,
    required this.baseUrl,
    required this.accessToken,
    this.backendMode = GteBackendMode.live,
  });

  final String matchId;
  final String side; // 'home' | 'away' — the team this user manages
  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<GtexLiveMatchViewerScreen> createState() => _GtexLiveMatchViewerScreenState();
}

class _GtexLiveMatchViewerScreenState extends State<GtexLiveMatchViewerScreen>
    with SingleTickerProviderStateMixin {
  late final LiveMatchRepository _repo = LiveMatchRepository.standard(
    baseUrl: widget.baseUrl,
    accessToken: widget.accessToken,
    mode: widget.backendMode,
  );
  Timer? _poll;
  late final AnimationController _pitchAnim;
  LiveMatchState? _state;
  String? _error;
  bool _halftimeDoneSent = false;
  bool _settleAttempted = false;
  Map<String, dynamic>? _settlement;

  // 2D / 2.5D Pitch & 3D Broadcast Overlay Controls
  bool _is25DCamera = true;
  bool _showVoronoi = true;
  bool _showHeatmap = false;
  bool _showLanes = true;
  bool _show3DCutIn = false;
  GtexCinema3DScene _active3DScene = GtexCinema3DScene.signingWalkout;

  @override
  void initState() {
    super.initState();
    _pitchAnim = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 24),
    )..repeat();
    _refresh();
    _poll = Timer.periodic(const Duration(seconds: 2), (_) => _refresh());
  }

  @override
  void dispose() {
    _poll?.cancel();
    _pitchAnim.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final LiveMatchState state = await _repo.fetchState(widget.matchId);
      if (!mounted) return;
      setState(() {
        _state = state;
        _error = null;
        if (state.phase != 'half_time') _halftimeDoneSent = false;
      });
      if (state.isFullTime) {
        _poll?.cancel();
        await _settleIfNeeded(state);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Reconnecting…');
    }
  }

  Future<void> _settleIfNeeded(LiveMatchState state) async {
    if (_settleAttempted || widget.side != 'home') return;
    _settleAttempted = true;
    try {
      final Map<String, dynamic> result = await _repo.settleMatch(widget.matchId);
      if (mounted) setState(() => _settlement = result);
    } catch (_) {}
  }

  String get _myFormation =>
      widget.side == 'home' ? (_state?.homeFormation ?? '4-3-3') : (_state?.awayFormation ?? '4-3-3');

  Future<void> _openTactics() async {
    String formation = _myFormation;
    String mentality = 'balanced';
    final bool? applied = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: _panel,
      isScrollControlled: true,
      builder: (BuildContext sheetContext) {
        return StatefulBuilder(
          builder: (BuildContext context, void Function(void Function()) setSheet) {
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text('Your tactics',
                        style: TextStyle(color: _text, fontSize: 17, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    const Text('Applies to your team only. The match keeps playing.',
                        style: TextStyle(color: _textMuted, fontSize: 12)),
                    const SizedBox(height: 14),
                    const Text('FORMATION', style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _formations.map((String f) {
                        final bool sel = f == formation;
                        return GestureDetector(
                          onTap: () => setSheet(() => formation = f),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
                            decoration: BoxDecoration(
                              color: sel ? _green.withValues(alpha: 0.16) : _bg,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: sel ? _green : _border, width: sel ? 1.5 : 0.5),
                            ),
                            child: Text(f,
                                style: TextStyle(
                                    fontFamily: _condensed,
                                    color: sel ? _green : _textSecondary,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w800)),
                          ),
                        );
                      }).toList(growable: false),
                    ),
                    const SizedBox(height: 16),
                    const Text('MENTALITY', style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      children: _mentalities.map((String m) {
                        final bool sel = m == mentality;
                        return GestureDetector(
                          onTap: () => setSheet(() => mentality = m),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
                            decoration: BoxDecoration(
                              color: sel ? _amber.withValues(alpha: 0.16) : _bg,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: sel ? _amber : _border, width: sel ? 1.5 : 0.5),
                            ),
                            child: Text(m[0].toUpperCase() + m.substring(1),
                                style: TextStyle(color: sel ? _amber : _textSecondary, fontWeight: FontWeight.w700)),
                          ),
                        );
                      }).toList(growable: false),
                    ),
                    const SizedBox(height: 18),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: _green, foregroundColor: const Color(0xFF06140C)),
                        onPressed: () => Navigator.of(sheetContext).pop(true),
                        child: const Text('Apply changes'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
    if (applied == true) {
      try {
        final LiveMatchState state = await _repo.setTactics(
          widget.matchId,
          side: widget.side,
          formation: formation,
          mentality: mentality,
        );
        if (mounted) setState(() => _state = state);
      } catch (_) {
        if (mounted) {
          ScaffoldMessenger.of(context)
              .showSnackBar(const SnackBar(content: Text("Couldn't apply tactics. Try again.")));
        }
      }
    }
  }

  Future<void> _halftimeDone() async {
    setState(() => _halftimeDoneSent = true);
    try {
      final LiveMatchState state = await _repo.markHalftimeReady(widget.matchId, side: widget.side);
      if (mounted) setState(() => _state = state);
    } catch (_) {
      if (mounted) setState(() => _halftimeDoneSent = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final LiveMatchState? s = _state;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        foregroundColor: _text,
        elevation: 0,
        title: const Text('Live match'),
        actions: <Widget>[
          if (s != null && !s.isFullTime)
            TextButton.icon(
              onPressed: _openTactics,
              icon: const Icon(Icons.dashboard_customize_rounded, size: 18, color: _green),
              label: const Text('Tactics', style: TextStyle(color: _green)),
            ),
        ],
      ),
      body: s == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Text(_error!, style: const TextStyle(color: _textSecondary)),
            )
          : Stack(
              children: <Widget>[
                _matchBody(s),
                if (s.isHalftime) _halftimeOverlay(s),
              ],
            ),
    );
  }

  Widget _matchBody(LiveMatchState s) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        // Broadcast Scoreboard Header
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[Color(0xFF141E2B), Color(0xFF0A0F17)],
            ),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _green.withValues(alpha: 0.35)),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.55),
                blurRadius: 24,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Column(
            children: <Widget>[
              Text(
                s.isFullTime ? 'FULL TIME' : "${s.minute}'  ·  ${_phaseLabel(s.phase)}",
                style: const TextStyle(
                  color: _amber,
                  fontFamily: _condensed,
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: <Widget>[
                  Expanded(child: _teamSide(s.homeName, s.homeFormation, widget.side == 'home')),
                  Text(
                    '${s.homeScore} - ${s.awayScore}',
                    style: const TextStyle(
                      color: _text,
                      fontFamily: _condensed,
                      fontSize: 34,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  Expanded(child: _teamSide(s.awayName, s.awayFormation, widget.side == 'away', alignEnd: true)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // 2D / 2.5D Pitch Camera & 3D Broadcast Cut-In Toolbar
        Wrap(
          spacing: 6,
          runSpacing: 6,
          alignment: WrapAlignment.spaceBetween,
          children: <Widget>[
            _togglePill(
              label: _is25DCamera ? '2.5D TV BROADCAST' : '2D TOP-DOWN',
              active: _is25DCamera,
              color: _green,
              icon: Icons.videocam_rounded,
              onTap: () => setState(() => _is25DCamera = !_is25DCamera),
            ),
            _togglePill(
              label: 'VORONOI',
              active: _showVoronoi,
              color: _cyan,
              icon: Icons.grid_4x4_rounded,
              onTap: () => setState(() => _showVoronoi = !_showVoronoi),
            ),
            _togglePill(
              label: 'HEATMAP',
              active: _showHeatmap,
              color: const Color(0xFFF43F5E),
              icon: Icons.local_fire_department_rounded,
              onTap: () => setState(() => _showHeatmap = !_showHeatmap),
            ),
            _togglePill(
              label: 'PASS ARCS',
              active: _showLanes,
              color: _green,
              icon: Icons.timeline_rounded,
              onTap: () => setState(() => _showLanes = !_showLanes),
            ),
            _togglePill(
              label: _show3DCutIn ? 'CLOSE 3D CAM' : '3D BROADCAST CAM',
              active: _show3DCutIn,
              color: _amber,
              icon: Icons.view_in_ar_rounded,
              onTap: () => setState(() {
                _active3DScene = s.isFullTime
                    ? GtexCinema3DScene.worldGala
                    : s.phase == 'pre_match'
                        ? GtexCinema3DScene.facilityUpgrade
                        : GtexCinema3DScene.signingWalkout;
                _show3DCutIn = !_show3DCutIn;
              }),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // Strategic 3D Broadcast Cut-In Stage (or Auto Full-Time 3D MOTM Trophy Stage)
        if (_show3DCutIn || s.isFullTime) ...<Widget>[
          GtexCinema3DStage(
            scene: s.isFullTime ? GtexCinema3DScene.worldGala : _active3DScene,
            title: s.isFullTime
                ? '${s.homeScore >= s.awayScore ? s.homeName : s.awayName} · MOTM HONORS'
                : '${s.homeName} VS ${s.awayName}',
            subtitle: s.isFullTime
                ? 'Full-Time 3D Man of the Match & Post-Match Gala'
                : 'Live 3D Matchday Broadcast Cut-In · Drag 360°',
            badgeText: s.isFullTime ? 'FULL-TIME 3D GALA' : 'LIVE 3D CUT-IN',
            clubName: s.homeName,
            compact: true,
          ),
          const SizedBox(height: 12),
        ],

        // 60fps 2D / 2.5D Spatial Match Engine Canvas
        _buildPitchEngineCard(s),

        if (s.isFullTime && _settlement != null) ...<Widget>[
          const SizedBox(height: 16),
          _settlementCard(_settlement!),
        ],
        const SizedBox(height: 16),
        const Text('TIMELINE', style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1)),
        const SizedBox(height: 8),
        ...s.events.reversed.take(20).map(_eventRow),
      ],
    );
  }

  Widget _togglePill({
    required String label,
    required bool active,
    required Color color,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: active ? color.withValues(alpha: 0.16) : _panel,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: active ? color.withValues(alpha: 0.7) : _border),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, size: 13, color: active ? color : _textMuted),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(
                color: active ? color : _textSecondary,
                fontFamily: _condensed,
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPitchEngineCard(LiveMatchState s) {
    return Container(
      height: 255,
      decoration: BoxDecoration(
        color: const Color(0xFF06150C),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _green.withValues(alpha: 0.35)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.7),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: <Widget>[
          // 360° Stadium LED Ad Perimeter Board in 2.5D mode
          if (_is25DCamera)
            Positioned(
              top: 6,
              left: 16,
              right: 16,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 3, horizontal: 10),
                decoration: BoxDecoration(
                  color: const Color(0xE6050D09),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: _green.withValues(alpha: 0.4)),
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: <Widget>[
                    Text(
                      'GTEX SOVEREIGN ARENA',
                      style: TextStyle(color: _green, fontSize: 8, fontWeight: FontWeight.w900, letterSpacing: 1.5),
                    ),
                    Text(
                      '★ \$TALENT LIQUIDITY ★',
                      style: TextStyle(color: _amber, fontSize: 8, fontWeight: FontWeight.w900, letterSpacing: 1.5),
                    ),
                    Text(
                      '60FPS SPATIAL ENGINE',
                      style: TextStyle(color: _cyan, fontSize: 8, fontWeight: FontWeight.w900, letterSpacing: 1.5),
                    ),
                  ],
                ),
              ),
            ),

          // Animated 22-Player 2D / 2.5D Pitch Canvas
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _pitchAnim,
              builder: (BuildContext context, _) {
                final Widget canvas = CustomPaint(
                  painter: _GtexMatchEngine2DPainter(
                    phase: _pitchAnim.value,
                    minute: s.minute,
                    showVoronoi: _showVoronoi,
                    showHeatmap: _showHeatmap,
                    showLanes: _showLanes,
                  ),
                );
                if (!_is25DCamera) return canvas;
                return Transform(
                  alignment: Alignment.center,
                  transform: Matrix4.identity()
                    ..setEntry(3, 2, 0.0009)
                    ..rotateX(-0.36)
                    ..scale(0.95, 0.95),
                  child: canvas,
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _teamSide(String name, String formation, bool isYou, {bool alignEnd = false}) {
    return Column(
      crossAxisAlignment: alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Text(name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: _text, fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 2),
        Text(isYou ? '$formation · you' : formation,
            style: TextStyle(color: isYou ? _green : _textMuted, fontSize: 11)),
      ],
    );
  }

  Widget _eventRow(Map<String, dynamic> e) {
    final String type = (e['type'] ?? '').toString();
    final int minute = (e['minute'] as num?)?.toInt() ?? 0;
    late final IconData icon;
    late final Color color;
    late final String label;
    switch (type) {
      case 'goal':
        icon = Icons.sports_soccer;
        color = _green;
        label = 'Goal — ${e['team'] ?? ''} (${e['score'] ?? ''})';
        break;
      case 'tactical_change':
        icon = Icons.dashboard_customize_rounded;
        color = _amber;
        label = 'Tactical change — ${e['side'] ?? ''} → ${e['formation'] ?? ''}';
        break;
      case 'half_time':
        icon = Icons.timer_outlined;
        color = _textSecondary;
        label = 'Half time';
        break;
      case 'second_half':
        icon = Icons.play_arrow_rounded;
        color = _textSecondary;
        label = 'Second half';
        break;
      case 'full_time':
        icon = Icons.flag_rounded;
        color = _textSecondary;
        label = 'Full time';
        break;
      default:
        icon = Icons.circle;
        color = _textMuted;
        label = type;
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: <Widget>[
          SizedBox(width: 32, child: Text("$minute'", style: const TextStyle(color: _textMuted, fontSize: 12))),
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Expanded(child: Text(label, style: const TextStyle(color: _textSecondary, fontSize: 13))),
        ],
      ),
    );
  }

  Widget _halftimeOverlay(LiveMatchState s) {
    final int remaining = s.halftimeSecondsRemaining ?? 0;
    final bool waiting = _halftimeDoneSent || s.halftimeReady.contains(widget.side);
    return Positioned.fill(
      child: ColoredBox(
        color: const Color(0xCC0E1217),
        child: Center(
          child: Container(
            margin: const EdgeInsets.all(28),
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              color: _panel,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: _border),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                const Text('HALF TIME',
                    style: TextStyle(
                        color: _amber,
                        fontFamily: _condensed,
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1)),
                const SizedBox(height: 6),
                Text('Back to the match in ${remaining}s',
                    style: const TextStyle(color: _textSecondary, fontSize: 13)),
                const SizedBox(height: 8),
                Text('${s.homeScore} - ${s.awayScore}',
                    style: const TextStyle(
                        color: _text, fontFamily: _condensed, fontSize: 30, fontWeight: FontWeight.w900)),
                const SizedBox(height: 16),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    OutlinedButton.icon(
                      onPressed: _openTactics,
                      icon: const Icon(Icons.dashboard_customize_rounded, size: 18),
                      label: const Text('Adjust tactics'),
                    ),
                    const SizedBox(width: 10),
                    FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: _green, foregroundColor: const Color(0xFF06140C)),
                      onPressed: waiting ? null : _halftimeDone,
                      child: Text(waiting ? 'Waiting for opponent…' : 'Done'),
                    ),
                  ],
                ),
                if (s.halftimeReady.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 10),
                  Text('${s.halftimeReady.length}/2 ready',
                      style: const TextStyle(color: _textMuted, fontSize: 12)),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _settlementCard(Map<String, dynamic> settlement) {
    final String result = (settlement['result'] ?? '').toString();
    final int remaining = (settlement['free_matches_remaining'] as num?)?.toInt() ?? 0;
    final bool charged = settlement['charge_required_now'] == true;
    final Color color = result == 'win'
        ? _green
        : result == 'loss'
            ? const Color(0xFFE3563C)
            : _amber;
    final String headline = result == 'win'
        ? 'You won'
        : result == 'loss'
            ? 'You lost'
            : 'Draw';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(headline,
              style: TextStyle(
                  color: color, fontFamily: _condensed, fontSize: 20, fontWeight: FontWeight.w900, letterSpacing: 1)),
          const SizedBox(height: 6),
          Text(
            charged
                ? 'Fan Coin entry fee applied. $remaining free matches left.'
                : 'Free match. $remaining free matches left.',
            style: const TextStyle(color: _textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }

  String _phaseLabel(String phase) {
    switch (phase) {
      case 'first_half':
        return 'First half';
      case 'second_half':
        return 'Second half';
      case 'half_time':
        return 'Half time';
      case 'pre_match':
        return 'Kick off soon';
      default:
        return phase;
    }
  }
}

class _GtexMatchEngine2DPainter extends CustomPainter {
  _GtexMatchEngine2DPainter({
    required this.phase,
    required this.minute,
    required this.showVoronoi,
    required this.showHeatmap,
    required this.showLanes,
  });

  final double phase;
  final int minute;
  final bool showVoronoi;
  final bool showHeatmap;
  final bool showLanes;

  static const List<Offset> _base433 = <Offset>[
    Offset(0.08, 0.50),
    Offset(0.24, 0.82),
    Offset(0.20, 0.62),
    Offset(0.20, 0.38),
    Offset(0.24, 0.18),
    Offset(0.38, 0.50),
    Offset(0.47, 0.68),
    Offset(0.48, 0.32),
    Offset(0.68, 0.80),
    Offset(0.68, 0.20),
    Offset(0.75, 0.50),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final double t = phase * math.pi * 2;
    final Rect full = Offset.zero & size;

    // Turf Gradient
    canvas.drawRect(
      full,
      Paint()
        ..shader = const RadialGradient(
          radius: 0.85,
          colors: <Color>[Color(0xFF164226), Color(0xFF0A2112)],
        ).createShader(full),
    );

    // Mowed Grass Stripes
    final double stripeW = size.width / 10;
    for (int i = 0; i < 10; i++) {
      if (i.isEven) {
        canvas.drawRect(
          Rect.fromLTWH(i * stripeW, 0, stripeW, size.height),
          Paint()..color = const Color(0x181F5B35),
        );
      }
    }

    // Voronoi Territory Shader
    if (showVoronoi) {
      final double splitX = size.width * (0.54 + math.sin(t * 2) * 0.05);
      canvas.drawRect(
        Rect.fromLTWH(16, 14, splitX - 16, size.height - 28),
        Paint()..color = _green.withValues(alpha: 0.10),
      );
      canvas.drawRect(
        Rect.fromLTWH(splitX, 14, size.width - splitX - 16, size.height - 28),
        Paint()..color = _amber.withValues(alpha: 0.09),
      );
      canvas.drawLine(
        Offset(splitX, 14),
        Offset(splitX, size.height - 14),
        Paint()
          ..color = _cyan.withValues(alpha: 0.55)
          ..strokeWidth = 1.2,
      );
    }

    // Pitch Lines
    final Paint linePaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.45)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.4;
    final Rect pitchRect = Rect.fromLTWH(16, 14, size.width - 32, size.height - 28);
    canvas.drawRect(pitchRect, linePaint);
    canvas.drawLine(Offset(size.width / 2, 14), Offset(size.width / 2, size.height - 14), linePaint);
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 28, linePaint);

    // Compute 11 Home & 11 Away Positions
    final List<Offset> homePts = <Offset>[];
    final List<Offset> awayPts = <Offset>[];
    for (int i = 0; i < _base433.length; i++) {
      final Offset b = _base433[i];
      final double hx = (b.dx + (i == 0 ? 0 : math.sin(t * 2 + i) * 0.025)) * size.width;
      final double hy = (b.dy + math.cos(t * 2 + i * 1.3) * 0.025) * size.height;
      homePts.add(Offset(hx, hy));

      final double ax = ((1 - b.dx) - (i == 0 ? 0 : math.cos(t * 2 + i) * 0.025)) * size.width;
      final double ay = ((1 - b.dy) + math.sin(t * 2 + i * 1.1) * 0.025) * size.height;
      awayPts.add(Offset(ax, ay));
    }

    // Heatmap
    if (showHeatmap) {
      for (final Offset p in homePts) {
        canvas.drawCircle(
          p,
          28,
          Paint()
            ..color = _green.withValues(alpha: 0.16)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
        );
      }
      for (final Offset p in awayPts) {
        canvas.drawCircle(
          p,
          28,
          Paint()
            ..color = _amber.withValues(alpha: 0.14)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
        );
      }
    }

    final int carrierIdx = ((phase * 16).floor() % 5) + 6;
    final int targetIdx = ((carrierIdx + 1) % 5) + 6;
    final Offset carrier = homePts[carrierIdx];
    final Offset receiver = homePts[targetIdx];

    // Pass Arcs & Threat Cone
    if (showLanes) {
      final Path arc = Path()
        ..moveTo(carrier.dx, carrier.dy)
        ..quadraticBezierTo(
          (carrier.dx + receiver.dx) / 2,
          (carrier.dy + receiver.dy) / 2 - 18,
          receiver.dx,
          receiver.dy,
        );
      canvas.drawPath(
        arc,
        Paint()
          ..color = _green.withValues(alpha: 0.85)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0,
      );
    }

    // Draw Players
    for (int i = 0; i < homePts.length; i++) {
      final Offset p = homePts[i];
      canvas.drawCircle(p, 7.5, Paint()..color = const Color(0xFF07110B));
      canvas.drawCircle(p, 6, Paint()..color = _green);
      if (i == carrierIdx) {
        canvas.drawCircle(
          p,
          12,
          Paint()
            ..color = _green.withValues(alpha: 0.65)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.6,
        );
      }
    }
    for (int i = 0; i < awayPts.length; i++) {
      final Offset p = awayPts[i];
      canvas.drawCircle(p, 7.5, Paint()..color = const Color(0xFF140E04));
      canvas.drawCircle(p, 6, Paint()..color = _amber);
    }

    // Ball + Comet Trail
    final double frac = (phase * 16) % 1.0;
    final Offset ballPos = Offset(
      carrier.dx + (receiver.dx - carrier.dx) * frac,
      carrier.dy + (receiver.dy - carrier.dy) * frac,
    );
    canvas.drawLine(
      carrier,
      ballPos,
      Paint()
        ..color = _cyan.withValues(alpha: 0.45)
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round,
    );
    canvas.drawCircle(ballPos, 4.5, Paint()..color = Colors.white);
    canvas.drawCircle(ballPos, 2.0, Paint()..color = _green);
  }

  @override
  bool shouldRepaint(covariant _GtexMatchEngine2DPainter oldDelegate) => true;
}
