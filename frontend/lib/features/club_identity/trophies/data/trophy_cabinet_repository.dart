import 'dart:async';

import 'honors_timeline_dto.dart';
import 'season_honors_dto.dart';
import 'trophy_cabinet_dto.dart';
import 'trophy_leaderboard_entry_dto.dart';

abstract class TrophyCabinetRepository {
  Future<TrophyCabinetDto> fetchTrophyCabinet({
    required String clubId,
    String? teamScope,
  });

  Future<HonorsTimelineDto> fetchHonorsTimeline({
    required String clubId,
    String? teamScope,
  });

  Future<SeasonHonorsArchiveDto> fetchSeasonHonors({
    required String clubId,
    String? teamScope,
  });

  Future<TrophyLeaderboardDto> fetchTrophyLeaderboard({
    String? teamScope,
  });
}

class TrophyCabinetRepositoryException implements Exception {
  const TrophyCabinetRepositoryException(this.message);

  final String message;

  @override
  String toString() => message;
}

enum TrophyRepositoryScenario {
  demo,
  empty,
  error,
}

class StubTrophyCabinetRepository implements TrophyCabinetRepository {
  StubTrophyCabinetRepository({
    this.scenario = TrophyRepositoryScenario.demo,
    this.latency = const Duration(milliseconds: 420),
  });

  final TrophyRepositoryScenario scenario;
  final Duration latency;

  @override
  Future<TrophyCabinetDto> fetchTrophyCabinet({
    required String clubId,
    String? teamScope,
  }) async {
    await _delay();
    _throwIfNeeded(
      'Trophy cabinet service is temporarily unavailable.',
    );
    final List<Map<String, dynamic>> honors =
        _filteredHonors(clubId: clubId, teamScope: teamScope);
    return TrophyCabinetDto.fromJson(
      _buildCabinetPayload(
        clubId: clubId,
        honors: honors,
      ),
    );
  }

  @override
  Future<HonorsTimelineDto> fetchHonorsTimeline({
    required String clubId,
    String? teamScope,
  }) async {
    await _delay();
    _throwIfNeeded(
      'Honors timeline could not be loaded.',
    );
    return HonorsTimelineDto.fromJson(
      <String, dynamic>{
        'club_id': clubId,
        'club_name': _clubNames[clubId] ?? 'Expansion XI',
        'honors': _filteredHonors(clubId: clubId, teamScope: teamScope),
      },
    );
  }

  @override
  Future<SeasonHonorsArchiveDto> fetchSeasonHonors({
    required String clubId,
    String? teamScope,
  }) async {
    await _delay();
    _throwIfNeeded(
      'Season honors archive could not be loaded.',
    );
    final List<Map<String, dynamic>> honors =
        _filteredHonors(clubId: clubId, teamScope: teamScope);
    final Map<String, List<Map<String, dynamic>>> bySeasonAndScope =
        <String, List<Map<String, dynamic>>>{};
    for (final Map<String, dynamic> honor in honors) {
      final String key = '${honor['season_label']}::${honor['team_scope']}';
      bySeasonAndScope
          .putIfAbsent(key, () => <Map<String, dynamic>>[])
          .add(honor);
    }
    final List<Map<String, dynamic>> records = bySeasonAndScope.entries
        .map((MapEntry<String, List<Map<String, dynamic>>> entry) {
      final List<Map<String, dynamic>> seasonHonors =
          List<Map<String, dynamic>>.of(entry.value)
            ..sort(
              (Map<String, dynamic> left, Map<String, dynamic> right) {
                return DateTime.parse(right['earned_at'] as String)
                    .compareTo(DateTime.parse(left['earned_at'] as String));
              },
            );
      final Map<String, dynamic> first = seasonHonors.first;
      return <String, dynamic>{
        'snapshot_id':
            'snapshot-${first['club_id']}-${first['season_label']}-${first['team_scope']}',
        'club_id': first['club_id'],
        'club_name': first['club_name'],
        'season_label': first['season_label'],
        'team_scope': first['team_scope'],
        'honors': seasonHonors,
        'total_honors_count': seasonHonors.length,
        'major_honors_count': seasonHonors
            .where(
                (Map<String, dynamic> item) => item['is_major_honor'] == true)
            .length,
        'elite_honors_count': seasonHonors
            .where(
                (Map<String, dynamic> item) => item['is_elite_honor'] == true)
            .length,
        'recorded_at': DateTime.parse(first['earned_at'] as String)
            .toUtc()
            .toIso8601String(),
      };
    }).toList(growable: false)
      ..sort((Map<String, dynamic> left, Map<String, dynamic> right) {
        final int seasonComparison = (right['season_label'] as String)
            .compareTo(left['season_label'] as String);
        if (seasonComparison != 0) {
          return seasonComparison;
        }
        return (left['team_scope'] as String)
            .compareTo(right['team_scope'] as String);
      });

    return SeasonHonorsArchiveDto.fromJson(
      <String, dynamic>{
        'club_id': clubId,
        'club_name': _clubNames[clubId] ?? 'Expansion XI',
        'season_records': records,
      },
    );
  }

  @override
  Future<TrophyLeaderboardDto> fetchTrophyLeaderboard({
    String? teamScope,
  }) async {
    await _delay();
    _throwIfNeeded(
      'Trophy leaderboard could not be loaded.',
    );
    if (scenario == TrophyRepositoryScenario.empty) {
      return TrophyLeaderboardDto.fromJson(
        <String, dynamic>{'entries': <dynamic>[]},
      );
    }

    final List<Map<String, dynamic>> entries =
        _clubNames.entries.map((MapEntry<String, String> clubEntry) {
      final List<Map<String, dynamic>> honors = _filteredHonors(
        clubId: clubEntry.key,
        teamScope: teamScope,
      );
      final List<Map<String, dynamic>> categories =
          _buildCategoryPayload(honors);
      final DateTime? latest = honors.isEmpty
          ? null
          : honors
              .map((Map<String, dynamic> item) =>
                  DateTime.parse(item['earned_at'] as String))
              .reduce((DateTime left, DateTime right) {
              return left.isAfter(right) ? left : right;
            });
      return <String, dynamic>{
        'club_id': clubEntry.key,
        'club_name': clubEntry.value,
        'total_honors_count': honors.length,
        'major_honors_count': honors
            .where(
                (Map<String, dynamic> item) => item['is_major_honor'] == true)
            .length,
        'elite_honors_count': honors
            .where(
                (Map<String, dynamic> item) => item['is_elite_honor'] == true)
            .length,
        'senior_honors_count': honors
            .where(
                (Map<String, dynamic> item) => item['team_scope'] == 'senior')
            .length,
        'academy_honors_count': honors
            .where(
                (Map<String, dynamic> item) => item['team_scope'] == 'academy')
            .length,
        'latest_honor_at': latest?.toUtc().toIso8601String(),
        'summary_outputs': categories.take(3).map((Map<String, dynamic> item) {
          return '${item['count']}x ${item['display_name']}';
        }).toList(growable: false),
        'continental_titles_count': honors.where((Map<String, dynamic> item) {
          final String tier = item['competition_tier'] as String;
          return tier.contains('continental');
        }).length,
        'world_titles_count': honors.where((Map<String, dynamic> item) {
          return item['trophy_type'] == 'world_super_cup';
        }).length,
      };
    }).toList(growable: false);

    return TrophyLeaderboardDto.fromJson(<String, dynamic>{'entries': entries});
  }

  Future<void> _delay() async {
    await Future<void>.delayed(latency);
  }

  void _throwIfNeeded(String message) {
    if (scenario == TrophyRepositoryScenario.error) {
      throw TrophyCabinetRepositoryException(message);
    }
  }

  List<Map<String, dynamic>> _filteredHonors({
    required String clubId,
    String? teamScope,
  }) {
    if (scenario == TrophyRepositoryScenario.empty) {
      return const <Map<String, dynamic>>[];
    }
    final List<Map<String, dynamic>> honors = List<Map<String, dynamic>>.of(
      _stubHonorsByClub[clubId] ?? const <Map<String, dynamic>>[],
    );
    final Iterable<Map<String, dynamic>> filtered = teamScope == null
        ? honors
        : honors.where(
            (Map<String, dynamic> item) => item['team_scope'] == teamScope,
          );
    final List<Map<String, dynamic>> ordered = filtered.toList(growable: false)
      ..sort((Map<String, dynamic> left, Map<String, dynamic> right) {
        return DateTime.parse(right['earned_at'] as String)
            .compareTo(DateTime.parse(left['earned_at'] as String));
      });
    return ordered;
  }

  Map<String, dynamic> _buildCabinetPayload({
    required String clubId,
    required List<Map<String, dynamic>> honors,
  }) {
    final List<Map<String, dynamic>> categories = _buildCategoryPayload(honors);
    return <String, dynamic>{
      'club_id': clubId,
      'club_name': _clubNames[clubId] ?? 'Expansion XI',
      'total_honors_count': honors.length,
      'major_honors_count': honors
          .where((Map<String, dynamic> item) => item['is_major_honor'] == true)
          .length,
      'elite_honors_count': honors
          .where((Map<String, dynamic> item) => item['is_elite_honor'] == true)
          .length,
      'senior_honors_count': honors
          .where((Map<String, dynamic> item) => item['team_scope'] == 'senior')
          .length,
      'academy_honors_count': honors
          .where((Map<String, dynamic> item) => item['team_scope'] == 'academy')
          .length,
      'trophies_by_category': categories,
      'trophies_by_season': _buildSeasonPayload(honors),
      'recent_honors': honors.take(4).toList(growable: false),
      'historic_honors_timeline': honors,
      'summary_outputs': categories.take(4).map((Map<String, dynamic> item) {
        return '${item['count']}x ${item['display_name']}';
      }).toList(growable: false),
    };
  }

  List<Map<String, dynamic>> _buildCategoryPayload(
    List<Map<String, dynamic>> honors,
  ) {
    final Map<String, List<Map<String, dynamic>>> grouped =
        <String, List<Map<String, dynamic>>>{};
    for (final Map<String, dynamic> honor in honors) {
      final String key = '${honor['trophy_type']}::${honor['team_scope']}';
      grouped.putIfAbsent(key, () => <Map<String, dynamic>>[]).add(honor);
    }
    final List<Map<String, dynamic>> categories =
        grouped.values.map((List<Map<String, dynamic>> items) {
      final Map<String, dynamic> first = items.first;
      return <String, dynamic>{
        'trophy_type': first['trophy_type'],
        'trophy_name': first['trophy_name'],
        'display_name': first['display_name'],
        'team_scope': first['team_scope'],
        'count': items.length,
        'is_major_honor': first['is_major_honor'],
        'is_elite_honor': first['is_elite_honor'],
      };
    }).toList(growable: false)
          ..sort((Map<String, dynamic> left, Map<String, dynamic> right) {
            final int countComparison =
                (right['count'] as int).compareTo(left['count'] as int);
            if (countComparison != 0) {
              return countComparison;
            }
            return (left['display_name'] as String)
                .compareTo(right['display_name'] as String);
          });
    return categories;
  }

  List<Map<String, dynamic>> _buildSeasonPayload(
    List<Map<String, dynamic>> honors,
  ) {
    final Map<String, List<Map<String, dynamic>>> grouped =
        <String, List<Map<String, dynamic>>>{};
    for (final Map<String, dynamic> honor in honors) {
      grouped
          .putIfAbsent(
              honor['season_label'] as String, () => <Map<String, dynamic>>[])
          .add(honor);
    }
    final List<Map<String, dynamic>> seasons = grouped.entries
        .map((MapEntry<String, List<Map<String, dynamic>>> entry) {
      final List<Map<String, dynamic>> items = entry.value;
      return <String, dynamic>{
        'season_label': entry.key,
        'total_honors_count': items.length,
        'major_honors_count': items
            .where(
                (Map<String, dynamic> item) => item['is_major_honor'] == true)
            .length,
        'elite_honors_count': items
            .where(
                (Map<String, dynamic> item) => item['is_elite_honor'] == true)
            .length,
        'senior_honors_count': items
            .where(
                (Map<String, dynamic> item) => item['team_scope'] == 'senior')
            .length,
        'academy_honors_count': items
            .where(
                (Map<String, dynamic> item) => item['team_scope'] == 'academy')
            .length,
      };
    }).toList(growable: false)
      ..sort((Map<String, dynamic> left, Map<String, dynamic> right) {
        return (right['season_label'] as String)
            .compareTo(left['season_label'] as String);
      });
    return seasons;
  }
}

const Map<String, String> _clubNames = <String, String>{
  'lagos-comets': 'Lagos Comets',
  'atlas-sporting': 'Atlas Sporting',
  'nile-athletic': 'Nile Athletic',
  'new-club': 'Expansion XI',
};

const Map<String, List<Map<String, dynamic>>> _stubHonorsByClub =
    <String, List<Map<String, dynamic>>>{
  'lagos-comets': <Map<String, dynamic>>[
    <String, dynamic>{
      'trophy_win_id': 'honor-001',
      'club_id': 'lagos-comets',
      'club_name': 'Lagos Comets',
      'trophy_type': 'world_super_cup',
      'trophy_name': 'World Super Cup',
      'display_name': 'GTEX World Super Cup Winner',
      'season_label': '2028',
      'competition_region': 'Global',
      'competition_tier': 'global',
      'final_result_summary': 'Beat Rio Giants 2-0 in the final',
      'earned_at': '2028-08-11T21:00:00Z',
      'captain_name': 'Tunde Okoye',
      'top_performer_name': 'Musa Adeyemi',
      'team_scope': 'senior',
      'is_major_honor': true,
      'is_elite_honor': true,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-002',
      'club_id': 'lagos-comets',
      'club_name': 'Lagos Comets',
      'trophy_type': 'champions_league',
      'trophy_name': 'Champions League',
      'display_name': 'African Champions League Winner',
      'season_label': '2028',
      'competition_region': 'Africa',
      'competition_tier': 'continental',
      'final_result_summary': 'Won the continental final 3-1',
      'earned_at': '2028-05-27T20:30:00Z',
      'captain_name': 'Tunde Okoye',
      'top_performer_name': 'Jamiu Bello',
      'team_scope': 'senior',
      'is_major_honor': true,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-003',
      'club_id': 'lagos-comets',
      'club_name': 'Lagos Comets',
      'trophy_type': 'academy_champions_league',
      'trophy_name': 'Academy Champions League',
      'display_name': 'Academy Champions League Winner',
      'season_label': '2028',
      'competition_region': 'Africa',
      'competition_tier': 'academy_continental',
      'final_result_summary': 'Academy final won on penalties',
      'earned_at': '2028-04-30T18:00:00Z',
      'captain_name': 'Seyi Dara',
      'top_performer_name': 'Kola Mendez',
      'team_scope': 'academy',
      'is_major_honor': true,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-004',
      'club_id': 'lagos-comets',
      'club_name': 'Lagos Comets',
      'trophy_type': 'league_title',
      'trophy_name': 'League Title',
      'display_name': 'African League Champion',
      'season_label': '2027',
      'competition_region': 'Africa',
      'competition_tier': 'domestic',
      'final_result_summary': 'Finished six points clear at the top',
      'earned_at': '2027-05-18T19:00:00Z',
      'captain_name': 'Tunde Okoye',
      'top_performer_name': 'Musa Adeyemi',
      'team_scope': 'senior',
      'is_major_honor': true,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-005',
      'club_id': 'lagos-comets',
      'club_name': 'Lagos Comets',
      'trophy_type': 'fast_cup',
      'trophy_name': 'Fast Cup',
      'display_name': 'Fast Cup Winner',
      'season_label': '2027',
      'competition_region': 'Africa',
      'competition_tier': 'cup',
      'final_result_summary': 'Won the Fast Cup showcase 4-2',
      'earned_at': '2027-02-03T17:00:00Z',
      'captain_name': null,
      'top_performer_name': 'Kehinde Sola',
      'team_scope': 'senior',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-006',
      'club_id': 'lagos-comets',
      'club_name': 'Lagos Comets',
      'trophy_type': 'golden_boot',
      'trophy_name': 'Golden Boot',
      'display_name': 'Golden Boot Winner',
      'season_label': '2027',
      'competition_region': 'Africa',
      'competition_tier': 'individual',
      'final_result_summary': 'Musa Adeyemi scored 31 league goals',
      'earned_at': '2027-05-18T20:00:00Z',
      'captain_name': null,
      'top_performer_name': 'Musa Adeyemi',
      'team_scope': 'senior',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-007',
      'club_id': 'lagos-comets',
      'club_name': 'Lagos Comets',
      'trophy_type': 'academy_league',
      'trophy_name': 'Academy League',
      'display_name': 'Academy League Champion',
      'season_label': '2027',
      'competition_region': 'Africa',
      'competition_tier': 'academy_domestic',
      'final_result_summary': 'Academy side finished unbeaten',
      'earned_at': '2027-05-05T16:00:00Z',
      'captain_name': 'Seyi Dara',
      'top_performer_name': 'Kola Mendez',
      'team_scope': 'academy',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
  ],
  'atlas-sporting': <Map<String, dynamic>>[
    <String, dynamic>{
      'trophy_win_id': 'honor-101',
      'club_id': 'atlas-sporting',
      'club_name': 'Atlas Sporting',
      'trophy_type': 'champions_league',
      'trophy_name': 'Champions League',
      'display_name': 'African Champions League Winner',
      'season_label': '2027',
      'competition_region': 'Africa',
      'competition_tier': 'continental',
      'final_result_summary': 'Continental crown secured 1-0',
      'earned_at': '2027-05-24T20:15:00Z',
      'captain_name': 'Yassine Daho',
      'top_performer_name': 'Rayan El Idrissi',
      'team_scope': 'senior',
      'is_major_honor': true,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-102',
      'club_id': 'atlas-sporting',
      'club_name': 'Atlas Sporting',
      'trophy_type': 'league_title',
      'trophy_name': 'League Title',
      'display_name': 'African League Champion',
      'season_label': '2026',
      'competition_region': 'Africa',
      'competition_tier': 'domestic',
      'final_result_summary': 'Won the league on head-to-head record',
      'earned_at': '2026-05-19T19:20:00Z',
      'captain_name': 'Yassine Daho',
      'top_performer_name': 'Rayan El Idrissi',
      'team_scope': 'senior',
      'is_major_honor': true,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-103',
      'club_id': 'atlas-sporting',
      'club_name': 'Atlas Sporting',
      'trophy_type': 'top_assist',
      'trophy_name': 'Top Assist',
      'display_name': 'Top Assist Winner',
      'season_label': '2026',
      'competition_region': 'Africa',
      'competition_tier': 'individual',
      'final_result_summary': 'Recorded 19 assists across the campaign',
      'earned_at': '2026-05-19T20:05:00Z',
      'captain_name': null,
      'top_performer_name': 'Ismael Tazi',
      'team_scope': 'senior',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-104',
      'club_id': 'atlas-sporting',
      'club_name': 'Atlas Sporting',
      'trophy_type': 'fast_cup',
      'trophy_name': 'Fast Cup',
      'display_name': 'Fast Cup Winner',
      'season_label': '2025',
      'competition_region': 'Africa',
      'competition_tier': 'cup',
      'final_result_summary': 'Fast Cup final won on late set piece',
      'earned_at': '2025-11-12T18:40:00Z',
      'captain_name': null,
      'top_performer_name': 'Rayan El Idrissi',
      'team_scope': 'senior',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
  ],
  'nile-athletic': <Map<String, dynamic>>[
    <String, dynamic>{
      'trophy_win_id': 'honor-201',
      'club_id': 'nile-athletic',
      'club_name': 'Nile Athletic',
      'trophy_type': 'league_runner_up',
      'trophy_name': 'League Runner-up',
      'display_name': 'African League Runner-up',
      'season_label': '2028',
      'competition_region': 'Africa',
      'competition_tier': 'domestic',
      'final_result_summary': 'Second place after a final-day swing',
      'earned_at': '2028-05-18T18:50:00Z',
      'captain_name': 'Samir Naguib',
      'top_performer_name': 'Omar Fadel',
      'team_scope': 'senior',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-202',
      'club_id': 'nile-athletic',
      'club_name': 'Nile Athletic',
      'trophy_type': 'fair_play',
      'trophy_name': 'Fair Play',
      'display_name': 'Fair Play Award',
      'season_label': '2028',
      'competition_region': 'Africa',
      'competition_tier': 'special',
      'final_result_summary': 'Fewest cards in league competition',
      'earned_at': '2028-05-18T20:05:00Z',
      'captain_name': null,
      'top_performer_name': null,
      'team_scope': 'senior',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
    <String, dynamic>{
      'trophy_win_id': 'honor-203',
      'club_id': 'nile-athletic',
      'club_name': 'Nile Athletic',
      'trophy_type': 'academy_league',
      'trophy_name': 'Academy League',
      'display_name': 'Academy League Champion',
      'season_label': '2026',
      'competition_region': 'Africa',
      'competition_tier': 'academy_domestic',
      'final_result_summary': 'Academy champions on goal difference',
      'earned_at': '2026-05-08T17:15:00Z',
      'captain_name': 'Mazen Rashad',
      'top_performer_name': 'Yusuf Salem',
      'team_scope': 'academy',
      'is_major_honor': false,
      'is_elite_honor': false,
    },
  ],
};
