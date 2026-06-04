import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/match_center.dart';

void main() {
  test('derives overlay availability from live match snapshot data', () {
    final LiveMatchSnapshot match = _snapshot(
      stats: const LiveMatchStatsSnapshot(
        expectedGoals: LiveMatchStatPair(home: 1.42, away: 0.81),
        shotMap: <LiveMatchShotMarker>[
          LiveMatchShotMarker(x: 0.72, y: 0.44, xg: 0.34, team: 'home'),
        ],
      ),
    );

    final MatchCenterOverlayAvailability xg =
        MatchCenterOverlayAvailability.fromSnapshot(
          match,
          LiveMatchOverlayMode.xg,
        );
    final MatchCenterOverlayAvailability market =
        MatchCenterOverlayAvailability.fromSnapshot(
          match,
          LiveMatchOverlayMode.market,
        );

    expect(xg.state, MatchCenterSurfaceState.confirmed);
    expect(xg.metrics.map((MatchCenterMetric metric) => metric.value), [
      '1.42 / 0.81',
      '1',
    ]);
    expect(market.state, MatchCenterSurfaceState.blocked);
    expect(market.detail, contains('Market context'));
  });

  test(
    'marks canonical lanes blocked, empty, or degraded without fallback truth',
    () {
      final MatchCenterReadiness sparse = MatchCenterReadiness.fromSnapshot(
        _snapshot(matchId: null, lineups: false),
      );
      final MatchCenterReadiness degraded = MatchCenterReadiness.fromSnapshot(
        _snapshot(
          stats: const LiveMatchStatsSnapshot(
            pressure: LiveMatchStatPair(home: 55, away: 38),
          ),
        ),
        feedDegraded: true,
      );

      expect(sparse.scorebug, MatchCenterSurfaceState.blocked);
      expect(sparse.pitch, MatchCenterSurfaceState.empty);
      expect(sparse.stats, MatchCenterSurfaceState.blocked);
      expect(degraded.scorebug, MatchCenterSurfaceState.degraded);
      expect(degraded.pitch, MatchCenterSurfaceState.degraded);
      expect(degraded.stats, MatchCenterSurfaceState.degraded);
    },
  );
}

LiveMatchSnapshot _snapshot({
  String? matchId = 'match-center-model-test',
  bool lineups = true,
  LiveMatchStatsSnapshot? stats,
}) {
  final DateTime expiresAt = DateTime.utc(2026, 1, 1);
  return LiveMatchSnapshot(
    matchId: matchId,
    homeTeam: 'Lagos United',
    awayTeam: 'Accra City',
    homeScore: 2,
    awayScore: 1,
    minute: 64,
    phase: LiveMatchPhase.secondHalf,
    momentum: const <int>[],
    commentary: const <LiveMatchEvent>[
      LiveMatchEvent(
        minute: 33,
        title: 'Goal - Lagos United',
        detail: 'Verified live feed event.',
        team: 'Lagos United',
        type: LiveMatchEventType.goal,
      ),
    ],
    homeLineup:
        lineups
            ? const <LiveMatchLineupPlayer>[
              LiveMatchLineupPlayer(
                name: 'Ayo Mensah',
                position: 'GK',
                rating: 7,
              ),
            ]
            : const <LiveMatchLineupPlayer>[],
    awayLineup:
        lineups
            ? const <LiveMatchLineupPlayer>[
              LiveMatchLineupPlayer(
                name: 'Kwame Boateng',
                position: 'GK',
                rating: 7,
              ),
            ]
            : const <LiveMatchLineupPlayer>[],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: expiresAt,
    premiumHighlightExpiresAt: expiresAt,
    stats: stats,
  );
}
