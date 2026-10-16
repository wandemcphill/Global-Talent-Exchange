import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

/// Reusable identity banner for Club, Player, or Manager profiles.
class GtexIdentityHeader extends StatelessWidget {
  const GtexIdentityHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.crestUrl,
    this.avatarChild,
    this.avatarIcon = Icons.shield,
    this.countryToken,
    this.prestigeTier,
    this.secondaryTag,
    this.actions = const <Widget>[],
    this.accentColor = GtexColors.gold,
  });

  final String title;
  final String? subtitle;
  final String? crestUrl;
  final Widget? avatarChild;
  final IconData avatarIcon;
  final String? countryToken;
  final String? prestigeTier;
  final String? secondaryTag;
  final List<Widget> actions;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: accentColor.withValues(alpha: 0.35)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: accentColor.withValues(alpha: 0.08),
            blurRadius: 16,
            spreadRadius: -2,
          ),
        ],
      ),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool isCompact = constraints.maxWidth < 600;

          final Widget avatarWidget = avatarChild ??
              Container(
                width: isCompact ? 54 : 68,
                height: isCompact ? 54 : 68,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: GtexColors.surfaceBase,
                  border: Border.all(color: accentColor, width: 2),
                ),
                child: ClipOval(
                  child: crestUrl != null && crestUrl!.isNotEmpty
                      ? Image.network(
                          crestUrl!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Icon(
                            avatarIcon,
                            size: isCompact ? 28 : 36,
                            color: accentColor,
                          ),
                        )
                      : Icon(
                          avatarIcon,
                          size: isCompact ? 28 : 36,
                          color: accentColor,
                        ),
                ),
              );

          final Widget infoWidget = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: GtexSpacing.xs,
                runSpacing: 4,
                children: <Widget>[
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                          letterSpacing: -0.3,
                        ),
                  ),
                  if (countryToken != null && countryToken!.isNotEmpty) ...<Widget>[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: GtexColors.surfaceRaised.withValues(alpha: 0.4),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: GtexColors.line),
                      ),
                      child: Text(
                        countryToken!.toUpperCase(),
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: GtexColors.textSecondary,
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ),
                  ],
                ],
              ),
              if (subtitle != null && subtitle!.isNotEmpty) ...<Widget>[
                const SizedBox(height: 2),
                Text(
                  subtitle!,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ],
              if (prestigeTier != null || secondaryTag != null) ...<Widget>[
                const SizedBox(height: 6),
                Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: 4,
                  children: <Widget>[
                    if (prestigeTier != null && prestigeTier!.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: accentColor.withValues(alpha: 0.16),
                          borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                          border: Border.all(color: accentColor.withValues(alpha: 0.5)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            Icon(Icons.workspace_premium, size: 14, color: accentColor),
                            const SizedBox(width: 4),
                            Text(
                              prestigeTier!,
                              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: accentColor,
                                    fontWeight: FontWeight.w900,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    if (secondaryTag != null && secondaryTag!.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: GtexColors.pitch.withValues(alpha: 0.16),
                          borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                          border: Border.all(color: GtexColors.pitch.withValues(alpha: 0.4)),
                        ),
                        child: Text(
                          secondaryTag!,
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: GtexColors.pitch,
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                      ),
                  ],
                ),
              ],
            ],
          );

          if (isCompact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    avatarWidget,
                    const SizedBox(width: GtexSpacing.md),
                    Expanded(child: infoWidget),
                  ],
                ),
                if (actions.isNotEmpty) ...<Widget>[
                  const SizedBox(height: GtexSpacing.md),
                  Wrap(
                    spacing: GtexSpacing.xs,
                    runSpacing: GtexSpacing.xs,
                    children: actions,
                  ),
                ],
              ],
            );
          }

          return Row(
            children: <Widget>[
              avatarWidget,
              const SizedBox(width: GtexSpacing.md),
              Expanded(child: infoWidget),
              if (actions.isNotEmpty) ...<Widget>[
                const SizedBox(width: GtexSpacing.md),
                Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  alignment: WrapAlignment.end,
                  children: actions,
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
