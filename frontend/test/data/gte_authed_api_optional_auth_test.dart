import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';

void main() {
  test('optional-auth requests attach a token when one is available', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final GteAuthedApi api = _api(transport, accessToken: 'optional-token');

    await api.getMap('/players/markets', auth: false, opportunisticAuth: true);

    expect(
      transport.requests.single.headers['Authorization'],
      'Bearer optional-token',
    );
  });

  test('optional-auth requests work without a token', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final GteAuthedApi api = _api(transport);

    await api.getMap('/players/markets', auth: false, opportunisticAuth: true);

    expect(transport.requests.single.headers['Authorization'], isNull);
  });

  test('required-auth requests still reject a missing token', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final GteAuthedApi api = _api(transport);

    await expectLater(
      api.getMap('/private', auth: true),
      throwsA(isA<GteApiException>()),
    );

    expect(transport.requests, isEmpty);
  });
}

GteAuthedApi _api(_RecordingTransport transport, {String? accessToken}) {
  return GteAuthedApi(
    config: const GteRepositoryConfig(baseUrl: 'https://example.test'),
    transport: transport,
    accessToken: accessToken,
  );
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
