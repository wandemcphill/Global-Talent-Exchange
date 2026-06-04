import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/platform/gtex_platform_experience_controller.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';
import 'package:gte_frontend/features/match_center/presentation/gtex_match_broadcast_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_event_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_hidden_controls_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_mode_selector_button.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_tv_mode_shell.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_web_mode_sidebar.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_widget.dart';

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
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _liveSegmentViewState(),
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
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _liveSegmentViewState(),
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

  testWidgets('event overlay appears from a backend-authored active frame', (
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
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _backendAuthoredChanceViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(_eventOverlayText('Chance'), findsOneWidget);
  });

  testWidgets('event overlay is not synthesized from event timing alone', (
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
          competitionLabel: 'GTEX Cup',
          viewStateLoader:
              () async => _withoutBackendAuthoredOverlayViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));
    await tester.pump(const Duration(seconds: 3));

    expect(_eventOverlayText('Chance'), findsNothing);
    expect(_eventOverlayText('Goal'), findsNothing);
  });

  testWidgets('broadcast screen exposes gifting controls for spectators', (
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
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _liveSegmentViewState(),
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
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _liveSegmentViewState(),
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

  testWidgets('alternate view requests stay on the 2D broadcast canvas', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: gtexMatchViewTypeFromString('3d'),
          isPremiumUser: true,
          spectatorMode: true,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _liveSegmentViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byType(Pitch2dWidget), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('twoD-canvas')), findsOneWidget);
  });

  testWidgets('broadcast remains 2D when alternate view is unavailable', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        child: GtexMatchBroadcastScreen(
          matchId: 'broadcast-screen',
          initialMode: GtexMatchRenderMode.quick,
          viewType: gtexMatchViewTypeFromString('3d'),
          isPremiumUser: false,
          spectatorMode: true,
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _liveSegmentViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byType(Pitch2dWidget), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('twoD-canvas')), findsOneWidget);
    expect(find.byTooltip('Broadcast+ locked'), findsNothing);
    expect(find.byTooltip('Switch to Broadcast+'), findsNothing);
    expect(find.byTooltip('Switch to 2D'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('legacy Broadcast+ controls stay hidden on the 2D canvas', (
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
          competitionLabel: 'GTEX Cup',
          viewStateLoader: () async => _liveSegmentViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.byType(Pitch2dWidget), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('twoD-canvas')), findsOneWidget);
    expect(find.byTooltip('Broadcast+ locked'), findsNothing);
    expect(find.byTooltip('Switch to Broadcast+'), findsNothing);
    expect(find.byTooltip('Switch to 2D'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'paused and backgrounded lifecycle does not advance match truth',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        _host(
          child: GtexMatchBroadcastScreen(
            matchId: 'broadcast-screen',
            initialMode: GtexMatchRenderMode.quick,
            viewType: GtexMatchViewType.twoD,
            isPremiumUser: false,
            spectatorMode: true,
            competitionLabel: 'GTEX Cup',
            viewStateLoader: () async => _backendHeldBeforeChanceViewState(),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 32));

      expect(_eventOverlayText('Chance'), findsNothing);

      await tester.tap(find.byType(Scaffold));
      await tester.pump(const Duration(milliseconds: 220));
      await tester.tap(find.text('Sync'));
      await tester.pump();
      await tester.pump(const Duration(seconds: 3));

      expect(_eventOverlayText('Chance'), findsNothing);

      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump(const Duration(seconds: 3));

      expect(_eventOverlayText('Chance'), findsNothing);

      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      await tester.pump(const Duration(seconds: 3));

      expect(_eventOverlayText('Chance'), findsNothing);
    },
  );

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
                              competitionLabel: 'GTEX Cup',
                              viewStateLoader:
                                  () async => _backendAuthoredChanceViewState(),
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
    await tester.pumpAndSettle();

    expect(_eventOverlayText('Chance'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Open broadcast'), findsOneWidget);

    await tester.tap(find.text('Open broadcast'));
    await tester.pumpAndSettle();

    expect(_eventOverlayText('Chance'), findsOneWidget);
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
          competitionLabel: 'GTEX Cup',
          platformMode: GtexPlatformMode.tv,
          platformController: platformController,
          viewStateLoader: () async => _liveSegmentViewState(),
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
          competitionLabel: 'GTEX Cup',
          platformMode: GtexPlatformMode.web,
          platformController: platformController,
          viewStateLoader: () async => _liveSegmentViewState(),
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

Finder _eventOverlayText(String text) {
  return find.descendant(
    of: find.byType(GtexEventOverlay),
    matching: find.text(text),
  );
}

MatchViewState _backendAuthoredChanceViewState() {
  final MatchViewState viewState = _liveSegmentViewState();
  return viewState.copyWith(
    frames: viewState.frames
        .map((MatchTimelineFrame frame) {
          if (frame.id != 'f1') {
            return frame;
          }
          return frame.copyWith(eventBanner: 'Chance');
        })
        .toList(growable: false),
  );
}

MatchViewState _withoutBackendAuthoredOverlayViewState() {
  final MatchViewState viewState = buildBroadcastTestViewState();
  return viewState.copyWith(
    segmentEndSeconds: 3,
    frames: viewState.frames
        .map((MatchTimelineFrame frame) {
          return frame.copyWith(
            eventBanner: null,
            overlayText: null,
            homeScore: 0,
            awayScore: 0,
            injectedEvents: const <MatchTimelineInjection>[],
          );
        })
        .toList(growable: false),
  );
}

MatchViewState _liveSegmentViewState() {
  return buildBroadcastTestViewState().copyWith(segmentEndSeconds: 1);
}

MatchViewState _backendHeldBeforeChanceViewState() {
  final MatchViewState viewState = buildBroadcastTestViewState();
  final MatchEvent futureChance = viewState
      .eventById('attack-home')!
      .copyWith(timeSeconds: 2);
  final List<MatchEvent> events = viewState.events
      .map((MatchEvent event) {
        return event.id == futureChance.id ? futureChance : event;
      })
      .toList(growable: false);
  final MatchTimelineFrame heldFrame = viewState.firstFrame.copyWith(
    id: 'backend-held-before-chance',
    timeSeconds: 1,
    clockMinute: 1,
    phase: MatchViewerPhase.openPlay,
    activeEventId: null,
    eventBanner: null,
    overlayText: null,
    injectedEvents: const <MatchTimelineInjection>[],
  );
  final MatchTimelineFrame futureChanceFrame = viewState.frames[1].copyWith(
    id: 'backend-future-chance',
    timeSeconds: 2,
    activeEventId: futureChance.id,
  );

  return viewState.copyWith(
    events: events,
    segmentEndSeconds: 1,
    frames: <MatchTimelineFrame>[
      heldFrame,
      futureChanceFrame,
      viewState.lastFrame,
    ],
  );
}
