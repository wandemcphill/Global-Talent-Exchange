import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/fan_wars_models.dart';
import '../data/fan_wars_repository.dart';

class FanWarsController extends ChangeNotifier {
  FanWarsController({
    required FanWarsRepository repository,
  }) : _repository = repository;

  factory FanWarsController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return FanWarsController(
      repository: FanWarsApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final FanWarsRepository _repository;
  final GteRequestGate _boardGate = GteRequestGate();
  final GteRequestGate _dashboardGate = GteRequestGate();

  FanWarsPeriodQuery currentBoardQuery = const FanWarsPeriodQuery();
  FanWarsDashboardQuery currentDashboardQuery = const FanWarsDashboardQuery();

  FanWarLeaderboard? leaderboard;
  RivalryLeaderboard? rivalries;
  FanWarDashboard? dashboard;
  NationsCupOverview? nationsCup;
  FanWarProfile? latestProfile;
  CreatorCountryAssignment? latestCountryAssignment;
  List<Map<String, Object?>> latestPoints = const <Map<String, Object?>>[];

  bool isLoadingBoards = false;
  bool isLoadingDashboard = false;
  bool isUpsertingProfile = false;
  bool isLinkingRivals = false;
  bool isRecordingPoints = false;
  bool isAssigningCreatorCountry = false;
  bool isCreatingNationsCup = false;
  bool isAdvancingNationsCup = false;

  String? boardsError;
  String? dashboardError;
  String? actionError;

  Future<void> loadBoards(
    String boardType, {
    FanWarsPeriodQuery query = const FanWarsPeriodQuery(),
  }) async {
    final int requestId = _boardGate.begin();
    currentBoardQuery = query;
    boardsError = null;
    isLoadingBoards = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchLeaderboard(boardType, query),
        _repository.fetchRivalries(boardType, query),
      ]);
      if (!_boardGate.isActive(requestId)) {
        return;
      }
      leaderboard = payload[0] as FanWarLeaderboard;
      rivalries = payload[1] as RivalryLeaderboard;
    } catch (error) {
      if (_boardGate.isActive(requestId)) {
        boardsError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_boardGate.isActive(requestId)) {
        isLoadingBoards = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadDashboard(
    String profileId, {
    FanWarsDashboardQuery query = const FanWarsDashboardQuery(),
    String? competitionId,
  }) async {
    final int requestId = _dashboardGate.begin();
    currentDashboardQuery = query;
    dashboardError = null;
    isLoadingDashboard = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchDashboard(profileId, query),
        if (competitionId != null) _repository.fetchNationsCup(competitionId),
      ]);
      if (!_dashboardGate.isActive(requestId)) {
        return;
      }
      dashboard = payload[0] as FanWarDashboard;
      if (competitionId != null) {
        nationsCup = payload[1] as NationsCupOverview;
      }
    } catch (error) {
      if (_dashboardGate.isActive(requestId)) {
        dashboardError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_dashboardGate.isActive(requestId)) {
        isLoadingDashboard = false;
        notifyListeners();
      }
    }
  }

  Future<void> upsertProfile(FanWarProfileUpsertRequest request) async {
    if (isUpsertingProfile) {
      return;
    }
    isUpsertingProfile = true;
    actionError = null;
    notifyListeners();
    try {
      latestProfile = await _repository.upsertProfile(request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingProfile = false;
      notifyListeners();
    }
  }

  Future<void> linkRivals(String profileId, String rivalProfileId) async {
    if (isLinkingRivals) {
      return;
    }
    isLinkingRivals = true;
    actionError = null;
    notifyListeners();
    try {
      final List<FanWarProfile> profiles =
          await _repository.linkRivals(profileId, rivalProfileId);
      if (profiles.isNotEmpty) {
        latestProfile = profiles.first;
      }
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isLinkingRivals = false;
      notifyListeners();
    }
  }

  Future<void> recordPoints(FanWarPointRecordRequest request) async {
    if (isRecordingPoints) {
      return;
    }
    isRecordingPoints = true;
    actionError = null;
    notifyListeners();
    try {
      latestPoints = await _repository.recordPoints(request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isRecordingPoints = false;
      notifyListeners();
    }
  }

  Future<void> assignCreatorCountry(
    CreatorCountryAssignmentRequest request,
  ) async {
    if (isAssigningCreatorCountry) {
      return;
    }
    isAssigningCreatorCountry = true;
    actionError = null;
    notifyListeners();
    try {
      latestCountryAssignment = await _repository.assignCreatorCountry(request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isAssigningCreatorCountry = false;
      notifyListeners();
    }
  }

  Future<void> createNationsCup(NationsCupCreateRequest request) async {
    if (isCreatingNationsCup) {
      return;
    }
    isCreatingNationsCup = true;
    actionError = null;
    notifyListeners();
    try {
      nationsCup = await _repository.createNationsCup(request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingNationsCup = false;
      notifyListeners();
    }
  }

  Future<void> advanceNationsCup(
    String competitionId, {
    bool force = false,
  }) async {
    if (isAdvancingNationsCup) {
      return;
    }
    isAdvancingNationsCup = true;
    actionError = null;
    notifyListeners();
    try {
      nationsCup = await _repository.advanceNationsCup(
        competitionId,
        force: force,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isAdvancingNationsCup = false;
      notifyListeners();
    }
  }
}
