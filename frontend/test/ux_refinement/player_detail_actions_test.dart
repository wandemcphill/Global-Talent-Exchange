import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

/// The market's only drill-down destination used to be read-only: there was
/// no way to act on a player anywhere it led. These cover the action states
/// so a CTA is never shown without a flow behind it.
void main() {
  // Controller setup performs real async work, so it has to run outside the
  // widget tester's fake-async zone.
  Future<GteExchangeController> signedInController(
    WidgetTester tester, {
    bool signIn = true,
  }) async {
    late GteExchangeController controller;
    await tester.runAsync(() async {
      controller = GteExchangeController(api: GteExchangeApiClient.fixture());
      await controller.bootstrap();
      if (signIn) {
        await controller.signIn(
          email: 'fixture.trader@gte.local',
          password: 'DemoPass123', // pragma: allowlist secret
        );
      }
    });
    return controller;
  }

  Future<void> pumpProfile(
    WidgetTester tester, {
    required String playerId,
    GteExchangeController? controller,
    VoidCallback? onOpenLogin,
  }) async {
    tester.view.physicalSize = const Size(420, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        home: GtexFmPlayerProfileScreen(
          playerId: playerId,
          baseUrl: 'http://fixture.local',
          backendMode: GteBackendMode.fixture,
          apiClient: GteExchangeApiClient.fixture(),
          controller: controller,
          onOpenLogin: onOpenLogin,
        ),
      ),
    );
    // The loading state uses an indefinite shimmer, so settle by pumping a
    // bounded number of frames rather than waiting for quiescence.
    for (int i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }
  }

  testWidgets('read-only when the shell supplies no exchange controller', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    final String playerId = controller.players.first.playerId;

    await pumpProfile(tester, playerId: playerId);

    expect(find.text('Trade player'), findsNothing);
    expect(find.text('Sign in to trade'), findsNothing);
  });

  testWidgets('signed-out session is offered sign-in, not a trade button', (
    WidgetTester tester,
  ) async {
    final GteExchangeController browsing = await signedInController(
      tester,
      signIn: false,
    );
    expect(browsing.isAuthenticated, isFalse);

    bool loginRequested = false;
    await pumpProfile(
      tester,
      playerId: browsing.players.first.playerId,
      controller: browsing,
      onOpenLogin: () => loginRequested = true,
    );

    expect(find.text('Trade player'), findsNothing);
    final Finder signIn = find.text('Sign in to trade');
    expect(signIn, findsOneWidget);

    await tester.tap(signIn);
    await tester.pump();
    expect(loginRequested, isTrue);
  });

  testWidgets('signed-in session reaches the live order ticket', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    final String playerId = controller.players.first.playerId;

    await pumpProfile(tester, playerId: playerId, controller: controller);

    final Finder trade = find.text('Trade player');
    expect(trade, findsOneWidget);

    await tester.tap(trade);
    for (int i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }

    // The sheet is the existing exchange order ticket, not a stub.
    expect(find.text('Place order'), findsOneWidget);
  });
}
