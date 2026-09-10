import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/domain/value/gtex_value_models.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_post_match_panel.dart';
import 'package:gte_frontend/features/player_detail/widgets/matchday_form_card.dart';
import 'package:gte_frontend/features/player_detail/widgets/ownership_consequence_card.dart';

void main() {
  group('GTEX Phase 5E - Owner Decision Loop Tests', () {
    testWidgets('GtexPostMatchPanel renders Owner Decision Loop CTAs at Full Time', (WidgetTester tester) async {
      bool portfolioOpened = false;
      bool marketOpened = false;

      const match = GtexLiveMatchState(
        matchId: 'match-5e-test',
        home: GtexMatchTeam(
          id: 'home-club',
          name: 'Home FC',
          shortName: 'HFC',
          score: 2,
          formation: '4-3-3',
          players: [],
        ),
        away: GtexMatchTeam(
          id: 'away-club',
          name: 'Away FC',
          shortName: 'AFC',
          score: 1,
          formation: '4-2-3-1',
          players: [],
        ),
        minute: 90,
        phase: GtexMatchPhase.fullTime,
        pitchPlayers: [],
        timeline: [],
        stats: GtexMatchStats(
          homePossession: 55,
          awayPossession: 45,
          homeShots: 10,
          awayShots: 6,
          homeShotsOnTarget: 5,
          awayShotsOnTarget: 3,
          homePassAccuracy: 88,
          awayPassAccuracy: 82,
          homeExpectedGoals: 2.1,
          awayExpectedGoals: 1.2,
        ),
        highlights: [],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GtexPostMatchPanel(
              match: match,
              onOpenPortfolio: () => portfolioOpened = true,
              onOpenMarket: () => marketOpened = true,
            ),
          ),
        ),
      );

      expect(find.text('MATCHDAY → OWNER DECISION LOOP'), findsOneWidget);
      expect(
        find.textContaining('Performance in this fixture has updated published player valuations'),
        findsOneWidget,
      );

      final portfolioBtn = find.byKey(const Key('gtex-post-match-portfolio-btn'));
      final marketBtn = find.byKey(const Key('gtex-post-match-market-btn'));

      expect(portfolioBtn, findsOneWidget);
      expect(marketBtn, findsOneWidget);

      await tester.tap(portfolioBtn);
      await tester.pump();
      expect(portfolioOpened, isTrue);

      await tester.tap(marketBtn);
      await tester.pump();
      expect(marketOpened, isTrue);
    });

    testWidgets('OwnershipConsequenceCard renders Portfolio CTA and PRICE != VALUE note', (WidgetTester tester) async {
      bool portfolioOpened = false;

      const holding = GtePortfolioHolding(
        playerId: 'p1',
        quantity: 10,
        averageCost: 100,
        currentPrice: 120,
        marketValue: 1200,
        unrealizedPl: 200,
        unrealizedPlPercent: 20.0,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: OwnershipConsequenceCard(
              holding: holding,
              onOpenPortfolio: () => portfolioOpened = true,
            ),
          ),
        ),
      );

      final btn = find.byKey(const Key('gtex-ownership-review-portfolio-btn'));
      expect(btn, findsOneWidget);

      await tester.tap(btn);
      await tester.pump();
      expect(portfolioOpened, isTrue);
    });

    testWidgets('MatchdayFormCard renders Matchday CTA', (WidgetTester tester) async {
      bool matchdayOpened = false;

      final form = GtexPlayerForm(
        playerId: 'p1',
        hasSample: true,
        matchesCounted: 3,
        competitionsCounted: 1,
        totalMinutes: 270,
        totalGoals: 2,
        totalAssists: 1,
        performances: [
          GtexPlayerPerformance(
            matchId: 'm1',
            competitionId: 'c1',
            occurredAt: DateTime(2026, 3, 22),
            rating: 7.8,
            minutesPlayed: 90,
            goals: 1,
            assists: 0,
            eligibleForValuation: true,
          ),
        ],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MatchdayFormCard(
              form: form,
              onOpenMatchday: () => matchdayOpened = true,
            ),
          ),
        ),
      );

      final btn = find.byKey(const Key('gtex-form-open-matchday-btn'));
      expect(btn, findsOneWidget);

      await tester.tap(btn);
      await tester.pump();
      expect(matchdayOpened, isTrue);
    });
  });
}
