import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  const String testPassword = 'DemoPass123'; // pragma: allowlist secret

  test('live-then-fixture mode fails closed for market reads', () async {
    final _RecordingPlayersFixtureApi fixtures = _RecordingPlayersFixtureApi();
    final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.liveThenFixture,
      ),
      transport: _ThrowingTransport(),
      fixtures: fixtures,
    );

    await expectLater(
      repository.fetchPlayers(),
      throwsA(isA<GteApiException>()),
    );
    expect(fixtures.fetchPlayersCalls, 0);
  });

  test(
    'fetch players in live mode maps live payload without borrowing fixture snapshots',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Map<String, Object?>>[
                <String, Object?>{
                  'player_id': 'live-player',
                  'player_name': 'Live Prospect',
                  'current_value_credits': 640,
                  'trend_score': 76,
                  'movement_pct': 5.5,
                },
              ],
            },
          ),
        ],
      );
      final _RecordingPlayersFixtureApi fixtures =
          _RecordingPlayersFixtureApi();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: fixtures,
      );

      final List<PlayerSnapshot> players = await repository.fetchPlayers();

      expect(fixtures.fetchPlayersCalls, 0);
      expect(players, hasLength(1));
      expect(players.single.id, 'live-player');
      expect(players.single.name, 'Live Prospect');
      expect(players.single.club, 'Unknown club');
      expect(players.single.nation, 'Unknown nation');
      expect(players.single.position, 'N/A');
      expect(players.single.age, 0);
      expect(players.single.marketCredits, 640);
      expect(players.single.gsi, 76);
      expect(players.single.formRating, 0);
      expect(players.single.valueDeltaPct, 5.5);
      expect(players.single.recentHighlights, isEmpty);
      expect(players.single.inTransferRoom, isFalse);
    },
  );

  test(
    'fetch players in fixture mode still returns fixture snapshots',
    () async {
      final _RecordingPlayersFixtureApi fixtures =
          _RecordingPlayersFixtureApi();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: fixtures,
      );

      final List<PlayerSnapshot> players = await repository.fetchPlayers();

      expect(fixtures.fetchPlayersCalls, 1);
      expect(players, hasLength(1));
      expect(players.single.id, 'fixture-player');
      expect(players.single.club, 'Fixture FC');
    },
  );

  test(
    'login does not fall back to fixture auth on transport failure',
    () async {
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: GteMockApi(latency: Duration.zero),
      );

      expect(
        () => repository.login(
          const GteAuthLoginRequest(
            email: 'qa@example.com',
            password: testPassword,
          ),
        ),
        throwsA(isA<GteApiException>()),
      );
    },
  );

  test('register rejects removed generic signup without transport', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'success': true,
            'data': <String, Object?>{
              'access_token': 'live-token',
              'session_id': 'live-session',
              'token_type': 'bearer',
              'expires_in': 3600,
              'user': <String, Object?>{
                'id': 'user-1',
                'email': 'qa@example.com',
                'username': 'qa_user',
                'display_name': 'QA User',
                'role': 'user',
              },
            },
          },
        ),
      ],
    );
    final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: GteMockApi(latency: Duration.zero),
    );

    await expectLater(
      () => repository.register(
        const GteAuthRegisterRequest(
          email: 'qa@example.com',
          fullName: 'QA User',
          phoneNumber: '08000000000',
          isOver18: true,
          regionCode: 'ng',
          password: testPassword,
        ),
      ),
      throwsA(isA<UnsupportedError>()),
    );

    expect(transport.requests, isEmpty);
  });

  test(
    'register ignores queued validation responses for removed endpoint',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 422,
            body: <String, Object?>{
              'detail': <Map<String, Object?>>[
                <String, Object?>{
                  'loc': <Object?>['body', 'region_code'],
                  'msg': 'Field required',
                },
              ],
            },
          ),
        ],
      );
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(latency: Duration.zero),
      );

      await expectLater(
        () => repository.register(
          const GteAuthRegisterRequest(
            email: 'qa@example.com',
            fullName: 'QA User',
            phoneNumber: '08000000000',
            isOver18: true,
            regionCode: 'NG',
            password: testPassword,
          ),
        ),
        throwsA(isA<UnsupportedError>()),
      );
      expect(transport.requests, isEmpty);
    },
  );

  test(
    'fetch current user does not fall back to fixture auth on transport failure',
    () async {
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      await tokenStore.writeToken('stale-token');
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: GteMockApi(latency: Duration.zero),
        tokenStore: tokenStore,
      );

      expect(repository.fetchCurrentUser, throwsA(isA<GteApiException>()));
    },
  );

  test(
    'policy document reads fail closed in live mode without consulting fixtures',
    () async {
      await _expectPolicyDocumentSurfaceFailuresWithoutFixtureFallback(
        GteBackendMode.live,
      );
    },
  );

  test(
    'policy document reads no longer fall back to fixtures in live-then-fixture mode',
    () async {
      await _expectPolicyDocumentSurfaceFailuresWithoutFixtureFallback(
        GteBackendMode.liveThenFixture,
      );
    },
  );

  test(
    'policy document reads still resolve from fixtures in explicit fixture mode',
    () async {
      final _RecordingPolicyFixtureApi fixtures = _RecordingPolicyFixtureApi();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: fixtures,
      );

      final List<GtePolicyDocumentSummary> documents = await repository
          .fetchPolicyDocuments(mandatoryOnly: true);
      final GtePolicyDocumentDetail detail = await repository
          .fetchPolicyDocument('terms_and_conditions');

      expect(fixtures.fetchPolicyDocumentsCalls, 1);
      expect(fixtures.fetchPolicyDocumentCalls, 1);
      expect(documents, isNotEmpty);
      expect(
        documents.every((GtePolicyDocumentSummary doc) => doc.isMandatory),
        isTrue,
      );
      expect(
        documents.any(
          (GtePolicyDocumentSummary doc) =>
              doc.documentKey == 'terms_and_conditions',
        ),
        isTrue,
      );
      expect(detail.documentKey, 'terms_and_conditions');
      expect(detail.title, 'Terms & Conditions');
    },
  );

  test(
    'policy acceptance reads fail closed in live mode without consulting fixtures',
    () async {
      await _expectPolicyAcceptanceSurfaceFailuresWithoutFixtureFallback(
        GteBackendMode.live,
      );
    },
  );

  test(
    'policy acceptance reads no longer fall back to fixtures in live-then-fixture mode',
    () async {
      await _expectPolicyAcceptanceSurfaceFailuresWithoutFixtureFallback(
        GteBackendMode.liveThenFixture,
      );
    },
  );

  test(
    'policy acceptance reads still resolve from fixtures in explicit fixture mode',
    () async {
      final _RecordingPolicyFixtureApi fixtures = _RecordingPolicyFixtureApi();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: fixtures,
      );

      final List<GtePolicyAcceptanceSummary> acceptances =
          await repository.fetchMyPolicyAcceptances();

      expect(fixtures.fetchMyPolicyAcceptancesCalls, 1);
      expect(acceptances, isNotEmpty);
      expect(acceptances.single.documentKey, 'terms_and_conditions');
      expect(acceptances.single.title, 'Terms & Conditions');
      expect(acceptances.single.versionLabel, 'v1.0');
      expect(acceptances.single.acceptedAt, DateTime.utc(2026, 3, 2, 10));
    },
  );

  test(
    'fetch market pulse in live mode derives pulse from live players without borrowing fixture pulse data',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Map<String, Object?>>[
                <String, Object?>{
                  'player_id': 'victor-osimhen',
                  'player_name': 'Victor Osimhen',
                  'current_club_name': 'Galatasaray',
                  'nationality': 'Nigeria',
                  'position': 'ST',
                  'age': 27,
                  'current_value_credits': 920,
                  'trend_score': 84,
                  'average_rating': 7.3,
                  'movement_pct': 6.1,
                },
                <String, Object?>{
                  'player_id': 'lamine-yamal',
                  'player_name': 'Lamine Yamal',
                  'current_club_name': 'Barcelona',
                  'nationality': 'Spain',
                  'position': 'RW',
                  'age': 18,
                  'current_value_credits': 1180,
                  'trend_score': 93,
                  'average_rating': 7.8,
                  'movement_pct': 7.8,
                },
              ],
            },
          ),
        ],
      );
      final _RecordingPulseFixtureApi fixtures = _RecordingPulseFixtureApi();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: fixtures,
      );

      final MarketPulse pulse = await repository.fetchMarketPulse();

      expect(fixtures.fetchMarketPulseCalls, 0);
      expect(pulse.marketMomentum, closeTo(6.95, 0.001));
      expect(pulse.dailyVolumeCredits, 2100);
      expect(pulse.liveDeals, 0);
      expect(pulse.hottestLeague, 'Global Exchange');
      expect(pulse.tickers, <String>[
        'Victor Osimhen +6.1%',
        'Lamine Yamal +7.8%',
      ]);
      expect(pulse.transferRoom, isEmpty);
    },
  );

  test(
    'fetch market pulse in fixture mode still returns fixture pulse',
    () async {
      final _RecordingPulseFixtureApi fixtures = _RecordingPulseFixtureApi();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: _ThrowingTransport(),
        fixtures: fixtures,
      );

      final MarketPulse pulse = await repository.fetchMarketPulse();

      expect(fixtures.fetchMarketPulseCalls, 1);
      expect(pulse.hottestLeague, 'Fixture Borrowed League');
      expect(pulse.transferRoom, hasLength(1));
      expect(pulse.transferRoom.single.id, 'fixture-pulse-entry');
    },
  );

  test(
    'fetch player profile maps native live market detail without fixture profile copy',
    () async {
      final _RecordingTransport
      transport = _RecordingTransport(<GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'identity': <String, Object?>{
              'player_name': 'Active Runtime Prospect',
              'current_club_name': 'Ibadan Lions FC',
              'nationality': 'Nigeria',
              'position': 'CM',
              'age': 21,
            },
            'value': <String, Object?>{
              'current_value_credits': 1200,
              'movement_pct': 4.5,
            },
            'trend': <String, Object?>{
              'global_scouting_index': 88,
              'average_rating': 7.2,
            },
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'symbol': 'A. Prospect',
            'last_price': 1200,
            'best_bid': 1190,
            'best_ask': 1210,
            'spread': 20,
            'mid_price': 1200,
            'reference_price': 1180,
            'day_change': 20,
            'day_change_percent': 1.69,
            'volume_24h': 4,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'interval': '1h',
            'candles': <Map<String, Object?>>[
              <String, Object?>{
                'timestamp': '2026-03-31T10:00:00Z',
                'open': 1180,
                'high': 1210,
                'low': 1175,
                'close': 1200,
                'volume': 4,
              },
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'generated_at': '2026-03-31T10:00:00Z',
            'bids': <Map<String, Object?>>[
              <String, Object?>{'price': 1190, 'quantity': 3, 'order_count': 1},
            ],
            'asks': <Map<String, Object?>>[
              <String, Object?>{'price': 1210, 'quantity': 2, 'order_count': 1},
            ],
          },
        ),
      ]);
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: _ThrowingProfileFixtureApi(),
      );

      final PlayerProfile profile = await repository.fetchPlayerProfile(
        'player-123',
      );

      expect(profile.snapshot.id, 'player-123');
      expect(profile.snapshot.name, 'Active Runtime Prospect');
      expect(profile.snapshot.club, 'Ibadan Lions FC');
      expect(profile.snapshot.marketCredits, 1200);
      expect(profile.snapshot.gsi, 88);
      expect(profile.snapshot.formRating, 7.2);
      expect(profile.snapshot.valueTrend, hasLength(1));
      expect(profile.gsiTrend, hasLength(1));
      expect(profile.awards, isEmpty);
      expect(profile.statBlocks, isEmpty);
      expect(profile.ticker?.playerId, 'player-123');
      expect(profile.orderBook?.playerId, 'player-123');
      expect(profile.candles?.playerId, 'player-123');
    },
  );

  test(
    'fetch player profile in live-then-fixture mode does not load legacy compatibility fixtures when live detail succeeds',
    () async {
      final _RecordingTransport
      transport = _RecordingTransport(<GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'identity': <String, Object?>{
              'player_name': 'Live Only Prospect',
              'current_club_name': 'Abuja Stars FC',
              'nationality': 'Nigeria',
              'position': 'ST',
              'age': 20,
            },
            'value': <String, Object?>{
              'current_value_credits': 950,
              'movement_pct': 2.5,
            },
            'trend': <String, Object?>{
              'global_scouting_index': 79,
              'average_rating': 7.0,
            },
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'symbol': 'L. Only',
            'last_price': 950,
            'best_bid': 940,
            'best_ask': 960,
            'spread': 20,
            'mid_price': 950,
            'reference_price': 930,
            'day_change': 20,
            'day_change_percent': 2.15,
            'volume_24h': 3,
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'interval': '1h',
            'candles': <Map<String, Object?>>[
              <String, Object?>{
                'timestamp': '2026-03-31T10:00:00Z',
                'open': 930,
                'high': 960,
                'low': 925,
                'close': 950,
                'volume': 3,
              },
            ],
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'player_id': 'player-123',
            'generated_at': '2026-03-31T10:00:00Z',
            'bids': <Map<String, Object?>>[
              <String, Object?>{'price': 940, 'quantity': 2, 'order_count': 1},
            ],
            'asks': <Map<String, Object?>>[
              <String, Object?>{'price': 960, 'quantity': 2, 'order_count': 1},
            ],
          },
        ),
      ]);
      final _RecordingProfileFixtureApi fixtures =
          _RecordingProfileFixtureApi();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.liveThenFixture,
        ),
        transport: transport,
        fixtures: fixtures,
      );

      final PlayerProfile profile = await repository.fetchPlayerProfile(
        'player-123',
      );

      expect(profile.snapshot.name, 'Live Only Prospect');
      expect(fixtures.fetchPlayerProfileCalls, 0);
    },
  );

  test(
    'fetch player profile in live mode does not fall back to fixture truth on transport failure',
    () async {
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: _ThrowingTransport(),
        fixtures: _ThrowingProfileFixtureApi(),
      );

      expect(
        () => repository.fetchPlayerProfile('player-123'),
        throwsA(
          isA<GteApiException>().having(
            (GteApiException error) => error.type,
            'type',
            GteApiErrorType.network,
          ),
        ),
      );
    },
  );

  test(
    'login persists token, merges bootstrap club context, and reuses it on authenticated requests',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'access_token': 'live-token',
              'session_id': 'live-session',
              'token_type': 'bearer',
              'expires_in': 3600,
              'user': <String, Object?>{
                'id': 'user-1',
                'email': 'qa@example.com',
                'username': 'qa_user',
                'display_name': 'QA User',
                'role': 'user',
              },
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'active_organization_id': 'ibadan-lions',
              'active_organization_name': 'Ibadan Lions FC',
              'active_organization_type': 'club',
              'club': <String, Object?>{
                'id': 'ibadan-lions',
                'name': 'Ibadan Lions FC',
              },
              'wallet': <String, Object?>{},
              'compliance': <String, Object?>{},
            },
          ),
          GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'id': 'user-1',
              'email': 'qa@example.com',
              'username': 'qa_user',
              'display_name': 'QA User',
              'role': 'user',
            },
          ),
        ],
      );
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(latency: Duration.zero),
        tokenStore: tokenStore,
        authSessionStore: authSessionStore,
      );

      final GteAuthSession session = await repository.login(
        const GteAuthLoginRequest(
          email: 'qa@example.com',
          password: testPassword,
        ),
      );
      final GteCurrentUser user = await repository.fetchCurrentUser();

      expect(session.accessToken, 'live-token');
      expect(session.sessionId, 'live-session');
      expect(session.rawJson['active_organization_id'], 'ibadan-lions');
      expect(await tokenStore.readToken(), 'live-token');
      expect((await authSessionStore.readSession())?.userId, 'user-1');
      expect((await authSessionStore.readSession())?.sessionId, 'live-session');
      expect((await authSessionStore.readSession())?.clubId, 'ibadan-lions');
      expect(user.username, 'qa_user');
      expect(transport.requests[1].uri.path, '/api/v2/session/bootstrap');
      expect(
        transport.requests.last.headers['Authorization'],
        'Bearer live-token',
      );
    },
  );

  test('logout clears persisted auth session', () async {
    final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
    final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();
    final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: _RecordingTransport(const <GteTransportResponse>[]),
      fixtures: GteMockApi(latency: Duration.zero),
      tokenStore: tokenStore,
      authSessionStore: authSessionStore,
    );

    await tokenStore.writeToken('live-token');
    await authSessionStore.writeSession(
      const AuthSession(
        userId: 'user-1',
        accessToken: 'live-token',
        refreshToken: 'refresh-live-token',
        sessionId: 'session-1',
      ),
    );

    await repository.logout();

    expect(await tokenStore.readToken(), isNull);
    expect(await authSessionStore.readSession(), isNull);
  });

  test(
    'list orders serializes repeated status filters for open order queries',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'items': <Object?>[],
              'limit': 10,
              'offset': 0,
              'total': 0,
            },
          ),
        ],
      );
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      await tokenStore.writeToken('orders-token');
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(latency: Duration.zero),
        tokenStore: tokenStore,
      );

      await repository.listOrders(
        limit: 10,
        statuses: const <GteOrderStatus>[
          GteOrderStatus.open,
          GteOrderStatus.partiallyFilled,
        ],
      );

      expect(
        transport.requests.single.uri.queryParametersAll['status'],
        <String>['open', 'partially_filled'],
      );
      expect(
        transport.requests.single.headers['Authorization'],
        'Bearer orders-token',
      );
    },
  );
}

Future<void> _expectPolicyDocumentSurfaceFailuresWithoutFixtureFallback(
  GteBackendMode mode,
) async {
  final _RecordingPolicyFixtureApi fixtures = _RecordingPolicyFixtureApi();
  final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
    config: GteRepositoryConfig(baseUrl: 'http://127.0.0.1:8000', mode: mode),
    transport: _ThrowingTransport(),
    fixtures: fixtures,
  );

  Future<void> expectNetworkError(Future<Object?> Function() action) async {
    await expectLater(
      action(),
      throwsA(
        isA<GteApiException>().having(
          (GteApiException error) => error.type,
          'type',
          GteApiErrorType.network,
        ),
      ),
    );
  }

  await expectNetworkError(() => repository.fetchPolicyDocuments());
  await expectNetworkError(
    () => repository.fetchPolicyDocument('terms_and_conditions'),
  );

  expect(fixtures.fetchPolicyDocumentsCalls, 0);
  expect(fixtures.fetchPolicyDocumentCalls, 0);
}

Future<void> _expectPolicyAcceptanceSurfaceFailuresWithoutFixtureFallback(
  GteBackendMode mode,
) async {
  final _RecordingPolicyFixtureApi fixtures = _RecordingPolicyFixtureApi();
  final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
    config: GteRepositoryConfig(baseUrl: 'http://127.0.0.1:8000', mode: mode),
    transport: _ThrowingTransport(),
    fixtures: fixtures,
  );

  await expectLater(
    repository.fetchMyPolicyAcceptances(),
    throwsA(
      isA<GteApiException>().having(
        (GteApiException error) => error.type,
        'type',
        GteApiErrorType.network,
      ),
    ),
  );

  expect(fixtures.fetchMyPolicyAcceptancesCalls, 0);
}

class _ThrowingTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw Exception('network down');
  }
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}

class _ThrowingProfileFixtureApi extends GteMockApi {
  _ThrowingProfileFixtureApi() : super(latency: Duration.zero);

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    throw Exception('fixture profile unavailable');
  }
}

class _RecordingProfileFixtureApi extends GteMockApi {
  _RecordingProfileFixtureApi() : super(latency: Duration.zero);

  int fetchPlayerProfileCalls = 0;

  @override
  Future<PlayerProfile> fetchPlayerProfile(String playerId) {
    fetchPlayerProfileCalls += 1;
    return super.fetchPlayerProfile(playerId);
  }
}

class _RecordingPolicyFixtureApi extends GteMockApi {
  _RecordingPolicyFixtureApi() : super(latency: Duration.zero);

  int fetchPolicyDocumentsCalls = 0;
  int fetchPolicyDocumentCalls = 0;
  int fetchMyPolicyAcceptancesCalls = 0;

  @override
  Future<List<GtePolicyDocumentSummary>> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  }) async {
    fetchPolicyDocumentsCalls += 1;
    return super.fetchPolicyDocuments(mandatoryOnly: mandatoryOnly);
  }

  @override
  Future<GtePolicyDocumentDetail> fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  }) async {
    fetchPolicyDocumentCalls += 1;
    return super.fetchPolicyDocument(documentKey, versionLabel: versionLabel);
  }

  @override
  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances() async {
    fetchMyPolicyAcceptancesCalls += 1;
    return super.fetchMyPolicyAcceptances();
  }
}

class _RecordingPlayersFixtureApi extends GteMockApi {
  _RecordingPlayersFixtureApi() : super(latency: Duration.zero);

  int fetchPlayersCalls = 0;

  @override
  Future<List<PlayerSnapshot>> fetchPlayers({int limit = 20}) async {
    fetchPlayersCalls += 1;
    return <PlayerSnapshot>[
      const PlayerSnapshot(
        id: 'fixture-player',
        name: 'Fixture Prospect',
        club: 'Fixture FC',
        nation: 'Fixture Nation',
        position: 'CB',
        age: 22,
        marketCredits: 777,
        gsi: 88,
        formRating: 7.7,
        valueDeltaPct: 3.3,
        valueTrend: <TrendPoint>[],
        recentHighlights: <String>['Fixture seeded highlight'],
        isWatchlisted: true,
        inTransferRoom: true,
      ),
    ];
  }
}

class _RecordingPulseFixtureApi extends GteMockApi {
  _RecordingPulseFixtureApi() : super(latency: Duration.zero);

  int fetchMarketPulseCalls = 0;

  @override
  Future<MarketPulse> fetchMarketPulse() async {
    fetchMarketPulseCalls += 1;
    return MarketPulse(
      marketMomentum: 99,
      dailyVolumeCredits: 99999,
      activeWatchers: 999,
      liveDeals: 99,
      hottestLeague: 'Fixture Borrowed League',
      tickers: const <String>['Fixture pulse ticker'],
      transferRoom: <TransferRoomEntry>[
        TransferRoomEntry(
          id: 'fixture-pulse-entry',
          headline: 'Fixture pulse headline',
          lane: 'Fixture lane',
          marketCredits: 999,
          activity: 'Fixture pulse activity',
          timestamp: DateTime.utc(2026, 3, 31, 12),
        ),
      ],
    );
  }
}
