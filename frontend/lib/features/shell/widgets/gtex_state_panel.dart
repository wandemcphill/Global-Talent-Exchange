import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';

class GtexStatePanel extends StatelessWidget {
  const GtexStatePanel({
    super.key,
    required this.state,
    required this.title,
    required this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.secondaryActionLabel,
    this.onSecondaryAction,
    this.icon,
    this.accentColor,
  });

  final GtexSurfaceState state;
  final String? eyebrow;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final String? secondaryActionLabel;
  final VoidCallback? onSecondaryAction;
  final IconData? icon;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = accentColor ?? gtexSurfaceToneFor(theme, state);
    final ColorScheme scheme = theme.colorScheme;
    return Semantics(
      liveRegion: state.requiresAttention,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 720),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Color.alphaBlend(
            tone.withValues(alpha: 0.05),
            scheme.surface.withValues(alpha: 0.94),
          ),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: tone.withValues(alpha: 0.26)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              width: 42,
              height: 42,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: tone.withValues(alpha: 0.13),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: tone.withValues(alpha: 0.24)),
              ),
              child: _StateIcon(state: state, icon: icon, tone: tone),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  if (eyebrow != null && eyebrow!.trim().isNotEmpty) ...[
                    Text(
                      eyebrow!.toUpperCase(),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: tone,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0,
                      ),
                    ),
                    const SizedBox(height: 6),
                  ],
                  Text(
                    title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    message,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: scheme.onSurface.withValues(alpha: 0.72),
                      height: 1.35,
                    ),
                  ),
                  if (actionLabel != null || secondaryActionLabel != null) ...[
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        if (actionLabel != null)
                          FilledButton(
                            onPressed: onAction,
                            child: Text(actionLabel!),
                          ),
                        if (secondaryActionLabel != null)
                          OutlinedButton(
                            onPressed: onSecondaryAction,
                            child: Text(secondaryActionLabel!),
                          ),
                      ],
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

class GtexStateBanner extends StatelessWidget {
  const GtexStateBanner({
    super.key,
    required this.state,
    this.title,
    this.message,
    this.actionLabel,
    this.onAction,
    this.icon,
    this.accentColor,
    this.dense = false,
  });

  final GtexSurfaceState state;
  final String? title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData? icon;
  final Color? accentColor;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = accentColor ?? gtexSurfaceToneFor(theme, state);
    final String resolvedTitle = _clean(title) ?? gtexSurfaceTitleFor(state);
    final String? resolvedMessage = _clean(message);
    return Semantics(
      liveRegion: state.requiresAttention,
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: dense ? 10 : 12,
          vertical: dense ? 8 : 10,
        ),
        decoration: BoxDecoration(
          color: tone.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: tone.withValues(alpha: 0.22)),
        ),
        child: Row(
          children: <Widget>[
            Icon(icon ?? gtexSurfaceIconFor(state), color: tone, size: 18),
            SizedBox(width: dense ? 8 : 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    resolvedTitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: tone,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                  ),
                  if (resolvedMessage != null) ...<Widget>[
                    const SizedBox(height: 3),
                    Text(
                      resolvedMessage,
                      maxLines: dense ? 1 : 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(
                          alpha: 0.70,
                        ),
                        height: 1.25,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (actionLabel != null) ...<Widget>[
              const SizedBox(width: 10),
              TextButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

class GtexSurfaceStateBadge extends StatelessWidget {
  const GtexSurfaceStateBadge({
    super.key,
    required this.state,
    this.label,
    this.compact = false,
    this.accentColor,
  });

  final GtexSurfaceState state;
  final String? label;
  final bool compact;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = accentColor ?? gtexSurfaceToneFor(theme, state);
    final String resolvedLabel = _clean(label) ?? state.name.toUpperCase();
    return Tooltip(
      message: resolvedLabel,
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? 7 : 8,
          vertical: compact ? 4 : 5,
        ),
        decoration: BoxDecoration(
          color: tone.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: tone.withValues(alpha: 0.22)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(gtexSurfaceIconFor(state), color: tone, size: 13),
            if (!compact) ...<Widget>[
              const SizedBox(width: 5),
              Text(
                resolvedLabel,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: tone,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StateIcon extends StatelessWidget {
  const _StateIcon({
    required this.state,
    required this.icon,
    required this.tone,
  });

  final GtexSurfaceState state;
  final IconData? icon;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    if (state == GtexSurfaceState.loading ||
        state == GtexSurfaceState.syncing ||
        state == GtexSurfaceState.reconnecting) {
      return SizedBox(
        width: 18,
        height: 18,
        child: CircularProgressIndicator(strokeWidth: 2.2, color: tone),
      );
    }
    return Icon(icon ?? gtexSurfaceIconFor(state), color: tone, size: 22);
  }
}

Color gtexSurfaceToneFor(ThemeData theme, GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
    case GtexSurfaceState.syncing:
    case GtexSurfaceState.reconnecting:
      return theme.colorScheme.primary;
    case GtexSurfaceState.empty:
    case GtexSurfaceState.pending:
      return const Color(0xFFFFD75B);
    case GtexSurfaceState.blocked:
    case GtexSurfaceState.error:
      return theme.colorScheme.error;
    case GtexSurfaceState.degraded:
      return const Color(0xFFFFB35C);
    case GtexSurfaceState.confirmed:
      return const Color(0xFF69F3A4);
  }
}

IconData gtexSurfaceIconFor(GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
      return Icons.hourglass_empty_rounded;
    case GtexSurfaceState.empty:
      return Icons.inbox_outlined;
    case GtexSurfaceState.blocked:
      return Icons.lock_outline_rounded;
    case GtexSurfaceState.pending:
      return Icons.pending_actions_outlined;
    case GtexSurfaceState.syncing:
      return Icons.sync_rounded;
    case GtexSurfaceState.reconnecting:
      return Icons.wifi_find_rounded;
    case GtexSurfaceState.degraded:
      return Icons.warning_amber_rounded;
    case GtexSurfaceState.confirmed:
      return Icons.verified_outlined;
    case GtexSurfaceState.error:
      return Icons.error_outline_rounded;
  }
}

String gtexSurfaceTitleFor(GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
      return 'Loading';
    case GtexSurfaceState.empty:
      return 'No data';
    case GtexSurfaceState.blocked:
      return 'Blocked';
    case GtexSurfaceState.pending:
      return 'Pending confirmation';
    case GtexSurfaceState.syncing:
      return 'Syncing';
    case GtexSurfaceState.reconnecting:
      return 'Reconnecting';
    case GtexSurfaceState.degraded:
      return 'Degraded';
    case GtexSurfaceState.confirmed:
      return 'Confirmed';
    case GtexSurfaceState.error:
      return 'Unable to load';
  }
}

String gtexSurfaceMessageFor(GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
      return 'GTEX is preparing the latest confirmed view.';
    case GtexSurfaceState.empty:
      return 'No confirmed backend record is available for this surface yet.';
    case GtexSurfaceState.blocked:
      return 'This surface needs an eligible role, club, or account state.';
    case GtexSurfaceState.pending:
      return 'This surface is waiting for the next confirmed backend event.';
    case GtexSurfaceState.syncing:
      return 'Recent backend changes are being reconciled.';
    case GtexSurfaceState.reconnecting:
      return 'Realtime transport is reconnecting while confirmed data remains visible.';
    case GtexSurfaceState.degraded:
      return 'The last confirmed snapshot remains visible while a feed recovers.';
    case GtexSurfaceState.confirmed:
      return 'The backend has confirmed this surface.';
    case GtexSurfaceState.error:
      return 'GTEX could not load the latest surface data.';
  }
}

String? _clean(String? value) {
  final String? trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}
