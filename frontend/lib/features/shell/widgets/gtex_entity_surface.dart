import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import 'gtex_state_panel.dart';

@immutable
class GtexEntityMetric {
  const GtexEntityMetric({
    required this.label,
    required this.value,
    this.state = GtexSurfaceState.confirmed,
  });

  final String label;
  final String value;
  final GtexSurfaceState state;
}

@immutable
class GtexEntityAction {
  const GtexEntityAction({
    required this.label,
    required this.icon,
    required this.onSelected,
    this.state = GtexSurfaceState.confirmed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onSelected;
  final GtexSurfaceState state;

  bool get isEnabled =>
      onSelected != null &&
      state != GtexSurfaceState.loading &&
      state != GtexSurfaceState.blocked &&
      state != GtexSurfaceState.error;
}

class GtexEntitySurface extends StatelessWidget {
  const GtexEntitySurface({
    super.key,
    required this.state,
    required this.title,
    this.eyebrow,
    this.subtitle,
    this.icon,
    this.leading,
    this.metrics = const <GtexEntityMetric>[],
    this.actions = const <GtexEntityAction>[],
    this.onTap,
    this.accentColor,
    this.dense = false,
  });

  final GtexSurfaceState state;
  final String title;
  final String? eyebrow;
  final String? subtitle;
  final IconData? icon;
  final Widget? leading;
  final List<GtexEntityMetric> metrics;
  final List<GtexEntityAction> actions;
  final VoidCallback? onTap;
  final Color? accentColor;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = accentColor ?? gtexSurfaceToneFor(theme, state);
    final String resolvedTitle = _clean(title) ?? gtexSurfaceTitleFor(state);
    final String resolvedSubtitle =
        _clean(subtitle) ?? gtexSurfaceMessageFor(state);
    final String? resolvedEyebrow = _clean(eyebrow);
    final List<GtexEntityMetric> visibleMetrics = metrics
        .where(
          (GtexEntityMetric metric) =>
              _clean(metric.label) != null || _clean(metric.value) != null,
        )
        .toList(growable: false);

    return Semantics(
      liveRegion: state.requiresAttention,
      button: onTap != null,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onTap,
          child: Container(
            padding: EdgeInsets.all(dense ? 12 : 14),
            decoration: BoxDecoration(
              color: tone.withValues(alpha: 0.07),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: tone.withValues(alpha: 0.22)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    leading ??
                        _EntityIcon(
                          icon: icon ?? gtexSurfaceIconFor(state),
                          tone: tone,
                          dense: dense,
                        ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          if (resolvedEyebrow != null) ...<Widget>[
                            Text(
                              resolvedEyebrow.toUpperCase(),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: theme.textTheme.labelSmall?.copyWith(
                                color: tone,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0,
                              ),
                            ),
                            const SizedBox(height: 4),
                          ],
                          Text(
                            resolvedTitle,
                            maxLines: dense ? 1 : 2,
                            overflow: TextOverflow.ellipsis,
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    GtexSurfaceStateBadge(state: state, compact: dense),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  resolvedSubtitle,
                  maxLines: dense ? 2 : 3,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.70),
                    height: 1.28,
                  ),
                ),
                if (visibleMetrics.isNotEmpty) ...<Widget>[
                  SizedBox(height: dense ? 8 : 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: visibleMetrics
                        .map((GtexEntityMetric metric) {
                          return _EntityMetricChip(metric: metric);
                        })
                        .toList(growable: false),
                  ),
                ],
                if (actions.isNotEmpty) ...<Widget>[
                  SizedBox(height: dense ? 8 : 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: actions
                        .map((GtexEntityAction action) {
                          return ActionChip(
                            avatar: Icon(action.icon, size: 16),
                            label: Text(action.label),
                            onPressed:
                                action.isEnabled ? action.onSelected : null,
                            side: BorderSide(
                              color: gtexSurfaceToneFor(
                                theme,
                                action.state,
                              ).withValues(alpha: 0.28),
                            ),
                          );
                        })
                        .toList(growable: false),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _EntityIcon extends StatelessWidget {
  const _EntityIcon({
    required this.icon,
    required this.tone,
    required this.dense,
  });

  final IconData icon;
  final Color tone;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final double size = dense ? 32 : 36;
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.20)),
      ),
      child: Icon(icon, color: tone, size: dense ? 17 : 19),
    );
  }
}

class _EntityMetricChip extends StatelessWidget {
  const _EntityMetricChip({required this.metric});

  final GtexEntityMetric metric;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = gtexSurfaceToneFor(theme, metric.state);
    final String label = _clean(metric.label) ?? 'Metric';
    final String value =
        _clean(metric.value) ?? gtexSurfaceTitleFor(metric.state);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.20)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: theme.textTheme.labelSmall?.copyWith(
              color: tone,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            value,
            style: theme.textTheme.labelMedium?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

String? _clean(String? value) {
  final String? trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}
