import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/screens/match/gtex_match_broadcast_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_event_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_hidden_controls_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_mode_selector_button.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_match_canvas.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('mode selector is placed in the app bar', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byType(AppBar), findsOneWidget);
    expect(
      find.descendant(
        of: find.byType(AppBar),
        matching: find.byType(GtexModeSelectorButton),
      ),
      findsOneWidget,
    );
  });

  testWidgets('hidden controls are not always visible and show on tap', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    final AnimatedOpacity initialOpacity = tester.widget<AnimatedOpacity>(
      find.byKey(GtexHiddenControlsOverlay.overlayKey),
    );
    expect(initialOpacity.opacity, 0);

    await tester.tap(find.byType(Scaffold));
    await tester.pump(const Duration(milliseconds: 220));

    final AnimatedOpacity visibleOpacity = tester.widget<AnimatedOpacity>(
      find.byKey(GtexHiddenControlsOverlay.overlayKey),
    );
    expect(visibleOpacity.opacity, 1);
  });

  testWidgets('event overlay appears during playback', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));
    await tester.pump(const Duration(milliseconds: 2500));

    expect(
      find.descendant(
        of: find.byType(GtexEventOverlay),
        matching: find.text('Chance'),
      ),
      findsOneWidget,
    );
  });

  testWidgets('broadcast screen does not expose gifting controls', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.text('Gift'), findsNothing);
    expect(find.byIcon(Icons.card_giftcard_rounded), findsNothing);
  });

  testWidgets('broadcast HUD remains usable in a narrow layout', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(360, 780));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));
    await tester.tap(find.byType(Scaffold));
    await tester.pump(const Duration(milliseconds: 220));

    expect(find.byType(AppBar), findsOneWidget);
    expect(find.byKey(GtexHiddenControlsOverlay.overlayKey), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pseudo-3D broadcast screen loads without crashing', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.pseudo3D,
          isPremiumUser: true,
          spectatorMode: true,
          auto3DEnabled: true,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byType(GtexPseudo3DMatchCanvas), findsOneWidget);
  });

  testWidgets('broadcast playback pauses while the app is backgrounded', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump(const Duration(milliseconds: 2600));

    expect(
      find.descendant(
        of: find.byType(GtexEventOverlay),
        matching: find.text('Chance'),
      ),
      findsNothing,
    );

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 2600));

    expect(
      find.descendant(
        of: find.byType(GtexEventOverlay),
        matching: find.text('Chance'),
      ),
      findsOneWidget,
    );
  });
}

Widget _host({required Widget child}) {
  return MaterialApp(
    theme: GteShellTheme.build(),
    home: child,
  );
}
