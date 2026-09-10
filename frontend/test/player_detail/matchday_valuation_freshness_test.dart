import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/domain/value/gtex_value_models.dart';
import 'package:gte_frontend/features/player_detail/widgets/matchday_form_card.dart';

/// GTEX recalculates valuations on a schedule, not per match.
///
/// That gap is the one thing this page could most easily lie about: the form
/// signal is derived live from the performance window, so the card can show a
/// real, applied adjustment minutes after a match while the published valuation
/// a holder is actually priced against still predates it. Saying "raising
/// valuation by +1.2%" with no timing would be a claim about a number that has
/// not moved yet.
///
/// These tests pin the timing language to the data, in both directions: it must
/// appear when there is genuinely unpublished football, it must not appear when
/// there is not, and it must never be manufactured out of a missing timestamp.

final DateTime _snapshotAt = DateTime.utc(2026, 9, 2, 4);

GtexPlayerPerformance _performance({
  required String matchId,
  required DateTime occurredAt,
  bool eligible = true,
}) {
  return GtexPlayerPerformance(
    matchId: matchId,
    competitionId: 'comp-1',
    occurredAt: occurredAt,
    rating: 8.1,
    minutesPlayed: 90,
    started: true,
    eligibleForValuation: eligible,
  );
}

GtexPlayerForm _form({
  List<GtexPlayerPerformance> performances = const <GtexPlayerPerformance>[],
}) {
  return GtexPlayerForm(
    playerId: 'p1',
    hasSample: true,
    matchesCounted: 6,
    competitionsCounted: 3,
    averageRating: 8.2,
    trend: 'rising',
    trendDelta: 0.4,
    totalMinutes: 540,
    signal: const GtexMatchdaySignal(
      applied: true,
      adjustmentPct: 0.0121,
      reasonCode: 'matchday_form_positive',
      confidence: 1,
      matchesCounted: 6,
      competitionsCounted: 3,
      minimumMatchesRequired: 3,
      effectiveMaxAdjustmentPct: 0.024,
    ),
    performances: performances,
  );
}

Future<void> _pump(WidgetTester tester, Widget child) async {
  await tester.pumpWidget(
    MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child))),
  );
  await tester.pump();
}

void main() {
  group('GtexValuationFreshnessReport', () {
    test('no recalculation on record makes no claim in either direction', () {
      final GtexValuationFreshnessReport report =
          GtexValuationFreshnessReport.from(
            lastSnapshotAt: null,
            performances: <GtexPlayerPerformance>[
              _performance(
                matchId: 'm1',
                occurredAt: DateTime.utc(2026, 9, 1, 15),
              ),
            ],
          );

      expect(report.state, GtexValuationFreshness.unknown);
      expect(report.isPending, isFalse);
      expect(report.pendingMatchCount, 0);
    });

    test('football played since the last recalculation reads as pending', () {
      final GtexValuationFreshnessReport report =
          GtexValuationFreshnessReport.from(
            lastSnapshotAt: _snapshotAt,
            performances: <GtexPlayerPerformance>[
              _performance(
                matchId: 'after-1',
                occurredAt: DateTime.utc(2026, 9, 3, 15),
              ),
              _performance(
                matchId: 'after-2',
                occurredAt: DateTime.utc(2026, 9, 4, 15),
              ),
              _performance(
                matchId: 'before',
                occurredAt: DateTime.utc(2026, 9, 1, 15),
              ),
            ],
          );

      expect(report.state, GtexValuationFreshness.pending);
      expect(report.pendingMatchCount, 2);
    });

    test('football already inside the last recalculation reads as updated', () {
      final GtexValuationFreshnessReport report =
          GtexValuationFreshnessReport.from(
            lastSnapshotAt: _snapshotAt,
            performances: <GtexPlayerPerformance>[
              _performance(
                matchId: 'before',
                occurredAt: DateTime.utc(2026, 9, 1, 15),
              ),
            ],
          );

      expect(report.state, GtexValuationFreshness.updated);
      expect(report.pendingMatchCount, 0);
    });

    test('an ineligible cameo is never counted as unpublished work', () {
      // An ineligible performance will not move the valuation however long it
      // waits, so calling it pending would promise a change that never comes.
      final GtexValuationFreshnessReport report =
          GtexValuationFreshnessReport.from(
            lastSnapshotAt: _snapshotAt,
            performances: <GtexPlayerPerformance>[
              _performance(
                matchId: 'cameo',
                occurredAt: DateTime.utc(2026, 9, 3, 15),
                eligible: false,
              ),
            ],
          );

      expect(report.state, GtexValuationFreshness.updated);
      expect(report.pendingMatchCount, 0);
    });

    test('a performance with no timestamp cannot make anything pending', () {
      final GtexValuationFreshnessReport report =
          GtexValuationFreshnessReport.from(
            lastSnapshotAt: _snapshotAt,
            performances: const <GtexPlayerPerformance>[
              GtexPlayerPerformance(
                matchId: 'undated',
                competitionId: 'comp-1',
                occurredAt: null,
                rating: 8.1,
              ),
            ],
          );

      expect(report.state, GtexValuationFreshness.updated);
    });
  });

  group('MatchdayFormCard valuation timing', () {
    testWidgets(
      'unpublished football is disclosed, not implied to be applied',
      (WidgetTester tester) async {
        await _pump(
          tester,
          MatchdayFormCard(
            form: _form(),
            freshness: GtexValuationFreshnessReport(
              state: GtexValuationFreshness.pending,
              lastSnapshotAt: _snapshotAt,
              pendingMatchCount: 2,
            ),
          ),
        );

        expect(
          find.textContaining('the published valuation does not'),
          findsOneWidget,
        );
        expect(find.textContaining('2 eligible matches'), findsOneWidget);
      },
    );

    testWidgets('a caught-up valuation says so rather than staying silent', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        MatchdayFormCard(
          form: _form(),
          freshness: GtexValuationFreshnessReport(
            state: GtexValuationFreshness.updated,
            lastSnapshotAt: _snapshotAt,
          ),
        ),
      );

      expect(
        find.textContaining('already accounts for every eligible match'),
        findsOneWidget,
      );
      expect(find.textContaining('2026-09-02 04:00 UTC'), findsOneWidget);
    });

    testWidgets(
      'a player with no recalculation on record is told exactly that',
      (WidgetTester tester) async {
        await _pump(
          tester,
          MatchdayFormCard(
            form: _form(),
            freshness: GtexValuationFreshnessReport(
              state: GtexValuationFreshness.unknown,
            ),
          ),
        );

        expect(
          find.textContaining('No valuation recalculation is on record'),
          findsOneWidget,
        );
      },
    );

    testWidgets('a caller with no valuation to compare makes no timing claim', (
      WidgetTester tester,
    ) async {
      await _pump(tester, MatchdayFormCard(form: _form()));

      expect(find.textContaining('recalculated'), findsNothing);
      expect(find.textContaining('recalculation'), findsNothing);
    });
  });
}
