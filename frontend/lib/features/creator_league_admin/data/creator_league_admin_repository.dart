import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'creator_league_admin_models.dart';

abstract class CreatorLeagueAdminRepository {
  Future<CreatorLeagueConfig> fetchOverview();

  Future<CreatorLeagueConfig> updateConfig(
    CreatorLeagueConfigUpdateRequest request,
  );

  Future<CreatorLeagueConfig> createTier(
      CreatorLeagueTierCreateRequest request);

  Future<CreatorLeagueConfig> updateTier(
    String tierId,
    CreatorLeagueTierUpdateRequest request,
  );

  Future<CreatorLeagueConfig> deleteTier(String tierId);

  Future<CreatorLeagueConfig> resetStructure();

  Future<CreatorLeagueSeason> createSeason(
    CreatorLeagueSeasonCreateRequest request,
  );

  Future<CreatorLeagueSeason> fetchSeason(String seasonId);

  Future<CreatorLeagueSeason> pauseSeason(String seasonId);

  Future<List<CreatorLeagueStanding>> fetchStandings(String seasonTierId);

  Future<CreatorLeagueLivePriority> fetchLivePriority(
    CreatorLeagueLivePriorityQuery query,
  );

  Future<CreatorLeagueFinancialReport> fetchFinancialReport(
    CreatorLeagueFinancialReportQuery query,
  );

  Future<List<CreatorLeagueSettlement>> listSettlements(
    CreatorLeagueFinancialSettlementsQuery query,
  );

  Future<CreatorLeagueSettlement> approveSettlement(
    String settlementId,
    CreatorLeagueSettlementReviewRequest request,
  );
}

class CreatorLeagueAdminApiRepository implements CreatorLeagueAdminRepository {
  CreatorLeagueAdminApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory CreatorLeagueAdminApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return CreatorLeagueAdminApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<CreatorLeagueConfig> fetchOverview() async {
    return CreatorLeagueConfig.fromJson(
      await _client.getMap('/creator-league', auth: false),
    );
  }

  @override
  Future<CreatorLeagueConfig> updateConfig(
    CreatorLeagueConfigUpdateRequest request,
  ) async {
    return CreatorLeagueConfig.fromJson(
      await _client.request(
        'PATCH',
        '/creator-league/config',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorLeagueConfig> createTier(
    CreatorLeagueTierCreateRequest request,
  ) async {
    return CreatorLeagueConfig.fromJson(
      await _client.request(
        'POST',
        '/creator-league/tiers',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorLeagueConfig> updateTier(
    String tierId,
    CreatorLeagueTierUpdateRequest request,
  ) async {
    return CreatorLeagueConfig.fromJson(
      await _client.request(
        'PATCH',
        '/creator-league/tiers/$tierId',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorLeagueConfig> deleteTier(String tierId) async {
    return CreatorLeagueConfig.fromJson(
      await _client.request(
        'DELETE',
        '/creator-league/tiers/$tierId',
      ),
    );
  }

  @override
  Future<CreatorLeagueConfig> resetStructure() async {
    return CreatorLeagueConfig.fromJson(
      await _client.request('POST', '/creator-league/reset'),
    );
  }

  @override
  Future<CreatorLeagueSeason> createSeason(
    CreatorLeagueSeasonCreateRequest request,
  ) async {
    return CreatorLeagueSeason.fromJson(
      await _client.request(
        'POST',
        '/creator-league/seasons',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorLeagueSeason> fetchSeason(String seasonId) async {
    return CreatorLeagueSeason.fromJson(
      await _client.getMap('/creator-league/seasons/$seasonId', auth: false),
    );
  }

  @override
  Future<CreatorLeagueSeason> pauseSeason(String seasonId) async {
    return CreatorLeagueSeason.fromJson(
      await _client.request('POST', '/creator-league/seasons/$seasonId/pause'),
    );
  }

  @override
  Future<List<CreatorLeagueStanding>> fetchStandings(
      String seasonTierId) async {
    return parseList(
      await _client.getList(
        '/creator-league/season-tiers/$seasonTierId/standings',
        auth: false,
      ),
      CreatorLeagueStanding.fromJson,
      label: 'creator league standings',
    );
  }

  @override
  Future<CreatorLeagueLivePriority> fetchLivePriority(
    CreatorLeagueLivePriorityQuery query,
  ) async {
    return CreatorLeagueLivePriority.fromJson(
      await _client.getMap(
        '/creator-league/live-priority',
        query: query.toQuery(),
        auth: false,
      ),
    );
  }

  @override
  Future<CreatorLeagueFinancialReport> fetchFinancialReport(
    CreatorLeagueFinancialReportQuery query,
  ) async {
    return CreatorLeagueFinancialReport.fromJson(
      await _client.getMap(
        '/creator-league/financial-report',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<List<CreatorLeagueSettlement>> listSettlements(
    CreatorLeagueFinancialSettlementsQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/creator-league/financial-settlements',
        query: query.toQuery(),
      ),
      CreatorLeagueSettlement.fromJson,
      label: 'creator league financial settlements',
    );
  }

  @override
  Future<CreatorLeagueSettlement> approveSettlement(
    String settlementId,
    CreatorLeagueSettlementReviewRequest request,
  ) async {
    return CreatorLeagueSettlement.fromJson(
      await _client.request(
        'POST',
        '/creator-league/financial-settlements/$settlementId/approve',
        body: request.toJson(),
      ),
    );
  }
}
