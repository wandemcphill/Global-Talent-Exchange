import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/creator_stadium_monetization_models.dart';
import '../data/creator_stadium_monetization_repository.dart';

class CreatorStadiumMonetizationController extends ChangeNotifier {
  CreatorStadiumMonetizationController({
    required CreatorStadiumMonetizationRepository repository,
  }) : _repository = repository;

  factory CreatorStadiumMonetizationController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return CreatorStadiumMonetizationController(
      repository: CreatorStadiumMonetizationApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final CreatorStadiumMonetizationRepository _repository;
  final GteRequestGate _modesGate = GteRequestGate();
  final GteRequestGate _clubGate = GteRequestGate();
  final GteRequestGate _matchGate = GteRequestGate();
  final GteRequestGate _adminGate = GteRequestGate();

  String? currentClubId;
  String? currentSeasonId;
  String? currentMatchId;
  String? currentAnalyticsClubId;
  CreatorMatchAccessQuery currentAccessQuery = const CreatorMatchAccessQuery();

  List<CreatorBroadcastMode> broadcastModes = const <CreatorBroadcastMode>[];
  CreatorMatchAccess? matchAccess;
  List<CreatorSeasonPass> seasonPasses = const <CreatorSeasonPass>[];
  CreatorStadiumMonetization? clubStadium;
  CreatorMatchStadiumOffer? matchOffer;
  List<CreatorStadiumPlacement> placements = const <CreatorStadiumPlacement>[];
  CreatorAnalyticsDashboard? analytics;
  CreatorStadiumControl? adminControl;
  CreatorBroadcastPurchase? latestBroadcastPurchase;
  CreatorSeasonPass? latestSeasonPass;
  CreatorStadiumTicketPurchase? latestTicketPurchase;
  CreatorMatchGift? latestGift;
  CreatorRevenueSettlement? latestSettlement;
  CreatorStadiumProfile? latestStadiumProfile;

  bool isLoadingModes = false;
  bool isLoadingClubStadium = false;
  bool isLoadingMatch = false;
  bool isLoadingAdmin = false;
  bool isPurchasingBroadcast = false;
  bool isPurchasingSeasonPass = false;
  bool isUpdatingClubStadium = false;
  bool isPurchasingTicket = false;
  bool isCreatingPlacement = false;
  bool isSendingGift = false;
  bool isSettlingRevenue = false;
  bool isUpdatingStadiumControl = false;
  bool isUpdatingStadiumLevel = false;

  String? modesError;
  String? clubError;
  String? matchError;
  String? adminError;
  String? actionError;

  Future<void> loadModes() async {
    final int requestId = _modesGate.begin();
    modesError = null;
    isLoadingModes = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.listBroadcastModes(),
        _repository.listMySeasonPasses(),
      ]);
      if (!_modesGate.isActive(requestId)) {
        return;
      }
      broadcastModes = payload[0] as List<CreatorBroadcastMode>;
      seasonPasses = payload[1] as List<CreatorSeasonPass>;
    } catch (error) {
      if (_modesGate.isActive(requestId)) {
        modesError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_modesGate.isActive(requestId)) {
        isLoadingModes = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadClubStadium(
    String clubId,
    String seasonId,
  ) async {
    final int requestId = _clubGate.begin();
    currentClubId = clubId;
    currentSeasonId = seasonId;
    clubError = null;
    isLoadingClubStadium = true;
    notifyListeners();

    try {
      final CreatorStadiumMonetization result =
          await _repository.fetchClubStadium(
        clubId,
        CreatorClubStadiumQuery(seasonId: seasonId),
      );
      if (!_clubGate.isActive(requestId)) {
        return;
      }
      clubStadium = result;
    } catch (error) {
      if (_clubGate.isActive(requestId)) {
        clubError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_clubGate.isActive(requestId)) {
        isLoadingClubStadium = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadMatch(
    String matchId, {
    CreatorMatchAccessQuery accessQuery = const CreatorMatchAccessQuery(),
    String? analyticsClubId,
    bool includeAdminAnalytics = false,
  }) async {
    final int requestId = _matchGate.begin();
    currentMatchId = matchId;
    currentAccessQuery = accessQuery;
    currentAnalyticsClubId = analyticsClubId;
    matchError = null;
    isLoadingMatch = true;
    notifyListeners();

    try {
      final CreatorMatchAnalyticsQuery analyticsQuery =
          CreatorMatchAnalyticsQuery(clubId: analyticsClubId);
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchMatchAccess(matchId, accessQuery),
        _repository.fetchMatchStadiumOffer(matchId),
        _repository.listPlacements(matchId),
        includeAdminAnalytics
            ? _repository.fetchAdminMatchAnalytics(matchId, analyticsQuery)
            : _repository.fetchMatchAnalytics(matchId, analyticsQuery),
      ]);
      if (!_matchGate.isActive(requestId)) {
        return;
      }
      matchAccess = payload[0] as CreatorMatchAccess;
      matchOffer = payload[1] as CreatorMatchStadiumOffer;
      placements = payload[2] as List<CreatorStadiumPlacement>;
      analytics = payload[3] as CreatorAnalyticsDashboard;
    } catch (error) {
      if (_matchGate.isActive(requestId)) {
        matchError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_matchGate.isActive(requestId)) {
        isLoadingMatch = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadAdmin() async {
    final int requestId = _adminGate.begin();
    adminError = null;
    isLoadingAdmin = true;
    notifyListeners();

    try {
      final CreatorStadiumControl result =
          await _repository.fetchStadiumControl();
      if (!_adminGate.isActive(requestId)) {
        return;
      }
      adminControl = result;
    } catch (error) {
      if (_adminGate.isActive(requestId)) {
        adminError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_adminGate.isActive(requestId)) {
        isLoadingAdmin = false;
        notifyListeners();
      }
    }
  }

  Future<void> purchaseBroadcast(
    String matchId,
    CreatorBroadcastPurchaseRequest request,
  ) async {
    if (isPurchasingBroadcast) {
      return;
    }
    isPurchasingBroadcast = true;
    actionError = null;
    notifyListeners();
    try {
      latestBroadcastPurchase =
          await _repository.purchaseMatchBroadcast(matchId, request);
      await loadMatch(
        matchId,
        accessQuery: CreatorMatchAccessQuery(
          durationMinutes: request.durationMinutes,
        ),
        analyticsClubId: currentAnalyticsClubId,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isPurchasingBroadcast = false;
      notifyListeners();
    }
  }

  Future<void> purchaseSeasonPass(
    CreatorSeasonPassCreateRequest request,
  ) async {
    if (isPurchasingSeasonPass) {
      return;
    }
    isPurchasingSeasonPass = true;
    actionError = null;
    notifyListeners();
    try {
      latestSeasonPass = await _repository.purchaseSeasonPass(request);
      await loadModes();
      await loadClubStadium(request.clubId, request.seasonId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isPurchasingSeasonPass = false;
      notifyListeners();
    }
  }

  Future<void> updateClubStadium(
    String clubId,
    CreatorStadiumConfigUpdateRequest request,
  ) async {
    if (isUpdatingClubStadium) {
      return;
    }
    isUpdatingClubStadium = true;
    actionError = null;
    notifyListeners();
    try {
      clubStadium = await _repository.updateClubStadium(clubId, request);
      await loadClubStadium(clubId, request.seasonId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingClubStadium = false;
      notifyListeners();
    }
  }

  Future<void> purchaseTicket(
    String matchId,
    CreatorStadiumTicketPurchaseRequest request,
  ) async {
    if (isPurchasingTicket) {
      return;
    }
    isPurchasingTicket = true;
    actionError = null;
    notifyListeners();
    try {
      latestTicketPurchase = await _repository.purchaseTicket(matchId, request);
      await loadMatch(
        matchId,
        accessQuery: currentAccessQuery,
        analyticsClubId: currentAnalyticsClubId,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isPurchasingTicket = false;
      notifyListeners();
    }
  }

  Future<void> createPlacement(
    String matchId,
    CreatorStadiumPlacementCreateRequest request,
  ) async {
    if (isCreatingPlacement) {
      return;
    }
    isCreatingPlacement = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createPlacement(matchId, request);
      await loadMatch(
        matchId,
        accessQuery: currentAccessQuery,
        analyticsClubId: currentAnalyticsClubId,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingPlacement = false;
      notifyListeners();
    }
  }

  Future<void> sendGift(
    String matchId,
    CreatorMatchGiftRequest request,
  ) async {
    if (isSendingGift) {
      return;
    }
    isSendingGift = true;
    actionError = null;
    notifyListeners();
    try {
      latestGift = await _repository.sendGift(matchId, request);
      await loadMatch(
        matchId,
        accessQuery: currentAccessQuery,
        analyticsClubId: request.clubId,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSendingGift = false;
      notifyListeners();
    }
  }

  Future<void> settleRevenue(String matchId) async {
    if (isSettlingRevenue) {
      return;
    }
    isSettlingRevenue = true;
    actionError = null;
    notifyListeners();
    try {
      latestSettlement = await _repository.settleMatchRevenue(matchId);
      await loadMatch(
        matchId,
        accessQuery: currentAccessQuery,
        analyticsClubId: currentAnalyticsClubId,
        includeAdminAnalytics: true,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSettlingRevenue = false;
      notifyListeners();
    }
  }

  Future<void> updateStadiumControl(
    CreatorStadiumControlUpdateRequest request,
  ) async {
    if (isUpdatingStadiumControl) {
      return;
    }
    isUpdatingStadiumControl = true;
    actionError = null;
    notifyListeners();
    try {
      adminControl = await _repository.updateStadiumControl(request);
      await loadAdmin();
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingStadiumControl = false;
      notifyListeners();
    }
  }

  Future<void> updateStadiumLevel(
    String clubId,
    CreatorStadiumLevelUpdateRequest request,
  ) async {
    if (isUpdatingStadiumLevel) {
      return;
    }
    isUpdatingStadiumLevel = true;
    actionError = null;
    notifyListeners();
    try {
      latestStadiumProfile =
          await _repository.updateStadiumLevel(clubId, request);
      if (currentSeasonId != null) {
        await loadClubStadium(clubId, currentSeasonId!);
      }
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingStadiumLevel = false;
      notifyListeners();
    }
  }
}
