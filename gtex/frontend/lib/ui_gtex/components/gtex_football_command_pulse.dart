import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

@immutable
class GtexCommandPulseMetric {
  const GtexCommandPulseMetric({
    required this.label,
    required this.value,
    this.delta,
    this.icon,
    this.accent = GtexColors.pitch,
  });

  final String label;
  final String value;
  final String? delta;
  final IconData? icon;
  final Color accent;
}

/// A compact football-operating-system status rail.
///
/// It intentionally sits above the primary board rather than behaving like
/// another generic dashboard card. Values are caller supplied and should come
/// from authoritative GTEX data.
class GtexFootballCommandPulse extends StatelessWidget {
  const GtexFootballCommandPulse({
    super.key,
    required this.kicker,
    required this.title,
    required this.metrics,
    this.trailing,
    this.accent = GtexColors.pitch,
  });

  final String kicker;
  final String title;
  final List<GtexCommandPulseMetric> metrics;
  final Widget? trailing;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            GtexColors.surfaceRaised,
            GtexColors.surfaceBase,
            accent.withValues(alpha: 0.055),
          ],
        ),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: accent.withValues(alpha: 0.34)),
      ),
      padding: const EdgeInsets.fromLTRB(
        GtexSpacing.md,
        GtexSpacing.sm,
        GtexSpacing.md,
        GtexSpacing.md,
      ),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool compact = constraints.maxWidth < 720;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Container(
                    width: 4,
                    height: 34,
                    decoration: BoxDecoration(
                      color: accent,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: GtexSpacing.sm),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          kicker.toUpperCase(),
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: accent,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.9,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: GtexColors.text,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (trailing != null) trailing!,
                ],
              ),
              const SizedBox(height: GtexSpacing.sm),
              SizedBox(
                height: compact ? 76 : 68,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: metrics.length,
                  separatorBuilder:
                      (_, __) => const SizedBox(width: GtexSpacing.sm),
                  itemBuilder: (BuildContext context, int index) {
                    final GtexCommandPulseMetric metric = metrics[index];
                    return _PulseMetric(metric: metric);
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _PulseMetric extends StatelessWidget {
  const _PulseMetric({required this.metric});

  final GtexCommandPulseMetric metric;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 150, maxWidth: 220),
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.sm,
        vertical: GtexSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong.withValues(alpha: 0.82),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.8)),
      ),
      child: Row(
        children: <Widget>[
          if (metric.icon != null) ...<Widget>[
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: metric.accent.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(metric.icon, color: metric.accent, size: 17),
            ),
            const SizedBox(width: GtexSpacing.xs),
          ],
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  metric.label.toUpperCase(),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.55,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: <Widget>[
                    Flexible(
                      child: Text(
                        metric.value,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    if (metric.delta != null &&
                        metric.delta!.trim().isNotEmpty) ...<Widget>[
                      const SizedBox(width: GtexSpacing.xs),
                      Flexible(
                        child: Text(
                          metric.delta!,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: metric.accent,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
