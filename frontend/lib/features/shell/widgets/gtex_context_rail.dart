import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import 'gtex_entity_surface.dart';
import 'gtex_state_panel.dart';

class GtexContextRailItem {
  const GtexContextRailItem({
    required this.id,
    required this.eyebrow,
    required this.title,
    required this.state,
    required this.icon,
    this.detail,
    this.metrics = const <GtexEntityMetric>[],
    this.actions = const <GtexEntityAction>[],
    this.onTap,
  });

  final String id;
  final String eyebrow;
  final String title;
  final String? detail;
  final GtexSurfaceState state;
  final IconData icon;
  final List<GtexEntityMetric> metrics;
  final List<GtexEntityAction> actions;
  final VoidCallback? onTap;
}

class GtexContextRail extends StatelessWidget {
  const GtexContextRail({
    super.key,
    required this.items,
    this.title = 'Context',
    this.accentColor,
    this.width = 320,
    this.state = GtexSurfaceState.confirmed,
    this.stateMessage,
    this.actionLabel,
    this.onAction,
    this.emptyState = GtexSurfaceState.empty,
    this.emptyTitle,
    this.emptyMessage,
  });

  final List<GtexContextRailItem> items;
  final String title;
  final Color? accentColor;
  final double? width;
  final GtexSurfaceState state;
  final String? stateMessage;
  final String? actionLabel;
  final VoidCallback? onAction;
  final GtexSurfaceState emptyState;
  final String? emptyTitle;
  final String? emptyMessage;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = accentColor ?? theme.colorScheme.primary;
    return Container(
      width: width,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.72),
        border: Border(
          left: BorderSide(
            color: theme.colorScheme.outline.withValues(alpha: 0.22),
          ),
        ),
      ),
      child: SafeArea(
        left: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(
                    Icons.auto_awesome_mosaic_outlined,
                    size: 18,
                    color: tone,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    title.toUpperCase(),
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: tone,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              if (items.isNotEmpty && !_isConfirmedLike(state)) ...<Widget>[
                GtexStateBanner(
                  state: state,
                  title: gtexSurfaceTitleFor(state),
                  message: stateMessage ?? gtexSurfaceMessageFor(state),
                  actionLabel: actionLabel,
                  onAction: onAction,
                  dense: true,
                  accentColor: tone,
                ),
                const SizedBox(height: 12),
              ],
              Expanded(
                child:
                    items.isEmpty
                        ? _EmptyContextRail(
                          tone: tone,
                          state: _isConfirmedLike(state) ? emptyState : state,
                          title: emptyTitle,
                          message: emptyMessage,
                          actionLabel: actionLabel,
                          onAction: onAction,
                        )
                        : ListView.separated(
                          itemCount: items.length,
                          separatorBuilder:
                              (BuildContext context, int index) =>
                                  const SizedBox(height: 10),
                          itemBuilder:
                              (BuildContext context, int index) =>
                                  _ContextRailTile(item: items[index]),
                        ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

bool _isConfirmedLike(GtexSurfaceState state) {
  return state == GtexSurfaceState.confirmed || state == GtexSurfaceState.data;
}

class _EmptyContextRail extends StatelessWidget {
  const _EmptyContextRail({
    required this.tone,
    required this.state,
    required this.title,
    required this.message,
    required this.actionLabel,
    required this.onAction,
  });

  final Color tone;
  final GtexSurfaceState state;
  final String? title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Center(
        child: GtexStatePanel(
          state: state,
          eyebrow: 'CONTEXT',
          title: title ?? _ContextRailTile._titleFor(state),
          message: message ?? _ContextRailTile._messageFor(state),
          icon: state == GtexSurfaceState.empty ? Icons.inbox_outlined : null,
          actionLabel: actionLabel,
          onAction: onAction,
          accentColor: tone,
        ),
      ),
    );
  }
}

class _ContextRailTile extends StatelessWidget {
  const _ContextRailTile({required this.item});

  final GtexContextRailItem item;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = _toneFor(theme, item.state);
    final String eyebrow = _clean(item.eyebrow) ?? item.state.name;
    final String title = _clean(item.title) ?? _titleFor(item.state);
    final String detail = _clean(item.detail) ?? _messageFor(item.state);
    return GtexEntitySurface(
      state: item.state,
      eyebrow: eyebrow,
      title: title,
      subtitle: detail,
      icon: item.icon,
      metrics: item.metrics,
      actions: item.actions,
      onTap: item.onTap,
      accentColor: tone,
      dense: true,
    );
  }

  static String _titleFor(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.loading:
        return 'Loading context';
      case GtexSurfaceState.empty:
        return 'No backend record';
      case GtexSurfaceState.blocked:
        return 'Context blocked';
      case GtexSurfaceState.pending:
        return 'Awaiting confirmation';
      case GtexSurfaceState.syncing:
        return 'Syncing context';
      case GtexSurfaceState.reconnecting:
        return 'Realtime reconnecting';
      case GtexSurfaceState.degraded:
        return 'Context degraded';
      case GtexSurfaceState.confirmed:
        return 'Context confirmed';
      case GtexSurfaceState.error:
        return 'Context failed';
    }
  }

  static String _messageFor(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.loading:
        return 'GTEX is loading this context from the backend.';
      case GtexSurfaceState.empty:
        return 'No confirmed record is available for this context yet.';
      case GtexSurfaceState.blocked:
        return 'This context requires an eligible account, role, or club scope.';
      case GtexSurfaceState.pending:
        return 'This context is waiting for the next confirmed backend event.';
      case GtexSurfaceState.syncing:
        return 'Recent backend changes are being reconciled.';
      case GtexSurfaceState.reconnecting:
        return 'Realtime context is reconnecting while confirmed data stays visible.';
      case GtexSurfaceState.degraded:
        return 'The last confirmed context remains visible while the feed recovers.';
      case GtexSurfaceState.confirmed:
        return 'The backend has confirmed this context.';
      case GtexSurfaceState.error:
        return 'GTEX could not load the latest context.';
    }
  }

  static Color _toneFor(ThemeData theme, GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.blocked:
      case GtexSurfaceState.error:
        return theme.colorScheme.error;
      case GtexSurfaceState.degraded:
      case GtexSurfaceState.pending:
      case GtexSurfaceState.empty:
        return const Color(0xFFFFD75B);
      case GtexSurfaceState.confirmed:
        return const Color(0xFF69F3A4);
      case GtexSurfaceState.loading:
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.reconnecting:
        return theme.colorScheme.primary;
    }
  }
}

String? _clean(String? value) {
  final String? trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}
