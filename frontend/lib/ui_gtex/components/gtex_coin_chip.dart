import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

enum GtexCoinType { gtc, fnc }

extension GtexCoinTypeX on GtexCoinType {
  String get code {
    return switch (this) {
      GtexCoinType.gtc => 'GTC',
      GtexCoinType.fnc => 'FNC',
    };
  }

  String get semanticName {
    return switch (this) {
      GtexCoinType.gtc => 'GTEX Coin',
      GtexCoinType.fnc => 'Fan Coin',
    };
  }
}

class GtexCoinChip extends StatelessWidget {
  const GtexCoinChip({
    super.key,
    required this.amount,
    this.compact = false,
    this.showCode = true,
    this.semanticLabel,
  });

  final String amount;
  final bool compact;
  final bool showCode;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return _CoinChip(
      amount: amount,
      type: GtexCoinType.gtc,
      compact: compact,
      showCode: showCode,
      semanticLabel: semanticLabel,
    );
  }
}

class FanCoinChip extends StatelessWidget {
  const FanCoinChip({
    super.key,
    required this.amount,
    this.compact = false,
    this.showCode = true,
    this.semanticLabel,
  });

  final String amount;
  final bool compact;
  final bool showCode;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return _CoinChip(
      amount: amount,
      type: GtexCoinType.fnc,
      compact: compact,
      showCode: showCode,
      semanticLabel: semanticLabel,
    );
  }
}

class GtexCoinIcon extends StatelessWidget {
  const GtexCoinIcon({
    super.key,
    required this.type,
    this.size = 16,
    this.color,
  });

  final GtexCoinType type;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final Color resolvedColor = color ?? _coinColor(context, type);
    return Semantics(
      label: type.semanticName,
      image: true,
      child: CustomPaint(
        size: Size.square(size),
        painter: _CoinIconPainter(type: type, color: resolvedColor),
      ),
    );
  }
}

class _CoinChip extends StatelessWidget {
  const _CoinChip({
    required this.amount,
    required this.type,
    required this.compact,
    required this.showCode,
    this.semanticLabel,
  });

  final String amount;
  final GtexCoinType type;
  final bool compact;
  final bool showCode;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final Color color = _coinColor(context, type);
    final String trimmedAmount = amount.trim();
    final String visibleLabel =
        showCode ? '$trimmedAmount ${type.code}' : trimmedAmount;
    return Semantics(
      label: semanticLabel ?? '${type.semanticName} $visibleLabel',
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
          vertical: compact ? 4 : 6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(GtexRadius.sm),
          border: Border.all(color: color.withValues(alpha: 0.4)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            GtexCoinIcon(type: type, size: compact ? 13 : 15, color: color),
            SizedBox(width: compact ? 4 : 6),
            Flexible(
              child: Text(
                visibleLabel,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.right,
                style: GtexText.monoSM.copyWith(
                  color: color,
                  fontSize: compact ? 11 : 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Color _coinColor(BuildContext context, GtexCoinType type) {
  final GtexColorTokens colors = GtexColors.of(context);
  return switch (type) {
    GtexCoinType.gtc => colors.brandCoin,
    GtexCoinType.fnc => colors.brandFan,
  };
}

class _CoinIconPainter extends CustomPainter {
  const _CoinIconPainter({required this.type, required this.color});

  final GtexCoinType type;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint stroke =
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = math.max(1.4, size.shortestSide * 0.1)
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round;
    final Paint fill =
        Paint()
          ..color = color.withValues(alpha: 0.14)
          ..style = PaintingStyle.fill;

    if (type == GtexCoinType.gtc) {
      final Path hex = Path();
      for (int index = 0; index < 6; index += 1) {
        final double angle = (math.pi / 3 * index) - math.pi / 6;
        final Offset point = Offset(
          size.width / 2 + math.cos(angle) * size.width * 0.42,
          size.height / 2 + math.sin(angle) * size.height * 0.42,
        );
        if (index == 0) {
          hex.moveTo(point.dx, point.dy);
        } else {
          hex.lineTo(point.dx, point.dy);
        }
      }
      hex.close();
      canvas.drawPath(hex, fill);
      canvas.drawPath(hex, stroke);
      canvas.drawLine(
        Offset(size.width * 0.34, size.height * 0.66),
        Offset(size.width * 0.68, size.height * 0.32),
        stroke,
      );
      canvas.drawArc(
        Rect.fromLTWH(
          size.width * 0.32,
          size.height * 0.28,
          size.width * 0.38,
          size.height * 0.44,
        ),
        math.pi * 0.18,
        math.pi * 1.35,
        false,
        stroke,
      );
      return;
    }

    final Offset center = Offset(size.width / 2, size.height / 2);
    canvas.drawCircle(center, size.shortestSide * 0.42, fill);
    canvas.drawCircle(center, size.shortestSide * 0.42, stroke);
    final Path burst = Path();
    for (int index = 0; index < 10; index += 1) {
      final double radius = index.isEven ? 0.28 : 0.13;
      final double angle = -math.pi / 2 + index * math.pi / 5;
      final Offset point = Offset(
        center.dx + math.cos(angle) * size.width * radius,
        center.dy + math.sin(angle) * size.height * radius,
      );
      if (index == 0) {
        burst.moveTo(point.dx, point.dy);
      } else {
        burst.lineTo(point.dx, point.dy);
      }
    }
    burst.close();
    canvas.drawPath(burst, stroke);
  }

  @override
  bool shouldRepaint(_CoinIconPainter oldDelegate) {
    return oldDelegate.type != type || oldDelegate.color != color;
  }
}
