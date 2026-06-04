import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import 'gtex_state_panel.dart';

class GtexLiveTicker extends StatelessWidget {
  const GtexLiveTicker({
    super.key,
    required this.items,
    this.label = 'Live pulse',
    this.state = GtexSurfaceState.confirmed,
    this.accentColor,
    this.isSyncing = false,
  });

  final List<String> items;
  final String label;
  final GtexSurfaceState state;
  final Color? accentColor;
  final bool isSyncing;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final GtexSurfaceState effectiveState =
        isSyncing && _isConfirmedLike(state) ? GtexSurfaceState.syncing : state;
    final Color tone = accentColor ?? gtexSurfaceToneFor(theme, effectiveState);
    final List<String> visibleItems =
        items.where((String item) => item.trim().isNotEmpty).toList();
    return Semantics(
      liveRegion: effectiveState.requiresAttention || visibleItems.isNotEmpty,
      label: '$label ${_emptyLabel(effectiveState, isSyncing)}',
      child: Container(
        height: 38,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface.withValues(alpha: 0.72),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: tone.withValues(alpha: 0.24)),
        ),
        child: Row(
          children: <Widget>[
            Icon(_iconFor(effectiveState), size: 16, color: tone),
            const SizedBox(width: 8),
            Text(
              label.toUpperCase(),
              style: theme.textTheme.labelSmall?.copyWith(
                color: tone,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child:
                  visibleItems.isEmpty
                      ? Text(
                        _emptyLabel(effectiveState, isSyncing),
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: theme.colorScheme.onSurface.withValues(
                            alpha: 0.64,
                          ),
                        ),
                      )
                      : SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: visibleItems
                              .map(
                                (String item) => Padding(
                                  padding: const EdgeInsets.only(right: 18),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: <Widget>[
                                      Container(
                                        width: 5,
                                        height: 5,
                                        decoration: BoxDecoration(
                                          color: tone,
                                          shape: BoxShape.circle,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Text(
                                        item,
                                        style: theme.textTheme.labelMedium
                                            ?.copyWith(
                                              fontWeight: FontWeight.w700,
                                            ),
                                      ),
                                    ],
                                  ),
                                ),
                              )
                              .toList(growable: false),
                        ),
                      ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _iconFor(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.confirmed:
        return Icons.monitor_heart_outlined;
      case GtexSurfaceState.loading:
      case GtexSurfaceState.syncing:
        return Icons.sync_rounded;
      case GtexSurfaceState.empty:
        return Icons.monitor_heart_outlined;
      case GtexSurfaceState.blocked:
      case GtexSurfaceState.pending:
      case GtexSurfaceState.reconnecting:
      case GtexSurfaceState.degraded:
      case GtexSurfaceState.error:
        return gtexSurfaceIconFor(state);
    }
  }

  String _emptyLabel(GtexSurfaceState state, bool isSyncing) {
    if (isSyncing && state == GtexSurfaceState.syncing) {
      return 'Syncing ecosystem pulse';
    }
    switch (state) {
      case GtexSurfaceState.loading:
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.reconnecting:
        return 'Syncing ecosystem pulse';
      case GtexSurfaceState.empty:
      case GtexSurfaceState.confirmed:
        return 'No live pulse';
      case GtexSurfaceState.blocked:
        return 'Live pulse blocked';
      case GtexSurfaceState.pending:
        return 'Live pulse pending';
      case GtexSurfaceState.degraded:
        return 'Live pulse degraded';
      case GtexSurfaceState.error:
        return 'Live pulse error';
    }
  }
}

bool _isConfirmedLike(GtexSurfaceState state) {
  return state == GtexSurfaceState.confirmed || state == GtexSurfaceState.data;
}
