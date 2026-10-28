import 'dart:math' as math;
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/* ============================================================================
   1. 3D-TILT HOLOGRAPHIC FOIL PLAYER CARD + 6-AXIS RADAR POLYGON (FLUTTER)
   ============================================================================ */
class GtexHolographicPlayerCard extends StatefulWidget {
  const GtexHolographicPlayerCard({
    super.key,
    required this.name,
    this.position = 'ST',
    this.overall = 90,
    this.potential = 95,
    this.clubName = 'GTEX FC',
    this.priceLabel = '18,500 GTX',
    this.badgeLabel = '★ TOTY HOLO FOIL',
    this.actionLabel = '3D Walkout →',
    this.onTap,
  });

  final String name;
  final String position;
  final int overall;
  final int? potential;
  final String clubName;
  final String priceLabel;
  final String badgeLabel;
  final String actionLabel;
  final VoidCallback? onTap;

  @override
  State<GtexHolographicPlayerCard> createState() =>
      _GtexHolographicPlayerCardState();
}

class _GtexHolographicPlayerCardState extends State<GtexHolographicPlayerCard> {
  double _rx = 0.0;
  double _ry = 0.0;
  Alignment _glareCenter = const Alignment(0.0, -0.4);
  bool _hovering = false;

  void _updateTilt(Offset localPos, Size size) {
    if (size.width <= 0 || size.height <= 0) return;
    final double nx = (localPos.dx / size.width).clamp(0.0, 1.0);
    final double ny = (localPos.dy / size.height).clamp(0.0, 1.0);
    setState(() {
      _rx = (0.5 - ny) * 0.28;
      _ry = (nx - 0.5) * 0.34;
      _glareCenter = Alignment((nx * 2) - 1, (ny * 2) - 1);
      _hovering = true;
    });
  }

  void _resetTilt() {
    setState(() {
      _rx = 0.0;
      _ry = 0.0;
      _glareCenter = const Alignment(0.0, -0.4);
      _hovering = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final int base = widget.overall.clamp(60, 99);
    final List<int> stats6 = <int>[
      (base + 4).clamp(50, 99),
      (base + 2).clamp(50, 99),
      base,
      (base + 3).clamp(50, 99),
      (base - 14).clamp(48, 99),
      (base - 1).clamp(50, 99),
    ];

    final Matrix4 matrix = Matrix4.identity()
      ..setEntry(3, 2, 0.0014)
      ..rotateX(_rx)
      ..rotateY(_ry);

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final Size cardSize = Size(
          constraints.maxWidth.isFinite ? constraints.maxWidth : 300,
          230,
        );
        return MouseRegion(
          onHover: (PointerHoverEvent e) => _updateTilt(e.localPosition, cardSize),
          onExit: (_) => _resetTilt(),
          child: GestureDetector(
            onPanUpdate: (DragUpdateDetails d) =>
                _updateTilt(d.localPosition, cardSize),
            onPanEnd: (_) => _resetTilt(),
            onTap: widget.onTap,
            child: Transform(
              alignment: Alignment.center,
              transform: matrix,
              child: Container(
                padding: const EdgeInsets.all(GtexSpacing.md),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[
                      Color(0xFF1E1B4B),
                      Color(0xFF090D16),
                      Color(0xFF422006),
                    ],
                  ),
                  border: Border.all(
                    color: GtexColors.gold.withValues(alpha: 0.85),
                    width: 2.0,
                  ),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: GtexColors.gold.withValues(
                        alpha: _hovering ? 0.36 : 0.22,
                      ),
                      blurRadius: 32,
                      offset: const Offset(0, 14),
                    ),
                  ],
                ),
                child: Stack(
                  children: <Widget>[
                    // Holographic Foil Glare Overlay
                    Positioned.fill(
                      child: IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(14),
                            gradient: RadialGradient(
                              center: _glareCenter,
                              radius: 0.95,
                              colors: <Color>[
                                GtexColors.gold.withValues(
                                  alpha: _hovering ? 0.34 : 0.16,
                                ),
                                GtexColors.pitch.withValues(
                                  alpha: _hovering ? 0.20 : 0.08,
                                ),
                                Colors.transparent,
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        // Top Row: OVR Shield & Tier Badge
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: <Widget>[
                            Row(
                              children: <Widget>[
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 10,
                                    vertical: 5,
                                  ),
                                  decoration: BoxDecoration(
                                    color: GtexColors.gold,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Column(
                                    children: <Widget>[
                                      Text(
                                        '${widget.overall}',
                                        style: const TextStyle(
                                          color: Color(0xFF050811),
                                          fontSize: 18,
                                          fontWeight: FontWeight.w900,
                                          height: 1.0,
                                        ),
                                      ),
                                      Text(
                                        widget.position,
                                        style: const TextStyle(
                                          color: Color(0xFF050811),
                                          fontSize: 10,
                                          fontWeight: FontWeight.w900,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(
                                      widget.clubName.toUpperCase(),
                                      style: const TextStyle(
                                        color: GtexColors.gold,
                                        fontSize: 10,
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                    Text(
                                      widget.name,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 15,
                                        fontWeight: FontWeight.w900,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            GtexStatusChip(
                              label: widget.badgeLabel,
                              color: GtexColors.gold,
                              compact: true,
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        // Center Row: 6 Attributes + 6-Axis Radar Polygon
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.42),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.12),
                            ),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: <Widget>[
                              Wrap(
                                spacing: 12,
                                runSpacing: 4,
                                children: <Widget>[
                                  _attrChip('PAC', stats6[0], GtexColors.pitch),
                                  _attrChip('SHO', stats6[1], GtexColors.gold),
                                  _attrChip('PAS', stats6[2], Colors.white),
                                  _attrChip('DRI', stats6[3], GtexColors.pitch),
                                  _attrChip('DEF', stats6[4], GtexColors.cyan),
                                  _attrChip('PHY', stats6[5], Colors.white),
                                ],
                              ),
                              SizedBox(
                                width: 58,
                                height: 58,
                                child: CustomPaint(
                                  painter: _GtexRadarPolygonPainter(
                                    values: stats6,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 10),
                        // Bottom Row: Potential / Price & Action Pill
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: <Widget>[
                            Row(
                              children: <Widget>[
                                if (widget.potential != null) ...<Widget>[
                                  GtexStatusChip(
                                    label: '${widget.potential} POT',
                                    color: GtexColors.pitch,
                                    compact: true,
                                  ),
                                  const SizedBox(width: 8),
                                ],
                                Text(
                                  widget.priceLabel,
                                  style: const TextStyle(
                                    color: GtexColors.gold,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ],
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 5,
                              ),
                              decoration: BoxDecoration(
                                color: GtexColors.pitch,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                widget.actionLabel,
                                style: const TextStyle(
                                  color: Color(0xFF050811),
                                  fontSize: 10,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _attrChip(String label, int val, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          '$label ',
          style: const TextStyle(
            color: GtexColors.textMuted,
            fontSize: 10,
            fontWeight: FontWeight.w800,
          ),
        ),
        Text(
          '$val',
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    );
  }
}

class _GtexRadarPolygonPainter extends CustomPainter {
  const _GtexRadarPolygonPainter({required this.values});

  final List<int> values;

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = Offset(size.width * 0.5, size.height * 0.5);
    final double maxR = math.min(size.width, size.height) * 0.44;
    const List<double> angles = <double>[-90, -30, 30, 90, 150, 210];

    final Paint gridPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.22)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    final Path outer = Path();
    for (int i = 0; i < 6; i++) {
      final double rad = angles[i] * math.pi / 180.0;
      final Offset p = Offset(
        center.dx + math.cos(rad) * maxR,
        center.dy + math.sin(rad) * maxR,
      );
      if (i == 0) {
        outer.moveTo(p.dx, p.dy);
      } else {
        outer.lineTo(p.dx, p.dy);
      }
    }
    outer.close();
    canvas.drawPath(outer, gridPaint);

    final Path poly = Path();
    for (int i = 0; i < 6; i++) {
      final double v = (values[i].clamp(40, 99)) / 100.0;
      final double rad = angles[i] * math.pi / 180.0;
      final Offset p = Offset(
        center.dx + math.cos(rad) * maxR * v,
        center.dy + math.sin(rad) * maxR * v,
      );
      if (i == 0) {
        poly.moveTo(p.dx, p.dy);
      } else {
        poly.lineTo(p.dx, p.dy);
      }
    }
    poly.close();

    canvas.drawPath(
      poly,
      Paint()
        ..color = GtexColors.pitch.withValues(alpha: 0.35)
        ..style = PaintingStyle.fill,
    );
    canvas.drawPath(
      poly,
      Paint()
        ..color = GtexColors.pitch
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0,
    );
  }

  @override
  bool shouldRepaint(covariant _GtexRadarPolygonPainter oldDelegate) =>
      oldDelegate.values != values;
}

/* ============================================================================
   2. ROBINHOOD-GRADE LIVE TELEMETRY SPARKLINE & ROLLING COUNTER CARD (FLUTTER)
   ============================================================================ */
class GtexTelemetrySparklineCard extends StatelessWidget {
  const GtexTelemetrySparklineCard({
    super.key,
    required this.title,
    required this.amount,
    this.currency = 'GTX',
    this.subtitle = 'Real-Time Club Treasury & Commercial Pulse',
    this.deltaLabel = '▲ +14.8% LIVE VELOCITY',
    this.trustScore = 94,
    this.hypeScore = 97,
  });

  final String title;
  final double amount;
  final String currency;
  final String subtitle;
  final String deltaLabel;
  final int trustScore;
  final int hypeScore;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: title,
      subtitle: subtitle,
      isSelected: true,
      trailing: GtexStatusChip(
        label: deltaLabel,
        color: GtexColors.pitch,
        compact: true,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: amount * 0.85, end: amount),
            duration: const Duration(milliseconds: 700),
            curve: Curves.easeOutCubic,
            builder: (BuildContext context, double value, _) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: <Widget>[
                  Text(
                    value.toStringAsFixed(0),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(width: 8),
                  GtexStatusChip(
                    label: currency,
                    color: GtexColors.cyan,
                    compact: true,
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 68,
            child: CustomPaint(
              painter: _GtexAreaSparklinePainter(),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              Expanded(
                child: _radialBadge(
                  'Board Trust',
                  '$trustScore%',
                  GtexColors.pitch,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _radialBadge(
                  'Global Fan Hype',
                  '$hypeScore%',
                  GtexColors.gold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _radialBadge(String label, String pct, Color color) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 32,
            height: 32,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: color, width: 2),
            ),
            child: Text(
              pct,
              style: TextStyle(
                color: color,
                fontSize: 9,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GtexAreaSparklinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final double w = size.width;
    final double h = size.height;
    final List<Offset> pts = <Offset>[
      Offset(4, h * 0.78),
      Offset(w * 0.18, h * 0.64),
      Offset(w * 0.36, h * 0.68),
      Offset(w * 0.54, h * 0.42),
      Offset(w * 0.72, h * 0.46),
      Offset(w * 0.88, h * 0.22),
      Offset(w - 6, h * 0.12),
    ];

    final Path line = Path()..moveTo(pts.first.dx, pts.first.dy);
    for (int i = 1; i < pts.length; i++) {
      line.lineTo(pts[i].dx, pts[i].dy);
    }

    final Path area = Path.from(line)
      ..lineTo(pts.last.dx, h)
      ..lineTo(pts.first.dx, h)
      ..close();

    canvas.drawPath(
      area,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[
            GtexColors.pitch.withValues(alpha: 0.40),
            Colors.transparent,
          ],
        ).createShader(Rect.fromLTWH(0, 0, w, h)),
    );

    canvas.drawPath(
      line,
      Paint()
        ..color = GtexColors.pitch
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.8
        ..strokeCap = StrokeCap.round,
    );

    canvas.drawCircle(
      pts.last,
      4.5,
      Paint()..color = GtexColors.gold,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/* ============================================================================
   3. INTERACTIVE 2.5D TACTICAL TURF PITCH WITH CHEMISTRY LINKS (FLUTTER)
   ============================================================================ */
class GtexTacticalPitch25D extends StatelessWidget {
  const GtexTacticalPitch25D({
    super.key,
    this.formation = '4-3-3',
    this.talismanName = 'REGENT #9',
  });

  final String formation;
  final String talismanName;

  @override
  Widget build(BuildContext context) {
    final Matrix4 pitchMatrix = Matrix4.identity()
      ..setEntry(3, 2, 0.0012)
      ..rotateX(0.32);

    return GtexPanel(
      title: '2.5D Tactical Pitch ($formation)',
      subtitle: 'Live Squad Chemistry Matrix & Positional Links',
      trailing: const GtexStatusChip(
        label: '⚡ CHEM 99',
        color: GtexColors.gold,
        compact: true,
      ),
      child: Center(
        child: Transform(
          alignment: Alignment.center,
          transform: pitchMatrix,
          child: Container(
            height: 175,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: <Color>[
                  Color(0xFF065F46),
                  Color(0xFF047857),
                  Color(0xFF065F46),
                ],
              ),
              border: Border.all(
                color: GtexColors.pitch.withValues(alpha: 0.75),
                width: 2,
              ),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.65),
                  blurRadius: 24,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            child: CustomPaint(
              painter: _GtexPitchChemistryPainter(),
              child: Stack(
                children: <Widget>[
                  Align(
                    alignment: const Alignment(0.0, -0.68),
                    child: _playerNode(talismanName, GtexColors.gold),
                  ),
                  Align(
                    alignment: const Alignment(-0.62, -0.42),
                    child: _playerNode('LW 89', GtexColors.pitch),
                  ),
                  Align(
                    alignment: const Alignment(0.62, -0.42),
                    child: _playerNode('RW 90', GtexColors.pitch),
                  ),
                  Align(
                    alignment: const Alignment(0.0, 0.05),
                    child: _playerNode('CAM 92', GtexColors.gold),
                  ),
                  Align(
                    alignment: const Alignment(0.0, 0.72),
                    child: _playerNode('DEF LINE · 88', GtexColors.cyan),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _playerNode(String label, Color border) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0xFF050811).withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: border, width: 1.5),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 10,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _GtexPitchChemistryPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final double w = size.width;
    final double h = size.height;

    final Paint linePaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.30)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;

    canvas.drawRect(Rect.fromLTWH(10, 8, w - 20, h - 16), linePaint);
    canvas.drawLine(Offset(10, h * 0.5), Offset(w - 10, h * 0.5), linePaint);
    canvas.drawCircle(Offset(w * 0.5, h * 0.5), 22, linePaint);

    final Paint chemGold = Paint()
      ..color = GtexColors.gold
      ..strokeWidth = 2.2;
    final Paint chemGreen = Paint()
      ..color = GtexColors.pitch
      ..strokeWidth = 2.0;

    final Offset st = Offset(w * 0.5, h * 0.18);
    final Offset lw = Offset(w * 0.20, h * 0.30);
    final Offset rw = Offset(w * 0.80, h * 0.30);
    final Offset cam = Offset(w * 0.5, h * 0.52);
    final Offset def = Offset(w * 0.5, h * 0.84);

    canvas.drawLine(st, lw, chemGold);
    canvas.drawLine(st, rw, chemGreen);
    canvas.drawLine(st, cam, chemGold);
    canvas.drawLine(lw, cam, chemGreen);
    canvas.drawLine(rw, cam, chemGreen);
    canvas.drawLine(cam, def, chemGold);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
