import 'package:flutter/material.dart';

import '../../../widgets/gte_shell_theme.dart';
import '../models/gtex_surface_state.dart';

@immutable
class GtexToastEntry {
  const GtexToastEntry({
    required this.id,
    required this.title,
    required this.message,
    this.state = GtexSurfaceState.confirmed,
    this.actionLabel,
    this.onAction,
  });

  final String id;
  final String title;
  final String message;
  final GtexSurfaceState state;
  final String? actionLabel;
  final VoidCallback? onAction;
}

class GtexToastHost extends StatelessWidget {
  const GtexToastHost({
    super.key,
    required this.child,
    this.toasts = const <GtexToastEntry>[],
    this.alignment = Alignment.topRight,
  });

  final Widget child;
  final List<GtexToastEntry> toasts;
  final AlignmentGeometry alignment;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: <Widget>[
        child,
        if (toasts.isNotEmpty)
          Align(
            alignment: alignment,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: toasts
                      .map(
                        (GtexToastEntry toast) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _ToastCard(toast: toast),
                        ),
                      )
                      .toList(growable: false),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _ToastCard extends StatelessWidget {
  const _ToastCard({required this.toast});

  final GtexToastEntry toast;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final config = toast.state.config(context);
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 360),
      child: Material(
        color: Colors.transparent,
        child: Container(
          padding: EdgeInsets.all(tokens.spaceMd),
          decoration: BoxDecoration(
            color: tokens.panelStrong,
            borderRadius: BorderRadius.circular(tokens.radiusMedium),
            border: Border.all(
              color: config.accentColor.withValues(alpha: 0.32),
            ),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: tokens.shadow.withValues(alpha: 0.38),
                blurRadius: 26,
                offset: const Offset(0, 16),
              ),
            ],
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(config.icon, color: config.accentColor, size: 20),
              SizedBox(width: tokens.spaceSm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      toast.title,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: tokens.textPrimary,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    SizedBox(height: tokens.spaceXs),
                    Text(
                      toast.message,
                      style: Theme.of(
                        context,
                      ).textTheme.bodySmall?.copyWith(color: tokens.textMuted),
                    ),
                    if (toast.actionLabel != null && toast.onAction != null)
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton(
                          onPressed: toast.onAction,
                          child: Text(toast.actionLabel!),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
