import 'package:flutter/foundation.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../data/transfer_news_calendar_models.dart';
import '../data/transfer_news_calendar_repository.dart';

class TransferNewsCalendarController extends ChangeNotifier {
  TransferNewsCalendarController({
    required TransferNewsCalendarRepository repository,
  }) : _repository = repository;

  factory TransferNewsCalendarController.standard({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return TransferNewsCalendarController(
      repository: TransferNewsCalendarApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
        accessToken: accessToken,
      ),
    );
  }

  final TransferNewsCalendarRepository _repository;
  final GteRequestGate _eventsGate = GteRequestGate();
  final GteRequestGate _calendarGate = GteRequestGate();
  final GteRequestGate _adminGate = GteRequestGate();

  FootballEventsAdminQuery currentEventsAdminQuery =
      const FootballEventsAdminQuery();
  FootballEventRulesQuery currentRulesQuery = const FootballEventRulesQuery();
  CalendarSeasonsQuery currentSeasonsQuery = const CalendarSeasonsQuery();
  CalendarEventsQuery currentEventsQuery = const CalendarEventsQuery();
  PauseStatusQuery currentPauseStatusQuery = const PauseStatusQuery();

  PlayerRealWorldImpact? playerImpact;
  List<RealWorldFootballEvent> playerEvents = const <RealWorldFootballEvent>[];
  List<RealWorldFootballEvent> adminEvents = const <RealWorldFootballEvent>[];
  List<EventEffectRule> eventRules = const <EventEffectRule>[];
  EventIngestionJob? latestIngestionJob;
  Map<String, Object?> latestExpireResult = const <String, Object?>{};

  CalendarDashboard? calendarDashboard;
  List<CalendarSeasonViewModel> seasons = const <CalendarSeasonViewModel>[];
  List<CalendarEventViewModel> calendarEvents =
      const <CalendarEventViewModel>[];
  PauseStatusViewModel? pauseStatus;
  List<CompetitionLifecycleRunViewModel> lifecycleRuns =
      const <CompetitionLifecycleRunViewModel>[];

  bool isLoadingEvents = false;
  bool isLoadingCalendar = false;
  bool isLoadingAdmin = false;
  bool isCreatingAdminEvent = false;
  bool isImportingEvents = false;
  bool isReviewingEvent = false;
  bool isOverridingSeverity = false;
  bool isUpsertingRule = false;
  bool isTogglingCategory = false;
  bool isExpiringEffects = false;
  bool isCreatingSeason = false;
  bool isCreatingCalendarEvent = false;
  bool isLaunchingHostedCompetition = false;
  bool isLaunchingNationalCompetition = false;

  String? eventsError;
  String? calendarError;
  String? adminError;
  String? actionError;

  Future<void> loadPlayerEvents(
    String playerId, {
    int limit = 20,
  }) async {
    final int requestId = _eventsGate.begin();
    eventsError = null;
    isLoadingEvents = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchPlayerImpact(playerId),
        _repository.listPlayerEvents(playerId, limit: limit),
      ]);
      if (!_eventsGate.isActive(requestId)) {
        return;
      }
      playerImpact = payload[0] as PlayerRealWorldImpact;
      playerEvents = payload[1] as List<RealWorldFootballEvent>;
    } catch (error) {
      if (_eventsGate.isActive(requestId)) {
        eventsError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_eventsGate.isActive(requestId)) {
        isLoadingEvents = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadAdminEvents({
    FootballEventsAdminQuery eventsQuery = const FootballEventsAdminQuery(),
    FootballEventRulesQuery rulesQuery = const FootballEventRulesQuery(),
  }) async {
    final int requestId = _adminGate.begin();
    currentEventsAdminQuery = eventsQuery;
    currentRulesQuery = rulesQuery;
    adminError = null;
    isLoadingAdmin = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.listAdminEvents(eventsQuery),
        _repository.listEventRules(rulesQuery),
      ]);
      if (!_adminGate.isActive(requestId)) {
        return;
      }
      adminEvents = payload[0] as List<RealWorldFootballEvent>;
      eventRules = payload[1] as List<EventEffectRule>;
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

  Future<void> loadCalendar({
    CalendarSeasonsQuery seasonsQuery = const CalendarSeasonsQuery(),
    CalendarEventsQuery eventsQuery = const CalendarEventsQuery(),
    PauseStatusQuery pauseQuery = const PauseStatusQuery(),
  }) async {
    final int requestId = _calendarGate.begin();
    currentSeasonsQuery = seasonsQuery;
    currentEventsQuery = eventsQuery;
    currentPauseStatusQuery = pauseQuery;
    calendarError = null;
    isLoadingCalendar = true;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchCalendarDashboard(),
        _repository.listCalendarSeasons(seasonsQuery),
        _repository.listCalendarEvents(eventsQuery),
        _repository.fetchPauseStatus(pauseQuery),
        _repository.listLifecycleRuns(),
      ]);
      if (!_calendarGate.isActive(requestId)) {
        return;
      }
      calendarDashboard = payload[0] as CalendarDashboard;
      seasons = payload[1] as List<CalendarSeasonViewModel>;
      calendarEvents = payload[2] as List<CalendarEventViewModel>;
      pauseStatus = payload[3] as PauseStatusViewModel;
      lifecycleRuns = payload[4] as List<CompetitionLifecycleRunViewModel>;
    } catch (error) {
      if (_calendarGate.isActive(requestId)) {
        calendarError = AppFeedback.messageFor(error);
      }
    } finally {
      if (_calendarGate.isActive(requestId)) {
        isLoadingCalendar = false;
        notifyListeners();
      }
    }
  }

  Future<void> createAdminEvent(
    RealWorldFootballEventCreateRequest request,
  ) async {
    if (isCreatingAdminEvent) {
      return;
    }
    isCreatingAdminEvent = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createAdminEvent(request);
      await loadAdminEvents(
        eventsQuery: currentEventsAdminQuery,
        rulesQuery: currentRulesQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingAdminEvent = false;
      notifyListeners();
    }
  }

  Future<void> importEvents(EventFeedIngestionRequestModel request) async {
    if (isImportingEvents) {
      return;
    }
    isImportingEvents = true;
    actionError = null;
    notifyListeners();
    try {
      latestIngestionJob = await _repository.importAdminEvents(request);
      await loadAdminEvents(
        eventsQuery: currentEventsAdminQuery,
        rulesQuery: currentRulesQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isImportingEvents = false;
      notifyListeners();
    }
  }

  Future<void> reviewEvent(
    String eventId,
    EventReviewRequest request,
  ) async {
    if (isReviewingEvent) {
      return;
    }
    isReviewingEvent = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.reviewAdminEvent(eventId, request);
      await loadAdminEvents(
        eventsQuery: currentEventsAdminQuery,
        rulesQuery: currentRulesQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isReviewingEvent = false;
      notifyListeners();
    }
  }

  Future<void> overrideSeverity(
    String eventId,
    EventSeverityOverrideRequest request,
  ) async {
    if (isOverridingSeverity) {
      return;
    }
    isOverridingSeverity = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.overrideAdminEventSeverity(eventId, request);
      await loadAdminEvents(
        eventsQuery: currentEventsAdminQuery,
        rulesQuery: currentRulesQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isOverridingSeverity = false;
      notifyListeners();
    }
  }

  Future<void> upsertRule(EventEffectRuleUpsertRequest request) async {
    if (isUpsertingRule) {
      return;
    }
    isUpsertingRule = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.upsertEventRule(request);
      await loadAdminEvents(
        eventsQuery: currentEventsAdminQuery,
        rulesQuery: currentRulesQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isUpsertingRule = false;
      notifyListeners();
    }
  }

  Future<void> toggleCategory(EventCategoryToggleRequest request) async {
    if (isTogglingCategory) {
      return;
    }
    isTogglingCategory = true;
    actionError = null;
    notifyListeners();
    try {
      eventRules = await _repository.toggleEventCategory(request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isTogglingCategory = false;
      notifyListeners();
    }
  }

  Future<void> expireEffects(ExpireEffectsRequest request) async {
    if (isExpiringEffects) {
      return;
    }
    isExpiringEffects = true;
    actionError = null;
    notifyListeners();
    try {
      latestExpireResult = await _repository.expireEffects(request);
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isExpiringEffects = false;
      notifyListeners();
    }
  }

  Future<void> createSeason(CalendarSeasonCreateRequest request) async {
    if (isCreatingSeason) {
      return;
    }
    isCreatingSeason = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createCalendarSeason(request);
      await loadCalendar(
        seasonsQuery: currentSeasonsQuery,
        eventsQuery: currentEventsQuery,
        pauseQuery: currentPauseStatusQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingSeason = false;
      notifyListeners();
    }
  }

  Future<void> createCalendarEvent(CalendarEventCreateRequest request) async {
    if (isCreatingCalendarEvent) {
      return;
    }
    isCreatingCalendarEvent = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.createCalendarEvent(request);
      await loadCalendar(
        seasonsQuery: currentSeasonsQuery,
        eventsQuery: currentEventsQuery,
        pauseQuery: currentPauseStatusQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isCreatingCalendarEvent = false;
      notifyListeners();
    }
  }

  Future<void> launchHostedCompetition(
    String competitionId,
    HostedCompetitionLaunchRequest request,
  ) async {
    if (isLaunchingHostedCompetition) {
      return;
    }
    isLaunchingHostedCompetition = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.launchHostedCompetition(competitionId, request);
      await loadCalendar(
        seasonsQuery: currentSeasonsQuery,
        eventsQuery: currentEventsQuery,
        pauseQuery: currentPauseStatusQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isLaunchingHostedCompetition = false;
      notifyListeners();
    }
  }

  Future<void> launchNationalCompetition(
    String competitionId,
    NationalCompetitionLaunchRequest request,
  ) async {
    if (isLaunchingNationalCompetition) {
      return;
    }
    isLaunchingNationalCompetition = true;
    actionError = null;
    notifyListeners();
    try {
      await _repository.launchNationalCompetition(competitionId, request);
      await loadCalendar(
        seasonsQuery: currentSeasonsQuery,
        eventsQuery: currentEventsQuery,
        pauseQuery: currentPauseStatusQuery,
      );
    } catch (error) {
      actionError = AppFeedback.messageFor(error);
    } finally {
      isLaunchingNationalCompetition = false;
      notifyListeners();
    }
  }
}
