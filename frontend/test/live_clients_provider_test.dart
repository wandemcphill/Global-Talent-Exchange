import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/live_clients_provider.dart';

void main() {
  test('active-shell routed providers clamp liveThenFixture down to live', () {
    final ProviderContainer container = ProviderContainer(
      overrides: [
        appConfigProvider.overrideWithValue(
          const GteAppConfig(
            apiBaseUrl: 'https://example.test',
            backendMode: GteBackendMode.liveThenFixture,
          ),
        ),
        authSessionStoreProvider.overrideWithValue(MemoryAuthSessionStore()),
        deviceIdentityStoreProvider.overrideWithValue(
          MemoryDeviceIdentityStore(),
        ),
        deviceIdProvider.overrideWithValue('device-1'),
      ],
    );
    addTearDown(container.dispose);

    expect(container.read(criticalBackendModeProvider), GteBackendMode.live);

    final authedApi = container.read(authedApiProvider);
    expect(authedApi.mode, GteBackendMode.live);
    expect(authedApi.config.mode, GteBackendMode.live);

    final exchangeApiClient = container.read(exchangeApiClientProvider);
    expect(exchangeApiClient.config.mode, GteBackendMode.live);

    final competitionApi = container.read(competitionApiProvider);
    expect(competitionApi.config.mode, GteBackendMode.live);

    final hostedCompetitionApi = container.read(hostedCompetitionApiProvider);
    expect(hostedCompetitionApi.client.mode, GteBackendMode.live);
    expect(hostedCompetitionApi.client.config.mode, GteBackendMode.live);
  });
}
