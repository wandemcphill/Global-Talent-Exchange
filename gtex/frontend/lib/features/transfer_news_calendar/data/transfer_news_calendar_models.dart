import '../../shared/data/gte_feature_support.dart';

class FootballEventsAdminQuery {
  const FootballEventsAdminQuery({
    this.approvalStatus,
    this.playerId,
    this.eventType,
    this.limit = 100,
  });

  final String? approvalStatus;
  final String? playerId;
  final String? eventType;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'approval_status': approvalStatus,
        'player_id': playerId,
        'event_type': eventType,
        'limit': limit,
      });
}

class FootballEventRulesQuery {
  const FootballEventRulesQuery({
    this.eventType,
    this.activeOnly = false,
  });

  final String? eventType;
  final bool activeOnly;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'event_type': eventType,
        'active_only': activeOnly,
      });
}

class CalendarSeasonsQuery {
  const CalendarSeasonsQuery({
    this.activeOnly = false,
  });

  final bool activeOnly;

  Map<String, Object?> toQuery() => <String, Object?>{
        'active_only': activeOnly,
      };
}

class CalendarEventsQuery {
  const CalendarEventsQuery({
    this.activeOnly = false,
    this.asOf,
    this.sourceType,
    this.sourceId,
    this.family,
    this.visibility,
    this.status,
  });

  final bool activeOnly;
  final DateTime? asOf;
  final String? sourceType;
  final String? sourceId;
  final String? family;
  final String? visibility;
  final String? status;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'active_only': activeOnly,
        'as_of': dateQueryValue(asOf),
        'source_type': sourceType,
        'source_id': sourceId,
        'family': family,
        'visibility': visibility,
        'status': status,
      });
}

class PauseStatusQuery {
  const PauseStatusQuery({
    this.asOf,
  });

  final DateTime? asOf;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'as_of': dateQueryValue(asOf),
      });
}

class RealWorldFootballEventCreateRequest {
  const RealWorldFootballEventCreateRequest({
    required this.eventType,
    required this.playerId,
    required this.occurredAt,
    this.sourceType = 'manual',
    this.sourceLabel = 'admin_manual',
    this.externalEventId,
    this.title,
    this.summary,
    this.severity = 1.0,
    this.currentClubId,
    this.competitionId,
    this.requiresAdminReview,
    this.metadata = const <String, Object?>{},
    this.rawPayload = const <String, Object?>{},
  });

  final String eventType;
  final String playerId;
  final DateTime occurredAt;
  final String sourceType;
  final String sourceLabel;
  final String? externalEventId;
  final String? title;
  final String? summary;
  final double severity;
  final String? currentClubId;
  final String? competitionId;
  final bool? requiresAdminReview;
  final JsonMap metadata;
  final JsonMap rawPayload;

  JsonMap toJson() => <String, Object?>{
        'event_type': eventType,
        'player_id': playerId,
        'occurred_at': occurredAt.toUtc().toIso8601String(),
        'source_type': sourceType,
        'source_label': sourceLabel,
        if (externalEventId != null) 'external_event_id': externalEventId,
        if (title != null) 'title': title,
        if (summary != null) 'summary': summary,
        'severity': severity,
        if (currentClubId != null) 'current_club_id': currentClubId,
        if (competitionId != null) 'competition_id': competitionId,
        if (requiresAdminReview != null)
          'requires_admin_review': requiresAdminReview,
        'metadata': metadata,
        'raw_payload': rawPayload,
      };
}

class EventFeedIngestionRequestModel {
  const EventFeedIngestionRequestModel({
    required this.sourceLabel,
    this.sourceType = 'import_feed',
    this.events = const <RealWorldFootballEventCreateRequest>[],
  });

  final String sourceLabel;
  final String sourceType;
  final List<RealWorldFootballEventCreateRequest> events;

  JsonMap toJson() => <String, Object?>{
        'source_label': sourceLabel,
        'source_type': sourceType,
        'events': events
            .map((RealWorldFootballEventCreateRequest item) => item.toJson())
            .toList(growable: false),
      };
}

class EventReviewRequest {
  const EventReviewRequest({
    required this.approve,
    this.notes,
  });

  final bool approve;
  final String? notes;

  JsonMap toJson() => <String, Object?>{
        'approve': approve,
        if (notes != null) 'notes': notes,
      };
}

class EventSeverityOverrideRequest {
  const EventSeverityOverrideRequest({
    this.severity,
  });

  final double? severity;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'severity': severity,
      });
}

class EventCategoryToggleRequest {
  const EventCategoryToggleRequest({
    required this.eventType,
    required this.isEnabled,
  });

  final String eventType;
  final bool isEnabled;

  JsonMap toJson() => <String, Object?>{
        'event_type': eventType,
        'is_enabled': isEnabled,
      };
}

class EventEffectRuleUpsertRequest {
  const EventEffectRuleUpsertRequest({
    required this.eventType,
    required this.effectType,
    required this.effectCode,
    required this.label,
    this.isEnabled = true,
    this.approvalRequired = false,
    this.baseMagnitude = 0,
    this.durationHours = 0,
    this.priority = 0,
    this.gameplayEnabled = false,
    this.marketEnabled = false,
    this.recommendationEnabled = false,
    this.config = const <String, Object?>{},
  });

  final String eventType;
  final String effectType;
  final String effectCode;
  final String label;
  final bool isEnabled;
  final bool approvalRequired;
  final double baseMagnitude;
  final int durationHours;
  final int priority;
  final bool gameplayEnabled;
  final bool marketEnabled;
  final bool recommendationEnabled;
  final JsonMap config;

  JsonMap toJson() => <String, Object?>{
        'event_type': eventType,
        'effect_type': effectType,
        'effect_code': effectCode,
        'label': label,
        'is_enabled': isEnabled,
        'approval_required': approvalRequired,
        'base_magnitude': baseMagnitude,
        'duration_hours': durationHours,
        'priority': priority,
        'gameplay_enabled': gameplayEnabled,
        'market_enabled': marketEnabled,
        'recommendation_enabled': recommendationEnabled,
        'config': config,
      };
}

class ExpireEffectsRequest {
  const ExpireEffectsRequest({
    this.asOf,
  });

  final DateTime? asOf;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'as_of': asOf?.toUtc().toIso8601String(),
      });
}

class CalendarSeasonCreateRequest {
  const CalendarSeasonCreateRequest({
    required this.seasonKey,
    required this.title,
    required this.startsOn,
    required this.endsOn,
    this.status = 'draft',
    this.metadata = const <String, Object?>{},
  });

  final String seasonKey;
  final String title;
  final DateTime startsOn;
  final DateTime endsOn;
  final String status;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        'season_key': seasonKey,
        'title': title,
        'starts_on': dateQueryValue(startsOn),
        'ends_on': dateQueryValue(endsOn),
        'status': status,
        'metadata_json': metadata,
      };
}

class CalendarEventCreateRequest {
  const CalendarEventCreateRequest({
    required this.eventKey,
    required this.title,
    required this.startsOn,
    required this.endsOn,
    this.seasonId,
    this.description,
    this.sourceType = 'manual',
    this.sourceId,
    this.family = 'general',
    this.ageBand = 'senior',
    this.exclusiveWindows = false,
    this.pauseOtherGtxCompetitions = false,
    this.visibility = 'public',
    this.status = 'scheduled',
    this.metadata = const <String, Object?>{},
  });

  final String eventKey;
  final String title;
  final DateTime startsOn;
  final DateTime endsOn;
  final String? seasonId;
  final String? description;
  final String sourceType;
  final String? sourceId;
  final String family;
  final String ageBand;
  final bool exclusiveWindows;
  final bool pauseOtherGtxCompetitions;
  final String visibility;
  final String status;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (seasonId != null) 'season_id': seasonId,
        'event_key': eventKey,
        'title': title,
        if (description != null) 'description': description,
        'source_type': sourceType,
        if (sourceId != null) 'source_id': sourceId,
        'family': family,
        'age_band': ageBand,
        'starts_on': dateQueryValue(startsOn),
        'ends_on': dateQueryValue(endsOn),
        'exclusive_windows': exclusiveWindows,
        'pause_other_gtx_competitions': pauseOtherGtxCompetitions,
        'visibility': visibility,
        'status': status,
        'metadata_json': metadata,
      };
}

class HostedCompetitionLaunchRequest {
  const HostedCompetitionLaunchRequest({
    this.startsOn,
    this.overrideTitle,
    this.preferredFamily = 'hosted',
  });

  final DateTime? startsOn;
  final String? overrideTitle;
  final String preferredFamily;

  JsonMap toJson() => <String, Object?>{
        if (startsOn != null) 'starts_on': dateQueryValue(startsOn),
        if (overrideTitle != null) 'override_title': overrideTitle,
        'preferred_family': preferredFamily,
      };
}

class NationalCompetitionLaunchRequest {
  const NationalCompetitionLaunchRequest({
    this.startsOn,
    this.overrideTitle,
    this.exclusiveWindows,
    this.pauseOtherGtxCompetitions,
  });

  final DateTime? startsOn;
  final String? overrideTitle;
  final bool? exclusiveWindows;
  final bool? pauseOtherGtxCompetitions;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'starts_on': dateQueryValue(startsOn),
        'override_title': overrideTitle,
        'exclusive_windows': exclusiveWindows,
        'pause_other_gtx_competitions': pauseOtherGtxCompetitions,
      });
}

class PlayerRealWorldImpact {
  const PlayerRealWorldImpact._(this.raw);

  final JsonMap raw;

  factory PlayerRealWorldImpact.fromJson(Object? value) {
    return PlayerRealWorldImpact._(
      jsonMap(value, label: 'player real world impact'),
    );
  }

  String get playerId => stringValue(raw['player_id']);
  List<JsonMap> get activeFlags =>
      jsonMapList(raw['active_flags'], label: 'active event flags');
  List<JsonMap> get activeFormModifiers => jsonMapList(
        raw['active_form_modifiers'],
        label: 'active form modifiers',
      );
  List<JsonMap> get activeDemandSignals => jsonMapList(
        raw['active_demand_signals'],
        label: 'active demand signals',
      );
  List<String> get activeFlagCodes => stringListValue(raw['active_flag_codes']);
  List<String> get affectedCardIds => stringListValue(raw['affected_card_ids']);
  double get recommendationPriorityDelta =>
      numberValue(raw['recommendation_priority_delta']);
  double get marketBuzzScore => numberValue(raw['market_buzz_score']);
  double get gameplayEffectTotal => numberValue(raw['gameplay_effect_total']);
  double get marketEffectTotal => numberValue(raw['market_effect_total']);
}

class RealWorldFootballEvent {
  const RealWorldFootballEvent._(this.raw);

  final JsonMap raw;

  factory RealWorldFootballEvent.fromJson(Object? value) {
    return RealWorldFootballEvent._(
      jsonMap(value, label: 'real world football event'),
    );
  }

  String get id => stringValue(raw['id']);
  String? get ingestionJobId => stringOrNullValue(raw['ingestion_job_id']);
  String get playerId => stringValue(raw['player_id']);
  String? get currentClubId => stringOrNullValue(raw['current_club_id']);
  String? get competitionId => stringOrNullValue(raw['competition_id']);
  String get eventType => stringValue(raw['event_type']);
  String get sourceType => stringValue(raw['source_type']);
  String get sourceLabel => stringValue(raw['source_label']);
  String? get externalEventId => stringOrNullValue(raw['external_event_id']);
  String get approvalStatus => stringValue(raw['approval_status']);
  bool get requiresAdminReview => boolValue(raw['requires_admin_review']);
  String get title => stringValue(raw['title']);
  String? get summary => stringOrNullValue(raw['summary']);
  double get severity => numberValue(raw['severity']);
  double? get effectSeverityOverride => raw['effect_severity_override'] == null
      ? null
      : numberValue(raw['effect_severity_override']);
  DateTime? get occurredAt => dateTimeValue(raw['occurred_at']);
  String? get reviewNotes => stringOrNullValue(raw['review_notes']);
  DateTime? get effectsAppliedAt => dateTimeValue(raw['effects_applied_at']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
  JsonMap get normalizedPayload => jsonMap(raw['normalized_payload_json'],
      fallback: const <String, Object?>{});
  String? get storyFeedItemId => stringOrNullValue(raw['story_feed_item_id']);
  String? get calendarEventId => stringOrNullValue(raw['calendar_event_id']);
  List<String> get affectedCardIds => stringListValue(raw['affected_card_ids']);
  int get activeFlagCount => intValue(raw['active_flag_count']);
  int get activeModifierCount => intValue(raw['active_modifier_count']);
  int get activeDemandSignalCount =>
      intValue(raw['active_demand_signal_count']);
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
}

class EventEffectRule {
  const EventEffectRule._(this.raw);

  final JsonMap raw;

  factory EventEffectRule.fromJson(Object? value) {
    return EventEffectRule._(jsonMap(value, label: 'event effect rule'));
  }

  String get id => stringValue(raw['id']);
  String get eventType => stringValue(raw['event_type']);
  String get effectType => stringValue(raw['effect_type']);
  String get effectCode => stringValue(raw['effect_code']);
  String get label => stringValue(raw['label']);
  bool get isEnabled => boolValue(raw['is_enabled']);
  bool get approvalRequired => boolValue(raw['approval_required']);
  double get baseMagnitude => numberValue(raw['base_magnitude']);
  int get durationHours => intValue(raw['duration_hours']);
  int get priority => intValue(raw['priority']);
  bool get gameplayEnabled => boolValue(raw['gameplay_enabled']);
  bool get marketEnabled => boolValue(raw['market_enabled']);
  bool get recommendationEnabled => boolValue(raw['recommendation_enabled']);
  JsonMap get config =>
      jsonMap(raw['config_json'], fallback: const <String, Object?>{});
}

class EventIngestionJob {
  const EventIngestionJob._(this.raw);

  final JsonMap raw;

  factory EventIngestionJob.fromJson(Object? value) {
    return EventIngestionJob._(jsonMap(value, label: 'event ingestion job'));
  }

  String get id => stringValue(raw['id']);
  String get sourceType => stringValue(raw['source_type']);
  String get sourceLabel => stringValue(raw['source_label']);
  String get status => stringValue(raw['status']);
  int get totalReceived => intValue(raw['total_received']);
  int get processedCount => intValue(raw['processed_count']);
  int get successCount => intValue(raw['success_count']);
  int get failedCount => intValue(raw['failed_count']);
  int get pendingReviewCount => intValue(raw['pending_review_count']);
  String? get errorMessage => stringOrNullValue(raw['error_message']);
  JsonMap get summary =>
      jsonMap(raw['summary_json'], fallback: const <String, Object?>{});
}

class CalendarSeasonViewModel {
  const CalendarSeasonViewModel._(this.raw);

  final JsonMap raw;

  factory CalendarSeasonViewModel.fromJson(Object? value) {
    return CalendarSeasonViewModel._(jsonMap(value, label: 'calendar season'));
  }

  String get id => stringValue(raw['id']);
  String get seasonKey => stringValue(raw['season_key']);
  String get title => stringValue(raw['title']);
  String get startsOn => stringValue(raw['starts_on']);
  String get endsOn => stringValue(raw['ends_on']);
  String get status => stringValue(raw['status']);
  bool get active => boolValue(raw['active']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CalendarEventViewModel {
  const CalendarEventViewModel._(this.raw);

  final JsonMap raw;

  factory CalendarEventViewModel.fromJson(Object? value) {
    return CalendarEventViewModel._(jsonMap(value, label: 'calendar event'));
  }

  String get id => stringValue(raw['id']);
  String? get seasonId => stringOrNullValue(raw['season_id']);
  String get eventKey => stringValue(raw['event_key']);
  String get title => stringValue(raw['title']);
  String? get description => stringOrNullValue(raw['description']);
  String get sourceType => stringValue(raw['source_type']);
  String? get sourceId => stringOrNullValue(raw['source_id']);
  String get family => stringValue(raw['family']);
  String get ageBand => stringValue(raw['age_band']);
  String get startsOn => stringValue(raw['starts_on']);
  String get endsOn => stringValue(raw['ends_on']);
  bool get exclusiveWindows => boolValue(raw['exclusive_windows']);
  bool get pauseOtherGtxCompetitions =>
      boolValue(raw['pause_other_gtx_competitions']);
  String get visibility => stringValue(raw['visibility']);
  String get status => stringValue(raw['status']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CompetitionLifecycleRunViewModel {
  const CompetitionLifecycleRunViewModel._(this.raw);

  final JsonMap raw;

  factory CompetitionLifecycleRunViewModel.fromJson(Object? value) {
    return CompetitionLifecycleRunViewModel._(
      jsonMap(value, label: 'competition lifecycle run'),
    );
  }

  String get id => stringValue(raw['id']);
  String? get eventId => stringOrNullValue(raw['event_id']);
  String get sourceType => stringValue(raw['source_type']);
  String get sourceId => stringValue(raw['source_id']);
  String get sourceTitle => stringValue(raw['source_title']);
  String get competitionFormat => stringValue(raw['competition_format']);
  String get status => stringValue(raw['status']);
  String get stage => stringValue(raw['stage']);
  int get generatedRounds => intValue(raw['generated_rounds']);
  int get generatedMatches => intValue(raw['generated_matches']);
  List<String> get scheduledDates =>
      stringListValue(raw['scheduled_dates_json']);
  String? get summaryText => stringOrNullValue(raw['summary_text']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class PauseStatusViewModel {
  const PauseStatusViewModel._(this.raw);

  final JsonMap raw;

  factory PauseStatusViewModel.fromJson(Object? value) {
    return PauseStatusViewModel._(jsonMap(value, label: 'pause status'));
  }

  String get asOf => stringValue(raw['as_of']);
  List<String> get blockedCompetitionFamilies =>
      stringListValue(raw['blocked_competition_families']);
  List<String> get activeEventKeys => stringListValue(raw['active_event_keys']);
  String get summary => stringValue(raw['summary']);
}

class CalendarDashboard {
  const CalendarDashboard._(this.raw);

  final JsonMap raw;

  factory CalendarDashboard.fromJson(Object? value) {
    return CalendarDashboard._(jsonMap(value, label: 'calendar dashboard'));
  }

  List<CalendarSeasonViewModel> get seasons => parseList(
        raw['seasons'],
        CalendarSeasonViewModel.fromJson,
        label: 'calendar seasons',
      );
  List<CalendarEventViewModel> get activeEvents => parseList(
        raw['active_events'],
        CalendarEventViewModel.fromJson,
        label: 'calendar active events',
      );
  PauseStatusViewModel get activePauseStatus =>
      PauseStatusViewModel.fromJson(raw['active_pause_status']);
  List<CompetitionLifecycleRunViewModel> get recentLifecycleRuns => parseList(
        raw['recent_lifecycle_runs'],
        CompetitionLifecycleRunViewModel.fromJson,
        label: 'calendar lifecycle runs',
      );
}
