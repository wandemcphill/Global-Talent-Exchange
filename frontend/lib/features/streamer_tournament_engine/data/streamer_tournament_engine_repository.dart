import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'streamer_tournament_engine_models.dart';

abstract class StreamerTournamentEngineRepository {
  Future<StreamerTournamentList> listPublicTournaments();

  Future<StreamerTournamentList> listMyTournaments();

  Future<StreamerTournament> createTournament(
    StreamerTournamentCreateRequest request,
  );

  Future<StreamerTournament> fetchTournament(String tournamentId);

  Future<StreamerTournament> updateTournament(
    String tournamentId,
    StreamerTournamentUpdateRequest request,
  );

  Future<StreamerTournament> replaceRewardPlan(
    String tournamentId,
    StreamerTournamentRewardPlanReplaceRequest request,
  );

  Future<StreamerTournament> createInvite(
    String tournamentId,
    StreamerTournamentInviteCreateRequest request,
  );

  Future<StreamerTournament> joinTournament(
    String tournamentId,
    StreamerTournamentJoinRequest request,
  );

  Future<StreamerTournament> publishTournament(
    String tournamentId,
    StreamerTournamentPublishRequest request,
  );

  Future<StreamerTournamentPolicy> fetchPolicy();

  Future<StreamerTournamentPolicy> upsertPolicy(
    StreamerTournamentPolicyUpsertRequest request,
  );

  Future<StreamerTournament> reviewTournament(
    String tournamentId,
    StreamerTournamentReviewRequest request,
  );

  Future<List<StreamerTournamentRiskSignal>> listRiskSignals();

  Future<StreamerTournamentRiskSignal> reviewRiskSignal(
    String signalId,
    StreamerTournamentRiskReviewRequest request,
  );

  Future<StreamerTournamentSettlement> settleTournament(
    String tournamentId,
    StreamerTournamentSettleRequest request,
  );
}

class StreamerTournamentEngineApiRepository
    implements StreamerTournamentEngineRepository {
  StreamerTournamentEngineApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory StreamerTournamentEngineApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return StreamerTournamentEngineApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<StreamerTournamentList> listPublicTournaments() async {
    return StreamerTournamentList.fromJson(
      await _client.getMap('/streamer-tournaments', auth: false),
    );
  }

  @override
  Future<StreamerTournamentList> listMyTournaments() async {
    return StreamerTournamentList.fromJson(
      await _client.getMap('/streamer-tournaments/mine'),
    );
  }

  @override
  Future<StreamerTournament> createTournament(
    StreamerTournamentCreateRequest request,
  ) async {
    return StreamerTournament.fromJson(
      await _client.request(
        'POST',
        '/streamer-tournaments',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournament> fetchTournament(String tournamentId) async {
    return StreamerTournament.fromJson(
      await _client.getMap('/streamer-tournaments/$tournamentId', auth: false),
    );
  }

  @override
  Future<StreamerTournament> updateTournament(
    String tournamentId,
    StreamerTournamentUpdateRequest request,
  ) async {
    return StreamerTournament.fromJson(
      await _client.request(
        'PATCH',
        '/streamer-tournaments/$tournamentId',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournament> replaceRewardPlan(
    String tournamentId,
    StreamerTournamentRewardPlanReplaceRequest request,
  ) async {
    return StreamerTournament.fromJson(
      await _client.request(
        'PUT',
        '/streamer-tournaments/$tournamentId/rewards',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournament> createInvite(
    String tournamentId,
    StreamerTournamentInviteCreateRequest request,
  ) async {
    return StreamerTournament.fromJson(
      await _client.request(
        'POST',
        '/streamer-tournaments/$tournamentId/invites',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournament> joinTournament(
    String tournamentId,
    StreamerTournamentJoinRequest request,
  ) async {
    return StreamerTournament.fromJson(
      await _client.request(
        'POST',
        '/streamer-tournaments/$tournamentId/join',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournament> publishTournament(
    String tournamentId,
    StreamerTournamentPublishRequest request,
  ) async {
    return StreamerTournament.fromJson(
      await _client.request(
        'POST',
        '/streamer-tournaments/$tournamentId/publish',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournamentPolicy> fetchPolicy() async {
    return StreamerTournamentPolicy.fromJson(
      await _client.getMap('/admin/streamer-tournaments/policy'),
    );
  }

  @override
  Future<StreamerTournamentPolicy> upsertPolicy(
    StreamerTournamentPolicyUpsertRequest request,
  ) async {
    return StreamerTournamentPolicy.fromJson(
      await _client.request(
        'PUT',
        '/admin/streamer-tournaments/policy',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournament> reviewTournament(
    String tournamentId,
    StreamerTournamentReviewRequest request,
  ) async {
    return StreamerTournament.fromJson(
      await _client.request(
        'POST',
        '/admin/streamer-tournaments/$tournamentId/review',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<StreamerTournamentRiskSignal>> listRiskSignals() async {
    return parseList(
      await _client.getList('/admin/streamer-tournaments/risk-signals'),
      StreamerTournamentRiskSignal.fromJson,
      label: 'streamer tournament risk signals',
    );
  }

  @override
  Future<StreamerTournamentRiskSignal> reviewRiskSignal(
    String signalId,
    StreamerTournamentRiskReviewRequest request,
  ) async {
    return StreamerTournamentRiskSignal.fromJson(
      await _client.request(
        'POST',
        '/admin/streamer-tournaments/risk-signals/$signalId/review',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<StreamerTournamentSettlement> settleTournament(
    String tournamentId,
    StreamerTournamentSettleRequest request,
  ) async {
    return StreamerTournamentSettlement.fromJson(
      await _client.request(
        'POST',
        '/admin/streamer-tournaments/$tournamentId/settle',
        body: request.toJson(),
      ),
    );
  }
}
