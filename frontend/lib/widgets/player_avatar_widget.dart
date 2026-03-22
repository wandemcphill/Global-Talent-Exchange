import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/player_avatar.dart';

const bool _debugAvatarOverlayEnabled =
    bool.fromEnvironment('DEBUG_AVATAR', defaultValue: false) ||
        bool.fromEnvironment('debug-avatar', defaultValue: false);

class PlayerAvatarWidget extends StatelessWidget {
  const PlayerAvatarWidget({
    super.key,
    required this.avatar,
    required this.size,
    this.mode = AvatarMode.card,
    this.withShadow = false,
  });

  final PlayerAvatar avatar;
  final double size;
  final AvatarMode mode;
  final bool withShadow;

  @override
  Widget build(BuildContext context) {
    final Widget avatarPaint = RepaintBoundary(
      child: SizedBox.square(
        dimension: size,
        child: Stack(
          fit: StackFit.expand,
          children: <Widget>[
            CustomPaint(
              isComplex: mode != AvatarMode.hudMinimal,
              willChange: false,
              painter: _PlayerAvatarPainter(
                avatar: avatar,
                mode: mode,
              ),
            ),
            if (_debugAvatarOverlayEnabled && size >= 48)
              IgnorePointer(
                child: _PlayerAvatarDebugOverlay(
                  avatar: avatar,
                  size: size,
                ),
              ),
          ],
        ),
      ),
    );

    if (!withShadow) {
      return avatarPaint;
    }

    return DecoratedBox(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.16),
            blurRadius: size * 0.14,
            offset: Offset(0, size * 0.04),
          ),
        ],
      ),
      child: avatarPaint,
    );
  }
}

class _PlayerAvatarDebugOverlay extends StatelessWidget {
  const _PlayerAvatarDebugOverlay({
    required this.avatar,
    required this.size,
  });

  final PlayerAvatar avatar;
  final double size;

  @override
  Widget build(BuildContext context) {
    final bool compact = size < 64;
    final double fontSize = math.max(8, size * 0.10);
    final TextStyle textStyle =
        Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: Colors.white,
                  fontSize: fontSize,
                  height: 1.0,
                ) ??
            TextStyle(
              color: Colors.white,
              fontSize: fontSize,
              height: 1.0,
            );

    return Align(
      alignment: Alignment.bottomCenter,
      child: Container(
        margin: EdgeInsets.all(size * 0.04),
        padding: EdgeInsets.symmetric(
          horizontal: size * 0.05,
          vertical: size * 0.035,
        ),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.72),
          borderRadius: BorderRadius.circular(size * 0.08),
          border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
        ),
        child: DefaultTextStyle(
          style: textStyle,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'seed ${_truncate(avatar.seedToken, compact ? 12 : 20)}',
                softWrap: false,
                overflow: TextOverflow.fade,
              ),
              if (!compact)
                Text(
                  avatar.debugSummary,
                  softWrap: false,
                  overflow: TextOverflow.fade,
                ),
            ],
          ),
        ),
      ),
    );
  }

  String _truncate(String value, int maxLength) {
    if (value.length <= maxLength) {
      return value;
    }
    return '${value.substring(0, maxLength - 1)}...';
  }
}

class _PlayerAvatarPainter extends CustomPainter {
  const _PlayerAvatarPainter({
    required this.avatar,
    required this.mode,
  });

  final PlayerAvatar avatar;
  final AvatarMode mode;

  static const List<Color> _skinPalette = <Color>[
    Color(0xFFF7D7C3),
    Color(0xFFE7BC9B),
    Color(0xFFD2A177),
    Color(0xFFB67E58),
    Color(0xFF8A5C39),
    Color(0xFF5F3C28),
  ];
  static const List<Color> _hairPalette = <Color>[
    Color(0xFF141414),
    Color(0xFF2F241E),
    Color(0xFF5C4433),
    Color(0xFFD5B37A),
    Color(0xFF8A4D33),
    Color(0xFF8D939C),
  ];
  static const List<Color> _accentPalette = <Color>[
    Color(0xFF2C7A5A),
    Color(0xFF1E4E89),
    Color(0xFF8E6C1F),
    Color(0xFF8C3C4A),
    Color(0xFF4F4BA2),
    Color(0xFF1B7A83),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final double side = math.min(size.width, size.height);
    final Rect bounds = Offset.zero & Size.square(side);
    final Color accent =
        _accentPalette[avatar.accentTone % _accentPalette.length];
    final Color skin = _skinPalette[avatar.skinTone % _skinPalette.length];
    final Color hair = _hairPalette[avatar.hairColor % _hairPalette.length];
    final Color jersey = Color.lerp(accent, Colors.black, 0.16) ?? accent;
    final Color outline = Colors.black.withValues(alpha: 0.22);
    final bool hudMinimal = mode == AvatarMode.hudMinimal;
    final bool compact =
        hudMinimal || mode == AvatarMode.hud || mode == AvatarMode.chip;
    final bool detailMode =
        mode == AvatarMode.card || mode == AvatarMode.profile;

    final Paint fillPaint = Paint()..style = PaintingStyle.fill;
    final Paint strokePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = side * (compact ? 0.018 : 0.022)
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = outline;

    fillPaint.color = accent.withValues(alpha: compact ? 0.18 : 0.22);
    canvas.drawCircle(bounds.center, side * 0.5, fillPaint);

    fillPaint.color = accent.withValues(alpha: 0.08);
    canvas.drawCircle(
      Offset(bounds.center.dx, side * 0.28),
      side * 0.26,
      fillPaint,
    );

    _drawJersey(
      canvas,
      size: side,
      jersey: jersey,
      accent: accent,
      strokePaint: strokePaint,
    );

    final Rect neckRect = Rect.fromCenter(
      center: Offset(bounds.center.dx, side * 0.60),
      width: side * 0.12,
      height: side * 0.11,
    );
    fillPaint.color = Color.lerp(skin, Colors.black, 0.04) ?? skin;
    canvas.drawRRect(
      RRect.fromRectAndRadius(neckRect, Radius.circular(side * 0.04)),
      fillPaint,
    );

    final Rect headRect = _headRect(side);
    if (hudMinimal) {
      _drawHudMinimalAvatar(
        canvas,
        headRect: headRect,
        skin: skin,
        hair: hair,
        strokePaint: strokePaint,
        size: side,
      );
      final Paint borderPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = side * 0.02
        ..color = accent.withValues(alpha: 0.22);
      canvas.drawCircle(bounds.center, side * 0.49, borderPaint);
      return;
    }

    final Path headPath = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          headRect,
          Radius.elliptical(headRect.width * 0.28, headRect.height * 0.32),
        ),
      );
    fillPaint.color = skin;
    canvas.drawPath(headPath, fillPaint);
    canvas.drawPath(headPath, strokePaint);

    _drawEars(canvas, headRect: headRect, skin: skin, strokePaint: strokePaint);
    _drawHair(
      canvas,
      headRect: headRect,
      hair: hair,
      strokePaint: strokePaint,
      size: side,
    );
    _drawFaceFeatures(
      canvas,
      headRect: headRect,
      strokePaint: strokePaint,
      size: side,
      detailMode: detailMode,
      compact: compact,
    );
    _drawBeard(
      canvas,
      headRect: headRect,
      hair: hair,
      strokePaint: strokePaint,
      size: side,
      compact: compact,
    );
    _drawAccessory(
      canvas,
      headRect: headRect,
      accent: accent,
      strokePaint: strokePaint,
      size: side,
    );

    final Paint borderPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = side * 0.02
      ..color = accent.withValues(alpha: 0.22);
    canvas.drawCircle(bounds.center, side * 0.49, borderPaint);
  }

  void _drawHudMinimalAvatar(
    Canvas canvas, {
    required Rect headRect,
    required Color skin,
    required Color hair,
    required Paint strokePaint,
    required double size,
  }) {
    final Paint headPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = skin;
    final RRect head = RRect.fromRectAndRadius(
      headRect,
      Radius.elliptical(headRect.width * 0.24, headRect.height * 0.28),
    );
    canvas.drawRRect(head, headPaint);
    canvas.drawRRect(head, strokePaint);

    final Paint hairPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = hair;
    switch (avatar.hairStyle % 3) {
      case 0:
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.06,
            headRect.top,
            headRect.width * 0.88,
            headRect.height * 0.30,
          ),
          math.pi,
          math.pi,
          true,
          hairPaint,
        );
        break;
      case 1:
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTWH(
              headRect.left + headRect.width * 0.10,
              headRect.top + headRect.height * 0.02,
              headRect.width * 0.80,
              headRect.height * 0.18,
            ),
            Radius.circular(size * 0.04),
          ),
          hairPaint,
        );
        break;
      case 2:
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.02,
            headRect.top - headRect.height * 0.02,
            headRect.width * 0.96,
            headRect.height * 0.24,
          ),
          math.pi,
          math.pi,
          false,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = size * 0.03
            ..strokeCap = StrokeCap.round
            ..color = hair.withValues(alpha: 0.52),
        );
        break;
    }

    final Paint badgePaint = Paint()
      ..style = PaintingStyle.fill
      ..color = Colors.white.withValues(alpha: 0.26);
    canvas.drawCircle(
      Offset(headRect.center.dx, headRect.bottom - headRect.height * 0.12),
      headRect.width * 0.05,
      badgePaint,
    );
  }

  Rect _headRect(double side) {
    const List<double> widthFactors = <double>[0.60, 0.64, 0.69, 0.62, 0.58];
    const List<double> heightFactors = <double>[0.73, 0.70, 0.68, 0.75, 0.78];
    final double width =
        side * widthFactors[avatar.faceShape % widthFactors.length];
    final double height =
        side * heightFactors[avatar.faceShape % heightFactors.length];
    return Rect.fromCenter(
      center: Offset(side * 0.5, side * 0.43),
      width: width,
      height: height,
    );
  }

  void _drawEars(
    Canvas canvas, {
    required Rect headRect,
    required Color skin,
    required Paint strokePaint,
  }) {
    final Paint earPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = Color.lerp(skin, Colors.black, 0.02) ?? skin;
    final Rect leftEar = Rect.fromCenter(
      center: Offset(headRect.left + headRect.width * 0.04, headRect.center.dy),
      width: headRect.width * 0.12,
      height: headRect.height * 0.18,
    );
    final Rect rightEar = Rect.fromCenter(
      center:
          Offset(headRect.right - headRect.width * 0.04, headRect.center.dy),
      width: headRect.width * 0.12,
      height: headRect.height * 0.18,
    );
    canvas.drawOval(leftEar, earPaint);
    canvas.drawOval(rightEar, earPaint);
    canvas.drawOval(leftEar, strokePaint);
    canvas.drawOval(rightEar, strokePaint);
  }

  void _drawJersey(
    Canvas canvas, {
    required double size,
    required Color jersey,
    required Color accent,
    required Paint strokePaint,
  }) {
    final Path jerseyPath = Path()
      ..moveTo(size * 0.16, size * 0.94)
      ..quadraticBezierTo(size * 0.20, size * 0.66, size * 0.40, size * 0.66)
      ..lineTo(size * 0.60, size * 0.66)
      ..quadraticBezierTo(size * 0.80, size * 0.66, size * 0.84, size * 0.94)
      ..close();
    final Paint jerseyPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = jersey;
    canvas.drawPath(jerseyPath, jerseyPaint);
    canvas.drawPath(jerseyPath, strokePaint);

    final Paint patternPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size * 0.04
      ..strokeCap = StrokeCap.round
      ..color = Color.lerp(accent, Colors.white, 0.35) ?? accent;
    switch (avatar.jerseyStyle % 4) {
      case 1:
        canvas.drawLine(
          Offset(size * 0.34, size * 0.70),
          Offset(size * 0.34, size * 0.92),
          patternPaint,
        );
        canvas.drawLine(
          Offset(size * 0.50, size * 0.68),
          Offset(size * 0.50, size * 0.94),
          patternPaint,
        );
        canvas.drawLine(
          Offset(size * 0.66, size * 0.70),
          Offset(size * 0.66, size * 0.92),
          patternPaint,
        );
        break;
      case 2:
        canvas.drawLine(
          Offset(size * 0.26, size * 0.74),
          Offset(size * 0.74, size * 0.74),
          patternPaint,
        );
        canvas.drawLine(
          Offset(size * 0.22, size * 0.84),
          Offset(size * 0.78, size * 0.84),
          patternPaint,
        );
        break;
      case 3:
        canvas.drawLine(
          Offset(size * 0.28, size * 0.70),
          Offset(size * 0.70, size * 0.92),
          patternPaint,
        );
        break;
      case 0:
        canvas.drawCircle(
          Offset(size * 0.50, size * 0.79),
          size * 0.04,
          Paint()
            ..style = PaintingStyle.fill
            ..color = accent.withValues(alpha: 0.28),
        );
        break;
    }
  }

  void _drawHair(
    Canvas canvas, {
    required Rect headRect,
    required Color hair,
    required Paint strokePaint,
    required double size,
  }) {
    final Paint hairPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = hair;
    final int style = avatar.hairStyle % 9;
    switch (style) {
      case 0:
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left,
            headRect.top - headRect.height * 0.02,
            headRect.width,
            headRect.height * 0.48,
          ),
          math.pi,
          math.pi,
          true,
          hairPaint,
        );
        break;
      case 1:
        final Path crop = Path()
          ..moveTo(headRect.left + headRect.width * 0.10,
              headRect.top + headRect.height * 0.16)
          ..quadraticBezierTo(
            headRect.center.dx,
            headRect.top - headRect.height * 0.10,
            headRect.right - headRect.width * 0.10,
            headRect.top + headRect.height * 0.16,
          )
          ..lineTo(headRect.right - headRect.width * 0.12,
              headRect.top + headRect.height * 0.27)
          ..quadraticBezierTo(
            headRect.center.dx,
            headRect.top + headRect.height * 0.18,
            headRect.left + headRect.width * 0.12,
            headRect.top + headRect.height * 0.27,
          )
          ..close();
        canvas.drawPath(crop, hairPaint);
        canvas.drawPath(crop, strokePaint);
        break;
      case 2:
        final RRect fadeTop = RRect.fromRectAndRadius(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.14,
            headRect.top + headRect.height * 0.02,
            headRect.width * 0.72,
            headRect.height * 0.24,
          ),
          Radius.circular(size * 0.05),
        );
        canvas.drawRRect(fadeTop, hairPaint);
        canvas.drawRRect(fadeTop, strokePaint);
        canvas.drawRect(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.05,
            headRect.top + headRect.height * 0.10,
            headRect.width * 0.08,
            headRect.height * 0.28,
          ),
          hairPaint,
        );
        canvas.drawRect(
          Rect.fromLTWH(
            headRect.right - headRect.width * 0.13,
            headRect.top + headRect.height * 0.10,
            headRect.width * 0.08,
            headRect.height * 0.28,
          ),
          hairPaint,
        );
        break;
      case 3:
        for (int index = 0; index < 7; index += 1) {
          final double t = index / 6;
          final Offset center = Offset(
            headRect.left + headRect.width * (0.10 + (t * 0.80)),
            headRect.top + headRect.height * (0.08 + ((index % 2) * 0.05)),
          );
          canvas.drawCircle(center, headRect.width * 0.12, hairPaint);
        }
        break;
      case 4:
        final Path swept = Path()
          ..moveTo(headRect.left + headRect.width * 0.12,
              headRect.top + headRect.height * 0.16)
          ..quadraticBezierTo(
            headRect.center.dx + headRect.width * 0.18,
            headRect.top - headRect.height * 0.14,
            headRect.right - headRect.width * 0.04,
            headRect.top + headRect.height * 0.18,
          )
          ..lineTo(headRect.right - headRect.width * 0.16,
              headRect.top + headRect.height * 0.30)
          ..quadraticBezierTo(
            headRect.center.dx - headRect.width * 0.10,
            headRect.top + headRect.height * 0.12,
            headRect.left + headRect.width * 0.16,
            headRect.top + headRect.height * 0.28,
          )
          ..close();
        canvas.drawPath(swept, hairPaint);
        canvas.drawPath(swept, strokePaint);
        break;
      case 5:
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.08,
            headRect.top + headRect.height * 0.04,
            headRect.width * 0.84,
            headRect.height * 0.28,
          ),
          math.pi,
          math.pi,
          true,
          hairPaint,
        );
        canvas.drawCircle(
          Offset(headRect.center.dx, headRect.top + headRect.height * 0.02),
          headRect.width * 0.11,
          hairPaint,
        );
        break;
      case 6:
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.08,
            headRect.top + headRect.height * 0.02,
            headRect.width * 0.84,
            headRect.height * 0.18,
          ),
          math.pi,
          math.pi,
          false,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = size * 0.02
            ..color = hair.withValues(alpha: 0.34),
        );
        break;
      case 7:
        for (int index = 0; index < 6; index += 1) {
          final double t = index / 5;
          canvas.drawCircle(
            Offset(
              headRect.left + headRect.width * (0.14 + (t * 0.72)),
              headRect.top + headRect.height * 0.10,
            ),
            headRect.width * 0.15,
            hairPaint,
          );
        }
        canvas.drawRect(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.06,
            headRect.top + headRect.height * 0.16,
            headRect.width * 0.88,
            headRect.height * 0.12,
          ),
          hairPaint,
        );
        break;
      case 8:
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.10,
            headRect.top + headRect.height * 0.02,
            headRect.width * 0.80,
            headRect.height * 0.24,
          ),
          math.pi,
          math.pi,
          true,
          hairPaint,
        );
        final Paint lockPaint = Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = size * 0.028
          ..strokeCap = StrokeCap.round
          ..color = hair;
        for (int index = 0; index < 4; index += 1) {
          final double t = index / 3;
          final double x = headRect.left + headRect.width * (0.22 + (t * 0.56));
          canvas.drawLine(
            Offset(x, headRect.top + headRect.height * 0.18),
            Offset(x, headRect.top + headRect.height * 0.42),
            lockPaint,
          );
        }
        break;
    }
  }

  void _drawFaceFeatures(
    Canvas canvas, {
    required Rect headRect,
    required Paint strokePaint,
    required double size,
    required bool detailMode,
    required bool compact,
  }) {
    final double eyeY = headRect.top + headRect.height * 0.43;
    final double browY = headRect.top + headRect.height * 0.34;
    final double leftEyeX = headRect.left + headRect.width * 0.33;
    final double rightEyeX = headRect.right - headRect.width * 0.33;
    final Paint featurePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size * (compact ? 0.016 : 0.02)
      ..strokeCap = StrokeCap.round
      ..color = Colors.black.withValues(alpha: 0.62);

    final double browLift = avatar.eyebrowStyle == 1
        ? -headRect.height * 0.015
        : avatar.eyebrowStyle == 2
            ? headRect.height * 0.01
            : 0;
    final double browLength =
        headRect.width * (avatar.eyebrowStyle == 3 ? 0.16 : 0.13);
    canvas.drawLine(
      Offset(leftEyeX - browLength * 0.5, browY + browLift),
      Offset(leftEyeX + browLength * 0.5, browY - browLift),
      featurePaint,
    );
    canvas.drawLine(
      Offset(rightEyeX - browLength * 0.5, browY - browLift),
      Offset(rightEyeX + browLength * 0.5, browY + browLift),
      featurePaint,
    );

    switch (avatar.eyeType % 4) {
      case 0:
        canvas.drawCircle(
          Offset(leftEyeX, eyeY),
          headRect.width * 0.028,
          Paint()..color = Colors.black.withValues(alpha: 0.72),
        );
        canvas.drawCircle(
          Offset(rightEyeX, eyeY),
          headRect.width * 0.028,
          Paint()..color = Colors.black.withValues(alpha: 0.72),
        );
        break;
      case 1:
        canvas.drawLine(
          Offset(leftEyeX - headRect.width * 0.05, eyeY),
          Offset(leftEyeX + headRect.width * 0.05, eyeY),
          featurePaint,
        );
        canvas.drawLine(
          Offset(rightEyeX - headRect.width * 0.05, eyeY),
          Offset(rightEyeX + headRect.width * 0.05, eyeY),
          featurePaint,
        );
        break;
      case 2:
        canvas.drawArc(
          Rect.fromCenter(
            center: Offset(leftEyeX, eyeY),
            width: headRect.width * 0.12,
            height: headRect.height * 0.08,
          ),
          math.pi,
          math.pi,
          false,
          featurePaint,
        );
        canvas.drawArc(
          Rect.fromCenter(
            center: Offset(rightEyeX, eyeY),
            width: headRect.width * 0.12,
            height: headRect.height * 0.08,
          ),
          math.pi,
          math.pi,
          false,
          featurePaint,
        );
        break;
      case 3:
        canvas.drawCircle(
          Offset(leftEyeX, eyeY),
          headRect.width * 0.022,
          Paint()..color = Colors.black.withValues(alpha: 0.72),
        );
        canvas.drawCircle(
          Offset(rightEyeX, eyeY),
          headRect.width * 0.022,
          Paint()..color = Colors.black.withValues(alpha: 0.72),
        );
        canvas.drawLine(
          Offset(
              leftEyeX - headRect.width * 0.04, eyeY + headRect.height * 0.02),
          Offset(
              leftEyeX + headRect.width * 0.04, eyeY + headRect.height * 0.02),
          featurePaint,
        );
        canvas.drawLine(
          Offset(
              rightEyeX - headRect.width * 0.04, eyeY + headRect.height * 0.02),
          Offset(
              rightEyeX + headRect.width * 0.04, eyeY + headRect.height * 0.02),
          featurePaint,
        );
        break;
    }

    if (detailMode) {
      final double noseX = headRect.center.dx;
      final double noseTop = headRect.top + headRect.height * 0.48;
      final double noseBottom = headRect.top + headRect.height * 0.62;
      switch (avatar.noseType % 4) {
        case 0:
          canvas.drawLine(
              Offset(noseX, noseTop), Offset(noseX, noseBottom), featurePaint);
          break;
        case 1:
          final Path path = Path()
            ..moveTo(noseX, noseTop)
            ..lineTo(noseX - headRect.width * 0.03, noseBottom)
            ..lineTo(noseX + headRect.width * 0.03, noseBottom);
          canvas.drawPath(path, featurePaint);
          break;
        case 2:
          canvas.drawLine(
            Offset(noseX - headRect.width * 0.01, noseTop),
            Offset(noseX + headRect.width * 0.01, noseBottom),
            featurePaint,
          );
          break;
        case 3:
          canvas.drawArc(
            Rect.fromCenter(
              center: Offset(noseX, headRect.top + headRect.height * 0.58),
              width: headRect.width * 0.10,
              height: headRect.height * 0.08,
            ),
            0,
            math.pi,
            false,
            featurePaint,
          );
          break;
      }
    }

    final double mouthY = headRect.top + headRect.height * 0.76;
    switch (avatar.mouthType % 4) {
      case 0:
        canvas.drawLine(
          Offset(headRect.center.dx - headRect.width * 0.08, mouthY),
          Offset(headRect.center.dx + headRect.width * 0.08, mouthY),
          featurePaint,
        );
        break;
      case 1:
        canvas.drawArc(
          Rect.fromCenter(
            center: Offset(headRect.center.dx, mouthY - headRect.height * 0.01),
            width: headRect.width * 0.18,
            height: headRect.height * 0.08,
          ),
          0,
          math.pi,
          false,
          featurePaint,
        );
        break;
      case 2:
        canvas.drawArc(
          Rect.fromCenter(
            center: Offset(headRect.center.dx, mouthY + headRect.height * 0.01),
            width: headRect.width * 0.18,
            height: headRect.height * 0.08,
          ),
          math.pi,
          math.pi,
          false,
          featurePaint,
        );
        break;
      case 3:
        canvas.drawLine(
          Offset(headRect.center.dx - headRect.width * 0.07, mouthY),
          Offset(headRect.center.dx + headRect.width * 0.07, mouthY),
          featurePaint,
        );
        canvas.drawCircle(
          Offset(headRect.center.dx - headRect.width * 0.09, mouthY),
          headRect.width * 0.01,
          Paint()..color = featurePaint.color,
        );
        canvas.drawCircle(
          Offset(headRect.center.dx + headRect.width * 0.09, mouthY),
          headRect.width * 0.01,
          Paint()..color = featurePaint.color,
        );
        break;
    }
  }

  void _drawBeard(
    Canvas canvas, {
    required Rect headRect,
    required Color hair,
    required Paint strokePaint,
    required double size,
    required bool compact,
  }) {
    final Paint beardPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = hair.withValues(alpha: compact ? 0.50 : 0.66);
    switch (avatar.beardStyle % 6) {
      case 0:
        return;
      case 1:
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.16,
            headRect.top + headRect.height * 0.64,
            headRect.width * 0.68,
            headRect.height * 0.22,
          ),
          0,
          math.pi,
          true,
          beardPaint,
        );
        break;
      case 2:
        final RRect goatee = RRect.fromRectAndRadius(
          Rect.fromCenter(
            center: Offset(
                headRect.center.dx, headRect.bottom - headRect.height * 0.12),
            width: headRect.width * 0.20,
            height: headRect.height * 0.20,
          ),
          Radius.circular(size * 0.03),
        );
        canvas.drawRRect(goatee, beardPaint);
        break;
      case 3:
        final Path shortBeard = Path()
          ..moveTo(headRect.left + headRect.width * 0.14,
              headRect.top + headRect.height * 0.64)
          ..quadraticBezierTo(
            headRect.center.dx,
            headRect.bottom + headRect.height * 0.02,
            headRect.right - headRect.width * 0.14,
            headRect.top + headRect.height * 0.64,
          )
          ..lineTo(headRect.right - headRect.width * 0.08,
              headRect.top + headRect.height * 0.54)
          ..quadraticBezierTo(
            headRect.center.dx,
            headRect.bottom - headRect.height * 0.08,
            headRect.left + headRect.width * 0.08,
            headRect.top + headRect.height * 0.54,
          )
          ..close();
        canvas.drawPath(shortBeard, beardPaint);
        canvas.drawPath(shortBeard, strokePaint);
        break;
      case 4:
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromCenter(
              center: Offset(
                  headRect.center.dx, headRect.top + headRect.height * 0.68),
              width: headRect.width * 0.24,
              height: headRect.height * 0.07,
            ),
            Radius.circular(size * 0.02),
          ),
          beardPaint,
        );
        break;
      case 5:
        final Path fullBeard = Path()
          ..moveTo(headRect.left + headRect.width * 0.10,
              headRect.top + headRect.height * 0.58)
          ..quadraticBezierTo(
            headRect.center.dx,
            headRect.bottom + headRect.height * 0.10,
            headRect.right - headRect.width * 0.10,
            headRect.top + headRect.height * 0.58,
          )
          ..lineTo(headRect.right - headRect.width * 0.05,
              headRect.top + headRect.height * 0.42)
          ..quadraticBezierTo(
            headRect.center.dx,
            headRect.bottom - headRect.height * 0.06,
            headRect.left + headRect.width * 0.05,
            headRect.top + headRect.height * 0.42,
          )
          ..close();
        canvas.drawPath(fullBeard, beardPaint);
        canvas.drawPath(fullBeard, strokePaint);
        break;
    }
  }

  void _drawAccessory(
    Canvas canvas, {
    required Rect headRect,
    required Color accent,
    required Paint strokePaint,
    required double size,
  }) {
    if (!avatar.hasAccessory || avatar.accessoryType == 0) {
      return;
    }
    switch (avatar.accessoryType % 4) {
      case 1:
        final Paint bandPaint = Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = size * 0.05
          ..strokeCap = StrokeCap.round
          ..color = accent.withValues(alpha: 0.88);
        canvas.drawArc(
          Rect.fromLTWH(
            headRect.left + headRect.width * 0.06,
            headRect.top + headRect.height * 0.08,
            headRect.width * 0.88,
            headRect.height * 0.22,
          ),
          math.pi,
          math.pi,
          false,
          bandPaint,
        );
        break;
      case 2:
        final Paint gogglePaint = Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = size * 0.02
          ..color = accent.withValues(alpha: 0.72);
        final Rect leftLens = Rect.fromCenter(
          center: Offset(headRect.left + headRect.width * 0.33,
              headRect.top + headRect.height * 0.43),
          width: headRect.width * 0.18,
          height: headRect.height * 0.10,
        );
        final Rect rightLens = Rect.fromCenter(
          center: Offset(headRect.right - headRect.width * 0.33,
              headRect.top + headRect.height * 0.43),
          width: headRect.width * 0.18,
          height: headRect.height * 0.10,
        );
        canvas.drawRRect(
          RRect.fromRectAndRadius(leftLens, Radius.circular(size * 0.02)),
          gogglePaint,
        );
        canvas.drawRRect(
          RRect.fromRectAndRadius(rightLens, Radius.circular(size * 0.02)),
          gogglePaint,
        );
        canvas.drawLine(
            leftLens.centerRight, rightLens.centerLeft, gogglePaint);
        break;
      case 3:
        final Paint tapePaint = Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = size * 0.03
          ..strokeCap = StrokeCap.round
          ..color = Colors.white.withValues(alpha: 0.86);
        canvas.drawLine(
          Offset(headRect.right - headRect.width * 0.20,
              headRect.top + headRect.height * 0.64),
          Offset(headRect.right - headRect.width * 0.08,
              headRect.top + headRect.height * 0.69),
          tapePaint,
        );
        break;
    }
  }

  @override
  bool shouldRepaint(covariant _PlayerAvatarPainter oldDelegate) {
    return oldDelegate.avatar != avatar || oldDelegate.mode != mode;
  }
}
