import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';
import 'package:gte_frontend/features/owner_console/models/gtex_world_clock_models.dart';
import 'package:gte_frontend/features/owner_console/widgets/gtex_world_clock_panel.dart';
import 'package:gte_frontend/ui_gtex/layout/gtex_shell_scaffold.dart';
import 'package:gte_frontend/ui_gtex/layout/gtex_top_bar.dart';

export 'package:gte_frontend/features/owner_console/widgets/gtex_world_clock_panel.dart'
    show GtexWorldClockHeaderPill, GtexWorldClockPanel, OwnerWorldClockGateway;
export 'package:gte_frontend/features/owner_console/models/gtex_world_clock_models.dart'
    show GtexWorldClockSnapshot, WorldClock;

/// Canonical GTEX App Shell with live synchronized GTEX World Clock pill in the top bar.
class GtexAppShell extends StatelessWidget {
  const GtexAppShell({
    super.key,
    required this.navigationModel,
    required this.topBar,
    required this.child,
    required this.selectedSlotId,
    required this.onSelectSlot,
    this.selectedSecondaryId,
    this.onSelectSecondary,
    this.activeRoute,
    this.status,
    this.livePulseStrip,
    this.worldPulseRail,
    this.offlineBannerMessage,
    this.worldClock,
    this.loadWorldClock,
    this.onOpenWorldClock,
  });

  final ShellNavigationModel navigationModel;
  final GtexTopBar topBar;
  final Widget child;
  final GtexShellSlotId selectedSlotId;
  final ValueChanged<GtexShellSlotSpec> onSelectSlot;
  final GtexSecondaryDestinationId? selectedSecondaryId;
  final ValueChanged<GtexSecondaryDestinationSpec>? onSelectSecondary;
  final String? activeRoute;
  final Widget? status;
  final Widget? livePulseStrip;
  final Widget? worldPulseRail;
  final String? offlineBannerMessage;
  final WorldClock? worldClock;
  final Future<WorldClock> Function()? loadWorldClock;
  final VoidCallback? onOpenWorldClock;

  GtexTopBar _injectWorldClockPill() {
    final GtexWorldClockHeaderPill pill = GtexWorldClockHeaderPill(
      clock: worldClock,
      load: loadWorldClock,
      onTap: onOpenWorldClock,
    );
    final List<Widget> augmentedActions = <Widget>[
      pill,
      ...topBar.extraActions,
    ];
    return GtexTopBar(
      key: topBar.key,
      title: topBar.title,
      subtitle: topBar.subtitle,
      availableWorkspaces: topBar.availableWorkspaces,
      activeWorkspace: topBar.activeWorkspace,
      onWorkspaceSelected: topBar.onWorkspaceSelected,
      ownedClubs: topBar.ownedClubs,
      activeClubId: topBar.activeClubId,
      activeClubName: topBar.activeClubName,
      onClubSelected: topBar.onClubSelected,
      attentionCount: topBar.attentionCount,
      onOpenAttention: topBar.onOpenAttention,
      onOpenSearch: topBar.onOpenSearch,
      walletBalanceGtc: topBar.walletBalanceGtc,
      onOpenWallet: topBar.onOpenWallet,
      onOpenAdmin: topBar.onOpenAdmin,
      onOpenProfile: topBar.onOpenProfile,
      isAuthenticated: topBar.isAuthenticated,
      userInitials: topBar.userInitials,
      extraActions: augmentedActions,
    );
  }

  @override
  Widget build(BuildContext context) {
    return GtexShellScaffold(
      key: const Key('gtex-app-shell'),
      navigationModel: navigationModel,
      topBar: _injectWorldClockPill(),
      selectedSlotId: selectedSlotId,
      onSelectSlot: onSelectSlot,
      selectedSecondaryId: selectedSecondaryId,
      onSelectSecondary: onSelectSecondary,
      activeRoute: activeRoute,
      status: status,
      livePulseStrip: livePulseStrip,
      worldPulseRail: worldPulseRail,
      offlineBannerMessage: offlineBannerMessage,
      child: child,
    );
  }
}
