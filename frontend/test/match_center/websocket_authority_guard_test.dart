import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/match_center/services/match_viewer_mapper.dart';
import 'package:gte_frontend/models/match_type.dart';

void main() {
  test(
    'fixture mode cannot generate a canonical live match snapshot',
    () async {
      await expectLater(
        loadLiveMatchSnapshot(_competition(), config: _fixtureConfig),
        throwsA(isA<GteApiException>()),
      );
    },
  );

  test('fixture mode cannot generate local match viewer frames', () async {
    await expectLater(
      MatchViewerMapper.load(
        competition: _competition(),
        matchKey: 'match-1',
        config: _fixtureConfig,
      ),
      throwsA(isA<StateError>()),
    );
  });

  test('timeline frames ignore local pause and injected event controls', () {
    final MatchTimelineFrame frame = MatchTimelineFrame.fromJson(
      <String, Object?>{
        'frame_id': 'frame-1',
        'time_seconds': 42,
        'clock_minute': 17,
        'phase': 'open_play',
        'home_score': 0,
        'away_score': 0,
        'home_attacks_right': true,
        'possession_side': 'home',
        'pause_playback': true,
        'injected_events': <Object?>[
          <String, Object?>{
            'id': 'local-goal',
            'type': 'goal',
            'banner_text': 'Injected goal',
            'start_seconds': 40,
            'peak_seconds': 42,
            'end_seconds': 45,
          },
        ],
        'players': const <Object?>[],
        'ball': const <String, Object?>{
          'position': <String, Object?>{'x': 50, 'y': 50},
          'state': 'rolling',
        },
      },
    );

    expect(frame.pausePlayback, isFalse);
    expect(frame.injectedEvents, isEmpty);
  });

  test(
    'event-only match viewer payloads do not synthesize timeline frames',
    () {
      final MatchViewState state = MatchViewState.fromJson(<String, Object?>{
        'match_id': 'event-only-authority-test',
        'source': 'backend-test',
        'duration_seconds': 90,
        'home_team': _team('home', 'Lagos United', 'LAG'),
        'away_team': _team('away', 'Accra City', 'ACC'),
        'events': <Object?>[
          <String, Object?>{
            'event_id': 'event-1',
            'sequence': 1,
            'event_type': 'goal',
            'minute': 12,
            'clock_label': '12:00',
            'time_seconds': 720,
            'team_id': 'home',
            'team_name': 'Lagos United',
            'primary_player_id': 'home-9',
            'primary_player_name': 'Ayo Mensah',
            'home_score': 1,
            'away_score': 0,
            'banner_text': 'Goal',
            'duration_ms': 900,
            'positions': <Object?>[
              <String, Object?>{
                'player_id': 'home-9',
                'player_name': 'Ayo Mensah',
                'team_id': 'home',
                'side': 'home',
                'shirt_number': 9,
                'role': 'forward',
                'line': 'attack',
                'position': <String, Object?>{'x': 42, 'y': 48},
              },
            ],
            'ball': const <String, Object?>{
              'position': <String, Object?>{'x': 42, 'y': 48},
              'owner_player_id': 'home-9',
              'state': 'shot',
            },
          },
        ],
        'frames': const <Object?>[],
      });

      expect(state.events, hasLength(1));
      expect(state.frames, isEmpty);
    },
  );
}

Map<String, Object?> _team(String id, String name, String shortName) {
  return <String, Object?>{
    'team_id': id,
    'team_name': name,
    'short_name': shortName,
    'side': id,
    'formation': '4-3-3',
    'primary_color': '#14532D',
    'secondary_color': '#F8FAFC',
    'accent_color': '#22C55E',
    'goalkeeper_color': '#EC4899',
  };
}

const GteAppConfig _fixtureConfig = GteAppConfig(
  apiBaseUrl: 'http://example.test',
  backendMode: GteBackendMode.fixture,
);

CompetitionSummary _competition() {
  final DateTime now = DateTime.utc(2026, 1, 1);
  return CompetitionSummary(
    id: 'competition-1',
    name: 'Canonical Cup',
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.inProgress,
    creatorId: 'creator-1',
    creatorName: 'GTEX',
    participantCount: 2,
    capacity: 2,
    currency: 'USD',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Backend-authored match center only.',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: false),
    beginnerFriendly: true,
    createdAt: now,
    updatedAt: now,
  );
}
