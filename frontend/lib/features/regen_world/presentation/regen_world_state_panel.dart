import 'package:flutter/material.dart';

import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_shell_theme.dart';

enum RegenWorldSurfaceState { loading, empty, degraded, blocked, error }

class RegenWorldStatePanel extends StatelessWidget {
  const RegenWorldStatePanel({
    super.key,
    required this.state,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final RegenWorldSurfaceState state;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  factory RegenWorldStatePanel.loading() {
    return const RegenWorldStatePanel(
      state: RegenWorldSurfaceState.loading,
      title: 'Syncing Regen World',
      message:
          'Loading lineage, traits, DNA, generation, rarity, and value from backend feeds.',
    );
  }

  factory RegenWorldStatePanel.empty({VoidCallback? onAction}) {
    return RegenWorldStatePanel(
      state: RegenWorldSurfaceState.empty,
      title: 'No backend regens published',
      message:
          'Regen World has no backend player records to display for the current filters.',
      actionLabel: onAction == null ? null : 'Show all',
      onAction: onAction,
    );
  }

  factory RegenWorldStatePanel.degraded({
    required String message,
    VoidCallback? onAction,
  }) {
    return RegenWorldStatePanel(
      state: RegenWorldSurfaceState.degraded,
      title: 'Backend truth degraded',
      message: message,
      actionLabel: onAction == null ? null : 'Show published fields',
      onAction: onAction,
    );
  }

  factory RegenWorldStatePanel.blocked({
    required String message,
    VoidCallback? onAction,
  }) {
    return RegenWorldStatePanel(
      state: RegenWorldSurfaceState.blocked,
      title: 'Backend truth blocked',
      message: message,
      actionLabel: onAction == null ? null : 'Refresh',
      onAction: onAction,
    );
  }

  factory RegenWorldStatePanel.error({
    required String message,
    VoidCallback? onAction,
  }) {
    return RegenWorldStatePanel(
      state: RegenWorldSurfaceState.error,
      title: 'Regen World is blocked',
      message: message,
      actionLabel: onAction == null ? null : 'Retry',
      onAction: onAction,
    );
  }

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final _StateVisual visual = _visualFor(context);
    return GteStatePanel(
      eyebrow: visual.eyebrow,
      title: title,
      message: message,
      actionLabel: actionLabel,
      onAction: onAction,
      icon: visual.icon,
      accentColor: visual.color ?? tokens.accent,
      isLoading: state == RegenWorldSurfaceState.loading,
    );
  }

  _StateVisual _visualFor(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    switch (state) {
      case RegenWorldSurfaceState.loading:
        return _StateVisual(
          eyebrow: 'REGEN WORLD',
          icon: Icons.sync_rounded,
          color: tokens.accent,
        );
      case RegenWorldSurfaceState.empty:
        return _StateVisual(
          eyebrow: 'NO RECORDS',
          icon: Icons.search_off_rounded,
          color: tokens.textMuted,
        );
      case RegenWorldSurfaceState.degraded:
        return _StateVisual(
          eyebrow: 'DEGRADED',
          icon: Icons.sync_problem_rounded,
          color: tokens.warning,
        );
      case RegenWorldSurfaceState.blocked:
        return _StateVisual(
          eyebrow: 'BLOCKED',
          icon: Icons.lock_rounded,
          color: tokens.negative,
        );
      case RegenWorldSurfaceState.error:
        return _StateVisual(
          eyebrow: 'ERROR',
          icon: Icons.warning_amber_rounded,
          color: tokens.negative,
        );
    }
  }
}

class _StateVisual {
  const _StateVisual({
    required this.eyebrow,
    required this.icon,
    required this.color,
  });

  final String eyebrow;
  final IconData icon;
  final Color? color;
}
