import 'dart:async';
import 'package:flutter/material.dart';

import 'gte_formatters.dart';
import 'gte_shell_theme.dart';
import 'gte_surface_panel.dart';

class GteSyncStatusCard extends StatelessWidget {
  const GteSyncStatusCard({
    super.key,
    required this.title,
    required this.status,
    this.detail,
    this.syncedAt,
    this.accent,
    this.onRefresh,
    this.isRefreshing = false,
  });

  final String title;
  final String status;
  final String? detail;
  final DateTime? syncedAt;
  final Color? accent;
  final FutureOr<void> Function()? onRefresh;
  final bool isRefreshing;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final tokens = GteShellTheme.tokensOf(context);
    final Color resolvedAccent = accent ?? tokens.accent;
    return GteSurfacePanel(
      accentColor: resolvedAccent,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: resolvedAccent.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(Icons.sync, color: resolvedAccent, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: theme.textTheme.titleMedium),
                const SizedBox(height: 3),
                Text(
                  status,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: tokens.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  detail ?? 'Last sync ${gteFormatRelativeTime(syncedAt)}',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          FilledButton.tonalIcon(
            onPressed: isRefreshing || onRefresh == null
                ? null
                : () {
                    onRefresh!.call();
                  },
            icon: isRefreshing
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
            label: Text(isRefreshing ? 'Syncing' : 'Refresh'),
          ),
        ],
      ),
    );
  }
}
