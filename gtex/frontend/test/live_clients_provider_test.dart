import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/live_clients_provider.dart';
import 'package:gte_frontend/shared/providers/regen_provider.dart';

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
    expect(exchangeApiClient.repository, isA<GteModeAwareApiRepository>());
    expect(
      (exchangeApiClient.repository as GteModeAwareApiRepository).config.mode,
      GteBackendMode.live,
    );

    final competitionApi = container.read(competitionApiProvider);
    expect(competitionApi.config.mode, GteBackendMode.live);

    final hostedCompetitionApi = container.read(hostedCompetitionApiProvider);
    expect(hostedCompetitionApi.client.mode, GteBackendMode.live);
    expect(hostedCompetitionApi.client.config.mode, GteBackendMode.live);
  });

  test('competition clients retain the current access token', () {
    final ProviderContainer container = ProviderContainer(
      overrides: [
        appConfigProvider.overrideWithValue(
          const GteAppConfig(
            apiBaseUrl: 'https://example.test',
            backendMode: GteBackendMode.live,
          ),
        ),
        initialAuthSessionProvider.overrideWithValue(
          const AuthSession(
            userId: 'user-1',
            accessToken: 'token-123',
            refreshToken: 'refresh-123',
            sessionId: 'session-123',
            role: 'user',
            userName: 'tester',
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

    final competitionApi = container.read(competitionApiProvider);
    expect(competitionApi.accessToken, 'token-123');

    const GteNavigationDependencies dependencies = GteNavigationDependencies(
      apiBaseUrl: 'https://example.test',
      backendMode: GteBackendMode.live,
      accessToken: 'token-123',
      isAuthenticated: true,
    );
    expect(dependencies.createCompetitionApi().accessToken, 'token-123');
  });

  test('regen creation client uses the active auth session wiring', () {
    final MemoryAuthSessionStore store = MemoryAuthSessionStore();
    const AuthSession session = AuthSession(
      userId: 'user-1',
      accessToken: 'token-regen',
      refreshToken: 'refresh-regen',
      sessionId: 'session-regen',
      role: 'user',
      userName: 'tester',
    );
    final ProviderContainer container = ProviderContainer(
      overrides: [
        appConfigProvider.overrideWithValue(
          const GteAppConfig(
            apiBaseUrl: 'https://example.test',
            backendMode: GteBackendMode.live,
          ),
        ),
        initialAuthSessionProvider.overrideWithValue(session),
        authSessionStoreProvider.overrideWithValue(store),
        deviceIdentityStoreProvider.overrideWithValue(
          MemoryDeviceIdentityStore(),
        ),
        deviceIdProvider.overrideWithValue('device-regen'),
      ],
    );
    addTearDown(container.dispose);

    final regenCreationApi = container.read(regenCreationApiProvider);

    expect(regenCreationApi.client.accessToken, 'token-regen');
    expect(regenCreationApi.client.authSession, session);
    expect(regenCreationApi.client.authSessionStore, same(store));
    expect(regenCreationApi.client.deviceId, 'device-regen');
    expect(regenCreationApi.client.mode, GteBackendMode.live);
  });
}
