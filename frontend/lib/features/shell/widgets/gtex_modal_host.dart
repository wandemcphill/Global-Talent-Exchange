import 'package:flutter/material.dart';

import '../../../widgets/gte_shell_theme.dart';
import '../models/gtex_surface_state.dart';

@immutable
class GtexModalEntry {
  const GtexModalEntry({
    required this.title,
    required this.body,
    this.state = GtexSurfaceState.pending,
    this.primaryLabel,
    this.onPrimary,
    this.secondaryLabel,
    this.onSecondary,
    this.onClose,
  });

  final String title;
  final Widget body;
  final GtexSurfaceState state;
  final String? primaryLabel;
  final VoidCallback? onPrimary;
  final String? secondaryLabel;
  final VoidCallback? onSecondary;
  final VoidCallback? onClose;
}

class GtexModalHost extends StatelessWidget {
  const GtexModalHost({super.key, required this.child, this.modal});

  final Widget child;
  final GtexModalEntry? modal;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: <Widget>[
        child,
        if (modal != null) _ModalOverlay(entry: modal!),
      ],
    );
  }
}

class _ModalOverlay extends StatelessWidget {
  const _ModalOverlay({required this.entry});

  final GtexModalEntry entry;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final config = entry.state.config(context);
    return Positioned.fill(
      child: Material(
        color: Colors.black.withValues(alpha: 0.56),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Container(
              margin: EdgeInsets.all(tokens.spaceLg),
              padding: EdgeInsets.all(tokens.spaceLg),
              decoration: BoxDecoration(
                color: tokens.panelStrong,
                borderRadius: BorderRadius.circular(tokens.radiusLarge),
                border: Border.all(
                  color: config.accentColor.withValues(alpha: 0.3),
                ),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: tokens.shadow.withValues(alpha: 0.5),
                    blurRadius: 34,
                    offset: const Offset(0, 22),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Icon(config.icon, color: config.accentColor),
                      SizedBox(width: tokens.spaceSm),
                      Expanded(
                        child: Text(
                          entry.title,
                          style: Theme.of(
                            context,
                          ).textTheme.titleLarge?.copyWith(
                            color: tokens.textPrimary,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      if (entry.onClose != null)
                        IconButton(
                          tooltip: 'Close modal',
                          onPressed: entry.onClose,
                          icon: const Icon(Icons.close),
                        ),
                    ],
                  ),
                  SizedBox(height: tokens.spaceMd),
                  entry.body,
                  if (entry.primaryLabel != null ||
                      entry.secondaryLabel != null) ...<Widget>[
                    SizedBox(height: tokens.spaceLg),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: <Widget>[
                        if (entry.secondaryLabel != null)
                          OutlinedButton(
                            onPressed: entry.onSecondary,
                            child: Text(entry.secondaryLabel!),
                          ),
                        if (entry.secondaryLabel != null &&
                            entry.primaryLabel != null)
                          SizedBox(width: tokens.spaceSm),
                        if (entry.primaryLabel != null)
                          FilledButton(
                            onPressed: entry.onPrimary,
                            child: Text(entry.primaryLabel!),
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
