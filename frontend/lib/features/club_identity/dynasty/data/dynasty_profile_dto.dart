import '../../../../data/gte_models.dart';
import 'dynasty_era_dto.dart';
import 'dynasty_types.dart';

class DynastySeasonSummaryDto {
  const DynastySeasonSummaryDto({
    required this.clubId,
    required this.clubName,
    required this.seasonId,
    required this.seasonLabel,
    required this.seasonIndex,
    required this.leagueFinish,
    required this.leagueTitle,
    required this.championsLeagueTitle,
    required this.worldSuperCupQualified,
    required this.worldSuperCupWinner,
    required this.trophyCount,
    required this.reputationGain,
    required this.topFourFinish,
    required this.eliteFinish,
  });

  final String clubId;
  final String clubName;
  final String seasonId;
  final String seasonLabel;
  final int seasonIndex;
  final int? leagueFinish;
  final bool leagueTitle;
  final bool championsLeagueTitle;
  final bool worldSuperCupQualified;
  final bool worldSuperCupWinner;
  final int trophyCount;
  final int reputationGain;
  final bool topFourFinish;
  final bool eliteFinish;

  factory DynastySeasonSummaryDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty season summary');
    final int seasonIndex = GteJson.integer(
      json,
      const <String>['season_index', 'seasonIndex'],
    );
    final Object? rawLeagueFinish = GteJson.value(
      json,
      const <String>['league_finish', 'leagueFinish'],
    );
    final String clubId = _stringOr(
      json,
      const <String>['club_id', 'clubId'],
      fallback: 'unknown-club',
    );
    final String clubName = _stringOr(
      json,
      const <String>['club_name', 'clubName'],
      fallback: clubId,
    );
    final String seasonId = _stringOr(
      json,
      const <String>['season_id', 'seasonId'],
      fallback: seasonIndex == 0 ? 'unknown-season' : '$seasonIndex',
    );
    final String seasonLabel = _stringOr(
      json,
      const <String>['season_label', 'seasonLabel'],
      fallback: seasonId,
    );
    return DynastySeasonSummaryDto(
      clubId: clubId,
      clubName: clubName,
      seasonId: seasonId,
      seasonLabel: seasonLabel,
      seasonIndex: seasonIndex,
      leagueFinish: rawLeagueFinish == null
          ? null
          : GteJson.integer(
              json,
              const <String>['league_finish', 'leagueFinish'],
            ),
      leagueTitle: GteJson.boolean(
        json,
        const <String>['league_title', 'leagueTitle'],
      ),
      championsLeagueTitle: GteJson.boolean(
        json,
        const <String>['champions_league_title', 'championsLeagueTitle'],
      ),
      worldSuperCupQualified: GteJson.boolean(
        json,
        const <String>[
          'world_super_cup_qualified',
          'worldSuperCupQualified',
        ],
      ),
      worldSuperCupWinner: GteJson.boolean(
        json,
        const <String>['world_super_cup_winner', 'worldSuperCupWinner'],
      ),
      trophyCount: GteJson.integer(
        json,
        const <String>['trophy_count', 'trophyCount'],
      ),
      reputationGain: GteJson.integer(
        json,
        const <String>['reputation_gain', 'reputationGain'],
      ),
      topFourFinish: GteJson.boolean(
        json,
        const <String>['top_four_finish', 'topFourFinish'],
      ),
      eliteFinish: GteJson.boolean(
        json,
        const <String>['elite_finish', 'eliteFinish'],
      ),
    );
  }
}

class DynastyStreaksDto {
  const DynastyStreaksDto({
    required this.topFour,
    required this.trophySeasons,
    required this.worldSuperCupQualification,
    required this.positiveReputation,
  });

  final int topFour;
  final int trophySeasons;
  final int worldSuperCupQualification;
  final int positiveReputation;

  factory DynastyStreaksDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty streaks');
    return DynastyStreaksDto(
      topFour: GteJson.integer(json, const <String>['top_four', 'topFour']),
      trophySeasons: GteJson.integer(
        json,
        const <String>['trophy_seasons', 'trophySeasons'],
      ),
      worldSuperCupQualification: GteJson.integer(
        json,
        const <String>[
          'world_super_cup_qualification',
          'worldSuperCupQualification',
        ],
      ),
      positiveReputation: GteJson.integer(
        json,
        const <String>['positive_reputation', 'positiveReputation'],
      ),
    );
  }
}

class DynastyWindowMetricsDto {
  const DynastyWindowMetricsDto({
    required this.clubId,
    required this.clubName,
    required this.seasonCount,
    required this.windowStartSeasonId,
    required this.windowStartSeasonLabel,
    required this.windowEndSeasonId,
    required this.windowEndSeasonLabel,
    required this.seasons,
    required this.leagueTitles,
    required this.championsLeagueTitles,
    required this.worldSuperCupTitles,
    required this.topFourFinishes,
    required this.eliteFinishes,
    required this.worldSuperCupQualifications,
    required this.trophyDensity,
    required this.reputationGainTotal,
    required this.recentTwoTopFourFinishes,
    required this.recentTwoTrophyDensity,
    required this.recentTwoReputationGain,
    required this.recentTwoLeagueTitles,
  });

  final String clubId;
  final String clubName;
  final int seasonCount;
  final String windowStartSeasonId;
  final String windowStartSeasonLabel;
  final String windowEndSeasonId;
  final String windowEndSeasonLabel;
  final List<DynastySeasonSummaryDto> seasons;
  final int leagueTitles;
  final int championsLeagueTitles;
  final int worldSuperCupTitles;
  final int topFourFinishes;
  final int eliteFinishes;
  final int worldSuperCupQualifications;
  final int trophyDensity;
  final int reputationGainTotal;
  final int recentTwoTopFourFinishes;
  final int recentTwoTrophyDensity;
  final int recentTwoReputationGain;
  final int recentTwoLeagueTitles;

  int get startSeasonIndex => seasons.isEmpty ? 0 : seasons.first.seasonIndex;

  int get endSeasonIndex => seasons.isEmpty ? 0 : seasons.last.seasonIndex;

  factory DynastyWindowMetricsDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty metrics');
    final List<DynastySeasonSummaryDto> seasons =
        List<DynastySeasonSummaryDto>.of(
      GteJson.typedList<DynastySeasonSummaryDto>(
        json,
        const <String>['seasons'],
        DynastySeasonSummaryDto.fromJson,
      ),
    )..sort((DynastySeasonSummaryDto left, DynastySeasonSummaryDto right) {
            return left.seasonIndex.compareTo(right.seasonIndex);
          });
    final String fallbackClubId =
        seasons.isNotEmpty ? seasons.first.clubId : 'unknown-club';
    final String fallbackClubName =
        seasons.isNotEmpty ? seasons.first.clubName : fallbackClubId;
    final String fallbackStartId =
        seasons.isNotEmpty ? seasons.first.seasonId : '';
    final String fallbackStartLabel =
        seasons.isNotEmpty ? seasons.first.seasonLabel : fallbackStartId;
    final String fallbackEndId =
        seasons.isNotEmpty ? seasons.last.seasonId : fallbackStartId;
    final String fallbackEndLabel =
        seasons.isNotEmpty ? seasons.last.seasonLabel : fallbackStartLabel;
    return DynastyWindowMetricsDto(
      clubId: _stringOr(
        json,
        const <String>['club_id', 'clubId'],
        fallback: fallbackClubId,
      ),
      clubName: _stringOr(
        json,
        const <String>['club_name', 'clubName'],
        fallback: fallbackClubName,
      ),
      seasonCount: GteJson.integer(
        json,
        const <String>['season_count', 'seasonCount'],
        fallback: seasons.length,
      ),
      windowStartSeasonId: _stringOr(
        json,
        const <String>['window_start_season_id', 'windowStartSeasonId'],
        fallback: fallbackStartId,
      ),
      windowStartSeasonLabel: _stringOr(
        json,
        const <String>['window_start_season_label', 'windowStartSeasonLabel'],
        fallback: fallbackStartLabel,
      ),
      windowEndSeasonId: _stringOr(
        json,
        const <String>['window_end_season_id', 'windowEndSeasonId'],
        fallback: fallbackEndId,
      ),
      windowEndSeasonLabel: _stringOr(
        json,
        const <String>['window_end_season_label', 'windowEndSeasonLabel'],
        fallback: fallbackEndLabel,
      ),
      seasons: seasons,
      leagueTitles: GteJson.integer(
        json,
        const <String>['league_titles', 'leagueTitles'],
      ),
      championsLeagueTitles: GteJson.integer(
        json,
        const <String>[
          'champions_league_titles',
          'championsLeagueTitles',
        ],
      ),
      worldSuperCupTitles: GteJson.integer(
        json,
        const <String>['world_super_cup_titles', 'worldSuperCupTitles'],
      ),
      topFourFinishes: GteJson.integer(
        json,
        const <String>['top_four_finishes', 'topFourFinishes'],
      ),
      eliteFinishes: GteJson.integer(
        json,
        const <String>['elite_finishes', 'eliteFinishes'],
      ),
      worldSuperCupQualifications: GteJson.integer(
        json,
        const <String>[
          'world_super_cup_qualifications',
          'worldSuperCupQualifications',
        ],
      ),
      trophyDensity: GteJson.integer(
        json,
        const <String>['trophy_density', 'trophyDensity'],
      ),
      reputationGainTotal: GteJson.integer(
        json,
        const <String>['reputation_gain_total', 'reputationGainTotal'],
      ),
      recentTwoTopFourFinishes: GteJson.integer(
        json,
        const <String>[
          'recent_two_top_four_finishes',
          'recentTwoTopFourFinishes',
        ],
      ),
      recentTwoTrophyDensity: GteJson.integer(
        json,
        const <String>[
          'recent_two_trophy_density',
          'recentTwoTrophyDensity',
        ],
      ),
      recentTwoReputationGain: GteJson.integer(
        json,
        const <String>[
          'recent_two_reputation_gain',
          'recentTwoReputationGain',
        ],
      ),
      recentTwoLeagueTitles: GteJson.integer(
        json,
        const <String>[
          'recent_two_league_titles',
          'recentTwoLeagueTitles',
        ],
      ),
    );
  }

  factory DynastyWindowMetricsDto.empty({
    required String clubId,
    required String clubName,
    String? seasonId,
    String? seasonLabel,
  }) {
    final String resolvedSeasonId = seasonId ?? '';
    final String resolvedSeasonLabel =
        seasonLabel ?? (resolvedSeasonId.isEmpty ? '' : resolvedSeasonId);
    return DynastyWindowMetricsDto(
      clubId: clubId,
      clubName: clubName,
      seasonCount: 0,
      windowStartSeasonId: resolvedSeasonId,
      windowStartSeasonLabel: resolvedSeasonLabel,
      windowEndSeasonId: resolvedSeasonId,
      windowEndSeasonLabel: resolvedSeasonLabel,
      seasons: const <DynastySeasonSummaryDto>[],
      leagueTitles: 0,
      championsLeagueTitles: 0,
      worldSuperCupTitles: 0,
      topFourFinishes: 0,
      eliteFinishes: 0,
      worldSuperCupQualifications: 0,
      trophyDensity: 0,
      reputationGainTotal: 0,
      recentTwoTopFourFinishes: 0,
      recentTwoTrophyDensity: 0,
      recentTwoReputationGain: 0,
      recentTwoLeagueTitles: 0,
    );
  }
}

class DynastySnapshotDto {
  const DynastySnapshotDto({
    required this.clubId,
    required this.clubName,
    required this.dynastyStatus,
    required this.eraLabel,
    required this.activeDynasty,
    required this.dynastyScore,
    required this.reasons,
    required this.metrics,
  });

  final String clubId;
  final String clubName;
  final DynastyStatus dynastyStatus;
  final DynastyEraType eraLabel;
  final bool activeDynasty;
  final int dynastyScore;
  final List<String> reasons;
  final DynastyWindowMetricsDto metrics;

  factory DynastySnapshotDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty snapshot');
    final String clubId = _stringOr(
      json,
      const <String>['club_id', 'clubId'],
      fallback: 'unknown-club',
    );
    final String clubName = _stringOr(
      json,
      const <String>['club_name', 'clubName'],
      fallback: clubId,
    );
    final Object? rawMetrics = GteJson.value(json, const <String>['metrics']);
    return DynastySnapshotDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: dynastyStatusFromRaw(
        GteJson.value(json, const <String>['dynasty_status', 'dynastyStatus']),
      ),
      eraLabel: dynastyEraTypeFromRaw(
        GteJson.value(json, const <String>['era_label', 'eraLabel']),
      ),
      activeDynasty: GteJson.boolean(
        json,
        const <String>['active_dynasty', 'activeDynasty'],
      ),
      dynastyScore: GteJson.integer(
        json,
        const <String>['dynasty_score', 'dynastyScore'],
      ),
      reasons: _stringList(json, const <String>['reasons']),
      metrics: rawMetrics == null
          ? DynastyWindowMetricsDto.empty(
              clubId: clubId,
              clubName: clubName,
            )
          : DynastyWindowMetricsDto.fromJson(rawMetrics),
    );
  }
}

class DynastyEventDto {
  const DynastyEventDto({
    required this.seasonId,
    required this.seasonLabel,
    required this.eventType,
    required this.title,
    required this.detail,
    required this.scoreImpact,
  });

  final String seasonId;
  final String seasonLabel;
  final String eventType;
  final String title;
  final String detail;
  final int scoreImpact;

  factory DynastyEventDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty event');
    return DynastyEventDto(
      seasonId: _stringOr(
        json,
        const <String>['season_id', 'seasonId'],
        fallback: 'unknown-season',
      ),
      seasonLabel: _stringOr(
        json,
        const <String>['season_label', 'seasonLabel'],
        fallback: 'Unknown season',
      ),
      eventType: _stringOr(
        json,
        const <String>['event_type', 'eventType'],
        fallback: 'event',
      ),
      title: _stringOr(
        json,
        const <String>['title'],
        fallback: 'Dynasty update',
      ),
      detail: _stringOr(
        json,
        const <String>['detail'],
        fallback: '',
      ),
      scoreImpact: GteJson.integer(
        json,
        const <String>['score_impact', 'scoreImpact'],
      ),
    );
  }
}

class DynastyHistoryDto {
  const DynastyHistoryDto({
    required this.clubId,
    required this.clubName,
    required this.dynastyTimeline,
    required this.eras,
    required this.events,
  });

  final String clubId;
  final String clubName;
  final List<DynastySnapshotDto> dynastyTimeline;
  final List<DynastyEraDto> eras;
  final List<DynastyEventDto> events;

  DynastyHistoryDto copyWith({
    List<DynastySnapshotDto>? dynastyTimeline,
    List<DynastyEraDto>? eras,
    List<DynastyEventDto>? events,
  }) {
    return DynastyHistoryDto(
      clubId: clubId,
      clubName: clubName,
      dynastyTimeline: dynastyTimeline ?? this.dynastyTimeline,
      eras: eras ?? this.eras,
      events: events ?? this.events,
    );
  }

  factory DynastyHistoryDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty history');
    return DynastyHistoryDto(
      clubId: _stringOr(
        json,
        const <String>['club_id', 'clubId'],
        fallback: 'unknown-club',
      ),
      clubName: _stringOr(
        json,
        const <String>['club_name', 'clubName'],
        fallback: 'Unknown club',
      ),
      dynastyTimeline: GteJson.typedList<DynastySnapshotDto>(
        json,
        const <String>['dynasty_timeline', 'dynastyTimeline'],
        DynastySnapshotDto.fromJson,
      ),
      eras: GteJson.typedList<DynastyEraDto>(
        json,
        const <String>['eras'],
        DynastyEraDto.fromJson,
      ),
      events: GteJson.typedList<DynastyEventDto>(
        json,
        const <String>['events'],
        DynastyEventDto.fromJson,
      ),
    );
  }
}

class DynastyProfileDto {
  const DynastyProfileDto({
    required this.clubId,
    required this.clubName,
    required this.dynastyStatus,
    required this.currentEraLabel,
    required this.activeDynastyFlag,
    required this.dynastyScore,
    required this.activeStreaks,
    required this.lastFourSeasonSummary,
    required this.reasons,
    required this.currentSnapshot,
    required this.dynastyTimeline,
    required this.eras,
    required this.events,
  });

  final String clubId;
  final String clubName;
  final DynastyStatus dynastyStatus;
  final DynastyEraType currentEraLabel;
  final bool activeDynastyFlag;
  final int dynastyScore;
  final DynastyStreaksDto activeStreaks;
  final List<DynastySeasonSummaryDto> lastFourSeasonSummary;
  final List<String> reasons;
  final DynastySnapshotDto? currentSnapshot;
  final List<DynastySnapshotDto> dynastyTimeline;
  final List<DynastyEraDto> eras;
  final List<DynastyEventDto> events;

  bool get hasRecognizedDynasty =>
      activeDynastyFlag ||
      dynastyStatus == DynastyStatus.fallen ||
      currentEraLabel.isDynasty ||
      currentEraLabel == DynastyEraType.fallenGiant;

  bool get isRisingClub =>
      currentEraLabel == DynastyEraType.emergingPower ||
      (!hasRecognizedDynasty && dynastyScore >= 35);

  int get trophiesLastFour => lastFourSeasonSummary.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) => sum + season.trophyCount,
      );

  int get reputationGainLastFour => lastFourSeasonSummary.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) =>
            sum + season.reputationGain,
      );

  factory DynastyProfileDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty profile');
    if (json.containsKey('progress')) {
      return _fromLegacyView(json);
    }
    return _fromProfileJson(json);
  }

  static DynastyProfileDto _fromProfileJson(Map<String, Object?> json) {
    final Object? currentSnapshotValue = GteJson.value(
      json,
      const <String>['current_snapshot', 'currentSnapshot'],
    );
    final List<DynastySeasonSummaryDto> lastFour =
        List<DynastySeasonSummaryDto>.of(
      GteJson.typedList<DynastySeasonSummaryDto>(
        json,
        const <String>[
          'last_four_season_summary',
          'lastFourSeasonSummary',
        ],
        DynastySeasonSummaryDto.fromJson,
      ),
    )..sort((DynastySeasonSummaryDto left, DynastySeasonSummaryDto right) {
            return left.seasonIndex.compareTo(right.seasonIndex);
          });
    final String clubId = _stringOr(
      json,
      const <String>['club_id', 'clubId'],
      fallback: 'unknown-club',
    );
    final String clubName = _stringOr(
      json,
      const <String>['club_name', 'clubName'],
      fallback: clubId,
    );
    return DynastyProfileDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: dynastyStatusFromRaw(
        GteJson.value(json, const <String>['dynasty_status', 'dynastyStatus']),
      ),
      currentEraLabel: dynastyEraTypeFromRaw(
        GteJson.value(
          json,
          const <String>['current_era_label', 'currentEraLabel', 'era_label'],
        ),
      ),
      activeDynastyFlag: GteJson.boolean(
        json,
        const <String>['active_dynasty_flag', 'activeDynastyFlag'],
      ),
      dynastyScore: GteJson.integer(
        json,
        const <String>['dynasty_score', 'dynastyScore'],
      ),
      activeStreaks: DynastyStreaksDto.fromJson(
        GteJson.value(
              json,
              const <String>['active_streaks', 'activeStreaks'],
            ) ??
            const <String, Object?>{},
      ),
      lastFourSeasonSummary: lastFour,
      reasons: _stringList(json, const <String>['reasons']),
      currentSnapshot: currentSnapshotValue == null
          ? null
          : DynastySnapshotDto.fromJson(currentSnapshotValue),
      dynastyTimeline: GteJson.typedList<DynastySnapshotDto>(
        json,
        const <String>['dynasty_timeline', 'dynastyTimeline'],
        DynastySnapshotDto.fromJson,
      ),
      eras: GteJson.typedList<DynastyEraDto>(
        json,
        const <String>['eras'],
        DynastyEraDto.fromJson,
      ),
      events: GteJson.typedList<DynastyEventDto>(
        json,
        const <String>['events'],
        DynastyEventDto.fromJson,
      ),
    );
  }

  static DynastyProfileDto _fromLegacyView(Map<String, Object?> json) {
    final Map<String, Object?> progress = GteJson.map(
      GteJson.value(json, const <String>['progress']) ??
          const <String, Object?>{},
      label: 'dynasty progress',
    );
    final String clubId = _stringOr(
      progress,
      const <String>['club_id', 'clubId'],
      fallback: 'unknown-club',
    );
    final String clubName = _stringOr(
      progress,
      const <String>['club_name', 'clubName'],
      fallback: clubId,
    );
    final int dynastyScore = GteJson.integer(
      progress,
      const <String>['dynasty_score', 'dynastyScore'],
    );
    return DynastyProfileDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: DynastyStatus.none,
      currentEraLabel: DynastyEraType.none,
      activeDynastyFlag: false,
      dynastyScore: dynastyScore,
      activeStreaks: const DynastyStreaksDto(
        topFour: 0,
        trophySeasons: 0,
        worldSuperCupQualification: 0,
        positiveReputation: 0,
      ),
      lastFourSeasonSummary: const <DynastySeasonSummaryDto>[],
      reasons: _legacyMilestoneReasons(json),
      currentSnapshot: null,
      dynastyTimeline: const <DynastySnapshotDto>[],
      eras: const <DynastyEraDto>[],
      events: const <DynastyEventDto>[],
    );
  }
}

String _stringOr(
  Map<String, Object?> json,
  List<String> keys, {
  required String fallback,
}) {
  return GteJson.stringOrNull(json, keys) ?? fallback;
}

List<String> _stringList(
  Map<String, Object?> json,
  List<String> keys,
) {
  final List<String> values = GteJson.typedList<String>(
    json,
    keys,
    (Object? entry) => entry == null ? '' : entry.toString().trim(),
  );
  return values
      .where((String value) => value.isNotEmpty)
      .toList(growable: false);
}

List<String> _legacyMilestoneReasons(Map<String, Object?> json) {
  final Object? rawMilestones = GteJson.value(json, const <String>['milestones']);
  if (rawMilestones == null) {
    return const <String>[];
  }
  final List<Object?> milestones =
      GteJson.list(rawMilestones, label: 'dynasty milestones');
  final List<String> reasons = <String>[];
  for (final Object? entry in milestones) {
    final Map<String, Object?> milestone =
        GteJson.map(entry, label: 'dynasty milestone');
    final bool unlocked = GteJson.boolean(
      milestone,
      const <String>['is_unlocked', 'isUnlocked'],
    );
    if (!unlocked) {
      continue;
    }
    final String title =
        GteJson.stringOrNull(milestone, const <String>['title']) ?? '';
    final String description =
        GteJson.stringOrNull(milestone, const <String>['description']) ?? '';
    if (title.isNotEmpty) {
      reasons.add(title);
    } else if (description.isNotEmpty) {
      reasons.add(description);
    }
  }
  return reasons.toSet().toList(growable: false);
}
