import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/hosted_competition_api.dart';

void main() {
  test('seed templates uses POST on the admin seed endpoint', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final HostedCompetitionApi api = HostedCompetitionApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'admin-token',
      mode: GteBackendMode.live,
      transport: transport,
    );

    await api.seedTemplates();

    expect(transport.requests, hasLength(1));
    expect(transport.requests.single.method, 'POST');
    expect(
      transport.requests.single.uri.path,
      '/admin/hosted-competitions/seed',
    );
  });
}

class _RecordingTransport implements GteTransport {
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return const GteTransportResponse(statusCode: 200, body: <Object?>[]);
  }
}
