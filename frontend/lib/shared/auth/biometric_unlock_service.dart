import 'package:local_auth/local_auth.dart';

import '../models/auth_session.dart';
import 'auth_identity_store.dart';

abstract class BiometricUnlockService {
  Future<bool> canAuthenticate();

  Future<bool> authenticate({required String reason});
}

class LocalBiometricUnlockService implements BiometricUnlockService {
  LocalBiometricUnlockService({LocalAuthentication? localAuthentication})
    : _localAuthentication = localAuthentication ?? LocalAuthentication();

  final LocalAuthentication _localAuthentication;

  @override
  Future<bool> canAuthenticate() async {
    try {
      final bool deviceSupported =
          await _localAuthentication.isDeviceSupported();
      if (!deviceSupported) {
        return false;
      }
      return _localAuthentication.canCheckBiometrics;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> authenticate({required String reason}) async {
    try {
      return await _localAuthentication.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}

class DisabledBiometricUnlockService implements BiometricUnlockService {
  const DisabledBiometricUnlockService();

  @override
  Future<bool> canAuthenticate() async => false;

  @override
  Future<bool> authenticate({required String reason}) async => false;
}

class TrustedDeviceBiometricUnlockController {
  const TrustedDeviceBiometricUnlockController({
    required AuthSessionStore sessionStore,
    required BiometricUnlockService biometricUnlockService,
  }) : _sessionStore = sessionStore,
       _biometricUnlockService = biometricUnlockService;

  final AuthSessionStore _sessionStore;
  final BiometricUnlockService _biometricUnlockService;

  Future<bool> canOfferBiometricUnlock() async {
    final AuthSession? session = await _sessionStore.readSession();
    if (session == null) {
      return false;
    }
    if (!session.deviceTrusted || !session.biometricEnabled) {
      return false;
    }
    try {
      return await _biometricUnlockService.canAuthenticate();
    } catch (_) {
      return false;
    }
  }

  Future<bool> canOfferBiometricEnrollment() async {
    final AuthSession? session = await _sessionStore.readSession();
    if (session == null || !session.deviceTrusted || session.biometricEnabled) {
      return false;
    }
    try {
      return await _biometricUnlockService.canAuthenticate();
    } catch (_) {
      return false;
    }
  }

  Future<bool> enableBiometricUnlockForCurrentSession({
    String reason = 'Enable biometric unlock for GTEX',
  }) async {
    final AuthSession? session = await _sessionStore.readSession();
    if (session == null || !session.deviceTrusted || session.biometricEnabled) {
      return false;
    }
    if (!await canOfferBiometricEnrollment()) {
      return false;
    }
    final bool authenticated = await _biometricUnlockService.authenticate(
      reason: reason,
    );
    if (!authenticated) {
      return false;
    }
    final Map<String, Object?> rawJson = Map<String, Object?>.from(
      session.rawJson,
    );
    if (rawJson.isNotEmpty) {
      rawJson['biometric_enabled'] = true;
    }
    await _sessionStore.writeSession(
      session.copyWith(
        biometricEnabled: true,
        rawJson: rawJson.isEmpty ? session.rawJson : rawJson,
      ),
    );
    return true;
  }

  Future<AuthSession?> unlockPersistedSession({
    String reason = 'Unlock GTEX',
  }) async {
    final AuthSession? session = await _sessionStore.readSession();
    if (session == null) {
      return null;
    }
    if (!session.deviceTrusted || !session.biometricEnabled) {
      return null;
    }
    if (!await canOfferBiometricUnlock()) {
      return null;
    }
    final bool authenticated = await _biometricUnlockService.authenticate(
      reason: reason,
    );
    return authenticated ? session : null;
  }
}
