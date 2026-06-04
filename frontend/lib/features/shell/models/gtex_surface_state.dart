import 'package:flutter/material.dart';

import '../../../widgets/gte_shell_theme.dart';
import '../domain/gtex_surface_state.dart';

export '../domain/gtex_surface_state.dart';

@immutable
class GtexSurfaceStateConfig {
  const GtexSurfaceStateConfig({
    required this.eyebrow,
    required this.title,
    required this.message,
    required this.icon,
    required this.accentColor,
    this.actionLabel,
  });

  final String eyebrow;
  final String title;
  final String message;
  final IconData icon;
  final Color accentColor;
  final String? actionLabel;
}

extension GtexSurfaceStateConfigX on GtexSurfaceState {
  bool get isProgressState {
    return switch (this) {
      GtexSurfaceState.loading ||
      GtexSurfaceState.pending ||
      GtexSurfaceState.syncing ||
      GtexSurfaceState.reconnecting => true,
      _ => false,
    };
  }

  GtexSurfaceStateConfig config(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return switch (this) {
      GtexSurfaceState.loading => GtexSurfaceStateConfig(
        eyebrow: 'LOADING',
        title: 'Loading football intelligence',
        message:
            'GTEX is preparing the latest operating state for this surface.',
        icon: Icons.sync,
        accentColor: tokens.accentClub,
      ),
      GtexSurfaceState.empty => GtexSurfaceStateConfig(
        eyebrow: 'EMPTY',
        title: 'No active football signal yet',
        message:
            'This surface is ready, but there is no backend record to show.',
        icon: Icons.inbox_outlined,
        accentColor: tokens.textMuted,
      ),
      GtexSurfaceState.blocked => GtexSurfaceStateConfig(
        eyebrow: 'BLOCKED',
        title: 'Action is blocked',
        message:
            'Resolve the listed requirement before this workflow can continue.',
        icon: Icons.lock_outline,
        accentColor: tokens.warning,
      ),
      GtexSurfaceState.pending => GtexSurfaceStateConfig(
        eyebrow: 'PENDING',
        title: 'Waiting for confirmation',
        message:
            'The request is queued and awaiting a confirmed operational result.',
        icon: Icons.hourglass_top,
        accentColor: tokens.accentCapital,
      ),
      GtexSurfaceState.syncing => GtexSurfaceStateConfig(
        eyebrow: 'SYNCING',
        title: 'Syncing live state',
        message: 'Recent football economy changes are being reconciled.',
        icon: Icons.cloud_sync_outlined,
        accentColor: tokens.accent,
      ),
      GtexSurfaceState.reconnecting => GtexSurfaceStateConfig(
        eyebrow: 'RECONNECTING',
        title: 'Reconnecting live channel',
        message:
            'The realtime feed is reconnecting without losing the current view.',
        icon: Icons.wifi_tethering_error_rounded,
        accentColor: tokens.accentWarm,
      ),
      GtexSurfaceState.degraded => GtexSurfaceStateConfig(
        eyebrow: 'DEGRADED',
        title: 'Live confidence is reduced',
        message:
            'Some realtime signals are delayed. Confirm critical actions before acting.',
        icon: Icons.signal_wifi_statusbar_connected_no_internet_4,
        accentColor: tokens.warning,
      ),
      GtexSurfaceState.confirmed => GtexSurfaceStateConfig(
        eyebrow: 'CONFIRMED',
        title: 'Confirmed',
        message: 'The backend has confirmed this operating state.',
        icon: Icons.verified_outlined,
        accentColor: tokens.positive,
      ),
      GtexSurfaceState.error => GtexSurfaceStateConfig(
        eyebrow: 'ERROR',
        title: 'Surface failed to load',
        message:
            'The latest backend truth could not be loaded for this surface.',
        icon: Icons.error_outline,
        accentColor: tokens.negative,
        actionLabel: 'Retry',
      ),
    };
  }
}
