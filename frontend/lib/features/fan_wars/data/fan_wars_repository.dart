import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'fan_wars_models.dart';

abstract class FanWarsRepository {
  Future<FanWarLeaderboard> fetchLeaderboard(
    String boardType,
    FanWarsPeriodQuery query,
  );

  Future<RivalryLeaderboard> fetchRivalries(
    String boardType,
    FanWarsPeriodQuery query,
  );

  Future<FanWarDashboard> fetchDashboard(
    String profileId,
    FanWarsDashboardQuery query,
  );

  Future<NationsCupOverview> fetchNationsCup(String competitionId);

  Future<FanWarProfile> upsertProfile(FanWarProfileUpsertRequest request);

  Future<List<FanWarProfile>> linkRivals(
    String profileId,
    String rivalProfileId,
  );

  Future<List<JsonMap>> recordPoints(FanWarPointRecordRequest request);

  Future<CreatorCountryAssignment> assignCreatorCountry(
    CreatorCountryAssignmentRequest request,
  );

  Future<NationsCupOverview> createNationsCup(NationsCupCreateRequest request);

  Future<NationsCupOverview> advanceNationsCup(
    String competitionId, {
    bool force = false,
  });
}

class FanWarsApiRepository implements FanWarsRepository {
  FanWarsApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory FanWarsApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return FanWarsApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<FanWarLeaderboard> fetchLeaderboard(
    String boardType,
    FanWarsPeriodQuery query,
  ) async {
    return FanWarLeaderboard.fromJson(
      await _client.getMap(
        '/fan-wars/leaderboards/$boardType',
        query: query.toQuery(),
        auth: false,
      ),
    );
  }

  @override
  Future<RivalryLeaderboard> fetchRivalries(
    String boardType,
    FanWarsPeriodQuery query,
  ) async {
    return RivalryLeaderboard.fromJson(
      await _client.getMap(
        '/fan-wars/rivalries/$boardType',
        query: query.toQuery(),
        auth: false,
      ),
    );
  }

  @override
  Future<FanWarDashboard> fetchDashboard(
    String profileId,
    FanWarsDashboardQuery query,
  ) async {
    return FanWarDashboard.fromJson(
      await _client.getMap(
        '/fan-wars/profiles/$profileId/dashboard',
        query: query.toQuery(),
        auth: false,
      ),
    );
  }

  @override
  Future<NationsCupOverview> fetchNationsCup(String competitionId) async {
    return NationsCupOverview.fromJson(
      await _client.getMap('/fan-wars/nations-cup/$competitionId', auth: false),
    );
  }

  @override
  Future<FanWarProfile> upsertProfile(
      FanWarProfileUpsertRequest request) async {
    return FanWarProfile.fromJson(
      await _client.request(
        'PUT',
        '/admin/fan-wars/profiles',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<FanWarProfile>> linkRivals(
    String profileId,
    String rivalProfileId,
  ) async {
    return parseList(
      await _client.request(
        'POST',
        '/admin/fan-wars/profiles/$profileId/rivals/$rivalProfileId',
      ),
      FanWarProfile.fromJson,
      label: 'fan war linked rivals',
    );
  }

  @override
  Future<List<JsonMap>> recordPoints(FanWarPointRecordRequest request) async {
    return jsonMapList(
      await _client.request(
        'POST',
        '/admin/fan-wars/points',
        body: request.toJson(),
      ),
      label: 'fan war points',
    );
  }

  @override
  Future<CreatorCountryAssignment> assignCreatorCountry(
    CreatorCountryAssignmentRequest request,
  ) async {
    return CreatorCountryAssignment.fromJson(
      await _client.request(
        'POST',
        '/admin/fan-wars/creator-country-assignments',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<NationsCupOverview> createNationsCup(
    NationsCupCreateRequest request,
  ) async {
    return NationsCupOverview.fromJson(
      await _client.request(
        'POST',
        '/admin/fan-wars/nations-cup',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<NationsCupOverview> advanceNationsCup(
    String competitionId, {
    bool force = false,
  }) async {
    return NationsCupOverview.fromJson(
      await _client.request(
        'POST',
        '/admin/fan-wars/nations-cup/$competitionId/advance',
        query: <String, Object?>{'force': force},
      ),
    );
  }
}
