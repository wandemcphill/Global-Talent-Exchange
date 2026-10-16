import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'creator_share_market_models.dart';

abstract class CreatorShareMarketRepository {
  Future<CreatorClubShareMarket> fetchMarket(String clubId);

  Future<CreatorClubShareMarket> issueMarket(
    String clubId,
    CreatorClubShareMarketIssueRequest request,
  );

  Future<CreatorClubSharePurchase> purchaseShares(
    String clubId,
    CreatorClubSharePurchaseRequest request,
  );

  Future<CreatorClubShareHolding?> fetchHolding(String clubId);

  Future<List<CreatorClubShareDistribution>> fetchDistributions(String clubId);

  Future<CreatorClubShareMarketControl> fetchControl();

  Future<CreatorClubShareMarketControl> updateControl(
    CreatorClubShareMarketControlUpdateRequest request,
  );
}

class CreatorShareMarketApiRepository implements CreatorShareMarketRepository {
  CreatorShareMarketApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory CreatorShareMarketApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return CreatorShareMarketApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<CreatorClubShareMarket> fetchMarket(String clubId) async {
    return CreatorClubShareMarket.fromJson(
      await _client.getMap('/api/creator/clubs/$clubId/fan-share-market'),
    );
  }

  @override
  Future<CreatorClubShareMarket> issueMarket(
    String clubId,
    CreatorClubShareMarketIssueRequest request,
  ) async {
    return CreatorClubShareMarket.fromJson(
      await _client.request(
        'POST',
        '/api/creator/clubs/$clubId/fan-share-market',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorClubSharePurchase> purchaseShares(
    String clubId,
    CreatorClubSharePurchaseRequest request,
  ) async {
    return CreatorClubSharePurchase.fromJson(
      await _client.request(
        'POST',
        '/api/creator/clubs/$clubId/fan-share-market/purchase',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorClubShareHolding?> fetchHolding(String clubId) async {
    final Object? payload = await _client.request(
      'GET',
      '/api/creator/clubs/$clubId/fan-share-market/holding',
    );
    if (payload == null) {
      return null;
    }
    return CreatorClubShareHolding.fromJson(payload);
  }

  @override
  Future<List<CreatorClubShareDistribution>> fetchDistributions(
    String clubId,
  ) async {
    return parseList(
      await _client
          .getList('/api/creator/clubs/$clubId/fan-share-market/distributions'),
      CreatorClubShareDistribution.fromJson,
      label: 'creator share distributions',
    );
  }

  @override
  Future<CreatorClubShareMarketControl> fetchControl() async {
    return CreatorClubShareMarketControl.fromJson(
      await _client.getMap('/api/admin/creator/fan-share-market/control'),
    );
  }

  @override
  Future<CreatorClubShareMarketControl> updateControl(
    CreatorClubShareMarketControlUpdateRequest request,
  ) async {
    return CreatorClubShareMarketControl.fromJson(
      await _client.request(
        'PUT',
        '/api/admin/creator/fan-share-market/control',
        body: request.toJson(),
      ),
    );
  }
}
