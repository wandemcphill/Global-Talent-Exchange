import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_surface_panel.dart';

String gtexCompactCurrency(double value) {
  if (value >= 1000000) {
    return '${(value / 1000000).toStringAsFixed(1)}M';
  }
  if (value >= 1000) {
    return '${(value / 1000).toStringAsFixed(0)}K';
  }
  return value.toStringAsFixed(0);
}

Color gtexAccentForIndex(BuildContext context, int index) {
  final tokens = GteShellTheme.tokensOf(context);
  final List<Color> palette = <Color>[
    tokens.accent,
    tokens.accentArena,
    tokens.accentClub,
    tokens.accentCommunity,
    tokens.accentCapital,
  ];
  return palette[index % palette.length];
}

class GtexBroadcastCard extends StatelessWidget {
  const GtexBroadcastCard({
    super.key,
    required this.child,
    this.accent,
    this.padding = const EdgeInsets.all(18),
    this.onTap,
  });

  final Widget child;
  final Color? accent;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accent,
      padding: padding,
      onTap: onTap,
      child: child,
    );
  }
}

class GtexBadgeIcon extends StatelessWidget {
  const GtexBadgeIcon({
    super.key,
    required this.label,
    this.color,
  });

  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color resolvedColor = color ?? tokens.accent;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: resolvedColor.withValues(alpha: 0.14),
        border: Border.all(color: resolvedColor.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: resolvedColor,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class GtexStatBar extends StatelessWidget {
  const GtexStatBar({
    super.key,
    required this.label,
    required this.value,
    required this.progress,
    this.color,
    this.trailing,
  });

  final String label;
  final String value;
  final double progress;
  final Color? color;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color resolvedColor = color ?? tokens.accent;
    final double safeProgress = progress.clamp(0, 1);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.bodySmall),
            ),
            if (trailing != null) trailing! else Text(value),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            minHeight: 10,
            value: safeProgress,
            backgroundColor: tokens.surfaceHighlight.withValues(alpha: 0.14),
            valueColor: AlwaysStoppedAnimation<Color>(resolvedColor),
          ),
        ),
      ],
    );
  }
}

class GtexMetricPill extends StatelessWidget {
  const GtexMetricPill({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.color,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color resolvedColor = color ?? tokens.accent;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: tokens.panelStrong.withValues(alpha: 0.82),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.7)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 18, color: resolvedColor),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(label, style: Theme.of(context).textTheme.bodySmall),
              Text(
                value,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: resolvedColor,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class GtexAnimatedAvatar extends StatefulWidget {
  const GtexAnimatedAvatar({
    super.key,
    required this.label,
    this.size = 68,
    this.accent,
    this.badges = const <String>[],
    this.rating,
  });

  final String label;
  final double size;
  final Color? accent;
  final List<String> badges;
  final int? rating;

  @override
  State<GtexAnimatedAvatar> createState() => _GtexAnimatedAvatarState();
}

class _GtexAnimatedAvatarState extends State<GtexAnimatedAvatar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent = widget.accent ?? tokens.accentArena;
    final String initials = _initials(widget.label);
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final double pulse = 0.94 + (_controller.value * 0.08);
        final double lift = math.sin(_controller.value * math.pi) * 6;
        return Transform.translate(
          offset: Offset(0, -lift),
          child: Stack(
            clipBehavior: Clip.none,
            children: <Widget>[
              Container(
                width: widget.size,
                height: widget.size,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: accent.withValues(alpha: 0.22 * pulse),
                      blurRadius: 28,
                      spreadRadius: 6,
                    ),
                  ],
                ),
              ),
              Container(
                width: widget.size,
                height: widget.size,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[
                      accent.withValues(alpha: 0.92),
                      tokens.panelElevated,
                      tokens.accentWarm.withValues(alpha: 0.75),
                    ],
                  ),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.16),
                  ),
                ),
                child: Center(
                  child: Text(
                    initials,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: tokens.textInverse,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
              ),
              if (widget.rating != null)
                Positioned(
                  right: -4,
                  bottom: -6,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: tokens.panel,
                      border: Border.all(
                        color: accent.withValues(alpha: 0.4),
                      ),
                    ),
                    child: Text(
                      widget.rating.toString(),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: accent,
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                  ),
                ),
              if (widget.badges.isNotEmpty)
                Positioned(
                  left: -6,
                  top: -8,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: tokens.panelStrong,
                      border: Border.all(
                        color: accent.withValues(alpha: 0.28),
                      ),
                    ),
                    child: Text(widget.badges.take(2).join(' ')),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  String _initials(String raw) {
    final List<String> parts = raw
        .trim()
        .split(RegExp(r'\s+'))
        .where((String value) => value.isNotEmpty)
        .toList();
    if (parts.isEmpty) {
      return 'GT';
    }
    if (parts.length == 1) {
      return parts.first
          .substring(0, math.min(2, parts.first.length))
          .toUpperCase();
    }
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }
}

class GtexModalSheet extends StatelessWidget {
  const GtexModalSheet({
    super.key,
    required this.title,
    this.subtitle,
    required this.child,
  });

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Center(
              child: Container(
                width: 52,
                height: 5,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  color: tokens.stroke.withValues(alpha: 0.8),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text(title, style: Theme.of(context).textTheme.headlineSmall),
            if (subtitle != null) ...<Widget>[
              const SizedBox(height: 8),
              Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
            ],
            const SizedBox(height: 18),
            child,
          ],
        ),
      ),
    );
  }
}

class GtexTimelineTile extends StatelessWidget {
  const GtexTimelineTile({
    super.key,
    required this.title,
    required this.subtitle,
    this.color,
  });

  final String title;
  final String subtitle;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color resolvedColor = color ?? tokens.accent;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Column(
          children: <Widget>[
            Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: resolvedColor,
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: resolvedColor.withValues(alpha: 0.3),
                    blurRadius: 12,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
            Container(
              width: 2,
              height: 54,
              color: tokens.stroke.withValues(alpha: 0.8),
            ),
          ],
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 6),
                Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class GtexRadarChart extends StatelessWidget {
  const GtexRadarChart({
    super.key,
    required this.attributes,
    this.color,
    this.size = 240,
  });

  final Map<String, int> attributes;
  final Color? color;
  final double size;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color resolvedColor = color ?? tokens.accentArena;
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _GtexRadarPainter(
          labels: attributes.keys.toList(growable: false),
          values: attributes.values.map((int value) => value / 100).toList(
                growable: false,
              ),
          color: resolvedColor,
          stroke: tokens.stroke.withValues(alpha: 0.65),
          textColor: tokens.textMuted,
        ),
      ),
    );
  }
}

class _GtexRadarPainter extends CustomPainter {
  _GtexRadarPainter({
    required this.labels,
    required this.values,
    required this.color,
    required this.stroke,
    required this.textColor,
  });

  final List<String> labels;
  final List<double> values;
  final Color color;
  final Color stroke;
  final Color textColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (labels.isEmpty || labels.length != values.length) {
      return;
    }
    final Offset center = Offset(size.width / 2, size.height / 2);
    final double radius = math.min(size.width, size.height) * 0.30;
    final Paint gridPaint = Paint()
      ..color = stroke
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final Paint fillPaint = Paint()
      ..color = color.withValues(alpha: 0.20)
      ..style = PaintingStyle.fill;
    final Paint outlinePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    for (int ring = 1; ring <= 4; ring += 1) {
      final double ringRadius = radius * (ring / 4);
      canvas.drawPath(
          _polygonPath(center, ringRadius, labels.length), gridPaint);
    }
    for (int index = 0; index < labels.length; index += 1) {
      final double angle = _angleFor(index, labels.length);
      final Offset point =
          center + Offset(math.cos(angle), math.sin(angle)) * radius;
      canvas.drawLine(center, point, gridPaint);
      final TextPainter painter = TextPainter(
        text: TextSpan(
          text: labels[index],
          style: TextStyle(
            color: textColor,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: 80);
      final Offset labelPoint =
          center + Offset(math.cos(angle), math.sin(angle)) * (radius + 20);
      painter.paint(
        canvas,
        Offset(labelPoint.dx - (painter.width / 2), labelPoint.dy - 8),
      );
    }
    final Path valuePath = Path();
    for (int index = 0; index < values.length; index += 1) {
      final double angle = _angleFor(index, values.length);
      final Offset point = center +
          Offset(math.cos(angle), math.sin(angle)) * (radius * values[index]);
      if (index == 0) {
        valuePath.moveTo(point.dx, point.dy);
      } else {
        valuePath.lineTo(point.dx, point.dy);
      }
    }
    valuePath.close();
    canvas.drawPath(valuePath, fillPaint);
    canvas.drawPath(valuePath, outlinePaint);
  }

  Path _polygonPath(Offset center, double radius, int count) {
    final Path path = Path();
    for (int index = 0; index < count; index += 1) {
      final double angle = _angleFor(index, count);
      final Offset point =
          center + Offset(math.cos(angle), math.sin(angle)) * radius;
      if (index == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }
    path.close();
    return path;
  }

  double _angleFor(int index, int count) {
    return (-math.pi / 2) + ((math.pi * 2) * (index / count));
  }

  @override
  bool shouldRepaint(covariant _GtexRadarPainter oldDelegate) {
    return oldDelegate.labels != labels ||
        oldDelegate.values != values ||
        oldDelegate.color != color ||
        oldDelegate.stroke != stroke ||
        oldDelegate.textColor != textColor;
  }
}
