import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_redesign_models.dart';
import 'package:gte_frontend/features/club_redesign/widgets/gtex_club_workspace_widgets.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_models.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/player_market_redesign/models/gtex_market_browse_models.dart';
import 'package:gte_frontend/features/player_market_redesign/widgets/gtex_market_selected_player_panel.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_match_lineups.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// GTEX had two competing player surfaces: the market's side panel held the
/// transfer terms, the profile held the attributes and the order book, and
/// several places that named a footballer - a club squad row, a match lineup
/// name, a search result - could not reach either. These pin the canonical
/// experience: one player detail, reachable the same way from everywhere.
void main() {
  Future<GteExchangeController> signedInController(WidgetTester tester) async {
    late GteExchangeController controller;
    await tester.runAsync(() async {
      controller = GteExchangeController(api: GteExchangeApiClient.fixture());
      await controller.bootstrap();
      await controller.signIn(
        email: 'fixture.trader@gte.local',
        password: 'DemoPass123', // pragma: allowlist secret
      );
    });
    return controller;
  }

  Future<void> pumpShell(
    WidgetTester tester,
    GteExchangeController controller,
    String path,
    Finder ready,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteExchangeShellScreen.fromPath(
          controller: controller,
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          initialPath: path,
        ),
      ),
    );
    for (int pump = 0; pump < 200; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
      if (ready.evaluate().isNotEmpty) {
        break;
      }
    }
  }

  testWidgets('the market opens the canonical player detail', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    await pumpShell(
      tester,
      controller,
      '/app/market',
      find.byType(GtexPlayerCard),
    );

    await tester.tap(find.text('Open').first);
    for (int pump = 0; pump < 40; pump += 1) {
      await tester.pump(const Duration(milliseconds: 60));
      if (find.byType(GtexFmPlayerProfileScreen).evaluate().isNotEmpty) {
        break;
      }
    }

    expect(find.byType(GtexFmPlayerProfileScreen), findsOneWidget);
  });

  testWidgets('the market summary panel is a preview, not a second detail', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(420, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
      GteMarketPlayerListItem.fromJson(<String, Object?>{
        'player_id': 'player-1',
        'player_name': 'Samuel Okoro',
        'position': 'ST',
        'nationality': 'Nigeria',
        'current_club_name': 'Ikorodu City',
        'age': 24,
        'current_value_credits': 420000,
        'movement_pct': 2.4,
        'global_scouting_index': 88,
        'salary_amount': 1200,
        'buy_clause_amount': 900000,
        'contract_years_remaining': 3,
        'availability_label': 'Transfer eligible',
        'asking_type': 'transfer_eligible',
        'is_tradable': true,
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: GtexMarketSelectedPlayerPanel(
            selectedPlayer: player,
            basketState: const GtexMarketBasketState(
              <String, GtexMarketPlayerView>{},
            ),
            isAuthenticated: true,
            onOpenLogin: () {},
            onOpenPlayer: (_) {},
            onToggleBasket: (_) {},
            onRemoveFromBasket: (_) {},
            onCheckout: () {},
          ),
        ),
      ),
    );
    await tester.pump();

    // What it keeps is a read on the player, not a second detail screen.
    expect(find.text('At a glance'), findsOneWidget);
    expect(find.text('+2.4%'), findsWidgets);

    // The preview leads with the way through to the canonical detail. It
    // sits below the summary in a scrolling panel, so scroll to it.
    await tester.drag(find.text('At a glance'), const Offset(0, -400));
    await tester.pump();
    expect(
      find.byKey(const Key('gtex-market-open-full-profile')),
      findsOneWidget,
    );
    // ...and no longer holds the terms only it used to have. Salary,
    // contract, buy clause, swap and loan terms are on the player detail.
    expect(find.text('Buy clause'), findsNothing);
    expect(find.text('Loan-to-buy'), findsNothing);
    expect(find.text('Salary range'), findsNothing);
    expect(find.text('Swap condition'), findsNothing);
  });

  testWidgets('the preview CTA is reachable in the real shell at 1440x900', (
    WidgetTester tester,
  ) async {
    // The preview only counts as the way into the canonical detail if a
    // user can actually see the way in. In the real shell the summary pane
    // is roughly a third of the workspace height, and the poster card used
    // to fill all of it: "Open full profile" sat so far down the list that
    // it was never built, let alone shown. A 420x1600 harness hides this
    // exactly the way the scaffold's own harness hid the width bug.
    final GteExchangeController controller = await signedInController(tester);
    await pumpShell(
      tester,
      controller,
      '/app/market',
      find.byType(GtexMarketSelectedPlayerPanel),
    );

    final Finder cta = find.byKey(const Key('gtex-market-open-full-profile'));
    expect(
      cta,
      findsOneWidget,
      reason: 'the preview must offer the canonical detail without scrolling',
    );

    final Rect panel = tester.getRect(
      find.byType(GtexMarketSelectedPlayerPanel),
    );
    final Rect button = tester.getRect(cta);
    expect(
      button.bottom,
      lessThanOrEqualTo(panel.bottom),
      reason: 'the CTA is below the summary pane at 1440x900',
    );
    expect(button.top, greaterThanOrEqualTo(panel.top));
  });

  testWidgets('a search hit for a player canonicalises to the player detail', (
    WidgetTester tester,
  ) async {
    // Previously '/app/market?player=<id>', a query no screen ever read.
    expect(
      gtexCanonicalGlobalSearchRoute('/player/abc-123', isAdmin: false),
      '/players/abc-123/profile',
    );
    expect(
      gtexCanonicalGlobalSearchRoute('/players/abc-123', isAdmin: false),
      '/players/abc-123/profile',
    );
  });

  testWidgets('a club squad row opens the canonical player detail', (
    WidgetTester tester,
  ) async {
    final List<String> opened = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: GtexPlayerNavigator(
            openPlayer: (String playerId) async => opened.add(playerId),
            child: const SingleChildScrollView(
              child: GtexClubSquadList(
                squad: <GtexClubMember>[
                  GtexClubMember(
                    id: 'player-77',
                    name: 'Samuel Okoro',
                    position: 'ST',
                    nationality: 'Nigeria',
                    valueCredits: 420000,
                    rating: 83.4,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.byKey(const Key('gtex-club-squad-open-player-77')));
    await tester.pump();

    expect(opened, <String>['player-77']);
  });

  testWidgets('a match lineup name opens the canonical player detail', (
    WidgetTester tester,
  ) async {
    final List<String> opened = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: GtexPlayerNavigator(
            openPlayer: (String playerId) async => opened.add(playerId),
            child: GtexMatchLineups(home: _team('home'), away: _team('away')),
          ),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.byKey(const Key('gtex-lineup-open-player-9')));
    await tester.pump();

    expect(opened, <String>['player-9']);
  });

  testWidgets('a lineup row with no player id is not made falsely tappable', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: GtexPlayerNavigator(
            openPlayer: (String playerId) async {},
            child: GtexMatchLineups(
              home: _team('home', idIsName: true),
              away: _team('away', idIsName: true),
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    // The repository falls back to the player's name when the feed omits an
    // id, and a name cannot be looked up.
    expect(find.byKey(const Key('gtex-lineup-open-Ade Balogun')), findsNothing);
  });

  testWidgets('outside the shell a squad row stays plain text', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexClubSquadList(
              squad: <GtexClubMember>[
                GtexClubMember(
                  id: 'player-77',
                  name: 'Samuel Okoro',
                  position: 'ST',
                  nationality: 'Nigeria',
                  valueCredits: 420000,
                  rating: 83.4,
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Samuel Okoro'), findsOneWidget);
    expect(
      find.byKey(const Key('gtex-club-squad-open-player-77')),
      findsNothing,
      reason: 'a control with nothing behind it must not be drawn',
    );
  });

  testWidgets('the canonical detail holds both halves of the player story', (
    WidgetTester tester,
  ) async {
    // The shell hands the profile a strict-live client, which by policy has
    // no fixtures, so content is asserted against the canonical screen
    // pumped with the fixture client - the same screen class the market,
    // the wallet, a club squad row and the /players/:id/profile deep link
    // all resolve to.
    tester.view.physicalSize = const Size(420, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final GteExchangeController controller = await signedInController(tester);
    await tester.pumpWidget(
      MaterialApp(
        home: GtexFmPlayerProfileScreen(
          playerId: controller.players.first.playerId,
          baseUrl: 'http://fixture.local',
          backendMode: GteBackendMode.fixture,
          apiClient: GteExchangeApiClient.fixture(),
          controller: controller,
        ),
      ),
    );
    for (int pump = 0; pump < 40; pump += 1) {
      await tester.pump(const Duration(milliseconds: 120));
      if (find.text('FOOTBALL PROFILE').evaluate().isNotEmpty) {
        break;
      }
    }

    expect(find.text('FOOTBALL PROFILE'), findsOneWidget);
    expect(find.text('ATTRIBUTES'), findsOneWidget);
    expect(find.text('TRAJECTORY'), findsOneWidget);
    expect(find.text('ASSET & MARKET INTELLIGENCE'), findsOneWidget);
    expect(find.text('TERMS'), findsOneWidget);
    // The transfer terms that used to live only in the market side panel.
    expect(find.text('TRANSFER'), findsOneWidget);
    expect(find.text('Buy clause'), findsOneWidget);
    expect(find.text('Salary'), findsOneWidget);
  });
}

GtexMatchTeam _team(String side, {bool idIsName = false}) {
  return GtexMatchTeam(
    id: side,
    name: side == 'home' ? 'Ikorodu City' : 'Lagos Union',
    shortName: side == 'home' ? 'IKO' : 'LAG',
    score: 0,
    formation: '4-3-3',
    players: <GtexLineupPlayer>[
      GtexLineupPlayer(
        id: idIsName ? 'Ade Balogun' : 'player-${side == 'home' ? 9 : 11}',
        name: 'Ade Balogun',
        position: 'ST',
        shirtNumber: 9,
        rating: 7.4,
      ),
    ],
  );
}
