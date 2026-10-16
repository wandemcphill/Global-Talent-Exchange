import 'package:flutter/material.dart';

import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_surface_panel.dart';

enum GtexSurfaceTone { neutral, live, info, success, warning, danger }

class GtexHeroPanel extends StatelessWidget {
  const GtexHeroPanel({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.description,
    this.metrics = const <Widget>[],
    this.actions = const <Widget>[],
    this.accentColor,
  });

  final String eyebrow;
  final String title;
  final String description;
  final List<Widget> metrics;
  final List<Widget> actions;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    final Color accent = accentColor ?? visuals.heroAccent;
    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      padding: EdgeInsets.all(tokens.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(tokens.radiusPill),
              border: Border.all(color: accent.withValues(alpha: 0.26)),
            ),
            child: Text(
              eyebrow,
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(color: accent),
            ),
          ),
          SizedBox(height: tokens.spaceMd),
          Text(title, style: Theme.of(context).textTheme.displaySmall),
          SizedBox(height: tokens.spaceXs),
          Text(
            description,
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(color: tokens.textMuted),
          ),
          if (metrics.isNotEmpty) ...<Widget>[
            SizedBox(height: tokens.spaceLg),
            Wrap(
              spacing: tokens.spaceSm,
              runSpacing: tokens.spaceSm,
              children: metrics,
            ),
          ],
          if (actions.isNotEmpty) ...<Widget>[
            SizedBox(height: tokens.spaceLg),
            Wrap(
              spacing: tokens.spaceSm,
              runSpacing: tokens.spaceSm,
              children: actions,
            ),
          ],
        ],
      ),
    );
  }
}

class GtexSectionPanel extends StatelessWidget {
  const GtexSectionPanel({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
    this.eyebrow,
    this.trailing,
    this.emphasized = false,
    this.accentColor,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final String? eyebrow;
  final Widget? trailing;
  final bool emphasized;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent =
        accentColor ?? GteShellTheme.definitionOf(context).primaryColor;
    return GteSurfacePanel(
      emphasized: emphasized,
      accentColor: accent,
      padding: EdgeInsets.all(tokens.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    if (eyebrow != null) ...<Widget>[
                      Text(
                        eyebrow!,
                        style: Theme.of(
                          context,
                        ).textTheme.labelLarge?.copyWith(color: accent),
                      ),
                      SizedBox(height: tokens.spaceXs),
                    ],
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    SizedBox(height: tokens.spaceXs),
                    Text(
                      subtitle,
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(color: tokens.textMuted),
                    ),
                  ],
                ),
              ),
              if (trailing != null) ...<Widget>[
                SizedBox(width: tokens.spaceMd),
                trailing!,
              ],
            ],
          ),
          SizedBox(height: tokens.spaceLg),
          child,
        ],
      ),
    );
  }
}

class GtexStatTile extends StatelessWidget {
  const GtexStatTile({
    super.key,
    required this.label,
    required this.value,
    this.support,
    this.icon,
    this.tone = GtexSurfaceTone.info,
  });

  final String label;
  final String value;
  final String? support;
  final IconData? icon;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color toneColor = _toneColor(context, tone);
    return Container(
      constraints: const BoxConstraints(minWidth: 160, maxWidth: 220),
      padding: EdgeInsets.all(tokens.spaceMd),
      decoration: BoxDecoration(
        color: toneColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(tokens.radiusMedium),
        border: Border.all(color: toneColor.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            children: <Widget>[
              if (icon != null) ...<Widget>[
                Icon(icon, color: toneColor, size: 16),
                SizedBox(width: tokens.spaceXs),
              ],
              Expanded(
                child: Text(
                  label.toUpperCase(),
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: toneColor,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: tokens.spaceSm),
          Text(value, style: Theme.of(context).textTheme.headlineSmall),
          if (support != null) ...<Widget>[
            SizedBox(height: tokens.spaceXs),
            Text(
              support!,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: tokens.textMuted),
            ),
          ],
        ],
      ),
    );
  }
}

class GtexPill extends StatelessWidget {
  const GtexPill({
    super.key,
    required this.label,
    this.icon,
    this.tone = GtexSurfaceTone.info,
  });

  final String label;
  final IconData? icon;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color toneColor = _toneColor(context, tone);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: toneColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(tokens.radiusPill),
        border: Border.all(color: toneColor.withValues(alpha: 0.26)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 14, color: toneColor),
            const SizedBox(width: 6),
          ],
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: toneColor,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class GtexListTile extends StatelessWidget {
  const GtexListTile({
    super.key,
    required this.title,
    required this.subtitle,
    this.leadingIcon,
    this.trailing,
    this.tone = GtexSurfaceTone.info,
  });

  final String title;
  final String subtitle;
  final IconData? leadingIcon;
  final Widget? trailing;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color toneColor = _toneColor(context, tone);
    return Container(
      padding: EdgeInsets.all(tokens.spaceMd),
      decoration: BoxDecoration(
        color: toneColor.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(tokens.radiusMedium),
        border: Border.all(
          color: GteShellTheme.tokensOf(context).stroke.withValues(alpha: 0.7),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (leadingIcon != null) ...<Widget>[
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: toneColor.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(tokens.radiusSmall),
              ),
              child: Icon(leadingIcon, color: toneColor, size: 18),
            ),
            SizedBox(width: tokens.spaceMd),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                SizedBox(height: tokens.spaceXs),
                Text(
                  subtitle,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: tokens.textMuted),
                ),
              ],
            ),
          ),
          if (trailing != null) ...<Widget>[
            SizedBox(width: tokens.spaceMd),
            trailing!,
          ],
        ],
      ),
    );
  }
}

Color _toneColor(BuildContext context, GtexSurfaceTone tone) {
  final theme = GteShellTheme.definitionOf(context);
  final tokens = GteShellTheme.tokensOf(context);
  switch (tone) {
    case GtexSurfaceTone.neutral:
      return tokens.textMuted;
    case GtexSurfaceTone.live:
      return theme.primaryColor;
    case GtexSurfaceTone.info:
      return theme.secondaryColor;
    case GtexSurfaceTone.success:
      return tokens.positive;
    case GtexSurfaceTone.warning:
      return tokens.warning;
    case GtexSurfaceTone.danger:
      return tokens.negative;
  }
}

class GtexLiveTickerBar extends StatelessWidget {
  const GtexLiveTickerBar({super.key, required this.items, this.accentColor});

  final List<String> items;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent =
        accentColor ?? GteShellTheme.definitionOf(context).primaryColor;
    final List<String> resolved =
        items.where((String item) => item.trim().isNotEmpty).toList();
    if (resolved.isEmpty) {
      return const SizedBox.shrink();
    }
    return GteSurfacePanel(
      accentColor: accent,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: SizedBox(
        height: 28,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          physics: const BouncingScrollPhysics(),
          itemCount: resolved.length,
          separatorBuilder:
              (BuildContext context, int index) => Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Icon(
                  Icons.fiber_manual_record_rounded,
                  size: 10,
                  color: accent.withValues(alpha: 0.72),
                ),
              ),
          itemBuilder:
              (BuildContext context, int index) => Center(
                child: Text(
                  resolved[index],
                  style: Theme.of(
                    context,
                  ).textTheme.labelLarge?.copyWith(color: tokens.textPrimary),
                ),
              ),
        ),
      ),
    );
  }
}

class GtexAnimatedMetricValue extends StatelessWidget {
  const GtexAnimatedMetricValue({
    super.key,
    required this.value,
    required this.builder,
    this.duration = const Duration(milliseconds: 700),
  });

  final double value;
  final Widget Function(BuildContext context, double value) builder;
  final Duration duration;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: value),
      duration: duration,
      curve: Curves.easeOutCubic,
      builder: (BuildContext context, double animated, Widget? child) {
        return builder(context, animated);
      },
    );
  }
}
