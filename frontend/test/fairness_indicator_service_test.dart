import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/fairness_indicator_service.dart';
import 'package:gte_frontend/widgets/match/fairness_badge.dart';

void main() {
  test('visible timeline hash is deterministic 32-bit hex', () {
    final MatchViewState baseState = _buildViewState();

    final String firstHash =
        FairnessIndicatorService.computeVisibleTimelineHash(baseState);
    final String secondHash =
        FairnessIndicatorService.computeVisibleTimelineHash(baseState);
    final String changedHash =
        FairnessIndicatorService.computeVisibleTimelineHash(
      baseState.copyWith(durationSeconds: baseState.durationSeconds + 1),
    );

    expect(firstHash, secondHash);
    expect(firstHash, matches(RegExp(r'^[0-9a-f]{8}$')));
    expect(changedHash, isNot(firstHash));
  });

  test('fairness indicator verifies a matching visible timeline proof', () {
    final MatchViewState baseState = _buildViewState();
    final MatchViewState verifiedState = baseState.copyWith(
      fairnessIndicator: const MatchFairnessIndicator(
        status: MatchVerificationStatus.verified,
        label: 'Fair Play Verified',
      ),
      timelineProof: MatchTimelineProof(
        status: MatchVerificationStatus.verified,
        visibleTimelineHash:
            FairnessIndicatorService.computeVisibleTimelineHash(baseState),
      ),
    );

    expect(
      FairnessIndicatorService.verify(verifiedState),
      MatchVerificationStatus.verified,
    );
  });

  test('fairness indicator marks mismatched proof as tampered', () {
    final MatchViewState baseState = _buildViewState().copyWith(
      fairnessIndicator: const MatchFairnessIndicator(
        status: MatchVerificationStatus.verified,
        label: 'Fair Play Verified',
      ),
      timelineProof: const MatchTimelineProof(
        status: MatchVerificationStatus.verified,
        visibleTimelineHash: 'deadbeef',
      ),
    );

    expect(
      FairnessIndicatorService.verify(baseState),
      MatchVerificationStatus.tampered,
    );
  });

  testWidgets('fairness badge renders the verified label',
      (WidgetTester tester) async {
    final MatchViewState baseState = _buildViewState();
    final MatchViewState verifiedState = baseState.copyWith(
      fairnessIndicator: const MatchFairnessIndicator(
        status: MatchVerificationStatus.verified,
        label: 'Fair Play Verified',
      ),
      timelineProof: MatchTimelineProof(
        status: MatchVerificationStatus.verified,
        visibleTimelineHash:
            FairnessIndicatorService.computeVisibleTimelineHash(baseState),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: FairnessBadge(viewState: verifiedState),
        ),
      ),
    );

    expect(find.text('Fair Play Verified'), findsOneWidget);
  });
}

MatchViewState _buildViewState() {
  const MatchViewerPlayerFrame homePlayer = MatchViewerPlayerFrame(
    playerId: 'home-9',
    teamId: 'home',
    side: MatchViewerSide.home,
    shirtNumber: 9,
    label: '9',
    role: MatchViewerRole.forward,
    line: MatchPlayerLine.attack,
    state: MatchViewerPlayerState.attacking,
    active: true,
    highlighted: true,
    position: MatchViewerPoint(x: 24, y: 48),
    anchorPosition: MatchViewerPoint(x: 20, y: 48),
  );
  const MatchViewerPlayerFrame awayPlayer = MatchViewerPlayerFrame(
    playerId: 'away-1',
    teamId: 'away',
    side: MatchViewerSide.away,
    shirtNumber: 1,
    label: '1',
    role: MatchViewerRole.goalkeeper,
    line: MatchPlayerLine.goalkeeper,
    state: MatchViewerPlayerState.defending,
    active: true,
    highlighted: false,
    position: MatchViewerPoint(x: 82, y: 50),
    anchorPosition: MatchViewerPoint(x: 84, y: 50),
  );
  final MatchTimelineFrame frame = MatchTimelineFrame(
    id: 'frame-1',
    timeSeconds: 12,
    clockMinute: 9,
    phase: MatchViewerPhase.openPlay,
    homeScore: 1,
    awayScore: 0,
    homeAttacksRight: true,
    possessionSide: MatchViewerSide.home,
    activeEventId: 'goal-1',
    eventBanner: 'Goal!',
    players: const <MatchViewerPlayerFrame>[homePlayer, awayPlayer],
    ball: const MatchViewerBallFrame(
      position: MatchViewerPoint(x: 26, y: 49),
      ownerPlayerId: 'home-9',
      state: 'rolling',
    ),
  );
  final MatchEvent event = MatchEvent(
    id: 'goal-1',
    sequence: 1,
    type: MatchViewerEventType.goal,
    minute: 9,
    addedTime: 0,
    clockLabel: "9'",
    timeSeconds: 12,
    homeScore: 1,
    awayScore: 0,
    bannerText: 'Goal!',
    commentary: 'Home side strikes first.',
    emphasisLevel: 3,
    highlightedPlayerIds: const <String>['home-9'],
    flags: const <String>[],
    teamId: 'home',
    teamName: 'Home',
    primaryPlayerId: 'home-9',
    primaryPlayerName: 'Home Nine',
  );
  return MatchViewState(
    matchId: 'match-1',
    source: 'session',
    supportsOffside: true,
    durationSeconds: 120,
    homeTeam: const MatchViewerTeam(
      teamId: 'home',
      teamName: 'Home',
      shortName: 'HOM',
      side: MatchViewerSide.home,
      formation: '4-3-3',
      primaryColorHex: '#173F7A',
      secondaryColorHex: '#F4F7FB',
      accentColorHex: '#F59E0B',
      goalkeeperColorHex: '#0F172A',
    ),
    awayTeam: const MatchViewerTeam(
      teamId: 'away',
      teamName: 'Away',
      shortName: 'AWY',
      side: MatchViewerSide.away,
      formation: '4-3-3',
      primaryColorHex: '#B42318',
      secondaryColorHex: '#FFF3F2',
      accentColorHex: '#FDB022',
      goalkeeperColorHex: '#111827',
    ),
    events: <MatchEvent>[event],
    frames: <MatchTimelineFrame>[frame],
  );
}
