import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_broadcast_presentation.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  test('large frame gaps snap to the nearest authoritative frame', () {
    final MatchViewerPlayerFrame leftPlayer = MatchViewerPlayerFrame(
      playerId: 'home-9',
      teamId: 'home',
      side: MatchViewerSide.home,
      shirtNumber: 9,
      label: '9',
      role: MatchViewerRole.forward,
      line: MatchPlayerLine.attack,
      state: MatchViewerPlayerState.attacking,
      active: true,
      highlighted: false,
      position: const MatchViewerPoint(x: 24, y: 44),
      anchorPosition: const MatchViewerPoint(x: 20, y: 44),
    );
    final MatchViewerPlayerFrame rightPlayer = leftPlayer.copyWith(
      position: const MatchViewerPoint(x: 78, y: 56),
      anchorPosition: const MatchViewerPoint(x: 76, y: 56),
    );
    final MatchTimelineFrame leftFrame = MatchTimelineFrame(
      id: 'left',
      timeSeconds: 0,
      clockMinute: 10,
      phase: MatchViewerPhase.openPlay,
      homeScore: 0,
      awayScore: 0,
      homeAttacksRight: true,
      possessionSide: MatchViewerSide.home,
      players: <MatchViewerPlayerFrame>[leftPlayer],
      ball: const MatchViewerBallFrame(
        position: MatchViewerPoint(x: 25, y: 45),
        ownerPlayerId: 'home-9',
        state: 'rolling',
      ),
    );
    final MatchTimelineFrame rightFrame = MatchTimelineFrame(
      id: 'right',
      timeSeconds: 6,
      clockMinute: 11,
      phase: MatchViewerPhase.openPlay,
      homeScore: 0,
      awayScore: 0,
      homeAttacksRight: true,
      possessionSide: MatchViewerSide.away,
      players: <MatchViewerPlayerFrame>[rightPlayer],
      ball: const MatchViewerBallFrame(
        position: MatchViewerPoint(x: 77, y: 55),
        ownerPlayerId: 'away-6',
        state: 'rolling',
      ),
    );

    final MatchTimelineFrame early = leftFrame.interpolate(rightFrame, 0.35);
    final MatchTimelineFrame late = leftFrame.interpolate(rightFrame, 0.75);

    expect(early.id, 'left');
    expect(early.players.first.position.x, 24);
    expect(late.id, 'right');
    expect(late.players.first.position.x, 78);
  });

  test('fallback viewer preserves live player references when available',
      () async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-viewer-player-refs',
    );
    final LiveMatchSnapshot baseSnapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );
    final List<LiveMatchLineupPlayer> homeLineup =
        List<LiveMatchLineupPlayer>.from(baseSnapshot.homeLineup);
    homeLineup[0] = const LiveMatchLineupPlayer(
      playerId: 'player-9',
      name: 'Canonical Forward',
      position: 'ST',
      rating: 7.4,
      avatarSeedToken: 'canonical-forward-seed',
    );
    final LiveMatchSnapshot snapshot = LiveMatchSnapshot(
      matchId: baseSnapshot.matchId,
      halftimeAnalyticsAvailable: baseSnapshot.halftimeAnalyticsAvailable,
      highlightsAvailable: baseSnapshot.highlightsAvailable,
      keyMomentsAvailable: baseSnapshot.keyMomentsAvailable,
      homeTeam: baseSnapshot.homeTeam,
      awayTeam: baseSnapshot.awayTeam,
      homeScore: baseSnapshot.homeScore,
      awayScore: baseSnapshot.awayScore,
      minute: baseSnapshot.minute,
      phase: baseSnapshot.phase,
      momentum: baseSnapshot.momentum,
      commentary: baseSnapshot.commentary,
      homeLineup: homeLineup,
      awayLineup: baseSnapshot.awayLineup,
      substitutions: baseSnapshot.substitutions,
      cards: baseSnapshot.cards,
      tacticalSuggestions: baseSnapshot.tacticalSuggestions,
      keyMoments: baseSnapshot.keyMoments,
      highlights: baseSnapshot.highlights,
      standardHighlightExpiresAt: baseSnapshot.standardHighlightExpiresAt,
      premiumHighlightExpiresAt: baseSnapshot.premiumHighlightExpiresAt,
    );

    final MatchViewState viewState = await MatchViewerMapper.load(
      competition: competition,
      matchKey: competition.id,
      fallbackSnapshot: snapshot,
      preferFallback: true,
    );
    final MatchViewerPlayerFrame homePlayer = viewState.firstFrame.players
        .firstWhere((MatchViewerPlayerFrame player) => player.teamId == 'home');

    expect(homePlayer.playerId, 'player-9');
  });

  testWidgets('replay viewer renders controls and replay rail',
      (WidgetTester tester) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-viewer-test',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
          renderMode: RenderMode.twoD,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    expect(find.text('2D Match Viewer'), findsOneWidget);
    expect(find.text('Restart'), findsOneWidget);
    expect(find.text('Next event'), findsOneWidget);
    await _pumpUntilVisible(tester, find.text('Replay lane'));

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets('replay viewer stays usable in a narrow layout', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(360, 780));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final CompetitionSummary competition = _buildCompetition(
      id: 'match-viewer-narrow-test',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
          renderMode: RenderMode.twoD,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    expect(find.text('Restart'), findsOneWidget);
    expect(find.text('Next event'), findsOneWidget);
    await _pumpUntilVisible(tester, find.text('Replay lane'));
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets('replay viewer pauses and resumes safely across app lifecycle',
      (WidgetTester tester) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-viewer-lifecycle-test',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          fallbackSnapshot: snapshot,
          preferFallback: true,
          renderMode: RenderMode.twoD,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));
    await _pumpUntilVisible(tester, find.text('Pause'));

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump();

    expect(find.text('Play'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 900));
    expect(find.text('Play'), findsOneWidget);

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();

    expect(find.text('Pause'), findsOneWidget);
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets(
      'broadcast viewer shows intro, live clock, masked score, and commentary',
      (WidgetTester tester) async {
    final MatchViewState viewState = _buildBroadcastViewState();
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: _buildCompetition(
            id: 'broadcast-match-viewer',
            status: CompetitionStatus.inProgress,
          ),
          matchKey: 'broadcast-match-viewer',
          presentationMode: MatchViewerPresentationMode.broadcast,
          entitlement: const Match3dUserEntitlement(isPremiumUser: true),
          viewStateLoader: () async => viewState,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    expect(find.text('Live broadcast'), findsOneWidget);
    expect(find.text('0:00'), findsOneWidget);
    expect(find.text('--'), findsNWidgets(2));
    expect(find.textContaining('Gift'), findsNothing);
    expect(find.text('Pro Manager'), findsNothing);

    await tester.pump(const Duration(seconds: 1));
    expect(find.text('Match starting...'), findsOneWidget);

    await tester.pump(const Duration(seconds: 1));
    expect(find.text('Formation 4-3-3'), findsNWidgets(2));

    await tester.pump(const Duration(milliseconds: 3800));
    expect(find.text('Match starting...'), findsNothing);
    expect(find.text('Formation 4-3-3'), findsNothing);
    expect(find.text('--'), findsNWidgets(2));

    await _pumpUntilVisible(tester, find.text('VAR checking...'));
    expect(find.text('--'), findsNWidgets(2));

    await _pumpUntilVisible(tester, find.text('Goal!'));
    expect(find.text('--'), findsNothing);

    await tester.pump(const Duration(milliseconds: 700));
    await _pumpUntilVisible(
      tester,
      find.text('VAR checking...'),
      timeout: const Duration(seconds: 2),
    );

    await _pumpUntilVisible(tester, find.text('Offside!'));

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  test('scoreless broadcast state stays masked until full time', () {
    final MatchViewState viewState = _buildScorelessBroadcastViewState();
    final MatchBroadcastPresentationState early =
        MatchBroadcastPresentationBuilder.fromPlayback(
      viewState: viewState,
      positionSeconds: 0,
      displayFrame: viewState.frames.first,
      leftFrame: viewState.frames.first,
      rightFrame: viewState.frames[1],
      interpolationT: 0,
      activeEvent: viewState.eventById('kickoff'),
    );
    final MatchBroadcastPresentationState late =
        MatchBroadcastPresentationBuilder.fromPlayback(
      viewState: viewState,
      positionSeconds: 8,
      displayFrame: viewState.frames.last,
      leftFrame: viewState.frames[1],
      rightFrame: viewState.frames.last,
      interpolationT: 1,
      activeEvent: viewState.eventById('fulltime'),
    );

    expect(early.scoreMasked, isTrue);
    expect(late.scoreMasked, isFalse);
    expect(late.visibleHomeScore, 0);
    expect(late.visibleAwayScore, 0);
  });

  test(
      'broadcast presentation camera and movement variation are deterministic and bounded',
      () {
    final MatchViewState viewState = _buildBroadcastViewState();
    final MatchTimelineFrame leftFrame = viewState.frames[2];
    final MatchTimelineFrame rightFrame = viewState.frames[3];
    final MatchTimelineFrame displayFrame = leftFrame.interpolate(
      rightFrame,
      0.5,
    );
    final MatchBroadcastPresentationState presentation =
        MatchBroadcastPresentationBuilder.fromPlayback(
      viewState: viewState,
      positionSeconds: 7.25,
      displayFrame: displayFrame,
      leftFrame: leftFrame,
      rightFrame: rightFrame,
      interpolationT: 0.5,
      activeEvent: viewState.eventById('goal-1'),
    );

    final MatchViewerPoint varied = presentation.pitchPresentation
        .resolvePlayerPosition(displayFrame.players.first);
    final double distance = math.sqrt(
      math.pow(varied.x - displayFrame.players.first.position.x, 2) +
          math.pow(varied.y - displayFrame.players.first.position.y, 2),
    );

    expect(
      presentation.pitchPresentation.cameraPreset,
      BroadcastCameraPreset.replayCamera,
    );
    expect(distance, lessThanOrEqualTo(1.5));
    expect(presentation.pitchPresentation.panX.abs(), lessThanOrEqualTo(0.12));
    expect(presentation.pitchPresentation.panY.abs(), lessThanOrEqualTo(0.08));
  });

  testWidgets('continuation retries once after a delayed chunk failure', (
    WidgetTester tester,
  ) async {
    int continuationCalls = 0;
    final MatchViewState initialState = _buildSegmentedReplayState(
      durationSeconds: 1,
      source: 'segment-1',
      hasMoreSegments: true,
      nextSegmentToken: 'segment-2-token',
      finalPhase: MatchViewerPhase.openPlay,
    );
    final MatchViewState continuedState = _buildSegmentedReplayState(
      durationSeconds: 2,
      source: 'segment-2',
      hasMoreSegments: false,
      nextSegmentToken: null,
      finalPhase: MatchViewerPhase.fulltime,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: _buildCompetition(id: 'continued-replay'),
          matchKey: 'continued-replay',
          renderMode: RenderMode.twoD,
          viewStateLoader: () async => initialState,
          continuationLoader: ({
            required String matchKey,
            required String continuationToken,
          }) async {
            continuationCalls += 1;
            if (continuationCalls == 1) {
              throw StateError('temporary continuation failure');
            }
            return continuedState;
          },
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));
    await _pumpUntilVisible(tester, find.textContaining('Duration: 1s'));

    await tester.pump(const Duration(milliseconds: 1200));
    expect(continuationCalls, 1);
    expect(find.text('Segment delayed. Retrying playback...'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 1200));
    await tester.pump();

    expect(continuationCalls, 2);
    expect(find.textContaining('Duration: 2s'), findsOneWidget);
    expect(find.text('Segment delayed. Retrying playback...'), findsNothing);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets('viewer remains stable across back-to-back replay loads',
      (WidgetTester tester) async {
    final CompetitionSummary firstCompetition = _buildCompetition(
      id: 'match-viewer-first',
    );
    final CompetitionSummary secondCompetition = _buildCompetition(
      id: 'match-viewer-second',
    );
    final LiveMatchSnapshot firstSnapshot = _snapshotWithTeams(
      competition: firstCompetition,
      homeTeam: 'Alpha',
      awayTeam: 'Beta',
    );
    final LiveMatchSnapshot secondSnapshot = _snapshotWithTeams(
      competition: secondCompetition,
      homeTeam: 'Gamma',
      awayTeam: 'Delta',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: firstCompetition,
          matchKey: firstCompetition.id,
          fallbackSnapshot: firstSnapshot,
          preferFallback: true,
          renderMode: RenderMode.twoD,
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 48));
    await _pumpUntilVisible(tester, find.text('Replay lane'));
    expect(find.text('ALP'), findsOneWidget);
    expect(find.text('BET'), findsOneWidget);

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: secondCompetition,
          matchKey: secondCompetition.id,
          fallbackSnapshot: secondSnapshot,
          preferFallback: true,
          renderMode: RenderMode.twoD,
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 48));

    expect(find.text('2D Match Viewer'), findsOneWidget);
    await _pumpUntilVisible(tester, find.text('Replay lane'));
    expect(find.text('GAM'), findsOneWidget);
    expect(find.text('DEL'), findsOneWidget);
    expect(find.text('ALP'), findsNothing);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });
}

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  Duration step = const Duration(milliseconds: 100),
  Duration timeout = const Duration(seconds: 3),
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

CompetitionSummary _buildCompetition({
  required String id,
  CompetitionStatus status = CompetitionStatus.completed,
}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX Replay Test',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: status,
    creatorId: 'creator-1',
    creatorName: 'GTEX',
    participantCount: 8,
    capacity: 8,
    currency: 'USD',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Replay validation fixture',
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}

LiveMatchSnapshot _snapshotWithTeams({
  required CompetitionSummary competition,
  required String homeTeam,
  required String awayTeam,
}) {
  final LiveMatchSnapshot base = LiveMatchFixtures.buildSnapshot(competition);
  return LiveMatchSnapshot(
    matchId: base.matchId,
    halftimeAnalyticsAvailable: base.halftimeAnalyticsAvailable,
    highlightsAvailable: base.highlightsAvailable,
    keyMomentsAvailable: base.keyMomentsAvailable,
    homeTeam: homeTeam,
    awayTeam: awayTeam,
    homeScore: base.homeScore,
    awayScore: base.awayScore,
    minute: base.minute,
    phase: base.phase,
    momentum: base.momentum,
    commentary: base.commentary,
    homeLineup: base.homeLineup,
    awayLineup: base.awayLineup,
    substitutions: base.substitutions,
    cards: base.cards,
    tacticalSuggestions: base.tacticalSuggestions,
    keyMoments: base.keyMoments,
    highlights: base.highlights,
    standardHighlightExpiresAt: base.standardHighlightExpiresAt,
    premiumHighlightExpiresAt: base.premiumHighlightExpiresAt,
  );
}

MatchViewState _buildSegmentedReplayState({
  required int durationSeconds,
  required String source,
  required bool hasMoreSegments,
  required String? nextSegmentToken,
  required MatchViewerPhase finalPhase,
}) {
  return MatchViewState(
    matchId: 'continued-replay',
    source: source,
    supportsOffside: true,
    durationSeconds: durationSeconds,
    homeTeam: _buildTeam(
      teamId: 'home',
      name: 'Northbridge',
      shortName: 'NOR',
      side: MatchViewerSide.home,
    ),
    awayTeam: _buildTeam(
      teamId: 'away',
      name: 'Southfield',
      shortName: 'SOU',
      side: MatchViewerSide.away,
    ),
    events: <MatchEvent>[
      const MatchEvent(
        id: 'kickoff',
        sequence: 0,
        type: MatchViewerEventType.kickoff,
        minute: 0,
        addedTime: 0,
        clockLabel: '0\'',
        timeSeconds: 0,
        homeScore: 0,
        awayScore: 0,
        bannerText: 'Kickoff',
        commentary: 'The match is underway.',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
      MatchEvent(
        id: 'segment-marker-$source',
        sequence: 1,
        type: MatchViewerEventType.attack,
        minute: durationSeconds * 10,
        addedTime: 0,
        clockLabel: "${durationSeconds * 10}'",
        timeSeconds: math.max(0.55, durationSeconds - 0.15).toDouble(),
        homeScore: 0,
        awayScore: 0,
        bannerText: 'Segment marker',
        commentary: 'Marker for $source',
        emphasisLevel: 1,
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
    ],
    frames: <MatchTimelineFrame>[
      _buildFrame(
        id: '$source-frame-0',
        timeSeconds: 0,
        clockMinute: 0,
        phase: MatchViewerPhase.kickoff,
        homeScore: 0,
        awayScore: 0,
        homeShiftX: 0,
        awayShiftX: 0,
        ball: const MatchViewerPoint(x: 50, y: 50),
        activeEventId: 'kickoff',
      ),
      _buildFrame(
        id: '$source-frame-end',
        timeSeconds: durationSeconds.toDouble(),
        clockMinute: durationSeconds * 10,
        phase: finalPhase,
        homeScore: 0,
        awayScore: 0,
        homeShiftX: 3,
        awayShiftX: -3,
        ball: const MatchViewerPoint(x: 62, y: 44),
        activeEventId: 'segment-marker-$source',
      ),
    ],
    hasMoreSegments: hasMoreSegments,
    nextSegmentToken: nextSegmentToken,
    segmentEndSeconds: durationSeconds,
  );
}

MatchViewState _buildBroadcastViewState() {
  final MatchViewerTeam homeTeam = _buildTeam(
    teamId: 'home',
    name: 'Northbridge',
    shortName: 'NOR',
    side: MatchViewerSide.home,
  );
  final MatchViewerTeam awayTeam = _buildTeam(
    teamId: 'away',
    name: 'Southfield',
    shortName: 'SOU',
    side: MatchViewerSide.away,
  );

  return MatchViewState(
    matchId: 'broadcast-view-state',
    source: 'fixture',
    supportsOffside: true,
    deterministicSeed: 42,
    durationSeconds: 11,
    homeTeam: homeTeam,
    awayTeam: awayTeam,
    events: <MatchEvent>[
      const MatchEvent(
        id: 'kickoff',
        sequence: 0,
        type: MatchViewerEventType.kickoff,
        minute: 0,
        addedTime: 0,
        clockLabel: '0\'',
        timeSeconds: 0,
        homeScore: 0,
        awayScore: 0,
        bannerText: 'Kickoff',
        commentary: 'The match is underway.',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
      const MatchEvent(
        id: 'goal-1',
        sequence: 1,
        type: MatchViewerEventType.goal,
        minute: 12,
        addedTime: 0,
        clockLabel: '12\'',
        timeSeconds: 6.2,
        teamId: 'home',
        teamName: 'Northbridge',
        primaryPlayerId: 'home-9',
        primaryPlayerName: '9',
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Northbridge score',
        commentary: 'Northbridge break the line and finish low.',
        emphasisLevel: 3,
        reviewable: true,
        reviewDecision: 'confirmed',
        scoreCommit: 'after_review',
        highlightedPlayerIds: <String>['home-9'],
        flags: <String>[],
      ),
      const MatchEvent(
        id: 'offside-1',
        sequence: 2,
        type: MatchViewerEventType.offside,
        minute: 18,
        addedTime: 0,
        clockLabel: '18\'',
        timeSeconds: 8.3,
        teamId: 'away',
        teamName: 'Southfield',
        primaryPlayerId: 'away-9',
        primaryPlayerName: '9',
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Offside',
        commentary: 'Southfield almost answer, but the flag saves Northbridge.',
        emphasisLevel: 2,
        reviewable: true,
        reviewDecision: 'disallowed',
        highlightedPlayerIds: <String>['away-9'],
        flags: <String>[],
      ),
      const MatchEvent(
        id: 'fulltime',
        sequence: 3,
        type: MatchViewerEventType.fulltime,
        minute: 90,
        addedTime: 0,
        clockLabel: '90\'',
        timeSeconds: 11,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Fulltime',
        commentary: 'Northbridge close it out.',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
    ],
    frames: <MatchTimelineFrame>[
      _buildFrame(
        id: 'frame-0',
        timeSeconds: 0,
        clockMinute: 0,
        phase: MatchViewerPhase.kickoff,
        homeScore: 0,
        awayScore: 0,
        homeShiftX: 0,
        awayShiftX: 0,
        ball: const MatchViewerPoint(x: 50, y: 50),
        activeEventId: 'kickoff',
      ),
      _buildFrame(
        id: 'frame-1',
        timeSeconds: 2.6,
        clockMinute: 5,
        phase: MatchViewerPhase.openPlay,
        homeScore: 0,
        awayScore: 0,
        homeShiftX: 1.4,
        awayShiftX: -0.8,
        ball: const MatchViewerPoint(x: 56, y: 46),
      ),
      _buildFrame(
        id: 'frame-2',
        timeSeconds: 6.2,
        clockMinute: 12,
        phase: MatchViewerPhase.openPlay,
        homeScore: 1,
        awayScore: 0,
        homeShiftX: 5.2,
        awayShiftX: -2.6,
        ball: const MatchViewerPoint(x: 82, y: 48),
        activeEventId: 'goal-1',
        cameraPreset: MatchCameraPreset.goalCelebration,
      ),
      _buildFrame(
        id: 'frame-3',
        timeSeconds: 7.8,
        clockMinute: 15,
        phase: MatchViewerPhase.openPlay,
        homeScore: 1,
        awayScore: 0,
        homeShiftX: 3.4,
        awayShiftX: -1.2,
        ball: const MatchViewerPoint(x: 62, y: 55),
      ),
      _buildFrame(
        id: 'frame-4',
        timeSeconds: 8.3,
        clockMinute: 18,
        phase: MatchViewerPhase.openPlay,
        homeScore: 1,
        awayScore: 0,
        homeShiftX: 2.0,
        awayShiftX: 4.5,
        ball: const MatchViewerPoint(x: 24, y: 42),
        activeEventId: 'offside-1',
        cameraPreset: MatchCameraPreset.assistantFlag,
      ),
      _buildFrame(
        id: 'frame-5',
        timeSeconds: 11,
        clockMinute: 90,
        phase: MatchViewerPhase.fulltime,
        homeScore: 1,
        awayScore: 0,
        homeShiftX: 0.4,
        awayShiftX: 0.2,
        ball: const MatchViewerPoint(x: 50, y: 50),
        activeEventId: 'fulltime',
      ),
    ],
  );
}

MatchViewState _buildScorelessBroadcastViewState() {
  return MatchViewState(
    matchId: 'scoreless-broadcast-view-state',
    source: 'fixture',
    supportsOffside: true,
    deterministicSeed: 7,
    durationSeconds: 8,
    homeTeam: _buildTeam(
      teamId: 'home',
      name: 'Northbridge',
      shortName: 'NOR',
      side: MatchViewerSide.home,
    ),
    awayTeam: _buildTeam(
      teamId: 'away',
      name: 'Southfield',
      shortName: 'SOU',
      side: MatchViewerSide.away,
    ),
    events: const <MatchEvent>[
      MatchEvent(
        id: 'kickoff',
        sequence: 0,
        type: MatchViewerEventType.kickoff,
        minute: 0,
        addedTime: 0,
        clockLabel: '0\'',
        timeSeconds: 0,
        homeScore: 0,
        awayScore: 0,
        bannerText: 'Kickoff',
        commentary: 'The match is underway.',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
      MatchEvent(
        id: 'fulltime',
        sequence: 1,
        type: MatchViewerEventType.fulltime,
        minute: 90,
        addedTime: 0,
        clockLabel: '90\'',
        timeSeconds: 8,
        homeScore: 0,
        awayScore: 0,
        bannerText: 'Fulltime',
        commentary: 'It finishes goalless.',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
    ],
    frames: <MatchTimelineFrame>[
      _buildFrame(
        id: 'scoreless-0',
        timeSeconds: 0,
        clockMinute: 0,
        phase: MatchViewerPhase.kickoff,
        homeScore: 0,
        awayScore: 0,
        homeShiftX: 0,
        awayShiftX: 0,
        ball: const MatchViewerPoint(x: 50, y: 50),
        activeEventId: 'kickoff',
      ),
      _buildFrame(
        id: 'scoreless-1',
        timeSeconds: 4,
        clockMinute: 45,
        phase: MatchViewerPhase.openPlay,
        homeScore: 0,
        awayScore: 0,
        homeShiftX: 1.2,
        awayShiftX: -1.2,
        ball: const MatchViewerPoint(x: 54, y: 48),
      ),
      _buildFrame(
        id: 'scoreless-2',
        timeSeconds: 8,
        clockMinute: 90,
        phase: MatchViewerPhase.fulltime,
        homeScore: 0,
        awayScore: 0,
        homeShiftX: 0.4,
        awayShiftX: 0.6,
        ball: const MatchViewerPoint(x: 50, y: 50),
        activeEventId: 'fulltime',
      ),
    ],
  );
}

MatchViewerTeam _buildTeam({
  required String teamId,
  required String name,
  required String shortName,
  required MatchViewerSide side,
}) {
  return MatchViewerTeam(
    teamId: teamId,
    teamName: name,
    shortName: shortName,
    side: side,
    formation: '4-3-3',
    primaryColorHex: side == MatchViewerSide.home ? '#164C96' : '#A61B1B',
    secondaryColorHex: '#FFFFFF',
    accentColorHex: '#F79009',
    goalkeeperColorHex: '#17B26A',
  );
}

MatchTimelineFrame _buildFrame({
  required String id,
  required double timeSeconds,
  required double clockMinute,
  required MatchViewerPhase phase,
  required int homeScore,
  required int awayScore,
  required double homeShiftX,
  required double awayShiftX,
  required MatchViewerPoint ball,
  String? activeEventId,
  MatchCameraPreset cameraPreset = MatchCameraPreset.broadcast,
}) {
  return MatchTimelineFrame(
    id: id,
    timeSeconds: timeSeconds,
    clockMinute: clockMinute,
    phase: phase,
    homeScore: homeScore,
    awayScore: awayScore,
    homeAttacksRight: true,
    possessionSide: ball.x >= 50 ? MatchViewerSide.home : MatchViewerSide.away,
    activeEventId: activeEventId,
    cameraPreset: cameraPreset,
    players: <MatchViewerPlayerFrame>[
      ..._buildPlayers(
        teamId: 'home',
        side: MatchViewerSide.home,
        xShift: homeShiftX,
        yShift: 0,
      ),
      ..._buildPlayers(
        teamId: 'away',
        side: MatchViewerSide.away,
        xShift: awayShiftX,
        yShift: 0.6,
      ),
    ],
    ball: MatchViewerBallFrame(
      position: ball,
      ownerPlayerId: ball.x >= 50 ? 'home-9' : 'away-9',
      state: 'rolling',
    ),
  );
}

List<MatchViewerPlayerFrame> _buildPlayers({
  required String teamId,
  required MatchViewerSide side,
  required double xShift,
  required double yShift,
}) {
  const List<MatchViewerPoint> homeBase = <MatchViewerPoint>[
    MatchViewerPoint(x: 8, y: 50),
    MatchViewerPoint(x: 20, y: 18),
    MatchViewerPoint(x: 22, y: 38),
    MatchViewerPoint(x: 22, y: 62),
    MatchViewerPoint(x: 20, y: 82),
    MatchViewerPoint(x: 40, y: 24),
    MatchViewerPoint(x: 44, y: 50),
    MatchViewerPoint(x: 40, y: 76),
    MatchViewerPoint(x: 65, y: 20),
    MatchViewerPoint(x: 70, y: 50),
    MatchViewerPoint(x: 65, y: 80),
  ];
  const List<MatchPlayerLine> lines = <MatchPlayerLine>[
    MatchPlayerLine.goalkeeper,
    MatchPlayerLine.defense,
    MatchPlayerLine.defense,
    MatchPlayerLine.defense,
    MatchPlayerLine.defense,
    MatchPlayerLine.midfield,
    MatchPlayerLine.midfield,
    MatchPlayerLine.midfield,
    MatchPlayerLine.attack,
    MatchPlayerLine.attack,
    MatchPlayerLine.attack,
  ];
  const List<MatchViewerRole> roles = <MatchViewerRole>[
    MatchViewerRole.goalkeeper,
    MatchViewerRole.defender,
    MatchViewerRole.defender,
    MatchViewerRole.defender,
    MatchViewerRole.defender,
    MatchViewerRole.midfielder,
    MatchViewerRole.midfielder,
    MatchViewerRole.midfielder,
    MatchViewerRole.forward,
    MatchViewerRole.forward,
    MatchViewerRole.forward,
  ];

  return List<MatchViewerPlayerFrame>.generate(11, (int index) {
    final MatchViewerPoint base = homeBase[index];
    final double baseX = side == MatchViewerSide.home ? base.x : 100 - base.x;
    final double baseY = side == MatchViewerSide.home ? base.y : 100 - base.y;
    final double x = (baseX + xShift + ((index % 3) * 0.22)).clamp(2, 98);
    final double y = (baseY + yShift + ((index % 2) * 0.18)).clamp(2, 98);
    final int shirtNumber = index + 1;
    return MatchViewerPlayerFrame(
      playerId: '$teamId-$shirtNumber',
      teamId: teamId,
      side: side,
      shirtNumber: shirtNumber,
      label: '$shirtNumber',
      role: roles[index],
      line: lines[index],
      state: shirtNumber >= 9
          ? MatchViewerPlayerState.attacking
          : MatchViewerPlayerState.moving,
      active: true,
      highlighted: shirtNumber == 9,
      position: MatchViewerPoint(x: x.toDouble(), y: y.toDouble()),
      anchorPosition: MatchViewerPoint(x: baseX, y: baseY),
    );
  });
}
