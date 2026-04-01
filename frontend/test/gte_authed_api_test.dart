import 'package:flutter_test/flutter_test.dart';
import 'dart:convert';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test('authed api defaults to live mode', () {
    final GteAuthedApi client = GteAuthedApi(
      config: const GteRepositoryConfig(baseUrl: 'http://127.0.0.1:8000'),
      transport: _RecordingTransport(),
    );

    expect(client.mode, GteBackendMode.live);
    expect(client.config.mode, GteBackendMode.liveThenFixture);
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
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return const GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{},
    );
  }
}
