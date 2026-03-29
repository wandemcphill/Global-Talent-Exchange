import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
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
