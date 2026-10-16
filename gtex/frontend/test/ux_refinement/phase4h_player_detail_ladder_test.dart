import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// PHASE 4H - the canonical player detail across the breakpoint ladder,
/// opened the way a user opens it: from a market card, through the one
/// canonical player navigator.
///
/// Player detail is pushed full-screen over the shell, so unlike the lanes it
/// really does own the whole window. What it must not do is fail to render,
/// stop scrolling, or hand the reader a different screen at any width the
/// product supports.
void main() {
  const List<double> ladder = <double>[390, 430, 768, 1024, 1280, 1440, 1920];

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

  Future<void> pumpUntil(WidgetTester tester, Finder finder) async {
    for (int pump = 0; pump < 120; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
      if (finder.evaluate().isNotEmpty) {
        return;
      }
    }
  }

  for (final double width in ladder) {
    testWidgets('canonical player detail lays out at ${width.toInt()}px', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = Size(width, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = await signedInController(tester);
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: KeyedSubtree(
            key: ValueKey<String>('detail-ladder-$width'),
            child: GteExchangeShellScreen.fromPath(
              controller: controller,
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              initialPath: '/app/market',
            ),
          ),
        ),
      );
      await pumpUntil(tester, find.byType(GtexPlayerCard));
      expect(
        find.byType(GtexPlayerCard),
        findsWidgets,
        reason: 'the market had no player to open at ${width.toInt()}px',
      );

      await tester.tap(find.text('Open').first);
      await pumpUntil(tester, find.byType(GtexFmPlayerProfileScreen));

      // One canonical detail, reached the same way at every width.
      expect(
        find.byType(GtexFmPlayerProfileScreen),
        findsOneWidget,
        reason:
            'opening a player at ${width.toInt()}px did not reach the '
            'canonical player detail',
      );

      final List<String> errors = <String>[];
      for (int i = 0; i < 20; i += 1) {
        final Object? error = tester.takeException();
        if (error == null) {
          break;
        }
        errors.add(error.toString().split('\n').first);
      }
      expect(
        errors,
        isEmpty,
        reason:
            'the canonical player detail reported unrenderable layout at '
            '${width.toInt()}px:\n  ${errors.join('\n  ')}',
      );

      // Whatever state it lands in - loaded, empty or blocked - the surface
      // scrolls, so nothing it renders sits below a clipped edge.
      expect(
        find.byType(Scrollable),
        findsWidgets,
        reason: 'player detail stopped scrolling at ${width.toInt()}px',
      );
    });
  }
}
