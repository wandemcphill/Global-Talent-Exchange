import 'dart:async';

import 'package:flutter/material.dart';

import '../data/player_match_service.dart';
import '../features/app_routes/gte_navigation_helpers.dart';
import '../features/app_routes/gte_route_data.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../features/player_market_redesign/presentation/gtex_market_ownership_desk_screen.dart';
import '../providers/gte_exchange_controller.dart';

/// Route-compatible V2 wrapper for the GTEX Market & Ownership Command Center.
class GteMarketPlayersScreenV2 extends StatelessWidget {
  const GteMarketPlayersScreenV2({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
    this.initialMode = GtexMarketDeskMode.market,
    this.matchService,
    this.navigationDependencies,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final GtexMarketDeskMode initialMode;
  final GtePlayerMatchService? matchService;
  final GteNavigationDependencies? navigationDependencies;

  @override
  Widget build(BuildContext context) {
    return GtexMarketOwnershipDeskScreen(
      controller: controller,
      initialMode: initialMode,
      onOpenPlayer: onOpenPlayer,
      onOpenLogin: onOpenLogin,
      onOpenTransferCalendar:
          navigationDependencies == null
              ? null
              : () {
                unawaited(
                  GteNavigationHelpers.pushRoute<void>(
                    context,
                    route: const FootballTransferCenterRouteData(
                      tab: GteTransferCenterTab.calendar,
                    ),
                    dependencies: navigationDependencies!,
                  ),
                );
              },
    );
  }
}
