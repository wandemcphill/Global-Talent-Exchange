import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';

class GteSurfacePanel extends StatelessWidget {
  const GteSurfacePanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.emphasized = false,
    this.onTap,
    this.accentColor,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final bool emphasized;
  final VoidCallback? onTap;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color glow =
        accentColor ?? (emphasized ? tokens.accent : tokens.accentWarm);
    final BorderRadius radius = BorderRadius.circular(tokens.radiusLarge);
    final Widget content = Container(
      padding: padding,
      decoration: BoxDecoration(
        borderRadius: radius,
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.9)),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            (emphasized ? tokens.panelElevated : tokens.panelStrong)
                .withValues(alpha: 0.96),
            tokens.panel.withValues(alpha: 0.95),
            tokens.surfaceHighlight.withValues(alpha: emphasized ? 0.06 : 0.03),
          ],
          stops: const <double>[0, 0.65, 1],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: tokens.shadow.withValues(alpha: 0.34),
            blurRadius: 30,
            offset: const Offset(0, 16),
          ),
          BoxShadow(
            color: glow.withValues(alpha: emphasized ? 0.08 : 0.04),
            blurRadius: 24,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Stack(
        children: <Widget>[
          Positioned(
            top: -40,
            right: -24,
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: <Color>[
                      glow.withValues(alpha: emphasized ? 0.16 : 0.1),
                      glow.withValues(alpha: 0),
                    ],
                  ),
                ),
                child: const SizedBox(width: 144, height: 144),
              ),
            ),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 3,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(tokens.radiusLarge),
                ),
                gradient: LinearGradient(
                  colors: <Color>[
                    glow.withValues(alpha: 0.95),
                    tokens.surfaceHighlight.withValues(alpha: 0.12),
                    tokens.accentWarm.withValues(alpha: 0.35),
                  ],
                ),
              ),
            ),
          ),
          child,
        ],
      ),
    );

    if (onTap == null) {
      return Material(color: Colors.transparent, child: content);
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: radius,
        onTap: onTap,
        child: content,
      ),
    );
  }
}
