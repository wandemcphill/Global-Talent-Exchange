import 'package:flutter/foundation.dart';

import '../core/app_feedback.dart';
import '../core/state_sync_system.dart';
import '../data/creator_api.dart';
import '../data/gte_api_repository.dart';
import '../models/creator_models.dart';

class CreatorController extends ChangeNotifier {
  CreatorController({required CreatorApi api}) : _api = api {
    _syncSystem = StateSyncSystem(
      interval: const Duration(seconds: 60),
      onSync: () => load(force: true),
      onStateChanged: notifyListeners,
    );
  }

  final CreatorApi _api;
  final GteRequestGate _loadGate = GteRequestGate();
  final GteRequestGate _shareGate = GteRequestGate();
  final GteRequestGate _copilotGate = GteRequestGate();
  late final StateSyncSystem _syncSystem;

  bool isLoading = false;
  bool isLoadingCompetitionShare = false;
  bool isAnalyzingCopilot = false;
  String? errorMessage;
  String? copilotErrorMessage;
  CreatorProfile? profile;
  CreatorFinanceSummary? financeSummary;
  CreatorCompetitionShareData? competitionShare;
  CreatorCopilotDraft? copilotDraft;
  CreatorCopilotAnalysis? copilotAnalysis;

  bool get hasData => profile != null;
  DateTime? get syncedAt => _syncSystem.lastSyncedAt;
  bool get isSyncing => _syncSystem.isSyncing;

  void attachStateSync({bool syncImmediately = false}) {
    _syncSystem.attach(syncImmediately: syncImmediately);
  }

  void detachStateSync() {
    _syncSystem.detach();
  }

  Future<void> syncNow() => _syncSystem.sync();

  Future<void> syncAfterCriticalAction() =>
      _syncSystem.syncAfterCriticalAction();

  Future<void> load({String creatorId = 'me', bool force = false}) async {
    if (isLoading || (profile != null && !force)) {
      return;
    }
    final int requestId = _loadGate.begin();
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final Future<CreatorProfile> profileFuture = _api.fetchCreatorProfile(
        creatorId: creatorId,
      );
      final Future<CreatorFinanceSummary?> financeFuture;
      if (creatorId == 'me') {
        financeFuture = _api.fetchCreatorFinance();
      } else {
        financeFuture = Future<CreatorFinanceSummary?>.value(null);
      }
      final CreatorProfile nextProfile = await profileFuture;
      final CreatorFinanceSummary? nextFinance = await financeFuture;
      if (!_loadGate.isActive(requestId)) {
        return;
      }
      profile = nextProfile;
      financeSummary = nextFinance ?? nextProfile.financeSummary;
      if (nextProfile.competitions.isNotEmpty) {
        final String activeCompetitionId =
            competitionShare?.competition.competitionId ??
            nextProfile.competitions.first.competitionId;
        await selectCompetition(activeCompetitionId);
      } else {
        competitionShare = null;
      }
      if (creatorId == 'me') {
        copilotDraft ??= _defaultCopilotDraft(nextProfile);
        await analyzeCopilot(force: true);
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
      final CreatorCompetitionShareData data = await _api.fetchCompetitionShare(
        competitionId,
      );
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

  void setCopilotDraft(CreatorCopilotDraft draft) {
    copilotDraft = draft;
    copilotErrorMessage = null;
    notifyListeners();
  }

  Future<void> analyzeCopilot({bool force = false}) async {
    final CreatorCopilotDraft? draft = copilotDraft;
    if (draft == null) {
      return;
    }
    if (isAnalyzingCopilot && !force) {
      return;
    }
    final int requestId = _copilotGate.begin();
    isAnalyzingCopilot = true;
    copilotErrorMessage = null;
    notifyListeners();

    try {
      final CreatorCopilotAnalysis analysis = await _api.analyzeCopilotDraft(
        draft,
      );
      if (!_copilotGate.isActive(requestId)) {
        return;
      }
      copilotAnalysis = analysis;
    } catch (error) {
      if (_copilotGate.isActive(requestId)) {
        copilotErrorMessage = AppFeedback.messageFor(error);
      }
    } finally {
      if (_copilotGate.isActive(requestId)) {
        isAnalyzingCopilot = false;
        notifyListeners();
      }
    }
  }

  CreatorCopilotDraft _defaultCopilotDraft(CreatorProfile profile) {
    final bool leansShort = profile.financeSummary.viralClipCount > 0;
    return CreatorCopilotDraft(
      title: '${profile.displayName} upload draft',
      durationSeconds: leansShort ? 17 : 21,
      eventType: 'goal',
      tags: const <String>['reaction', 'matchday'],
      preferredFormat: leansShort ? 'meme' : 'instant',
      introSeconds: 1.2,
      visualIntensity: 0.68,
      eventDensity: 0.63,
      audienceCluster: 'general',
      hasReactionOverlay: leansShort,
    );
  }

  @override
  void dispose() {
    _syncSystem.stop();
    super.dispose();
  }
}
