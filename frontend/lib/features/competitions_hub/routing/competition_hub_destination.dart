import 'package:flutter/material.dart';

enum CompetitionHubDestination {
  overview,
  leagues,
  championsLeague,
  gtexFastCup,
  worldSuperCup,
  academy,
}

extension CompetitionHubDestinationX on CompetitionHubDestination {
  String get label {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Overview';
      case CompetitionHubDestination.leagues:
        return 'Leagues';
      case CompetitionHubDestination.championsLeague:
        return 'Champions League';
      case CompetitionHubDestination.gtexFastCup:
        return 'GTEX Fast Cup';
      case CompetitionHubDestination.worldSuperCup:
        return 'World Super Cup';
      case CompetitionHubDestination.academy:
        return 'Academy';
    }
  }

  String get pathSegment {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'overview';
      case CompetitionHubDestination.leagues:
        return 'leagues';
      case CompetitionHubDestination.championsLeague:
        return 'champions-league';
      case CompetitionHubDestination.gtexFastCup:
        return 'gtex-fast-cup';
      case CompetitionHubDestination.worldSuperCup:
        return 'world-super-cup';
      case CompetitionHubDestination.academy:
        return 'academy';
    }
  }

  String get routePath => '/competitions/$pathSegment';

  IconData get icon {
    switch (this) {
      case CompetitionHubDestination.overview:
        return Icons.grid_view_rounded;
      case CompetitionHubDestination.leagues:
        return Icons.table_chart_outlined;
      case CompetitionHubDestination.championsLeague:
        return Icons.workspace_premium_outlined;
      case CompetitionHubDestination.gtexFastCup:
        return Icons.flash_on_outlined;
      case CompetitionHubDestination.worldSuperCup:
        return Icons.public_outlined;
      case CompetitionHubDestination.academy:
        return Icons.school_outlined;
    }
  }

  String get homeDescription {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Jump into the live competition map.';
      case CompetitionHubDestination.leagues:
        return 'Track table races and season climbs.';
      case CompetitionHubDestination.championsLeague:
        return 'Curated elite brackets and premium stakes.';
      case CompetitionHubDestination.gtexFastCup:
        return 'Short-format cups built for fast turnover.';
      case CompetitionHubDestination.worldSuperCup:
        return 'Persistent global slot reserved for activation.';
      case CompetitionHubDestination.academy:
        return 'Rookie cups and development runs.';
    }
  }

  String get hubDescription {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Jump between every competition from one matchday board, then dive into what is live now.';
      case CompetitionHubDestination.leagues:
        return 'Track title races, points tables, and season momentum.';
      case CompetitionHubDestination.championsLeague:
        return 'Elite creator cups and continental nights.';
      case CompetitionHubDestination.gtexFastCup:
        return 'Quick-fire knockout cups with fast entry and fast results.';
      case CompetitionHubDestination.worldSuperCup:
        return 'The world stage stays on the board even between seasons.';
      case CompetitionHubDestination.academy:
        return 'Starter competitions for rookies, easy entry, and academy growth.';
    }
  }

  String get emptyTitle {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Arena is warming up';
      case CompetitionHubDestination.leagues:
        return 'No league races live';
      case CompetitionHubDestination.championsLeague:
        return 'No Champions League nights yet';
      case CompetitionHubDestination.gtexFastCup:
        return 'Fast Cup is between rounds';
      case CompetitionHubDestination.worldSuperCup:
        return 'World Super Cup off-season';
      case CompetitionHubDestination.academy:
        return 'No academy cups live';
    }
  }

  String get emptyMessage {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Pull to refresh when new cups go live.';
      case CompetitionHubDestination.leagues:
        return 'League cards show up here when a new season opens.';
      case CompetitionHubDestination.championsLeague:
        return 'Champions League cards return when the next slate is live.';
      case CompetitionHubDestination.gtexFastCup:
        return 'Fast Cup cards return when the next bracket opens.';
      case CompetitionHubDestination.worldSuperCup:
        return 'The tab stays live so the world stage never disappears.';
      case CompetitionHubDestination.academy:
        return 'Academy cards appear when rookie routes open.';
    }
  }

  bool get isPersistentWhenInactive =>
      this == CompetitionHubDestination.worldSuperCup;
}

CompetitionHubDestination competitionHubDestinationFromPathSegment(
  String? segment,
) {
  switch ((segment ?? '').trim().toLowerCase()) {
    case 'leagues':
      return CompetitionHubDestination.leagues;
    case 'champions-league':
      return CompetitionHubDestination.championsLeague;
    case 'gtex-fast-cup':
      return CompetitionHubDestination.gtexFastCup;
    case 'world-super-cup':
      return CompetitionHubDestination.worldSuperCup;
    case 'academy':
      return CompetitionHubDestination.academy;
    case 'overview':
    default:
      return CompetitionHubDestination.overview;
  }
}
