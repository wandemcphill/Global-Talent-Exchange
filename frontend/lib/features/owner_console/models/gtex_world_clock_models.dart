/// Typed models for the authoritative GTEX world clock and the owner daily briefing.
///
/// World clock contract: `GET /api/world/clock` (Global-Talent-Exchange PR #347). Game time is
/// only ever what the server returned; nothing here reads the device clock or runs timers.
///
/// Briefing: BLOCKED ON BACKEND CONTRACT. No persisted briefing/event endpoint is published yet
/// (PR #341 work packet A5, decision D7), so [kOwnerBriefingEndpoint] is null and the UI shows an
/// honest unavailable state. These types are the typed boundary a verified-event card needs.
library;

const String kWorldClockPath = '/api/world/clock';
const String? kOwnerBriefingEndpoint = null;

class WorldClockContractException implements Exception {
  const WorldClockContractException(this.message);
  final String message;
  @override
  String toString() => 'world_clock_contract_violation: $message';
}

final RegExp _isoDate = RegExp(r'^\d{4}-\d{2}-\d{2}$');
final RegExp _isoDateTimeWithOffset = RegExp(
  r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$',
);

const List<String> _months = <String>[
  'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
  'September', 'October', 'November', 'December',
];
const List<String> _weekdays = <String>['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

class WorldClock {
  const WorldClock({
    required this.clockId,
    required this.worldTime,
    required this.worldDate,
    required this.isPaused,
    required this.progressionRate,
    required this.virtualMonthsPerSeason,
  });

  /// Strictly validates the published schema; anything else is rejected rather than guessed.
  factory WorldClock.fromJson(Object? raw) {
    if (raw is! Map) {
      throw const WorldClockContractException('response is not an object');
    }
    final Map<Object?, Object?> r = raw;
    final Object? clockId = r['clock_id'];
    if (clockId is! String || clockId.trim().isEmpty) {
      throw const WorldClockContractException('clock_id missing');
    }
    final Object? time = r['world_time'];
    if (time is! String || !_isoDateTimeWithOffset.hasMatch(time)) {
      throw const WorldClockContractException(
        'world_time must be an ISO timestamp with an explicit UTC offset',
      );
    }
    final DateTime? instant = DateTime.tryParse(time)?.toUtc();
    if (instant == null) {
      throw const WorldClockContractException('world_time is not a valid instant');
    }
    final Object? date = r['world_date'];
    if (date is! String || !_isoDate.hasMatch(date)) {
      throw const WorldClockContractException('world_date must be YYYY-MM-DD');
    }
    if (instant.toIso8601String().substring(0, 10) != date) {
      throw const WorldClockContractException(
        'world_date does not match the UTC date of world_time',
      );
    }
    final Object? paused = r['is_paused'];
    if (paused is! bool) {
      throw const WorldClockContractException('is_paused must be a boolean');
    }
    final Object? rate = r['progression_rate'];
    if (rate is! num || !rate.isFinite || rate <= 0) {
      throw const WorldClockContractException('progression_rate must be a positive number');
    }
    final Object? months = r['virtual_months_per_season'];
    if (months is! num || months != months.truncate() || months < 1) {
      throw const WorldClockContractException(
        'virtual_months_per_season must be an integer >= 1',
      );
    }
    return WorldClock(
      clockId: clockId,
      worldTime: instant,
      worldDate: date,
      isPaused: paused,
      progressionRate: rate.toDouble(),
      virtualMonthsPerSeason: months.toInt(),
    );
  }

  final String clockId;

  /// Server-issued virtual instant (UTC).
  final DateTime worldTime;

  /// Server-issued virtual date, `YYYY-MM-DD`.
  final String worldDate;
  final bool isPaused;
  final double progressionRate;
  final int virtualMonthsPerSeason;

  /// e.g. `Fri, 14 March 2031`, derived from the server's date string only.
  String get displayDate {
    final List<int> p = worldDate.split('-').map(int.parse).toList();
    final DateTime d = DateTime.utc(p[0], p[1], p[2]);
    return '${_weekdays[d.weekday - 1]}, ${d.day} ${_months[d.month - 1]} ${d.year}';
  }

  /// e.g. `09:05 UTC`.
  String get displayTime {
    String two(int v) => v.toString().padLeft(2, '0');
    return '${two(worldTime.hour)}:${two(worldTime.minute)} UTC';
  }

  String get displayRate {
    final String t = progressionRate.toStringAsFixed(4).replaceFirst(RegExp(r'\.?0+$'), '');
    return '${t}x';
  }
}

enum BriefingTargetType { decision, clubHistory, matchResult }

class BriefingTarget {
  const BriefingTarget(this.type, this.id);
  final BriefingTargetType type;
  final String id;

  static BriefingTarget? tryParse(Object? raw) {
    if (raw is! Map) return null;
    String? text(Object? v) {
      final String t = '${v ?? ''}'.trim();
      return t.isEmpty ? null : t;
    }

    switch (raw['type']) {
      case 'decision':
        final String? id = text(raw['inbox_item_id']);
        return id == null ? null : BriefingTarget(BriefingTargetType.decision, id);
      case 'club_history':
        final String? id = text(raw['club_id']);
        return id == null ? null : BriefingTarget(BriefingTargetType.clubHistory, id);
      case 'match_result':
        final String? id = text(raw['match_id']);
        return id == null ? null : BriefingTarget(BriefingTargetType.matchResult, id);
    }
    return null;
  }

  /// Existing Flutter destinations: private decision inbox, public club profile, 2D match viewer.
  /// The inbox route is owned by the separate B2 inbox-routing work and is referenced only here.
  String get route {
    switch (type) {
      case BriefingTargetType.decision:
        return '/app/inbox';
      case BriefingTargetType.clubHistory:
        return '/clubs/${Uri.encodeComponent(id)}/profile';
      case BriefingTargetType.matchResult:
        return '/matches/viewer/${Uri.encodeComponent(id)}';
    }
  }

  String get label {
    switch (type) {
      case BriefingTargetType.decision:
        return 'Open decision';
      case BriefingTargetType.clubHistory:
        return 'View club history';
      case BriefingTargetType.matchResult:
        return 'View match result';
    }
  }
}

class BriefingEvent {
  const BriefingEvent({
    required this.eventId,
    required this.headline,
    required this.occurredAt,
    this.detail,
    this.target,
  });
  final String eventId;
  final String headline;
  final String occurredAt;
  final String? detail;
  final BriefingTarget? target;
}

class OwnerBriefing {
  const OwnerBriefing({
    required this.briefingId,
    required this.clubId,
    required this.worldDate,
    required this.events,
    this.rejectedEventCount = 0,
    this.explanation,
  });

  factory OwnerBriefing.fromJson(Object? raw) {
    String? text(Object? v) {
      final String t = '${v ?? ''}'.trim();
      return t.isEmpty || t == 'null' ? null : t;
    }

    if (raw is! Map) throw const FormatException('owner_briefing_contract_violation');
    final String? id = text(raw['briefing_id']);
    final String? club = text(raw['club_id']);
    final String? date = text(raw['world_date']);
    if (id == null || club == null || date == null) {
      throw const FormatException('owner_briefing_contract_violation');
    }
    final List<BriefingEvent> events = <BriefingEvent>[];
    int rejected = 0;
    for (final Object? e in (raw['events'] is List ? raw['events'] as List : const <Object?>[])) {
      final Map<Object?, Object?>? m = e is Map ? e : null;
      final String? eventId = text(m?['event_id']);
      final String? headline = text(m?['headline']);
      final String? at = text(m?['occurred_at']);
      if (eventId == null || headline == null || at == null) {
        rejected++;
        continue;
      }
      events.add(BriefingEvent(
        eventId: eventId,
        headline: headline,
        occurredAt: at,
        detail: text(m?['detail']),
        target: BriefingTarget.tryParse(m?['target']),
      ));
    }
    return OwnerBriefing(
      briefingId: id,
      clubId: club,
      worldDate: date,
      events: events,
      rejectedEventCount: rejected,
      explanation: text(raw['explanation']),
    );
  }

  final String briefingId;
  final String clubId;
  final String worldDate;
  final List<BriefingEvent> events;
  final int rejectedEventCount;

  /// Optional AI prose. Explanatory only; never the source of game facts.
  final String? explanation;
}

sealed class BriefingViewState {
  const BriefingViewState();
}

class BriefingLoading extends BriefingViewState {
  const BriefingLoading();
}

class BriefingUnavailable extends BriefingViewState {
  const BriefingUnavailable();
}

class BriefingError extends BriefingViewState {
  const BriefingError();
}

class BriefingEmpty extends BriefingViewState {
  const BriefingEmpty({this.worldDate});
  final String? worldDate;
}

class BriefingReady extends BriefingViewState {
  const BriefingReady(this.briefing, {this.stale = false});
  final OwnerBriefing briefing;
  final bool stale;
}
