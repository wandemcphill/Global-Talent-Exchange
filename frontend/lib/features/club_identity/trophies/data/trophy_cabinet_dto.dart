import 'trophy_item_dto.dart';

class TrophyCategoryDto {
  const TrophyCategoryDto({
    required this.trophyType,
    required this.trophyName,
    required this.displayName,
    required this.teamScope,
    required this.count,
    required this.isMajorHonor,
    required this.isEliteHonor,
  });

  final String trophyType;
  final String trophyName;
  final String displayName;
  final TrophyTeamScope teamScope;
  final int count;
  final bool isMajorHonor;
  final bool isEliteHonor;

  factory TrophyCategoryDto.fromJson(Map<String, dynamic> json) {
    return TrophyCategoryDto(
      trophyType: json['trophy_type'] as String,
      trophyName: json['trophy_name'] as String,
      displayName: json['display_name'] as String,
      teamScope: parseTrophyTeamScope(json['team_scope'] as String),
      count: json['count'] as int,
      isMajorHonor: json['is_major_honor'] as bool? ?? false,
      isEliteHonor: json['is_elite_honor'] as bool? ?? false,
    );
  }
}

class TrophySeasonSummaryDto {
  const TrophySeasonSummaryDto({
    required this.seasonLabel,
    required this.totalHonorsCount,
    required this.majorHonorsCount,
    required this.eliteHonorsCount,
    required this.seniorHonorsCount,
    required this.academyHonorsCount,
  });

  final String seasonLabel;
  final int totalHonorsCount;
  final int majorHonorsCount;
  final int eliteHonorsCount;
  final int seniorHonorsCount;
  final int academyHonorsCount;

  factory TrophySeasonSummaryDto.fromJson(Map<String, dynamic> json) {
    return TrophySeasonSummaryDto(
      seasonLabel: json['season_label'] as String,
      totalHonorsCount: json['total_honors_count'] as int,
      majorHonorsCount: json['major_honors_count'] as int,
      eliteHonorsCount: json['elite_honors_count'] as int,
      seniorHonorsCount: json['senior_honors_count'] as int,
      academyHonorsCount: json['academy_honors_count'] as int,
    );
  }
}

class TrophyCabinetDto {
  const TrophyCabinetDto({
    required this.clubId,
    required this.clubName,
    required this.totalHonorsCount,
    required this.majorHonorsCount,
    required this.eliteHonorsCount,
    required this.seniorHonorsCount,
    required this.academyHonorsCount,
    required this.trophiesByCategory,
    required this.trophiesBySeason,
    required this.recentHonors,
    required this.historicHonorsTimeline,
    required this.summaryOutputs,
  });

  final String clubId;
  final String clubName;
  final int totalHonorsCount;
  final int majorHonorsCount;
  final int eliteHonorsCount;
  final int seniorHonorsCount;
  final int academyHonorsCount;
  final List<TrophyCategoryDto> trophiesByCategory;
  final List<TrophySeasonSummaryDto> trophiesBySeason;
  final List<TrophyItemDto> recentHonors;
  final List<TrophyItemDto> historicHonorsTimeline;
  final List<String> summaryOutputs;

  bool get isEmpty => totalHonorsCount == 0;

  List<TrophyItemDto> featuredHonors({int limit = 3}) {
    final List<TrophyItemDto> honors = <TrophyItemDto>[
      ...historicHonorsTimeline
          .where((TrophyItemDto item) => item.isWorldSuperCup),
      ...historicHonorsTimeline.where(
        (TrophyItemDto item) => item.isEliteHonor && !item.isWorldSuperCup,
      ),
      ...historicHonorsTimeline.where(
        (TrophyItemDto item) => item.isMajorHonor && !item.isEliteHonor,
      ),
      ...historicHonorsTimeline.where(
        (TrophyItemDto item) => !item.isMajorHonor && !item.isEliteHonor,
      ),
    ];
    return honors.take(limit).toList(growable: false);
  }

  factory TrophyCabinetDto.fromJson(Map<String, dynamic> json) {
    return TrophyCabinetDto(
      clubId: json['club_id'] as String,
      clubName: json['club_name'] as String,
      totalHonorsCount: json['total_honors_count'] as int,
      majorHonorsCount: json['major_honors_count'] as int,
      eliteHonorsCount: json['elite_honors_count'] as int,
      seniorHonorsCount: json['senior_honors_count'] as int,
      academyHonorsCount: json['academy_honors_count'] as int,
      trophiesByCategory: (json['trophies_by_category'] as List<dynamic>)
          .map((dynamic item) =>
              TrophyCategoryDto.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      trophiesBySeason: (json['trophies_by_season'] as List<dynamic>)
          .map((dynamic item) =>
              TrophySeasonSummaryDto.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      recentHonors: (json['recent_honors'] as List<dynamic>)
          .map((dynamic item) =>
              TrophyItemDto.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      historicHonorsTimeline:
          (json['historic_honors_timeline'] as List<dynamic>)
              .map((dynamic item) =>
                  TrophyItemDto.fromJson(item as Map<String, dynamic>))
              .toList(growable: false),
      summaryOutputs: (json['summary_outputs'] as List<dynamic>)
          .map((dynamic item) => item as String)
          .toList(growable: false),
    );
  }
}
