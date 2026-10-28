import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexMetricTile extends StatelessWidget {
  const GtexMetricTile({
    super.key,
    required this.label,
    required this.value,
    this.delta,
    this.helper,
    this.icon,
    this.accent = GtexColors.pitch,
  });

  final String label;
  final String value;
  final String? delta;
  final String? helper;
  final IconData? icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            const Color(0xFF111C32).withValues(alpha: 0.90),
            const Color(0xFF080E1B).withValues(alpha: 0.96),
          ],
        ),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.45),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: <Widget>[
          // Left Vertical Telemetry Accent Bar
          Positioned(
            left: 0,
            top: 10,
            bottom: 10,
            child: Container(
              width: 3.5,
              decoration: BoxDecoration(
                color: accent,
                borderRadius: const BorderRadius.horizontal(
                  right: Radius.circular(4),
                ),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: accent.withValues(alpha: 0.65),
                    blurRadius: 8,
                  ),
                ],
              ),
            ),
          ),
          // Subtle Bottom-Right Micro-Sparkline Wave
          Positioned(
            right: 8,
            bottom: 8,
            width: 78,
            height: 28,
            child: IgnorePointer(
              child: CustomPaint(
                painter: _GtexMicroSparklinePainter(color: accent),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                if (icon != null) ...<Widget>[
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.14),
                      shape: BoxShape.circle,
                      border: Border.all(color: accent.withValues(alpha: 0.35)),
                    ),
                    child: Icon(icon, color: accent, size: 20),
                  ),
                  const SizedBox(height: GtexSpacing.xs),
                ],
                Text(
                  label.toUpperCase(),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                ),
                const SizedBox(height: 3),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                ),
                if (helper != null && helper!.trim().isNotEmpty) ...<Widget>[
                  const SizedBox(height: 3),
                  Text(
                    helper!,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: GtexColors.textMuted,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ],
                if (delta != null) ...<Widget>[
                  const SizedBox(height: 3),
                  Text(
                    delta!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: accent,
                          fontWeight: FontWeight.w900,
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

class _GtexMicroSparklinePainter extends CustomPainter {
  const _GtexMicroSparklinePainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color.withValues(alpha: 0.32)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0
      ..strokeCap = StrokeCap.round;

    final Path path = Path()
      ..moveTo(2, size.height * 0.82)
      ..lineTo(size.width * 0.25, size.height * 0.62)
      ..lineTo(size.width * 0.50, size.height * 0.68)
      ..lineTo(size.width * 0.75, size.height * 0.34)
      ..lineTo(size.width - 2, size.height * 0.14);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _GtexMicroSparklinePainter oldDelegate) =>
      oldDelegate.color != color;
}
