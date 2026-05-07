import 'package:flutter_test/flutter_test.dart';
import 'dart:convert';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test('authed api defaults to live mode', () {
    final GteAuthedApi client = GteAuthedApi(
      config: const GteRepositoryConfig(baseUrl: 'http://127.0.0.1:8000'),
      transport: _RecordingTransport(),
    );

    expect(client.mode, GteBackendMode.live);
    expect(client.config.mode, GteBackendMode.live);
  });

  test('authenticated requests include bearer and identity headers', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final GteAuthedApi client = GteAuthedApi(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      authSession: const AuthSession(
        userId: 'user-123',
        accessToken: 'session-token',
        refreshToken: 'refresh-session-token',
        sessionId: 'session-abc',
      ),
      deviceId: 'device-xyz',
      mode: GteBackendMode.live,
    );

    await client.post('/feed/for-you');

    final GteTransportRequest request = transport.requests.single;
    expect(request.uri.path, '/api/v2/feed/for-you');
    expect(request.headers['Authorization'], 'Bearer session-token');
    expect(request.headers['X-User-Id'], 'user-123');
    expect(request.headers['X-Session-Id'], 'session-abc');
    expect(request.headers['X-Device-Id'], 'device-xyz');
  });

  test(
    'authenticated requests recover identity headers from token claims when the stored session is incomplete',
    () async {
      final _RecordingTransport transport = _RecordingTransport();
      final String token = _jwtToken(<String, Object?>{
        'sub': 'user-456',
        'sid': 'session-derived',
      });
      final GteAuthedApi client = GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        authSession: AuthSession(
          userId: '',
          accessToken: token,
          refreshToken: 'refresh-derived-token',
          sessionId: '',
        ),
        mode: GteBackendMode.live,
      );

      await client.getMap('/feed/for-you');

      final GteTransportRequest request = transport.requests.single;
      expect(request.headers['Authorization'], 'Bearer $token');
      expect(request.headers['X-User-Id'], 'user-456');
      expect(request.headers['X-Session-Id'], 'session-derived');
      expect(request.headers['X-Device-Id'], 'web-client');
    },
  );

  test('withFallback fails closed in live mode', () async {
    final GteAuthedApi client = GteAuthedApi(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: _RecordingTransport(),
      mode: GteBackendMode.live,
    );

    expect(
      () => client.withFallback<int>(
        () =>
            throw const GteApiException(
              type: GteApiErrorType.unavailable,
              message: 'backend unavailable',
            ),
        () => 7,
      ),
      throwsA(isA<GteApiException>()),
    );
  });

  test('withFallback remains available for explicit fixture mode', () async {
    final GteAuthedApi client = GteAuthedApi(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.fixture,
      ),
      transport: _RecordingTransport(),
      mode: GteBackendMode.fixture,
    );

    expect(
      await client.withFallback<int>(
        () =>
            throw const GteApiException(
              type: GteApiErrorType.unavailable,
              message: 'backend unavailable',
            ),
        () => 7,
      ),
      7,
    );
  });

  test('getMap unwraps standard success envelopes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      response: const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'success': true,
          'data': <String, Object?>{'items': <Object?>[]},
        },
      ),
    );
    final GteAuthedApi client = GteAuthedApi(
      config: const GteRepositoryConfig(baseUrl: 'http://127.0.0.1:8000'),
      transport: transport,
      mode: GteBackendMode.live,
    );

    final Map<String, dynamic> payload = await client.getMap(
      '/feed/for-you',
      auth: false,
    );

    expect(payload, <String, Object?>{'items': <Object?>[]});
  });

  test(
    'access-token-only clients recover by refreshing the persisted session',
    () async {
      final MemoryAuthSessionStore persistedStore = MemoryAuthSessionStore();
      await persistedStore.writeSession(
        const AuthSession(
          userId: 'user-99',
          accessToken: 'expired-token',
          refreshToken: 'refresh-token-99',
          sessionId: 'session-old',
        ),
      );
      final _QueuedTransport transport = _QueuedTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 401,
            body: <String, Object?>{'detail': 'Access token has expired.'},
          ),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'success': true,
              'data': <String, Object?>{
                'user_id': 'user-99',
                'access_token': 'fresh-token',
                'refresh_token': 'refresh-token-100',
                'session_id': 'session-new',
                'role': 'user',
              },
            },
          ),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'success': true,
              'data': <String, Object?>{
                'user': <String, Object?>{
                  'id': 'user-99',
                  'display_name': 'Ayo',
                },
                'club': <String, Object?>{},
                'wallet': <String, Object?>{},
                'compliance': <String, Object?>{},
              },
            },
          ),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'success': true,
              'data': <String, Object?>{'profile': 'ok'},
            },
          ),
        ],
      );
      final GteAuthedApi client = GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: 'stale-param-token',
        fallbackAuthSessionStore: persistedStore,
        mode: GteBackendMode.live,
      );

      final Map<String, dynamic> payload = await client.getMap(
        '/api/creators/me/summary',
      );

      expect(payload, <String, Object?>{'profile': 'ok'});
      expect(transport.requests, hasLength(4));
      expect(
        transport.requests.first.headers['Authorization'],
        'Bearer expired-token',
      );
      expect(transport.requests[1].uri.path, '/api/v2/auth/refresh');
      expect(
        transport.requests[2].headers['Authorization'],
        'Bearer fresh-token',
      );
      expect(
        transport.requests.last.headers['Authorization'],
        'Bearer fresh-token',
      );
      expect((await persistedStore.readSession())?.accessToken, 'fresh-token');
      expect((await persistedStore.readSession())?.sessionId, 'session-new');
    },
  );

  test(
    'explicit auth session is preferred over stale persisted sessions',
    () async {
      final MemoryAuthSessionStore persistedStore = MemoryAuthSessionStore();
      await persistedStore.writeSession(
        const AuthSession(
          userId: 'old-user',
          accessToken: 'expired-token',
          refreshToken: 'old-refresh',
          sessionId: 'old-session',
        ),
      );
      final _RecordingTransport transport = _RecordingTransport();
      final GteAuthedApi client = GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        authSession: const AuthSession(
          userId: 'fresh-user',
          accessToken: 'fresh-token',
          refreshToken: 'fresh-refresh',
          sessionId: 'fresh-session',
        ),
        fallbackAuthSessionStore: persistedStore,
        mode: GteBackendMode.live,
      );

      await client.getMap('/api/creators/me/summary');

      expect(
        transport.requests.single.headers['Authorization'],
        'Bearer fresh-token',
      );
      expect(transport.requests.single.headers['X-User-Id'], 'fresh-user');
      expect(
        transport.requests.single.headers['X-Session-Id'],
        'fresh-session',
      );
    },
  );
}

String _jwtToken(Map<String, Object?> payload) {
  const Map<String, Object?> header = <String, Object?>{
    'alg': 'none',
    'typ': 'JWT',
  };
  final String encodedHeader = base64Url.encode(
    utf8.encode(jsonEncode(header)),
  );
  final String encodedPayload = base64Url.encode(
    utf8.encode(jsonEncode(payload)),
  );
  return '$encodedHeader.$encodedPayload.';
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport({
    this.response = const GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{},
    ),
  });

  final List<GteTransportRequest> requests = <GteTransportRequest>[];
  final GteTransportResponse response;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return response;
  }
}

class _QueuedTransport implements GteTransport {
  _QueuedTransport(this.responses);

  final List<GteTransportResponse> responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    if (responses.isEmpty) {
      throw StateError('No queued response for ${request.uri}');
    }
    return responses.removeAt(0);
  }
}
