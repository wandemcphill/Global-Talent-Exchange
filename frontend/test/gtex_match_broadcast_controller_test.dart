import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/controllers/gtex_match_broadcast_controller.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_event.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  test('scoreboard uses backend-authored frame scores and lock state', () {
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: _viewStatePinnedToFrame('f2', scoreRevealLocked: true),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
        );

    expect(controller.hudState.scoreMasked, isTrue);
    expect(controller.hudState.homeScore, isNull);
    expect(controller.hudState.awayScore, isNull);
    expect(controller.hudState.clockLabel, '--:--');

    final GtexMatchBroadcastController confirmedController =
        GtexMatchBroadcastController(
          viewState: _viewStatePinnedToFrame('f3'),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
        );

    expect(confirmedController.hudState.scoreMasked, isFalse);
    expect(confirmedController.hudState.homeScore, 1);
    expect(confirmedController.hudState.awayScore, 0);
  });

  test('scoreless matches reveal 0-0 from the backend full-time frame', () {
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: _viewStatePinnedToFrame('f2', scoreless: true),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
        );

    expect(controller.isFullTime, isTrue);
    expect(controller.hudState.scoreMasked, isFalse);
    expect(controller.hudState.homeScore, 0);
    expect(controller.hudState.awayScore, 0);
  });

  test('render modes do not remap the backend timeline', () {
    final viewState = buildBroadcastTestViewState();

    final GtexMatchBroadcastController quick = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.quick,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
    );
    final GtexMatchBroadcastController standard = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.standard,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
    );
    final GtexMatchBroadcastController cinematic = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.cinematic,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
    );

    expect(
      quick.modeController.targetDurationSeconds,
      viewState.durationSeconds,
    );
    expect(
      standard.modeController.targetDurationSeconds,
      viewState.durationSeconds,
    );
    expect(
      cinematic.modeController.targetDurationSeconds,
      viewState.durationSeconds,
    );
    expect(quick.modeController.viewerSecondsForAuthoritative(2.2), 2.2);
    expect(cinematic.modeController.authoritativeSecondsForViewer(2.2), 2.2);

    expect(quick.frameAtAuthoritativeSeconds(2.2).id, 'f3');
    expect(standard.frameAtAuthoritativeSeconds(2.2).id, 'f3');
    expect(cinematic.frameAtAuthoritativeSeconds(2.2).id, 'f3');
  });

  test('broadcast spectator HUD keeps gifting affordances available', () {
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: buildBroadcastTestViewState(),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
        );

    expect(controller.hudState.canGift, isTrue);
    expect(controller.hudState.showSocialRail, isTrue);
  });

  test('event overlay requires backend-authored frame overlay text', () {
    final MatchViewState viewState = _viewStatePinnedToFrame('f5');
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: viewState,
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
        );

    expect(controller.currentFrame.activeEventId, 'miss-home');
    expect(controller.hudState.eventOverlay, isNull);
    expect(controller.hudState.commentary, isNull);
    expect(controller.hudState.commentaryDetail, isNull);
  });

  test('alternate view requests resolve to the 2D broadcast state', () {
    final GtexMatchViewType legacyInput = gtexMatchViewTypeFromString('3d');
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: buildBroadcastTestViewState(),
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: legacyInput,
          isPremiumUser: true,
          spectatorMode: true,
        );

    expect(controller.viewType, GtexMatchViewType.twoD);

    controller.setViewType(gtexMatchViewTypeFromString('3d'));

    expect(controller.viewType, GtexMatchViewType.twoD);
    expect(controller.hudState.viewType, GtexMatchViewType.twoD);
  });

  test('render modes expose no viewer-only generated match beats', () {
    final viewState = buildBroadcastTestViewState();
    final GtexMatchBroadcastController quick = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.quick,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
    );
    final GtexMatchBroadcastController cinematic = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: GtexMatchRenderMode.cinematic,
      initialViewType: GtexMatchViewType.twoD,
      isPremiumUser: false,
      spectatorMode: true,
    );

    expect(quick.modeController.viewerOnlyBeats, isEmpty);
    expect(cinematic.modeController.viewerOnlyBeats, isEmpty);

    final MatchTimelineFrame quickFinalFrame = quick
        .frameAtAuthoritativeSeconds(
          quick.modeController.targetDurationSeconds.toDouble(),
        );
    final MatchTimelineFrame cinematicFinalFrame = cinematic
        .frameAtAuthoritativeSeconds(
          cinematic.modeController.targetDurationSeconds.toDouble(),
        );

    expect(quickFinalFrame.homeScore, cinematicFinalFrame.homeScore);
    expect(quickFinalFrame.awayScore, cinematicFinalFrame.awayScore);
    expect(cinematicFinalFrame.homeScore, 1);
    expect(cinematicFinalFrame.awayScore, 0);
  });

  test('VAR/disallowed presentation never commits the disallowed goal', () {
    final viewState = _viewStatePinnedToFrame('f4');
    final GtexMatchBroadcastController controller =
        GtexMatchBroadcastController(
          viewState: viewState,
          initialMode: GtexMatchRenderMode.quick,
          initialViewType: GtexMatchViewType.twoD,
          isPremiumUser: false,
          spectatorMode: true,
        );

    expect(controller.hudState.varOverlay, isNotNull);
    expect(
      controller.hudState.varOverlay!.type,
      GtexBroadcastEventType.varDisallowed,
    );
    expect(controller.hudState.homeScore, 1);
    expect(controller.hudState.awayScore, 0);
    expect(controller.currentFrame.isSynthetic, isFalse);
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
          );

      final MatchEvent goalEvent = viewState.events.firstWhere(
        (MatchEvent event) => event.id == 'goal-home',
      );
      final preConfirmationFrame = controller.frameAtAuthoritativeSeconds(
        goalEvent.timeSeconds,
      );
      final confirmedFrame = controller.frameAtAuthoritativeSeconds(2.2);

      expect(preConfirmationFrame.id, 'f1');
      expect(preConfirmationFrame.isSynthetic, isFalse);
      expect(confirmedFrame.id, 'f3');
      expect(confirmedFrame.activeEventId, 'goal-home');
      expect(confirmedFrame.isSynthetic, isFalse);
      expect(
        confirmedFrame.players.map((player) => player.playerId),
        contains('home-9'),
      );
      expect(controller.viewState.homeTeam.teamName, 'Lagos Stars');
    },
  );
}

MatchViewState _viewStatePinnedToFrame(
  String frameId, {
  bool scoreRevealLocked = false,
  bool scoreless = false,
}) {
  final MatchViewState viewState = buildBroadcastTestViewState(
    scoreless: scoreless,
  );
  final MatchTimelineFrame frame = viewState.frames.firstWhere(
    (MatchTimelineFrame frame) => frame.id == frameId,
  );
  return viewState.copyWith(
    frames: <MatchTimelineFrame>[frame],
    durationSeconds: frame.timeSeconds.ceil(),
    segmentEndSeconds: frame.timeSeconds.ceil(),
    scoreRevealLocked: scoreRevealLocked,
  );
}
