import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/creator_application_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/models/creator_application_models.dart';

void main() {
  test('creator application api uses creator operations routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'id': 'user-1',
            'email_verified_at': null,
            'phone_verified_at': null,
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'user_id': 'user-1',
            'email_verified_at': '2026-04-18T12:00:00Z',
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'user_id': 'user-1',
            'phone_verified_at': '2026-04-18T12:05:00Z',
          },
        ),
        const GteTransportResponse(statusCode: 200, body: null),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'application_id': 'app-1',
            'user_id': 'user-1',
            'requested_handle': 'maya_scout',
            'display_name': 'Maya Scout',
            'platform': 'tiktok',
            'follower_count': 120000,
            'social_links': <Object?>['https://example.test/@maya'],
            'email_verified_at': '2026-04-18T12:00:00Z',
            'phone_verified_at': '2026-04-18T12:05:00Z',
            'status': 'pending',
            'created_at': '2026-04-18T12:10:00Z',
            'updated_at': '2026-04-18T12:10:00Z',
          },
        ),
      ],
    );
    final CreatorApplicationApi api = CreatorApplicationApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: 'token-1',
        mode: GteBackendMode.live,
      ),
      mode: GteBackendMode.live,
    );

    await api.fetchVerificationStatus();
    await api.verifyEmail();
    await api.verifyPhone();
    await api.fetchMyApplication();
    await api.submitApplication(
      const CreatorApplicationSubmitRequest(
        requestedHandle: 'maya_scout',
        displayName: 'Maya Scout',
        platform: 'tiktok',
        followerCount: 120000,
        socialLinks: <String>['https://example.test/@maya'],
      ),
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/auth/me',
        '/api/v2/creator/verify-email',
        '/api/v2/creator/verify-phone',
        '/api/v2/creator/application',
        '/api/v2/creator/apply',
      ],
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

