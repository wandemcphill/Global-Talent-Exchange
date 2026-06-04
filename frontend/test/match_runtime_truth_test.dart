import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/realtime/realtime.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/features/match_center/services/match_viewer_mapper.dart';

void main() {
  test('fixture mode cannot generate canonical live match snapshots', () async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'live-feed-truth',
    );

    await expectLater(
      loadLiveMatchSnapshot(
        competition,
        config: const GteAppConfig(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
        ),
      ),
      throwsA(
        isA<GteApiException>()
            .having(
              (GteApiException error) => error.type,
              'type',
              GteApiErrorType.unavailable,
            )
            .having(
              (GteApiException error) => error.message,
              'message',
              contains('backend-authored websocket or live snapshot'),
            ),
      ),
    );
  });

  test(
    'match viewer mapper rejects fixture mode before local frames',
    () async {
      final CompetitionSummary competition = _buildCompetition(
        id: 'viewer-truth',
      );

      await expectLater(
        MatchViewerMapper.load(
          competition: competition,
          matchKey: competition.id,
          config: const GteAppConfig(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
        ),
        throwsA(
          isA<StateError>().having(
            (StateError error) => error.message,
            'message',
            contains('backend-authored timeline frames'),
          ),
        ),
      );
    },
  );

  test('live match viewer mapper requires backend-authored frames', () {
    final CompetitionSummary competition = _buildCompetition(
      id: 'viewer-live-frame-truth',
    );
    final GteExchangeApiClient api = GteExchangeApiClient(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.live,
      ),
      transport: const _MissingFramesMatchViewerTransport(),
      repository: GteMockApi(),
    );

    expect(
      MatchViewerMapper.load(
        competition: competition,
        matchKey: competition.id,
        config: const GteAppConfig(
          apiBaseUrl: 'https://example.test',
          backendMode: GteBackendMode.live,
        ),
        api: api,
      ),
      throwsA(
        isA<GteApiException>()
            .having(
              (GteApiException error) => error.type,
              'type',
              GteApiErrorType.parsing,
            )
            .having(
              (GteApiException error) => error.message,
              'message',
              contains('backend-authored timeline frames'),
            ),
      ),
    );
  });

  test('websocket realtime parser drops locally inferred events', () {
    expect(
      LiveMatchRealtimePayloadMapper.decode(
        'String-only commentary should not become backend truth.',
        source: LiveMatchRealtimeSource.commentaryWebSocket,
      ).payload,
      isNull,
    );
    expect(
      LiveMatchRealtimePayloadMapper.decode(<String, Object?>{
        'event_type': 'goal',
        'commentary': 'Backend line without clock.',
      }, source: LiveMatchRealtimeSource.commentaryWebSocket).payload,
      isNull,
    );
    expect(
      LiveMatchRealtimePayloadMapper.decode(<String, Object?>{
        'minute': 44,
        'event_type': 'goal',
      }, source: LiveMatchRealtimeSource.commentaryWebSocket).payload,
      isNull,
    );

    final LiveMatchRealtimePayloadResult parsed =
        LiveMatchRealtimePayloadMapper.decode(<String, Object?>{
          'minute': 44,
          'event_type': 'goal',
          'commentary': 'Backend-authored goal call.',
        }, source: LiveMatchRealtimeSource.commentaryWebSocket);

    final List<Object?> events = parsed.payload?['events'] as List<Object?>;
    final Map<String, Object?> event = events.single as Map<String, Object?>;
    expect(event['minute'], 44);
    expect(event['commentary'], 'Backend-authored goal call.');
  });
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'Runtime truth test',
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
    rulesSummary: 'Runtime truth coverage',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}

class _MissingFramesMatchViewerTransport implements GteTransport {
  const _MissingFramesMatchViewerTransport();

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return const GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{
        'match_id': 'viewer-live-frame-truth',
        'source': 'backend-live',
        'supports_offside': true,
        'duration_seconds': 90,
        'home_team': <String, Object?>{
          'team_id': 'home',
          'team_name': 'Lagos Exchange',
          'short_name': 'LAG',
          'side': 'home',
          'formation': '4-3-3',
          'primary_color': '#103B2F',
          'secondary_color': '#F8FAFC',
          'accent_color': '#D6A11E',
          'goalkeeper_color': '#111827',
        },
        'away_team': <String, Object?>{
          'team_id': 'away',
          'team_name': 'Accra Capital',
          'short_name': 'ACC',
          'side': 'away',
          'formation': '4-2-3-1',
          'primary_color': '#1E3A8A',
          'secondary_color': '#F8FAFC',
          'accent_color': '#38BDF8',
          'goalkeeper_color': '#0F172A',
        },
        'events': <Object?>[
          <String, Object?>{
            'id': 'backend-event-with-position',
            'sequence': 1,
            'type': 'chance',
            'minute': 12,
            'time_seconds': 72,
            'clock_label': "12'",
            'home_score': 0,
            'away_score': 0,
            'x': 64,
            'y': 42,
          },
        ],
        'frames': <Object?>[],
      },
    );
  }
}
