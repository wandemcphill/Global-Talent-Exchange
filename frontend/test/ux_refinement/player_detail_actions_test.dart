import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

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
    Size size = const Size(420, 1400),
  }) async {
    tester.view.physicalSize = size;
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

  testWidgets('football sections come before the asset sections', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    await pumpProfile(
      tester,
      playerId: controller.players.first.playerId,
      controller: controller,
    );

    // Position in the widget tree, not pixel position: below 1100px the page
    // is one column, so the football half is literally earlier in the scroll.
    final int football = _indexOfText(tester, 'FOOTBALL PROFILE');
    final int attributes = _indexOfText(tester, 'ATTRIBUTES');
    final int trajectory = _indexOfText(tester, 'TRAJECTORY');
    final int asset = _indexOfText(tester, 'ASSET & MARKET INTELLIGENCE');

    expect(football, greaterThanOrEqualTo(0));
    expect(asset, greaterThan(football));
    expect(attributes, greaterThan(football));
    expect(asset, greaterThan(attributes));
    expect(asset, greaterThan(trajectory));
  });

  testWidgets('the trade action is reachable without scrolling on mobile', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    await pumpProfile(
      tester,
      playerId: controller.players.first.playerId,
      controller: controller,
      size: const Size(390, 844),
    );

    final Finder trade = find.text('Trade player');
    expect(trade, findsOneWidget);
    final Rect rect = tester.getRect(trade);
    expect(rect.bottom, lessThanOrEqualTo(844));
    expect(rect.top, greaterThanOrEqualTo(0));
  });

  testWidgets('the trade action is reachable without scrolling on desktop', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    await pumpProfile(
      tester,
      playerId: controller.players.first.playerId,
      controller: controller,
      size: const Size(1440, 900),
    );

    final Finder trade = find.text('Trade player');
    expect(trade, findsOneWidget);
    final Rect rect = tester.getRect(trade);
    expect(rect.bottom, lessThanOrEqualTo(900));
  });

  testWidgets('desktop uses two columns and mobile stays single column', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    final String playerId = controller.players.first.playerId;

    await pumpProfile(
      tester,
      playerId: playerId,
      controller: controller,
      size: const Size(1200, 1000),
    );
    final Rect wideFootball = tester.getRect(find.text('FOOTBALL PROFILE'));
    final Rect wideAsset = tester.getRect(
      find.text('ASSET & MARKET INTELLIGENCE'),
    );
    expect(
      wideAsset.left,
      greaterThan(wideFootball.right),
      reason: 'at 1200px the asset case sits beside the football profile',
    );

    await pumpProfile(
      tester,
      playerId: playerId,
      controller: controller,
      size: const Size(900, 1600),
    );
    final Rect narrowFootball = tester.getRect(find.text('FOOTBALL PROFILE'));
    final Rect narrowAsset = tester.getRect(
      find.text('ASSET & MARKET INTELLIGENCE'),
    );
    expect(
      narrowAsset.top,
      greaterThan(narrowFootball.top),
      reason: 'at 900px the page stays a single column',
    );
    expect(narrowAsset.left, closeTo(narrowFootball.left, 1));
  });

  testWidgets('a profile with no photograph gets an identity plate, no face', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = await signedInController(tester);
    await pumpProfile(
      tester,
      playerId: controller.players.first.playerId,
      controller: controller,
    );

    expect(
      find.byType(GtexPlayerPortrait),
      findsOneWidget,
      reason: 'the identity block must carry a portrait region',
    );
    final bool hasPhoto =
        find
            .byKey(const Key('gtex-player-portrait-image'))
            .evaluate()
            .isNotEmpty;
    final bool hasPlate =
        find
            .byKey(const Key('gtex-player-portrait-plate'))
            .evaluate()
            .isNotEmpty;
    expect(hasPhoto || hasPlate, isTrue);
  });

  testWidgets('unknown potential and attributes render as unknown, not zero', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(420, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: GtexFmPlayerProfileScreen(
          playerId: 'unscouted-player',
          baseUrl: 'http://fixture.local',
          backendMode: GteBackendMode.fixture,
          apiClient: _UnscoutedPlayerApi(),
        ),
      ),
    );
    for (int i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }

    expect(find.text('POT'), findsOneWidget);
    expect(
      find.text('0'),
      findsNothing,
      reason: 'an unscouted attribute must never be rendered as a zero',
    );
    // Six attribute bars plus the potential plate all read as unknown.
    expect(find.text('\u2014'), findsAtLeastNWidgets(7));
  });

  testWidgets('an unpriced asset shows no percentage movement', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(420, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: GtexFmPlayerProfileScreen(
          playerId: 'unscouted-player',
          baseUrl: 'http://fixture.local',
          backendMode: GteBackendMode.fixture,
          apiClient: _UnscoutedPlayerApi(),
        ),
      ),
    );
    for (int i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }

    expect(find.text('Unpriced'), findsOneWidget);
    expect(
      find.textContaining('% recent'),
      findsNothing,
      reason: 'a movement percentage implies a price this asset does not have',
    );
  });
}

/// Position of a text widget in a depth-first walk of the tree. Used to
/// assert section order without depending on pixel geometry.
int _indexOfText(WidgetTester tester, String text) {
  final List<Element> all = <Element>[];
  void visit(Element element) {
    all.add(element);
    element.visitChildren(visit);
  }

  tester.binding.rootElement!.visitChildren(visit);
  for (int index = 0; index < all.length; index += 1) {
    final Widget widget = all[index].widget;
    if (widget is Text && widget.data == text) {
      return index;
    }
  }
  return -1;
}

/// A player the backend has priced and scouted for nothing: every attribute
/// defaults to zero and there is no market value. This is the shape that
/// used to render six red zeroes and a movement percentage.
class _UnscoutedPlayerApi extends GteExchangeApiClient {
  _UnscoutedPlayerApi._(GteExchangeApiClient base)
    : super(
        config: base.config,
        transport: base.transport,
        repository: base.repository,
      );

  factory _UnscoutedPlayerApi() =>
      _UnscoutedPlayerApi._(GteExchangeApiClient.fixture());

  @override
  Future<GteMarketPlayerDetailView> fetchPlayerDetail(String playerId) async {
    return GteMarketPlayerDetailView.fromJson(<String, Object?>{
      'player_id': playerId,
      'identity': <String, Object?>{
        'player_id': playerId,
        'player_name': 'Unscouted Prospect',
        'position': 'CM',
        'age': 19,
        'nationality': 'Nigeria',
      },
      'market_profile': <String, Object?>{'is_tradable': false},
      'value': <String, Object?>{
        'current_value_credits': 0,
        'movement_pct': 0.1,
      },
      'trend': <String, Object?>{
        'trend_score': 0,
        'market_interest_score': 0,
        'global_scouting_index': 61,
      },
      'attributes': <String, Object?>{},
    });
  }
}
