import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

enum GtexCinema3DScene {
  signingWalkout,
  negotiationTable,
  luxuryTurntable,
  worldGala,
  buildASon,
  managerArrival,
  stadiumSponsor,
  boardroomClash,
}

enum GtexCinema3DMode {
  motion3d,
  fmDiorama,
}

/// GTEX 3D Presentation & Diorama Stage (Flutter)
/// Combines FIFA/eFootball-style 60fps 3D Motion Cinema with Football Manager-style
/// 3D Diorama Stills and interactive 360-degree Matrix4 perspective rotation.
class GtexCinema3DStage extends StatefulWidget {
  const GtexCinema3DStage({
    super.key,
    required this.scene,
    required this.title,
    this.subtitle,
    this.badgeText,
    this.clubName = 'GTEX FC',
    this.subjectName = 'MARQUEE STAR',
    this.subjectRole = 'First-Team Signing',
    this.jerseyNumber = 9,
    this.overallRating = 88,
    this.potentialRating,
    this.sponsorName = 'GTEX GLOBAL AIRWAYS',
    this.quote,
    this.defaultMode = GtexCinema3DMode.motion3d,
    this.compact = false,
  });

  final GtexCinema3DScene scene;
  final String title;
  final String? subtitle;
  final String? badgeText;
  final String clubName;
  final String subjectName;
  final String subjectRole;
  final int jerseyNumber;
  final int overallRating;
  final int? potentialRating;
  final String sponsorName;
  final String? quote;
  final GtexCinema3DMode defaultMode;
  final bool compact;

  @override
  State<GtexCinema3DStage> createState() => _GtexCinema3DStageState();
}

class _GtexCinema3DStageState extends State<GtexCinema3DStage>
    with SingleTickerProviderStateMixin {
  late GtexCinema3DMode _mode;
  late final AnimationController _controller;
  double _rotY = 0.0;
  double _rotX = 0.08;
  bool _dragging = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.defaultMode;
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 12),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool isGala = widget.scene == GtexCinema3DScene.worldGala;
    final Color accentColor = isGala ? GtexColors.gold : GtexColors.pitch;

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF050811),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: accentColor.withValues(alpha: 0.55),
          width: 1.5,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          // Top Broadcast Switcher Bar
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: GtexSpacing.sm,
              vertical: 8,
            ),
            color: const Color(0xFF0B1120),
            child: Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 6,
              children: <Widget>[
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Icon(
                      _mode == GtexCinema3DMode.motion3d
                          ? Icons.movie_filter_rounded
                          : Icons.camera_alt_rounded,
                      size: 14,
                      color: accentColor,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      _mode == GtexCinema3DMode.motion3d
                          ? '3D MOTION CINEMA (FIFA/eFOOTBALL)'
                          : '3D STATIC DIORAMA (FM STYLE)',
                      style: TextStyle(
                        color: accentColor,
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                    ),
                    if (widget.badgeText != null) ...<Widget>[
                      const SizedBox(width: 8),
                      GtexStatusChip(
                        label: widget.badgeText!,
                        color: GtexColors.gold,
                        compact: true,
                      ),
                    ],
                  ],
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    InkWell(
                      onTap: () => setState(() => _mode = GtexCinema3DMode.motion3d),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _mode == GtexCinema3DMode.motion3d
                              ? GtexColors.pitch.withValues(alpha: 0.2)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '3D Motion',
                          style: TextStyle(
                            color: _mode == GtexCinema3DMode.motion3d
                                ? GtexColors.pitch
                                : GtexColors.textMuted,
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 4),
                    InkWell(
                      onTap: () => setState(() {
                        _mode = GtexCinema3DMode.fmDiorama;
                        _rotY = -0.24;
                        _rotX = 0.08;
                      }),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _mode == GtexCinema3DMode.fmDiorama
                              ? GtexColors.cyan.withValues(alpha: 0.2)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'FM 3D Still',
                          style: TextStyle(
                            color: _mode == GtexCinema3DMode.fmDiorama
                                ? GtexColors.cyan
                                : GtexColors.textMuted,
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Main 3D Stage Viewport
          GestureDetector(
            onPanStart: (_) => setState(() => _dragging = true),
            onPanUpdate: (DragUpdateDetails d) {
              setState(() {
                _rotY += d.delta.dx * 0.012;
                _rotX = (_rotX - d.delta.dy * 0.006).clamp(-0.35, 0.35);
              });
            },
            onPanEnd: (_) => setState(() => _dragging = false),
            child: SizedBox(
              height: widget.compact ? 210 : 260,
              child: AnimatedBuilder(
                animation: _controller,
                builder: (BuildContext context, _) {
                  final double t = _mode == GtexCinema3DMode.motion3d
                      ? _controller.value * 2 * math.pi
                      : 0.0;
                  final double effectiveRotY =
                      _mode == GtexCinema3DMode.motion3d && !_dragging
                          ? _rotY + math.sin(t) * 0.42
                          : _rotY;

                  final Matrix4 matrix = Matrix4.identity()
                    ..setEntry(3, 2, 0.0014)
                    ..rotateX(_rotX)
                    ..rotateY(effectiveRotY);

                  return Stack(
                    alignment: Alignment.center,
                    children: <Widget>[
                      // 1. Volumetric Floodlights, Perspective Grid & Flashbulbs
                      Positioned.fill(
                        child: CustomPaint(
                          painter: _Cinema3DBackdropPainter(
                            phase: t,
                            isGala: isGala,
                          ),
                        ),
                      ),

                      // 2. 3D Centerpiece Object with Matrix4 Perspective
                      Transform(
                        alignment: Alignment.center,
                        transform: matrix,
                        child: _build3DCenterpiece(),
                      ),

                      // 3. 360-degree Drag Hint
                      Positioned(
                        top: 8,
                        left: 10,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.55),
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.12),
                            ),
                          ),
                          child: const Text(
                            'Drag 360° 3D Camera',
                            style: TextStyle(
                              color: GtexColors.textSecondary,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),

          // Broadcast Lower-Third Banner
          Container(
            padding: const EdgeInsets.all(GtexSpacing.sm),
            decoration: BoxDecoration(
              color: const Color(0xFF0A101E),
              border: Border(
                top: BorderSide(color: GtexColors.gold.withValues(alpha: 0.3)),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  widget.title,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                    fontSize: 13,
                  ),
                ),
                if (widget.subtitle != null)
                  Text(
                    widget.subtitle!,
                    style: const TextStyle(
                      color: GtexColors.textSecondary,
                      fontSize: 11,
                    ),
                  ),
                if (widget.quote != null) ...<Widget>[
                  const SizedBox(height: 3),
                  Text(
                    '"${widget.quote!}"',
                    style: const TextStyle(
                      color: GtexColors.gold,
                      fontSize: 11,
                      fontStyle: FontStyle.italic,
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

  Widget _build3DCenterpiece() {
    switch (widget.scene) {
      case GtexCinema3DScene.worldGala:
        return Container(
          width: 145,
          height: 155,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const RadialGradient(
              colors: <Color>[
                Color(0xFFFEF08A),
                Color(0xFFF59E0B),
                Color(0xFF78350F),
              ],
            ),
            border: Border.all(color: GtexColors.gold, width: 3),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: GtexColors.gold.withValues(alpha: 0.55),
                blurRadius: 28,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              const Icon(Icons.emoji_events_rounded, size: 40, color: Color(0xFF451A03)),
              const Text(
                "GTEX D'OR",
                style: TextStyle(
                  color: Color(0xFF451A03),
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                widget.subjectName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.black,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        );

      case GtexCinema3DScene.luxuryTurntable:
        return Container(
          width: 165,
          height: 155,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF141126),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: GtexColors.gold, width: 2),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: GtexColors.gold.withValues(alpha: 0.35),
                blurRadius: 24,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              const Icon(Icons.diamond_rounded, size: 36, color: GtexColors.gold),
              const SizedBox(height: 6),
              Text(
                widget.subjectName,
                textAlign: TextAlign.center,
                maxLines: 2,
                style: const TextStyle(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                widget.subjectRole,
                style: const TextStyle(
                  color: GtexColors.pitch,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        );

      case GtexCinema3DScene.signingWalkout:
      case GtexCinema3DScene.buildASon:
      case GtexCinema3DScene.stadiumSponsor:
      case GtexCinema3DScene.negotiationTable:
      case GtexCinema3DScene.managerArrival:
      case GtexCinema3DScene.boardroomClash:
        return Container(
          width: 155,
          height: 170,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xFF064E3B),
                Color(0xFF0F172A),
                Color(0xFF78350F),
              ],
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: GtexColors.gold, width: 2),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: GtexColors.pitch.withValues(alpha: 0.35),
                blurRadius: 24,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: <Widget>[
                  Flexible(
                    child: Text(
                      widget.clubName,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexColors.textSecondary,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  Text(
                    'OVR ${widget.overallRating}',
                    style: const TextStyle(
                      color: GtexColors.gold,
                      fontSize: 9,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              Column(
                children: <Widget>[
                  Text(
                    widget.subjectName.toUpperCase(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: GtexColors.text,
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  Text(
                    '#${widget.jerseyNumber}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 34,
                      fontWeight: FontWeight.w900,
                      height: 1.05,
                    ),
                  ),
                ],
              ),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 3, horizontal: 6),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.55),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  widget.sponsorName,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: GtexColors.gold,
                    fontSize: 8,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        );
    }
  }
}

class _Cinema3DBackdropPainter extends CustomPainter {
  const _Cinema3DBackdropPainter({
    required this.phase,
    required this.isGala,
  });

  final double phase;
  final bool isGala;

  @override
  void paint(Canvas canvas, Size size) {
    final double w = size.width;
    final double h = size.height;
    final double horizonY = h * 0.65;

    // Perspective Grid
    final Paint gridPaint = Paint()
      ..color = (isGala ? GtexColors.gold : GtexColors.pitch).withValues(alpha: 0.16)
      ..strokeWidth = 1.0;

    final double vpX = w * 0.5 + math.sin(phase) * 14.0;
    for (int i = -6; i <= 6; i++) {
      canvas.drawLine(
        Offset(vpX, horizonY),
        Offset(vpX + i * 65.0, h),
        gridPaint,
      );
    }
    for (int r = 1; r <= 5; r++) {
      final double py = horizonY + math.pow(r / 5.0, 1.6) * (h - horizonY);
      canvas.drawLine(Offset(0, py), Offset(w, py), gridPaint);
    }

    // Floodlight Cones
    for (int b = 0; b < 3; b++) {
      final double bx = (w / 4.0) * (b + 1);
      final double sway = math.sin(phase + b * 1.3) * 28.0;
      final Path cone = Path()
        ..moveTo(bx - 10, 0)
        ..lineTo(bx + 10, 0)
        ..lineTo(bx + sway + 85, h * 0.9)
        ..lineTo(bx + sway - 85, h * 0.9)
        ..close();
      final Paint beamPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[
            (b.isEven ? GtexColors.gold : GtexColors.pitch).withValues(alpha: 0.18),
            Colors.transparent,
          ],
        ).createShader(Rect.fromLTWH(0, 0, w, h));
      canvas.drawPath(cone, beamPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _Cinema3DBackdropPainter oldDelegate) =>
      oldDelegate.phase != phase || oldDelegate.isGala != isGala;
}
