import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'gift_economy_admin_models.dart';

abstract class GiftEconomyAdminRepository {
  Future<List<GiftCatalogItem>> listGiftCatalog();

  Future<GiftCatalogItem> upsertGiftCatalogItem(
    GiftCatalogItemUpsertRequest request,
  );

  Future<List<RevenueShareRule>> listRevenueShareRules(
    GiftEconomyRuleListQuery query,
  );

  Future<RevenueShareRule> upsertRevenueShareRule(
    RevenueShareRuleUpsertRequest request,
  );

  Future<List<GiftComboRule>> listGiftComboRules(
    GiftEconomyRuleListQuery query,
  );

  Future<GiftComboRule> upsertGiftComboRule(
    GiftComboRuleUpsertRequest request,
  );

  Future<List<EconomyBurnEvent>> listBurnEvents(
    GiftEconomyBurnEventsQuery query,
  );
}

class GiftEconomyAdminApiRepository implements GiftEconomyAdminRepository {
  GiftEconomyAdminApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory GiftEconomyAdminApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return GiftEconomyAdminApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<List<GiftCatalogItem>> listGiftCatalog() async {
    return parseList(
      await _client.getList('/economy/gift-catalog', auth: false),
      GiftCatalogItem.fromJson,
      label: 'gift catalog',
    );
  }

  @override
  Future<GiftCatalogItem> upsertGiftCatalogItem(
    GiftCatalogItemUpsertRequest request,
  ) async {
    return GiftCatalogItem.fromJson(
      await _client.request(
        'POST',
        '/admin/economy/gift-catalog',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<RevenueShareRule>> listRevenueShareRules(
    GiftEconomyRuleListQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/admin/economy/revenue-share-rules',
        query: query.toQuery(),
      ),
      RevenueShareRule.fromJson,
      label: 'gift revenue share rules',
    );
  }

  @override
  Future<RevenueShareRule> upsertRevenueShareRule(
    RevenueShareRuleUpsertRequest request,
  ) async {
    return RevenueShareRule.fromJson(
      await _client.request(
        'POST',
        '/admin/economy/revenue-share-rules',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<GiftComboRule>> listGiftComboRules(
    GiftEconomyRuleListQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/admin/economy/gift-combo-rules',
        query: query.toQuery(),
      ),
      GiftComboRule.fromJson,
      label: 'gift combo rules',
    );
  }

  @override
  Future<GiftComboRule> upsertGiftComboRule(
    GiftComboRuleUpsertRequest request,
  ) async {
    return GiftComboRule.fromJson(
      await _client.request(
        'POST',
        '/admin/economy/gift-combo-rules',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<EconomyBurnEvent>> listBurnEvents(
    GiftEconomyBurnEventsQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/admin/economy/burn-events',
        query: query.toQuery(),
      ),
      EconomyBurnEvent.fromJson,
      label: 'economy burn events',
    );
  }
}
