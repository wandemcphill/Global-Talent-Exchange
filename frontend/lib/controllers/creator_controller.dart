import 'package:flutter/foundation.dart';
import '../core/app_feedback.dart';

import '../data/creator_api.dart';
import '../data/gte_api_repository.dart';
import '../models/creator_models.dart';

class CreatorController extends ChangeNotifier {
  CreatorController({
    required CreatorApi api,
  }) : _api = api;

  final CreatorApi _api;
  final GteRequestGate _loadGate = GteRequestGate();
  final GteRequestGate _shareGate = GteRequestGate();

  bool isLoading = false;
  bool isLoadingCompetitionShare = false;
  String? errorMessage;
  CreatorProfile? profile;
  CreatorCompetitionShareData? competitionShare;

  bool get hasData => profile != null;

  Future<void> load({
    String creatorId = 'me',
    bool force = false,
  }) async {
    if (isLoading || (profile != null && !force)) {
      return;
    }
    final int requestId = _loadGate.begin();
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final CreatorProfile nextProfile =
          await _api.fetchCreatorProfile(creatorId: creatorId);
      if (!_loadGate.isActive(requestId)) {
        return;
      }
      profile = nextProfile;
      if (nextProfile.competitions.isNotEmpty) {
        await selectCompetition(nextProfile.competitions.first.competitionId);
      } else {
        competitionShare = null;
      }
      errorMessage = null;
    } catch (error) {
      if (_loadGate.isActive(requestId)) {
        errorMessage = AppFeedback.messageFor(error);
      }
    } finally {
      if (_loadGate.isActive(requestId)) {
        isLoading = false;
        notifyListeners();
      }
    }
  }

  Future<void> selectCompetition(String competitionId) async {
    final int requestId = _shareGate.begin();
    isLoadingCompetitionShare = true;
    notifyListeners();

    try {
      final CreatorCompetitionShareData data =
          await _api.fetchCompetitionShare(competitionId);
      if (!_shareGate.isActive(requestId)) {
        return;
      }
      competitionShare = data;
    } catch (error) {
      if (_shareGate.isActive(requestId)) {
        errorMessage = AppFeedback.messageFor(error);
      }
    } finally {
      if (_shareGate.isActive(requestId)) {
        isLoadingCompetitionShare = false;
        notifyListeners();
      }
    }
  }
}
