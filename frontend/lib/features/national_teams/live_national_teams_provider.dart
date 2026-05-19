import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../../data/gte_models.dart';
import '../../models/national_team_models.dart';
import '../../models/regen_universe_models.dart';
import '../../shared/providers/auth_provider.dart';
import '../shared/data/feature_api_provider.dart';
import '../shared/data/gte_feature_support.dart';

class NationalTeamCountryRankingRecord {
  const NationalTeamCountryRankingRecord({
    required this.countryCode,
    required this.countryName,
    required this.eloRating,
    required this.matchesPlayed,
    required this.wins,
    required this.draws,
    required this.losses,
    required this.titles,
  });

  final String countryCode;
  final String countryName;
  final double eloRating;
  final int matchesPlayed;
  final int wins;
  final int draws;
  final int losses;
  final int titles;

  factory NationalTeamCountryRankingRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'national team ranking');
    return NationalTeamCountryRankingRecord(
      countryCode: stringValue(json['country_code']),
      countryName: stringValue(json['country_name']),
      eloRating: numberValue(json['elo_rating']),
      matchesPlayed: intValue(json['matches_played']),
      wins: intValue(json['wins']),
      draws: intValue(json['draws']),
      losses: intValue(json['losses']),
      titles: intValue(json['titles']),
    );
  }
}

class NationalTeamCountryPipeline {
  const NationalTeamCountryPipeline({
    required this.countryCode,
    required this.countryName,
    required this.confederationCode,
    required this.prospectCount,
    required this.eliteProspects,
    required this.averagePotential,
    required this.topPotential,
    required this.topProspectName,
    required this.focusPositions,
    this.rankingElo,
  });

  final String countryCode;
  final String countryName;
  final String confederationCode;
  final int prospectCount;
  final int eliteProspects;
  final double averagePotential;
  final int topPotential;
  final String topProspectName;
  final List<String> focusPositions;
  final double? rankingElo;
}

class NationalTeamAcademySignal {
  const NationalTeamAcademySignal({
    required this.confederationCode,
    required this.label,
    required this.countryCount,
    required this.prospectCount,
    required this.averagePotential,
    required this.topPotential,
    required this.focusPositions,
  });

  final String confederationCode;
  final String label;
  final int countryCount;
  final int prospectCount;
  final double averagePotential;
  final int topPotential;
  final List<String> focusPositions;
}

class NationalTeamsHubData {
  const NationalTeamsHubData({
    required this.competitions,
    required this.rankings,
    required this.nationalRegens,
    required this.regenScoutingFeed,
    required this.history,
  });

  final List<NationalTeamCompetition> competitions;
  final List<NationalTeamCountryRankingRecord> rankings;
  final List<NationalRegenSeed> nationalRegens;
  final List<RegenScoutingFeedItem> regenScoutingFeed;
  final NationalTeamUserHistory? history;

  List<NationalRegenSeed> get youthProspects {
    return _sortedRegens(
      nationalRegens
          .where(
            (NationalRegenSeed seed) =>
                (seed.age ?? 99) <= 20 ||
                seed.ageBand.toLowerCase().contains('u17') ||
                seed.ageBand.toLowerCase().contains('u20') ||
                seed.ageBand.toLowerCase().contains('youth'),
          )
          .toList(growable: false),
    );
  }

  List<NationalRegenSeed> get futureStars => _sortedRegens(nationalRegens);

  List<NationalTeamCountryPipeline> get countryPipelines {
    final Map<String, NationalTeamCountryRankingRecord> rankingByCountry =
        <String, NationalTeamCountryRankingRecord>{
          for (final NationalTeamCountryRankingRecord ranking in rankings)
            ranking.countryCode.toUpperCase(): ranking,
        };
    final Map<String, List<NationalRegenSeed>> byCountry =
        <String, List<NationalRegenSeed>>{};
    for (final NationalRegenSeed seed in nationalRegens) {
      byCountry
          .putIfAbsent(
            seed.countryCode.toUpperCase(),
            () => <NationalRegenSeed>[],
          )
          .add(seed);
    }
    final List<NationalTeamCountryPipeline> pipelines = byCountry.entries
        .map((MapEntry<String, List<NationalRegenSeed>> entry) {
          final List<NationalRegenSeed> seeds = _sortedRegens(entry.value);
          final NationalRegenSeed topSeed = seeds.first;
          final NationalTeamCountryRankingRecord? ranking =
              rankingByCountry[entry.key];
          return NationalTeamCountryPipeline(
            countryCode: topSeed.countryCode,
            countryName: topSeed.countryName,
            confederationCode: _confederationCode(topSeed),
            prospectCount: seeds.length,
            eliteProspects:
                seeds
                    .where(
                      (NationalRegenSeed seed) => seed.potentialRating >= 84,
                    )
                    .length,
            averagePotential: _averagePotential(seeds),
            topPotential: topSeed.potentialRating,
            topProspectName: topSeed.displayName,
            focusPositions: _focusPositions(seeds),
            rankingElo: ranking?.eloRating,
          );
        })
        .toList(growable: false);
    pipelines.sort((
      NationalTeamCountryPipeline left,
      NationalTeamCountryPipeline right,
    ) {
      final int potentialCompare = right.topPotential.compareTo(
        left.topPotential,
      );
      if (potentialCompare != 0) {
        return potentialCompare;
      }
      return right.prospectCount.compareTo(left.prospectCount);
    });
    return pipelines;
  }

  List<NationalTeamAcademySignal> get internationalAcademies {
    final Map<String, List<NationalRegenSeed>> byConfederation =
        <String, List<NationalRegenSeed>>{};
    for (final NationalRegenSeed seed in nationalRegens) {
      byConfederation
          .putIfAbsent(_confederationCode(seed), () => <NationalRegenSeed>[])
          .add(seed);
    }
    final List<NationalTeamAcademySignal> signals = byConfederation.entries
        .map((MapEntry<String, List<NationalRegenSeed>> entry) {
          final List<NationalRegenSeed> seeds = _sortedRegens(entry.value);
          final Set<String> countryCodes =
              seeds
                  .map(
                    (NationalRegenSeed seed) => seed.countryCode.toUpperCase(),
                  )
                  .toSet();
          return NationalTeamAcademySignal(
            confederationCode: entry.key,
            label: _confederationLabel(entry.key),
            countryCount: countryCodes.length,
            prospectCount: seeds.length,
            averagePotential: _averagePotential(seeds),
            topPotential: seeds.isEmpty ? 0 : seeds.first.potentialRating,
            focusPositions: _focusPositions(seeds),
          );
        })
        .toList(growable: false);
    signals.sort((
      NationalTeamAcademySignal left,
      NationalTeamAcademySignal right,
    ) {
      final int potentialCompare = right.topPotential.compareTo(
        left.topPotential,
      );
      if (potentialCompare != 0) {
        return potentialCompare;
      }
      return right.prospectCount.compareTo(left.prospectCount);
    });
    return signals;
  }
}

class NationalTeamCompetitionDetailData {
  const NationalTeamCompetitionDetailData({
    required this.competition,
    required this.lifecycle,
    required this.presentation,
    required this.rentalPool,
    required this.history,
  });

  final NationalTeamCompetition competition;
  final JsonMap lifecycle;
  final JsonMap presentation;
  final JsonMap rentalPool;
  final NationalTeamUserHistory? history;
}

class NationalTeamsApi {
  const NationalTeamsApi({required this.client});

  final GteAuthedApi client;

  Future<List<NationalTeamCompetition>> listCompetitions() async {
    final List<dynamic> payload = await client.getList(
      '/api/national-team-engine/competitions',
      auth: false,
    );
    return payload
        .map(NationalTeamCompetition.fromJson)
        .toList(growable: false);
  }

  Future<List<NationalTeamCountryRankingRecord>> listRankings({
    int limit = 20,
  }) async {
    final List<dynamic> payload = await client.getList(
      '/api/national-team-engine/rankings',
      auth: false,
      query: <String, Object?>{'limit': limit},
    );
    return payload
        .map(NationalTeamCountryRankingRecord.fromJson)
        .toList(growable: false);
  }

  Future<NationalTeamCompetition> fetchCompetition(String competitionId) async {
    final JsonMap payload = await client.getMap(
      '/api/national-team-engine/competitions/$competitionId',
      auth: false,
    );
    return NationalTeamCompetition.fromJson(payload);
  }

  Future<JsonMap> fetchLifecycle(String competitionId) {
    return client.getMap(
      '/api/national-team-engine/competitions/$competitionId/lifecycle',
      auth: false,
    );
  }

  Future<JsonMap> fetchPresentation(String competitionId) {
    return client.getMap(
      '/api/national-team-engine/competitions/$competitionId/presentation',
      auth: false,
    );
  }

  Future<JsonMap> fetchRentalPoolPreview(String competitionId) {
    return client.getMap(
      '/api/national-team-engine/competitions/$competitionId/rental-pool',
      auth: false,
      query: <String, Object?>{'limit': 12, 'preseeded_only': true},
    );
  }

  Future<NationalTeamEntry> createRentalEntry({
    required String competitionId,
    required String countryCode,
    required String countryName,
  }) async {
    final Object? payload = await client.post(
      '/api/national-team-engine/competitions/$competitionId/rental-entry',
      body: <String, Object?>{
        'country_code': countryCode,
        'country_name': countryName,
        'metadata_json': <String, Object?>{
          'created_from': 'national_teams_screen',
        },
      },
    );
    return NationalTeamEntry.fromJson(payload);
  }

  Future<void> claimFreePlayers({required String entryId}) async {
    await client.post(
      '/api/national-team-engine/entries/$entryId/free-players/claim',
    );
  }

  Future<void> rentPlayer({
    required String entryId,
    required String playerId,
  }) async {
    await client.post(
      '/api/national-team-engine/entries/$entryId/rentals',
      body: <String, Object?>{'player_id': playerId},
    );
  }

  Future<void> submitBuiltSquad({
    required String competitionId,
    required String countryCode,
    required String countryName,
    required List<JsonMap> players,
  }) async {
    await client.post(
      '/api/national-team-engine/competitions/$competitionId/entries',
      body: <String, Object?>{
        'country_code': countryCode,
        'country_name': countryName,
        'squad': players
            .map(
              (JsonMap player) => <String, Object?>{
                'player_id': stringOrNullValue(player['player_id']),
                'player_name': stringValue(
                  player['player_name'],
                  fallback: 'Player',
                ),
                'age': _optionalInt(player['age']),
                'overall_rating': _optionalInt(player['overall_rating']),
                'position': stringOrNullValue(player['primary_position']),
                'metadata_json': <String, Object?>{
                  'source_bucket': stringOrNullValue(player['source_bucket']),
                  'loan_price_coin': player['loan_price_coin'],
                  'assigned_slot': stringOrNullValue(player['assigned_slot']),
                },
              },
            )
            .toList(growable: false),
      },
    );
  }

  Future<NationalTeamUserHistory> fetchUserHistory() async {
    final JsonMap payload = await client.getMap(
      '/api/national-team-engine/me/history',
    );
    return NationalTeamUserHistory.fromJson(payload);
  }

  Future<List<NationalRegenSeed>> listNationalRegens({
    int limit = 12,
    int? ageMin = 14,
    int? ageMax = 17,
    String? preseedBatch = 'u17_batch',
  }) async {
    final JsonMap payload = await client.getMap(
      '/regen-universe/national-regens',
      auth: false,
      query: compactQuery(<String, Object?>{
        'limit': limit,
        'age_min': ageMin,
        'age_max': ageMax,
        'preseed_batch': preseedBatch,
      }),
    );
    final List<Object?> items = GteJson.list(
      payload['items'] ?? const <Object?>[],
    );
    return items.map(NationalRegenSeed.fromJson).toList(growable: false);
  }

  Future<List<RegenScoutingFeedItem>> listRegenScoutingFeed({
    int limit = 8,
  }) async {
    final JsonMap payload = await client.getMap(
      '/regen-universe/scouting-feed',
      auth: false,
      query: compactQuery(<String, Object?>{'limit': limit}),
    );
    final List<Object?> items = GteJson.list(
      payload['items'] ?? const <Object?>[],
    );
    return items.map(RegenScoutingFeedItem.fromJson).toList(growable: false);
  }

  Future<JsonMap> buildAutoSquad({
    required String competitionId,
    required String countryCode,
    required double budgetCoin,
    int squadSize = 18,
    String ageGrade = 'Senior',
    required String tactic,
  }) async {
    final Object? payload = await client.post(
      '/api/national-team-engine/competitions/$competitionId/auto-build-squad',
      auth: false,
      body: <String, Object?>{
        'country_code': countryCode,
        'budget_coin': budgetCoin,
        'squadSize': squadSize,
        'ageGrade': ageGrade,
        'tactic': tactic,
      },
    );
    return jsonMap(payload, label: 'national team auto build');
  }

  Future<JsonMap?> fetchPreviousRoster({
    required String countryCode,
    required String ageGrade,
  }) async {
    final Object? payload = await client.request(
      'GET',
      '/api/national-team-engine/me/previous-roster',
      query: <String, Object?>{
        'country_code': countryCode,
        'age_grade': ageGrade,
      },
    );
    if (payload == null) {
      return null;
    }
    return jsonMap(payload, label: 'previous national roster');
  }
}

final Provider<NationalTeamsApi> nationalTeamsApiProvider =
    createFeatureApiProvider<NationalTeamsApi>(
      (GteAuthedApi client) => NationalTeamsApi(client: client),
    );

final FutureProvider<NationalTeamsHubData> nationalTeamsHubProvider =
    FutureProvider<NationalTeamsHubData>((Ref ref) async {
      final NationalTeamsApi api = ref.watch(nationalTeamsApiProvider);
      final bool authenticated = ref.watch(isAuthenticatedProvider);
      final Future<List<NationalTeamCompetition>> competitionsFuture =
          api.listCompetitions();
      final Future<List<NationalTeamCountryRankingRecord>> rankingsFuture =
          api.listRankings();
      final Future<List<NationalRegenSeed>> nationalRegensFuture =
          api.listNationalRegens();
      final Future<List<RegenScoutingFeedItem>> scoutingFeedFuture = api
          .listRegenScoutingFeed(limit: 8);
      NationalTeamUserHistory? history;
      if (authenticated) {
        try {
          history = await api.fetchUserHistory();
        } catch (_) {
          history = null;
        }
      }
      List<RegenScoutingFeedItem> regenScoutingFeed =
          const <RegenScoutingFeedItem>[];
      try {
        regenScoutingFeed = await scoutingFeedFuture;
      } catch (_) {
        regenScoutingFeed = const <RegenScoutingFeedItem>[];
      }
      return NationalTeamsHubData(
        competitions: await competitionsFuture,
        rankings: await rankingsFuture,
        nationalRegens: await nationalRegensFuture,
        regenScoutingFeed: regenScoutingFeed,
        history: history,
      );
    });

int? _optionalInt(Object? value) {
  if (value == null) {
    return null;
  }
  return intValue(value);
}

List<NationalRegenSeed> _sortedRegens(List<NationalRegenSeed> seeds) {
  return List<NationalRegenSeed>.of(seeds)
    ..sort((NationalRegenSeed left, NationalRegenSeed right) {
      final int potentialCompare = right.potentialRating.compareTo(
        left.potentialRating,
      );
      if (potentialCompare != 0) {
        return potentialCompare;
      }
      final int currentCompare = right.currentRating.compareTo(
        left.currentRating,
      );
      if (currentCompare != 0) {
        return currentCompare;
      }
      return right.growthCurve.compareTo(left.growthCurve);
    });
}

String _confederationCode(NationalRegenSeed seed) {
  final String? rawCode =
      seed.confederationCode ??
      stringOrNullValue(seed.metadata['confederation_code']) ??
      stringOrNullValue(seed.metadata['confederationCode']);
  final String normalized = rawCode?.trim().toUpperCase() ?? '';
  return normalized.isEmpty ? 'GLOBAL' : normalized;
}

String _confederationLabel(String code) {
  switch (code.trim().toUpperCase()) {
    case 'AFC':
      return 'AFC academy circuit';
    case 'CAF':
      return 'CAF academy circuit';
    case 'CONCACAF':
      return 'CONCACAF academy circuit';
    case 'CONMEBOL':
      return 'CONMEBOL academy circuit';
    case 'OFC':
      return 'OFC academy circuit';
    case 'UEFA':
      return 'UEFA academy circuit';
    default:
      return 'International academy circuit';
  }
}

double _averagePotential(List<NationalRegenSeed> seeds) {
  if (seeds.isEmpty) {
    return 0;
  }
  final int total = seeds.fold<int>(
    0,
    (int sum, NationalRegenSeed seed) => sum + seed.potentialRating,
  );
  return total / seeds.length;
}

List<String> _focusPositions(List<NationalRegenSeed> seeds) {
  final Map<String, int> counts = <String, int>{};
  for (final NationalRegenSeed seed in seeds) {
    final List<String> positions = <String>[
      seed.primaryPosition,
      ...seed.secondaryPositions,
    ];
    for (final String position in positions) {
      final String normalized = position.trim().toUpperCase();
      if (normalized.isEmpty) {
        continue;
      }
      counts[normalized] = (counts[normalized] ?? 0) + 1;
    }
  }
  final List<MapEntry<String, int>> entries =
      counts.entries.toList()
        ..sort((MapEntry<String, int> left, MapEntry<String, int> right) {
          final int countCompare = right.value.compareTo(left.value);
          if (countCompare != 0) {
            return countCompare;
          }
          return left.key.compareTo(right.key);
        });
  return entries
      .take(3)
      .map((MapEntry<String, int> entry) => entry.key)
      .toList(growable: false);
}

final dynamic nationalTeamCompetitionDetailProvider =
    FutureProvider.family<NationalTeamCompetitionDetailData, String>((
      Ref ref,
      String competitionId,
    ) async {
      final NationalTeamsApi api = ref.watch(nationalTeamsApiProvider);
      final NationalTeamsHubData hub = await ref.watch(
        nationalTeamsHubProvider.future,
      );
      NationalTeamCompetition? competition;
      for (final NationalTeamCompetition item in hub.competitions) {
        if (item.id == competitionId) {
          competition = item;
          break;
        }
      }
      competition ??= await api.fetchCompetition(competitionId);
      final Future<JsonMap> lifecycleFuture = api.fetchLifecycle(competitionId);
      final Future<JsonMap> presentationFuture = api.fetchPresentation(
        competitionId,
      );
      final Future<JsonMap> rentalPoolFuture = api.fetchRentalPoolPreview(
        competitionId,
      );
      return NationalTeamCompetitionDetailData(
        competition: competition,
        lifecycle: await lifecycleFuture,
        presentation: await presentationFuture,
        rentalPool: await rentalPoolFuture,
        history: hub.history,
      );
    });
