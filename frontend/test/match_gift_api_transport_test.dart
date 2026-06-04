import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/match_center/data/match_gift_api.dart';

void main() {
  test('match gift api uses canonical api routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'gift_key': 'fire',
            'gift_display_name': 'Fire',
            'gross_amount': '2.0000',
          },
        ),
      ],
    );
    final MatchGiftApi api = MatchGiftApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: 'token-1',
        mode: GteBackendMode.live,
      ),
    );

    await api.sendGift(
      target: const MatchGiftTarget(
        recipientUserId: 'user-2',
        recipientLabel: 'Match host',
        sourceScope: 'user_hosted',
      ),
      gift: kMatchGiftCatalog.first,
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>['/api/v2/gift-engine/send'],
    );
  });
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
