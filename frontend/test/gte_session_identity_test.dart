import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/gte_session_identity.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

void main() {
  test('session identity falls back to guest defaults', () {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(controller);

    expect(identity.userId, 'demo-user');
    expect(identity.clubId, 'royal-lagos-fc');
    expect(identity.clubName, 'Royal Lagos FC');
  });

  test('session identity resolves signed in user and club naming', () async {
    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await controller.signIn(email: 'demo@gtex.test', password: 'password');
    final GteSessionIdentity identity =
        GteSessionIdentity.fromExchangeController(controller);

    expect(identity.userId, controller.session!.user.id);
    expect(identity.userName, isNotEmpty);
    expect(identity.clubId, controller.session!.user.id);
  });
}
