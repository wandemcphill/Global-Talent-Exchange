import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import 'gtex_match_visual_tokens.dart';

/// Command-driven 2.5D broadcast pitch.
///
/// This is the default watch surface: GTEX emits football intentions, the
/// viewer plays them as a broadcast camera match. It is not per-frame
/// transform puppet playback and it is not Unity.
class Gtex25dBroadcastPitch extends StatefulWidget {
  const Gtex25dBroadcastPitch({super.key, this.autoplay = true});

  final bool autoplay;

  @override
  State<Gtex25dBroadcastPitch> createState() => _Gtex25dBroadcastPitchState();
}

class _Gtex25dBroadcastPitchState extends State<Gtex25dBroadcastPitch>
    with SingleTickerProviderStateMixin {
  late final Ticker _ticker;
  late _BroadcastWorld _world;
  Duration _last = Duration.zero;
  bool _paused = false;
  double _speed = 1;

  @override
  void initState() {
    super.initState();
    _world = _BroadcastWorld();
    _ticker = createTicker(_onTick);
    if (widget.autoplay) {
      _ticker.start();
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  void _onTick(Duration elapsed) {
    final Duration previous = _last == Duration.zero ? elapsed : _last;
    _last = elapsed;
    final double dt = (elapsed - previous).inMicroseconds / 1e6;
    if (!_paused) {
      _world.step(dt.clamp(0.0, 0.033) * _speed);
    }
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 16 / 9,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xFF071018),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: GtexMatchVisualTokens.borderStrong),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Stack(
            children: [
              Positioned.fill(
                child: CustomPaint(painter: _BroadcastPainter(_world)),
              ),
              Positioned(left: 12, top: 12, child: _Scorebug(world: _world)),
              Positioned(
                left: 12,
                right: 12,
                bottom: 12,
                child: _EventBar(
                  world: _world,
                  paused: _paused,
                  speed: _speed,
                  onPause: () {
                    setState(() => _paused = !_paused);
                    if (_paused) {
                      _ticker.stop();
                    } else {
                      _last = Duration.zero;
                      _ticker.start();
                    }
                  },
                  onReplay: () => setState(_world.replayAttack),
                  onSpeed: () {
                    setState(() {
                      _speed = _speed == 1
                          ? 1.5
                          : _speed == 1.5
                          ? 2
                          : _speed == 2
                          ? 0.5
                          : 1;
                    });
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class Gtex25dBroadcastDemoScreen extends StatelessWidget {
  const Gtex25dBroadcastDemoScreen({super.key, this.onExit});

  final VoidCallback? onExit;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF050709),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  if (onExit != null)
                    IconButton(
                      onPressed: onExit,
                      icon: const Icon(
                        Icons.arrow_back,
                        color: Color(0xFFF4F7F8),
                      ),
                    ),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'GTEX MATCHDAY · 2.5D BROADCAST',
                          style: TextStyle(
                            color: Color(0xFFB9FF3D),
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.4,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Command-driven watch surface. Unity stays optional.',
                          style: TextStyle(color: Color(0xFF93A0AA), fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Expanded(child: Gtex25dBroadcastPitch()),
            ],
          ),
        ),
      ),
    );
  }
}

class _Scorebug extends StatelessWidget {
  const _Scorebug({required this.world});
  final _BroadcastWorld world;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xCC050709),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: const Color(0x6636E38A)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'LAGOS UTD',
            style: TextStyle(
              color: Color(0xFF36E38A),
              fontWeight: FontWeight.w800,
              fontSize: 11,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '${world.homeGoals} – ${world.awayGoals}',
            style: const TextStyle(
              color: Color(0xFFF4F7F8),
              fontWeight: FontWeight.w900,
              fontSize: 16,
            ),
          ),
          const SizedBox(width: 8),
          const Text(
            'ACCRA CITY',
            style: TextStyle(
              color: Color(0xFFFFC857),
              fontWeight: FontWeight.w800,
              fontSize: 11,
            ),
          ),
          const SizedBox(width: 12),
          Text(
            world.clockLabel,
            style: const TextStyle(
              color: Color(0xFFB9FF3D),
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _EventBar extends StatelessWidget {
  const _EventBar({
    required this.world,
    required this.paused,
    required this.speed,
    required this.onPause,
    required this.onReplay,
    required this.onSpeed,
  });

  final _BroadcastWorld world;
  final bool paused;
  final double speed;
  final VoidCallback onPause;
  final VoidCallback onReplay;
  final VoidCallback onSpeed;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xE6050709),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  world.eventLabel,
                  style: const TextStyle(
                    color: Color(0xFFF4F7F8),
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Next  ${world.nextLabel}',
                  style: const TextStyle(
                    color: Color(0xFFB9FF3D),
                    fontFamily: 'JetBrains Mono',
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          TextButton(onPressed: onPause, child: Text(paused ? 'Play' : 'Pause')),
          TextButton(onPressed: onReplay, child: const Text('Replay')),
          TextButton(onPressed: onSpeed, child: Text('${speed}x')),
        ],
      ),
    );
  }
}

class _BroadcastCommand {
  const _BroadcastCommand({
    required this.t,
    required this.type,
    required this.text,
    required this.next,
    this.from,
    this.to,
    this.who,
    this.x,
    this.y,
    this.gx,
    this.gy,
    this.team,
  });

  final double t;
  final String type;
  final String text;
  final String next;
  final String? from;
  final String? to;
  final String? who;
  final double? x;
  final double? y;
  final double? gx;
  final double? gy;
  final String? team;
}

class _Actor {
  _Actor({
    required this.id,
    required this.number,
    required this.home,
    required this.homeX,
    required this.homeY,
  }) : px = homeX,
       py = homeY,
       tx = homeX,
       ty = homeY;

  final String id;
  final int number;
  final bool home;
  final double homeX;
  final double homeY;
  double px;
  double py;
  double tx;
  double ty;
}

class _BroadcastWorld {
  _BroadcastWorld() {
    players = <_Actor>[
      _Actor(id: 'H1', number: 1, home: true, homeX: 0.06, homeY: 0.50),
      _Actor(id: 'H2', number: 2, home: true, homeX: 0.18, homeY: 0.18),
      _Actor(id: 'H3', number: 5, home: true, homeX: 0.16, homeY: 0.38),
      _Actor(id: 'H4', number: 4, home: true, homeX: 0.16, homeY: 0.62),
      _Actor(id: 'H5', number: 3, home: true, homeX: 0.18, homeY: 0.82),
      _Actor(id: 'H6', number: 6, home: true, homeX: 0.32, homeY: 0.32),
      _Actor(id: 'H7', number: 8, home: true, homeX: 0.30, homeY: 0.50),
      _Actor(id: 'H8', number: 10, home: true, homeX: 0.34, homeY: 0.70),
      _Actor(id: 'H9', number: 7, home: true, homeX: 0.48, homeY: 0.22),
      _Actor(id: 'H10', number: 9, home: true, homeX: 0.52, homeY: 0.50),
      _Actor(id: 'H11', number: 11, home: true, homeX: 0.48, homeY: 0.78),
      _Actor(id: 'A1', number: 1, home: false, homeX: 0.94, homeY: 0.50),
      _Actor(id: 'A2', number: 2, home: false, homeX: 0.82, homeY: 0.82),
      _Actor(id: 'A3', number: 5, home: false, homeX: 0.84, homeY: 0.62),
      _Actor(id: 'A4', number: 4, home: false, homeX: 0.84, homeY: 0.38),
      _Actor(id: 'A5', number: 3, home: false, homeX: 0.82, homeY: 0.18),
      _Actor(id: 'A6', number: 6, home: false, homeX: 0.68, homeY: 0.68),
      _Actor(id: 'A7', number: 8, home: false, homeX: 0.70, homeY: 0.50),
      _Actor(id: 'A8', number: 10, home: false, homeX: 0.66, homeY: 0.30),
      _Actor(id: 'A9', number: 7, home: false, homeX: 0.52, homeY: 0.78),
      _Actor(id: 'A10', number: 9, home: false, homeX: 0.48, homeY: 0.50),
      _Actor(id: 'A11', number: 11, home: false, homeX: 0.52, homeY: 0.22),
    ];
    byId = {for (final _Actor p in players) p.id: p};
  }

  late final List<_Actor> players;
  late final Map<String, _Actor> byId;
  double ballX = 0.5;
  double ballY = 0.5;
  double ballZ = 0;
  double ballSx = 0.5;
  double ballSy = 0.5;
  double ballSz = 0;
  double ballTx = 0.5;
  double ballTy = 0.5;
  double ballTz = 0.02;
  double flight = 0;
  double flightDur = 0.6;
  double peak = 0.25;
  String? holder = 'H10';
  String? catchId;
  double camX = 0.5;
  double camY = 0.5;
  double shake = 0;
  double matchT = 0;
  int cmdIndex = 0;
  int homeGoals = 0;
  int awayGoals = 0;
  String eventLabel = 'Kickoff · Lagos United';
  String nextLabel = 'PASS  #9 → #10';

  static const List<_BroadcastCommand> script = <_BroadcastCommand>[
    _BroadcastCommand(
      t: 0.4,
      type: 'KICKOFF',
      who: 'H10',
      text: 'Kickoff · Traore',
      next: 'PASS  #9 → #10',
    ),
    _BroadcastCommand(
      t: 1.6,
      type: 'PASS',
      from: 'H10',
      to: 'H8',
      text: 'Pass · Traore to Adebayo',
      next: 'CARRY  #10',
    ),
    _BroadcastCommand(
      t: 3.2,
      type: 'CARRY',
      who: 'H8',
      x: 0.42,
      y: 0.62,
      text: 'Adebayo carries into the half',
      next: 'PASS  #10 → #7',
    ),
    _BroadcastCommand(
      t: 5.0,
      type: 'PASS',
      from: 'H8',
      to: 'H9',
      text: 'Switch · Adebayo to Keita',
      next: 'THROUGH  #7 → #9',
    ),
    _BroadcastCommand(
      t: 6.4,
      type: 'SUPPORT',
      who: 'H10',
      x: 0.62,
      y: 0.42,
      text: 'Traore makes the channel run',
      next: 'THROUGH  #7 → #9',
    ),
    _BroadcastCommand(
      t: 7.6,
      type: 'THROUGH',
      from: 'H9',
      to: 'H10',
      x: 0.78,
      y: 0.44,
      text: 'Through ball · Keita to Traore',
      next: 'SHOT  #9',
    ),
    _BroadcastCommand(
      t: 9.2,
      type: 'SHOT',
      from: 'H10',
      gx: 0.97,
      gy: 0.48,
      text: 'Shot · Traore, near post',
      next: 'SAVE  #1',
    ),
    _BroadcastCommand(
      t: 10.15,
      type: 'SAVE',
      who: 'A1',
      text: 'Saved · Mensah',
      next: 'CLEARANCE',
    ),
    _BroadcastCommand(
      t: 19.6,
      type: 'PASS',
      from: 'H1',
      to: 'H7',
      text: 'Restart · Lagos United',
      next: 'WIDE  #11',
    ),
    _BroadcastCommand(
      t: 21.1,
      type: 'PASS',
      from: 'H7',
      to: 'H11',
      text: 'Wide · Mendes to Yusuf',
      next: 'CARRY  #11',
    ),
    _BroadcastCommand(
      t: 22.4,
      type: 'CARRY',
      who: 'H11',
      x: 0.72,
      y: 0.74,
      text: 'Yusuf beats the full-back',
      next: 'CUT-BACK',
    ),
    _BroadcastCommand(
      t: 23.8,
      type: 'PASS',
      from: 'H11',
      to: 'H10',
      text: 'Cut-back · Yusuf to Traore',
      next: 'SHOT  #9',
    ),
    _BroadcastCommand(
      t: 24.9,
      type: 'SHOT',
      from: 'H10',
      gx: 0.97,
      gy: 0.50,
      text: 'Shot · Traore, open net',
      next: 'GOAL',
    ),
    _BroadcastCommand(
      t: 25.7,
      type: 'GOAL',
      team: 'H',
      text: "GOAL · Traore 26'",
      next: 'RESET KICKOFF',
    ),
    _BroadcastCommand(
      t: 28.4,
      type: 'RESET',
      who: 'A10',
      text: 'Kickoff · Accra City',
      next: 'LOOP',
    ),
  ];

  String get clockLabel {
    final int minute = math.min(89, (matchT * 3.1).floor());
    final int sec = (((matchT * 3.1) - minute) * 60).floor() % 60;
    return '${minute.toString().padLeft(2, '0')}:${sec.toString().padLeft(2, '0')}';
  }

  void replayAttack() {
    matchT = 21.0;
    cmdIndex = script.indexWhere((_BroadcastCommand c) => c.t >= 21);
    if (cmdIndex < 0) {
      cmdIndex = 0;
    }
    eventLabel = 'Replay · Lagos attack';
  }

  void step(double dt) {
    matchT += dt;
    if (matchT > 31) {
      matchT = 0;
      cmdIndex = 0;
      homeGoals = 0;
      awayGoals = 0;
      for (final _Actor p in players) {
        p.px = p.homeX;
        p.py = p.homeY;
        p.tx = p.homeX;
        p.ty = p.homeY;
      }
    }
    while (cmdIndex < script.length && matchT >= script[cmdIndex].t) {
      _apply(script[cmdIndex]);
      cmdIndex += 1;
    }
    for (final _Actor p in players) {
      p.px = _approach(p.px, p.tx, dt, 2.4);
      p.py = _approach(p.py, p.ty, dt, 2.4);
      if (holder == p.id) {
        ballX = p.px + (p.home ? 0.012 : -0.012);
        ballY = p.py;
        ballZ = 0.03 + math.sin(matchT * 10) * 0.008;
      }
    }
    if (holder == null && flight > 0) {
      flight += dt;
      final double u = (flight / flightDur).clamp(0.0, 1.0);
      final double arc = math.sin(u * math.pi) * peak;
      ballX = _lerp(ballSx, ballTx, u);
      ballY = _lerp(ballSy, ballTy, u);
      ballZ = _lerp(ballSz, ballTz, u) + arc;
      if (u >= 1) {
        flight = 0;
        final String? catchTo = catchId;
        if (catchTo != null) {
          _hold(catchTo);
        }
      }
    }
    camX = _approach(camX, ballX, dt, 1.6);
    camY = _approach(camY, ballY, dt, 1.6);
    shake = math.max(0, shake - dt * 2.4);
  }

  void _apply(_BroadcastCommand cmd) {
    eventLabel = cmd.text;
    nextLabel = cmd.next;
    shake = cmd.type == 'SHOT' || cmd.type == 'GOAL' ? 1 : math.max(shake, 0.15);
    if (cmd.type == 'KICKOFF' || cmd.type == 'RESET') {
      if (cmd.type == 'RESET') {
        for (final _Actor p in players) {
          p.tx = p.homeX;
          p.ty = p.homeY;
        }
      }
      _hold(cmd.who!);
    } else if (cmd.type == 'PASS' ||
        cmd.type == 'THROUGH' ||
        cmd.type == 'CROSS') {
      final _Actor dest = byId[cmd.to]!;
      dest.tx = cmd.x ?? dest.homeX;
      dest.ty = cmd.y ?? dest.homeY;
      _fly(
        dest.tx + (dest.home ? 0.01 : -0.01),
        dest.ty,
        cmd.type == 'CROSS' ? 0.95 : 0.62,
        cmd.type == 'CROSS' ? 0.55 : 0.28,
      );
      catchId = cmd.to;
    } else if (cmd.type == 'CARRY' || cmd.type == 'SUPPORT') {
      final _Actor p = byId[cmd.who]!;
      p.tx = cmd.x!;
      p.ty = cmd.y!;
      if (cmd.type == 'CARRY') {
        _hold(cmd.who!);
      }
    } else if (cmd.type == 'SHOT') {
      _fly(cmd.gx!, cmd.gy!, 0.72, 0.32);
      catchId = null;
    } else if (cmd.type == 'SAVE') {
      final _Actor gk = byId[cmd.who]!;
      gk.tx = ballTx;
      gk.ty = ballTy;
      _fly(gk.px, gk.py, 0.28, 0.12);
      catchId = cmd.who;
    } else if (cmd.type == 'GOAL') {
      if (cmd.team == 'H') {
        homeGoals += 1;
      } else {
        awayGoals += 1;
      }
    }
  }

  void _hold(String id) {
    final _Actor p = byId[id]!;
    holder = id;
    ballX = p.px + (p.home ? 0.012 : -0.012);
    ballY = p.py;
    ballZ = 0.02;
    flight = 0;
  }

  void _fly(double toX, double toY, double dur, double peakH) {
    holder = null;
    ballSx = ballX;
    ballSy = ballY;
    ballSz = ballZ;
    ballTx = toX;
    ballTy = toY;
    ballTz = 0.02;
    flight = 0.0001;
    flightDur = dur;
    peak = peakH;
  }

  static double _lerp(double a, double b, double t) => a + (b - a) * t;

  static double _approach(double v, double t, double dt, double rate) {
    final double k = 1 - math.exp(-rate * dt);
    return _lerp(v, t, k);
  }
}

class _BroadcastPainter extends CustomPainter {
  _BroadcastPainter(this.world);
  final _BroadcastWorld world;

  Offset _project(Size size, double x, double y, double z) {
    final double cx = size.width * 0.5 + (0.5 - world.camX) * size.width * 0.18;
    final double cy =
        size.height * 0.58 + (0.5 - world.camY) * size.height * 0.10;
    final double persp = 0.42 + y * 0.72;
    final double shake = world.shake * 4;
    return Offset(
      cx + (x - 0.5) * size.width * 0.86 * persp + shake,
      cy - (y - 0.18) * size.height * 0.46 - z * size.height * 0.12,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    final Paint grass = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: <Color>[Color(0xFF0B1A24), Color(0xFF0A1410), Color(0xFF05080A)],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, grass);

    final Path pitch = Path()
      ..moveTo(_project(size, 0, 0, 0).dx, _project(size, 0, 0, 0).dy)
      ..lineTo(_project(size, 1, 0, 0).dx, _project(size, 1, 0, 0).dy)
      ..lineTo(_project(size, 1, 1, 0).dx, _project(size, 1, 1, 0).dy)
      ..lineTo(_project(size, 0, 1, 0).dx, _project(size, 0, 1, 0).dy)
      ..close();
    canvas.drawPath(pitch, Paint()..color = const Color(0xFF14532D));

    for (int i = 0; i < 10; i++) {
      final Path band = Path()
        ..moveTo(
          _project(size, i / 10, 0, 0).dx,
          _project(size, i / 10, 0, 0).dy,
        )
        ..lineTo(
          _project(size, (i + 1) / 10, 0, 0).dx,
          _project(size, (i + 1) / 10, 0, 0).dy,
        )
        ..lineTo(
          _project(size, (i + 1) / 10, 1, 0).dx,
          _project(size, (i + 1) / 10, 1, 0).dy,
        )
        ..lineTo(
          _project(size, i / 10, 1, 0).dx,
          _project(size, i / 10, 1, 0).dy,
        )
        ..close();
      canvas.drawPath(
        band,
        Paint()
          ..color = i.isEven
              ? const Color(0x14FFFFFF)
              : const Color(0x1A000000),
      );
    }

    final Paint line = Paint()
      ..color = const Color(0x8CF4F7F8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6;
    canvas.drawPath(pitch, line);
    canvas.drawLine(
      _project(size, 0.5, 0, 0),
      _project(size, 0.5, 1, 0),
      line,
    );

    final List<_Actor> ordered = List<_Actor>.from(world.players)
      ..sort((_Actor a, _Actor b) => a.py.compareTo(b.py));
    for (final _Actor p in ordered) {
      _drawPlayer(canvas, size, p);
    }
    _drawBall(canvas, size);
  }

  void _drawPlayer(Canvas canvas, Size size, _Actor p) {
    final Offset pos = _project(size, p.px, p.py, 0);
    final double s = 9 + p.py * 8;
    canvas.drawOval(
      Rect.fromCenter(
        center: pos.translate(0, 5),
        width: s * 1.1,
        height: s * 0.42,
      ),
      Paint()..color = const Color(0x59000000),
    );
    final Color kit = p.home ? const Color(0xFF1EC97A) : const Color(0xFFE7B23A);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(
          center: pos.translate(0, -s * 0.55),
          width: s * 0.7,
          height: s * 1.15,
        ),
        const Radius.circular(4),
      ),
      Paint()..color = kit,
    );
    canvas.drawCircle(
      pos.translate(0, -s * 1.22),
      s * 0.22,
      Paint()..color = const Color(0xFFF2D2B0),
    );
    final TextPainter tp = TextPainter(
      text: TextSpan(
        text: '${p.number}',
        style: TextStyle(
          color: const Color(0xFF071018),
          fontWeight: FontWeight.w800,
          fontSize: math.max(8, s * 0.38),
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, pos.translate(-tp.width / 2, -s * 0.72));
    if (world.holder == p.id) {
      canvas.drawCircle(
        pos.translate(0, -s * 0.5),
        s * 0.7,
        Paint()
          ..color = const Color(0xD9FFFFFF)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.6,
      );
    }
  }

  void _drawBall(Canvas canvas, Size size) {
    final Offset shadow = _project(size, world.ballX, world.ballY, 0);
    final Offset pos = _project(size, world.ballX, world.ballY, world.ballZ);
    canvas.drawOval(
      Rect.fromCenter(
        center: shadow.translate(0, 4),
        width: 12 + world.ballZ * 18,
        height: 6,
      ),
      Paint()..color = const Color(0x66000000),
    );
    canvas.drawCircle(pos, 5.2, Paint()..color = const Color(0xFFF4F7F8));
  }

  @override
  bool shouldRepaint(covariant _BroadcastPainter oldDelegate) => true;
}
