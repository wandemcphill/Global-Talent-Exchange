import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/creator_stadium_monetization/data/creator_stadium_monetization_models.dart';
import 'package:gte_frontend/features/creator_stadium_monetization/data/creator_stadium_monetization_repository.dart';

void main() {
  test(
    'creator stadium repository uses canonical api media-engine routes',
    () async {
      final _RecordingTransport
      transport = _RecordingTransport(<GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{'mode_key': 'standard'},
          ],
        ),
        const GteTransportResponse(statusCode: 200, body: <String, Object?>{}),
        const GteTransportResponse(statusCode: 200, body: <String, Object?>{}),
        const GteTransportResponse(statusCode: 200, body: <String, Object?>{}),
      ]);
      final CreatorStadiumMonetizationApiRepository repository =
          CreatorStadiumMonetizationApiRepository(
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

      await repository.listBroadcastModes();
      await repository.fetchMatchAccess(
        'match-1',
        const CreatorMatchAccessQuery(durationMinutes: 45),
      );
      await repository.fetchAdminMatchAnalytics(
        'match-1',
        const CreatorMatchAnalyticsQuery(clubId: 'club-1'),
      );
      await repository.updateStadiumControl(
        const CreatorStadiumControlUpdateRequest(
          maxMatchdayTicketPriceCoin: 25,
          maxSeasonPassPriceCoin: 120,
          maxVipTicketPriceCoin: 90,
          maxStadiumLevel: 5,
          vipSeatRatioBps: 800,
          maxInStadiumAdSlots: 6,
          maxSponsorBannerSlots: 4,
          adPlacementEnabled: true,
          ticketSalesEnabled: true,
          maxPlacementPriceCoin: 75,
        ),
      );

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v1/media-engine/creator-league/broadcast-modes',
          '/api/v1/media-engine/creator-league/matches/match-1/access',
          '/api/v1/admin/media-engine/creator-league/matches/match-1/analytics',
          '/api/v1/admin/media-engine/creator-league/stadium-controls',
        ],
      );
      expect(
        transport.requests[1].uri.queryParameters['duration_minutes'],
        '45',
      );
      expect(transport.requests[2].uri.queryParameters['club_id'], 'club-1');
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
