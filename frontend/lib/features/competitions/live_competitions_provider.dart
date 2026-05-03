import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/competition_api.dart';
import '../../data/gte_authed_api.dart';
import '../../data/hosted_competition_api.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../features/streamer_tournament_engine/data/streamer_tournament_engine_repository.dart';
import '../../models/competition_models.dart';
import '../../models/hosted_competition_models.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
import '../streamer_tournament_engine/data/streamer_tournament_engine_models.dart';

enum CompetitionFamilyRoute { gtex, hosted, streamer }

extension CompetitionFamilyRouteX on CompetitionFamilyRoute {
  String get pathSegment {
    return switch (this) {
      CompetitionFamilyRoute.gtex => 'gtex',
      CompetitionFamilyRoute.hosted => 'hosted',
      CompetitionFamilyRoute.streamer => 'streamer',
    };
  }

  String get label {
    return switch (this) {
      CompetitionFamilyRoute.gtex => 'GTEX Competitions',
      CompetitionFamilyRoute.hosted => 'User Competitions',
      CompetitionFamilyRoute.streamer => 'E-Games',
    };
  }

  static CompetitionFamilyRoute fromSegment(String value) {
    switch (value.trim().toLowerCase()) {
      case 'hosted':
        return CompetitionFamilyRoute.hosted;
      case 'streamer':
        return CompetitionFamilyRoute.streamer;
      default:
        return CompetitionFamilyRoute.gtex;
    }
  }
}

CompetitionFamilyRoute competitionFamilyRouteFromSegment(String value) {
  switch (value.trim().toLowerCase()) {
    case 'hosted':
      return CompetitionFamilyRoute.hosted;
    case 'streamer':
      return CompetitionFamilyRoute.streamer;
    default:
      return CompetitionFamilyRoute.gtex;
  }
}

class CompetitionHubData {
  const CompetitionHubData({
    required this.gtexCompetitions,
    required this.hostedCompetitions,
    required this.streamerTournaments,
    this.userCompetitions = const <CompetitionSummary>[],
  });

  final List<CompetitionSummary> gtexCompetitions;
  final List<CompetitionSummary> userCompetitions;
  final List<HostedCompetition> hostedCompetitions;
  final List<StreamerTournament> streamerTournaments;
}

class GtexCompetitionDetailBundle {
  const GtexCompetitionDetailBundle({
    required this.competition,
    required this.financials,
    required this.standings,
    required this.fixtures,
  });

  final CompetitionSummary competition;
  final CompetitionFinancialSummary financials;
  final List<JsonMap> standings;
  final List<JsonMap> fixtures;
}

class HostedCompetitionDetailBundle {
  const HostedCompetitionDetailBundle({
    required this.detail,
    required this.finance,
    required this.standings,
    required this.invites,
  });

  final HostedCompetitionDetail detail;
  final HostedCompetitionFinance finance;
  final List<HostedCompetitionStanding> standings;
  final List<HostedCompetitionInvite> invites;
}

class StreamerTournamentDetailBundle {
  const StreamerTournamentDetailBundle({
    required this.tournament,
    required this.currentSeason,
  });

  final StreamerTournament tournament;
  final LeaderboardSeason currentSeason;
}

final FutureProvider<CompetitionHubData> competitionHubProvider =
    FutureProvider<CompetitionHubData>((Ref ref) async {
      final CompetitionApi competitionApi = ref.watch(competitionApiProvider);
      final StreamerTournamentEngineRepository streamerApi = ref.watch(
        streamerTournamentRepositoryProvider,
      );
      final String? userId = ref.watch(currentUserIdProvider);
      final CompetitionListResponse competitionList = await competitionApi
          .fetchCompetitions(userId: userId);
      final StreamerTournamentList streamerTournaments =
          await streamerApi.listPublicTournaments();
      return CompetitionHubData(
        gtexCompetitions: competitionList.items
            .where((CompetitionSummary item) => item.isGtexHosted)
            .toList(growable: false),
        userCompetitions: competitionList.items
            .where((CompetitionSummary item) => item.isUserHosted)
            .toList(growable: false),
        hostedCompetitions: const <HostedCompetition>[],
        streamerTournaments: streamerTournaments.tournaments,
      );
    });

final gtexCompetitionDetailProvider =
    FutureProvider.family<GtexCompetitionDetailBundle, String>((
      Ref ref,
      String competitionId,
    ) async {
      final CompetitionApi competitionApi = ref.watch(competitionApiProvider);
      final GteAuthedApi api = ref.watch(authedApiProvider);
      final String? userId = ref.watch(currentUserIdProvider);
      final CompetitionSummary competition = await competitionApi
          .fetchCompetition(competitionId, userId: userId);
      final CompetitionFinancialSummary financials = await competitionApi
          .fetchFinancials(competitionId, userId: userId);
      List<JsonMap> standings = const <JsonMap>[];
      List<JsonMap> fixtures = const <JsonMap>[];
      try {
        standings = (await api.getList(
              '/api/competitions/$competitionId/standings',
              auth: false,
            ))
            .map((dynamic item) => jsonMap(item, label: 'standing'))
            .toList(growable: false);
      } catch (_) {}
      try {
        fixtures = (await api.getList(
              '/api/competitions/$competitionId/fixtures',
              auth: false,
            ))
            .map((dynamic item) => jsonMap(item, label: 'fixture'))
            .toList(growable: false);
      } catch (_) {}
      return GtexCompetitionDetailBundle(
        competition: competition,
        financials: financials,
        standings: standings,
        fixtures: fixtures,
      );
    });

final hostedCompetitionDetailProvider =
    FutureProvider.family<HostedCompetitionDetailBundle, String>((
      Ref ref,
      String competitionId,
    ) async {
      final HostedCompetitionApi hostedApi = ref.watch(
        hostedCompetitionApiProvider,
      );
      final HostedCompetitionDetail detail = await hostedApi.fetchDetail(
        competitionId,
      );
      final HostedCompetitionFinance finance = await hostedApi.fetchFinance(
        competitionId,
      );
      final List<HostedCompetitionStanding> standings = await hostedApi
          .listStandings(competitionId);
      final bool isAuthenticated = ref.watch(isAuthenticatedProvider);
      final List<HostedCompetitionInvite> invites =
          isAuthenticated
              ? await hostedApi.listInvites(competitionId)
              : const <HostedCompetitionInvite>[];
      return HostedCompetitionDetailBundle(
        detail: detail,
        finance: finance,
        standings: standings,
        invites: invites,
      );
    });

final streamerTournamentDetailProvider =
    FutureProvider.family<StreamerTournamentDetailBundle, String>((
      Ref ref,
      String tournamentId,
    ) async {
      final StreamerTournamentEngineRepository streamerApi = ref.watch(
        streamerTournamentRepositoryProvider,
      );
      final StreamerTournament tournament = await streamerApi.fetchTournament(
        tournamentId,
      );
      final LeaderboardSeason season = await streamerApi.fetchCurrentSeason();
      return StreamerTournamentDetailBundle(
        tournament: tournament,
        currentSeason: season,
      );
    });
