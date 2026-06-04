import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';

void main() {
  test('backend payload parser does not invent commentary or score truth', () {
    final LiveMatchSnapshot snapshot = liveMatchSnapshotFromPayload(
      <String, Object?>{
        'match_id': 'match-abc',
        'home_team_name': 'Lagos United',
        'away_team_name': 'Accra City',
        'home_score': 2,
        'away_score': 1,
        'minute': 64,
        'status': 'live',
        'phase': 'second_half',
        'highlights': <Object?>[
          <String, Object?>{
            'title': 'Backend clip',
            'minute': 64,
            'duration_seconds': 12,
          },
        ],
      },
      competition: _competition(),
    );

    expect(snapshot.matchId, 'match-abc');
    expect(snapshot.homeScore, 2);
    expect(snapshot.awayScore, 1);
    expect(snapshot.minute, 64);
    expect(snapshot.commentary, isEmpty);
    expect(snapshot.highlights.single.id, 'match-abc-highlight-0');
  });

  test('backend timeline parser drops incomplete commentary events', () {
    final LiveMatchSnapshot snapshot = liveMatchSnapshotFromPayload(
      <String, Object?>{
        ..._baseLivePayload(matchId: 'match-timeline-truth'),
        'timeline_events': <Object?>[
          'Loose string from transport',
          <String, Object?>{'minute': 18, 'event_type': 'goal'},
          <String, Object?>{
            'event_type': 'card',
            'description': 'Card description without clock.',
          },
          <String, Object?>{
            'minute': 22,
            'event_type': 'chance',
            'description': 'Backend-authored chance line.',
          },
        ],
      },
      competition: _competition(),
    );

    expect(snapshot.commentary, hasLength(1));
    expect(snapshot.commentary.single.minute, 22);
    expect(snapshot.commentary.single.title, 'Backend-authored chance line.');
    expect(snapshot.commentary.single.detail, 'Backend-authored chance line.');
  });

  test('backend key moments use match id fallback for clip ids', () {
    final LiveMatchSnapshot snapshot = liveMatchSnapshotFromPayload(
      <String, Object?>{
        'match_id': 'match-key',
        'home_team_name': 'Lagos United',
        'away_team_name': 'Accra City',
        'home_score': 1,
        'away_score': 0,
        'minute': 31,
        'status': 'live',
        'key_moments': <Object?>[
          <String, Object?>{
            'title': 'Backend key moment',
            'minute': 31,
            'duration_seconds': 8,
          },
        ],
      },
      competition: _competition(),
    );

    expect(snapshot.keyMoments.single.id, 'match-key-highlight-0');
    expect(snapshot.keyMoments.single.isPremium, isTrue);
    expect(snapshot.commentary, isEmpty);
  });

  test('canonical overlay payload parser maps all overlay modes', () {
    final LiveMatchSnapshot snapshot = liveMatchSnapshotFromPayload(
      <String, Object?>{
        ..._baseLivePayload(),
        'overlay_payload': <String, Object?>{
          'shape': <String, Object?>{
            'home_formation': '4-3-3',
            'away_formation': '4-2-3-1',
          },
          'pressure': <String, Object?>{'home': 63, 'away': 37},
          'shots': <String, Object?>{
            'home': 9,
            'away': 4,
            'markers': <Object?>[
              <String, Object?>{'x': 72, 'y': 41, 'xg': 0.23, 'team': 'home'},
              <String, Object?>{
                'pitch_x': 22,
                'pitch_y': 53,
                'expected_goals': '0.05',
                'side': 'away',
              },
            ],
          },
          'shots_on_target': <String, Object?>{'home': 4, 'away': 2},
          'xg': <String, Object?>{'home': '1.42', 'away': '0.55'},
          'territory': <String, Object?>{'home_pct': '58%', 'away_pct': '42%'},
          'market': <String, Object?>{
            'signal': 'Bid pressure rising',
            'detail': 'Order book imbalance is widening from verified feed.',
          },
        },
      },
      competition: _competition(),
    );

    final LiveMatchStatsSnapshot stats = snapshot.stats!;
    expect(stats.supportsOverlay(LiveMatchOverlayMode.shape), isTrue);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.pressure), isTrue);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.shots), isTrue);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.xg), isTrue);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.territory), isTrue);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.market), isTrue);
    expect(stats.pressure!.home, 63);
    expect(stats.shots!.away, 4);
    expect(stats.shotsOnTarget!.home, 4);
    expect(stats.expectedGoals!.home, 1.42);
    expect(stats.territory!.homeLabel(), '58%');
    expect(stats.marketSignal, 'Bid pressure rising');
    expect(stats.shotMap, hasLength(2));
    expect(stats.shotMap.first.x, closeTo(0.72, 0.001));
    expect(stats.shotMap.last.isHome, isFalse);
  });

  test('malformed and missing overlay payloads do not invent metrics', () {
    final LiveMatchSnapshot missing = liveMatchSnapshotFromPayload(
      _baseLivePayload(),
      competition: _competition(),
    );
    expect(missing.stats, isNull);

    final LiveMatchSnapshot malformed = liveMatchSnapshotFromPayload(
      <String, Object?>{
        ..._baseLivePayload(matchId: 'match-malformed-overlay'),
        'overlays': <String, Object?>{
          'pressure': <String, Object?>{'home': '64', 'away': 36},
          'shots': <String, Object?>{
            'markers': <Object?>[
              <String, Object?>{'x': 'bad', 'y': 40, 'xg': 0.2},
              <String, Object?>{'x': 50},
            ],
          },
          'xg': <String, Object?>{'home': 'bad', 'away': null},
          'market': <String, Object?>{'signal': '', 'detail': ''},
        },
      },
      competition: _competition(),
    );

    final LiveMatchStatsSnapshot stats = malformed.stats!;
    expect(stats.supportsOverlay(LiveMatchOverlayMode.shape), isTrue);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.pressure), isTrue);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.shots), isFalse);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.xg), isFalse);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.territory), isFalse);
    expect(stats.supportsOverlay(LiveMatchOverlayMode.market), isFalse);
    expect(stats.pressure!.home, 64);
    expect(stats.shotMap, isEmpty);
  });

  test('degraded live intelligence is represented when feed says degraded', () {
    final LiveMatchSnapshot snapshot = liveMatchSnapshotFromPayload(
      <String, Object?>{
        ..._baseLivePayload(matchId: 'match-degraded-intel'),
        'overlay_payload': 'temporarily unavailable',
        'live_intelligence': <String, Object?>{'status': 'degraded'},
      },
      competition: _competition(),
    );

    expect(snapshot.stats, isNull);
    expect(snapshot.liveIntelligence!.status, 'degraded');
    expect(snapshot.liveIntelligence!.hasSignals, isFalse);
  });

  test('live intelligence parser maps summary, timestamp and signals', () {
    final DateTime updatedAt = DateTime.utc(2026, 5, 29, 9, 30);
    final LiveMatchSnapshot snapshot = liveMatchSnapshotFromPayload(
      <String, Object?>{
        ..._baseLivePayload(matchId: 'match-intel'),
        'liveIntelligence': <String, Object?>{
          'status': 'provided',
          'summary': 'Verified pressure swing from backend feed.',
          'updated_at': updatedAt.toIso8601String(),
          'signals': <Object?>[
            <String, Object?>{
              'headline': 'High press flagged',
              'description': 'Home side has forced three regains.',
              'severity': 'warning',
              'provider': 'ops-model',
            },
            'Away bench is preparing a verified substitution.',
          ],
        },
      },
      competition: _competition(),
    );

    final LiveMatchLiveIntelligence intelligence = snapshot.liveIntelligence!;
    expect(intelligence.status, 'provided');
    expect(intelligence.summary, 'Verified pressure swing from backend feed.');
    expect(intelligence.updatedAt, updatedAt);
    expect(intelligence.signals, hasLength(2));
    expect(intelligence.signals.first.title, 'High press flagged');
    expect(intelligence.signals.first.severity, 'warning');
    expect(intelligence.signals.first.source, 'ops-model');
    expect(
      intelligence.signals.last.detail,
      'Away bench is preparing a verified substitution.',
    );
  });

  test(
    'backend payload parser rejects missing scores instead of inventing them',
    () {
      expect(
        () => liveMatchSnapshotFromPayload(<String, Object?>{
          'match_id': 'match-no-score',
          'home_team_name': 'Lagos United',
          'away_team_name': 'Accra City',
          'minute': 12,
          'status': 'live',
        }, competition: _competition()),
        throwsA(isA<GteParsingException>()),
      );
    },
  );

  test('merge keeps explicit fallback events when event payload is absent', () {
    const LiveMatchEvent backendEvent = LiveMatchEvent(
      minute: 12,
      title: 'Backend event',
      detail: 'Verified feed event.',
      team: 'Lagos United',
      type: LiveMatchEventType.incident,
    );
    final LiveMatchSnapshot current = LiveMatchSnapshot(
      matchId: 'match-abc',
      homeTeam: 'Lagos United',
      awayTeam: 'Accra City',
      homeScore: 1,
      awayScore: 1,
      minute: 50,
      phase: LiveMatchPhase.secondHalf,
      momentum: const <int>[],
      commentary: const <LiveMatchEvent>[backendEvent],
      homeLineup: const <LiveMatchLineupPlayer>[],
      awayLineup: const <LiveMatchLineupPlayer>[],
      substitutions: const <LiveMatchEvent>[],
      cards: const <LiveMatchEvent>[],
      tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
      keyMoments: const <LiveMatchHighlightClip>[],
      highlights: const <LiveMatchHighlightClip>[],
      standardHighlightExpiresAt: DateTime.fromMillisecondsSinceEpoch(
        0,
        isUtc: true,
      ),
      premiumHighlightExpiresAt: DateTime.fromMillisecondsSinceEpoch(
        0,
        isUtc: true,
      ),
    );

    final LiveMatchSnapshot merged = mergeLiveMatchSnapshotPayload(
      current,
      <String, Object?>{
        'highlights': <Object?>[
          <String, Object?>{
            'title': 'Backend clip',
            'minute': 50,
            'duration_seconds': 10,
          },
        ],
      },
    );

    expect(merged.commentary, const <LiveMatchEvent>[backendEvent]);
    expect(merged.highlights.single.id, 'match-abc-highlight-0');
    expect(merged.homeScore, 1);
    expect(merged.awayScore, 1);
  });

  test('merge keeps backend truth while applying partial parser updates', () {
    const LiveMatchIntelligenceSignal existingSignal =
        LiveMatchIntelligenceSignal(
          title: 'Backend signal',
          detail: 'Original backend intelligence remains relevant.',
          severity: 'info',
          source: 'ops',
        );
    final LiveMatchSnapshot current = LiveMatchSnapshot(
      matchId: 'backend-match-42',
      homeTeam: 'Lagos United',
      awayTeam: 'Accra City',
      homeScore: 2,
      awayScore: 1,
      minute: 61,
      phase: LiveMatchPhase.secondHalf,
      momentum: const <int>[1, 2, 3],
      commentary: const <LiveMatchEvent>[],
      homeLineup: const <LiveMatchLineupPlayer>[],
      awayLineup: const <LiveMatchLineupPlayer>[],
      substitutions: const <LiveMatchEvent>[],
      cards: const <LiveMatchEvent>[],
      tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
      keyMoments: const <LiveMatchHighlightClip>[],
      highlights: const <LiveMatchHighlightClip>[],
      standardHighlightExpiresAt: DateTime.fromMillisecondsSinceEpoch(
        0,
        isUtc: true,
      ),
      premiumHighlightExpiresAt: DateTime.fromMillisecondsSinceEpoch(
        0,
        isUtc: true,
      ),
      stats: const LiveMatchStatsSnapshot(
        possession: LiveMatchStatPair(home: 55, away: 45, unit: '%'),
        expectedGoals: LiveMatchStatPair(home: 1.1, away: 0.8),
        marketSignal: 'Backend market signal',
        shotMap: <LiveMatchShotMarker>[
          LiveMatchShotMarker(x: 0.7, y: 0.4, xg: 0.18, team: 'home'),
        ],
      ),
      liveIntelligence: const LiveMatchLiveIntelligence(
        status: 'provided',
        summary: 'Original backend summary.',
        signals: <LiveMatchIntelligenceSignal>[existingSignal],
      ),
    );

    final LiveMatchSnapshot merged = mergeLiveMatchSnapshotPayload(
      current,
      <String, Object?>{
        'minute': 66,
        'status': 'live',
        'overlay_payload': <String, Object?>{
          'pressure': <String, Object?>{'home': 71, 'away': 29},
        },
        'live_intelligence': <String, Object?>{'status': 'degraded'},
      },
      competition: _competition(),
    );

    expect(merged.matchId, 'backend-match-42');
    expect(merged.homeScore, 2);
    expect(merged.awayScore, 1);
    expect(merged.minute, 66);
    expect(merged.stats!.pressure!.home, 71);
    expect(merged.stats!.possession!.home, 55);
    expect(merged.stats!.expectedGoals!.away, 0.8);
    expect(merged.stats!.marketSignal, 'Backend market signal');
    expect(merged.stats!.shotMap.single.xg, 0.18);
    expect(merged.liveIntelligence!.status, 'degraded');
    expect(merged.liveIntelligence!.summary, 'Original backend summary.');
    expect(merged.liveIntelligence!.signals.single, existingSignal);
  });

  test('live loader does not synthesize fixture snapshots', () async {
    await expectLater(
      loadLiveMatchSnapshot(
        _competition(),
        api: GteExchangeApiClient.fixture(),
      ),
      throwsA(
        isA<GteApiException>().having(
          (GteApiException error) => error.type,
          'type',
          GteApiErrorType.unavailable,
        ),
      ),
    );
  });
}

Map<String, Object?> _baseLivePayload({String matchId = 'match-abc'}) {
  return <String, Object?>{
    'match_id': matchId,
    'home_team_name': 'Lagos United',
    'away_team_name': 'Accra City',
    'home_score': 0,
    'away_score': 0,
    'minute': 12,
    'status': 'live',
    'phase': 'first_half',
  };
}

CompetitionSummary _competition() {
  final DateTime timestamp = DateTime.utc(2026);
  return CompetitionSummary(
    id: 'competition-1',
    name: 'Backend Cup',
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.inProgress,
    creatorId: 'gtex',
    creatorName: 'GTEX',
    participantCount: 2,
    capacity: 2,
    currency: 'FC',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Backend owned live match.',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: false),
    beginnerFriendly: true,
    createdAt: timestamp,
    updatedAt: timestamp,
  );
}
