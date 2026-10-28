import 'dart:async';
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
  clubTakeover,
  facilityUpgrade,
  academyUpgrade,
  wonderkidEmergence,
  competitionFinal,
  stadiumAdDisplay,
  newAdDeal,
  clubAnnouncement,
  privateJetFlex,
}

enum GtexCinema3DMode {
  motion3d,
  fmDiorama,
}

/// GTEX Next-Gen v2.0 Volumetric 3D Presentation, Broadcast & Diorama Stage (Flutter — Full 17-Scene Suite)
/// Features:
///  - True Dual-Sided 180° Matrix4 Volumes (Front Face + Extruded Depth Plane + Counter-Rotated True Back Face)
///  - `Director Cut` 3-Shot Camera Choreography (Macro Close-Up -> 180° Back Reveal -> Hero Wide Orbit)
///  - Interactive Pyro & Confetti Particle Burst Painter
///  - Livery / Kit Edition Customizer (Home / Gold / Midnight)
class GtexCinema3DStage extends StatefulWidget {
  const GtexCinema3DStage({
    super.key,
    required this.scene,
    required this.title,
    this.subtitle,
    this.badgeText,
    this.clubName = 'GTEX FC',
    this.ownerName = 'Club Owner',
    this.subjectName = 'MARQUEE STAR',
    this.subjectRole = 'First-Team Signing',
    this.jerseyNumber = 9,
    this.overallRating = 88,
    this.potentialRating,
    this.sponsorName = 'GTEX GLOBAL AIRWAYS',
    this.facilityLevel = 4,
    this.quote,
    this.defaultMode = GtexCinema3DMode.motion3d,
    this.compact = false,
    this.enableSocialSalute = false,
  });

  final GtexCinema3DScene scene;
  final String title;
  final String? subtitle;
  final String? badgeText;
  final String clubName;
  final String ownerName;
  final String subjectName;
  final String subjectRole;
  final int jerseyNumber;
  final int overallRating;
  final int? potentialRating;
  final String sponsorName;
  final int facilityLevel;
  final String? quote;
  final GtexCinema3DMode defaultMode;
  final bool compact;
  final bool enableSocialSalute;

  @override
  State<GtexCinema3DStage> createState() => _GtexCinema3DStageState();
}

class _GtexCinema3DStageState extends State<GtexCinema3DStage>
    with SingleTickerProviderStateMixin {
  late GtexCinema3DMode _mode;
  late final AnimationController _controller;
  double _rotY = -0.22;
  double _rotX = 0.1;
  double _cameraScale = 1.0;
  bool _dragging = false;
  int _salutes = 54;
  bool _saluted = false;
  int _liveryIndex = 0; // 0: Home, 1: Gold, 2: Midnight
  String? _directorShotLabel;
  double _pyroBurstSeed = 0.0;
  Timer? _directorTimer;

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
    _directorTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _triggerPyro() {
    setState(() {
      _pyroBurstSeed = DateTime.now().millisecondsSinceEpoch.toDouble();
    });
  }

  void _flip180() {
    setState(() {
      final bool isBack = math.cos(_rotY) < 0;
      _rotY = isBack ? -0.22 : math.pi - 0.18;
    });
  }

  void _runDirectorCut() {
    _directorTimer?.cancel();
    setState(() {
      _mode = GtexCinema3DMode.motion3d;
      _directorShotLabel = 'SHOT 1 · MACRO CREST CLOSE-UP';
      _cameraScale = 1.18;
      _rotX = 0.18;
      _rotY = -0.15;
    });

    _directorTimer = Timer(const Duration(milliseconds: 1400), () {
      if (!mounted) return;
      setState(() {
        _directorShotLabel = 'SHOT 2 · 180° BACK PRINT & PYRO';
        _cameraScale = 1.06;
        _rotX = 0.08;
        _rotY = math.pi - 0.12;
        _pyroBurstSeed = DateTime.now().millisecondsSinceEpoch.toDouble();
      });

      _directorTimer = Timer(const Duration(milliseconds: 1500), () {
        if (!mounted) return;
        setState(() {
          _directorShotLabel = 'SHOT 3 · HERO WIDE 360° ORBIT';
          _cameraScale = 1.0;
          _rotX = 0.1;
          _rotY = -0.22;
        });

        _directorTimer = Timer(const Duration(milliseconds: 1400), () {
          if (!mounted) return;
          setState(() {
            _directorShotLabel = null;
          });
        });
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final bool isGala = widget.scene == GtexCinema3DScene.worldGala ||
        widget.scene == GtexCinema3DScene.competitionFinal ||
        widget.scene == GtexCinema3DScene.privateJetFlex ||
        widget.scene == GtexCinema3DScene.clubTakeover ||
        widget.scene == GtexCinema3DScene.wonderkidEmergence;
    final Color accentColor = _liveryIndex == 1
        ? GtexColors.gold
        : _liveryIndex == 2
            ? GtexColors.cyan
            : (isGala ? GtexColors.gold : GtexColors.pitch);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF04070F),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: accentColor.withValues(alpha: 0.6),
          width: 1.5,
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.7),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
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
            color: const Color(0xFF090E1C),
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
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: <Widget>[
                    InkWell(
                      onTap: _runDirectorCut,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                        decoration: BoxDecoration(
                          color: GtexColors.gold,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text(
                          'Director Cut',
                          style: TextStyle(
                            color: Color(0xFF050811),
                            fontSize: 10,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: _flip180,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Colors.white24),
                        ),
                        child: const Text(
                          'Flip 180°',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: _triggerPyro,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                        decoration: BoxDecoration(
                          color: GtexColors.gold.withValues(alpha: 0.16),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: GtexColors.gold.withValues(alpha: 0.45)),
                        ),
                        child: const Text(
                          'Pyro',
                          style: TextStyle(
                            color: GtexColors.gold,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: () => setState(() => _liveryIndex = (_liveryIndex + 1) % 3),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                        decoration: BoxDecoration(
                          color: GtexColors.cyan.withValues(alpha: 0.16),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: GtexColors.cyan.withValues(alpha: 0.45)),
                        ),
                        child: Text(
                          _liveryIndex == 0
                              ? 'Home'
                              : _liveryIndex == 1
                                  ? 'Gold'
                                  : 'Midnight',
                          style: const TextStyle(
                            color: GtexColors.cyan,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: () => setState(() => _mode = GtexCinema3DMode.motion3d),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _mode == GtexCinema3DMode.motion3d
                              ? GtexColors.pitch.withValues(alpha: 0.22)
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
                    InkWell(
                      onTap: () => setState(() {
                        _mode = GtexCinema3DMode.fmDiorama;
                        _rotY = -0.26;
                        _rotX = 0.1;
                      }),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _mode == GtexCinema3DMode.fmDiorama
                              ? GtexColors.cyan.withValues(alpha: 0.22)
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
              height: widget.compact ? 220 : 270,
              child: AnimatedBuilder(
                animation: _controller,
                builder: (BuildContext context, _) {
                  final double t = _mode == GtexCinema3DMode.motion3d
                      ? _controller.value * 2 * math.pi
                      : 0.0;
                  final double effectiveRotY =
                      _mode == GtexCinema3DMode.motion3d && !_dragging && _directorShotLabel == null
                          ? _rotY + math.sin(t) * 0.45
                          : _rotY;

                  final bool isShowingBack = math.cos(effectiveRotY) < 0;

                  final Matrix4 backShadowMatrix = Matrix4.identity()
                    ..setEntry(3, 2, 0.0015)
                    ..translateByDouble(8.0, 10.0, -18.0, 1.0)
                    ..scaleByDouble(_cameraScale, _cameraScale, 1.0, 1.0)
                    ..rotateX(_rotX)
                    ..rotateY(effectiveRotY);

                  final Matrix4 mainMatrix = Matrix4.identity()
                    ..setEntry(3, 2, 0.0015)
                    ..scaleByDouble(_cameraScale, _cameraScale, 1.0, 1.0)
                    ..rotateX(_rotX)
                    ..rotateY(isShowingBack ? effectiveRotY + math.pi : effectiveRotY);

                  return Stack(
                    alignment: Alignment.center,
                    children: <Widget>[
                      Positioned.fill(
                        child: CustomPaint(
                          painter: _Cinema3DBackdropPainter(
                            phase: t,
                            isGala: isGala,
                            pyroSeed: _pyroBurstSeed,
                          ),
                        ),
                      ),
                      // Back Extruded Depth Shadow Plane
                      Opacity(
                        opacity: 0.45,
                        child: Transform(
                          alignment: Alignment.center,
                          transform: backShadowMatrix,
                          child: _build3DCenterpiece(),
                        ),
                      ),
                      // Foreground Dual-Sided Volumetric 3D Object
                      Transform(
                        alignment: Alignment.center,
                        transform: mainMatrix,
                        child: isShowingBack
                            ? _build3DBackCenterpiece(accentColor)
                            : _build3DCenterpiece(),
                      ),
                      Positioned(
                        top: 8,
                        left: 10,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 3,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.65),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.14),
                                ),
                              ),
                              child: Text(
                                _directorShotLabel ?? 'Drag 360° Volumetric 3D Camera',
                                style: const TextStyle(
                                  color: GtexColors.textSecondary,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: (isShowingBack ? GtexColors.cyan : GtexColors.pitch)
                                    .withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                  color: isShowingBack ? GtexColors.cyan : GtexColors.pitch,
                                ),
                              ),
                              child: Text(
                                isShowingBack ? '180° BACK FACE' : 'FRONT FACE',
                                style: TextStyle(
                                  color: isShowingBack ? GtexColors.cyan : GtexColors.pitch,
                                  fontSize: 9,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                          ],
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
                top: BorderSide(color: GtexColors.gold.withValues(alpha: 0.35)),
              ),
            ),
            child: Row(
              children: <Widget>[
                Expanded(
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
                if (widget.enableSocialSalute ||
                    widget.scene == GtexCinema3DScene.privateJetFlex ||
                    widget.scene == GtexCinema3DScene.clubAnnouncement)
                  GtexActionButton(
                    key: const Key('cinema-3d-social-salute-btn'),
                    label: '${_saluted ? "Saluted" : "Salute Flex"} ($_salutes)',
                    icon: Icons.thumb_up_alt_rounded,
                    compact: true,
                    secondary: !_saluted,
                    onPressed: _saluted
                        ? null
                        : () => setState(() {
                              _saluted = true;
                              _salutes += 1;
                              _pyroBurstSeed =
                                  DateTime.now().millisecondsSinceEpoch.toDouble();
                            }),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _build3DBackCenterpiece(Color accentColor) {
    final String surname = widget.subjectName.split(' ').last.toUpperCase();
    return Container(
      width: 185,
      height: 170,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFF0F172A),
            Color(0xFF040814),
          ],
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accentColor, width: 2.5),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: accentColor.withValues(alpha: 0.45),
            blurRadius: 28,
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: <Widget>[
          Text(
            widget.scene == GtexCinema3DScene.privateJetFlex
                ? 'VIP CABIN CUTAWAY'
                : widget.scene == GtexCinema3DScene.facilityUpgrade ||
                        widget.scene == GtexCinema3DScene.stadiumAdDisplay
                    ? '4-ZONE REVENUE BLUEPRINT'
                    : 'OFFICIAL REVERSE 3D VIEW',
            style: TextStyle(
              color: accentColor,
              fontSize: 9,
              fontWeight: FontWeight.w900,
            ),
          ),
          Column(
            children: <Widget>[
              Text(
                widget.scene == GtexCinema3DScene.privateJetFlex
                    ? '14-SEAT LOUNGE'
                    : '#${widget.jerseyNumber} $surname',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'OVR ${widget.overallRating} · VERIFIED BACKPLATE',
                style: const TextStyle(
                  color: GtexColors.gold,
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          Text(
            '${widget.clubName} · ${widget.ownerName}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: GtexColors.textSecondary,
              fontSize: 9,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _build3DCenterpiece() {
    switch (widget.scene) {
      case GtexCinema3DScene.worldGala:
      case GtexCinema3DScene.competitionFinal:
        return Container(
          width: 150,
          height: 160,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const RadialGradient(
              center: Alignment(-0.3, -0.35),
              colors: <Color>[
                Color(0xFFFFFFFF),
                Color(0xFFFEF08A),
                Color(0xFFF59E0B),
                Color(0xFF78350F),
              ],
            ),
            border: Border.all(color: GtexColors.gold, width: 3.5),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: GtexColors.gold.withValues(alpha: 0.65),
                blurRadius: 32,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              const Icon(Icons.emoji_events_rounded, size: 42, color: Color(0xFF451A03)),
              Text(
                widget.scene == GtexCinema3DScene.competitionFinal
                    ? 'FINAL PLINTH'
                    : "GTEX D'OR",
                style: const TextStyle(
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
      case GtexCinema3DScene.privateJetFlex:
      case GtexCinema3DScene.clubTakeover:
        return Container(
          width: 185,
          height: 165,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: const RadialGradient(
              center: Alignment(-0.25, -0.3),
              colors: <Color>[
                Color(0xFF3B2A14),
                Color(0xFF141126),
                Color(0xFF070610),
              ],
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: GtexColors.gold, width: 2.5),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: GtexColors.gold.withValues(alpha: 0.45),
                blurRadius: 28,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(
                widget.scene == GtexCinema3DScene.privateJetFlex
                    ? Icons.flight_takeoff_rounded
                    : widget.scene == GtexCinema3DScene.clubTakeover
                        ? Icons.workspace_premium_rounded
                        : Icons.diamond_rounded,
                size: 40,
                color: GtexColors.gold,
              ),
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
                '${widget.clubName} · ${widget.ownerName}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: GtexColors.pitch,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        );

      case GtexCinema3DScene.facilityUpgrade:
      case GtexCinema3DScene.academyUpgrade:
      case GtexCinema3DScene.stadiumAdDisplay:
        return Container(
          width: 195,
          height: 165,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xFF0C4A6E),
                Color(0xFF082F49),
                Color(0xFF041322),
              ],
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: GtexColors.cyan, width: 2.5),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: GtexColors.cyan.withValues(alpha: 0.4),
                blurRadius: 28,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Text(
                '3D CATHEDRAL BOWL LVL ${widget.facilityLevel}/5',
                style: const TextStyle(
                  color: GtexColors.cyan,
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                ),
              ),
              Container(
                width: 135,
                height: 68,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: GtexColors.gold, width: 3),
                  color: const Color(0xFF064E3B),
                ),
                alignment: Alignment.center,
                child: Container(
                  width: 92,
                  height: 38,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: Colors.white70, width: 1.5),
                    color: const Color(0xFF10B981),
                  ),
                  alignment: Alignment.center,
                  child: const Icon(Icons.stadium_rounded, size: 20, color: Colors.white),
                ),
              ),
              Text(
                widget.subjectName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: GtexColors.gold,
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        );

      case GtexCinema3DScene.signingWalkout:
      case GtexCinema3DScene.buildASon:
      case GtexCinema3DScene.wonderkidEmergence:
      case GtexCinema3DScene.stadiumSponsor:
      case GtexCinema3DScene.negotiationTable:
      case GtexCinema3DScene.managerArrival:
      case GtexCinema3DScene.boardroomClash:
      case GtexCinema3DScene.newAdDeal:
      case GtexCinema3DScene.clubAnnouncement:
        return Container(
          width: 165,
          height: 175,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: _liveryIndex == 1
                  ? const <Color>[Color(0xFFB45309), Color(0xFF0F172A), Color(0xFFF59E0B)]
                  : _liveryIndex == 2
                      ? const <Color>[Color(0xFF0284C7), Color(0xFF090D16), Color(0xFF7E22CE)]
                      : const <Color>[Color(0xFF059669), Color(0xFF0F172A), Color(0xFFB45309)],
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: GtexColors.gold, width: 2.5),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: GtexColors.pitch.withValues(alpha: 0.45),
                blurRadius: 28,
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
                      fontSize: 36,
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
                  color: Colors.black.withValues(alpha: 0.65),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: GtexColors.gold.withValues(alpha: 0.5)),
                ),
                child: Text(
                  widget.sponsorName,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: GtexColors.gold,
                    fontSize: 8,
                    fontWeight: FontWeight.w900,
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
    required this.pyroSeed,
  });

  final double phase;
  final bool isGala;
  final double pyroSeed;

  @override
  void paint(Canvas canvas, Size size) {
    final double w = size.width;
    final double h = size.height;
    final double horizonY = h * 0.64;

    final Paint gridPaint = Paint()
      ..color = (isGala ? GtexColors.gold : GtexColors.pitch).withValues(alpha: 0.18)
      ..strokeWidth = 1.0;

    final double vpX = w * 0.5 + math.sin(phase) * 16.0;
    for (int i = -7; i <= 7; i++) {
      canvas.drawLine(
        Offset(vpX, horizonY),
        Offset(vpX + i * 65.0, h),
        gridPaint,
      );
    }
    for (int r = 1; r <= 6; r++) {
      final double py = horizonY + math.pow(r / 6.0, 1.65) * (h - horizonY);
      canvas.drawLine(Offset(0, py), Offset(w, py), gridPaint);
    }

    for (int b = 0; b < 4; b++) {
      final double bx = (w / 5.0) * (b + 1);
      final double sway = math.sin(phase + b * 1.3) * 32.0;
      final Path cone = Path()
        ..moveTo(bx - 12, 0)
        ..lineTo(bx + 12, 0)
        ..lineTo(bx + sway + 92, h * 0.92)
        ..lineTo(bx + sway - 92, h * 0.92)
        ..close();
      final Paint beamPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[
            (b.isEven ? GtexColors.gold : GtexColors.pitch).withValues(alpha: 0.2),
            Colors.transparent,
          ],
        ).createShader(Rect.fromLTWH(0, 0, w, h));
      canvas.drawPath(cone, beamPaint);
    }

    // Pyro / Confetti Sparkles
    if (pyroSeed > 0) {
      final Paint sparkPaint = Paint()..style = PaintingStyle.fill;
      for (int i = 0; i < 28; i++) {
        final double px = (w * 0.2) + ((i * 37.0 + phase * 40) % (w * 0.6));
        final double py = (h * 0.18) + ((i * 29.0 + math.sin(phase + i) * 30) % (h * 0.65));
        sparkPaint.color = i.isEven
            ? GtexColors.gold.withValues(alpha: 0.75)
            : GtexColors.pitch.withValues(alpha: 0.75);
        canvas.drawCircle(Offset(px, py), 2.5 + (i % 3), sparkPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _Cinema3DBackdropPainter oldDelegate) =>
      oldDelegate.phase != phase ||
      oldDelegate.isGala != isGala ||
      oldDelegate.pyroSeed != pyroSeed;
}
