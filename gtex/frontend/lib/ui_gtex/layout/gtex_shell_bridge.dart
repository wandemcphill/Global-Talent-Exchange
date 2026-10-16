import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';

import '../routes/gtex_current_route_adapter.dart';
import 'gtex_app_shell.dart';

/// Route-compatible bridge for the existing GTEX shell.
///
/// Use this only when migrating `GteNavigationShellScreen`. It does not change
/// the current router. It simply presents the current destination enum through
/// the new GTEX shell layout.
class GtexShellBridge extends StatelessWidget {
  const GtexShellBridge({
    super.key,
    required this.currentDestination,
    required this.onOpenPrimaryDestination,
    required this.child,
    this.actions = const <Widget>[],
    this.status,
  });

  final GtePrimaryDestination currentDestination;
  final ValueChanged<GtePrimaryDestination> onOpenPrimaryDestination;
  final Widget child;
  final List<Widget> actions;
  final Widget? status;

  @override
  Widget build(BuildContext context) {
    return GtexAppShell(
      title: GtexCurrentRouteAdapter.titleFor(currentDestination),
      subtitle: GtexCurrentRouteAdapter.subtitleFor(currentDestination),
      destinations: GtexCurrentRouteAdapter.destinations(
        current: currentDestination,
        onOpen: onOpenPrimaryDestination,
      ),
      actions: actions,
      status: status,
      child: child,
    );
  }
}
