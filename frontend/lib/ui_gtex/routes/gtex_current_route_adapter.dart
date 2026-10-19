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
        return 'GTEX';
      case GtePrimaryDestination.market:
        return 'Transfer Market';
      case GtePrimaryDestination.regens:
        return 'Regen World';
      case GtePrimaryDestination.competitions:
        return 'Matchday';
      case GtePrimaryDestination.club:
        return 'Club HQ';
      case GtePrimaryDestination.hub:
        return 'Studio';
      case GtePrimaryDestination.community:
        return 'Fan Community';
      case GtePrimaryDestination.wallet:
        return 'Capital';
    }
  }

  static String subtitleFor(GtePrimaryDestination destination) {
    switch (destination) {
      case GtePrimaryDestination.home:
        return 'Own the club. Run the economy.';
      case GtePrimaryDestination.market:
        return 'Sign, bid, shortlist, and trade talent';
      case GtePrimaryDestination.regens:
        return 'Prospects, lineage, and youth development';
      case GtePrimaryDestination.competitions:
        return 'Fixtures, cups, and tournament pressure';
      case GtePrimaryDestination.club:
        return 'Squad, staff, facilities, and prestige';
      case GtePrimaryDestination.hub:
        return 'Creator desk and world activity';
      case GtePrimaryDestination.community:
        return 'Fans, stories, and club noise';
      case GtePrimaryDestination.wallet:
        return 'FanCoin, GTEX Coin, orders, and payouts';
    }
  }
}
