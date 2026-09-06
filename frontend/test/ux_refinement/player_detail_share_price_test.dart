import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// The canonical Player Detail has to answer "what is he worth?" and "what
/// does a share cost?" as two different questions.
///
/// It answered only the first: the market card showed the valuation under the
/// caption VALUE and stopped there, so the tradable price - the number the
/// user is actually charged - existed nowhere on the screen they decide from.
/// They met it for the first time inside the trade ticket.
void main() {
  Future<void> pumpProfile(WidgetTester tester, String playerId) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: GtexFmPlayerProfileScreen(
            playerId: playerId,
            baseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            apiClient: GteExchangeApiClient.fixture(),
          ),
        ),
      ),
    );
    for (int pump = 0; pump < 200; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
      if (find.text('VALUE').evaluate().isNotEmpty) {
        break;
      }
    }
  }

  testWidgets('quotes the tradable share price beside the valuation', (
    WidgetTester tester,
  ) async {
    await pumpProfile(tester, 'lamine-yamal');

    // The valuation keeps its own caption...
    expect(find.text('VALUE'), findsOneWidget);
    // ...and the price a trade settles at is stated in coin, on the screen
    // the user decides from rather than only inside the ticket.
    expect(find.text('SHARE PRICE'), findsOneWidget);
    expect(find.text('1.25 GTEX Coin'), findsOneWidget);
  });

  testWidgets('names the price and the valuation as different things', (
    WidgetTester tester,
  ) async {
    await pumpProfile(tester, 'lamine-yamal');

    // Two captions, two figures, and a line saying which is which. The
    // fixture prices a Yamal share at 1.25 coin and has no EUR valuation for
    // him, so the price must not borrow the valuation's slot or its absence.
    expect(find.text('VALUE'), findsOneWidget);
    expect(find.text('SHARE PRICE'), findsOneWidget);
    expect(find.text('1.25 GTEX Coin'), findsOneWidget);
    expect(
      find.text('What one share settles at. Value above is an estimate.'),
      findsOneWidget,
    );
  });
}
