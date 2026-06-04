import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/match_center.dart';
import 'package:gte_frontend/features/match_center/realtime/live_match_realtime_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  testWidgets('renders scorebug, pitch shell, live intelligence, and tabs', (
    WidgetTester tester,
  ) async {
    await _setWideSurface(tester);
    await tester.pumpWidget(_app(MatchCenterSurface(match: _richSnapshot())));

    expect(find.byKey(const Key('match-center-scorebug')), findsOneWidget);
    expect(find.text('Lagos United'), findsWidgets);
    expect(find.text('Accra City'), findsWidgets);
    expect(find.text('2 - 1'), findsOneWidget);
    expect(find.text('2D pitch shell'), findsOneWidget);
    expect(find.text('Shape'), findsWidgets);
    expect(find.text('xG'), findsWidgets);
    expect(find.text('Live intelligence'), findsOneWidget);
    expect(find.text('Press trap forming'), findsOneWidget);
    expect(find.text('Timeline'), findsWidgets);
    expect(find.text('Goal - Lagos United'), findsOneWidget);

    await tester.tap(
      find.descendant(of: find.byType(TabBar), matching: find.text('Stats')),
    );
    await tester.pumpAndSettle();

    expect(find.text('Possession'), findsOneWidget);
    expect(find.text('Expected goals'), findsOneWidget);
  });

  testWidgets('does not expose local demo controls or forbidden labels', (
    WidgetTester tester,
  ) async {
    await _setWideSurface(tester);
    final LiveMatchSnapshot snapshot = _richSnapshot();

    await tester.pumpWidget(_app(MatchCenterSurface(match: snapshot)));

    _expectNoForbiddenMatchCenterText();

    final LiveMatchRealtimeFrame syncingFrame =
        LiveMatchRealtimeFrame.fromSnapshot(
          snapshot: snapshot,
          status: LiveMatchRealtimeStatus.syncing,
          source: LiveMatchRealtimeSource.commentaryWebSocket,
          hasBackendSnapshotTruth: false,
          issue: const LiveMatchRealtimeIssue(
            code: 'awaiting_backend_snapshot',
            message: 'Awaiting backend score-clock snapshot.',
            source: LiveMatchRealtimeSource.commentaryWebSocket,
          ),
        );

    await tester.pumpWidget(
      _app(MatchCenterSurface.fromRealtimeFrame(frame: syncingFrame)),
    );

    _expectNoForbiddenMatchCenterText();
  });

  testWidgets('reports degraded overlay modes', (WidgetTester tester) async {
    await _setWideSurface(tester);
    await tester.pumpWidget(
      _app(
        MatchCenterSurface(
          match: _richSnapshot(),
          feedDegraded: true,
          initialOverlayMode: LiveMatchOverlayMode.xg,
        ),
      ),
    );

    expect(find.text('xG overlay degraded'), findsOneWidget);
    expect(find.text('1.42 / 0.81'), findsOneWidget);
    expect(find.text('DEGRADED'), findsWidgets);

    await tester.pumpWidget(
      _app(
        MatchCenterSurface(
          match: _richSnapshot(),
          feedDegraded: true,
          initialOverlayMode: LiveMatchOverlayMode.market,
        ),
      ),
    );
    expect(find.text('Market overlay degraded'), findsOneWidget);
    expect(find.text('Home control rising'), findsOneWidget);
  });

  testWidgets('renders blocked and empty states for sparse snapshots', (
    WidgetTester tester,
  ) async {
    await _setWideSurface(tester);
    await tester.pumpWidget(_app(MatchCenterSurface(match: _sparseSnapshot())));

    expect(find.text('Match id blocked'), findsWidgets);
    expect(find.text('Pitch shell waiting for lineups'), findsOneWidget);
    expect(find.text('Live intelligence empty'), findsOneWidget);

    await tester.tap(
      find.descendant(of: find.byType(TabBar), matching: find.text('Stats')),
    );
    await tester.pumpAndSettle();

    expect(find.text('Stats payload blocked'), findsWidgets);
  });

  testWidgets(
    'withholds score clock and timeline until realtime truth arrives',
    (WidgetTester tester) async {
      await _setWideSurface(tester);
      final LiveMatchSnapshot snapshot = _richSnapshot();
      final LiveMatchRealtimeFrame syncingFrame =
          LiveMatchRealtimeFrame.fromSnapshot(
            snapshot: snapshot,
            status: LiveMatchRealtimeStatus.syncing,
            source: LiveMatchRealtimeSource.commentaryWebSocket,
            hasBackendSnapshotTruth: false,
            issue: const LiveMatchRealtimeIssue(
              code: 'awaiting_backend_snapshot',
              message: 'Awaiting backend score-clock snapshot.',
              source: LiveMatchRealtimeSource.commentaryWebSocket,
            ),
          );

      await tester.pumpWidget(
        _app(MatchCenterSurface.fromRealtimeFrame(frame: syncingFrame)),
      );

      expect(find.text('2 - 1'), findsNothing);
      expect(find.text("64'"), findsNothing);
      expect(find.text('Goal - Lagos United'), findsNothing);
      expect(find.text('-- - --'), findsOneWidget);
      expect(find.text('Scorebug syncing'), findsOneWidget);
      expect(find.text('Timeline syncing'), findsOneWidget);

      final LiveMatchRealtimeFrame liveFrame =
          LiveMatchRealtimeFrame.fromSnapshot(
            snapshot: snapshot,
            status: LiveMatchRealtimeStatus.live,
            source: LiveMatchRealtimeSource.snapshotWebSocket,
            hasBackendSnapshotTruth: true,
          );

      await tester.pumpWidget(
        _app(MatchCenterSurface.fromRealtimeFrame(frame: liveFrame)),
      );

      expect(find.text('2 - 1'), findsOneWidget);
      expect(find.text("64'"), findsOneWidget);
      expect(find.text('Goal - Lagos United'), findsOneWidget);
    },
  );

  testWidgets('closed realtime frames render a blocked overlay state', (
    WidgetTester tester,
  ) async {
    await _setWideSurface(tester);
    final LiveMatchRealtimeFrame closedFrame =
        LiveMatchRealtimeFrame.fromSnapshot(
          snapshot: _richSnapshot(),
          status: LiveMatchRealtimeStatus.closed,
          source: LiveMatchRealtimeSource.snapshotWebSocket,
          hasBackendSnapshotTruth: false,
          issue: const LiveMatchRealtimeIssue(
            code: 'websocket_closed',
            message:
                'Live match websocket closed before backend score-clock truth.',
            source: LiveMatchRealtimeSource.snapshotWebSocket,
          ),
        );

    await tester.pumpWidget(
      _app(MatchCenterSurface.fromRealtimeFrame(frame: closedFrame)),
    );

    expect(find.text('2 - 1'), findsNothing);
    expect(find.text("64'"), findsNothing);
    expect(find.text('-- - --'), findsOneWidget);
    expect(find.text('Scorebug blocked'), findsOneWidget);
    expect(find.text('Timeline blocked'), findsOneWidget);
    expect(
      find.text(
        'Live match websocket closed before backend score-clock truth.',
      ),
      findsWidgets,
    );
  });
}

void _expectNoForbiddenMatchCenterText() {
  final RegExp forbidden = RegExp(
    [
      r'inject(?:ed)?\s+(?:go'
          r'al|event)',
      r'local\s+pa'
          r'use',
      r'pa'
          r'use\s+simulation',
      r'res'
          r'ume\s+simulation',
      r'fa'
          r'ke\s+timer',
      r'genera'
          r'ted\s+event',
      r'uni'
          r'ty',
      r'na'
          r'tive\s+3d',
      r'pseu'
          r'do-?3d',
      r'pay'
          r'stack',
    ].join('|'),
    caseSensitive: false,
  );

  expect(find.textContaining(forbidden), findsNothing);
}

Widget _app(Widget child) {
  return MaterialApp(
    theme: GteShellTheme.build(),
    home: Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: child,
      ),
    ),
  );
}

Future<void> _setWideSurface(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(1200, 1000);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

LiveMatchSnapshot _richSnapshot() {
  final DateTime expiresAt = DateTime.utc(2026, 1, 1);
  return LiveMatchSnapshot(
    matchId: 'match-center-widget-test',
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
        detail: 'Verified live feed event.',
        team: 'Lagos United',
        type: LiveMatchEventType.goal,
      ),
      LiveMatchEvent(
        minute: 41,
        title: 'Yellow card - Accra City',
        detail: 'Verified live feed booking.',
        team: 'Accra City',
        type: LiveMatchEventType.card,
      ),
    ],
    homeLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Ayo Mensah', position: 'GK', rating: 7),
      LiveMatchLineupPlayer(name: 'Tunde Bello', position: 'CB', rating: 7),
      LiveMatchLineupPlayer(name: 'Kofi Ade', position: 'CM', rating: 7),
    ],
    awayLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Kwame Boateng', position: 'GK', rating: 7),
      LiveMatchLineupPlayer(name: 'Yaw Owusu', position: 'CB', rating: 7),
      LiveMatchLineupPlayer(name: 'Kojo Mensah', position: 'FW', rating: 7),
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
      shots: LiveMatchStatPair(home: 9, away: 6),
      shotsOnTarget: LiveMatchStatPair(home: 5, away: 3),
      expectedGoals: LiveMatchStatPair(home: 1.42, away: 0.81),
      territory: LiveMatchStatPair(home: 61, away: 39, unit: '%'),
      pressure: LiveMatchStatPair(home: 67, away: 44),
      marketSignal: 'Home control rising',
      marketDetail: 'Liquidity watching next goal exposure',
      shotMap: <LiveMatchShotMarker>[
        LiveMatchShotMarker(x: 0.78, y: 0.42, xg: 0.34, team: 'home'),
        LiveMatchShotMarker(x: 0.22, y: 0.58, xg: 0.18, team: 'away'),
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
