import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/player_match_service.dart';
import 'package:gte_frontend/domain/match/match_weight_presets.dart';

void main() {
  test('match service ranks exact fits ahead of partial fits', () async {
    final GtePlayerMatchService service = GtePlayerMatchService(
      latency: Duration.zero,
    );

    final List<GteMarketPlayerListItem> players = <GteMarketPlayerListItem>[
      const GteMarketPlayerListItem(
        playerId: 'victor',
        playerName: 'Victor Demo',
        position: 'ST',
        nationality: 'Nigeria',
        currentClubName: 'Free Agent',
        age: 24,
        currentValueCredits: 900,
        movementPct: 0.08,
        trendScore: 8.3,
        marketInterestScore: 82,
        averageRating: 7.6,
        isAvailable: true,
        availabilityLabel: 'Free Agent',
        askingType: 'market_value',
        agentUserId: 'agent-victor',
        agentName: 'Scout board',
      ),
      const GteMarketPlayerListItem(
        playerId: 'mina',
        playerName: 'Mina Creator',
        position: 'AM',
        nationality: 'Ghana',
        currentClubName: 'Accra Stars',
        age: 22,
        currentValueCredits: 760,
        movementPct: 0.02,
        trendScore: 7.1,
        marketInterestScore: 64,
        averageRating: 7.2,
        isAvailable: true,
        availabilityLabel: 'Transfer listed',
        askingType: 'market_value',
        agentUserId: 'agent-mina',
        agentName: 'Scout board',
      ),
      const GteMarketPlayerListItem(
        playerId: 'senior-striker',
        playerName: 'Senior Striker',
        position: 'ST',
        nationality: 'Nigeria',
        currentClubName: 'Abuja City',
        age: 30,
        currentValueCredits: 640,
        movementPct: -0.01,
        trendScore: 6.8,
        marketInterestScore: 58,
        averageRating: 6.9,
        isAvailable: true,
        availabilityLabel: 'Club controlled',
        askingType: 'market_value',
        agentUserId: 'agent-senior',
        agentName: 'Scout board',
      ),
    ];

    final List<GtePlayerMatchResult> matches = await service.getMatches(
      players: players,
      filters: const GteScoutMatchFilters.defaultBrief(),
      limit: 3,
    );

    expect(matches, hasLength(3));
    expect(matches.first.player.playerId, 'victor');
    expect(matches.first.score, 1.0);
    expect(matches.first.reasons, contains('Perfect position match'));
    expect(matches.first.reasons, contains('Preferred foot matches'));
    expect(matches.first.reasons, contains('Free-agent bonus'));

    expect(matches[1].player.playerId, 'senior-striker');
    expect(matches[1].score, lessThan(matches.first.score));
    expect(matches[2].player.playerId, 'mina');
  });

  test('filters parse from api-shaped json payload', () {
    final GteScoutMatchFilters filters = GteScoutMatchFilters.fromJson(
      <String, dynamic>{
        'position': 'ST',
        'min_age': 18,
        'max_age': 27,
        'country': 'Nigeria',
        'preferred_foot': 'Right',
        'min_height': 1.75,
      },
    );

    expect(filters.position, 'ST');
    expect(filters.minAge, 18);
    expect(filters.maxAge, 27);
    expect(filters.country, 'Nigeria');
    expect(filters.preferredFoot, 'Right');
    expect(filters.minHeightMeters, 1.75);
    expect(
        filters.summaryLabels(),
        containsAll(<String>[
          'ST',
          '18-27',
          'Nigeria',
          'Right foot',
          '1.75m+',
        ]));
  });

  test('custom weights can favor ready-now free agents over younger targets',
      () async {
    final GtePlayerMatchService service = GtePlayerMatchService(
      latency: Duration.zero,
    );

    final List<GteMarketPlayerListItem> players = <GteMarketPlayerListItem>[
      const GteMarketPlayerListItem(
        playerId: 'ready-now',
        playerName: 'Ready Now',
        position: 'ST',
        nationality: 'Nigeria',
        currentClubName: 'Free Agent',
        age: 30,
        currentValueCredits: 900,
        movementPct: 0.04,
        trendScore: 7.3,
        marketInterestScore: 79,
        averageRating: 7.1,
      ),
      const GteMarketPlayerListItem(
        playerId: 'younger-fit',
        playerName: 'Younger Fit',
        position: 'ST',
        nationality: 'Nigeria',
        currentClubName: 'Abuja City',
        age: 23,
        currentValueCredits: 880,
        movementPct: 0.03,
        trendScore: 7.0,
        marketInterestScore: 75,
        averageRating: 7.2,
      ),
    ];

    final List<GtePlayerMatchResult> defaultMatches = await service.getMatches(
      players: players,
      filters: const GteScoutMatchFilters.defaultBrief(),
      limit: 2,
    );
    final List<GtePlayerMatchResult> readyNowMatches = await service.getMatches(
      players: players,
      filters: const GteScoutMatchFilters.defaultBrief(),
      weights: MatchWeightPresets.readyNow(),
      limit: 2,
    );

    expect(defaultMatches.first.player.playerId, 'younger-fit');
    expect(readyNowMatches.first.player.playerId, 'ready-now');
  });

  test('match service sends normalized weights in the backend payload',
      () async {
    final _RecordingMatchTransport transport = _RecordingMatchTransport();
    final GteExchangeApiClient client = GteExchangeApiClient(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      repository: GteMockApi(),
    );
    final GtePlayerMatchService service = GtePlayerMatchService(
      api: client,
      latency: Duration.zero,
    );

    final List<GtePlayerMatchResult> matches = await service.getMatches(
      players: const <GteMarketPlayerListItem>[
        GteMarketPlayerListItem(
          playerId: 'local-fallback',
          playerName: 'Local Fallback',
          position: 'ST',
          nationality: 'Nigeria',
          currentClubName: 'Free Agent',
          age: 24,
          currentValueCredits: 900,
          movementPct: 0.04,
          trendScore: 7.2,
          marketInterestScore: 80,
          averageRating: 7.0,
        ),
      ],
      filters: const GteScoutMatchFilters.defaultBrief(),
      weights: MatchWeightPresets.readyNow(),
      limit: 3,
    );

    expect(transport.lastRequest, isNotNull);
    expect(transport.lastRequest!.uri.path, '/api/v2/players/match');

    final Map<String, Object?> body =
        Map<String, Object?>.from(transport.lastRequest!.body! as Map);
    final Map<String, Object?> brief =
        Map<String, Object?>.from(body['brief']! as Map);
    final Map<String, Object?> pagination =
        Map<String, Object?>.from(body['pagination']! as Map);
    final Map<String, Object?> weights =
        Map<String, Object?>.from(body['weights']! as Map);

    expect(brief['positions'], <String>['ST']);
    expect(
      Map<String, Object?>.from(brief['age']! as Map),
      <String, Object?>{'min': 18, 'max': 27},
    );
    expect(pagination['limit'], 3);
    expect(weights['availability'], closeTo(0.2, 0.0001));
    expect(matches.single.player.playerName, 'Remote Target');
  });
}

class _RecordingMatchTransport implements GteTransport {
  GteTransportRequest? lastRequest;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    lastRequest = request;
    requests.add(request);
    return const GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{
        'matches': <Object?>[
          <String, Object?>{
            'player_id': 'remote-target',
            'score': 0.82,
            'score_breakdown': <String, Object?>{
              'position': 1.0,
              'age': 1.0,
              'country': 1.0,
              'height': 1.0,
              'foot': 1.0,
              'availability': 1.0,
            },
            'reasons': <Object?>[
              <String, Object?>{
                'type': 'position',
                'label': 'Perfect position match',
                'impact': '+0.45',
              },
            ],
            'flags': <String, Object?>{
              'is_free_agent': true,
              'is_exact_position': true,
              'is_high_potential': false,
            },
            'player': <String, Object?>{
              'player_id': 'remote-target',
              'player_name': 'Remote Target',
              'name': 'Remote Target',
              'age': 24,
              'position': 'ST',
              'country': 'Nigeria',
              'nationality': 'Nigeria',
              'height_cm': 183,
              'preferred_foot': 'Right',
              'club': null,
              'current_club_name': null,
            },
          },
        ],
        'meta': <String, Object?>{
          'total_candidates': 1,
          'scored_candidates': 1,
          'returned': 1,
          'next_cursor': null,
          'has_more': false,
        },
        'summary': <String, Object?>{
          'average_score': 0.82,
          'top_score': 0.82,
          'distribution': <String, Object?>{
            '90_100': 0,
            '80_89': 1,
            '70_79': 0,
            'below_70': 0,
          },
        },
        'applied_config': <String, Object?>{
          'weights': <String, Object?>{
            'position': 0.45,
            'age': 0.10,
            'country': 0.05,
            'height': 0.10,
            'foot': 0.10,
            'availability': 0.20,
          },
          'constraints': <String, Object?>{
            'strict_position': true,
            'exclude_injured': false,
            'min_match_score': 0.55,
          },
        },
      },
    );
  }
}

