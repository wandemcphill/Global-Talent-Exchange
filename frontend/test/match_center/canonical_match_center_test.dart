import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/canonical_match_center.dart';

void main() {
  test('overlay statuses reflect backend payload availability', () {
    final LiveMatchSnapshot snapshot = _snapshot();
    final List<CanonicalOverlayStatus> statuses = canonicalOverlayStatuses(
      snapshot,
    );

    expect(statuses, hasLength(LiveMatchOverlayMode.values.length));
    expect(
      statuses
          .singleWhere(
            (CanonicalOverlayStatus status) =>
                status.mode == LiveMatchOverlayMode.xg,
          )
          .state,
      CanonicalMatchSurfaceState.confirmed,
    );
    expect(
      statuses
          .singleWhere(
            (CanonicalOverlayStatus status) =>
                status.mode == LiveMatchOverlayMode.market,
          )
          .state,
      CanonicalMatchSurfaceState.confirmed,
    );
  });

  test('overlay statuses block missing payloads', () {
    final LiveMatchSnapshot snapshot = _snapshot(stats: null);

    expect(
      canonicalOverlayStatuses(snapshot)
          .singleWhere(
            (CanonicalOverlayStatus status) =>
                status.mode == LiveMatchOverlayMode.pressure,
          )
          .state,
      CanonicalMatchSurfaceState.blocked,
    );
  });

  testWidgets('scorebug and intelligence render backend fields', (
    WidgetTester tester,
  ) async {
    final LiveMatchSnapshot snapshot = _snapshot();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Column(
            children: <Widget>[
              CanonicalLiveScorebug(snapshot: snapshot),
              CanonicalLiveIntelligenceRail(snapshot: snapshot),
            ],
          ),
        ),
      ),
    );

    expect(find.text('Lagos United'), findsOneWidget);
    expect(find.text('Accra City'), findsOneWidget);
    expect(find.text('Live intelligence'), findsOneWidget);
    expect(find.text('Backend pressure rising'), findsOneWidget);
  });

  testWidgets('scorebug masks score and clock before backend truth', (
    WidgetTester tester,
  ) async {
    final LiveMatchSnapshot snapshot = _snapshot();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CanonicalLiveScorebug(
            snapshot: snapshot,
            hasBackendSnapshotTruth: false,
          ),
        ),
      ),
    );

    expect(find.text('2'), findsNothing);
    expect(find.text('1'), findsNothing);
    expect(find.text('64 min'), findsNothing);
    expect(find.text('--'), findsNWidgets(2));
    expect(find.text('Syncing'), findsOneWidget);
  });

  testWidgets('intelligence rail blocks when payload is absent', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CanonicalLiveIntelligenceRail(snapshot: _snapshot(intel: null)),
        ),
      ),
    );

    expect(find.text('Live intelligence blocked'), findsOneWidget);
  });
}

LiveMatchSnapshot _snapshot({
  LiveMatchStatsSnapshot? stats = const LiveMatchStatsSnapshot(
    possession: LiveMatchStatPair(home: 55, away: 45, unit: '%'),
    pressure: LiveMatchStatPair(home: 61, away: 39),
    expectedGoals: LiveMatchStatPair(home: 1.3, away: 0.7),
    territory: LiveMatchStatPair(home: 58, away: 42, unit: '%'),
    marketSignal: 'Home control',
    shotMap: <LiveMatchShotMarker>[
      LiveMatchShotMarker(x: 0.7, y: 0.4, xg: 0.25, team: 'home'),
    ],
  ),
  LiveMatchLiveIntelligence? intel = const LiveMatchLiveIntelligence(
    status: 'provided',
    summary: 'Backend pressure rising',
    signals: <LiveMatchIntelligenceSignal>[
      LiveMatchIntelligenceSignal(
        title: 'Right channel',
        detail: 'Backend signal favors right-side pressure.',
        severity: 'high',
      ),
    ],
  ),
}) {
  final DateTime expires = DateTime.utc(2026);
  return LiveMatchSnapshot(
    matchId: 'match-1',
    homeTeam: 'Lagos United',
    awayTeam: 'Accra City',
    homeScore: 2,
    awayScore: 1,
    minute: 64,
    phase: LiveMatchPhase.secondHalf,
    momentum: const <int>[1, 2, 0],
    commentary: const <LiveMatchEvent>[
      LiveMatchEvent(
        minute: 33,
        title: 'Goal - Lagos United',
        detail: 'Backend event.',
        team: 'Lagos United',
        type: LiveMatchEventType.goal,
      ),
    ],
    homeLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Ayo Mensah', position: 'GK', rating: 7),
    ],
    awayLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Kofi Boateng', position: 'GK', rating: 7),
    ],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: expires,
    premiumHighlightExpiresAt: expires,
    stats: stats,
    liveIntelligence: intel,
  );
}
