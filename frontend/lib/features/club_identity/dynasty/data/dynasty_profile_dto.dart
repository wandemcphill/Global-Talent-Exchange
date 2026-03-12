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
    final Object? rawLeagueFinish = GteJson.value(
      json,
      const <String>['league_finish', 'leagueFinish'],
    );
    return DynastySeasonSummaryDto(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, const <String>['club_name', 'clubName']),
      seasonId: GteJson.string(json, const <String>['season_id', 'seasonId']),
      seasonLabel: GteJson.string(
        json,
        const <String>['season_label', 'seasonLabel'],
      ),
      seasonIndex: GteJson.integer(
        json,
        const <String>['season_index', 'seasonIndex'],
      ),
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
    return DynastyWindowMetricsDto(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, const <String>['club_name', 'clubName']),
      seasonCount: GteJson.integer(
        json,
        const <String>['season_count', 'seasonCount'],
      ),
      windowStartSeasonId: GteJson.string(
        json,
        const <String>['window_start_season_id', 'windowStartSeasonId'],
      ),
      windowStartSeasonLabel: GteJson.string(
        json,
        const <String>['window_start_season_label', 'windowStartSeasonLabel'],
      ),
      windowEndSeasonId: GteJson.string(
        json,
        const <String>['window_end_season_id', 'windowEndSeasonId'],
      ),
      windowEndSeasonLabel: GteJson.string(
        json,
        const <String>['window_end_season_label', 'windowEndSeasonLabel'],
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
    return DynastySnapshotDto(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, const <String>['club_name', 'clubName']),
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
      reasons: GteJson.typedList<String>(
        json,
        const <String>['reasons'],
        (Object? entry) => entry.toString(),
      ),
      metrics: DynastyWindowMetricsDto.fromJson(
        GteJson.value(json, const <String>['metrics']),
      ),
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
      seasonId: GteJson.string(json, const <String>['season_id', 'seasonId']),
      seasonLabel: GteJson.string(
        json,
        const <String>['season_label', 'seasonLabel'],
      ),
      eventType: GteJson.string(
        json,
        const <String>['event_type', 'eventType'],
      ),
      title: GteJson.string(json, const <String>['title']),
      detail: GteJson.string(json, const <String>['detail']),
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
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, const <String>['club_name', 'clubName']),
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
    return DynastyProfileDto(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, const <String>['club_name', 'clubName']),
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
      reasons: GteJson.typedList<String>(
        json,
        const <String>['reasons'],
        (Object? entry) => entry.toString(),
      ),
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
}
