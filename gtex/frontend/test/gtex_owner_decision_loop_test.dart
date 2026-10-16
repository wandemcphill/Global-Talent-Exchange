import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/domain/value/gtex_value_models.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/home/data/gtex_home_digest_provider.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/home/models/gtex_home_digest_models.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_post_match_panel.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/features/player_detail/widgets/matchday_form_card.dart';
import 'package:gte_frontend/features/player_detail/widgets/ownership_consequence_card.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  group('GTEX Phase 5E - Owner Decision Loop Tests', () {
    testWidgets('owned affected player: surfaces real holding context and Portfolio CTA', (WidgetTester tester) async {
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

      final form = GtexPlayerForm(
        playerId: 'p1',
        hasSample: true,
        matchesCounted: 3,
        competitionsCounted: 1,
        totalMinutes: 270,
        totalGoals: 2,
        totalAssists: 1,
        signal: const GtexMatchdaySignal(
          applied: true,
          adjustmentPct: 0.05,
          reasonCode: 'strong_form',
        ),
        performances: [],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: OwnershipConsequenceCard(
              holding: holding,
              form: form,
              onOpenPortfolio: () => portfolioOpened = true,
            ),
          ),
        ),
      );

      // Asserts real holding context
      expect(find.text('Shares held'), findsOneWidget);
      expect(find.text('10'), findsOneWidget);
      expect(find.text('Position market value'), findsOneWidget);
      expect(find.textContaining('1200 cr'), findsOneWidget);

      // Asserts valuation note keeps PRICE != VALUE distinction
      expect(
        find.textContaining('adding +5.00% to his published player valuation'),
        findsOneWidget,
      );
      expect(
        find.textContaining('tradable share price is unchanged'),
        findsOneWidget,
      );

      // Asserts Portfolio CTA
      final btn = find.byKey(const Key('gtex-ownership-review-portfolio-btn'));
      expect(btn, findsOneWidget);

      await tester.tap(btn);
      await tester.pump();
      expect(portfolioOpened, isTrue);
    });

    testWidgets('affected player not owned: surfaces player/market context and Market CTA without portfolio pretence', (WidgetTester tester) async {
      bool marketOpened = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: OwnershipConsequenceCard(
              holding: null,
              onOpenMarket: () => marketOpened = true,
            ),
          ),
        ),
      );

      // Asserts truthful non-ownership copy
      expect(find.text('You hold no shares in this player'), findsOneWidget);
      expect(
        find.textContaining('does not move your portfolio'),
        findsOneWidget,
      );

      // Asserts Market CTA instead of Portfolio CTA
      expect(find.byKey(const Key('gtex-ownership-review-portfolio-btn')), findsNothing);
      final btn = find.byKey(const Key('gtex-ownership-explore-market-btn'));
      expect(btn, findsOneWidget);

      await tester.tap(btn);
      await tester.pump();
      expect(marketOpened, isTrue);
    });

    testWidgets('no player ID: activity item with no player ID or route location is non-tappable and does not open Wallet', (WidgetTester tester) async {
      const activityWithoutId = GtexHomeActivityItem(
        id: 'act-1',
        label: 'System Maintenance Event',
        timestampLabel: '2 mins ago',
        playerId: null,
        routeLocation: null,
      );

      final digest = GtexHomeDigest(
        userState: GtexHomeUserState.playerOwner,
        headline: 'Welcome back',
        ownedPlayers: [],
        yourMoversToday: [],
        opportunityMovers: [],
        clubs: [],
        regens: [],
        attentionItems: [],
        recentActivity: [activityWithoutId],
        warnings: [],
      );

      final GoRouter router = GoRouter(
        initialLocation: '/home',
        routes: [
          GoRoute(
            path: '/home',
            builder: (context, state) => Scaffold(
              body: HomeRecentActivityPanel(
                digestValue: AsyncValue.data(digest),
              ),
            ),
          ),
          GoRoute(
            path: '/app/wallet',
            builder: (context, state) => const Scaffold(
              body: Text('WALLET SCREEN'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(MaterialApp.router(routerConfig: router));
      await tester.pumpAndSettle();

      expect(find.text('System Maintenance Event'), findsOneWidget);
      // No open-in-new icon or button semantics for items without domain evidence
      expect(find.byIcon(Icons.open_in_new), findsNothing);

      await tester.tap(find.text('System Maintenance Event'));
      await tester.pumpAndSettle();

      // Wallet screen was NOT opened
      expect(find.text('WALLET SCREEN'), findsNothing);
    });

    testWidgets('full-time decision panel: GtexPostMatchPanel renders decision loop with Portfolio and Market CTAs at FT', (WidgetTester tester) async {
      bool portfolioOpened = false;
      bool marketOpened = false;

      const match = GtexLiveMatchState(
        matchId: 'match-ft-test',
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

    testWidgets('Player Detail -> Portfolio: navigating via OwnershipConsequenceCard CTA opens /app/portfolio', (WidgetTester tester) async {
      String? navigatedLocation;

      final GoRouter router = GoRouter(
        initialLocation: '/player/p1',
        routes: [
          GoRoute(
            path: '/player/:id',
            builder: (context, state) => Scaffold(
              body: OwnershipConsequenceCard(
                holding: const GtePortfolioHolding(
                  playerId: 'p1',
                  quantity: 5,
                  averageCost: 50,
                  currentPrice: 60,
                  marketValue: 300,
                  unrealizedPl: 50,
                  unrealizedPlPercent: 20,
                ),
              ),
            ),
          ),
          GoRoute(
            path: '/app/portfolio',
            builder: (context, state) {
              navigatedLocation = '/app/portfolio';
              return const Scaffold(body: Text('PORTFOLIO TARGET'));
            },
          ),
        ],
      );

      await tester.pumpWidget(MaterialApp.router(routerConfig: router));
      await tester.pumpAndSettle();

      final btn = find.byKey(const Key('gtex-ownership-review-portfolio-btn'));
      expect(btn, findsOneWidget);

      await tester.tap(btn);
      await tester.pumpAndSettle();

      expect(navigatedLocation, equals('/app/portfolio'));
      expect(find.text('PORTFOLIO TARGET'), findsOneWidget);
    });

    testWidgets('Player Detail -> Matchday: navigating via MatchdayFormCard CTA opens /app/matches', (WidgetTester tester) async {
      String? navigatedLocation;

      final form = GtexPlayerForm(
        playerId: 'p1',
        hasSample: true,
        matchesCounted: 2,
        competitionsCounted: 1,
        totalMinutes: 180,
        totalGoals: 1,
        totalAssists: 0,
        performances: [],
      );

      final GoRouter router = GoRouter(
        initialLocation: '/player/p1',
        routes: [
          GoRoute(
            path: '/player/:id',
            builder: (context, state) => Scaffold(
              body: MatchdayFormCard(form: form),
            ),
          ),
          GoRoute(
            path: '/app/matches',
            builder: (context, state) {
              navigatedLocation = '/app/matches';
              return const Scaffold(body: Text('MATCHDAY TARGET'));
            },
          ),
        ],
      );

      await tester.pumpWidget(MaterialApp.router(routerConfig: router));
      await tester.pumpAndSettle();

      final btn = find.byKey(const Key('gtex-form-open-matchday-btn'));
      expect(btn, findsOneWidget);

      await tester.tap(btn);
      await tester.pumpAndSettle();

      expect(navigatedLocation, equals('/app/matches'));
      expect(find.text('MATCHDAY TARGET'), findsOneWidget);
    });

    testWidgets('Home -> canonical destinations: player movers route to Player Detail and club holdings route to Club screen', (WidgetTester tester) async {
      String? lastNavigatedRoute;

      const mover = GtexHomeMoverHighlight(
        playerId: 'player-101',
        playerName: 'Victor Osimhen',
        dayChangePercent: 4.5,
        isOwned: true,
      );

      const club = GtexHomeClubHighlight(
        clubId: 'club-202',
        clubName: 'Lagos City FC',
        sharesLabel: '10 shares',
        sharePriceLabel: '12.5 GTEX',
        plLabel: '+25 GTEX',
        isInProfit: true,
        hasPerformanceHistory: true,
      );

      final digest = GtexHomeDigest(
        userState: GtexHomeUserState.multiAsset,
        headline: 'Multi-asset owner overview',
        ownedPlayers: [],
        yourMoversToday: [mover],
        opportunityMovers: [],
        clubs: [club],
        regens: [],
        attentionItems: [],
        recentActivity: [],
        warnings: [],
      );

      late final GoRouter router;
      router = GoRouter(
        initialLocation: '/home',
        routes: [
          GoRoute(
            path: '/home',
            builder: (context, state) => GtexPlayerNavigator(
              openPlayer: (id) async {
                router.go('/player/$id');
              },
              child: Scaffold(
                body: Column(
                  children: [
                    HomeWhatMovedPanel(
                      digestValue: AsyncValue.data(digest),
                    ),
                    HomeYourClubsPanel(
                      digestValue: AsyncValue.data(digest),
                    ),
                  ],
                ),
              ),
            ),
          ),
          GoRoute(
            path: '/player/:id',
            builder: (context, state) {
              lastNavigatedRoute = '/player/${state.pathParameters['id']}';
              return Scaffold(body: Text('PLAYER DETAIL ${state.pathParameters['id']}'));
            },
          ),
          GoRoute(
            path: '/app/club',
            builder: (context, state) {
              lastNavigatedRoute = '/app/club';
              return const Scaffold(body: Text('CLUB SCREEN'));
            },
          ),
        ],
      );

      await tester.pumpWidget(MaterialApp.router(routerConfig: router));
      await tester.pumpAndSettle();

      // Tap player mover -> routes to /player/player-101
      expect(find.text('Victor Osimhen'), findsOneWidget);
      await tester.tap(find.text('Victor Osimhen'));
      await tester.pumpAndSettle();

      expect(lastNavigatedRoute, equals('/player/player-101'));
      expect(find.text('PLAYER DETAIL player-101'), findsOneWidget);

      // Go back to home
      router.go('/home');
      await tester.pumpAndSettle();

      // Tap club holding -> routes to /app/club
      expect(find.text('Lagos City FC'), findsOneWidget);
      await tester.tap(find.text('Lagos City FC'));
      await tester.pumpAndSettle();

      expect(lastNavigatedRoute, equals('/app/club'));
      expect(find.text('CLUB SCREEN'), findsOneWidget);
    });
  });
}
