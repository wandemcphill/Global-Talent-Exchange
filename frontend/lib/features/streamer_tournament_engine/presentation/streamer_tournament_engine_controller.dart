import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/streamer_tournament_engine_models.dart';
import '../data/streamer_tournament_engine_repository.dart';

class StreamerTournamentEngineController extends ChangeNotifier {
  StreamerTournamentEngineController({
    required StreamerTournamentEngineRepository repository,
  }) : _repository = repository;

  factory StreamerTournamentEngineController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return StreamerTournamentEngineController(
      repository: StreamerTournamentEngineApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final StreamerTournamentEngineRepository _repository;
  final GteRequestGate _listGate = GteRequestGate();
  final GteRequestGate _detailGate = GteRequestGate();
  final GteRequestGate _adminGate = GteRequestGate();

  StreamerTournamentList publicTournaments =
      const StreamerTournamentList.empty();
  StreamerTournamentList myTournaments = const StreamerTournamentList.empty();
  StreamerTournament? tournament;
  StreamerTournamentPolicy? policy;
  List<StreamerTournamentRiskSignal> riskSignals =
      const <StreamerTournamentRiskSignal>[];
  StreamerTournamentSettlement? latestSettlement;

  bool isLoadingLists = false;
  bool isLoadingTournament = false;
  bool isLoadingAdmin = false;
  bool isCreatingTournament = false;
  bool isUpdatingTournament = false;
  bool isReplacingRewardPlan = false;
  bool isCreatingInvite = false;
  bool isJoiningTournament = false;
  bool isPublishingTournament = false;
  bool isUpdatingPolicy = false;
  bool isReviewingTournament = false;
  bool isReviewingRiskSignal = false;
  bool isSettlingTournament = false;

  String? listError;
  String? tournamentError;
  String? adminError;
  String? actionError;

  Future<void> loadLists({bool includeMine = false}) async {
    final int requestId = _listGate.begin();
    listError = null;
    isLoadingLists = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.listPublicTournaments(),
        if (includeMine) _repository.listMyTournaments(),
      ]);
      if (!_listGate.isActive(requestId)) {
        return;
      }
      publicTournaments = payload[0] as StreamerTournamentList;
      if (includeMine) {
        myTournaments = payload[1] as StreamerTournamentList;
      }
    } catch (error) {
      if (_listGate.isActive(requestId)) {
        listError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_listGate.isActive(requestId)) {
        isLoadingLists = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadTournament(String tournamentId) async {
    final int requestId = _detailGate.begin();
    tournamentError = null;
    isLoadingTournament = true;
    notifyListeners();

    try {
      final StreamerTournament result =
          await _repository.fetchTournament(tournamentId);
      if (!_detailGate.isActive(requestId)) {
        return;
      }
      tournament = result;
    } catch (error) {
      if (_detailGate.isActive(requestId)) {
        tournamentError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_detailGate.isActive(requestId)) {
        isLoadingTournament = false;
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
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchPolicy(),
        _repository.listRiskSignals(),
      ]);
      if (!_adminGate.isActive(requestId)) {
        return;
      }
      policy = payload[0] as StreamerTournamentPolicy;
      riskSignals = payload[1] as List<StreamerTournamentRiskSignal>;
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

  Future<void> createTournament(StreamerTournamentCreateRequest request) async {
    if (isCreatingTournament) {
      return;
    }
    isCreatingTournament = true;
    actionError = null;
    notifyListeners();
    try {
      tournament = await _repository.createTournament(request);
      await loadLists(includeMine: true);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingTournament = false;
      notifyListeners();
    }
  }

  Future<void> updateTournament(
    String tournamentId,
    StreamerTournamentUpdateRequest request,
  ) async {
    if (isUpdatingTournament) {
      return;
    }
    isUpdatingTournament = true;
    actionError = null;
    notifyListeners();
    try {
      tournament = await _repository.updateTournament(tournamentId, request);
      await loadLists(includeMine: true);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingTournament = false;
      notifyListeners();
    }
  }

  Future<void> replaceRewardPlan(
    String tournamentId,
    StreamerTournamentRewardPlanReplaceRequest request,
  ) async {
    if (isReplacingRewardPlan) {
      return;
    }
    isReplacingRewardPlan = true;
    actionError = null;
    notifyListeners();
    try {
      tournament = await _repository.replaceRewardPlan(tournamentId, request);
      await loadTournament(tournamentId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isReplacingRewardPlan = false;
      notifyListeners();
    }
  }

  Future<void> createInvite(
    String tournamentId,
    StreamerTournamentInviteCreateRequest request,
  ) async {
    if (isCreatingInvite) {
      return;
    }
    isCreatingInvite = true;
    actionError = null;
    notifyListeners();
    try {
      tournament = await _repository.createInvite(tournamentId, request);
      await loadTournament(tournamentId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingInvite = false;
      notifyListeners();
    }
  }

  Future<void> joinTournament(
    String tournamentId,
    StreamerTournamentJoinRequest request,
  ) async {
    if (isJoiningTournament) {
      return;
    }
    isJoiningTournament = true;
    actionError = null;
    notifyListeners();
    try {
      tournament = await _repository.joinTournament(tournamentId, request);
      await loadLists(includeMine: true);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isJoiningTournament = false;
      notifyListeners();
    }
  }

  Future<void> publishTournament(
    String tournamentId,
    StreamerTournamentPublishRequest request,
  ) async {
    if (isPublishingTournament) {
      return;
    }
    isPublishingTournament = true;
    actionError = null;
    notifyListeners();
    try {
      tournament = await _repository.publishTournament(tournamentId, request);
      await loadTournament(tournamentId);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isPublishingTournament = false;
      notifyListeners();
    }
  }

  Future<void> upsertPolicy(
    StreamerTournamentPolicyUpsertRequest request,
  ) async {
    if (isUpdatingPolicy) {
      return;
    }
    isUpdatingPolicy = true;
    actionError = null;
    notifyListeners();
    try {
      policy = await _repository.upsertPolicy(request);
      await loadAdmin();
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpdatingPolicy = false;
      notifyListeners();
    }
  }

  Future<void> reviewTournament(
    String tournamentId,
    StreamerTournamentReviewRequest request,
  ) async {
    if (isReviewingTournament) {
      return;
    }
    isReviewingTournament = true;
    actionError = null;
    notifyListeners();
    try {
      tournament = await _repository.reviewTournament(tournamentId, request);
      await Future.wait<void>(<Future<void>>[
        loadTournament(tournamentId),
        loadAdmin(),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isReviewingTournament = false;
      notifyListeners();
    }
  }

  Future<void> reviewRiskSignal(
    String signalId,
    StreamerTournamentRiskReviewRequest request,
  ) async {
    if (isReviewingRiskSignal) {
      return;
    }
    isReviewingRiskSignal = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.reviewRiskSignal(signalId, request);
      await loadAdmin();
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isReviewingRiskSignal = false;
      notifyListeners();
    }
  }

  Future<void> settleTournament(
    String tournamentId,
    StreamerTournamentSettleRequest request,
  ) async {
    if (isSettlingTournament) {
      return;
    }
    isSettlingTournament = true;
    actionError = null;
    notifyListeners();
    try {
      latestSettlement =
          await _repository.settleTournament(tournamentId, request);
      tournament = latestSettlement!.tournament;
      await Future.wait<void>(<Future<void>>[
        loadTournament(tournamentId),
        loadAdmin(),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSettlingTournament = false;
      notifyListeners();
    }
  }
}
