import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

typedef GtexApiLogSink = void Function(String message);

class GtexLoggingInterceptor extends Interceptor {
  GtexLoggingInterceptor({this.enabled = kDebugMode, GtexApiLogSink? log})
    : _log = log ?? debugPrint;

  final bool enabled;
  final GtexApiLogSink _log;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    _write(
      'GTEX API -> ${options.method} ${options.uri} '
      'headers=${_redactedHeaders(options.headers)}',
    );
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    _write(
      'GTEX API <- ${response.statusCode} '
      '${response.requestOptions.method} ${response.requestOptions.uri}',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    _write(
      'GTEX API xx ${err.response?.statusCode ?? err.type.name} '
      '${err.requestOptions.method} ${err.requestOptions.uri}',
    );
    handler.next(err);
  }

  void _write(String message) {
    if (enabled) {
      _log(message);
    }
  }
}

Map<String, Object?> _redactedHeaders(Map<String, dynamic> headers) {
  return <String, Object?>{
    for (final MapEntry<String, dynamic> entry in headers.entries)
      entry.key:
          entry.key.toLowerCase() == 'authorization'
              ? '<redacted>'
              : entry.value,
  };
}
