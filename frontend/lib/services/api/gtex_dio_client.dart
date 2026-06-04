import 'package:dio/dio.dart';

import 'gtex_auth_interceptor.dart';
import 'gtex_error_interceptor.dart';
import 'gtex_logging_interceptor.dart';

class GtexDioClient {
  const GtexDioClient._();

  static Dio create({
    required String baseUrl,
    GtexAccessTokenProvider? accessTokenProvider,
    GtexTokenRefresher? refreshToken,
    GtexUnauthorizedHandler? onUnauthorized,
    Duration connectTimeout = const Duration(seconds: 10),
    Duration receiveTimeout = const Duration(seconds: 20),
    Duration sendTimeout = const Duration(seconds: 20),
    bool enableLogging = false,
    GtexApiLogSink? log,
    Iterable<Interceptor> interceptors = const <Interceptor>[],
  }) {
    final Dio dio = Dio(
      BaseOptions(
        baseUrl: _normalizeBaseUrl(baseUrl),
        connectTimeout: connectTimeout,
        receiveTimeout: receiveTimeout,
        sendTimeout: sendTimeout,
        responseType: ResponseType.json,
        headers: const <String, Object?>{
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-GTEX-Client': 'flutter',
        },
        validateStatus: (int? status) {
          return status != null && status >= 200 && status < 300;
        },
      ),
    );

    if (accessTokenProvider != null || refreshToken != null) {
      dio.interceptors.add(
        GtexAuthInterceptor(
          accessTokenProvider: accessTokenProvider,
          refreshToken: refreshToken,
          retryClient: dio,
          onUnauthorized: onUnauthorized,
        ),
      );
    }
    dio.interceptors.add(const GtexErrorInterceptor());
    if (enableLogging) {
      dio.interceptors.add(GtexLoggingInterceptor(enabled: true, log: log));
    }
    dio.interceptors.addAll(interceptors);
    return dio;
  }
}

String _normalizeBaseUrl(String value) {
  final String trimmed = value.trim();
  if (trimmed.isEmpty) {
    throw ArgumentError.value(
      value,
      'baseUrl',
      'GTEX API baseUrl is required.',
    );
  }
  return trimmed.endsWith('/') ? trimmed : '$trimmed/';
}
