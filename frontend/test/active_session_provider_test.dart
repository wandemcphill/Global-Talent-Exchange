import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  test('app session controller persists update, merge, and clear', () async {
    final MemoryAuthSessionStore store = MemoryAuthSessionStore();
    final ProviderContainer container = ProviderContainer(
      overrides: [
        authSessionStoreProvider.overrideWithValue(store),
        initialAuthSessionProvider.overrideWithValue(null),
      ],
    );
    addTearDown(container.dispose);

    await container
        .read(appSessionControllerProvider.notifier)
        .updateSession(
          const AuthSession(
            userId: 'user-1',
            accessToken: 'token-1',
            refreshToken: 'refresh-token-1',
            sessionId: 'session-1',
            role: 'admin',
          ),
        );

    expect(container.read(isAuthenticatedProvider), isTrue);
    expect(container.read(currentUserRoleProvider), 'admin');
    expect(container.read(isAdminProvider), isTrue);
    expect(container.read(isDelegatedAdminProvider), isTrue);
    expect(container.read(isSuperAdminProvider), isFalse);
    expect(container.read(canAccessGodModeProvider), isFalse);

    await container.read(appSessionControllerProvider.notifier).mergeProfile(
      <String, Object?>{
        'display_name': 'Ayo Admin',
        'club_id': 'club-1',
        'federation_id': 'fed-1',
        'permissions': <String>['view_audit_log'],
      },
    );

    expect(container.read(currentUserNameProvider), 'Ayo Admin');
    expect(container.read(clubContextProvider)?.id, 'club-1');
    expect(container.read(federationContextProvider)?.id, 'fed-1');
    expect(container.read(canAccessGodModeProvider), isTrue);
    expect((await store.readSession())?.displayName, 'Ayo Admin');
    expect(
      (await store.readSession())?.hasPermission('view_audit_log'),
      isTrue,
    );

    await container
        .read(appSessionControllerProvider.notifier)
        .updateSession(
          const AuthSession(
            userId: 'user-1',
            accessToken: 'token-2',
            refreshToken: 'refresh-token-2',
            sessionId: 'session-2',
            role: 'super_admin',
            permissions: <String>['manage_payment_rails'],
          ),
        );

    expect(container.read(isSuperAdminProvider), isTrue);
    expect(container.read(isDelegatedAdminProvider), isFalse);
    expect(container.read(canAccessGodModeProvider), isTrue);
    expect(
      container.read(authProvider)?.hasPermission('manage_payment_rails'),
      isTrue,
    );

    await container.read(appSessionControllerProvider.notifier).clear();

    expect(container.read(authProvider), isNull);
    expect(await store.readSession(), isNull);
  });
}
