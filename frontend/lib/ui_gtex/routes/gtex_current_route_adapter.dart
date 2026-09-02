import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';

import '../layout/gtex_app_shell.dart';

class GtexCurrentRouteAdapter {
  const GtexCurrentRouteAdapter._();

  static List<GtexShellDestination> destinations({
    required GtePrimaryDestination current,
    required ValueChanged<GtePrimaryDestination> onOpen,
    Map<GtePrimaryDestination, String> badgeLabels =
        const <GtePrimaryDestination, String>{},
    List<GtePrimaryDestination> items = const <GtePrimaryDestination>[
      GtePrimaryDestination.home,
      GtePrimaryDestination.market,
      GtePrimaryDestination.competitions,
      GtePrimaryDestination.club,
      GtePrimaryDestination.wallet,
      GtePrimaryDestination.hub,
      GtePrimaryDestination.community,
    ],
  }) {
    return items
        .map((GtePrimaryDestination destination) {
          return GtexShellDestination(
            label: destination.label,
            icon: destination.icon,
            selectedIcon: destination.selectedIcon,
            isSelected: destination == current,
            accent: destination.accentColor,
            badgeLabel: badgeLabels[destination],
            onTap: () => onOpen(destination),
          );
        })
        .toList(growable: false);
  }

  static String titleFor(GtePrimaryDestination destination) {
    switch (destination) {
      case GtePrimaryDestination.home:
        return 'GTEX Command';
      case GtePrimaryDestination.market:
        return 'Transfer Hub';
      case GtePrimaryDestination.regens:
        return 'Regen World';
      case GtePrimaryDestination.competitions:
        return 'Matchday & Tournaments';
      case GtePrimaryDestination.club:
        return 'Club HQ';
      case GtePrimaryDestination.hub:
        return 'Creator & World Hub';
      case GtePrimaryDestination.community:
        return 'Community';
      case GtePrimaryDestination.wallet:
        return 'Wallet & Capital';
    }
  }

  static String subtitleFor(GtePrimaryDestination destination) {
    switch (destination) {
      case GtePrimaryDestination.home:
        return 'Your football operating system';
      case GtePrimaryDestination.market:
        return 'Transfer, loan, swap, and loan-to-buy football operations';
      case GtePrimaryDestination.regens:
        return 'Regen prospects, lineage, development, and Create-a-Son';
      case GtePrimaryDestination.competitions:
        return 'Run, join, and monitor GTEX football competitions';
      case GtePrimaryDestination.club:
        return 'Own, build, brand, and grow your club';
      case GtePrimaryDestination.hub:
        return 'Creator, regen, awards, and world activity';
      case GtePrimaryDestination.community:
        return 'Fans, followers, discussions, and social activity';
      case GtePrimaryDestination.wallet:
        return 'Coins, top-ups, withdrawals, orders, and treasury';
    }
  }
}
