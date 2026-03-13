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
    final Color glow = accentColor ?? (emphasized ? GteShellTheme.accent : GteShellTheme.accentWarm);
    final BorderRadius radius = BorderRadius.circular(30);
    final Widget content = Container(
      padding: padding,
      decoration: BoxDecoration(
        borderRadius: radius,
        border: Border.all(color: GteShellTheme.stroke.withValues(alpha: 0.9)),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            (emphasized ? GteShellTheme.panelElevated : GteShellTheme.panelStrong).withValues(alpha: 0.96),
            GteShellTheme.panel.withValues(alpha: 0.95),
            Colors.white.withValues(alpha: emphasized ? 0.06 : 0.03),
          ],
          stops: const <double>[0, 0.65, 1],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.34),
            blurRadius: 34,
            offset: const Offset(0, 18),
          ),
          BoxShadow(
            color: glow.withValues(alpha: emphasized ? 0.1 : 0.06),
            blurRadius: 34,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Stack(
        children: <Widget>[
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 3,
              decoration: BoxDecoration(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(30)),
                gradient: LinearGradient(
                  colors: <Color>[
                    glow.withValues(alpha: 0.95),
                    Colors.white.withValues(alpha: 0.12),
                    GteShellTheme.accentWarm.withValues(alpha: 0.35),
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
