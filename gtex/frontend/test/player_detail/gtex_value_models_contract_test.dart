import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/domain/value/gtex_value_models.dart';

/// Audit point 11: the API response and the Flutter model must agree on
/// nullability and semantics.
///
/// The Dart side is deliberately equal-or-more permissive than the Pydantic
/// schema at every field — it tolerates absence where the API guarantees a
/// value, never the reverse. That is the safe direction: a backend that starts
/// omitting a field degrades to a sane default instead of throwing in front of
/// a holder who is trying to read what their player is worth.
///
/// Payloads below mirror `backend/app/players/form_schemas.py` exactly.
void main() {
  group('PlayerFormView contract', () {
    test('a full payload parses with every field carried through', () {
      final GtexPlayerForm form = GtexPlayerForm.fromJson(<String, dynamic>{
        'player_id': 'p1',
        'has_sample': true,
        'matches_counted': 6,
        'competitions_counted': 3,
        'average_rating': 8.217,
        'trend': 'rising',
        'trend_delta': 0.42,
        'total_minutes': 540,
        'total_goals': 4,
        'total_assists': 2,
        'excluded_by_competition_cap': 3,
        'signal': <String, dynamic>{
          'applied': true,
          'adjustment_pct': 0.0121,
          'reason_code': 'matchday_form_positive',
          'confidence': 1.0,
          'capped': false,
          'matches_counted': 6,
          'competitions_counted': 3,
          'minimum_matches_required': 3,
          'effective_max_adjustment_pct': 0.024,
        },
        'performances': <dynamic>[
          <String, dynamic>{
            'match_id': 'm1',
            'competition_id': 'c1',
            'club_id': 'club-home',
            'occurred_at': '2026-09-01T15:00:00+00:00',
            'rating': 8.4,
            'started': true,
            'minutes_played': 90,
            'goals': 1,
            'assists': 0,
            'saves': 0,
            'key_passes': 2,
            'tackles_won': 1,
            'interceptions': 0,
            'yellow_cards': 0,
            'red_card': false,
            'eligible_for_valuation': true,
            'ineligibility_reason': null,
          },
        ],
      });

      expect(form.playerId, 'p1');
      expect(form.hasSample, isTrue);
      expect(form.matchesCounted, 6);
      expect(form.averageRating, 8.217);
      expect(form.isRising, isTrue);
      expect(form.excludedByCompetitionCap, 3);
      expect(form.signal?.applied, isTrue);
      expect(form.signal?.adjustmentPct, 0.0121);
      expect(form.signal?.effectiveMaxAdjustmentPct, 0.024);
      expect(form.movesValuation, isTrue);
      expect(form.performances.single.rating, 8.4);
      expect(form.performances.single.occurredAt, isNotNull);
    });

    test('the documented nullable fields parse as null, not as zero', () {
      final GtexPlayerForm form = GtexPlayerForm.fromJson(<String, dynamic>{
        'player_id': 'p1',
        'has_sample': false,
        'matches_counted': 0,
        'competitions_counted': 0,
        'average_rating': null,
        'trend': 'steady',
        'trend_delta': 0.0,
        'total_minutes': 0,
        'total_goals': 0,
        'total_assists': 0,
        'excluded_by_competition_cap': 0,
        'signal': null,
        'performances': <dynamic>[],
      });

      // A player with no football must not read as a 0.0 rating.
      expect(form.averageRating, isNull);
      expect(form.signal, isNull);
      expect(form.hasSample, isFalse);
      expect(form.movesValuation, isFalse);
    });

    test('an unapplied signal never reports as moving valuation', () {
      final GtexPlayerForm form = GtexPlayerForm.fromJson(<String, dynamic>{
        'player_id': 'p1',
        'has_sample': true,
        'matches_counted': 1,
        'signal': <String, dynamic>{
          'applied': false,
          'adjustment_pct': 0.0,
          'reason_code': 'matchday_form_insufficient_sample',
          'minimum_matches_required': 3,
          'matches_counted': 1,
        },
      });

      expect(form.signal?.applied, isFalse);
      expect(form.movesValuation, isFalse);
      expect(form.signal?.matchesRemaining, 2);
    });

    test('an applied but zero-adjustment signal does not claim movement', () {
      final GtexPlayerForm form = GtexPlayerForm.fromJson(<String, dynamic>{
        'player_id': 'p1',
        'has_sample': true,
        'signal': <String, dynamic>{
          'applied': true,
          'adjustment_pct': 0.0,
          'reason_code': 'matchday_form_neutral',
        },
      });

      expect(form.signal?.applied, isTrue);
      expect(form.movesValuation, isFalse);
    });

    test('a truncated payload degrades to safe defaults rather than throwing', () {
      final GtexPlayerForm form = GtexPlayerForm.fromJson(<String, dynamic>{
        'player_id': 'p1',
      });

      expect(form.hasSample, isFalse);
      expect(form.matchesCounted, 0);
      expect(form.averageRating, isNull);
      expect(form.trend, 'steady');
      expect(form.performances, isEmpty);
      expect(form.movesValuation, isFalse);
    });

    test('matchesRemaining never goes negative', () {
      const GtexMatchdaySignal signal = GtexMatchdaySignal(
        applied: true,
        adjustmentPct: 0.01,
        reasonCode: 'matchday_form_positive',
        matchesCounted: 6,
        minimumMatchesRequired: 3,
      );

      expect(signal.matchesRemaining, 0);
    });

    test('the unknown factory is an honest empty, not a zeroed form', () {
      final GtexPlayerForm form = GtexPlayerForm.unknown('p1');

      expect(form.playerId, 'p1');
      expect(form.hasSample, isFalse);
      expect(form.averageRating, isNull);
      expect(form.signal, isNull);
      expect(form.movesValuation, isFalse);
    });

    test('an ineligible performance carries its reason through', () {
      final GtexPlayerPerformance performance = GtexPlayerPerformance.fromJson(
        <String, dynamic>{
          'match_id': 'm2',
          'competition_id': 'c1',
          'occurred_at': '2026-09-01T15:00:00+00:00',
          'rating': 6.1,
          'minutes_played': 4,
          'eligible_for_valuation': false,
          'ineligibility_reason': 'insufficient_minutes',
        },
      );

      expect(performance.eligibleForValuation, isFalse);
      expect(performance.ineligibilityReason, 'insufficient_minutes');
    });

    test('integer fields sent as JSON numbers still parse', () {
      final GtexPlayerForm form = GtexPlayerForm.fromJson(<String, dynamic>{
        'player_id': 'p1',
        'has_sample': true,
        'matches_counted': 6.0,
        'total_minutes': 540.0,
      });

      expect(form.matchesCounted, 6);
      expect(form.totalMinutes, 540);
    });
  });
}
