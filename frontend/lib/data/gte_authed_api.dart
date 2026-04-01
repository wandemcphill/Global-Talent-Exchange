import 'dart:async';
import 'dart:convert';

import 'gte_api_repository.dart';
import '../shared/auth/auth_identity_store.dart';
import '../shared/models/auth_session.dart';

class GteAuthedApi {
  GteAuthedApi({
    required this.config,
    required this.transport,
    this.accessToken,
    this.authSession,
    this.authSessionStore,
    this.onSessionChanged,
    this.deviceId,
    this.mode = GteBackendMode.live,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String? accessToken;
  final AuthSession? authSession;
  final AuthSessionStore? authSessionStore;
  final Future<void> Function(AuthSession? session)? onSessionChanged;
  final String? deviceId;
  final GteBackendMode mode;

  Future<Object?> request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
    bool auth = true,
    bool allowRefresh = true,
  }) async {
    final Map<String, String> headers = <String, String>{
      'Content-Type': 'application/json',
    };
    final AuthSession? resolvedSession = await _readCurrentSession();
    if (auth) {
      final String resolvedAccessToken =
          resolvedSession?.accessToken ?? accessToken ?? '';
      if (resolvedAccessToken.isEmpty) {
        throw const GteApiException(
          type: GteApiErrorType.unauthorized,
          message: 'Authentication required for this action.',
        );
      }
      headers['Authorization'] = 'Bearer $resolvedAccessToken';
      final Map<String, Object?> tokenClaims = _decodeJwtClaims(
        resolvedAccessToken,
      );
      final String resolvedUserId = _firstNonEmpty(
        resolvedSession?.userId,
        _stringClaim(tokenClaims, 'sub'),
      );
      final String resolvedSessionId = _firstNonEmpty(
        resolvedSession?.sessionId,
        _stringClaim(tokenClaims, 'sid'),
      );
      final String resolvedDeviceId = _firstNonEmpty(deviceId, 'web-client');
      if (resolvedUserId.isNotEmpty && resolvedSessionId.isNotEmpty) {
        headers['X-User-Id'] = resolvedUserId;
        headers['X-Session-Id'] = resolvedSessionId;
        headers['X-Device-Id'] = resolvedDeviceId;
      }
    }
    final GteTransportResponse response = await transport.send(
      GteTransportRequest(
        method: method,
        uri: config.uriFor(path, query),
        headers: headers,
        body: body,
      ),
    );
    if (response.statusCode == 401 &&
        auth &&
        allowRefresh &&
        await _refreshSession(resolvedSession)) {
      return request(
        method,
        path,
        query: query,
        body: body,
        auth: auth,
        allowRefresh: false,
      );
    }
    if (response.statusCode >= 400) {
      throw _toException(response);
    }
    return response.body;
  }

  Future<Object?> post(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
    bool auth = true,
  }) {
    return request('POST', path, query: query, body: body, auth: auth);
  }

  Future<Map<String, dynamic>> getMap(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    bool auth = true,
  }) async {
    final Object? body = await request('GET', path, query: query, auth: auth);
    if (body is Map) {
      return Map<String, dynamic>.from(body);
    }
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message: 'Unexpected response shape.',
    );
  }

  Future<List<dynamic>> getList(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    bool auth = true,
  }) async {
    final Object? body = await request('GET', path, query: query, auth: auth);
    if (body is List) {
      return body;
    }
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message: 'Unexpected list response shape.',
    );
  }

  Future<T> withFallback<T>(
    FutureOr<T> Function() liveCall,
    FutureOr<T> Function() fixtureCall,
  ) async {
    if (mode == GteBackendMode.fixture) {
      return await fixtureCall();
    }
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (mode == GteBackendMode.liveThenFixture &&
          error.supportsFixtureFallback) {
        return await fixtureCall();
      }
      rethrow;
    }
  }

  GteApiException _toException(GteTransportResponse response) {
    final Object? body = response.body;
    String message = 'Request failed.';
    if (body is Map<String, dynamic>) {
      message = (body['detail'] ?? body['message'] ?? message).toString();
    } else if (body is String && body.trim().isNotEmpty) {
      message = body;
    }
    return GteApiException(
      type: _errorType(response.statusCode),
      message: message,
      statusCode: response.statusCode,
    );
  }

  GteApiErrorType _errorType(int statusCode) {
    if (statusCode == 401 || statusCode == 403) {
      return GteApiErrorType.unauthorized;
    }
    if (statusCode == 404) {
      return GteApiErrorType.notFound;
    }
    if (statusCode == 422) {
      return GteApiErrorType.validation;
    }
    if (statusCode >= 500) {
      return GteApiErrorType.unavailable;
    }
    return GteApiErrorType.unknown;
  }

  Future<AuthSession?> _readCurrentSession() async {
    final AuthSession? stored = await authSessionStore?.readSession();
    return stored ?? authSession;
  }

  Future<bool> _refreshSession(AuthSession? currentSession) async {
    final String refreshToken = currentSession?.refreshToken.trim() ?? '';
    if (refreshToken.isEmpty) {
      await _clearSession();
      return false;
    }
    final Map<String, String> headers = <String, String>{
      'Content-Type': 'application/json',
      'X-Device-Id': _firstNonEmpty(deviceId, 'web-client'),
    };
    final GteTransportResponse response = await transport.send(
      GteTransportRequest(
        method: 'POST',
        uri: config.uriFor('/auth/refresh'),
        headers: headers,
        body: <String, Object?>{'refresh_token': refreshToken},
      ),
    );
    if (response.statusCode >= 400 || response.body is! Map) {
      await _clearSession();
      return false;
    }
    final Map<String, Object?> payload = Map<String, Object?>.from(
      response.body as Map,
    );
    final AuthSession refreshed = AuthSession.fromTokenPayload(payload);
    final AuthSession bootstrapMerged = await _bootstrapSession(refreshed);
    await _persistSession(bootstrapMerged);
    return true;
  }

  Future<AuthSession> _bootstrapSession(AuthSession session) async {
    final Map<String, String> headers = <String, String>{
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ${session.accessToken}',
      'X-User-Id': session.userId,
      'X-Session-Id': session.sessionId,
      'X-Device-Id': _firstNonEmpty(deviceId, 'web-client'),
    };
    final GteTransportResponse response = await transport.send(
      GteTransportRequest(
        method: 'GET',
        uri: config.uriFor('/api/session/bootstrap'),
        headers: headers,
      ),
    );
    if (response.statusCode >= 400 || response.body is! Map) {
      return session;
    }
    return session.mergeProfile(
      Map<String, Object?>.from(response.body as Map),
    );
  }

  Future<void> _persistSession(AuthSession session) async {
    await authSessionStore?.writeSession(session);
    await onSessionChanged?.call(session);
  }

  Future<void> _clearSession() async {
    await authSessionStore?.writeSession(null);
    await onSessionChanged?.call(null);
  }
}

String _firstNonEmpty(String? first, [String? second]) {
  final String resolvedFirst = first?.trim() ?? '';
  if (resolvedFirst.isNotEmpty) {
    return resolvedFirst;
  }
  return second?.trim() ?? '';
}

String? _stringClaim(Map<String, Object?> claims, String key) {
  final Object? value = claims[key];
  if (value == null) {
    return null;
  }
  final String resolved = value.toString().trim();
  return resolved.isEmpty ? null : resolved;
}

Map<String, Object?> _decodeJwtClaims(String token) {
  final List<String> segments = token.split('.');
  if (segments.length < 2) {
    return const <String, Object?>{};
  }
  try {
    final String normalized = base64Url.normalize(segments[1]);
    final Object? decoded = jsonDecode(
      utf8.decode(base64Url.decode(normalized)),
    );
    if (decoded is Map<String, dynamic>) {
      return Map<String, Object?>.from(decoded);
    }
    if (decoded is Map) {
      return decoded.map(
        (Object? key, Object? value) => MapEntry(key.toString(), value),
      );
    }
  } catch (_) {
    return const <String, Object?>{};
  }
  return const <String, Object?>{};
}
