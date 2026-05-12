import 'dart:async';

import 'package:flutter/material.dart';

import '../data/player_match_service.dart';
import '../features/app_routes/gte_navigation_helpers.dart';
import '../features/app_routes/gte_route_data.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../features/player_market_redesign/player_market_redesign.dart';
import '../providers/gte_exchange_controller.dart';

/// Route-compatible V2 wrapper for the existing GTEX `/app/market` destination.
///
/// It deliberately keeps the same constructor shape as [GteMarketPlayersScreen]
/// so Codex can replace the market destination without changing GoRouter or
/// shell routing.
class GteMarketPlayersScreenV2 extends StatelessWidget {
  const GteMarketPlayersScreenV2({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
    this.matchService,
    this.navigationDependencies,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final GtePlayerMatchService? matchService;
  final GteNavigationDependencies? navigationDependencies;

  @override
  Widget build(BuildContext context) {
    return GtexPlayerMarketRedesignScreen(
      controller: controller,
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
