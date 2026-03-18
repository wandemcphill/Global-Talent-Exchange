import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'football_world_simulation_models.dart';

abstract class FootballWorldSimulationRepository {
  Future<List<FootballCulture>> listCultures(FootballCultureListQuery query);

  Future<ClubWorldContext> fetchClubContext(String clubId);

  Future<CompetitionWorldContext> fetchCompetitionContext(
    String competitionId,
  );

  Future<List<WorldNarrative>> listNarratives(WorldNarrativeListQuery query);

  Future<FootballCulture> upsertCulture(
    String cultureKey,
    FootballCultureUpsertRequest request,
  );

  Future<ClubWorldContext> upsertClubContext(
    String clubId,
    ClubWorldProfileUpsertRequest request,
  );

  Future<WorldNarrative> upsertNarrative(
    String narrativeSlug,
    WorldNarrativeUpsertRequest request,
  );
}

class FootballWorldSimulationApiRepository
    implements FootballWorldSimulationRepository {
  FootballWorldSimulationApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory FootballWorldSimulationApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return FootballWorldSimulationApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<List<FootballCulture>> listCultures(
      FootballCultureListQuery query) async {
    return parseList(
      await _client.getList('/api/world/cultures',
          query: query.toQuery(), auth: false),
      FootballCulture.fromJson,
      label: 'football cultures',
    );
  }

  @override
  Future<ClubWorldContext> fetchClubContext(String clubId) async {
    return ClubWorldContext.fromJson(
      await _client.getMap('/api/world/clubs/$clubId/context', auth: false),
    );
  }

  @override
  Future<CompetitionWorldContext> fetchCompetitionContext(
    String competitionId,
  ) async {
    return CompetitionWorldContext.fromJson(
      await _client.getMap(
        '/api/world/competitions/$competitionId/context',
        auth: false,
      ),
    );
  }

  @override
  Future<List<WorldNarrative>> listNarratives(
    WorldNarrativeListQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/api/world/narratives',
        query: query.toQuery(),
        auth: false,
      ),
      WorldNarrative.fromJson,
      label: 'world narratives',
    );
  }

  @override
  Future<FootballCulture> upsertCulture(
    String cultureKey,
    FootballCultureUpsertRequest request,
  ) async {
    return FootballCulture.fromJson(
      await _client.request(
        'PUT',
        '/admin/world/cultures/$cultureKey',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<ClubWorldContext> upsertClubContext(
    String clubId,
    ClubWorldProfileUpsertRequest request,
  ) async {
    return ClubWorldContext.fromJson(
      await _client.request(
        'PUT',
        '/admin/world/clubs/$clubId/context',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<WorldNarrative> upsertNarrative(
    String narrativeSlug,
    WorldNarrativeUpsertRequest request,
  ) async {
    return WorldNarrative.fromJson(
      await _client.request(
        'PUT',
        '/admin/world/narratives/$narrativeSlug',
        body: request.toJson(),
      ),
    );
  }
}
