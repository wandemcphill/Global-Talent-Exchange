import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';

void main() {
  test(
    'mode aware repository uses canonical api notification routes',
    () async {
      final _RecordingTransport
      transport = _RecordingTransport(<GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'notification_id': 'notif-1',
              'title': 'Kickoff',
              'body': 'Your match starts now.',
              'sent_at': '2026-04-18T12:00:00Z',
              'read': false,
            },
          ],
        ),
        const GteTransportResponse(statusCode: 200, body: <String, Object?>{}),
        const GteTransportResponse(statusCode: 200, body: <String, Object?>{}),
      ]);
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(latency: Duration.zero),
      );

      await repository.listNotifications(limit: 5);
      await repository.markNotificationRead('notif-1');
      await repository.markAllNotificationsRead();

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v1/notifications/me',
          '/api/v1/notifications/notif-1/read',
          '/api/v1/notifications/read-all',
        ],
      );
      expect(transport.requests.first.uri.queryParameters['limit'], '5');
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
