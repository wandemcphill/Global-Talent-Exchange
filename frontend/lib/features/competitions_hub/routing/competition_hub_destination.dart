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
        return 'Beginner-friendly routes and development lanes.';
    }
  }

  String get hubDescription {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Route into every competition program from one switchboard, then drill into the active cards that matter right now.';
      case CompetitionHubDestination.leagues:
        return 'Persistent league routing for season-based standings, ladder movement, and verified scoring windows.';
      case CompetitionHubDestination.championsLeague:
        return 'Premium creator competitions and elite brackets staged as the continental layer of the hub.';
      case CompetitionHubDestination.gtexFastCup:
        return 'Fast-turnaround knockout cups that keep entry, fill, and result cycles short.';
      case CompetitionHubDestination.worldSuperCup:
        return 'Global prestige lane kept visible in navigation even when the event is between seasons.';
      case CompetitionHubDestination.academy:
        return 'Development-first competitions for rookie onboarding, low-friction entry, and academy progression.';
    }
  }

  String get emptyTitle {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Competition map is warming up';
      case CompetitionHubDestination.leagues:
        return 'No league routes are visible';
      case CompetitionHubDestination.championsLeague:
        return 'Champions League slate is not populated yet';
      case CompetitionHubDestination.gtexFastCup:
        return 'Fast Cup brackets are between windows';
      case CompetitionHubDestination.worldSuperCup:
        return 'World Super Cup is inactive';
      case CompetitionHubDestination.academy:
        return 'Academy routes are not visible yet';
    }
  }

  String get emptyMessage {
    switch (this) {
      case CompetitionHubDestination.overview:
        return 'Pull to refresh when new competitions publish.';
      case CompetitionHubDestination.leagues:
        return 'League cards will appear here as soon as a season feed is published.';
      case CompetitionHubDestination.championsLeague:
        return 'The elite route stays ready even while the current Champions League slate is light.';
      case CompetitionHubDestination.gtexFastCup:
        return 'Fast Cup cards return as soon as a short-format bracket opens.';
      case CompetitionHubDestination.worldSuperCup:
        return 'The tab remains visible by design so the global slot never disappears from the top-level map.';
      case CompetitionHubDestination.academy:
        return 'Academy cards appear when beginner-friendly routes or rookie programs are live.';
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
