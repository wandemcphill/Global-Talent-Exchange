import 'dart:async';

import 'package:dio/dio.dart';

typedef GtexAccessTokenProvider = FutureOr<String?> Function();
typedef GtexTokenRefresher = FutureOr<String?> Function();
typedef GtexUnauthorizedHandler = FutureOr<void> Function(DioException error);

class GtexAuthInterceptor extends Interceptor {
  GtexAuthInterceptor({
    GtexAccessTokenProvider? accessTokenProvider,
    GtexTokenRefresher? refreshToken,
    Dio? retryClient,
    GtexUnauthorizedHandler? onUnauthorized,
    this.authorizationScheme = 'Bearer',
  }) : _accessTokenProvider = accessTokenProvider,
       _refreshToken = refreshToken,
       _retryClient = retryClient,
       _onUnauthorized = onUnauthorized;

  static const String _retriedExtraKey = 'gtex.auth.retried';

  final GtexAccessTokenProvider? _accessTokenProvider;
  final GtexTokenRefresher? _refreshToken;
  final Dio? _retryClient;
  final GtexUnauthorizedHandler? _onUnauthorized;
  final String authorizationScheme;

  String? _refreshedAccessToken;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    options.headers.putIfAbsent('Accept', () => 'application/json');
    final String? token = await _resolveToken();
    if (token != null) {
      options.headers['Authorization'] = '$authorizationScheme $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (!_shouldRefresh(err)) {
      handler.next(err);
      return;
    }

    try {
      final String? refreshed = (await _refreshToken?.call())?.trim();
      if (refreshed == null || refreshed.isEmpty) {
        await _onUnauthorized?.call(err);
        handler.next(err);
        return;
      }
      _refreshedAccessToken = refreshed;

      final Dio? retryClient = _retryClient;
      if (retryClient == null) {
        handler.next(err);
        return;
      }

      final RequestOptions request = err.requestOptions;
      request.extra[_retriedExtraKey] = true;
      request.headers['Authorization'] = '$authorizationScheme $refreshed';
      final Response<dynamic> retryResponse = await retryClient.fetch<dynamic>(
        request,
      );
      handler.resolve(retryResponse);
    } catch (_) {
      await _onUnauthorized?.call(err);
      handler.next(err);
    }
  }

  Future<String?> _resolveToken() async {
    final String? refreshed = _refreshedAccessToken?.trim();
    if (refreshed != null && refreshed.isNotEmpty) {
      return refreshed;
    }
    final String? provided = (await _accessTokenProvider?.call())?.trim();
    if (provided != null && provided.isNotEmpty) {
      return provided;
    }
    return null;
  }

  bool _shouldRefresh(DioException err) {
    return err.response?.statusCode == 401 &&
        _refreshToken != null &&
        err.requestOptions.extra[_retriedExtraKey] != true;
  }
}
