import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/creator_league_admin_models.dart';
import '../data/creator_league_admin_repository.dart';

class CreatorLeagueAdminController extends ChangeNotifier {
  CreatorLeagueAdminController({
    required CreatorLeagueAdminRepository repository,
  }) : _repository = repository;

  factory CreatorLeagueAdminController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return CreatorLeagueAdminController(
      repository: CreatorLeagueAdminApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final CreatorLeagueAdminRepository _repository;
  final GteRequestGate _overviewGate = GteRequestGate();
  final GteRequestGate _seasonGate = GteRequestGate();
  final GteRequestGate _financeGate = GteRequestGate();

  CreatorLeagueLivePriorityQuery currentLivePriorityQuery =
      const CreatorLeagueLivePriorityQuery();
  CreatorLeagueFinancialReportQuery currentFinancialReportQuery =
      const CreatorLeagueFinancialReportQuery();
  CreatorLeagueFinancialSettlementsQuery currentSettlementsQuery =
      const CreatorLeagueFinancialSettlementsQuery();

  CreatorLeagueConfig? overview;
  CreatorLeagueSeason? season;
  List<CreatorLeagueStanding> standings = const <CreatorLeagueStanding>[];
  CreatorLeagueLivePriority? livePriority;
  CreatorLeagueFinancialReport? financialReport;
  List<CreatorLeagueSettlement> settlements = const <CreatorLeagueSettlement>[];
  CreatorLeagueSettlement? latestApprovedSettlement;

  bool isLoadingOverview = false;
  bool isLoadingSeason = false;
  bool isLoadingFinance = false;
  bool isUpdatingConfig = false;
  bool isCreatingTier = false;
  bool isUpdatingTier = false;
  bool isDeletingTier = false;
  bool isResettingStructure = false;
  bool isCreatingSeason = false;
  bool isPausingSeason = false;
  bool isApprovingSettlement = false;

  String? overviewError;
  String? seasonError;
  String? financeError;
  String? actionError;

  Future<void> loadOverview({
    CreatorLeagueLivePriorityQuery livePriorityQuery =
        const CreatorLeagueLivePriorityQuery(),
  }) async {
    final int requestId = _overviewGate.begin();
    currentLivePriorityQuery = livePriorityQuery;
    overviewError = null;
    isLoadingOverview = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchOverview(),
        _repository.fetchLivePriority(livePriorityQuery),
      ]);
      if (!_overviewGate.isActive(requestId)) {
        return;
      }
      overview = payload[0] as CreatorLeagueConfig;
      livePriority = payload[1] as CreatorLeagueLivePriority;
    } catch (error) {
      if (_overviewGate.isActive(requestId)) {
        overviewError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_overviewGate.isActive(requestId)) {
        isLoadingOverview = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadSeason(
    String seasonId, {
    String? seasonTierId,
  }) async {
    final int requestId = _seasonGate.begin();
    seasonError = null;
    isLoadingSeason = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchSeason(seasonId),
        if (seasonTierId != null) _repository.fetchStandings(seasonTierId),
      ]);
      if (!_seasonGate.isActive(requestId)) {
        return;
      }
      season = payload[0] as CreatorLeagueSeason;
      standings = seasonTierId == null
          ? const <CreatorLeagueStanding>[]
          : payload[1] as List<CreatorLeagueStanding>;
    } catch (error) {
      if (_seasonGate.isActive(requestId)) {
        seasonError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_seasonGate.isActive(requestId)) {
        isLoadingSeason = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadFinance({
    CreatorLeagueFinancialReportQuery reportQuery =
        const CreatorLeagueFinancialReportQuery(),
    CreatorLeagueFinancialSettlementsQuery settlementsQuery =
        const CreatorLeagueFinancialSettlementsQuery(),
  }) async {
    final int requestId = _financeGate.begin();
    currentFinancialReportQuery = reportQuery;
    currentSettlementsQuery = settlementsQuery;
    financeError = null;
    isLoadingFinance = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchFinancialReport(reportQuery),
        _repository.listSettlements(settlementsQuery),
      ]);
      if (!_financeGate.isActive(requestId)) {
        return;
      }
      financialReport = payload[0] as CreatorLeagueFinancialReport;
      settlements = payload[1] as List<CreatorLeagueSettlement>;
    } catch (error) {
      if (_financeGate.isActive(requestId)) {
        financeError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_financeGate.isActive(requestId)) {
        isLoadingFinance = false;
        notifyListeners();
      }
    }
  }

  Future<void> updateConfig(CreatorLeagueConfigUpdateRequest request) async {
    if (isUpdatingConfig) {
      return;
    }
    isUpdatingConfig = true;
    actionError = null;
    notifyListeners();
    try {
      overview = await _repository.updateConfig(request);
      await loadOverview(livePriorityQuery: currentLivePriorityQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingConfig = false;
      notifyListeners();
    }
  }

  Future<void> createTier(CreatorLeagueTierCreateRequest request) async {
    if (isCreatingTier) {
      return;
    }
    isCreatingTier = true;
    actionError = null;
    notifyListeners();
    try {
      overview = await _repository.createTier(request);
      await loadOverview(livePriorityQuery: currentLivePriorityQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingTier = false;
      notifyListeners();
    }
  }

  Future<void> updateTier(
    String tierId,
    CreatorLeagueTierUpdateRequest request,
  ) async {
    if (isUpdatingTier) {
      return;
    }
    isUpdatingTier = true;
    actionError = null;
    notifyListeners();
    try {
      overview = await _repository.updateTier(tierId, request);
      await loadOverview(livePriorityQuery: currentLivePriorityQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingTier = false;
      notifyListeners();
    }
  }

  Future<void> deleteTier(String tierId) async {
    if (isDeletingTier) {
      return;
    }
    isDeletingTier = true;
    actionError = null;
    notifyListeners();
    try {
      overview = await _repository.deleteTier(tierId);
      await loadOverview(livePriorityQuery: currentLivePriorityQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isDeletingTier = false;
      notifyListeners();
    }
  }

  Future<void> resetStructure() async {
    if (isResettingStructure) {
      return;
    }
    isResettingStructure = true;
    actionError = null;
    notifyListeners();
    try {
      overview = await _repository.resetStructure();
      await loadOverview(livePriorityQuery: currentLivePriorityQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isResettingStructure = false;
      notifyListeners();
    }
  }

  Future<void> createSeason(CreatorLeagueSeasonCreateRequest request) async {
    if (isCreatingSeason) {
      return;
    }
    isCreatingSeason = true;
    actionError = null;
    notifyListeners();
    try {
      season = await _repository.createSeason(request);
      await Future.wait<void>(<Future<void>>[
        loadOverview(livePriorityQuery: currentLivePriorityQuery),
        loadFinance(
          reportQuery: currentFinancialReportQuery,
          settlementsQuery: currentSettlementsQuery,
        ),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingSeason = false;
      notifyListeners();
    }
  }

  Future<void> pauseSeason(String seasonId) async {
    if (isPausingSeason) {
      return;
    }
    isPausingSeason = true;
    actionError = null;
    notifyListeners();
    try {
      season = await _repository.pauseSeason(seasonId);
      await loadOverview(livePriorityQuery: currentLivePriorityQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isPausingSeason = false;
      notifyListeners();
    }
  }

  Future<void> approveSettlement(
    String settlementId,
    CreatorLeagueSettlementReviewRequest request,
  ) async {
    if (isApprovingSettlement) {
      return;
    }
    isApprovingSettlement = true;
    actionError = null;
    notifyListeners();
    try {
      latestApprovedSettlement =
          await _repository.approveSettlement(settlementId, request);
      await loadFinance(
        reportQuery: currentFinancialReportQuery,
        settlementsQuery: currentSettlementsQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isApprovingSettlement = false;
      notifyListeners();
    }
  }
}
