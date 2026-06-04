import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import 'gtex_state_panel.dart';

class GtexAsyncSurface extends StatelessWidget {
  const GtexAsyncSurface({
    super.key,
    required this.state,
    required this.child,
    this.title,
    this.message,
    this.eyebrow,
    this.actionLabel,
    this.onAction,
    this.icon,
    this.accentColor,
    this.showConfirmedPanel = false,
  });

  final GtexSurfaceState state;
  final Widget child;
  final String? eyebrow;
  final String? title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData? icon;
  final Color? accentColor;
  final bool showConfirmedPanel;

  @override
  Widget build(BuildContext context) {
    if ((state == GtexSurfaceState.confirmed ||
            state == GtexSurfaceState.data) &&
        !showConfirmedPanel) {
      return child;
    }
    if ((state == GtexSurfaceState.confirmed ||
            state == GtexSurfaceState.data) &&
        showConfirmedPanel) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          GtexStatePanel(
            state: state,
            eyebrow: eyebrow,
            title: title ?? 'Confirmed',
            message: message ?? 'This surface is confirmed by the live system.',
            actionLabel: actionLabel,
            onAction: onAction,
            icon: icon,
            accentColor: accentColor,
          ),
          const SizedBox(height: 16),
          Expanded(child: child),
        ],
      );
    }
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: GtexStatePanel(
          state: state,
          eyebrow: eyebrow ?? _eyebrowFor(state),
          title: title ?? _titleFor(state),
          message: message ?? _messageFor(state),
          actionLabel: actionLabel,
          onAction: onAction,
          icon: icon,
          accentColor: accentColor,
        ),
      ),
    );
  }

  String _eyebrowFor(GtexSurfaceState state) => state.name.toUpperCase();

  String _titleFor(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.loading:
        return 'Loading surface';
      case GtexSurfaceState.empty:
        return 'No records yet';
      case GtexSurfaceState.blocked:
        return 'Action blocked';
      case GtexSurfaceState.pending:
        return 'Waiting for confirmation';
      case GtexSurfaceState.syncing:
        return 'Syncing live data';
      case GtexSurfaceState.reconnecting:
        return 'Reconnecting';
      case GtexSurfaceState.degraded:
        return 'Surface degraded';
      case GtexSurfaceState.confirmed:
        return 'Confirmed';
      case GtexSurfaceState.error:
        return 'Unable to load surface';
    }
  }

  String _messageFor(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.loading:
        return 'GTEX is preparing the latest confirmed view.';
      case GtexSurfaceState.empty:
        return 'There is no backend-derived data to show for this surface yet.';
      case GtexSurfaceState.blocked:
        return 'This action needs an eligible role, club, payment state, or review before it can continue.';
      case GtexSurfaceState.pending:
        return 'The request has been submitted and is waiting for the next system event.';
      case GtexSurfaceState.syncing:
        return 'Live data is being reconciled with the backend.';
      case GtexSurfaceState.reconnecting:
        return 'Realtime activity is reconnecting. Confirmed records remain visible.';
      case GtexSurfaceState.degraded:
        return 'The latest confirmed snapshot is visible while one or more feeds recover.';
      case GtexSurfaceState.confirmed:
        return 'This view is confirmed by the live system.';
      case GtexSurfaceState.error:
        return 'The platform could not load this surface. Retry when the service is reachable.';
    }
  }
}
