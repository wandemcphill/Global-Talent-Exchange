import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/features/compete/repositories/competition_api.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/compete/repositories/hosted_competition_api.dart';
import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';
import 'package:gte_frontend/features/compete/repositories/streamer_tournament_engine_repository.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/compete/domain/hosted_competition_models.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/live_clients_provider.dart';
import 'package:gte_frontend/features/compete/domain/streamer_tournament_engine_models.dart';

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
    required this.standingsFeed,
    required this.fixturesFeed,
  });

  final CompetitionSummary competition;
  final CompetitionFinancialSummary financials;
  final CompetitionBackendFeed<JsonMap> standingsFeed;
  final CompetitionBackendFeed<JsonMap> fixturesFeed;

  List<JsonMap> get standings => standingsFeed.items;

  List<JsonMap> get fixtures => fixturesFeed.items;
}

class HostedCompetitionDetailBundle {
  const HostedCompetitionDetailBundle({
    required this.detail,
    required this.finance,
    required this.standingsFeed,
    required this.invites,
  });

  final HostedCompetitionDetail detail;
  final HostedCompetitionFinance finance;
  final CompetitionBackendFeed<HostedCompetitionStanding> standingsFeed;
  final List<HostedCompetitionInvite> invites;

  List<HostedCompetitionStanding> get standings => standingsFeed.items;
}

enum CompetitionBackendFeedState { synced, empty, syncing, blocked, degraded }

class CompetitionBackendFeed<T> {
  const CompetitionBackendFeed({
    required this.state,
    required this.items,
    this.message,
  });

  final CompetitionBackendFeedState state;
  final List<T> items;
  final String? message;

  bool get hasAuthoritativeItems =>
      state == CompetitionBackendFeedState.synced && items.isNotEmpty;

  String countLabel(String label) {
    switch (state) {
      case CompetitionBackendFeedState.synced:
        return '$label ${items.length}';
      case CompetitionBackendFeedState.empty:
        return '$label empty';
      case CompetitionBackendFeedState.syncing:
        return '$label syncing';
      case CompetitionBackendFeedState.blocked:
        return '$label blocked';
      case CompetitionBackendFeedState.degraded:
        return '$label degraded';
    }
  }

  static CompetitionBackendFeed<T> fromItems<T>(List<T> items) {
    return CompetitionBackendFeed<T>(
      state:
          items.isEmpty
              ? CompetitionBackendFeedState.empty
              : CompetitionBackendFeedState.synced,
      items: items,
    );
  }

  static CompetitionBackendFeed<T> blocked<T>(Object error) {
    return CompetitionBackendFeed<T>(
      state: CompetitionBackendFeedState.blocked,
      items: <T>[],
      message: AppFeedback.messageFor(error),
    );
  }
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
      final HostedCompetitionApi hostedApi = ref.watch(
        hostedCompetitionApiProvider,
      );
      final StreamerTournamentEngineRepository streamerApi = ref.watch(
        streamerTournamentRepositoryProvider,
      );
      final String? userId = ref.watch(currentUserIdProvider);
      final CompetitionListResponse competitionList = await competitionApi
          .fetchCompetitions(userId: userId);
      final StreamerTournamentList streamerTournaments =
          await streamerApi.listPublicTournaments();
      final List<HostedCompetition> hostedCompetitions =
          await hostedApi.listCompetitions();
      return CompetitionHubData(
        gtexCompetitions: competitionList.items
            .where((CompetitionSummary item) => item.isGtexHosted)
            .toList(growable: false),
        userCompetitions: competitionList.items
            .where((CompetitionSummary item) => item.isUserHosted)
            .toList(growable: false),
        hostedCompetitions: hostedCompetitions,
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
      CompetitionBackendFeed<JsonMap> standingsFeed =
          const CompetitionBackendFeed<JsonMap>(
            state: CompetitionBackendFeedState.syncing,
            items: <JsonMap>[],
          );
      CompetitionBackendFeed<JsonMap> fixturesFeed =
          const CompetitionBackendFeed<JsonMap>(
            state: CompetitionBackendFeedState.syncing,
            items: <JsonMap>[],
          );
      try {
        final List<JsonMap> standings = (await api.getList(
              '/api/competitions/$competitionId/standings',
              auth: false,
            ))
            .map((dynamic item) => jsonMap(item, label: 'standing'))
            .toList(growable: false);
        standingsFeed = CompetitionBackendFeed.fromItems(standings);
      } catch (error) {
        standingsFeed = CompetitionBackendFeed.blocked(error);
      }
      try {
        final List<JsonMap> fixtures = (await api.getList(
              '/api/competitions/$competitionId/fixtures',
              auth: false,
            ))
            .map((dynamic item) => jsonMap(item, label: 'fixture'))
            .toList(growable: false);
        fixturesFeed = CompetitionBackendFeed.fromItems(fixtures);
      } catch (_) {
        fixturesFeed = const CompetitionBackendFeed<JsonMap>(
          state: CompetitionBackendFeedState.blocked,
          items: <JsonMap>[],
          message: 'Backend fixtures route is unavailable.',
        );
      }
      return GtexCompetitionDetailBundle(
        competition: competition,
        financials: financials,
        standingsFeed: standingsFeed,
        fixturesFeed: fixturesFeed,
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
      CompetitionBackendFeed<HostedCompetitionStanding> standingsFeed;
      try {
        standingsFeed = CompetitionBackendFeed.fromItems(
          await hostedApi.listStandings(competitionId),
        );
      } catch (error) {
        standingsFeed = CompetitionBackendFeed.blocked(error);
      }
      final bool isAuthenticated = ref.watch(isAuthenticatedProvider);
      final List<HostedCompetitionInvite> invites =
          isAuthenticated
              ? await hostedApi.listInvites(competitionId)
              : const <HostedCompetitionInvite>[];
      return HostedCompetitionDetailBundle(
        detail: detail,
        finance: finance,
        standingsFeed: standingsFeed,
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
