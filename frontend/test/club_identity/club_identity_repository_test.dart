import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_defaults.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_set_dto.dart';

void main() {
  test('fetch identity succeeds and targets the identity endpoint', () async {
    final Map<String, dynamic> payload = _identityPayload();
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: payload),
      ],
    );
    final ClubIdentityApiRepository repository = ClubIdentityApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: MockClubIdentityRepository(),
    );

    final identity = await repository.fetchIdentity('atlas-fc');

    expect(identity.clubId, 'atlas-fc');
    expect(transport.requests.single.method, 'GET');
    expect(
      transport.requests.single.uri.path,
      '/api/clubs/atlas-fc/identity',
    );
  });

  test('fetch and save jerseys parse jersey payloads', () async {
  final JerseySetDto jerseys = _sampleIdentity().jerseySet;
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: jerseys.toJson()),
        GteTransportResponse(statusCode: 200, body: jerseys.toJson()),
      ],
    );
    final ClubIdentityApiRepository repository = ClubIdentityApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: MockClubIdentityRepository(),
    );

    final JerseySetDto fetched = await repository.fetchJerseys('atlas-fc');
    final JerseySetDto patched = await repository.patchJerseys(
      clubId: 'atlas-fc',
      patch: jerseys.toJson(),
    );

    expect(fetched.home.primaryColor, jerseys.home.primaryColor);
    expect(patched.away.secondaryColor, jerseys.away.secondaryColor);
    expect(transport.requests.first.method, 'GET');
    expect(transport.requests.last.method, 'PATCH');
  });

  test('patch identity returns parsed identity payload', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: _identityPayload()),
      ],
    );
    final ClubIdentityApiRepository repository = ClubIdentityApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: MockClubIdentityRepository(),
    );

    final identity = await repository.patchIdentity(
      clubId: 'atlas-fc',
      patch: <String, dynamic>{'club_name': 'Atlas FC'},
    );

    expect(identity.clubName, 'Atlas FC');
    expect(transport.requests.single.method, 'PATCH');
  });

  test('backend errors surface as api exceptions', () async {
    final _RecordingTransport transport = _RecordingTransport(
      const <GteTransportResponse>[
        GteTransportResponse(statusCode: 500, body: 'Service down'),
      ],
    );
    final ClubIdentityApiRepository repository = ClubIdentityApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: MockClubIdentityRepository(),
    );

    expect(
      () => repository.fetchIdentity('atlas-fc'),
      throwsA(
        isA<GteApiException>().having(
          (GteApiException error) => error.type,
          'type',
          GteApiErrorType.unavailable,
        ),
      ),
    );
  });

  test('match identity falls back when missing from payload', () async {
    final Map<String, dynamic> payload =
        _identityPayload(includeMatchIdentity: false);
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: payload),
      ],
    );
    final ClubIdentityApiRepository repository = ClubIdentityApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: MockClubIdentityRepository(),
    );

    final identity = await repository.fetchIdentity('atlas-fc');

    expect(
      identity.matchIdentity.homeKitColors,
      <String>[
        identity.jerseySet.home.primaryColor,
        identity.jerseySet.home.secondaryColor,
        identity.jerseySet.home.accentColor,
      ],
    );
    expect(
      identity.matchIdentity.generatedBadge.initials,
      identity.badgeProfile.initials,
    );
  });
}

Map<String, dynamic> _identityPayload({bool includeMatchIdentity = true}) {
  final Map<String, dynamic> payload = _sampleIdentity().toJson();
  if (!includeMatchIdentity) {
    payload.remove('match_identity');
  }
  return payload;
}

ClubIdentityDto _sampleIdentity() {
  return ClubIdentityDefaults.generate(
    clubId: 'atlas-fc',
    clubName: 'Atlas FC',
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
