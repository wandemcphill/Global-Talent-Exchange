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
    required this.history,
  });

  final NationalTeamCompetition competition;
  final JsonMap lifecycle;
  final JsonMap presentation;
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
    required String tactic,
  }) async {
    final Object? payload = await client.post(
      '/api/national-team-engine/competitions/$competitionId/auto-build-squad',
      auth: false,
      body: <String, Object?>{
        'country_code': countryCode,
        'budget_coin': budgetCoin,
        'tactic': tactic,
      },
    );
    return jsonMap(payload, label: 'national team auto build');
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
      return NationalTeamCompetitionDetailData(
        competition: competition,
        lifecycle: await lifecycleFuture,
        presentation: await presentationFuture,
        history: hub.history,
      );
    });
