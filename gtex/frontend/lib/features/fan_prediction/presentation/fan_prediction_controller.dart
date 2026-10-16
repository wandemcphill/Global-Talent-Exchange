import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/fan_prediction_models.dart';
import '../data/fan_prediction_repository.dart';

class FanPredictionController extends ChangeNotifier {
  FanPredictionController({
    required FanPredictionRepository repository,
  }) : _repository = repository;

  factory FanPredictionController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return FanPredictionController(
      repository: FanPredictionApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final FanPredictionRepository _repository;
  final GteRequestGate _fixtureGate = GteRequestGate();
  final GteRequestGate _leaderboardGate = GteRequestGate();
  final GteRequestGate _profileGate = GteRequestGate();

  String? currentMatchId;
  String? currentCreatorClubId;
  FanPredictionMatchLeaderboardQuery currentMatchLeaderboardQuery =
      const FanPredictionMatchLeaderboardQuery();
  FanPredictionLeaderboardQuery currentWeeklyQuery =
      const FanPredictionLeaderboardQuery();

  FanPredictionFixture? fixture;
  FanPredictionLeaderboard? matchLeaderboard;
  FanPredictionLeaderboard? weeklyLeaderboard;
  FanPredictionLeaderboard? creatorClubWeeklyLeaderboard;
  FanPredictionTokenSummary? tokenSummary;
  List<FanPredictionSubmission> mySubmissions =
      const <FanPredictionSubmission>[];

  bool isLoadingFixture = false;
  bool isLoadingLeaderboards = false;
  bool isLoadingProfile = false;
  bool isSubmittingPrediction = false;
  bool isConfiguringFixture = false;
  bool isSettlingFixture = false;

  String? fixtureError;
  String? leaderboardError;
  String? profileError;
  String? actionError;

  Future<void> loadFixture(
    String matchId, {
    FanPredictionMatchLeaderboardQuery leaderboardQuery =
        const FanPredictionMatchLeaderboardQuery(),
  }) async {
    final int requestId = _fixtureGate.begin();
    currentMatchId = matchId;
    currentMatchLeaderboardQuery = leaderboardQuery;
    fixtureError = null;
    isLoadingFixture = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchFixture(matchId),
        _repository.fetchMatchLeaderboard(matchId, leaderboardQuery),
      ]);
      if (!_fixtureGate.isActive(requestId)) {
        return;
      }
      fixture = payload[0] as FanPredictionFixture;
      matchLeaderboard = payload[1] as FanPredictionLeaderboard;
    } catch (error) {
      if (_fixtureGate.isActive(requestId)) {
        fixtureError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_fixtureGate.isActive(requestId)) {
        isLoadingFixture = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadLeaderboards({
    FanPredictionLeaderboardQuery weeklyQuery =
        const FanPredictionLeaderboardQuery(),
    String? creatorClubId,
  }) async {
    final int requestId = _leaderboardGate.begin();
    currentWeeklyQuery = weeklyQuery;
    currentCreatorClubId = creatorClubId;
    leaderboardError = null;
    isLoadingLeaderboards = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchWeeklyLeaderboard(weeklyQuery),
        if (creatorClubId != null)
          _repository.fetchCreatorClubWeeklyLeaderboard(
              creatorClubId, weeklyQuery),
      ]);
      if (!_leaderboardGate.isActive(requestId)) {
        return;
      }
      weeklyLeaderboard = payload[0] as FanPredictionLeaderboard;
      creatorClubWeeklyLeaderboard =
          creatorClubId == null ? null : payload[1] as FanPredictionLeaderboard;
    } catch (error) {
      if (_leaderboardGate.isActive(requestId)) {
        leaderboardError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_leaderboardGate.isActive(requestId)) {
        isLoadingLeaderboards = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadProfile() async {
    final int requestId = _profileGate.begin();
    profileError = null;
    isLoadingProfile = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchTokenSummary(),
        _repository.listMySubmissions(),
      ]);
      if (!_profileGate.isActive(requestId)) {
        return;
      }
      tokenSummary = payload[0] as FanPredictionTokenSummary;
      mySubmissions = payload[1] as List<FanPredictionSubmission>;
    } catch (error) {
      if (_profileGate.isActive(requestId)) {
        profileError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_profileGate.isActive(requestId)) {
        isLoadingProfile = false;
        notifyListeners();
      }
    }
  }

  Future<void> submitPrediction(
    String matchId,
    FanPredictionSubmissionRequest request,
  ) async {
    if (isSubmittingPrediction) {
      return;
    }
    isSubmittingPrediction = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.submitPrediction(matchId, request);
      await Future.wait<void>(<Future<void>>[
        loadFixture(matchId, leaderboardQuery: currentMatchLeaderboardQuery),
        loadProfile(),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSubmittingPrediction = false;
      notifyListeners();
    }
  }

  Future<void> configureFixture(
    String matchId,
    FanPredictionFixtureConfigRequest request,
  ) async {
    if (isConfiguringFixture) {
      return;
    }
    isConfiguringFixture = true;
    actionError = null;
    notifyListeners();
    try {
      fixture = await _repository.configureFixture(matchId, request);
      await loadFixture(matchId,
          leaderboardQuery: currentMatchLeaderboardQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isConfiguringFixture = false;
      notifyListeners();
    }
  }

  Future<void> settleFixture(
    String matchId,
    FanPredictionOutcomeOverrideRequest request,
  ) async {
    if (isSettlingFixture) {
      return;
    }
    isSettlingFixture = true;
    actionError = null;
    notifyListeners();
    try {
      fixture = await _repository.settleFixture(matchId, request);
      await Future.wait<void>(<Future<void>>[
        loadFixture(matchId, leaderboardQuery: currentMatchLeaderboardQuery),
        loadLeaderboards(
          weeklyQuery: currentWeeklyQuery,
          creatorClubId: currentCreatorClubId,
        ),
        loadProfile(),
      ]);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isSettlingFixture = false;
      notifyListeners();
    }
  }
}
