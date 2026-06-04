import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/controllers/match_playback_controller.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/match_center/presentation/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/features/match_center/services/match_commentary_engine.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import 'support/gtex_match_broadcast_fixture.dart';

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

  test('commentary engine renders final-form live payloads', () {
    final String line = MatchCommentaryEngine.lineForRaw(
      eventType: 'goal',
      player: 'John Doe',
      team: 'Home FC',
      score: '2-1',
      minute: 67,
    );

    expect(line, contains('John Doe finds the net'));
    expect(line, contains('Score: 2-1'));
  });

  testWidgets('legacy local viewer is blocked before loading playback data', (
    WidgetTester tester,
  ) async {
    int loadCount = 0;
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-viewer-quarantine-test',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexMatchViewerScreen(
          competition: competition,
          matchKey: competition.id,
          viewStateLoader: () async {
            loadCount += 1;
            return buildBroadcastTestViewState();
          },
        ),
      ),
    );

    await tester.pump();

    expect(loadCount, 0);
    expect(
      find.byKey(GtexMatchViewerScreen.quarantinePanelKey),
      findsOneWidget,
    );
    expect(find.text(GtexMatchViewerScreen.quarantineTitle), findsOneWidget);
    expect(
      find.textContaining('legacy local 2D playback viewer'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('match-2d-score-strip')), findsNothing);
    expect(find.byKey(const Key('match-2d-pitch-stage')), findsNothing);
    expect(find.byKey(const Key('match-2d-live-panel')), findsNothing);
    expect(find.byKey(const Key('match-2d-controls')), findsNothing);
  });

  testWidgets('legacy playback controller fails fast when constructed', (
    WidgetTester tester,
  ) async {
    expect(
      () => MatchPlaybackController(
        vsync: tester,
        viewState: buildBroadcastTestViewState(),
        autoplay: false,
      ),
      throwsA(
        isA<UnsupportedError>().having(
          (UnsupportedError error) => error.message,
          'message',
          MatchPlaybackController.quarantineMessage,
        ),
      ),
    );
    expect(
      MatchPlaybackController.clampAnimationDurationMs(1200),
      MatchPlaybackController.maxAnimationMs,
    );
  });

  test('event-only pass payloads do not build fallback 2D frames', () {
    final Map<String, Object?> payload = _eventOnlyPassPayload();

    final MatchViewState eventState = MatchViewState.fromJson(payload);
    expect(eventState.events.single.type, MatchViewerEventType.pass);
    expect(eventState.events.single.durationMs, 650);
    expect(eventState.frames, isEmpty);
  });
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX 2D Match Test',
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
    rulesSummary: '2D viewer validation fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}

Map<String, Object?> _eventOnlyPassPayload() {
  return <String, Object?>{
    'match_id': 'event-only-pass',
    'source': 'test',
    'supports_offside': true,
    'duration_seconds': 20,
    'home_team': <String, Object?>{
      'team_id': 'home',
      'team_name': 'Valencia',
      'short_name': 'VAL',
      'side': 'home',
      'formation': '4-3-3',
      'primary_color': '#FFFFFF',
      'secondary_color': '#111827',
      'accent_color': '#FDB022',
      'goalkeeper_color': '#EC4899',
    },
    'away_team': <String, Object?>{
      'team_id': 'away',
      'team_name': 'Dumbarton',
      'short_name': 'DUM',
      'side': 'away',
      'formation': '4-3-3',
      'primary_color': '#4C1D95',
      'secondary_color': '#FFFFFF',
      'accent_color': '#FDE68A',
      'goalkeeper_color': '#FDE68A',
    },
    'events': <Object?>[
      <String, Object?>{
        'event_id': 'pass-1',
        'sequence': 1,
        'event_type': 'pass',
        'minute': 1,
        'added_time': 0,
        'clock_label': '00:11',
        'time_seconds': 11,
        'team_id': 'away',
        'team_name': 'Dumbarton',
        'primary_player_id': 'away-6',
        'primary_player_name': 'Zakaria',
        'secondary_player_id': 'away-8',
        'secondary_player_name': 'Schingienne',
        'home_score': 0,
        'away_score': 0,
        'banner_text': 'Pass',
        'commentary': 'Zakaria lays it back to Schingienne',
        'emphasis_level': 1,
        'duration_ms': 650,
        'highlighted_player_ids': <Object?>['away-6', 'away-8'],
        'flags': <Object?>[],
        'positions': <Object?>[
          <String, Object?>{
            'player_id': 'away-6',
            'player_name': 'Zakaria',
            'team_id': 'away',
            'side': 'away',
            'shirt_number': 6,
            'role': 'midfielder',
            'line': 'midfield',
            'position': <String, Object?>{'x': 48, 'y': 50},
          },
          <String, Object?>{
            'player_id': 'away-8',
            'player_name': 'Schingienne',
            'team_id': 'away',
            'side': 'away',
            'shirt_number': 8,
            'role': 'midfielder',
            'line': 'midfield',
            'position': <String, Object?>{'x': 55, 'y': 48},
          },
        ],
        'ball': <String, Object?>{
          'position': <String, Object?>{'x': 55, 'y': 48},
          'owner_player_id': 'away-8',
          'state': 'pass',
        },
      },
    ],
    'frames': <Object?>[],
  };
}
