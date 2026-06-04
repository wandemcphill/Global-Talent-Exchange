import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import '../realtime/gtex_realtime_models.dart';
import 'gtex_command_palette.dart';
import 'gtex_context_rail.dart';
import 'gtex_drawer_host.dart';
import 'gtex_live_ticker.dart';
import 'gtex_modal_host.dart';
import 'gtex_realtime_widgets.dart';
import 'gtex_shell_topbar.dart';
import 'gtex_state_panel.dart';
import 'gtex_toast_host.dart';
import 'gtex_wallet_chip.dart';

class GtexShellDestination {
  const GtexShellDestination({
    required this.id,
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.tone,
    this.isEnabled = true,
  });

  final String id;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final Color tone;
  final bool isEnabled;
}

class GtexOperatingShell extends StatefulWidget {
  const GtexOperatingShell({
    super.key,
    required this.destinations,
    required this.activeDestinationId,
    required this.onDestinationSelected,
    required this.body,
    required this.title,
    required this.contextLine,
    required this.tickerItems,
    required this.contextItems,
    required this.commandActions,
    this.walletBalance,
    this.walletCurrency,
    this.searchState,
    this.livePulseState,
    this.walletState,
    this.roleState,
    this.clubState,
    this.notificationState,
    this.themeState,
    this.quickActionState,
    this.walletIsLoading = false,
    this.walletIsBlocked = false,
    this.roleLabel = 'Guest',
    this.clubLabel = 'No active club',
    this.connectionLabel = 'Disconnected',
    this.connectionState = GtexSurfaceState.reconnecting,
    this.connectionStatus,
    this.notificationCount = 0,
    this.isSyncing = false,
    this.onOpenWallet,
    this.onToggleTheme,
    this.onQuickAction,
    this.onNotifications,
    this.onRoleSwitcher,
    this.onClubSelector,
  });

  final List<GtexShellDestination> destinations;
  final String activeDestinationId;
  final ValueChanged<String> onDestinationSelected;
  final Widget body;
  final String title;
  final String contextLine;
  final List<String> tickerItems;
  final List<GtexContextRailItem> contextItems;
  final List<GtexCommandAction> commandActions;
  final double? walletBalance;
  final String? walletCurrency;
  final GtexSurfaceState? searchState;
  final GtexSurfaceState? livePulseState;
  final GtexSurfaceState? walletState;
  final GtexSurfaceState? roleState;
  final GtexSurfaceState? clubState;
  final GtexSurfaceState? notificationState;
  final GtexSurfaceState? themeState;
  final GtexSurfaceState? quickActionState;
  final bool walletIsLoading;
  final bool walletIsBlocked;
  final String roleLabel;
  final String clubLabel;
  final String connectionLabel;
  final GtexSurfaceState connectionState;
  final GtexRealtimeStatus? connectionStatus;
  final int notificationCount;
  final bool isSyncing;
  final VoidCallback? onOpenWallet;
  final VoidCallback? onToggleTheme;
  final VoidCallback? onQuickAction;
  final VoidCallback? onNotifications;
  final VoidCallback? onRoleSwitcher;
  final VoidCallback? onClubSelector;

  @override
  State<GtexOperatingShell> createState() => _GtexOperatingShellState();
}

enum _AdaptiveDrawer { navigation, intelligence }

class _GtexOperatingShellState extends State<GtexOperatingShell> {
  _AdaptiveDrawer? _openDrawer;

  void _openNavigationDrawer() {
    setState(() {
      _openDrawer = _AdaptiveDrawer.navigation;
    });
  }

  void _openIntelligenceDrawer() {
    setState(() {
      _openDrawer = _AdaptiveDrawer.intelligence;
    });
  }

  void _closeDrawer() {
    setState(() {
      _openDrawer = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.sizeOf(context);
    final bool desktop = size.width >= 1180;
    final bool tablet = size.width >= 760 && !desktop;
    final bool mobile = size.width < 760;
    final bool compactTopbar = size.width < 1360;
    final bool narrowTopbar = size.width < 520;
    final GtexDrawerEntry? activeDrawer =
        desktop ? null : _drawerEntryFor(mobile: mobile);
    final Widget chrome = Column(
      children: <Widget>[
        GtexShellTopbar(
          title: widget.title,
          contextLine: widget.contextLine,
          tickerItems: widget.tickerItems,
          commandActions: widget.commandActions,
          searchState: widget.searchState ?? _searchState(),
          livePulseState: widget.livePulseState ?? _livePulseState(),
          walletBalance: widget.walletBalance,
          walletCurrency: widget.walletCurrency,
          walletState: widget.walletState ?? _walletState(),
          walletIsLoading: widget.walletIsLoading,
          walletIsBlocked: widget.walletIsBlocked,
          roleLabel: widget.roleLabel,
          roleState: widget.roleState ?? _roleState(),
          clubLabel: widget.clubLabel,
          clubState: widget.clubState ?? _clubState(),
          connectionLabel: widget.connectionLabel,
          connectionState: widget.connectionState,
          connectionStatus: widget.connectionStatus,
          notificationCount: widget.notificationCount,
          notificationState: widget.notificationState ?? _notificationState(),
          themeState: widget.themeState ?? _actionState(widget.onToggleTheme),
          quickActionState:
              widget.quickActionState ?? _actionState(widget.onQuickAction),
          isSyncing: widget.isSyncing,
          compact: compactTopbar,
          narrow: narrowTopbar,
          onOpenNavigationDrawer: mobile ? _openNavigationDrawer : null,
          onOpenIntelligenceRail: desktop ? null : _openIntelligenceDrawer,
          onOpenWallet: widget.onOpenWallet,
          onToggleTheme: widget.onToggleTheme,
          onQuickAction: widget.onQuickAction,
          onNotifications: widget.onNotifications,
          onRoleSwitcher: widget.onRoleSwitcher,
          onClubSelector: widget.onClubSelector,
        ),
        Expanded(
          child: Row(
            children: <Widget>[
              if (!mobile)
                _SemanticRail(
                  key: const ValueKey<String>('gtex-shell-left-rail'),
                  destinations: widget.destinations,
                  activeDestinationId: widget.activeDestinationId,
                  compact: tablet,
                  onDestinationSelected: widget.onDestinationSelected,
                ),
              Expanded(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border(
                      top: BorderSide(
                        color: Theme.of(
                          context,
                        ).colorScheme.outline.withValues(alpha: 0.18),
                      ),
                    ),
                  ),
                  child: widget.body,
                ),
              ),
              if (desktop)
                KeyedSubtree(
                  key: const ValueKey<String>(
                    'gtex-shell-right-intelligence-rail',
                  ),
                  child: GtexContextRail(
                    title: 'Intelligence',
                    items: widget.contextItems,
                    accentColor: _activeTone(),
                    state: _intelligenceState(),
                    stateMessage: _emptyIntelligenceMessage(),
                    emptyState: _intelligenceState(),
                    emptyTitle: _emptyIntelligenceTitle(),
                    emptyMessage: _emptyIntelligenceMessage(),
                  ),
                ),
            ],
          ),
        ),
        if (mobile)
          _MobileBottomNav(
            key: const ValueKey<String>('gtex-shell-mobile-bottom-nav'),
            destinations: widget.destinations,
            activeDestinationId: widget.activeDestinationId,
            onDestinationSelected: widget.onDestinationSelected,
          ),
      ],
    );
    return GtexToastHost(
      child: GtexModalHost(
        child: GtexDrawerHost(
          drawer: activeDrawer,
          child: Scaffold(body: SafeArea(child: chrome)),
        ),
      ),
    );
  }

  GtexSurfaceState _searchState() {
    if (widget.commandActions.isEmpty) {
      return _missingDataState();
    }
    for (final GtexCommandAction action in widget.commandActions) {
      if (action.state.requiresAttention) {
        return action.state;
      }
    }
    return GtexSurfaceState.confirmed;
  }

  GtexSurfaceState _livePulseState() {
    if (widget.isSyncing) {
      return GtexSurfaceState.syncing;
    }
    if (widget.tickerItems.any((String item) => item.trim().isNotEmpty)) {
      return GtexSurfaceState.confirmed;
    }
    return _missingDataState();
  }

  GtexSurfaceState _walletState() {
    if (widget.walletIsBlocked) {
      return GtexSurfaceState.blocked;
    }
    if (widget.walletIsLoading) {
      return GtexSurfaceState.syncing;
    }
    if (widget.walletBalance == null) {
      return _missingDataState();
    }
    return GtexSurfaceState.confirmed;
  }

  GtexSurfaceState _roleState() {
    final String role = widget.roleLabel.trim().toLowerCase();
    if (role.isEmpty) {
      return _missingDataState();
    }
    return GtexSurfaceState.confirmed;
  }

  GtexSurfaceState _clubState() {
    final String club = widget.clubLabel.trim().toLowerCase();
    if (club.isEmpty || club == 'no active club') {
      return GtexSurfaceState.empty;
    }
    return GtexSurfaceState.confirmed;
  }

  GtexSurfaceState _notificationState() {
    if (widget.notificationCount > 0) {
      return GtexSurfaceState.confirmed;
    }
    return widget.connectionState.requiresAttention
        ? widget.connectionState
        : GtexSurfaceState.empty;
  }

  GtexSurfaceState _actionState(VoidCallback? action) {
    return action == null
        ? GtexSurfaceState.blocked
        : GtexSurfaceState.confirmed;
  }

  GtexDrawerEntry? _drawerEntryFor({required bool mobile}) {
    switch (_openDrawer) {
      case _AdaptiveDrawer.navigation:
        if (!mobile) {
          return null;
        }
        return GtexDrawerEntry(
          title: 'Navigation',
          side: GtexDrawerSide.left,
          width: 344,
          state: _navigationState(),
          onClose: _closeDrawer,
          child: _NavigationDrawerPanel(
            destinations: widget.destinations,
            activeDestinationId: widget.activeDestinationId,
            roleLabel: widget.roleLabel,
            clubLabel: widget.clubLabel,
            connectionLabel: widget.connectionLabel,
            connectionState: widget.connectionState,
            connectionStatus: widget.connectionStatus,
            walletBalance: widget.walletBalance,
            walletCurrency: widget.walletCurrency,
            walletIsLoading: widget.walletIsLoading,
            walletIsBlocked: widget.walletIsBlocked,
            onDestinationSelected: (String destinationId) {
              widget.onDestinationSelected(destinationId);
              _closeDrawer();
            },
            onOpenWallet: widget.onOpenWallet,
            onToggleTheme: widget.onToggleTheme,
            onQuickAction: widget.onQuickAction,
          ),
        );
      case _AdaptiveDrawer.intelligence:
        return GtexDrawerEntry(
          title: 'Intelligence rail',
          side: GtexDrawerSide.right,
          width: mobile ? 372 : 420,
          state: _intelligenceState(),
          onClose: _closeDrawer,
          child: KeyedSubtree(
            key: const ValueKey<String>('gtex-shell-intelligence-drawer'),
            child: GtexContextRail(
              title: 'Intelligence',
              items: widget.contextItems,
              accentColor: _activeTone(),
              width: double.infinity,
              state: _intelligenceState(),
              stateMessage: _emptyIntelligenceMessage(),
              emptyState: _intelligenceState(),
              emptyTitle: _emptyIntelligenceTitle(),
              emptyMessage: _emptyIntelligenceMessage(),
            ),
          ),
        );
      case null:
        return null;
    }
  }

  GtexSurfaceState _navigationState() {
    if (widget.destinations.isEmpty) {
      return _missingDataState();
    }
    for (final GtexShellDestination destination in widget.destinations) {
      if (destination.id == widget.activeDestinationId &&
          !destination.isEnabled) {
        return GtexSurfaceState.blocked;
      }
    }
    if (widget.connectionState.requiresAttention ||
        widget.connectionState == GtexSurfaceState.loading) {
      return widget.connectionState;
    }
    return GtexSurfaceState.confirmed;
  }

  GtexSurfaceState _intelligenceState() {
    if (widget.contextItems.isEmpty) {
      return _missingDataState();
    }
    for (final GtexContextRailItem item in widget.contextItems) {
      if (item.state.requiresAttention) {
        return item.state;
      }
    }
    for (final GtexContextRailItem item in widget.contextItems) {
      if (item.state != GtexSurfaceState.confirmed &&
          item.state != GtexSurfaceState.data) {
        return item.state;
      }
    }
    return GtexSurfaceState.confirmed;
  }

  GtexSurfaceState _missingDataState() {
    return switch (widget.connectionState) {
      GtexSurfaceState.confirmed => GtexSurfaceState.empty,
      _ => widget.connectionState,
    };
  }

  String _emptyIntelligenceTitle() {
    return switch (_intelligenceState()) {
      GtexSurfaceState.loading => 'Loading intelligence',
      GtexSurfaceState.empty => 'No intelligence selected',
      GtexSurfaceState.blocked => 'Intelligence blocked',
      GtexSurfaceState.pending => 'Intelligence pending',
      GtexSurfaceState.syncing => 'Syncing intelligence',
      GtexSurfaceState.reconnecting => 'Reconnecting intelligence',
      GtexSurfaceState.degraded => 'Intelligence degraded',
      GtexSurfaceState.confirmed => 'No intelligence selected',
      GtexSurfaceState.error => 'Intelligence failed',
    };
  }

  String _emptyIntelligenceMessage() {
    return switch (_intelligenceState()) {
      GtexSurfaceState.loading =>
        'GTEX is loading the right rail operating context.',
      GtexSurfaceState.empty =>
        'Select a route, club, player, or record to show confirmed context.',
      GtexSurfaceState.blocked =>
        'This account or lane cannot read the requested intelligence yet.',
      GtexSurfaceState.pending =>
        'The right rail is waiting for the next confirmed backend signal.',
      GtexSurfaceState.syncing =>
        'GTEX is reconciling the latest operating context.',
      GtexSurfaceState.reconnecting =>
        'Realtime context is reconnecting while confirmed data stays visible.',
      GtexSurfaceState.degraded =>
        'Confirmed context is limited while live intelligence recovers.',
      GtexSurfaceState.confirmed =>
        'Select a route, club, player, or record to show confirmed context.',
      GtexSurfaceState.error =>
        'GTEX could not load the latest operating intelligence.',
    };
  }

  Color _activeTone() {
    for (final GtexShellDestination destination in widget.destinations) {
      if (destination.id == widget.activeDestinationId) {
        return destination.tone;
      }
    }
    return const Color(0xFF69F3A4);
  }
}

class _Topbar extends StatelessWidget {
  const _Topbar({
    required this.title,
    required this.contextLine,
    required this.tickerItems,
    required this.commandActions,
    required this.walletBalance,
    required this.walletCurrency,
    required this.walletIsLoading,
    required this.walletIsBlocked,
    required this.roleLabel,
    required this.clubLabel,
    required this.connectionLabel,
    required this.connectionState,
    required this.connectionStatus,
    required this.notificationCount,
    required this.isSyncing,
    required this.compact,
    required this.narrow,
    required this.onOpenNavigationDrawer,
    required this.onOpenIntelligenceRail,
    required this.onOpenWallet,
    required this.onToggleTheme,
    required this.onQuickAction,
    required this.onNotifications,
    required this.onRoleSwitcher,
    required this.onClubSelector,
  });

  final String title;
  final String contextLine;
  final List<String> tickerItems;
  final List<GtexCommandAction> commandActions;
  final double? walletBalance;
  final String? walletCurrency;
  final bool walletIsLoading;
  final bool walletIsBlocked;
  final String roleLabel;
  final String clubLabel;
  final String connectionLabel;
  final GtexSurfaceState connectionState;
  final GtexRealtimeStatus? connectionStatus;
  final int notificationCount;
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
              Container(
                width: 38,
                height: 38,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: theme.colorScheme.primary.withValues(alpha: 0.28),
                  ),
                ),
                child: Text(
                  'G',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: compact ? 1 : 2,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      title,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      contextLine,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(
                          alpha: 0.62,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              if (!compact) ...<Widget>[
                Expanded(
                  flex: 3,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: _SearchButton(commandActions: commandActions),
                  ),
                ),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: GtexLiveTicker(
                    items: tickerItems,
                    isSyncing: isSyncing,
                    accentColor: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 10),
                _PillButton(
                  label: roleLabel,
                  icon: Icons.switch_account_outlined,
                  onPressed: onRoleSwitcher,
                ),
                const SizedBox(width: 8),
                _PillButton(
                  label: clubLabel,
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
                  isLoading: walletIsLoading,
                  isBlocked: walletIsBlocked,
                  onTap: onOpenWallet,
                ),
              ],
              if (compact) _SearchIconButton(commandActions: commandActions),
              if (compact && onOpenIntelligenceRail != null)
                IconButton(
                  key: const ValueKey<String>('gtex-shell-intelligence-action'),
                  tooltip: 'Open intelligence rail',
                  onPressed: onOpenIntelligenceRail,
                  icon: const Icon(Icons.auto_awesome_mosaic_outlined),
                ),
              _NotificationButton(
                count: notificationCount,
                onPressed: onNotifications,
              ),
              if (!compact || !narrow) ...<Widget>[
                IconButton(
                  tooltip: 'Theme',
                  onPressed: onToggleTheme,
                  icon: const Icon(Icons.contrast_rounded),
                ),
                IconButton(
                  tooltip: 'Quick actions',
                  onPressed: onQuickAction,
                  icon: const Icon(Icons.bolt_outlined),
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
                    isSyncing: isSyncing,
                    accentColor: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 8),
                GtexConnectionStatusBadge(
                  status: effectiveConnectionStatus,
                  label: connectionLabel,
                ),
              ],
            ),
          ],
        ],
      ),
    );
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

class _NavigationDrawerPanel extends StatelessWidget {
  const _NavigationDrawerPanel({
    required this.destinations,
    required this.activeDestinationId,
    required this.roleLabel,
    required this.clubLabel,
    required this.connectionLabel,
    required this.connectionState,
    required this.connectionStatus,
    required this.walletBalance,
    required this.walletCurrency,
    required this.walletIsLoading,
    required this.walletIsBlocked,
    required this.onDestinationSelected,
    required this.onOpenWallet,
    required this.onToggleTheme,
    required this.onQuickAction,
  });

  final List<GtexShellDestination> destinations;
  final String activeDestinationId;
  final String roleLabel;
  final String clubLabel;
  final String connectionLabel;
  final GtexSurfaceState connectionState;
  final GtexRealtimeStatus? connectionStatus;
  final double? walletBalance;
  final String? walletCurrency;
  final bool walletIsLoading;
  final bool walletIsBlocked;
  final ValueChanged<String> onDestinationSelected;
  final VoidCallback? onOpenWallet;
  final VoidCallback? onToggleTheme;
  final VoidCallback? onQuickAction;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = theme.colorScheme.primary;
    return Column(
      key: const ValueKey<String>('gtex-shell-navigation-drawer'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: tone.withValues(alpha: 0.07),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: tone.withValues(alpha: 0.18)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                roleLabel,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                clubLabel,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.68),
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  connectionStatus == null
                      ? GtexConnectionStatusBadge.fromSurfaceState(
                        state: connectionState,
                        label: connectionLabel,
                        compact: true,
                      )
                      : GtexConnectionStatusBadge(
                        status: connectionStatus!,
                        label: connectionLabel,
                        compact: true,
                      ),
                  GtexWalletChip(
                    balance: walletBalance,
                    currencyCode: walletCurrency,
                    isLoading: walletIsLoading,
                    isBlocked: walletIsBlocked,
                    onTap: onOpenWallet,
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child:
              destinations.isEmpty
                  ? Center(
                    child: GtexStatePanel(
                      state: GtexSurfaceState.empty,
                      eyebrow: 'NAVIGATION',
                      title: 'No shell routes available',
                      message:
                          'The shell has no confirmed destinations to show.',
                      icon: Icons.explore_off_outlined,
                    ),
                  )
                  : ListView.separated(
                    itemCount: destinations.length,
                    separatorBuilder:
                        (BuildContext context, int index) =>
                            const SizedBox(height: 8),
                    itemBuilder: (BuildContext context, int index) {
                      final GtexShellDestination destination =
                          destinations[index];
                      return _DrawerDestinationTile(
                        destination: destination,
                        active: destination.id == activeDestinationId,
                        onSelected: onDestinationSelected,
                      );
                    },
                  ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: <Widget>[
            OutlinedButton.icon(
              onPressed: onToggleTheme,
              icon: const Icon(Icons.contrast_rounded, size: 17),
              label: const Text('Theme'),
              style: OutlinedButton.styleFrom(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
            OutlinedButton.icon(
              onPressed: onQuickAction,
              icon: const Icon(Icons.bolt_outlined, size: 17),
              label: const Text('Quick'),
              style: OutlinedButton.styleFrom(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _DrawerDestinationTile extends StatelessWidget {
  const _DrawerDestinationTile({
    required this.destination,
    required this.active,
    required this.onSelected,
  });

  final GtexShellDestination destination;
  final bool active;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = destination.tone;
    return Semantics(
      selected: active,
      button: true,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap:
              destination.isEnabled ? () => onSelected(destination.id) : null,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
            decoration: BoxDecoration(
              color: active ? tone.withValues(alpha: 0.13) : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color:
                    active
                        ? tone.withValues(alpha: 0.32)
                        : theme.colorScheme.outline.withValues(alpha: 0.14),
              ),
            ),
            child: Row(
              children: <Widget>[
                Icon(
                  active ? destination.selectedIcon : destination.icon,
                  color:
                      active
                          ? tone
                          : theme.colorScheme.onSurface.withValues(alpha: 0.72),
                  size: 21,
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Text(
                    destination.label,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: active ? tone : theme.colorScheme.onSurface,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                  ),
                ),
                if (!destination.isEnabled)
                  Icon(
                    Icons.lock_outline_rounded,
                    color: theme.colorScheme.error,
                    size: 17,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SearchButton extends StatelessWidget {
  const _SearchButton({required this.commandActions});

  final List<GtexCommandAction> commandActions;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap:
            () => showGtexCommandPalette(
              context: context,
              actions: commandActions,
            ),
        child: Container(
          height: 38,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest.withValues(
              alpha: 0.38,
            ),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: theme.colorScheme.outline.withValues(alpha: 0.24),
            ),
          ),
          child: Row(
            children: <Widget>[
              const Icon(Icons.search_rounded, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Search players, clubs, traders, payments',
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.62),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SearchIconButton extends StatelessWidget {
  const _SearchIconButton({required this.commandActions});

  final List<GtexCommandAction> commandActions;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      tooltip: 'Search',
      onPressed:
          () =>
              showGtexCommandPalette(context: context, actions: commandActions),
      icon: const Icon(Icons.search_rounded),
    );
  }
}

class _PillButton extends StatelessWidget {
  const _PillButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 16),
      label: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 120),
        child: Text(label, overflow: TextOverflow.ellipsis),
      ),
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, 38),
        padding: const EdgeInsets.symmetric(horizontal: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}

class _NotificationButton extends StatelessWidget {
  const _NotificationButton({required this.count, required this.onPressed});

  final int count;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: <Widget>[
        IconButton(
          tooltip: 'Notifications',
          onPressed: onPressed,
          icon: const Icon(Icons.notifications_none_rounded),
        ),
        if (count > 0)
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
                  count > 99 ? '99+' : '$count',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onError,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _SemanticRail extends StatelessWidget {
  const _SemanticRail({
    super.key,
    required this.destinations,
    required this.activeDestinationId,
    required this.compact,
    required this.onDestinationSelected,
  });

  final List<GtexShellDestination> destinations;
  final String activeDestinationId;
  final bool compact;
  final ValueChanged<String> onDestinationSelected;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      width: compact ? 86 : 108,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.76),
        border: Border(
          right: BorderSide(
            color: theme.colorScheme.outline.withValues(alpha: 0.18),
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        right: false,
        child: ListView.separated(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
          itemCount: destinations.length,
          separatorBuilder:
              (BuildContext context, int index) => const SizedBox(height: 8),
          itemBuilder: (BuildContext context, int index) {
            final GtexShellDestination destination = destinations[index];
            return _RailButton(
              destination: destination,
              active: destination.id == activeDestinationId,
              compact: compact,
              onSelected: onDestinationSelected,
            );
          },
        ),
      ),
    );
  }
}

class _RailButton extends StatelessWidget {
  const _RailButton({
    required this.destination,
    required this.active,
    required this.compact,
    required this.onSelected,
  });

  final GtexShellDestination destination;
  final bool active;
  final bool compact;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = destination.tone;
    return Tooltip(
      message: destination.label,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap:
              destination.isEnabled ? () => onSelected(destination.id) : null,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            padding: EdgeInsets.symmetric(
              horizontal: compact ? 6 : 8,
              vertical: 10,
            ),
            decoration: BoxDecoration(
              color: active ? tone.withValues(alpha: 0.14) : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color:
                    active ? tone.withValues(alpha: 0.38) : Colors.transparent,
              ),
            ),
            child: Column(
              children: <Widget>[
                Icon(
                  active ? destination.selectedIcon : destination.icon,
                  color:
                      active
                          ? tone
                          : theme.colorScheme.onSurface.withValues(alpha: 0.68),
                  size: 21,
                ),
                const SizedBox(height: 6),
                Text(
                  destination.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color:
                        active
                            ? tone
                            : theme.colorScheme.onSurface.withValues(
                              alpha: 0.72,
                            ),
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MobileBottomNav extends StatelessWidget {
  const _MobileBottomNav({
    super.key,
    required this.destinations,
    required this.activeDestinationId,
    required this.onDestinationSelected,
  });

  final List<GtexShellDestination> destinations;
  final String activeDestinationId;
  final ValueChanged<String> onDestinationSelected;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.94),
        border: Border(
          top: BorderSide(
            color: theme.colorScheme.outline.withValues(alpha: 0.18),
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child:
            destinations.isEmpty
                ? const Padding(
                  padding: EdgeInsets.fromLTRB(10, 8, 10, 10),
                  child: GtexStatePanel(
                    state: GtexSurfaceState.empty,
                    eyebrow: 'NAVIGATION',
                    title: 'No shell routes available',
                    message:
                        'The mobile shell has no confirmed destinations to show.',
                    icon: Icons.explore_off_outlined,
                  ),
                )
                : SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                  child: Row(
                    children: destinations
                        .map(
                          (GtexShellDestination destination) => Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: _MobileNavChip(
                              destination: destination,
                              active: destination.id == activeDestinationId,
                              onSelected: onDestinationSelected,
                            ),
                          ),
                        )
                        .toList(growable: false),
                  ),
                ),
      ),
    );
  }
}

class _MobileNavChip extends StatelessWidget {
  const _MobileNavChip({
    required this.destination,
    required this.active,
    required this.onSelected,
  });

  final GtexShellDestination destination;
  final bool active;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return ActionChip(
      avatar: Icon(
        active ? destination.selectedIcon : destination.icon,
        size: 17,
        color: active ? destination.tone : theme.colorScheme.onSurfaceVariant,
      ),
      label: Text(destination.label),
      onPressed:
          destination.isEnabled ? () => onSelected(destination.id) : null,
      backgroundColor:
          active
              ? destination.tone.withValues(alpha: 0.14)
              : theme.colorScheme.surfaceContainerHighest.withValues(
                alpha: 0.4,
              ),
      side: BorderSide(
        color:
            active
                ? destination.tone.withValues(alpha: 0.36)
                : theme.colorScheme.outline.withValues(alpha: 0.18),
      ),
      labelStyle: theme.textTheme.labelLarge?.copyWith(
        color: active ? destination.tone : theme.colorScheme.onSurface,
        fontWeight: FontWeight.w800,
        letterSpacing: 0,
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    );
  }
}
