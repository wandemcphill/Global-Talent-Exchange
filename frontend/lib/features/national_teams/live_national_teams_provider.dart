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

class NationalTeamsHubData {
  const NationalTeamsHubData({
    required this.competitions,
    required this.rankings,
    required this.nationalRegens,
    required this.history,
  });

  final List<NationalTeamCompetition> competitions;
  final List<NationalTeamCountryRankingRecord> rankings;
  final List<NationalRegenSeed> nationalRegens;
  final NationalTeamUserHistory? history;
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
      NationalTeamUserHistory? history;
      if (authenticated) {
        try {
          history = await api.fetchUserHistory();
        } catch (_) {
          history = null;
        }
      }
      return NationalTeamsHubData(
        competitions: await competitionsFuture,
        rankings: await rankingsFuture,
        nationalRegens: await nationalRegensFuture,
        history: history,
      );
    });

int? _optionalInt(Object? value) {
  if (value == null) {
    return null;
  }
  return intValue(value);
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
