import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/auth/biometric_unlock_service.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test(
    'trusted biometric session unlocks after local authentication',
    () async {
      final MemoryAuthSessionStore store = MemoryAuthSessionStore();
      const AuthSession session = AuthSession(
        userId: 'user-1',
        accessToken: 'access',
        refreshToken: 'refresh',
        sessionId: 'session-1',
        deviceTrusted: true,
        biometricEnabled: true,
      );
      await store.writeSession(session);
      final _FakeBiometricUnlockService biometric = _FakeBiometricUnlockService(
        canAuthenticateResult: true,
        authenticated: true,
      );
      final TrustedDeviceBiometricUnlockController controller =
          TrustedDeviceBiometricUnlockController(
            sessionStore: store,
            biometricUnlockService: biometric,
          );

      expect(await controller.canOfferBiometricUnlock(), isTrue);
      expect(await controller.unlockPersistedSession(), same(session));
      expect(biometric.authenticateCalls, 1);
    },
  );

  test('untrusted sessions never invoke biometric unlock', () async {
    final MemoryAuthSessionStore store = MemoryAuthSessionStore();
    await store.writeSession(
      const AuthSession(
        userId: 'user-1',
        accessToken: 'access',
        refreshToken: 'refresh',
        sessionId: 'session-1',
        deviceTrusted: false,
        biometricEnabled: true,
      ),
    );
    final _FakeBiometricUnlockService biometric = _FakeBiometricUnlockService(
      canAuthenticateResult: true,
      authenticated: true,
    );
    final TrustedDeviceBiometricUnlockController controller =
        TrustedDeviceBiometricUnlockController(
          sessionStore: store,
          biometricUnlockService: biometric,
        );

    expect(await controller.canOfferBiometricUnlock(), isFalse);
    expect(await controller.unlockPersistedSession(), isNull);
    expect(biometric.authenticateCalls, 0);
  });

  test('trusted sessions can enroll biometric unlock locally', () async {
    final MemoryAuthSessionStore store = MemoryAuthSessionStore();
    await store.writeSession(
      const AuthSession(
        userId: 'user-1',
        accessToken: 'access',
        refreshToken: 'refresh',
        sessionId: 'session-1',
        deviceTrusted: true,
        biometricEnabled: false,
      ),
    );
    final _FakeBiometricUnlockService biometric = _FakeBiometricUnlockService(
      canAuthenticateResult: true,
      authenticated: true,
    );
    final TrustedDeviceBiometricUnlockController controller =
        TrustedDeviceBiometricUnlockController(
          sessionStore: store,
          biometricUnlockService: biometric,
        );

    expect(await controller.canOfferBiometricEnrollment(), isTrue);
    expect(await controller.enableBiometricUnlockForCurrentSession(), isTrue);
    expect(biometric.authenticateCalls, 1);
    expect((await store.readSession())?.biometricEnabled, isTrue);
    expect(await controller.canOfferBiometricUnlock(), isTrue);
  });

  test('biometric availability failures fail closed', () async {
    final MemoryAuthSessionStore store = MemoryAuthSessionStore();
    await store.writeSession(
      const AuthSession(
        userId: 'user-1',
        accessToken: 'access',
        refreshToken: 'refresh',
        sessionId: 'session-1',
        deviceTrusted: true,
        biometricEnabled: true,
      ),
    );
    final _FakeBiometricUnlockService biometric = _FakeBiometricUnlockService(
      canAuthenticateResult: true,
      authenticated: true,
      throwOnCanAuthenticate: true,
    );
    final TrustedDeviceBiometricUnlockController controller =
        TrustedDeviceBiometricUnlockController(
          sessionStore: store,
          biometricUnlockService: biometric,
        );

    expect(await controller.canOfferBiometricUnlock(), isFalse);
    expect(await controller.unlockPersistedSession(), isNull);
    expect(biometric.authenticateCalls, 0);
  });
}

class _FakeBiometricUnlockService implements BiometricUnlockService {
  _FakeBiometricUnlockService({
    required this.canAuthenticateResult,
    required this.authenticated,
    this.throwOnCanAuthenticate = false,
  });

  final bool canAuthenticateResult;
  final bool authenticated;
  final bool throwOnCanAuthenticate;
  int authenticateCalls = 0;

  @override
  Future<bool> canAuthenticate() async {
    if (throwOnCanAuthenticate) {
      throw StateError('biometric unavailable');
    }
    return canAuthenticateResult;
  }

  @override
  Future<bool> authenticate({required String reason}) async {
    authenticateCalls += 1;
    return authenticated;
  }
}
