import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/realtime/live_match_realtime.dart';

void main() {
  test(
    'snapshot reducer waits for backend payload before exposing truth',
    () async {
      final LiveMatchSnapshot seed = _snapshot();
      final List<LiveMatchRealtimeState> states =
          await const LiveMatchRealtimeReducer()
              .bind(
                seed: seed,
                backendPayloads: Stream<Map<String, Object?>>.fromIterable(
                  <Map<String, Object?>>[
                    <String, Object?>{
                      'match_id': 'match-1',
                      'home_score': 3,
                      'away_score': 1,
                      'minute': 70,
                      'status': 'live',
                      'timeline_events': <Object?>[
                        <String, Object?>{
                          'event_type': 'goal',
                          'minute': 70,
                          'team_name': 'Lagos United',
                          'description': 'Backend goal update.',
                        },
                      ],
                    },
                  ],
                ),
              )
              .toList();

      expect(states.first.connection, LiveMatchRealtimeConnection.connecting);
      expect(states.first.hasBackendSnapshotTruth, isFalse);
      expect(states.first.isUsable, isFalse);
      expect(states.first.snapshot.homeScore, 0);
      expect(states.first.snapshot.awayScore, 0);
      expect(states.first.snapshot.minute, 0);
      expect(states[1].connection, LiveMatchRealtimeConnection.live);
      expect(states[1].hasBackendSnapshotTruth, isTrue);
      expect(states[1].isUsable, isTrue);
      expect(states[1].snapshot.homeScore, 3);
      expect(states[1].snapshot.commentary.last.minute, 70);
      expect(states.last.connection, LiveMatchRealtimeConnection.closed);
      expect(states.last.isUsable, isFalse);
    },
  );

  test('event-only reducer payload does not certify snapshot truth', () async {
    final List<LiveMatchRealtimeState> states =
        await const LiveMatchRealtimeReducer()
            .bind(
              seed: _snapshot(),
              backendPayloads: Stream<Map<String, Object?>>.fromIterable(
                <Map<String, Object?>>[
                  <String, Object?>{
                    'timeline_events': <Object?>[
                      <String, Object?>{
                        'event_type': 'incident',
                        'minute': 70,
                        'team_name': 'Lagos United',
                        'description': 'Backend event without score clock.',
                      },
                    ],
                  },
                ],
              ),
            )
            .toList();

    expect(states[1].connection, LiveMatchRealtimeConnection.live);
    expect(states[1].hasBackendSnapshotTruth, isFalse);
    expect(states[1].isUsable, isFalse);
    expect(states[1].snapshot.homeScore, 0);
    expect(states[1].snapshot.awayScore, 0);
    expect(states[1].snapshot.minute, 0);
    expect(states[1].snapshot.commentary, hasLength(1));
  });

  test(
    'score-clock authority survives later commentary-only reducer payloads',
    () async {
      final List<LiveMatchRealtimeState> states =
          await const LiveMatchRealtimeReducer()
              .bind(
                seed: _snapshot(),
                backendPayloads: Stream<Map<String, Object?>>.fromIterable(
                  <Map<String, Object?>>[
                    <String, Object?>{
                      'score': <String, Object?>{
                        'home': <String, Object?>{'score': 2},
                        'away': <String, Object?>{'score': 2},
                      },
                      'clock_minute': 74,
                      'status': 'live',
                    },
                    <String, Object?>{
                      'timeline_events': <Object?>[
                        <String, Object?>{
                          'event_type': 'incident',
                          'minute': 75,
                          'team_name': 'Accra City',
                          'description':
                              'Backend event after score-clock authority.',
                        },
                      ],
                    },
                  ],
                ),
              )
              .toList();

      final LiveMatchRealtimeState snapshotTruth = states[1];
      expect(snapshotTruth.hasBackendSnapshotTruth, isTrue);
      expect(snapshotTruth.isUsable, isTrue);
      expect(snapshotTruth.snapshot.homeScore, 2);
      expect(snapshotTruth.snapshot.awayScore, 2);
      expect(snapshotTruth.snapshot.minute, 74);

      final LiveMatchRealtimeState commentaryAfterTruth = states[2];
      expect(commentaryAfterTruth.hasBackendSnapshotTruth, isTrue);
      expect(commentaryAfterTruth.isUsable, isTrue);
      expect(commentaryAfterTruth.snapshot.homeScore, 2);
      expect(commentaryAfterTruth.snapshot.awayScore, 2);
      expect(commentaryAfterTruth.snapshot.minute, 74);
      expect(commentaryAfterTruth.snapshot.commentary, hasLength(1));
    },
  );

  test('commentary reducer keeps backend events ordered and deduped', () async {
    const LiveMatchEvent seed = LiveMatchEvent(
      minute: 12,
      title: 'Backend event',
      detail: 'Initial event.',
      team: 'Lagos United',
      type: LiveMatchEventType.incident,
    );
    final List<List<LiveMatchEvent>> states =
        await const LiveCommentaryRealtimeReducer()
            .bind(
              seed: const <LiveMatchEvent>[seed],
              backendEvents: Stream<List<LiveMatchEvent>>.fromIterable(
                const <List<LiveMatchEvent>>[
                  <LiveMatchEvent>[
                    LiveMatchEvent(
                      minute: 6,
                      title: 'Earlier backend event',
                      detail: 'Arrived late.',
                      team: 'Accra City',
                      type: LiveMatchEventType.incident,
                    ),
                    seed,
                  ],
                ],
              ),
            )
            .toList();

    expect(states.last, hasLength(2));
    expect(states.last.first.minute, 6);
  });
}

LiveMatchSnapshot _snapshot() {
  final DateTime expires = DateTime.utc(2026);
  return LiveMatchSnapshot(
    matchId: 'match-1',
    homeTeam: 'Lagos United',
    awayTeam: 'Accra City',
    homeScore: 2,
    awayScore: 1,
    minute: 64,
    phase: LiveMatchPhase.secondHalf,
    momentum: const <int>[],
    commentary: const <LiveMatchEvent>[],
    homeLineup: const <LiveMatchLineupPlayer>[],
    awayLineup: const <LiveMatchLineupPlayer>[],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: expires,
    premiumHighlightExpiresAt: expires,
  );
}
