import 'package:flutter/material.dart';

import '../../../widgets/gte_shell_theme.dart';
import '../models/gtex_surface_state.dart';

enum GtexDrawerSide { left, right }

@immutable
class GtexDrawerEntry {
  const GtexDrawerEntry({
    required this.title,
    required this.child,
    this.state = GtexSurfaceState.confirmed,
    this.side = GtexDrawerSide.right,
    this.width = 380,
    this.onClose,
  });

  final String title;
  final Widget child;
  final GtexSurfaceState state;
  final GtexDrawerSide side;
  final double width;
  final VoidCallback? onClose;
}

class GtexDrawerHost extends StatelessWidget {
  const GtexDrawerHost({super.key, required this.child, this.drawer});

  final Widget child;
  final GtexDrawerEntry? drawer;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: <Widget>[
        child,
        if (drawer != null) _DrawerOverlay(entry: drawer!),
      ],
    );
  }
}

class _DrawerOverlay extends StatelessWidget {
  const _DrawerOverlay({required this.entry});

  final GtexDrawerEntry entry;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final config = entry.state.config(context);
    final Alignment alignment =
        entry.side == GtexDrawerSide.left
            ? Alignment.centerLeft
            : Alignment.centerRight;

    return Positioned.fill(
      child: Material(
        color: Colors.black.withValues(alpha: 0.34),
        child: Align(
          alignment: alignment,
          child: SafeArea(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: entry.width, minWidth: 280),
              child: Container(
                height: double.infinity,
                margin: EdgeInsets.all(tokens.spaceSm),
                decoration: BoxDecoration(
                  color: tokens.panelStrong,
                  borderRadius: BorderRadius.circular(tokens.radiusLarge),
                  border: Border.all(
                    color: config.accentColor.withValues(alpha: 0.28),
                  ),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: tokens.shadow.withValues(alpha: 0.48),
                      blurRadius: 32,
                      offset: const Offset(0, 18),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Padding(
                      padding: EdgeInsets.all(tokens.spaceMd),
                      child: Row(
                        children: <Widget>[
                          Icon(config.icon, color: config.accentColor),
                          SizedBox(width: tokens.spaceSm),
                          Expanded(
                            child: Text(
                              entry.title,
                              style: Theme.of(
                                context,
                              ).textTheme.titleMedium?.copyWith(
                                color: tokens.textPrimary,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                          if (entry.onClose != null)
                            IconButton(
                              tooltip: 'Close drawer',
                              onPressed: entry.onClose,
                              icon: const Icon(Icons.close),
                            ),
                        ],
                      ),
                    ),
                    Divider(color: tokens.stroke, height: 1),
                    Expanded(
                      child: Padding(
                        padding: EdgeInsets.all(tokens.spaceMd),
                        child: entry.child,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
