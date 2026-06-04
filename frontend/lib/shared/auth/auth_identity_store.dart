import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/auth_session.dart';

abstract class AuthSessionStore {
  Future<AuthSession?> readSession();

  Future<void> writeSession(AuthSession? session);
}

class SecureAuthSessionStore implements AuthSessionStore {
  SecureAuthSessionStore({
    FlutterSecureStorage? storage,
    this.storageKey = _defaultAuthSessionStorageKey,
  }) : _storage = storage ?? const FlutterSecureStorage();

  static const String _defaultAuthSessionStorageKey = 'gtex_auth_session';

  final FlutterSecureStorage _storage;
  final String storageKey;

  @override
  Future<AuthSession?> readSession() async {
    final String raw = (await _storage.read(key: storageKey) ?? '').trim();
    if (raw.isEmpty) {
      return null;
    }
    final Object? decoded = jsonDecode(raw);
    if (decoded is! Map) {
      return null;
    }
    return AuthSession.fromJson(Map<String, Object?>.from(decoded));
  }

  @override
  Future<void> writeSession(AuthSession? session) async {
    if (session == null) {
      await _storage.delete(key: storageKey);
      return;
    }
    await _storage.write(key: storageKey, value: jsonEncode(session.toJson()));
  }
}

class MemoryAuthSessionStore implements AuthSessionStore {
  AuthSession? _session;

  @override
  Future<AuthSession?> readSession() async => _session;

  @override
  Future<void> writeSession(AuthSession? session) async {
    _session = session;
  }
}

abstract class DeviceIdentityStore {
  Future<String?> readDeviceId();

  Future<void> writeDeviceId(String? deviceId);
}

abstract class TrustedDeviceTokenStore {
  Future<String?> readTrustedDeviceToken();

  Future<void> writeTrustedDeviceToken(String? token);
}

class SecureTrustedDeviceTokenStore implements TrustedDeviceTokenStore {
  SecureTrustedDeviceTokenStore({
    FlutterSecureStorage? storage,
    this.storageKey = _defaultTrustedDeviceTokenStorageKey,
  }) : _storage = storage ?? const FlutterSecureStorage();

  static const String _defaultTrustedDeviceTokenStorageKey =
      'gtex_trusted_device_token';

  final FlutterSecureStorage _storage;
  final String storageKey;

  @override
  Future<String?> readTrustedDeviceToken() async {
    final String value = (await _storage.read(key: storageKey) ?? '').trim();
    return value.isEmpty ? null : value;
  }

  @override
  Future<void> writeTrustedDeviceToken(String? token) async {
    final String resolved = token?.trim() ?? '';
    if (resolved.isEmpty) {
      await _storage.delete(key: storageKey);
      return;
    }
    await _storage.write(key: storageKey, value: resolved);
  }
}

class MemoryTrustedDeviceTokenStore implements TrustedDeviceTokenStore {
  String? _token;

  @override
  Future<String?> readTrustedDeviceToken() async => _token;

  @override
  Future<void> writeTrustedDeviceToken(String? token) async {
    _token = token;
  }
}

class SecureDeviceIdentityStore implements DeviceIdentityStore {
  SecureDeviceIdentityStore({
    FlutterSecureStorage? storage,
    this.storageKey = _defaultDeviceIdStorageKey,
  }) : _storage = storage ?? const FlutterSecureStorage();

  static const String _defaultDeviceIdStorageKey = 'gtex_device_id';

  final FlutterSecureStorage _storage;
  final String storageKey;

  @override
  Future<String?> readDeviceId() async {
    final String value = (await _storage.read(key: storageKey) ?? '').trim();
    return value.isEmpty ? null : value;
  }

  @override
  Future<void> writeDeviceId(String? deviceId) async {
    final String resolved = deviceId?.trim() ?? '';
    if (resolved.isEmpty) {
      await _storage.delete(key: storageKey);
      return;
    }
    await _storage.write(key: storageKey, value: resolved);
  }
}

class MemoryDeviceIdentityStore implements DeviceIdentityStore {
  String? _deviceId;

  @override
  Future<String?> readDeviceId() async => _deviceId;

  @override
  Future<void> writeDeviceId(String? deviceId) async {
    _deviceId = deviceId;
  }
}

Future<String> ensureDeviceId(
  DeviceIdentityStore store, {
  String Function()? uuidGenerator,
}) async {
  final String existing = (await store.readDeviceId() ?? '').trim();
  if (existing.isNotEmpty) {
    return existing;
  }
  final String deviceId = (uuidGenerator ?? generateIdentityUuid)();
  await store.writeDeviceId(deviceId);
  return deviceId;
}

final math.Random _uuidRandom = _createUuidRandom();

math.Random _createUuidRandom() {
  try {
    return math.Random.secure();
  } catch (_) {
    return math.Random();
  }
}

String generateIdentityUuid() {
  final List<int> bytes = List<int>.generate(
    16,
    (_) => _uuidRandom.nextInt(256),
  );
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final String hex =
      bytes.map((int value) => value.toRadixString(16).padLeft(2, '0')).join();
  return <String>[
    hex.substring(0, 8),
    hex.substring(8, 12),
    hex.substring(12, 16),
    hex.substring(16, 20),
    hex.substring(20, 32),
  ].join('-');
}
