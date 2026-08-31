import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/features/player_market_redesign/widgets/gtex_market_context_panel.dart';
import 'package:gte_frontend/features/player_market_redesign/widgets/gtex_market_selected_player_panel.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// The Transfer Hub used to lose its player list to secondary chrome across
/// two wide bands of viewport width. `GtexMasterDetailScaffold` sized itself
/// from `MediaQuery` - the window - while the box it was actually handed was
/// ~412px narrower (nav rail + world-pulse rail), so it reserved inline
/// panels it could not afford and the detail pane absorbed the whole
/// shortfall. Measured card widths were 0px at 720-820, 70px at 900, 194px
/// at 1024, 64px at 1280 and 224px at 1440.
///
/// These tests measure the real shell, not a synthetic scaffold harness: the
/// bug was invisible to a directly-pumped scaffold precisely because there
/// the window and the box are the same thing.
void main() {
  /// Every window width the audit measured, including both sides of each
  /// breakpoint the old layout tripped over.
  const List<double> ladder = <double>[
    390,
    600,
    719,
    720,
    768,
    820,
    900,
    960,
    1024,
    1100,
    1200,
    1240,
    1279,
    1280,
    1300,
    1366,
    1400,
    1440,
    1500,
    1600,
    1920,
  ];

  /// The narrowest a browse card may be and still show a footballer: name,
  /// position, club, rating and price side by side.
  const double minCardWidth = 300;

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
    double width,
    String path,
    Finder ready, {
    GteExchangeController? controller,
  }) async {
    tester.view.physicalSize = Size(width, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        // Keyed by width so sweeping the ladder inside a single test
        // remounts the shell rather than reusing the previous width's state.
        home: KeyedSubtree(
          key: ValueKey<String>('ladder-$path-$width'),
          child: GteExchangeShellScreen.fromPath(
            controller:
                controller ??
                GteExchangeController(api: GteExchangeApiClient.fixture()),
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialPath: path,
          ),
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

  final Map<double, double> measuredCardWidth = <double, double>{};

  for (final double width in ladder) {
    testWidgets('transfer hub keeps a usable player card at ${width}px', (
      WidgetTester tester,
    ) async {
      await pumpShell(
        tester,
        width,
        '/app/market',
        find.byType(GtexPlayerCard),
      );

      final Finder cards = find.byType(GtexPlayerCard);
      expect(
        cards,
        findsWidgets,
        reason: 'the market must render player cards at ${width}px',
      );

      final double cardWidth = tester.getSize(cards.first).width;
      measuredCardWidth[width] = cardWidth;
      expect(
        cardWidth,
        greaterThanOrEqualTo(minCardWidth),
        reason:
            'player cards collapsed to ${cardWidth.toStringAsFixed(0)}px at '
            '${width}px - secondary chrome is eating the content pane again',
      );

      // The micro layout is the card's last-resort presentation: name, price
      // and nothing actionable. It must never be what the market renders.
      expect(
        find.text('Shortlist'),
        findsWidgets,
        reason:
            'browse cards fell back to the micro layout at ${width}px '
            '(card was ${cardWidth.toStringAsFixed(0)}px wide)',
      );

      expect(
        tester.takeException(),
        isNull,
        reason: 'the market overflowed at ${width}px',
      );
    });
  }

  testWidgets('no viewport width starves the card the way a smaller one does', (
    WidgetTester tester,
  ) async {
    // Progressive disclosure means a card can legitimately narrow when a
    // panel becomes affordable - going 1200 -> 1240 buys the summary panel
    // and spends detail width on it. What must never happen again is the
    // collapse the audit measured, where crossing 1280 upward cost 385px and
    // dropped the card below legibility. Every step stays above the floor,
    // and no single step may give up more than the widest panel it can be
    // paying for.
    const double maxStepRegression = 360;
    for (final double width in ladder) {
      await pumpShell(
        tester,
        width,
        '/app/market',
        find.byType(GtexPlayerCard),
      );
      final Finder cards = find.byType(GtexPlayerCard);
      expect(cards, findsWidgets, reason: 'no cards at ${width}px');
      measuredCardWidth[width] = tester.getSize(cards.first).width;
    }

    for (int index = 1; index < ladder.length; index += 1) {
      final double previous = measuredCardWidth[ladder[index - 1]]!;
      final double current = measuredCardWidth[ladder[index]]!;
      expect(
        current,
        greaterThanOrEqualTo(minCardWidth),
        reason: 'card starved at ${ladder[index]}px',
      );
      expect(
        previous - current,
        lessThanOrEqualTo(maxStepRegression),
        reason:
            'card lost ${(previous - current).toStringAsFixed(0)}px going '
            'from ${ladder[index - 1]}px to ${ladder[index]}px',
      );
    }
  });

  testWidgets('the summary panel stays reachable at every width', (
    WidgetTester tester,
  ) async {
    for (final double width in ladder) {
      await pumpShell(
        tester,
        width,
        '/app/market',
        find.byType(GtexPlayerCard),
      );

      final bool inlineSummary =
          find.byType(GtexMarketSelectedPlayerPanel).evaluate().isNotEmpty;
      final bool summarySheetAction =
          find
              .byKey(const Key('gtex-master-detail-summary-action'))
              .evaluate()
              .isNotEmpty;

      expect(
        inlineSummary || summarySheetAction,
        isTrue,
        reason: 'the shortlist/summary panel is unreachable at ${width}px',
      );
    }
  });

  testWidgets('the browse panel stays reachable at every width', (
    WidgetTester tester,
  ) async {
    for (final double width in ladder) {
      await pumpShell(
        tester,
        width,
        '/app/market',
        find.byType(GtexPlayerCard),
      );

      final bool inlineBrowse =
          find.byType(GtexMarketContextPanel).evaluate().isNotEmpty;
      final bool browseSheetAction =
          find
              .byKey(const Key('gtex-master-detail-browse-action'))
              .evaluate()
              .isNotEmpty;

      expect(
        inlineBrowse || browseSheetAction,
        isTrue,
        reason: 'the browse/filter panel is unreachable at ${width}px',
      );
    }
  });

  // The scaffold is shared, so the fix has to hold on every screen that uses
  // it - Wallet & Capital runs the same three-pane composition.
  for (final double width in <double>[390, 768, 1024, 1280, 1440]) {
    testWidgets('wallet & capital lays out cleanly at ${width}px', (
      WidgetTester tester,
    ) async {
      await pumpShell(
        tester,
        width,
        '/app/capital',
        find.byType(GtexMasterDetailScaffold),
        controller: await signedInController(tester),
      );

      expect(
        find.byType(GtexMasterDetailScaffold),
        findsOneWidget,
        reason: 'capital must use the shared master-detail scaffold',
      );
      expect(
        tester.takeException(),
        isNull,
        reason: 'wallet & capital overflowed at ${width}px',
      );
    });
  }
}
