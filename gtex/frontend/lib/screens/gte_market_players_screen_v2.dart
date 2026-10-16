import 'dart:async';

import 'package:flutter/material.dart';

import '../data/player_match_service.dart';
import '../features/app_routes/gte_navigation_helpers.dart';
import '../features/app_routes/gte_route_data.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../features/navigation/routing/gte_navigation_route.dart';
import '../features/player_market_redesign/player_market_redesign.dart';
import '../providers/gte_exchange_controller.dart';

/// Route-compatible V2 wrapper for the existing GTEX `/app/market` destination.
///
/// It mounts [GtexMarketOwnershipDeskScreen] so the shell exposes both
/// Transfer Intelligence and My Ownership modes under `/app/market`.
class GteMarketPlayersScreenV2 extends StatelessWidget {
  const GteMarketPlayersScreenV2({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
    this.initialMode = GtexMarketDeskMode.market,
    this.matchService,
    this.navigationDependencies,
    this.onModeChanged,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final GtexMarketDeskMode initialMode;
  final GtePlayerMatchService? matchService;
  final GteNavigationDependencies? navigationDependencies;
  final ValueChanged<GtexMarketDeskMode>? onModeChanged;

  @override
  Widget build(BuildContext context) {
    return GtexMarketOwnershipDeskScreen(
      controller: controller,
      initialMode: initialMode,
      onOpenPlayer: onOpenPlayer,
      onOpenLogin: onOpenLogin,
      onModeChanged: onModeChanged,
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
