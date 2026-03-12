import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/models/competition_models.dart';

List<CompetitionSummary> competitionHubFeaturedCompetitions(
  List<CompetitionSummary> competitions,
) {
  final List<CompetitionSummary> sorted =
      competitions.toList(growable: true)..sort(_compareSpotlight);
  return sorted.take(4).toList(growable: false);
}

List<CompetitionSummary> competitionHubCompetitionsForDestination(
  CompetitionHubDestination destination,
  List<CompetitionSummary> competitions,
) {
  switch (destination) {
    case CompetitionHubDestination.overview:
      return competitionHubFeaturedCompetitions(competitions);
    case CompetitionHubDestination.leagues:
      return _sorted(
        competitions.where((CompetitionSummary item) => item.isLeague),
        _compareLeagueRows,
      );
    case CompetitionHubDestination.championsLeague:
      return _sorted(_eliteCompetitions(competitions), _compareEliteRows);
    case CompetitionHubDestination.gtexFastCup:
      return _sorted(
        competitions.where((CompetitionSummary item) => item.isCup),
        _compareFastCupRows,
      );
    case CompetitionHubDestination.worldSuperCup:
      return const <CompetitionSummary>[];
    case CompetitionHubDestination.academy:
      return _sorted(
        competitions.where(_isAcademyCompetition),
        _compareAcademyRows,
      );
  }
}

List<CompetitionSummary> competitionHubWorldSuperCupWatchlist(
  List<CompetitionSummary> competitions,
) {
  return competitionHubCompetitionsForDestination(
    CompetitionHubDestination.championsLeague,
    competitions,
  ).take(3).toList(growable: false);
}

bool competitionHubHasActiveSeason(
  CompetitionHubDestination destination,
  List<CompetitionSummary> competitions,
) {
  if (destination == CompetitionHubDestination.worldSuperCup) {
    return false;
  }
  return competitionHubCompetitionsForDestination(destination, competitions)
      .isNotEmpty;
}

List<CompetitionSummary> _eliteCompetitions(
  List<CompetitionSummary> competitions,
) {
  return competitions.where((CompetitionSummary item) {
    final bool hasPremiumSignal =
        item.entryFee >= 10 || item.prizePool >= 50 || item.participantCount >= 8;
    return item.beginnerFriendly != true &&
        hasPremiumSignal &&
        (item.isCup || item.isLeague);
  }).toList(growable: false);
}

bool _isAcademyCompetition(CompetitionSummary item) {
  final String creator = item.creatorLabel.toLowerCase();
  final String name = item.name.toLowerCase();
  return item.beginnerFriendly == true ||
      creator.contains('academy') ||
      name.contains('rookie') ||
      name.contains('academy');
}

List<CompetitionSummary> _sorted(
  Iterable<CompetitionSummary> competitions,
  int Function(CompetitionSummary left, CompetitionSummary right) compare,
) {
  final List<CompetitionSummary> sorted =
      competitions.toList(growable: true)..sort(compare);
  return sorted.toList(growable: false);
}

int _compareSpotlight(CompetitionSummary left, CompetitionSummary right) {
  final int statusCompare =
      _statusRank(left.status).compareTo(_statusRank(right.status));
  if (statusCompare != 0) {
    return statusCompare;
  }
  final int participantCompare =
      right.participantCount.compareTo(left.participantCount);
  if (participantCompare != 0) {
    return participantCompare;
  }
  return right.updatedAt.compareTo(left.updatedAt);
}

int _compareLeagueRows(CompetitionSummary left, CompetitionSummary right) {
  final int statusCompare =
      _statusRank(left.status).compareTo(_statusRank(right.status));
  if (statusCompare != 0) {
    return statusCompare;
  }
  final int fillCompare = right.fillRate.compareTo(left.fillRate);
  if (fillCompare != 0) {
    return fillCompare;
  }
  return right.updatedAt.compareTo(left.updatedAt);
}

int _compareEliteRows(CompetitionSummary left, CompetitionSummary right) {
  final int prizeCompare = right.prizePool.compareTo(left.prizePool);
  if (prizeCompare != 0) {
    return prizeCompare;
  }
  final int participantCompare =
      right.participantCount.compareTo(left.participantCount);
  if (participantCompare != 0) {
    return participantCompare;
  }
  return right.updatedAt.compareTo(left.updatedAt);
}

int _compareFastCupRows(CompetitionSummary left, CompetitionSummary right) {
  final int statusCompare =
      _statusRank(left.status).compareTo(_statusRank(right.status));
  if (statusCompare != 0) {
    return statusCompare;
  }
  final int freshnessCompare = right.updatedAt.compareTo(left.updatedAt);
  if (freshnessCompare != 0) {
    return freshnessCompare;
  }
  return right.participantCount.compareTo(left.participantCount);
}

int _compareAcademyRows(CompetitionSummary left, CompetitionSummary right) {
  final int beginnerCompare =
      (right.beginnerFriendly == true ? 1 : 0).compareTo(
        left.beginnerFriendly == true ? 1 : 0,
      );
  if (beginnerCompare != 0) {
    return beginnerCompare;
  }
  final int statusCompare =
      _statusRank(left.status).compareTo(_statusRank(right.status));
  if (statusCompare != 0) {
    return statusCompare;
  }
  return right.updatedAt.compareTo(left.updatedAt);
}

int _statusRank(CompetitionStatus status) {
  switch (status) {
    case CompetitionStatus.openForJoin:
      return 0;
    case CompetitionStatus.published:
      return 1;
    case CompetitionStatus.filled:
      return 2;
    case CompetitionStatus.inProgress:
      return 3;
    case CompetitionStatus.locked:
      return 4;
    case CompetitionStatus.completed:
      return 5;
    case CompetitionStatus.draft:
      return 6;
    case CompetitionStatus.cancelled:
      return 7;
    case CompetitionStatus.refunded:
      return 8;
    case CompetitionStatus.disputed:
      return 9;
  }
}
