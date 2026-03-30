import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/football_world_simulation_models.dart';
import '../data/football_world_simulation_repository.dart';

class FootballWorldSimulationController extends ChangeNotifier {
  FootballWorldSimulationController({
    required FootballWorldSimulationRepository repository,
  }) : _repository = repository;

  factory FootballWorldSimulationController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return FootballWorldSimulationController(
      repository: FootballWorldSimulationApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final FootballWorldSimulationRepository _repository;
  final GteRequestGate _cultureGate = GteRequestGate();
  final GteRequestGate _contextGate = GteRequestGate();
  final GteRequestGate _federationGate = GteRequestGate();

  FootballCultureListQuery currentCultureQuery =
      const FootballCultureListQuery();
  WorldNarrativeListQuery currentNarrativeQuery =
      const WorldNarrativeListQuery();

  List<FootballCulture> cultures = const <FootballCulture>[];
  List<WorldFederation> federations = const <WorldFederation>[];
  ClubWorldContext? clubContext;
  CompetitionWorldContext? competitionContext;
  List<WorldNarrative> narratives = const <WorldNarrative>[];

  bool isLoadingCultures = false;
  bool isLoadingContext = false;
  bool isLoadingFederations = false;
  bool isUpsertingCulture = false;
  bool isUpsertingClubContext = false;
  bool isUpsertingNarrative = false;
  bool isJoiningFederation = false;
  String? joiningFederationId;

  String? cultureError;
  String? contextError;
  String? federationError;
  String? actionError;

  Future<void> loadCultures({
    FootballCultureListQuery query = const FootballCultureListQuery(),
  }) async {
    final int requestId = _cultureGate.begin();
    currentCultureQuery = query;
    cultureError = null;
    isLoadingCultures = true;
    notifyListeners();

    try {
      final List<FootballCulture> result = await _repository.listCultures(
        query,
      );
      if (!_cultureGate.isActive(requestId)) {
        return;
      }
      cultures = result;
    } catch (error) {
      if (_cultureGate.isActive(requestId)) {
        cultureError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_cultureGate.isActive(requestId)) {
        isLoadingCultures = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadContext({
    String? clubId,
    String? competitionId,
    WorldNarrativeListQuery narrativeQuery = const WorldNarrativeListQuery(),
  }) async {
    final int requestId = _contextGate.begin();
    currentNarrativeQuery = narrativeQuery;
    contextError = null;
    isLoadingContext = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
            if (clubId != null) _repository.fetchClubContext(clubId),
            if (competitionId != null)
              _repository.fetchCompetitionContext(competitionId),
            _repository.listNarratives(narrativeQuery),
          ]);
      if (!_contextGate.isActive(requestId)) {
        return;
      }
      int index = 0;
      if (clubId != null) {
        clubContext = payload[index++] as ClubWorldContext;
      }
      if (competitionId != null) {
        competitionContext = payload[index++] as CompetitionWorldContext;
      }
      narratives = payload[index] as List<WorldNarrative>;
    } catch (error) {
      if (_contextGate.isActive(requestId)) {
        contextError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_contextGate.isActive(requestId)) {
        isLoadingContext = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadFederations() async {
    final int requestId = _federationGate.begin();
    federationError = null;
    isLoadingFederations = true;
    notifyListeners();

    try {
      final List<WorldFederation> result = await _repository.listFederations();
      if (!_federationGate.isActive(requestId)) {
        return;
      }
      federations = result;
    } catch (error) {
      if (_federationGate.isActive(requestId)) {
        federationError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_federationGate.isActive(requestId)) {
        isLoadingFederations = false;
        notifyListeners();
      }
    }
  }

  Future<void> upsertCulture(
    String cultureKey,
    FootballCultureUpsertRequest request,
  ) async {
    if (isUpsertingCulture) {
      return;
    }
    isUpsertingCulture = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.upsertCulture(cultureKey, request);
      await loadCultures(query: currentCultureQuery);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingCulture = false;
      notifyListeners();
    }
  }

  Future<void> upsertClubContext(
    String clubId,
    ClubWorldProfileUpsertRequest request,
  ) async {
    if (isUpsertingClubContext) {
      return;
    }
    isUpsertingClubContext = true;
    actionError = null;
    notifyListeners();
    try {
      clubContext = await _repository.upsertClubContext(clubId, request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingClubContext = false;
      notifyListeners();
    }
  }

  Future<void> upsertNarrative(
    String narrativeSlug,
    WorldNarrativeUpsertRequest request,
  ) async {
    if (isUpsertingNarrative) {
      return;
    }
    isUpsertingNarrative = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.upsertNarrative(narrativeSlug, request);
      await loadContext(
        clubId: request.clubId,
        competitionId: request.competitionId,
        narrativeQuery: WorldNarrativeListQuery(
          clubId: currentNarrativeQuery.clubId,
          competitionId: currentNarrativeQuery.competitionId,
          limit: currentNarrativeQuery.limit,
        ),
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingNarrative = false;
      notifyListeners();
    }
  }

  Future<WorldFederationMembership?> joinFederation(
    String federationId, {
    required String clubId,
  }) async {
    if (isJoiningFederation) {
      return null;
    }
    isJoiningFederation = true;
    joiningFederationId = federationId;
    actionError = null;
    notifyListeners();
    try {
      final WorldFederationMembership membership = await _repository
          .joinFederation(federationId, clubId: clubId);
      await loadFederations();
      return membership;
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
      return null;
    } finally {
      isJoiningFederation = false;
      joiningFederationId = null;
      notifyListeners();
    }
  }
}
