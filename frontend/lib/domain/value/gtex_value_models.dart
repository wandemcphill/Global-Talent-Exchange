import 'package:flutter/foundation.dart';

/// A footballer's recent GTEX competition form, and the bounded effect that form
/// currently has on his valuation.
///
/// The honesty rules for this model, which the UI must respect:
///
///   * [hasSample] false means the player has no eligible GTEX competition
///     football. The interface must say so, not render a neutral-looking
///     trajectory that implies he has been playing.
///   * [signal] null, or [GtexMatchdaySignal.applied] false, means form exists but
///     is *not* moving this player's value. The interface must not imply a causal
///     link that the backend has not made.
@immutable
class GtexPlayerForm {
  const GtexPlayerForm({
    required this.playerId,
    this.hasSample = false,
    this.matchesCounted = 0,
    this.competitionsCounted = 0,
    this.averageRating,
    this.trend = 'steady',
    this.trendDelta = 0,
    this.totalMinutes = 0,
    this.totalGoals = 0,
    this.totalAssists = 0,
    this.excludedByCompetitionCap = 0,
    this.signal,
    this.performances = const <GtexPlayerPerformance>[],
  });

  /// The honest empty state, used when form could not be loaded. It reports no
  /// sample rather than inventing one.
  factory GtexPlayerForm.unknown(String playerId) =>
      GtexPlayerForm(playerId: playerId);

  factory GtexPlayerForm.fromJson(Map<String, dynamic> json) {
    final Object? rawSignal = json['signal'];
    final Object? rawPerformances = json['performances'];
    return GtexPlayerForm(
      playerId: (json['player_id'] as Object?)?.toString() ?? '',
      hasSample: json['has_sample'] == true,
      matchesCounted: _int(json['matches_counted']),
      competitionsCounted: _int(json['competitions_counted']),
      averageRating: _doubleOrNull(json['average_rating']),
      trend: (json['trend'] as Object?)?.toString() ?? 'steady',
      trendDelta: _double(json['trend_delta']),
      totalMinutes: _int(json['total_minutes']),
      totalGoals: _int(json['total_goals']),
      totalAssists: _int(json['total_assists']),
      excludedByCompetitionCap: _int(json['excluded_by_competition_cap']),
      signal:
          rawSignal is Map<String, dynamic>
              ? GtexMatchdaySignal.fromJson(rawSignal)
              : null,
      performances:
          rawPerformances is List
              ? rawPerformances
                  .whereType<Map<String, dynamic>>()
                  .map(GtexPlayerPerformance.fromJson)
                  .toList(growable: false)
              : const <GtexPlayerPerformance>[],
    );
  }

  final String playerId;
  final bool hasSample;
  final int matchesCounted;
  final int competitionsCounted;
  final double? averageRating;
  final String trend;
  final double trendDelta;
  final int totalMinutes;
  final int totalGoals;
  final int totalAssists;

  /// Performances dropped from the window because no single competition may
  /// dominate it. Surfaced rather than hidden so the anti-farming rule is
  /// visible to the person whose player it throttles.
  final int excludedByCompetitionCap;

  final GtexMatchdaySignal? signal;
  final List<GtexPlayerPerformance> performances;

  bool get isRising => trend == 'rising';
  bool get isFalling => trend == 'falling';

  /// True only when the backend is actually moving this player's value from his
  /// form. Anything else and the UI must not claim causality.
  bool get movesValuation =>
      signal?.applied == true && signal?.adjustmentPct != 0;
}

/// The bounded valuation influence a player's competition form carries.
@immutable
class GtexMatchdaySignal {
  const GtexMatchdaySignal({
    required this.applied,
    required this.adjustmentPct,
    required this.reasonCode,
    this.confidence = 0,
    this.capped = false,
    this.matchesCounted = 0,
    this.competitionsCounted = 0,
    this.minimumMatchesRequired = 0,
    this.effectiveMaxAdjustmentPct = 0,
  });

  factory GtexMatchdaySignal.fromJson(Map<String, dynamic> json) {
    return GtexMatchdaySignal(
      applied: json['applied'] == true,
      adjustmentPct: _double(json['adjustment_pct']),
      reasonCode: (json['reason_code'] as Object?)?.toString() ?? '',
      confidence: _double(json['confidence']),
      capped: json['capped'] == true,
      matchesCounted: _int(json['matches_counted']),
      competitionsCounted: _int(json['competitions_counted']),
      minimumMatchesRequired: _int(json['minimum_matches_required']),
      effectiveMaxAdjustmentPct: _double(json['effective_max_adjustment_pct']),
    );
  }

  final bool applied;
  final double adjustmentPct;
  final String reasonCode;
  final double confidence;
  final bool capped;
  final int matchesCounted;
  final int competitionsCounted;
  final int minimumMatchesRequired;
  final double effectiveMaxAdjustmentPct;

  /// How many more eligible matches are needed before form counts at all.
  int get matchesRemaining {
    final int remaining = minimumMatchesRequired - matchesCounted;
    return remaining > 0 ? remaining : 0;
  }
}

/// One persisted competition performance.
@immutable
class GtexPlayerPerformance {
  const GtexPlayerPerformance({
    required this.matchId,
    required this.competitionId,
    required this.occurredAt,
    required this.rating,
    this.minutesPlayed = 0,
    this.goals = 0,
    this.assists = 0,
    this.started = false,
    this.eligibleForValuation = true,
    this.ineligibilityReason,
  });

  factory GtexPlayerPerformance.fromJson(Map<String, dynamic> json) {
    return GtexPlayerPerformance(
      matchId: (json['match_id'] as Object?)?.toString() ?? '',
      competitionId: (json['competition_id'] as Object?)?.toString() ?? '',
      occurredAt:
          DateTime.tryParse(
            (json['occurred_at'] as Object?)?.toString() ?? '',
          )?.toLocal(),
      rating: _double(json['rating']),
      minutesPlayed: _int(json['minutes_played']),
      goals: _int(json['goals']),
      assists: _int(json['assists']),
      started: json['started'] == true,
      eligibleForValuation: json['eligible_for_valuation'] != false,
      ineligibilityReason:
          (json['ineligibility_reason'] as Object?)?.toString(),
    );
  }

  final String matchId;
  final String competitionId;
  final DateTime? occurredAt;
  final double rating;
  final int minutesPlayed;
  final int goals;
  final int assists;
  final bool started;
  final bool eligibleForValuation;
  final String? ineligibilityReason;
}

int _int(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _double(Object? value) => _doubleOrNull(value) ?? 0;

double? _doubleOrNull(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '');
}

/// Whether the published valuation has caught up with the football on this page.
///
/// GTEX recalculates valuations on a schedule, not per match: performances are
/// persisted the moment a competition match settles, but the number a holder
/// sees only moves when the value snapshot job next runs. Between those two
/// instants the form card can truthfully show a signal that the published
/// valuation does not yet contain, and saying nothing about it would let the
/// page imply an effect that has not been applied.
enum GtexValuationFreshness {
  /// Every eligible performance on this page predates the last recalculation,
  /// so the published valuation already accounts for them.
  updated,

  /// At least one eligible performance postdates the last recalculation. Its
  /// effect is real but not yet published.
  pending,

  /// No recalculation is on record for this player, so no claim can be made in
  /// either direction.
  unknown,
}

/// The freshness of a player's published valuation relative to his form.
///
/// Derived entirely from data the page already holds -- the valuation's own
/// `lastSnapshotAt` and the performance timestamps returned with form -- so
/// stating it costs no extra request and invents no timestamp.
@immutable
class GtexValuationFreshnessReport {
  const GtexValuationFreshnessReport({
    required this.state,
    this.lastSnapshotAt,
    this.pendingMatchCount = 0,
  });

  /// Only *eligible* performances can count as pending: an ineligible cameo
  /// will never move a valuation however long it waits, so treating one as
  /// unpublished work would promise a change that is never coming.
  factory GtexValuationFreshnessReport.from({
    required DateTime? lastSnapshotAt,
    required List<GtexPlayerPerformance> performances,
  }) {
    if (lastSnapshotAt == null) {
      return const GtexValuationFreshnessReport(
        state: GtexValuationFreshness.unknown,
      );
    }
    final DateTime boundary = lastSnapshotAt.toUtc();
    final int pending =
        performances
            .where(
              (GtexPlayerPerformance performance) =>
                  performance.eligibleForValuation &&
                  performance.occurredAt != null &&
                  performance.occurredAt!.toUtc().isAfter(boundary),
            )
            .length;
    return GtexValuationFreshnessReport(
      state:
          pending > 0
              ? GtexValuationFreshness.pending
              : GtexValuationFreshness.updated,
      lastSnapshotAt: lastSnapshotAt,
      pendingMatchCount: pending,
    );
  }

  final GtexValuationFreshness state;
  final DateTime? lastSnapshotAt;
  final int pendingMatchCount;

  bool get isPending => state == GtexValuationFreshness.pending;
}
