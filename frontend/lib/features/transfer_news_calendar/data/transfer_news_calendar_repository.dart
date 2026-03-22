import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../shared/data/gte_feature_support.dart';
import 'transfer_news_calendar_models.dart';

abstract class TransferNewsCalendarRepository {
  Future<PlayerRealWorldImpact> fetchPlayerImpact(String playerId);

  Future<List<RealWorldFootballEvent>> listPlayerEvents(
    String playerId, {
    int limit = 20,
  });

  Future<List<RealWorldFootballEvent>> listAdminEvents(
    FootballEventsAdminQuery query,
  );

  Future<RealWorldFootballEvent> createAdminEvent(
    RealWorldFootballEventCreateRequest request,
  );

  Future<EventIngestionJob> importAdminEvents(
    EventFeedIngestionRequestModel request,
  );

  Future<RealWorldFootballEvent> reviewAdminEvent(
    String eventId,
    EventReviewRequest request,
  );

  Future<RealWorldFootballEvent> overrideAdminEventSeverity(
    String eventId,
    EventSeverityOverrideRequest request,
  );

  Future<List<EventEffectRule>> listEventRules(FootballEventRulesQuery query);

  Future<EventEffectRule> upsertEventRule(
    EventEffectRuleUpsertRequest request,
  );

  Future<List<EventEffectRule>> toggleEventCategory(
    EventCategoryToggleRequest request,
  );

  Future<JsonMap> expireEffects(ExpireEffectsRequest request);

  Future<CalendarDashboard> fetchCalendarDashboard();

  Future<List<CalendarSeasonViewModel>> listCalendarSeasons(
    CalendarSeasonsQuery query,
  );

  Future<List<CalendarEventViewModel>> listCalendarEvents(
    CalendarEventsQuery query,
  );

  Future<PauseStatusViewModel> fetchPauseStatus(PauseStatusQuery query);

  Future<List<CompetitionLifecycleRunViewModel>> listLifecycleRuns();

  Future<CalendarSeasonViewModel> createCalendarSeason(
    CalendarSeasonCreateRequest request,
  );

  Future<CalendarEventViewModel> createCalendarEvent(
    CalendarEventCreateRequest request,
  );

  Future<CompetitionLifecycleRunViewModel> launchHostedCompetition(
    String competitionId,
    HostedCompetitionLaunchRequest request,
  );

  Future<CompetitionLifecycleRunViewModel> launchNationalCompetition(
    String competitionId,
    NationalCompetitionLaunchRequest request,
  );
}

class TransferNewsCalendarApiRepository
    implements TransferNewsCalendarRepository {
  TransferNewsCalendarApiRepository({
    required GteAuthedApi client,
  }) : _client = client;

  factory TransferNewsCalendarApiRepository.standard({
    required String baseUrl,
    required GteBackendMode mode,
    required String? accessToken,
  }) {
    return TransferNewsCalendarApiRepository(
      client: createFeatureApi(
        baseUrl: baseUrl,
        mode: mode,
        accessToken: accessToken,
      ),
    );
  }

  final GteAuthedApi _client;

  @override
  Future<PlayerRealWorldImpact> fetchPlayerImpact(String playerId) async {
    return PlayerRealWorldImpact.fromJson(
      await _client.getMap('/football-events/players/$playerId/impact',
          auth: false),
    );
  }

  @override
  Future<List<RealWorldFootballEvent>> listPlayerEvents(
    String playerId, {
    int limit = 20,
  }) async {
    return parseList(
      await _client.getList(
        '/football-events/players/$playerId/events',
        query: <String, Object?>{'limit': limit},
        auth: false,
      ),
      RealWorldFootballEvent.fromJson,
      label: 'player football events',
    );
  }

  @override
  Future<List<RealWorldFootballEvent>> listAdminEvents(
    FootballEventsAdminQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/admin/football-events/events',
        query: query.toQuery(),
      ),
      RealWorldFootballEvent.fromJson,
      label: 'admin football events',
    );
  }

  @override
  Future<RealWorldFootballEvent> createAdminEvent(
    RealWorldFootballEventCreateRequest request,
  ) async {
    return RealWorldFootballEvent.fromJson(
      await _client.request(
        'POST',
        '/admin/football-events/events',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<EventIngestionJob> importAdminEvents(
    EventFeedIngestionRequestModel request,
  ) async {
    return EventIngestionJob.fromJson(
      await _client.request(
        'POST',
        '/admin/football-events/events/import',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<RealWorldFootballEvent> reviewAdminEvent(
    String eventId,
    EventReviewRequest request,
  ) async {
    return RealWorldFootballEvent.fromJson(
      await _client.request(
        'POST',
        '/admin/football-events/events/$eventId/review',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<RealWorldFootballEvent> overrideAdminEventSeverity(
    String eventId,
    EventSeverityOverrideRequest request,
  ) async {
    return RealWorldFootballEvent.fromJson(
      await _client.request(
        'POST',
        '/admin/football-events/events/$eventId/severity',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<EventEffectRule>> listEventRules(
    FootballEventRulesQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/admin/football-events/rules',
        query: query.toQuery(),
      ),
      EventEffectRule.fromJson,
      label: 'football event rules',
    );
  }

  @override
  Future<EventEffectRule> upsertEventRule(
    EventEffectRuleUpsertRequest request,
  ) async {
    return EventEffectRule.fromJson(
      await _client.request(
        'POST',
        '/admin/football-events/rules',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<List<EventEffectRule>> toggleEventCategory(
    EventCategoryToggleRequest request,
  ) async {
    return parseList(
      await _client.request(
        'POST',
        '/admin/football-events/categories',
        body: request.toJson(),
      ),
      EventEffectRule.fromJson,
      label: 'football event category rules',
    );
  }

  @override
  Future<JsonMap> expireEffects(ExpireEffectsRequest request) async {
    return jsonMap(
      await _client.request(
        'POST',
        '/admin/football-events/effects/expire',
        body: request.toJson(),
      ),
      label: 'expire football effects',
    );
  }

  @override
  Future<CalendarDashboard> fetchCalendarDashboard() async {
    return CalendarDashboard.fromJson(
      await _client.getMap('/calendar-engine/dashboard', auth: false),
    );
  }

  @override
  Future<List<CalendarSeasonViewModel>> listCalendarSeasons(
    CalendarSeasonsQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/calendar-engine/seasons',
        query: query.toQuery(),
        auth: false,
      ),
      CalendarSeasonViewModel.fromJson,
      label: 'calendar seasons',
    );
  }

  @override
  Future<List<CalendarEventViewModel>> listCalendarEvents(
    CalendarEventsQuery query,
  ) async {
    return parseList(
      await _client.getList(
        '/calendar-engine/events',
        query: query.toQuery(),
        auth: false,
      ),
      CalendarEventViewModel.fromJson,
      label: 'calendar events',
    );
  }

  @override
  Future<PauseStatusViewModel> fetchPauseStatus(PauseStatusQuery query) async {
    return PauseStatusViewModel.fromJson(
      await _client.getMap(
        '/calendar-engine/pause-status',
        query: query.toQuery(),
        auth: false,
      ),
    );
  }

  @override
  Future<List<CompetitionLifecycleRunViewModel>> listLifecycleRuns() async {
    return parseList(
      await _client.getList('/calendar-engine/lifecycle-runs', auth: false),
      CompetitionLifecycleRunViewModel.fromJson,
      label: 'calendar lifecycle runs',
    );
  }

  @override
  Future<CalendarSeasonViewModel> createCalendarSeason(
    CalendarSeasonCreateRequest request,
  ) async {
    return CalendarSeasonViewModel.fromJson(
      await _client.request(
        'POST',
        '/admin/calendar-engine/seasons',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CalendarEventViewModel> createCalendarEvent(
    CalendarEventCreateRequest request,
  ) async {
    return CalendarEventViewModel.fromJson(
      await _client.request(
        'POST',
        '/admin/calendar-engine/events',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CompetitionLifecycleRunViewModel> launchHostedCompetition(
    String competitionId,
    HostedCompetitionLaunchRequest request,
  ) async {
    return CompetitionLifecycleRunViewModel.fromJson(
      await _client.request(
        'POST',
        '/admin/calendar-engine/hosted-competitions/$competitionId/launch',
        body: request.toJson(),
      ),
    );
  }

  @override
  Future<CompetitionLifecycleRunViewModel> launchNationalCompetition(
    String competitionId,
    NationalCompetitionLaunchRequest request,
  ) async {
    return CompetitionLifecycleRunViewModel.fromJson(
      await _client.request(
        'POST',
        '/admin/calendar-engine/national-competitions/$competitionId/launch',
        body: request.toJson(),
      ),
    );
  }
}
