import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/platform/gtex_platform_experience_controller.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';
import 'package:gte_frontend/screens/match/gtex_match_broadcast_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_event_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_hidden_controls_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_mode_selector_button.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_tv_mode_shell.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_web_mode_sidebar.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
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

  testWidgets('broadcast screen exposes gifting controls', (
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

    expect(find.text('Gift'), findsOneWidget);
    expect(find.byIcon(Icons.card_giftcard_rounded), findsOneWidget);
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

  testWidgets('broadcast falls back to 2D when pseudo-3D is unavailable', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: GtexMatchViewType.pseudo3D,
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

    expect(find.byType(Pitch2dWidget), findsOneWidget);
    expect(find.byType(GtexPseudo3DMatchCanvas), findsNothing);
    expect(find.byTooltip('Broadcast+ locked'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('broadcast switches cleanly between 2D and pseudo-3D views', (
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
          isPremiumUser: true,
          spectatorMode: true,
          auto3DEnabled: false,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byType(Pitch2dWidget), findsOneWidget);
    expect(find.byType(GtexPseudo3DMatchCanvas), findsNothing);

    await tester.tap(find.byTooltip('Switch to Broadcast+'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 260));

    expect(find.byType(GtexPseudo3DMatchCanvas), findsOneWidget);
    expect(find.byType(Pitch2dWidget), findsNothing);

    await tester.tap(find.byTooltip('Switch to 2D'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 260));

    expect(find.byType(Pitch2dWidget), findsOneWidget);
    expect(find.byType(GtexPseudo3DMatchCanvas), findsNothing);
    expect(tester.takeException(), isNull);
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

  testWidgets('broadcast route can be popped and reopened cleanly', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Builder(
          builder: (BuildContext context) {
            return Scaffold(
              body: Center(
                child: FilledButton(
                  onPressed: () {
                    Navigator.of(context).push<void>(
                      MaterialPageRoute<void>(
                        builder:
                            (BuildContext context) => GtexMatchBroadcastScreen(
                              matchId: 'broadcast-screen',
                              initialMode: GtexMatchRenderMode.quick,
                              viewType: GtexMatchViewType.twoD,
                              isPremiumUser: false,
                              spectatorMode: true,
                              auto3DEnabled: false,
                              competitionLabel: 'GTEX Cup',
                              viewStateLoader:
                                  () async => buildBroadcastTestViewState(),
                            ),
                      ),
                    );
                  },
                  child: const Text('Open broadcast'),
                ),
              ),
            );
          },
        ),
      ),
    );

    await tester.tap(find.text('Open broadcast'));
    await tester.pump(const Duration(milliseconds: 350));
    await _pumpUntilVisible(
      tester,
      find.descendant(
        of: find.byType(GtexEventOverlay),
        matching: find.text('Chance'),
      ),
    );

    expect(
      find.descendant(
        of: find.byType(GtexEventOverlay),
        matching: find.text('Chance'),
      ),
      findsOneWidget,
    );

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Open broadcast'), findsOneWidget);

    await tester.tap(find.text('Open broadcast'));
    await tester.pump(const Duration(milliseconds: 350));
    await _pumpUntilVisible(
      tester,
      find.descendant(
        of: find.byType(GtexEventOverlay),
        matching: find.text('Chance'),
      ),
    );

    expect(
      find.descendant(
        of: find.byType(GtexEventOverlay),
        matching: find.text('Chance'),
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('tv mode removes the app bar and shows the live channel shell', (
    WidgetTester tester,
  ) async {
    final GtexPlatformExperienceController platformController =
        GtexPlatformExperienceController(
          mode: GtexPlatformMode.tv,
          channels: const <GtexTvChannel>[
            GtexTvChannel(
              channelId: 'live',
              name: 'Live',
              headline: 'Lagos Stars vs Abuja City',
              subheadline: 'Main feed',
              matchId: 'broadcast-screen',
              viewerCount: 1200,
            ),
          ],
        );

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
          platformMode: GtexPlatformMode.tv,
          platformController: platformController,
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byType(AppBar), findsNothing);
    expect(find.byKey(GtexTvModeShell.shellKey), findsOneWidget);
    expect(find.text('What\'s Live Now'), findsOneWidget);
  });

  testWidgets('web mode shows the multi-match and trading sidebar', (
    WidgetTester tester,
  ) async {
    final GtexPlatformExperienceController platformController =
        GtexPlatformExperienceController(
          mode: GtexPlatformMode.web,
          channels: const <GtexTvChannel>[
            GtexTvChannel(
              channelId: 'trending',
              name: 'Trending',
              headline: 'GTEX Match Desk',
              subheadline: 'Secondary feed',
              viewerCount: 680,
            ),
          ],
        );

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
          platformMode: GtexPlatformMode.web,
          platformController: platformController,
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byKey(GtexWebModeSidebar.sidebarKey), findsOneWidget);
    expect(find.text('Match Control'), findsOneWidget);
    expect(find.byType(AppBar), findsOneWidget);
  });
}

Widget _host({required Widget child}) {
  return MaterialApp(theme: GteShellTheme.build(), home: child);
}

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  Duration step = const Duration(milliseconds: 100),
  Duration timeout = const Duration(seconds: 4),
}) async {
  final int attempts = timeout.inMilliseconds ~/ step.inMilliseconds;
  for (int index = 0; index < attempts; index += 1) {
    if (finder.evaluate().isNotEmpty) {
      return;
    }
    await tester.pump(step);
  }
  expect(finder, findsOneWidget);
}
