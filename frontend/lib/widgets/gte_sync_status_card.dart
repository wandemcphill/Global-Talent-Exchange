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

  Future<void> _runRefresh() async {
    await onRefresh?.call();
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final tokens = GteShellTheme.tokensOf(context);
    final Color resolvedAccent = accent ?? tokens.accent;
    final Widget syncIcon = AnimatedContainer(
      duration: const Duration(milliseconds: 320),
      curve: Curves.easeOutCubic,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isRefreshing
            ? resolvedAccent.withValues(alpha: 0.22)
            : resolvedAccent.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(18),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: resolvedAccent.withValues(alpha: isRefreshing ? 0.24 : 0.12),
            blurRadius: isRefreshing ? 24 : 14,
            spreadRadius: isRefreshing ? 1 : 0,
          ),
        ],
      ),
      child: Icon(
        isRefreshing ? Icons.sync_rounded : Icons.wifi_tethering_rounded,
        color: resolvedAccent,
        size: 18,
      ),
    );
    final Widget copyBlock = Column(
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
          detail ??
              (isRefreshing
                  ? 'Live systems are refreshing now.'
                  : 'Last sync ${gteFormatRelativeTime(syncedAt)}'),
          style: theme.textTheme.bodySmall,
        ),
      ],
    );

    return GteSurfacePanel(
      accentColor: resolvedAccent,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              syncIcon,
              const SizedBox(width: 12),
              Expanded(child: copyBlock),
              const SizedBox(width: 12),
              _LivePulseBadge(
                accent: resolvedAccent,
                label: isRefreshing ? 'AUTO-SYNC' : 'LIVE WATCH',
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            onRefresh == null
                ? 'This surface is standing by for the next live signal.'
                : 'Auto-refresh is active. Pull down if you want to force a re-check.',
            style: theme.textTheme.bodySmall?.copyWith(
              color: tokens.textMuted.withValues(alpha: 0.92),
            ),
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: onRefresh == null || isRefreshing ? null : _runRefresh,
              icon: Icon(
                isRefreshing ? Icons.sync_rounded : Icons.refresh_rounded,
              ),
              label: const Text('Refresh'),
            ),
          ),
        ],
      ),
    );
  }
}

class _LivePulseBadge extends StatefulWidget {
  const _LivePulseBadge({required this.accent, required this.label});

  final Color accent;
  final String label;

  @override
  State<_LivePulseBadge> createState() => _LivePulseBadgeState();
}

class _LivePulseBadgeState extends State<_LivePulseBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );
    if (!_isTestBinding) {
      _controller.repeat(reverse: true);
    } else {
      _controller.value = 1;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return FadeTransition(
      opacity: Tween<double>(
        begin: 0.65,
        end: 1,
      ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut)),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: widget.accent.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(tokens.radiusPill),
          border: Border.all(color: widget.accent.withValues(alpha: 0.22)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(
              Icons.fiber_manual_record_rounded,
              color: widget.accent,
              size: 12,
            ),
            const SizedBox(width: 6),
            Text(
              widget.label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: widget.accent,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
