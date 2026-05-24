import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/system_profile_redesign/data/profile_runtime_adapter.dart';

void main() {
  test('profile runtime adapter reads canonical live endpoints', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <String, GteTransportResponse>{
        '/api/v2/session/bootstrap': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'roles': <String>['club_owner'],
            'permissions': <String>['manage_club'],
            'runtime': <String, Object?>{
              'strictLive': true,
              'payments': <String, Object?>{
                'korapayEnabled': true,
                'paystackEnabled': false,
              },
            },
          },
        ),
        '/api/v2/profile': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'id': 'user-1',
            'email': 'owner@gtex.com',
            'username': 'owner',
            'role': 'club_owner',
            'account_type': 'club_owner',
            'display_name': 'Club Owner',
          },
        ),
        '/api/v2/profile/security': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'active_session_count': 2,
            'mfa_enabled': true,
          },
        ),
        '/api/v2/profile/sessions': const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{'session_id': 'session-1', 'is_current': true},
          ],
        ),
        '/api/v2/wallet/summary': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'available_balance': 1250,
            'reserved_balance': 50,
            'total_balance': 1300,
            'currency': 'coin',
          },
        ),
        '/api/v2/club/current': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'id': 'club-1', 'name': 'GTEX Live FC'},
        ),
      },
    );
    final ProfileRuntimeAdapter adapter = ProfileRuntimeAdapter(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(baseUrl: 'https://api.gtex.test'),
        transport: transport,
        accessToken: 'live-token',
      ),
    );

    final GtexProfileRuntimeSnapshot snapshot = await adapter.load();

    expect(snapshot.user.email, 'owner@gtex.com');
    expect(snapshot.clubName, 'GTEX Live FC');
    expect(snapshot.wallet.availableBalance, 1250);
    expect(snapshot.activeSessionCount, 2);
    expect(snapshot.mfaEnabled, isTrue);
    expect(snapshot.roles, <String>['club_owner']);
    expect(snapshot.permissions, <String>['manage_club']);
    expect(snapshot.strictLive, isTrue);
    expect(snapshot.korapayEnabled, isTrue);
    expect(snapshot.paystackEnabled, isFalse);
    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      containsAll(<String>[
        '/api/v2/session/bootstrap',
        '/api/v2/profile',
        '/api/v2/profile/security',
        '/api/v2/profile/sessions',
        '/api/v2/wallet/summary',
        '/api/v2/club/current',
      ]),
    );
  });

  test(
    'profile runtime adapter treats no-club 404 as explicit no club',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <String, GteTransportResponse>{
          '/api/v2/session/bootstrap': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'roles': <String>['user'],
              'permissions': <String>[],
              'runtime': <String, Object?>{
                'strictLive': true,
                'payments': <String, Object?>{
                  'korapayEnabled': true,
                  'paystackEnabled': false,
                },
              },
            },
          ),
          '/api/v2/profile': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'id': 'user-2',
              'email': 'fan@gtex.com',
              'username': 'fan',
              'role': 'user',
            },
          ),
          '/api/v2/profile/security': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{'active_session_count': 1},
          ),
          '/api/v2/profile/sessions': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[],
          ),
          '/api/v2/wallet/summary': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'available_balance': 0,
              'reserved_balance': 0,
              'total_balance': 0,
              'currency': 'coin',
            },
          ),
          '/api/v2/club/current': const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'No active club'},
          ),
        },
      );
      final ProfileRuntimeAdapter adapter = ProfileRuntimeAdapter(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(baseUrl: 'https://api.gtex.test'),
          transport: transport,
          accessToken: 'live-token',
        ),
      );

      final GtexProfileRuntimeSnapshot snapshot = await adapter.load();

      expect(snapshot.user.email, 'fan@gtex.com');
      expect(snapshot.club, isNull);
      expect(snapshot.clubName, isNull);
    },
  );
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this.responses);

  final Map<String, GteTransportResponse> responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return responses[request.uri.path] ??
        GteTransportResponse(
          statusCode: 404,
          body: <String, Object?>{'detail': 'Unexpected ${request.uri.path}'},
        );
  }
}
