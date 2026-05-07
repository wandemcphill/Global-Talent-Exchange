import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/match/gtex_match_broadcast_controller.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_event.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_event.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test('scoreboard stays masked until a goal is confirmed', () {
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: buildBroadcastTestViewState(),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
        );

    expect(controller.hudState.scoreMasked, isTrue);

    final double revealViewerSeconds =
        controller.modeController.viewerSecondsForAuthoritative(1) + 1.15;

    controller.advanceBy(
      Duration(milliseconds: ((revealViewerSeconds - 0.4) * 1000).round()),
    );
    expect(controller.hudState.scoreMasked, isTrue);

    controller.advanceBy(const Duration(milliseconds: 500));
    expect(controller.hudState.scoreMasked, isFalse);
    expect(controller.hudState.homeScore, 1);
    expect(controller.hudState.awayScore, 0);
  });

  test('scoreless matches reveal 0-0 only at full time', () {
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: buildBroadcastTestViewState(scoreless: true),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
        );

    expect(controller.hudState.scoreMasked, isTrue);

    controller.advanceBy(
      Duration(seconds: controller.modeController.targetDurationSeconds),
    );

    expect(controller.isFullTime, isTrue);
    expect(controller.hudState.scoreMasked, isFalse);
    expect(controller.hudState.homeScore, 0);
    expect(controller.hudState.awayScore, 0);
  });

  test('mode pacing stays within locked broadcast windows', () {
    final viewState = buildBroadcastTestViewState();

    final GtexMatchBroadcastController quick = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.quick,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
      auto3DEnabled: false,
    );
    final GtexMatchBroadcastController standard = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.standard,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
      auto3DEnabled: false,
    );
    final GtexMatchBroadcastController cinematic = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.cinematic,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
      auto3DEnabled: false,
    );

    expect(
      quick.modeController.targetDurationSeconds,
      inInclusiveRange(180, 300),
    );
    expect(
      standard.modeController.targetDurationSeconds,
      inInclusiveRange(420, 600),
    );
    expect(
      cinematic.modeController.targetDurationSeconds,
      inInclusiveRange(600, 900),
    );
    expect(
      quick.modeController.targetDurationSeconds,
      lessThan(standard.modeController.targetDurationSeconds),
    );
    expect(
      standard.modeController.targetDurationSeconds,
      lessThan(cinematic.modeController.targetDurationSeconds),
    );
  });

  test('broadcast spectator HUD exposes gifting affordances', () {
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: buildBroadcastTestViewState(),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
        );

    expect(controller.hudState.canGift, isTrue);
    expect(controller.hudState.showSocialRail, isTrue);
  });

  test(
    'cinematic viewer-only beats do not change the authoritative outcome',
    () {
      final viewState = buildBroadcastTestViewState();
      final GtexMatchBroadcastController quick = GtexMatchBroadcastController(
        viewState: viewState,
        initialMode: GtexMatchRenderMode.quick,
        initialViewType: GtexMatchViewType.twoD,
        isPremiumUser: false,
        spectatorMode: true,
        auto3DEnabled: false,
      );
      final GtexMatchBroadcastController cinematic =
          GtexMatchBroadcastController(
            viewState: viewState,
            initialMode: GtexMatchRenderMode.cinematic,
            initialViewType: GtexMatchViewType.twoD,
            isPremiumUser: false,
            spectatorMode: true,
            auto3DEnabled: false,
          );

      expect(quick.modeController.viewerOnlyBeats, isEmpty);
      expect(cinematic.modeController.viewerOnlyBeats, isNotEmpty);

      quick.advanceBy(
        Duration(seconds: quick.modeController.targetDurationSeconds),
      );
      cinematic.advanceBy(
        Duration(seconds: cinematic.modeController.targetDurationSeconds),
      );

      expect(quick.hudState.homeScore, cinematic.hudState.homeScore);
      expect(quick.hudState.awayScore, cinematic.hudState.awayScore);
      expect(cinematic.hudState.homeScore, 1);
      expect(cinematic.hudState.awayScore, 0);
    },
  );

  test('VAR/disallowed presentation never commits the disallowed goal', () {
    final viewState = buildBroadcastTestViewState();
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: viewState,
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
          auto3DEnabled: false,
        );

    final double disallowedViewerSeconds =
        controller.modeController.viewerSecondsForAuthoritative(2.8) + 1.0;
    controller.advanceBy(
      Duration(milliseconds: (disallowedViewerSeconds * 1000).round()),
    );

    expect(controller.hudState.varOverlay, isNotNull);
    expect(
      controller.hudState.varOverlay!.type,
      anyOf(
        GtexBroadcastEventType.varChecking,
        GtexBroadcastEventType.varDisallowed,
      ),
    );
    expect(controller.hudState.homeScore, 1);
    expect(controller.hudState.awayScore, 0);
    expect(viewState.lastFrame.homeScore, 1);
    expect(viewState.lastFrame.awayScore, 0);
  });

  test(
    'broadcast controller stays on existing viewer contracts for frame data',
    () {
      final viewState = buildBroadcastTestViewState();
      final GtexMatchBroadcastController controller =
          GtexMatchBroadcastController(
            viewState: viewState,
            initialMode: GtexMatchRenderMode.quick,
            initialViewType: GtexMatchViewType.twoD,
            isPremiumUser: false,
            spectatorMode: true,
            auto3DEnabled: false,
          );

      final MatchEvent goalEvent = viewState.events.firstWhere(
        (MatchEvent event) => event.id == 'goal-home',
      );
      final frame = controller.frameAtAuthoritativeSeconds(
        goalEvent.timeSeconds,
      );

      expect(frame.activeEventId, anyOf('attack-home', 'goal-home'));
      expect(
        frame.players.map((player) => player.playerId),
        contains('home-9'),
      );
      expect(controller.viewState.homeTeam.teamName, 'Lagos Stars');
    },
  );
}
