import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_ball.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_camera_viewport.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_match_canvas.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_pitch.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_player.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_players_layer.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets(
    'pseudo-3D canvas wires telemetry into pitch, camera, and actors',
    (WidgetTester tester) async {
      final viewState = buildBroadcastTestViewState();
      final MatchTimelineFrame frame = viewState.frames[2].copyWith(
        possessionPhase: MatchPossessionPhase.boxAttack,
        transitionState: MatchTransitionState.homeBreak,
        dangerZone: 'box',
        pressureIndex: 0.9,
        frameTags: const <String>['counter', 'box_entry'],
        ball: viewState.frames[2].ball.copyWith(
          position: const MatchViewerPoint(x: 84, y: 44),
          ownerPlayerId: 'home-9',
          state: 'shot',
          elevation: 2.8,
        ),
        players: viewState.frames[2].players
            .map((MatchViewerPlayerFrame player) {
              if (player.playerId == 'home-9') {
                return player.copyWith(
                  animationState: MatchPlayerAnimationState.sprint,
                  speedRatio: 0.9,
                );
              }
              return player;
            })
            .toList(growable: false),
      );
      final GtexBroadcastHudState hudState = _hudState(
        mode: GtexMatchRenderMode.cinematic,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 960,
                child: GtexPseudo3DMatchCanvas(
                  viewState: viewState,
                  frame: frame,
                  hudState: hudState,
                ),
              ),
            ),
          ),
        ),
      );

      final telemetryStyle = GtexPseudo3DMatchCanvas.describeTelemetryStyle(
        frame: frame,
        mode: hudState.mode,
      );
      final GtexPseudo3DCameraViewport viewport = tester
          .widget<GtexPseudo3DCameraViewport>(
            find.byType(GtexPseudo3DCameraViewport),
          );
      final GtexPseudo3DPitch pitch = tester.widget<GtexPseudo3DPitch>(
        find.byType(GtexPseudo3DPitch),
      );
      final GtexPseudo3DPlayersLayer playersLayer = tester
          .widget<GtexPseudo3DPlayersLayer>(
            find.byType(GtexPseudo3DPlayersLayer),
          );

      expect(viewport.zoom, greaterThan(1.14));
      expect(viewport.pan.dx, lessThan(0));
      expect(viewport.pan.dy.abs(), greaterThan(1));
      expect(
        identical(pitch.telemetryStyle, playersLayer.telemetryStyle),
        isTrue,
      );
      expect(pitch.telemetryStyle.showBoxOverlay, isTrue);
      expect(
        playersLayer.telemetryStyle.cameraZoomBias,
        telemetryStyle.cameraZoomBias,
      );

      final DecoratedBox decoratedBox = tester.widget<DecoratedBox>(
        find.byType(DecoratedBox).first,
      );
      final BoxDecoration decoration = decoratedBox.decoration as BoxDecoration;
      final LinearGradient gradient = decoration.gradient! as LinearGradient;
      expect(gradient.colors, telemetryStyle.stadiumGradient);

      expect(find.byKey(GtexPseudo3DPlayer.haloKey), findsWidgets);
      expect(find.byKey(GtexPseudo3DPlayer.badgeKey), findsWidgets);
      expect(find.byKey(GtexPseudo3DBall.trailKey), findsOneWidget);
      expect(find.byKey(GtexPseudo3DBall.haloKey), findsOneWidget);
    },
  );

  testWidgets(
    'pseudo-3D set pieces keep the ball ring but avoid a transition trail',
    (WidgetTester tester) async {
      final viewState = buildBroadcastTestViewState();
      final MatchTimelineFrame frame = viewState.frames[4].copyWith(
        possessionSide: MatchViewerSide.away,
        possessionPhase: MatchPossessionPhase.setPiece,
        transitionState: MatchTransitionState.awayReset,
        dangerZone: 'set_piece',
        pressureIndex: 0.64,
        frameTags: const <String>['set_piece'],
        ball: viewState.frames[4].ball.copyWith(
          state: 'placed',
          ownerPlayerId: 'away-9',
          elevation: 0,
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 960,
                child: GtexPseudo3DMatchCanvas(
                  viewState: viewState,
                  frame: frame,
                  hudState: _hudState(),
                ),
              ),
            ),
          ),
        ),
      );

      expect(find.byKey(GtexPseudo3DBall.ringKey), findsOneWidget);
      expect(find.byKey(GtexPseudo3DBall.trailKey), findsNothing);
      expect(find.byKey(GtexPseudo3DBall.haloKey), findsOneWidget);
    },
  );
}

GtexBroadcastHudState _hudState({
  GtexMatchRenderMode mode = GtexMatchRenderMode.standard,
}) {
  return GtexBroadcastHudState(
    clockLabel: "14'",
    statusLabel: 'Live',
    scoreMasked: false,
    controlsVisible: true,
    isPaused: false,
    speedLabel: '1x',
    mode: mode,
    viewType: GtexMatchViewType.pseudo3D,
    homeScore: 1,
    awayScore: 0,
  );
}
