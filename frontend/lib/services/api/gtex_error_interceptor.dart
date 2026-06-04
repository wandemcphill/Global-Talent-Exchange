import 'package:dio/dio.dart';

class GtexApiException implements Exception {
  const GtexApiException({
    required this.code,
    required this.message,
    this.statusCode,
    this.requestId,
    this.details,
  });

  final String code;
  final String message;
  final int? statusCode;
  final String? requestId;
  final Object? details;

  @override
  String toString() {
    final String status = statusCode == null ? '' : ' [$statusCode]';
    final String request = requestId == null ? '' : ' request=$requestId';
    return 'GtexApiException$status $code: $message$request';
  }
}

class GtexErrorInterceptor extends Interceptor {
  const GtexErrorInterceptor();

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.error is GtexApiException) {
      handler.next(err);
      return;
    }
    handler.next(_mapException(err));
  }

  DioException _mapException(DioException err) {
    final Response<dynamic>? response = err.response;
    final GtexApiException exception =
        response == null
            ? _networkException(err)
            : _responseException(response);
    return DioException(
      requestOptions: err.requestOptions,
      response: response,
      type: err.type,
      error: exception,
      stackTrace: err.stackTrace,
      message: exception.message,
    );
  }

  GtexApiException _networkException(DioException err) {
    final String code = switch (err.type) {
      DioExceptionType.cancel => 'request_cancelled',
      DioExceptionType.connectionTimeout => 'connection_timeout',
      DioExceptionType.sendTimeout => 'send_timeout',
      DioExceptionType.receiveTimeout => 'receive_timeout',
      DioExceptionType.badCertificate => 'bad_certificate',
      DioExceptionType.connectionError => 'connection_error',
      DioExceptionType.unknown => 'network_error',
      DioExceptionType.badResponse => 'network_error',
    };
    return GtexApiException(
      code: code,
      message: err.message ?? 'GTEX API request failed before a response.',
      details: err.error,
    );
  }

  GtexApiException _responseException(Response<dynamic> response) {
    final Map<String, Object?> fields = _errorFields(response.data);
    final int statusCode = response.statusCode ?? 0;
    return GtexApiException(
      code: _stringField(fields, const <String>[
        'code',
        'error_code',
        'error',
      ], fallback: _codeForStatus(statusCode)),
      message: _stringField(fields, const <String>[
        'message',
        'detail',
        'title',
      ], fallback: _messageForStatus(statusCode)),
      statusCode: statusCode,
      requestId:
          _header(response, 'x-request-id') ??
          _header(response, 'x-correlation-id') ??
          _header(response, 'traceparent'),
      details: response.data,
    );
  }
}

Map<String, Object?> _errorFields(Object? value) {
  if (value is Map) {
    return <String, Object?>{
      for (final MapEntry<dynamic, dynamic> entry in value.entries)
        entry.key.toString(): entry.value,
    };
  }
  if (value is String && value.trim().isNotEmpty) {
    return <String, Object?>{'message': value.trim()};
  }
  return const <String, Object?>{};
}

String _stringField(
  Map<String, Object?> fields,
  List<String> keys, {
  required String fallback,
}) {
  for (final String key in keys) {
    final String value = fields[key]?.toString().trim() ?? '';
    if (value.isNotEmpty) {
      return value;
    }
  }
  return fallback;
}

String? _header(Response<dynamic> response, String name) {
  final String? value = response.headers.value(name);
  final String trimmed = value?.trim() ?? '';
  return trimmed.isEmpty ? null : trimmed;
}

String _codeForStatus(int statusCode) {
  return switch (statusCode) {
    400 => 'bad_request',
    401 => 'unauthorized',
    403 => 'forbidden',
    404 => 'not_found',
    409 => 'conflict',
    422 => 'validation_error',
    429 => 'rate_limited',
    >= 500 => 'server_error',
    _ => 'api_error',
  };
}

String _messageForStatus(int statusCode) {
  return switch (statusCode) {
    400 => 'The API rejected this request.',
    401 => 'Authentication is required for this GTEX request.',
    403 => 'This GTEX action is not allowed for the current actor.',
    404 => 'The requested GTEX resource was not found.',
    409 => 'The GTEX resource is in a conflicting state.',
    422 => 'The API could not validate this GTEX request.',
    429 => 'The API rate limit was reached.',
    >= 500 => 'The GTEX API is temporarily unavailable.',
    _ => 'The GTEX API request failed.',
  };
}
