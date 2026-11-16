import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';

void main() {
  test(
    'dedicated signup endpoints submit strict schema-aligned payloads without cross-account leakage',
    () async {
      final _RecordingSignupTransport transport = _RecordingSignupTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 201,
            body: _sessionBody(accountType: 'user', landingRoute: '/app'),
          ),
          GteTransportResponse(
            statusCode: 201,
            body: _sessionBody(accountType: 'creator', landingRoute: '/creator'),
          ),
          GteTransportResponse(
            statusCode: 201,
            body: _sessionBody(
              accountType: 'coin_trader',
              landingRoute: '/trader',
            ),
          ),
        ],
      );

      final GteModeAwareApiRepository repo = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: const GteFixtureRepositoryUnavailable(),
      );

      await repo.signupUser(
        const GteUserSignupRequest(
          fullName: 'Ada User',
          username: '@ada_user',
          email: 'ada.user@gtex.local',
          password: 'StrongPassword!2026', // pragma: allowlist secret
          isOver18: true,
          dateOfBirth: '1998-04-12',
          clubName: 'Lagos FC',
        ),
      );

      final Map<String, Object?> userBody =
          transport.requests[0].body as Map<String, Object?>;
      expect(
        transport.requests[0].uri.path,
        anyOf('/auth/signup/user', '/api/v2/auth/signup/user'),
      );
      expect(userBody['username'], 'ada_user');
      expect(userBody['is_over_18'], isTrue);
      expect(userBody.containsKey('trading_alias'), isFalse);
      expect(userBody.containsKey('totp_secret'), isFalse);

      await repo.signupCreator(
        const GteCreatorSignupRequest(
          creatorName: 'Kratos Tactician',
          username: 'kratos_creator',
          email: 'creator@gtex.local',
          password: 'StrongPassword!2026', // pragma: allowlist secret
          country: 'NG',
          category: 'tactical_analysis',
          mainClubSupported: 'Enyimba',
          primaryLanguage: 'en',
          monetization: <String>['subscriptions', 'tips'],
        ),
      );

      final Map<String, Object?> creatorBody =
          transport.requests[1].body as Map<String, Object?>;
      expect(
        transport.requests[1].uri.path,
        anyOf('/auth/signup/creator', '/api/v2/auth/signup/creator'),
      );
      expect(creatorBody['creator_name'], 'Kratos Tactician');
      expect(creatorBody['username'], 'kratos_creator');
      expect(creatorBody.containsKey('trading_alias'), isFalse);
      expect(creatorBody.containsKey('is_over_18'), isFalse);

      await repo.signupTrader(
        const GteTraderSignupRequest(
          fullName: 'Desk Operator',
          tradingAlias: 'lagos_otc_desk',
          email: 'trader@gtex.local',
          password: 'StrongPassword!2026', // pragma: allowlist secret
          phoneNumber: '+2348012345678',
          country: 'NG',
          preferredCurrency: 'NGN',
          tradingExperience: '2-5_years',
          interests: <String>['GTEX Coin', 'Fan Coins'],
          totpSecret: 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP', // pragma: allowlist secret
          totpCode: '123456',
          recoveryPhraseHash:
              'pbkdf2-sha256\$210000\$recovery\$00112233445566778899aabbccddeeff\$0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
          securityPinHash:
              'pbkdf2-sha256\$210000\$pin\$00112233445566778899aabbccddeeff\$0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
        ),
      );

      final Map<String, Object?> traderBody =
          transport.requests[2].body as Map<String, Object?>;
      expect(
        transport.requests[2].uri.path,
        anyOf('/auth/signup/trader', '/api/v2/auth/signup/trader'),
      );
      expect(traderBody['trading_alias'], 'lagos_otc_desk');
      expect(traderBody['preferred_currency'], 'NGN');
      expect(
        (traderBody['recovery_phrase_hash'] as String).startsWith(
          'pbkdf2-sha256\$210000\$recovery\$',
        ),
        isTrue,
      );
      expect(
        (traderBody['security_pin_hash'] as String).startsWith(
          'pbkdf2-sha256\$210000\$pin\$',
        ),
        isTrue,
      );
      expect(traderBody.containsKey('username'), isFalse);
      expect(traderBody.containsKey('is_over_18'), isFalse);
    },
  );
}

Map<String, Object?> _sessionBody({
  required String accountType,
  required String landingRoute,
}) {
  return <String, Object?>{
    'access_token': 'tok-$accountType',
    'refresh_token': 'ref-$accountType',
    'session_id': 'sess-$accountType',
    'token_type': 'bearer',
    'expires_in': 3600,
    'refresh_expires_in': 86400,
    'landing_route': landingRoute,
    'user': <String, Object?>{
      'id': 'usr-$accountType',
      'email': '$accountType@gtex.local',
      'username': 'usr_$accountType',
      'role': 'user',
      'account_type': accountType,
    },
  };
}

class _RecordingSignupTransport implements GteTransport {
  _RecordingSignupTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}
