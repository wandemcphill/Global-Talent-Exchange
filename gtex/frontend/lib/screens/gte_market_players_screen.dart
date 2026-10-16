import 'package:flutter/material.dart';

import '../data/player_match_service.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../providers/gte_exchange_controller.dart';
import 'gte_market_players_screen_v2.dart';

/// Legacy import-compatible entry point for the GTEX market.
///
/// The old flat market implementation has been retired so every route and
/// lingering import lands on the unified Transfer Hub experience.
class GteMarketPlayersScreen extends StatelessWidget {
  const GteMarketPlayersScreen({
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
    return GteMarketPlayersScreenV2(
      controller: controller,
      onOpenPlayer: onOpenPlayer,
      onOpenLogin: onOpenLogin,
      matchService: matchService,
      navigationDependencies: navigationDependencies,
    );
  }
}
