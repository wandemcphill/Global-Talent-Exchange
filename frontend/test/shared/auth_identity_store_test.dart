import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test('memory auth session store persists and clears identity session',
      () async {
    final MemoryAuthSessionStore store = MemoryAuthSessionStore();
    const AuthSession session = AuthSession(
      userId: 'user-1',
      accessToken: 'token-1',
      sessionId: 'session-1',
    );

    await store.writeSession(session);
    expect(await store.readSession(), isNotNull);
    expect((await store.readSession())?.sessionId, 'session-1');

    await store.writeSession(null);
    expect(await store.readSession(), isNull);
  });

  test('ensureDeviceId reuses stored device identity', () async {
    final MemoryDeviceIdentityStore store = MemoryDeviceIdentityStore();

    final String first = await ensureDeviceId(
      store,
      uuidGenerator: () => 'device-fixed',
    );
    final String second = await ensureDeviceId(
      store,
      uuidGenerator: () => 'device-other',
    );

    expect(first, 'device-fixed');
    expect(second, 'device-fixed');
    expect(await store.readDeviceId(), 'device-fixed');
  });
}
