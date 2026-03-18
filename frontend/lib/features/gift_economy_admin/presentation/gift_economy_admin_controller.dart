import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/gift_economy_admin_models.dart';
import '../data/gift_economy_admin_repository.dart';

class GiftEconomyAdminController extends ChangeNotifier {
  GiftEconomyAdminController({
    required GiftEconomyAdminRepository repository,
  }) : _repository = repository;

  factory GiftEconomyAdminController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return GiftEconomyAdminController(
      repository: GiftEconomyAdminApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final GiftEconomyAdminRepository _repository;
  final GteRequestGate _catalogGate = GteRequestGate();
  final GteRequestGate _rulesGate = GteRequestGate();
  final GteRequestGate _burnGate = GteRequestGate();

  GiftEconomyRuleListQuery currentRulesQuery = const GiftEconomyRuleListQuery();
  GiftEconomyBurnEventsQuery currentBurnEventsQuery =
      const GiftEconomyBurnEventsQuery();

  List<GiftCatalogItem> catalog = const <GiftCatalogItem>[];
  List<RevenueShareRule> revenueShareRules = const <RevenueShareRule>[];
  List<GiftComboRule> comboRules = const <GiftComboRule>[];
  List<EconomyBurnEvent> burnEvents = const <EconomyBurnEvent>[];

  bool isLoadingCatalog = false;
  bool isLoadingRules = false;
  bool isLoadingBurnEvents = false;
  bool isUpsertingCatalogItem = false;
  bool isUpsertingRevenueShareRule = false;
  bool isUpsertingComboRule = false;

  String? catalogError;
  String? rulesError;
  String? burnEventsError;
  String? actionError;

  Future<void> loadCatalog() async {
    final int requestId = _catalogGate.begin();
    catalogError = null;
    isLoadingCatalog = true;
    notifyListeners();

    try {
      final List<GiftCatalogItem> result = await _repository.listGiftCatalog();
      if (!_catalogGate.isActive(requestId)) {
        return;
      }
      catalog = result;
    } catch (error) {
      if (_catalogGate.isActive(requestId)) {
        catalogError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_catalogGate.isActive(requestId)) {
        isLoadingCatalog = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadRules({
    GiftEconomyRuleListQuery query = const GiftEconomyRuleListQuery(),
  }) async {
    final int requestId = _rulesGate.begin();
    currentRulesQuery = query;
    rulesError = null;
    isLoadingRules = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.listRevenueShareRules(query),
        _repository.listGiftComboRules(query),
      ]);
      if (!_rulesGate.isActive(requestId)) {
        return;
      }
      revenueShareRules = payload[0] as List<RevenueShareRule>;
      comboRules = payload[1] as List<GiftComboRule>;
    } catch (error) {
      if (_rulesGate.isActive(requestId)) {
        rulesError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_rulesGate.isActive(requestId)) {
        isLoadingRules = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadBurnEvents({
    GiftEconomyBurnEventsQuery query = const GiftEconomyBurnEventsQuery(),
  }) async {
    final int requestId = _burnGate.begin();
    currentBurnEventsQuery = query;
    burnEventsError = null;
    isLoadingBurnEvents = true;
    notifyListeners();

    try {
      final List<EconomyBurnEvent> result =
          await _repository.listBurnEvents(query);
      if (!_burnGate.isActive(requestId)) {
        return;
      }
      burnEvents = result;
    } catch (error) {
      if (_burnGate.isActive(requestId)) {
        burnEventsError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_burnGate.isActive(requestId)) {
        isLoadingBurnEvents = false;
        notifyListeners();
      }
    }
  }

  Future<void> upsertCatalogItem(GiftCatalogItemUpsertRequest request) async {
    if (isUpsertingCatalogItem) {
      return;
    }
    isUpsertingCatalogItem = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.upsertGiftCatalogItem(request);
      await loadCatalog();
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingCatalogItem = false;
      notifyListeners();
    }
  }

  Future<void> upsertRevenueShareRule(
    RevenueShareRuleUpsertRequest request,
  ) async {
    if (isUpsertingRevenueShareRule) {
      return;
    }
    isUpsertingRevenueShareRule = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.upsertRevenueShareRule(request);
      await loadRules(query: currentRulesQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingRevenueShareRule = false;
      notifyListeners();
    }
  }

  Future<void> upsertComboRule(GiftComboRuleUpsertRequest request) async {
    if (isUpsertingComboRule) {
      return;
    }
    isUpsertingComboRule = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.upsertGiftComboRule(request);
      await loadRules(query: currentRulesQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingComboRule = false;
      notifyListeners();
    }
  }
}
