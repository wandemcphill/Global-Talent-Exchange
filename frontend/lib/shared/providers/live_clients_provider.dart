import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/competition_api.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/player_service.dart';
import '../../data/hosted_competition_api.dart';
import '../../features/streamer_tournament_engine/data/streamer_tournament_engine_repository.dart';
import 'auth_provider.dart';

final Provider<GteExchangeApiClient> exchangeApiClientProvider =
    Provider<GteExchangeApiClient>((Ref ref) {
      return GteExchangeApiClient.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        mode: ref.watch(criticalBackendModeProvider),
      );
    });

final Provider<PlayerService> livePlayerServiceProvider =
    Provider<PlayerService>((Ref ref) {
      return PlayerService(client: ref.watch(authedApiProvider));
    });

final Provider<CompetitionApi> competitionApiProvider =
    Provider<CompetitionApi>((Ref ref) {
      return CompetitionApi.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        mode: ref.watch(criticalBackendModeProvider),
      );
    });

final Provider<HostedCompetitionApi> hostedCompetitionApiProvider =
    Provider<HostedCompetitionApi>((Ref ref) {
      return HostedCompetitionApi.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        accessToken: ref.watch(accessTokenProvider),
        mode: ref.watch(criticalBackendModeProvider),
      );
    });

final Provider<StreamerTournamentEngineRepository>
streamerTournamentRepositoryProvider =
    Provider<StreamerTournamentEngineRepository>((Ref ref) {
      return StreamerTournamentEngineApiRepository.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        mode: ref.watch(criticalBackendModeProvider),
        accessToken: ref.watch(accessTokenProvider),
      );
    });
