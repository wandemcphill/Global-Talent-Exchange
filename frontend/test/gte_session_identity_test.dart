import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/gte_session_identity.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  test('session identity falls back to guest user without a canonical club',
      () {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(controller);

    expect(identity.userId, 'guest-user');
    expect(identity.clubId, isNull);
    expect(identity.clubName, isNull);
  });

  test(
      'session identity prefers current_club_id from the authenticated payload',
      () {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.session = _sessionFromJson(
      <String, Object?>{
        'current_club_id': 'ibadan-lions',
        'current_club_name': 'Ibadan Lions FC',
        'user': <String, Object?>{
          'id': 'user-1',
          'email': 'user-1@gtex.test',
          'username': 'ibadan_owner',
          'display_name': 'Ibadan Owner',
          'role': 'user',
          'current_club_id': 'ibadan-lions',
          'current_club_name': 'Ibadan Lions FC',
          'memberships': <Map<String, Object?>>[
            <String, Object?>{
              'club_id': 'royal-lagos-fc',
              'club_name': 'Royal Lagos FC',
            },
          ],
        },
      },
    );

    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(controller);

    expect(identity.userId, 'user-1');
    expect(identity.userName, 'Ibadan Owner');
    expect(identity.clubId, 'ibadan-lions');
    expect(identity.clubName, 'Ibadan Lions FC');
  });

  test('session identity falls back to clubId when current club is absent', () {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.session = _sessionFromJson(
      <String, Object?>{
        'user': <String, Object?>{
          'id': 'user-2',
          'email': 'user-2@gtex.test',
          'username': 'ondo_manager',
          'role': 'user',
          'clubId': 'ondo-waves',
          'clubName': 'Ondo Waves FC',
        },
      },
    );

    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(controller);

    expect(identity.clubId, 'ondo-waves');
    expect(identity.clubName, 'Ondo Waves FC');
  });

  test(
      'session identity derives the first canonical membership club when direct fields are absent',
      () {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.session = _sessionFromJson(
      <String, Object?>{
        'user': <String, Object?>{
          'id': 'user-3',
          'email': 'user-3@gtex.test',
          'username': 'akure_owner',
          'role': 'user',
          'memberships': <Map<String, Object?>>[
            <String, Object?>{
              'is_current': true,
              'club': <String, Object?>{
                'id': 'akure-city',
                'name': 'Akure City',
              },
            },
            <String, Object?>{
              'club_id': 'royal-lagos-fc',
              'club_name': 'Royal Lagos FC',
            },
          ],
        },
      },
    );

    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(controller);

    expect(identity.clubId, 'akure-city');
    expect(identity.clubName, 'Akure City');
  });
}

GteAuthSession _sessionFromJson(Map<String, Object?> payload) {
  return GteAuthSession.fromJson(
    <String, Object?>{
      'access_token': 'test-token',
      'token_type': 'bearer',
      'expires_in': 3600,
      'user': <String, Object?>{
        'id': 'test-user',
        'email': 'test-user@gtex.test',
        'username': 'tester',
        'role': 'user',
      },
      ...payload,
    },
  );
}
