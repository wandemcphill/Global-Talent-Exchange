import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';
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
    final MatchTimelineFrame firstFrame = viewState.firstFrame;
    final MatchViewerPlayerFrame homePlayer = firstFrame.players.firstWhere(
      (MatchViewerPlayerFrame player) =>
          player.teamId == 'home' && player.label == '1',
    );

    expect(homePlayer.playerId, 'player-9');
  });

  testWidgets(
      'match viewer renders fallback replay, controls, and offside placeholder',
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
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    expect(find.text('2D Match Viewer'), findsOneWidget);
    expect(find.text('Replay lane'), findsOneWidget);
    expect(find.text('Restart'), findsOneWidget);
    expect(find.text('Next event'), findsOneWidget);
    expect(
      find.text(snapshot.homeTeam.substring(0, 3).toUpperCase()),
      findsOneWidget,
    );
    expect(
      find.text(snapshot.awayTeam.substring(0, 3).toUpperCase()),
      findsOneWidget,
    );

    for (int index = 0;
        index < 8 && find.text('Offside (data unavailable)').evaluate().isEmpty;
        index += 1) {
      await tester.tap(find.text('Next event'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 24));
    }

    expect(find.text('Offside (data unavailable)'), findsWidgets);
  });

  test('fallback viewer marks the synthetic offside path as data unavailable',
      () async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-viewer-placeholder',
    );
    final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
      competition,
    );

    final viewState = await MatchViewerMapper.load(
      competition: competition,
      matchKey: competition.id,
      fallbackSnapshot: snapshot,
      preferFallback: true,
    );

    final offsideEvent = viewState.events.firstWhere(
      (event) => event.type == MatchViewerEventType.offside,
    );
    expect(offsideEvent.isDataUnavailable, isTrue);
    expect(offsideEvent.bannerText, 'Offside (data unavailable)');
  });

  testWidgets('match viewer remains stable across back-to-back replay loads',
      (WidgetTester tester) async {
    final CompetitionSummary firstCompetition = _buildCompetition(
      id: 'match-viewer-first',
    );
    final CompetitionSummary secondCompetition = _buildCompetition(
      id: 'match-viewer-second',
    );
    final LiveMatchSnapshot firstSnapshot = LiveMatchFixtures.buildSnapshot(
      firstCompetition,
    );
    final LiveMatchSnapshot secondSnapshot = LiveMatchFixtures.buildSnapshot(
      secondCompetition,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: firstCompetition,
          matchKey: firstCompetition.id,
          fallbackSnapshot: firstSnapshot,
          preferFallback: true,
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 48));

    expect(find.text('Replay lane'), findsOneWidget);

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: secondCompetition,
          matchKey: secondCompetition.id,
          fallbackSnapshot: secondSnapshot,
          preferFallback: true,
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 48));

    expect(find.text('2D Match Viewer'), findsOneWidget);
    expect(find.text('Replay lane'), findsOneWidget);
    expect(find.text('Next event'), findsOneWidget);
  });
}

CompetitionSummary _buildCompetition({
  required String id,
}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX Replay Test',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.completed,
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
