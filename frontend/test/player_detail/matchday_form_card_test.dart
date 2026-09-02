import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/domain/value/gtex_value_models.dart';
import 'package:gte_frontend/features/player_detail/widgets/matchday_form_card.dart';
import 'package:gte_frontend/features/player_detail/widgets/ownership_consequence_card.dart';

/// These tests exist to defend the honesty rules, not the pixels.
///
/// The whole point of this feature is that a reader can trust what the page
/// says about the link between a footballer's performances and their own money.
/// A card that implies a causal link the backend has not made would be worse
/// than no card at all, so each rule gets a test.

Future<void> _pump(WidgetTester tester, Widget child) async {
  await tester.pumpWidget(
    MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child))),
  );
  await tester.pump();
}

GtexPlayerForm _form({
  bool hasSample = true,
  int matchesCounted = 6,
  int competitionsCounted = 3,
  double? averageRating = 8.2,
  String trend = 'rising',
  double trendDelta = 0.4,
  int excludedByCompetitionCap = 0,
  GtexMatchdaySignal? signal,
  List<GtexPlayerPerformance> performances = const <GtexPlayerPerformance>[],
}) {
  return GtexPlayerForm(
    playerId: 'p1',
    hasSample: hasSample,
    matchesCounted: matchesCounted,
    competitionsCounted: competitionsCounted,
    averageRating: averageRating,
    trend: trend,
    trendDelta: trendDelta,
    totalMinutes: 540,
    excludedByCompetitionCap: excludedByCompetitionCap,
    signal: signal,
    performances: performances,
  );
}

GtexMatchdaySignal _signal({
  bool applied = true,
  double adjustmentPct = 0.0121,
  int matchesCounted = 6,
  int minimumMatchesRequired = 3,
}) {
  return GtexMatchdaySignal(
    applied: applied,
    adjustmentPct: adjustmentPct,
    reasonCode: applied ? 'matchday_form_positive' : 'matchday_form_insufficient_sample',
    confidence: 1,
    matchesCounted: matchesCounted,
    competitionsCounted: 3,
    minimumMatchesRequired: minimumMatchesRequired,
    effectiveMaxAdjustmentPct: 0.024,
  );
}

void main() {
  group('MatchdayFormCard honesty', () {
    testWidgets('a player with no competition football says exactly that', (
      WidgetTester tester,
    ) async {
      await _pump(tester, MatchdayFormCard(form: _form(hasSample: false)));

      expect(find.textContaining('No GTEX competition football yet'), findsOneWidget);
      // It must not render a rating, which would read as "he played and was average".
      expect(find.textContaining('Form rating'), findsNothing);
    });

    testWidgets('form that is not yet counted says so and says what is missing', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        MatchdayFormCard(
          form: _form(
            matchesCounted: 1,
            signal: _signal(applied: false, adjustmentPct: 0, matchesCounted: 1),
          ),
        ),
      );

      expect(find.textContaining('Not affecting valuation yet'), findsOneWidget);
      expect(find.textContaining('2 more eligible matches'), findsOneWidget);
      expect(find.textContaining('One strong match does not move a price'), findsOneWidget);
    });

    testWidgets('form with no signal at all never claims an effect', (
      WidgetTester tester,
    ) async {
      await _pump(tester, MatchdayFormCard(form: _form(signal: null)));

      expect(find.textContaining('Not affecting valuation'), findsOneWidget);
      expect(find.textContaining('Raising valuation'), findsNothing);
    });

    testWidgets('an applied signal states the real bounded figure', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        MatchdayFormCard(form: _form(signal: _signal(adjustmentPct: 0.0121))),
      );

      expect(find.textContaining('Raising valuation by +1.21%'), findsOneWidget);
      // And it discloses the cap, so the reader knows the ceiling.
      expect(find.textContaining('capped at ±2.4%'), findsOneWidget);
    });

    testWidgets('a negative signal reads as lowering, not raising', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        MatchdayFormCard(form: _form(signal: _signal(adjustmentPct: -0.0090))),
      );

      expect(find.textContaining('Lowering valuation by -0.90%'), findsOneWidget);
    });

    testWidgets('the anti-farming cap is disclosed rather than hidden', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        MatchdayFormCard(
          form: _form(excludedByCompetitionCap: 3, signal: _signal()),
        ),
      );

      expect(
        find.textContaining('no single competition may fill it'),
        findsOneWidget,
      );
    });

    testWidgets('an ineligible performance is shown, not hidden', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        MatchdayFormCard(
          form: _form(
            signal: _signal(),
            performances: <GtexPlayerPerformance>[
              const GtexPlayerPerformance(
                matchId: 'm1',
                competitionId: 'c1',
                occurredAt: null,
                rating: 7.8,
              ),
              const GtexPlayerPerformance(
                matchId: 'm2',
                competitionId: 'c1',
                occurredAt: null,
                rating: 6.1,
                minutesPlayed: 4,
                eligibleForValuation: false,
                ineligibilityReason: 'insufficient_minutes',
              ),
            ],
          ),
        ),
      );

      expect(find.text('7.8'), findsOneWidget);
      expect(find.text('6.1'), findsOneWidget);
    });

    testWidgets('a rising trajectory is labelled as such', (
      WidgetTester tester,
    ) async {
      await _pump(tester, MatchdayFormCard(form: _form(signal: _signal())));

      expect(find.textContaining('Rising'), findsOneWidget);
    });
  });

  group('OwnershipConsequenceCard honesty', () {
    const GtePortfolioHolding holding = GtePortfolioHolding(
      playerId: 'p1',
      quantity: 25,
      averageCost: 100,
      currentPrice: 112,
      marketValue: 2800,
      unrealizedPl: 300,
      unrealizedPlPercent: 12,
    );

    testWidgets('no position reads as no position', (WidgetTester tester) async {
      await _pump(tester, const OwnershipConsequenceCard(holding: null));

      expect(find.textContaining('You hold no shares'), findsOneWidget);
      expect(
        find.textContaining('it does not move your portfolio'),
        findsOneWidget,
      );
    });

    testWidgets('a real position shows the real numbers', (
      WidgetTester tester,
    ) async {
      await _pump(tester, const OwnershipConsequenceCard(holding: holding));

      expect(find.text('25'), findsOneWidget);
      expect(find.textContaining('+300 cr'), findsOneWidget);
    });

    testWidgets('the form-to-position link only appears when form drives value', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        OwnershipConsequenceCard(
          holding: holding,
          form: _form(signal: _signal(applied: false, adjustmentPct: 0)),
        ),
      );

      expect(find.textContaining('therefore to your position'), findsNothing);
    });

    testWidgets('the form-to-position link appears when form does drive value', (
      WidgetTester tester,
    ) async {
      await _pump(
        tester,
        OwnershipConsequenceCard(
          holding: holding,
          form: _form(signal: _signal(adjustmentPct: 0.0121)),
        ),
      );

      expect(find.textContaining('therefore to your position'), findsOneWidget);
      expect(find.textContaining('+1.21%'), findsOneWidget);
    });
  });
}
