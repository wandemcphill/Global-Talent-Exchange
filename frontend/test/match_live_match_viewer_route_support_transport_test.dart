import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';

void main() {
  test(
    'resolveBootstrap does not duplicate a 404 match-viewer bootstrap request through a legacy alias',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'not found'},
          ),
        ],
      );
      final ApiLiveMatchViewerRepository repository =
          ApiLiveMatchViewerRepository(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'http://127.0.0.1:8000',
                mode: GteBackendMode.live,
              ),
              transport: transport,
            ),
            isAuthenticated: false,
          );

      await expectLater(
        repository.resolveBootstrap('match-001'),
        throwsA(isA<GteApiException>()),
      );

      expect(transport.requests, hasLength(1));
      expect(
        transport.requests.single.uri.path,
        '/api/v1/match-viewer/match-001',
      );
    },
  );

  test(
    'loadViewState does not duplicate a 404 match-viewer session request through a legacy alias',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'not found'},
          ),
        ],
      );
      final ApiLiveMatchViewerRepository repository =
          ApiLiveMatchViewerRepository(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'http://127.0.0.1:8000',
                mode: GteBackendMode.live,
              ),
              transport: transport,
            ),
            isAuthenticated: false,
          );

      await expectLater(
        repository.loadViewState('match-001', continuationToken: 'segment-2'),
        throwsA(isA<GteApiException>()),
      );

      expect(transport.requests, hasLength(1));
      expect(
        transport.requests.single.uri.path,
        '/api/v1/match-viewer/match-001/session',
      );
      expect(
        transport.requests.single.uri.queryParameters['token'],
        'segment-2',
      );
    },
  );
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
