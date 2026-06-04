import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import '../realtime/gtex_realtime_models.dart';
import 'gtex_command_palette.dart';
import 'gtex_live_ticker.dart';
import 'gtex_realtime_widgets.dart';
import 'gtex_state_panel.dart';
import 'gtex_wallet_chip.dart';

class GtexShellTopbar extends StatelessWidget {
  const GtexShellTopbar({
    super.key,
    required this.title,
    required this.contextLine,
    required this.tickerItems,
    required this.commandActions,
    this.searchHint = 'Search players, clubs, traders, payments',
    this.searchState = GtexSurfaceState.confirmed,
    this.livePulseState = GtexSurfaceState.confirmed,
    this.walletBalance,
    this.walletCurrency,
    this.walletState,
    this.walletIsLoading = false,
    this.walletIsBlocked = false,
    this.roleLabel = 'Guest',
    this.roleState = GtexSurfaceState.confirmed,
    this.clubLabel = 'No active club',
    this.clubState = GtexSurfaceState.empty,
    this.connectionLabel = 'Disconnected',
    this.connectionState = GtexSurfaceState.reconnecting,
    this.connectionStatus,
    this.notificationCount = 0,
    this.notificationState = GtexSurfaceState.confirmed,
    this.themeState = GtexSurfaceState.confirmed,
    this.quickActionState = GtexSurfaceState.confirmed,
    this.isSyncing = false,
    this.compact = false,
    this.narrow = false,
    this.onOpenNavigationDrawer,
    this.onOpenIntelligenceRail,
    this.onOpenWallet,
    this.onToggleTheme,
    this.onQuickAction,
    this.onNotifications,
    this.onRoleSwitcher,
    this.onClubSelector,
  });

  final String title;
  final String contextLine;
  final List<String> tickerItems;
  final List<GtexCommandAction> commandActions;
  final String searchHint;
  final GtexSurfaceState searchState;
  final GtexSurfaceState livePulseState;
  final double? walletBalance;
  final String? walletCurrency;
  final GtexSurfaceState? walletState;
  final bool walletIsLoading;
  final bool walletIsBlocked;
  final String roleLabel;
  final GtexSurfaceState roleState;
  final String clubLabel;
  final GtexSurfaceState clubState;
  final String connectionLabel;
  final GtexSurfaceState connectionState;
  final GtexRealtimeStatus? connectionStatus;
  final int notificationCount;
  final GtexSurfaceState notificationState;
  final GtexSurfaceState themeState;
  final GtexSurfaceState quickActionState;
  final bool isSyncing;
  final bool compact;
  final bool narrow;
  final VoidCallback? onOpenNavigationDrawer;
  final VoidCallback? onOpenIntelligenceRail;
  final VoidCallback? onOpenWallet;
  final VoidCallback? onToggleTheme;
  final VoidCallback? onQuickAction;
  final VoidCallback? onNotifications;
  final VoidCallback? onRoleSwitcher;
  final VoidCallback? onClubSelector;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final GtexRealtimeStatus effectiveConnectionStatus =
        connectionStatus ?? _connectionStatusForSurfaceState(connectionState);
    final GtexSurfaceState effectiveWalletState =
        walletState ?? _walletStateFromLegacyFlags();
    return Container(
      padding: EdgeInsets.fromLTRB(compact ? 12 : 16, 10, compact ? 8 : 16, 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.88),
        border: Border(
          bottom: BorderSide(
            color: theme.colorScheme.outline.withValues(alpha: 0.18),
          ),
        ),
      ),
      child: Column(
        children: <Widget>[
          Row(
            children: <Widget>[
              if (onOpenNavigationDrawer != null) ...<Widget>[
                IconButton(
                  tooltip: 'Open navigation drawer',
                  onPressed: onOpenNavigationDrawer,
                  icon: const Icon(Icons.menu_rounded),
                ),
                const SizedBox(width: 2),
              ],
              _BrandMark(tone: theme.colorScheme.primary),
              const SizedBox(width: 12),
              Expanded(
                flex: compact ? 1 : 2,
                child: _TitleBlock(title: title, contextLine: contextLine),
              ),
              if (!compact) ...<Widget>[
                Expanded(
                  flex: 3,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: _SearchButton(
                      commandActions: commandActions,
                      hint: searchHint,
                      state: searchState,
                    ),
                  ),
                ),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: GtexLiveTicker(
                    items: tickerItems,
                    state: livePulseState,
                    isSyncing: isSyncing,
                    accentColor: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 10),
                _PillButton(
                  label: roleLabel,
                  fallbackLabel: 'Role pending',
                  state: roleState,
                  icon: Icons.switch_account_outlined,
                  onPressed: onRoleSwitcher,
                ),
                const SizedBox(width: 8),
                _PillButton(
                  label: clubLabel,
                  fallbackLabel: 'Club pending',
                  state: clubState,
                  icon: Icons.shield_outlined,
                  onPressed: onClubSelector,
                ),
                const SizedBox(width: 8),
                GtexConnectionStatusBadge(
                  status: effectiveConnectionStatus,
                  label: connectionLabel,
                ),
                const SizedBox(width: 8),
                GtexWalletChip(
                  balance: walletBalance,
                  currencyCode: walletCurrency,
                  state: effectiveWalletState,
                  isLoading: walletIsLoading,
                  isBlocked: walletIsBlocked,
                  onTap: onOpenWallet,
                ),
              ],
              if (compact)
                _SearchIconButton(
                  commandActions: commandActions,
                  state: searchState,
                ),
              if (compact && onOpenIntelligenceRail != null)
                IconButton(
                  key: const ValueKey<String>('gtex-shell-intelligence-action'),
                  tooltip: 'Open intelligence rail',
                  onPressed: onOpenIntelligenceRail,
                  icon: const Icon(Icons.auto_awesome_mosaic_outlined),
                ),
              _NotificationButton(
                count: notificationCount,
                state: notificationState,
                onPressed: onNotifications,
              ),
              if (!compact || !narrow) ...<Widget>[
                _TopbarIconButton(
                  tooltip: 'Theme',
                  icon: Icons.contrast_rounded,
                  state: themeState,
                  onPressed: onToggleTheme,
                ),
                _TopbarIconButton(
                  tooltip: 'Quick actions',
                  icon: Icons.bolt_outlined,
                  state: quickActionState,
                  onPressed: onQuickAction,
                ),
              ],
            ],
          ),
          if (compact) ...<Widget>[
            const SizedBox(height: 10),
            Row(
              children: <Widget>[
                Expanded(
                  child: GtexLiveTicker(
                    items: tickerItems,
                    state: livePulseState,
                    isSyncing: isSyncing,
                    accentColor: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 8),
                GtexConnectionStatusBadge(
                  status: effectiveConnectionStatus,
                  label: connectionLabel,
                  compact: true,
                ),
              ],
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: <Widget>[
                  _PillButton(
                    label: roleLabel,
                    fallbackLabel: 'Role pending',
                    state: roleState,
                    icon: Icons.switch_account_outlined,
                    onPressed: onRoleSwitcher,
                  ),
                  const SizedBox(width: 8),
                  _PillButton(
                    label: clubLabel,
                    fallbackLabel: 'Club pending',
                    state: clubState,
                    icon: Icons.shield_outlined,
                    onPressed: onClubSelector,
                  ),
                  const SizedBox(width: 8),
                  GtexWalletChip(
                    balance: walletBalance,
                    currencyCode: walletCurrency,
                    state: effectiveWalletState,
                    isLoading: walletIsLoading,
                    isBlocked: walletIsBlocked,
                    onTap: onOpenWallet,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  GtexSurfaceState _walletStateFromLegacyFlags() {
    if (walletIsBlocked) {
      return GtexSurfaceState.blocked;
    }
    if (walletIsLoading) {
      return GtexSurfaceState.syncing;
    }
    if (walletBalance == null) {
      return GtexSurfaceState.empty;
    }
    return GtexSurfaceState.confirmed;
  }

  GtexRealtimeStatus _connectionStatusForSurfaceState(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.loading:
        return GtexRealtimeStatus.connecting;
      case GtexSurfaceState.empty:
      case GtexSurfaceState.blocked:
        return GtexRealtimeStatus.disconnected;
      case GtexSurfaceState.pending:
      case GtexSurfaceState.syncing:
        return GtexRealtimeStatus.syncing;
      case GtexSurfaceState.reconnecting:
        return GtexRealtimeStatus.reconnecting;
      case GtexSurfaceState.degraded:
        return GtexRealtimeStatus.degraded;
      case GtexSurfaceState.confirmed:
        return GtexRealtimeStatus.live;
      case GtexSurfaceState.error:
        return GtexRealtimeStatus.error;
    }
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark({required this.tone});

  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      height: 38,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.28)),
      ),
      child: Text(
        'G',
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          color: tone,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _TitleBlock extends StatelessWidget {
  const _TitleBlock({required this.title, required this.contextLine});

  final String title;
  final String contextLine;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          _clean(title) ?? 'GTEX',
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w900,
          ),
        ),
        Text(
          _clean(contextLine) ?? 'Operating shell',
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.labelMedium?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.62),
          ),
        ),
      ],
    );
  }
}

class _SearchButton extends StatelessWidget {
  const _SearchButton({
    required this.commandActions,
    required this.hint,
    required this.state,
  });

  final List<GtexCommandAction> commandActions;
  final String hint;
  final GtexSurfaceState state;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = gtexSurfaceToneFor(theme, state);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap:
            () => showGtexCommandPalette(
              context: context,
              actions: commandActions,
              state: state,
            ),
        child: Container(
          height: 38,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest.withValues(
              alpha: 0.38,
            ),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: tone.withValues(alpha: 0.24)),
          ),
          child: Row(
            children: <Widget>[
              Icon(Icons.search_rounded, size: 18, color: tone),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _isConfirmedLike(state)
                      ? (_clean(hint) ?? 'Search commands')
                      : gtexSurfaceTitleFor(state),
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.62),
                  ),
                ),
              ),
              if (!_isConfirmedLike(state))
                GtexSurfaceStateBadge(state: state, compact: true),
            ],
          ),
        ),
      ),
    );
  }
}

class _SearchIconButton extends StatelessWidget {
  const _SearchIconButton({required this.commandActions, required this.state});

  final List<GtexCommandAction> commandActions;
  final GtexSurfaceState state;

  @override
  Widget build(BuildContext context) {
    return _TopbarIconButton(
      tooltip: 'Search',
      icon: Icons.search_rounded,
      state: state,
      onPressed:
          () => showGtexCommandPalette(
            context: context,
            actions: commandActions,
            state: state,
          ),
    );
  }
}

class _PillButton extends StatelessWidget {
  const _PillButton({
    required this.label,
    required this.fallbackLabel,
    required this.state,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final String fallbackLabel;
  final GtexSurfaceState state;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = gtexSurfaceToneFor(theme, state);
    final String resolvedLabel =
        _clean(label) ??
        (_isConfirmedLike(state) ? fallbackLabel : gtexSurfaceTitleFor(state));
    return OutlinedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 16, color: tone),
      label: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 120),
        child: Text(resolvedLabel, overflow: TextOverflow.ellipsis),
      ),
      style: OutlinedButton.styleFrom(
        foregroundColor:
            _isConfirmedLike(state) ? theme.colorScheme.onSurface : tone,
        minimumSize: const Size(0, 38),
        padding: const EdgeInsets.symmetric(horizontal: 10),
        side: BorderSide(color: tone.withValues(alpha: 0.28)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}

class _TopbarIconButton extends StatelessWidget {
  const _TopbarIconButton({
    required this.tooltip,
    required this.icon,
    required this.state,
    required this.onPressed,
  });

  final String tooltip;
  final IconData icon;
  final GtexSurfaceState state;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final Color tone = gtexSurfaceToneFor(Theme.of(context), state);
    return IconButton(
      tooltip:
          _isConfirmedLike(state)
              ? tooltip
              : '$tooltip: ${gtexSurfaceTitleFor(state)}',
      onPressed: onPressed,
      color: _isConfirmedLike(state) ? null : tone,
      icon: Icon(icon),
    );
  }
}

class _NotificationButton extends StatelessWidget {
  const _NotificationButton({
    required this.count,
    required this.state,
    required this.onPressed,
  });

  final int count;
  final GtexSurfaceState state;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final Color tone = gtexSurfaceToneFor(Theme.of(context), state);
    final int safeCount = count < 0 ? 0 : count;
    return Stack(
      alignment: Alignment.center,
      children: <Widget>[
        IconButton(
          tooltip:
              _isConfirmedLike(state)
                  ? 'Notifications'
                  : 'Notifications: ${gtexSurfaceTitleFor(state)}',
          onPressed: onPressed,
          color: _isConfirmedLike(state) ? null : tone,
          icon: const Icon(Icons.notifications_none_rounded),
        ),
        if (safeCount > 0)
          Positioned(
            right: 6,
            top: 6,
            child: IgnorePointer(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.error,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  safeCount > 99 ? '99+' : '$safeCount',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onError,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
          ),
        if (safeCount == 0 && state.requiresAttention)
          Positioned(
            right: 9,
            top: 9,
            child: Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: tone, shape: BoxShape.circle),
            ),
          ),
      ],
    );
  }
}

String? _clean(String? value) {
  final String? trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}

bool _isConfirmedLike(GtexSurfaceState state) {
  return state == GtexSurfaceState.confirmed || state == GtexSurfaceState.data;
}
