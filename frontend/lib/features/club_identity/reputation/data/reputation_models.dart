import 'package:flutter/material.dart';

enum PrestigeTier {
  local,
  rising,
  established,
  elite,
  legendary,
  dynasty,
}

PrestigeTier prestigeTierFromRaw(String raw) {
  final String normalized = raw.trim().toLowerCase().replaceAll('-', ' ');
  switch (normalized) {
    case 'local':
      return PrestigeTier.local;
    case 'rising':
      return PrestigeTier.rising;
    case 'established':
      return PrestigeTier.established;
    case 'elite':
      return PrestigeTier.elite;
    case 'legendary':
      return PrestigeTier.legendary;
    case 'dynasty':
      return PrestigeTier.dynasty;
    default:
      return PrestigeTier.local;
  }
}

extension PrestigeTierX on PrestigeTier {
  String get label {
    switch (this) {
      case PrestigeTier.local:
        return 'Local';
      case PrestigeTier.rising:
        return 'Rising';
      case PrestigeTier.established:
        return 'Established';
      case PrestigeTier.elite:
        return 'Elite';
      case PrestigeTier.legendary:
        return 'Legendary';
      case PrestigeTier.dynasty:
        return 'Dynasty';
    }
  }

  int get minimumScore {
    switch (this) {
      case PrestigeTier.local:
        return 0;
      case PrestigeTier.rising:
        return 150;
      case PrestigeTier.established:
        return 350;
      case PrestigeTier.elite:
        return 650;
      case PrestigeTier.legendary:
        return 1050;
      case PrestigeTier.dynasty:
        return 1600;
    }
  }

  PrestigeTier? get nextTier {
    switch (this) {
      case PrestigeTier.local:
        return PrestigeTier.rising;
      case PrestigeTier.rising:
        return PrestigeTier.established;
      case PrestigeTier.established:
        return PrestigeTier.elite;
      case PrestigeTier.elite:
        return PrestigeTier.legendary;
      case PrestigeTier.legendary:
        return PrestigeTier.dynasty;
      case PrestigeTier.dynasty:
        return null;
    }
  }

  IconData get icon {
    switch (this) {
      case PrestigeTier.local:
        return Icons.shield_outlined;
      case PrestigeTier.rising:
        return Icons.trending_up;
      case PrestigeTier.established:
        return Icons.workspace_premium_outlined;
      case PrestigeTier.elite:
        return Icons.verified;
      case PrestigeTier.legendary:
        return Icons.auto_awesome;
      case PrestigeTier.dynasty:
        return Icons.emoji_events;
    }
  }
}

enum ReputationEventCategory {
  league,
  continental,
  worldSuperCup,
  awards,
  general,
}

extension ReputationEventCategoryX on ReputationEventCategory {
  String get label {
    switch (this) {
      case ReputationEventCategory.league:
        return 'League';
      case ReputationEventCategory.continental:
        return 'Continental';
      case ReputationEventCategory.worldSuperCup:
        return 'World Super Cup';
      case ReputationEventCategory.awards:
        return 'Awards';
      case ReputationEventCategory.general:
        return 'Club';
    }
  }

  IconData get icon {
    switch (this) {
      case ReputationEventCategory.league:
        return Icons.stadium_outlined;
      case ReputationEventCategory.continental:
        return Icons.public;
      case ReputationEventCategory.worldSuperCup:
        return Icons.language;
      case ReputationEventCategory.awards:
        return Icons.star_outline;
      case ReputationEventCategory.general:
        return Icons.history;
    }
  }
}

enum ReputationHistoryFilter {
  all,
  league,
  continental,
  worldSuperCup,
  awards,
}

extension ReputationHistoryFilterX on ReputationHistoryFilter {
  String get label {
    switch (this) {
      case ReputationHistoryFilter.all:
        return 'All';
      case ReputationHistoryFilter.league:
        return 'League';
      case ReputationHistoryFilter.continental:
        return 'Continental';
      case ReputationHistoryFilter.worldSuperCup:
        return 'World Super Cup';
      case ReputationHistoryFilter.awards:
        return 'Awards';
    }
  }
}

enum PrestigeLeaderboardScope {
  global,
  region,
  following,
}

extension PrestigeLeaderboardScopeX on PrestigeLeaderboardScope {
  String get label {
    switch (this) {
      case PrestigeLeaderboardScope.global:
        return 'Global';
      case PrestigeLeaderboardScope.region:
        return 'Region';
      case PrestigeLeaderboardScope.following:
        return 'Following';
    }
  }
}

class PrestigeTierProgress {
  const PrestigeTierProgress({
    required this.currentTier,
    required this.currentScore,
    required this.floorScore,
    required this.ceilingScore,
    required this.nextTier,
  });

  final PrestigeTier currentTier;
  final int currentScore;
  final int floorScore;
  final int? ceilingScore;
  final PrestigeTier? nextTier;

  int? get pointsToNextTier {
    if (ceilingScore == null) {
      return null;
    }
    final int remaining = ceilingScore! - currentScore;
    return remaining <= 0 ? 0 : remaining;
  }

  double get normalizedProgress {
    if (ceilingScore == null) {
      return 1;
    }
    final int span = ceilingScore! - floorScore;
    if (span <= 0) {
      return 1;
    }
    final double progress = (currentScore - floorScore) / span;
    return progress.clamp(0, 1);
  }
}

PrestigeTierProgress buildPrestigeTierProgress(int score, PrestigeTier tier) {
  final PrestigeTier resolvedTier = tier;
  final PrestigeTier? nextTier = resolvedTier.nextTier;
  return PrestigeTierProgress(
    currentTier: resolvedTier,
    currentScore: score,
    floorScore: resolvedTier.minimumScore,
    ceilingScore: nextTier?.minimumScore,
    nextTier: nextTier,
  );
}

class ReputationMilestoneDto {
  const ReputationMilestoneDto({
    required this.title,
    required this.delta,
    required this.occurredAt,
    this.badgeCode,
    this.season,
  });

  final String title;
  final String? badgeCode;
  final int? season;
  final int delta;
  final DateTime occurredAt;
}

class ReputationEventDto {
  const ReputationEventDto({
    required this.id,
    required this.season,
    required this.title,
    required this.description,
    required this.delta,
    required this.category,
    required this.occurredAt,
    this.badges = const <String>[],
    this.milestones = const <String>[],
  });

  final String id;
  final int season;
  final String title;
  final String description;
  final int delta;
  final ReputationEventCategory category;
  final DateTime occurredAt;
  final List<String> badges;
  final List<String> milestones;

  bool get isPositive => delta >= 0;
  String get seasonLabel => 'Season $season';
}

class ReputationProfileDto {
  const ReputationProfileDto({
    required this.clubId,
    required this.clubName,
    required this.regionLabel,
    required this.currentScore,
    required this.highestScore,
    required this.currentPrestigeTier,
    required this.badgesEarned,
    required this.biggestMilestones,
    this.lastActiveSeason,
  });

  final String clubId;
  final String clubName;
  final String regionLabel;
  final int currentScore;
  final int highestScore;
  final PrestigeTier currentPrestigeTier;
  final int? lastActiveSeason;
  final List<String> badgesEarned;
  final List<ReputationMilestoneDto> biggestMilestones;

  PrestigeTierProgress get progress =>
      buildPrestigeTierProgress(currentScore, currentPrestigeTier);
}

class ReputationHistoryDto {
  const ReputationHistoryDto({
    required this.clubId,
    required this.currentScore,
    required this.currentPrestigeTier,
    required this.events,
  });

  final String clubId;
  final int currentScore;
  final PrestigeTier currentPrestigeTier;
  final List<ReputationEventDto> events;
}

class PrestigeLeaderboardEntryDto {
  const PrestigeLeaderboardEntryDto({
    required this.clubId,
    required this.clubName,
    required this.regionLabel,
    required this.currentScore,
    required this.currentPrestigeTier,
    required this.highestScore,
    required this.totalSeasons,
    required this.rank,
    this.isFollowing = false,
  });

  final String clubId;
  final String clubName;
  final String regionLabel;
  final int currentScore;
  final PrestigeTier currentPrestigeTier;
  final int highestScore;
  final int totalSeasons;
  final int rank;
  final bool isFollowing;
}

class PrestigeLeaderboardDto {
  const PrestigeLeaderboardDto({
    required this.scope,
    required this.entries,
    this.note,
  });

  final PrestigeLeaderboardScope scope;
  final List<PrestigeLeaderboardEntryDto> entries;
  final String? note;
}

String prettifyClubId(String clubId) {
  final List<String> parts = clubId
      .split(RegExp(r'[-_\s]+'))
      .where((String value) => value.trim().isNotEmpty)
      .map((String value) => value.trim())
      .toList(growable: false);
  if (parts.isEmpty) {
    return clubId;
  }
  return parts
      .map((String value) =>
          '${value.substring(0, 1).toUpperCase()}${value.substring(1).toLowerCase()}')
      .join(' ');
}

String prettifyBadgeCode(String badgeCode) {
  return prettifyClubId(badgeCode.replaceAll(RegExp(r'[^a-zA-Z0-9]+'), ' '));
}
