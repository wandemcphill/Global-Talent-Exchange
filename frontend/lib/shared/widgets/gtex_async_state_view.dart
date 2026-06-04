import 'package:flutter/material.dart';

import '../../theme/gte_theme_tokens.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../state/gtex_async_surface_state.dart';

class GtexAsyncStateView extends StatelessWidget {
  const GtexAsyncStateView({
    super.key,
    required this.state,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  });

  const GtexAsyncStateView.loading({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.loading;

  const GtexAsyncStateView.empty({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.empty;

  const GtexAsyncStateView.blocked({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.blocked;

  const GtexAsyncStateView.pending({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.pending;

  const GtexAsyncStateView.syncing({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.syncing;

  const GtexAsyncStateView.reconnecting({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.reconnecting;

  const GtexAsyncStateView.degraded({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.degraded;

  const GtexAsyncStateView.confirmed({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.confirmed;

  const GtexAsyncStateView.error({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.error;

  const GtexAsyncStateView.data({
    super.key,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  }) : state = GtexAsyncSurfaceState.data;

  final GtexAsyncSurfaceState state;
  final String? title;
  final String? message;
  final String? eyebrow;
  final String? actionLabel;
  final VoidCallback? onAction;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent = _accentFor(state, tokens);
    final String resolvedTitle = title ?? state.title;
    final String resolvedMessage = message ?? state.message;
    final String resolvedEyebrow = eyebrow ?? state.eyebrow;

    if (compact) {
      return _GtexCompactAsyncStateView(
        state: state,
        title: resolvedTitle,
        message: resolvedMessage,
        eyebrow: resolvedEyebrow,
        accent: accent,
        actionLabel: actionLabel,
        onAction: onAction,
      );
    }

    return Semantics(
      container: true,
      label: '${state.label}: $resolvedTitle. $resolvedMessage',
      child: GteStatePanel(
        title: resolvedTitle,
        message: resolvedMessage,
        eyebrow: resolvedEyebrow,
        icon: state.showsProgress ? null : state.icon,
        isLoading: state.showsProgress,
        accentColor: accent,
        actionLabel: actionLabel,
        onAction: onAction,
      ),
    );
  }
}

class _GtexCompactAsyncStateView extends StatelessWidget {
  const _GtexCompactAsyncStateView({
    required this.state,
    required this.title,
    required this.message,
    required this.eyebrow,
    required this.accent,
    required this.actionLabel,
    required this.onAction,
  });

  final GtexAsyncSurfaceState state;
  final String title;
  final String message;
  final String eyebrow;
  final Color accent;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final TextTheme textTheme = Theme.of(context).textTheme;

    return Semantics(
      container: true,
      label: '${state.label}: $title. $message',
      child: Container(
        padding: EdgeInsets.all(tokens.spaceMd),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(tokens.radiusMedium),
          border: Border.all(color: accent.withValues(alpha: 0.24)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            SizedBox(
              width: 28,
              height: 28,
              child:
                  state.showsProgress
                      ? CircularProgressIndicator(
                        strokeWidth: 2.4,
                        valueColor: AlwaysStoppedAnimation<Color>(accent),
                      )
                      : Icon(state.icon, color: accent, size: 24),
            ),
            SizedBox(width: tokens.spaceSm),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    eyebrow,
                    style: textTheme.labelMedium?.copyWith(
                      color: accent,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  SizedBox(height: tokens.spaceXs),
                  Text(title, style: textTheme.titleMedium),
                  SizedBox(height: tokens.spaceXs),
                  Text(
                    message,
                    style: textTheme.bodySmall?.copyWith(
                      color: tokens.textMuted,
                      height: 1.35,
                    ),
                  ),
                  if (actionLabel != null && onAction != null) ...<Widget>[
                    SizedBox(height: tokens.spaceSm),
                    TextButton.icon(
                      onPressed: onAction,
                      icon: const Icon(Icons.arrow_forward_rounded),
                      label: Text(actionLabel!),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Color _accentFor(GtexAsyncSurfaceState state, GteThemeTokens tokens) {
  return switch (state) {
    GtexAsyncSurfaceState.loading => tokens.accent,
    GtexAsyncSurfaceState.empty => tokens.textMuted,
    GtexAsyncSurfaceState.blocked => tokens.negative,
    GtexAsyncSurfaceState.pending => tokens.warning,
    GtexAsyncSurfaceState.syncing => tokens.accentWarm,
    GtexAsyncSurfaceState.reconnecting => tokens.accentClub,
    GtexAsyncSurfaceState.degraded => tokens.warning,
    GtexAsyncSurfaceState.confirmed => tokens.positive,
    GtexAsyncSurfaceState.error => tokens.negative,
    GtexAsyncSurfaceState.data => tokens.accent,
  };
}
