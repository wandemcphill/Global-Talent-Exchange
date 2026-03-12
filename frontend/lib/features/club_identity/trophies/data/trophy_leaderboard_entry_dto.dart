class TrophyLeaderboardEntryDto {
  const TrophyLeaderboardEntryDto({
    required this.clubId,
    required this.clubName,
    required this.totalHonorsCount,
    required this.majorHonorsCount,
    required this.eliteHonorsCount,
    required this.seniorHonorsCount,
    required this.academyHonorsCount,
    required this.latestHonorAt,
    required this.summaryOutputs,
    required this.continentalTitlesCount,
    required this.worldTitlesCount,
  });

  final String clubId;
  final String clubName;
  final int totalHonorsCount;
  final int majorHonorsCount;
  final int eliteHonorsCount;
  final int seniorHonorsCount;
  final int academyHonorsCount;
  final DateTime? latestHonorAt;
  final List<String> summaryOutputs;
  final int continentalTitlesCount;
  final int worldTitlesCount;

  factory TrophyLeaderboardEntryDto.fromJson(Map<String, dynamic> json) {
    return TrophyLeaderboardEntryDto(
      clubId: json['club_id'] as String,
      clubName: json['club_name'] as String,
      totalHonorsCount: json['total_honors_count'] as int,
      majorHonorsCount: json['major_honors_count'] as int,
      eliteHonorsCount: json['elite_honors_count'] as int,
      seniorHonorsCount: json['senior_honors_count'] as int,
      academyHonorsCount: json['academy_honors_count'] as int,
      latestHonorAt: json['latest_honor_at'] == null
          ? null
          : DateTime.parse(json['latest_honor_at'] as String),
      summaryOutputs: (json['summary_outputs'] as List<dynamic>)
          .map((dynamic item) => item as String)
          .toList(growable: false),
      continentalTitlesCount: json['continental_titles_count'] as int? ?? 0,
      worldTitlesCount: json['world_titles_count'] as int? ?? 0,
    );
  }
}

class TrophyLeaderboardDto {
  const TrophyLeaderboardDto({
    required this.entries,
  });

  final List<TrophyLeaderboardEntryDto> entries;

  bool get isEmpty => entries.isEmpty;

  List<TrophyLeaderboardEntryDto> topByTotal({int limit = 5}) =>
      _sorted((TrophyLeaderboardEntryDto item) => item.totalHonorsCount,
          limit: limit);

  List<TrophyLeaderboardEntryDto> topByMajor({int limit = 5}) =>
      _sorted((TrophyLeaderboardEntryDto item) => item.majorHonorsCount,
          limit: limit);

  List<TrophyLeaderboardEntryDto> topByContinental({int limit = 5}) =>
      _sorted((TrophyLeaderboardEntryDto item) => item.continentalTitlesCount,
          limit: limit);

  List<TrophyLeaderboardEntryDto> topByWorld({int limit = 5}) =>
      _sorted((TrophyLeaderboardEntryDto item) => item.worldTitlesCount,
          limit: limit);

  factory TrophyLeaderboardDto.fromJson(Map<String, dynamic> json) {
    return TrophyLeaderboardDto(
      entries: (json['entries'] as List<dynamic>)
          .map((dynamic item) =>
              TrophyLeaderboardEntryDto.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
    );
  }

  List<TrophyLeaderboardEntryDto> _sorted(
    int Function(TrophyLeaderboardEntryDto entry) selector, {
    required int limit,
  }) {
    final List<TrophyLeaderboardEntryDto> sorted =
        List<TrophyLeaderboardEntryDto>.of(entries)
          ..sort((TrophyLeaderboardEntryDto left,
              TrophyLeaderboardEntryDto right) {
            final int primary = selector(right).compareTo(selector(left));
            if (primary != 0) {
              return primary;
            }
            final int secondary =
                right.majorHonorsCount.compareTo(left.majorHonorsCount);
            if (secondary != 0) {
              return secondary;
            }
            return left.clubName.compareTo(right.clubName);
          });
    return sorted.take(limit).toList(growable: false);
  }
}
