import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'fan_prediction_models.dart';

abstract class FanPredictionRepository {
  Future<FanPredictionFixture> fetchFixture(String matchId);

  Future<FanPredictionSubmission> submitPrediction(
    String matchId,
    FanPredictionSubmissionRequest request,
  );

  Future<FanPredictionLeaderboard> fetchMatchLeaderboard(
    String matchId,
    FanPredictionMatchLeaderboardQuery query,
  );

  Future<FanPredictionLeaderboard> fetchWeeklyLeaderboard(
    FanPredictionLeaderboardQuery query,
  );

  Future<FanPredictionLeaderboard> fetchCreatorClubWeeklyLeaderboard(
    String clubId,
    FanPredictionLeaderboardQuery query,
  );

  Future<FanPredictionTokenSummary> fetchTokenSummary();

  Future<List<FanPredictionSubmission>> listMySubmissions();

  Future<FanPredictionFixture> configureFixture(
    String matchId,
    FanPredictionFixtureConfigRequest request,
  );

  Future<FanPredictionFixture> settleFixture(
    String matchId,
    FanPredictionOutcomeOverrideRequest request,
  );
}

class FanPredictionApiRepository implements FanPredictionRepository {
  FanPredictionApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory FanPredictionApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return FanPredictionApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<FanPredictionFixture> fetchFixture(String matchId) async {
    return FanPredictionFixture.fromJson(
      await _client.getMap('/fan-predictions/matches/$matchId'),
    );
  }

  @override
  Future<FanPredictionSubmission> submitPrediction(
    String matchId,
    FanPredictionSubmissionRequest request,
  ) async {
    return FanPredictionSubmission.fromJson(
      await _client.request(
        'POST',
        '/fan-predictions/matches/$matchId/submissions',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<FanPredictionLeaderboard> fetchMatchLeaderboard(
    String matchId,
    FanPredictionMatchLeaderboardQuery query,
  ) async {
    return FanPredictionLeaderboard.fromJson(
      await _client.getMap(
        '/fan-predictions/matches/$matchId/leaderboard',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<FanPredictionLeaderboard> fetchWeeklyLeaderboard(
    FanPredictionLeaderboardQuery query,
  ) async {
    return FanPredictionLeaderboard.fromJson(
      await _client.getMap(
        '/fan-predictions/leaderboards/weekly',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<FanPredictionLeaderboard> fetchCreatorClubWeeklyLeaderboard(
    String clubId,
    FanPredictionLeaderboardQuery query,
  ) async {
    return FanPredictionLeaderboard.fromJson(
      await _client.getMap(
        '/fan-predictions/creator-clubs/$clubId/leaderboards/weekly',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<FanPredictionTokenSummary> fetchTokenSummary() async {
    return FanPredictionTokenSummary.fromJson(
      await _client.getMap('/fan-predictions/me/tokens'),
    );
  }

  @override
  Future<List<FanPredictionSubmission>> listMySubmissions() async {
    return parseList(
      await _client.getList('/fan-predictions/me/submissions'),
      FanPredictionSubmission.fromJson,
      label: 'fan prediction my submissions',
    );
  }

  @override
  Future<FanPredictionFixture> configureFixture(
    String matchId,
    FanPredictionFixtureConfigRequest request,
  ) async {
    return FanPredictionFixture.fromJson(
      await _client.request(
        'PUT',
        '/admin/fan-predictions/matches/$matchId/fixture',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<FanPredictionFixture> settleFixture(
    String matchId,
    FanPredictionOutcomeOverrideRequest request,
  ) async {
    return FanPredictionFixture.fromJson(
      await _client.request(
        'POST',
        '/admin/fan-predictions/matches/$matchId/settlement',
        body: request.toJson(),
      ),
    );
  }
}
