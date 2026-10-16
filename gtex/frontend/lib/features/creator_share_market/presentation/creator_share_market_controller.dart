import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/creator_share_market_models.dart';
import '../data/creator_share_market_repository.dart';

class CreatorShareMarketController extends ChangeNotifier {
  CreatorShareMarketController({
    required CreatorShareMarketRepository repository,
  }) : _repository = repository;

  factory CreatorShareMarketController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return CreatorShareMarketController(
      repository: CreatorShareMarketApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final CreatorShareMarketRepository _repository;
  final GteRequestGate _marketGate = GteRequestGate();
  final GteRequestGate _controlGate = GteRequestGate();

  String? currentClubId;
  CreatorClubShareMarket? market;
  CreatorClubShareHolding? holding;
  List<CreatorClubShareDistribution> distributions =
      const <CreatorClubShareDistribution>[];
  CreatorClubShareMarketControl? control;

  bool isLoadingMarket = false;
  bool isLoadingControl = false;
  bool isIssuingMarket = false;
  bool isPurchasingShares = false;
  bool isUpdatingControl = false;

  String? marketError;
  String? controlError;
  String? actionError;

  Future<void> loadMarket(String clubId) async {
    final int requestId = _marketGate.begin();
    currentClubId = clubId;
    marketError = null;
    isLoadingMarket = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchMarket(clubId),
        _repository.fetchHolding(clubId),
        _repository.fetchDistributions(clubId),
      ]);
      if (!_marketGate.isActive(requestId)) {
        return;
      }
      market = payload[0] as CreatorClubShareMarket;
      holding = payload[1] as CreatorClubShareHolding?;
      distributions = payload[2] as List<CreatorClubShareDistribution>;
    } catch (error) {
      if (_marketGate.isActive(requestId)) {
        marketError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_marketGate.isActive(requestId)) {
        isLoadingMarket = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadControl() async {
    final int requestId = _controlGate.begin();
    controlError = null;
    isLoadingControl = true;
    notifyListeners();

    try {
      final CreatorClubShareMarketControl nextControl =
          await _repository.fetchControl();
      if (!_controlGate.isActive(requestId)) {
        return;
      }
      control = nextControl;
    } catch (error) {
      if (_controlGate.isActive(requestId)) {
        controlError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_controlGate.isActive(requestId)) {
        isLoadingControl = false;
        notifyListeners();
      }
    }
  }

  Future<void> issueMarket(
    String clubId,
    CreatorClubShareMarketIssueRequest request,
  ) async {
    if (isIssuingMarket) {
      return;
    }
    isIssuingMarket = true;
    actionError = null;
    notifyListeners();
    try {
      market = await _repository.issueMarket(clubId, request);
      await loadMarket(clubId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isIssuingMarket = false;
      notifyListeners();
    }
  }

  Future<void> purchaseShares(
    String clubId,
    CreatorClubSharePurchaseRequest request,
  ) async {
    if (isPurchasingShares) {
      return;
    }
    isPurchasingShares = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.purchaseShares(clubId, request);
      await loadMarket(clubId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isPurchasingShares = false;
      notifyListeners();
    }
  }

  Future<void> updateControl(
    CreatorClubShareMarketControlUpdateRequest request,
  ) async {
    if (isUpdatingControl) {
      return;
    }
    isUpdatingControl = true;
    actionError = null;
    notifyListeners();
    try {
      control = await _repository.updateControl(request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingControl = false;
      notifyListeners();
    }
  }
}
