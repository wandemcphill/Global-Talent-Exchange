import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';

class GteSurfacePanel extends StatelessWidget {
  const GteSurfacePanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.emphasized = false,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final bool emphasized;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final Widget content = Container(
      padding: padding,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: GteShellTheme.stroke),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            emphasized ? GteShellTheme.panelStrong : GteShellTheme.panel,
            GteShellTheme.panel.withValues(alpha: 0.88),
          ],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.28),
            blurRadius: 28,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: child,
    );

    if (onTap == null) {
      return Material(
        color: Colors.transparent,
        child: content,
      );
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(28),
        onTap: onTap,
        child: content,
      ),
    );
  }
}
