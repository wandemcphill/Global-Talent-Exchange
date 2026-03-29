import 'gte_api_repository.dart';
import '../shared/models/auth_session.dart';

class GteAuthedApi {
  GteAuthedApi({
    required this.config,
    required this.transport,
    this.accessToken,
    this.authSession,
    this.deviceId,
    this.mode = GteBackendMode.liveThenFixture,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String? accessToken;
  final AuthSession? authSession;
  final String? deviceId;
  final GteBackendMode mode;

  Future<T> withFallback<T>(
    Future<T> Function() live,
    Future<T> Function() fixtures,
  ) async {
    switch (mode) {
      case GteBackendMode.fixture:
        return fixtures();
      case GteBackendMode.liveThenFixture:
        try {
          return await live();
        } catch (_) {
          return fixtures();
        }
      case GteBackendMode.live:
        return live();
    }
  }

  Future<Object?> request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
    bool auth = true,
  }) async {
    final Map<String, String> headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (auth) {
      final String resolvedAccessToken =
          authSession?.accessToken ?? accessToken ?? '';
      if (resolvedAccessToken.isEmpty) {
        throw const GteApiException(
          type: GteApiErrorType.unauthorized,
          message: 'Authentication required for this action.',
        );
      }
      headers['Authorization'] = 'Bearer $resolvedAccessToken';
      final String resolvedDeviceId = deviceId?.trim() ?? '';
      if (authSession != null && resolvedDeviceId.isNotEmpty) {
        headers['X-User-Id'] = authSession!.userId;
        headers['X-Session-Id'] = authSession!.sessionId;
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
    return request(
      'POST',
      path,
      query: query,
      body: body,
      auth: auth,
    );
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
}
