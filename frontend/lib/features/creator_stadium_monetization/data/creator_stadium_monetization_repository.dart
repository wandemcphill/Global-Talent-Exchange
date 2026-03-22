import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'creator_stadium_monetization_models.dart';

abstract class CreatorStadiumMonetizationRepository {
  Future<List<CreatorBroadcastMode>> listBroadcastModes();

  Future<CreatorMatchAccess> fetchMatchAccess(
    String matchId,
    CreatorMatchAccessQuery query,
  );

  Future<CreatorBroadcastPurchase> purchaseMatchBroadcast(
    String matchId,
    CreatorBroadcastPurchaseRequest request,
  );

  Future<CreatorSeasonPass> purchaseSeasonPass(
    CreatorSeasonPassCreateRequest request,
  );

  Future<List<CreatorSeasonPass>> listMySeasonPasses();

  Future<CreatorStadiumMonetization> fetchClubStadium(
    String clubId,
    CreatorClubStadiumQuery query,
  );

  Future<CreatorStadiumMonetization> updateClubStadium(
    String clubId,
    CreatorStadiumConfigUpdateRequest request,
  );

  Future<CreatorMatchStadiumOffer> fetchMatchStadiumOffer(String matchId);

  Future<CreatorStadiumTicketPurchase> purchaseTicket(
    String matchId,
    CreatorStadiumTicketPurchaseRequest request,
  );

  Future<List<CreatorStadiumPlacement>> listPlacements(String matchId);

  Future<CreatorStadiumPlacement> createPlacement(
    String matchId,
    CreatorStadiumPlacementCreateRequest request,
  );

  Future<CreatorMatchGift> sendGift(
    String matchId,
    CreatorMatchGiftRequest request,
  );

  Future<CreatorAnalyticsDashboard> fetchMatchAnalytics(
    String matchId,
    CreatorMatchAnalyticsQuery query,
  );

  Future<CreatorAnalyticsDashboard> fetchAdminMatchAnalytics(
    String matchId,
    CreatorMatchAnalyticsQuery query,
  );

  Future<CreatorRevenueSettlement> settleMatchRevenue(String matchId);

  Future<CreatorStadiumControl> fetchStadiumControl();

  Future<CreatorStadiumControl> updateStadiumControl(
    CreatorStadiumControlUpdateRequest request,
  );

  Future<CreatorStadiumProfile> updateStadiumLevel(
    String clubId,
    CreatorStadiumLevelUpdateRequest request,
  );
}

class CreatorStadiumMonetizationApiRepository
    implements CreatorStadiumMonetizationRepository {
  CreatorStadiumMonetizationApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory CreatorStadiumMonetizationApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return CreatorStadiumMonetizationApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<List<CreatorBroadcastMode>> listBroadcastModes() async {
    return parseList(
      await _client.getList('/media-engine/creator-league/broadcast-modes'),
      CreatorBroadcastMode.fromJson,
      label: 'creator broadcast modes',
    );
  }

  @override
  Future<CreatorMatchAccess> fetchMatchAccess(
    String matchId,
    CreatorMatchAccessQuery query,
  ) async {
    return CreatorMatchAccess.fromJson(
      await _client.getMap(
        '/media-engine/creator-league/matches/$matchId/access',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<CreatorBroadcastPurchase> purchaseMatchBroadcast(
    String matchId,
    CreatorBroadcastPurchaseRequest request,
  ) async {
    return CreatorBroadcastPurchase.fromJson(
      await _client.request(
        'POST',
        '/media-engine/creator-league/matches/$matchId/purchase',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorSeasonPass> purchaseSeasonPass(
    CreatorSeasonPassCreateRequest request,
  ) async {
    return CreatorSeasonPass.fromJson(
      await _client.request(
        'POST',
        '/media-engine/creator-league/season-passes',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<CreatorSeasonPass>> listMySeasonPasses() async {
    return parseList(
      await _client.getList('/media-engine/creator-league/season-passes/me'),
      CreatorSeasonPass.fromJson,
      label: 'creator season passes',
    );
  }

  @override
  Future<CreatorStadiumMonetization> fetchClubStadium(
    String clubId,
    CreatorClubStadiumQuery query,
  ) async {
    return CreatorStadiumMonetization.fromJson(
      await _client.getMap(
        '/media-engine/creator-league/clubs/$clubId/stadium',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<CreatorStadiumMonetization> updateClubStadium(
    String clubId,
    CreatorStadiumConfigUpdateRequest request,
  ) async {
    return CreatorStadiumMonetization.fromJson(
      await _client.request(
        'PUT',
        '/media-engine/creator-league/clubs/$clubId/stadium',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorMatchStadiumOffer> fetchMatchStadiumOffer(
    String matchId,
  ) async {
    return CreatorMatchStadiumOffer.fromJson(
      await _client
          .getMap('/media-engine/creator-league/matches/$matchId/stadium'),
    );
  }

  @override
  Future<CreatorStadiumTicketPurchase> purchaseTicket(
    String matchId,
    CreatorStadiumTicketPurchaseRequest request,
  ) async {
    return CreatorStadiumTicketPurchase.fromJson(
      await _client.request(
        'POST',
        '/media-engine/creator-league/matches/$matchId/tickets',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<CreatorStadiumPlacement>> listPlacements(String matchId) async {
    return parseList(
      await _client.getList(
        '/media-engine/creator-league/matches/$matchId/stadium/placements',
      ),
      CreatorStadiumPlacement.fromJson,
      label: 'creator stadium placements',
    );
  }

  @override
  Future<CreatorStadiumPlacement> createPlacement(
    String matchId,
    CreatorStadiumPlacementCreateRequest request,
  ) async {
    return CreatorStadiumPlacement.fromJson(
      await _client.request(
        'POST',
        '/media-engine/creator-league/matches/$matchId/stadium/placements',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorMatchGift> sendGift(
    String matchId,
    CreatorMatchGiftRequest request,
  ) async {
    return CreatorMatchGift.fromJson(
      await _client.request(
        'POST',
        '/media-engine/creator-league/matches/$matchId/gifts',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorAnalyticsDashboard> fetchMatchAnalytics(
    String matchId,
    CreatorMatchAnalyticsQuery query,
  ) async {
    return CreatorAnalyticsDashboard.fromJson(
      await _client.getMap(
        '/media-engine/creator-league/matches/$matchId/analytics',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<CreatorAnalyticsDashboard> fetchAdminMatchAnalytics(
    String matchId,
    CreatorMatchAnalyticsQuery query,
  ) async {
    return CreatorAnalyticsDashboard.fromJson(
      await _client.getMap(
        '/admin/media-engine/creator-league/matches/$matchId/analytics',
        query: query.toQuery(),
      ),
    );
  }

  @override
  Future<CreatorRevenueSettlement> settleMatchRevenue(String matchId) async {
    return CreatorRevenueSettlement.fromJson(
      await _client.request(
        'POST',
        '/admin/media-engine/creator-league/matches/$matchId/settlement',
      ),
    );
  }

  @override
  Future<CreatorStadiumControl> fetchStadiumControl() async {
    return CreatorStadiumControl.fromJson(
      await _client
          .getMap('/admin/media-engine/creator-league/stadium-controls'),
    );
  }

  @override
  Future<CreatorStadiumControl> updateStadiumControl(
    CreatorStadiumControlUpdateRequest request,
  ) async {
    return CreatorStadiumControl.fromJson(
      await _client.request(
        'PUT',
        '/admin/media-engine/creator-league/stadium-controls',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CreatorStadiumProfile> updateStadiumLevel(
    String clubId,
    CreatorStadiumLevelUpdateRequest request,
  ) async {
    return CreatorStadiumProfile.fromJson(
      await _client.request(
        'PUT',
        '/admin/media-engine/creator-league/clubs/$clubId/stadium-level',
        body: request.toJson(),
      ),
    );
  }
}
