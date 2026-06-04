import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/live_match_session.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/features/match_center/presentation/gte_live_match_center_screen.dart';
import 'package:gte_frontend/features/match_center/realtime/realtime.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('competition route shell renders canonical match center', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _competition();
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteLiveMatchCenterScreen(
          competition: competition,
          snapshotLoader: (_, {String? matchId}) async => _richSnapshot(),
          sessionResolver: _sessionResolver,
          webSocketResolver: _webSocketResolver,
          realtimeWatcher:
              (_) => Stream<LiveMatchRealtimeFrame>.value(
                LiveMatchRealtimeFrame.fromSnapshot(
                  snapshot: _richSnapshot(),
                  status: LiveMatchRealtimeStatus.live,
                  source: LiveMatchRealtimeSource.snapshotWebSocket,
                ),
              ),
        ),
      ),
    );

    await tester.pump();
    await tester.pumpAndSettle(const Duration(milliseconds: 120));

    expect(find.text('Live match center'), findsOneWidget);
    expect(find.byKey(const Key('match-center-scorebug')), findsOneWidget);
    expect(find.text('2D pitch shell'), findsOneWidget);
    expect(find.text('Live intelligence'), findsOneWidget);
    expect(find.text('Goal - Lagos United'), findsOneWidget);
  });

  testWidgets('competition route shell exposes canonical empty states', (
    WidgetTester tester,
  ) async {
    final CompetitionSummary competition = _competition();
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteLiveMatchCenterScreen(
          competition: competition,
          snapshotLoader: (_, {String? matchId}) async => _sparseSnapshot(),
          sessionResolver: _sessionResolver,
          webSocketResolver: _webSocketResolver,
          realtimeWatcher:
              (_) => Stream<LiveMatchRealtimeFrame>.value(
                LiveMatchRealtimeFrame.fromSnapshot(
                  snapshot: _sparseSnapshot(),
                  status: LiveMatchRealtimeStatus.live,
                  source: LiveMatchRealtimeSource.snapshotWebSocket,
                ),
              ),
        ),
      ),
    );

    await tester.pump();
    await tester.pumpAndSettle(const Duration(milliseconds: 120));

    expect(find.text('Pitch shell waiting for lineups'), findsOneWidget);
    expect(find.text('Timeline empty'), findsWidgets);
  });
}

CompetitionSummary _competition() {
  return CompetitionSummary(
    id: 'match-center-competition-test',
    name: 'GTEX Live',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.inProgress,
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
    rulesSummary: 'Live center fixture',
    matchType: MatchType.userHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 1),
  );
}

Future<LiveMatchSpectateSession?> _sessionResolver(String matchId) async {
  return LiveMatchSpectateSession(
    id: 'session-$matchId',
    matchId: matchId,
    channel: 'matchday',
    websocketPath: '/ws/matches/$matchId',
  );
}

Uri? _webSocketResolver(String? path) {
  return Uri.parse('ws://example.test${path ?? '/ws/matches/test'}');
}

LiveMatchSnapshot _richSnapshot() {
  final DateTime expiresAt = DateTime.utc(2026, 1, 1);
  return LiveMatchSnapshot(
    matchId: 'match-center-test',
    homeTeam: 'Lagos United',
    awayTeam: 'Accra City',
    homeScore: 2,
    awayScore: 1,
    minute: 64,
    phase: LiveMatchPhase.secondHalf,
    momentum: const <int>[1, 2, 1],
    commentary: const <LiveMatchEvent>[
      LiveMatchEvent(
        minute: 33,
        title: 'Goal - Lagos United',
        detail: 'Backend-confirmed finish.',
        team: 'Lagos United',
        type: LiveMatchEventType.goal,
        isKeyMoment: true,
      ),
    ],
    homeLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Ayo Mensah', position: 'GK', rating: 7),
      LiveMatchLineupPlayer(name: 'Tunde Bello', position: 'CB', rating: 7),
    ],
    awayLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Kwame Boateng', position: 'GK', rating: 7),
      LiveMatchLineupPlayer(name: 'Yaw Owusu', position: 'CB', rating: 7),
    ],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: expiresAt,
    premiumHighlightExpiresAt: expiresAt,
    stats: const LiveMatchStatsSnapshot(
      possession: LiveMatchStatPair(home: 58, away: 42, unit: '%'),
      expectedGoals: LiveMatchStatPair(home: 1.42, away: 0.81),
      pressure: LiveMatchStatPair(home: 67, away: 44),
      shotMap: <LiveMatchShotMarker>[
        LiveMatchShotMarker(x: 0.78, y: 0.42, xg: 0.34, team: 'home'),
      ],
    ),
    liveIntelligence: const LiveMatchLiveIntelligence(
      status: 'provided',
      summary: 'Live model sees pressure arriving from the home right channel.',
      updatedAt: null,
      signals: <LiveMatchIntelligenceSignal>[
        LiveMatchIntelligenceSignal(
          title: 'Press trap forming',
          detail: 'Away build-up is being forced toward the touchline.',
          severity: 'high',
          source: 'ops-feed',
        ),
      ],
    ),
  );
}

LiveMatchSnapshot _sparseSnapshot() {
  final DateTime expiresAt = DateTime.utc(2026, 1, 1);
  return LiveMatchSnapshot(
    matchId: 'match-center-sparse-test',
    homeTeam: 'Lagos United',
    awayTeam: 'Accra City',
    homeScore: 0,
    awayScore: 0,
    minute: 0,
    phase: LiveMatchPhase.preMatch,
    momentum: const <int>[],
    commentary: const <LiveMatchEvent>[],
    homeLineup: const <LiveMatchLineupPlayer>[],
    awayLineup: const <LiveMatchLineupPlayer>[],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: expiresAt,
    premiumHighlightExpiresAt: expiresAt,
  );
}
