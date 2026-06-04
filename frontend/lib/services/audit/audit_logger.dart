import 'dart:async';

import 'package:dio/dio.dart';

import 'audit_event.dart';

typedef AuditLocalSink = FutureOr<void> Function(AuditEvent event);

class AuditLogResult {
  const AuditLogResult({
    required this.confirmed,
    this.auditRef,
    this.queuedLocally = false,
    this.errorCode,
  });

  final bool confirmed;
  final String? auditRef;
  final bool queuedLocally;
  final String? errorCode;
}

class AuditLogger {
  AuditLogger({
    required Dio dio,
    String endpoint = '/audit/events',
    AuditLocalSink? localSink,
    this.requireBackendConfirmation = false,
  }) : _dio = dio,
       _endpoint = endpoint,
       _localSink = localSink;

  final Dio _dio;
  final String _endpoint;
  final AuditLocalSink? _localSink;
  final bool requireBackendConfirmation;

  Future<AuditLogResult> log(AuditEvent event) async {
    await _writeLocal(event);
    try {
      final Response<dynamic> response = await _dio.post<dynamic>(
        _endpoint,
        data: event.toJson(),
      );
      return AuditLogResult(
        confirmed: true,
        auditRef: _auditRefFrom(response.data) ?? event.idempotencyKey,
      );
    } catch (error) {
      if (requireBackendConfirmation) {
        rethrow;
      }
      return AuditLogResult(
        confirmed: false,
        queuedLocally: true,
        auditRef: event.idempotencyKey,
        errorCode: _errorCode(error),
      );
    }
  }

  Future<void> _writeLocal(AuditEvent event) async {
    final AuditLocalSink? localSink = _localSink;
    if (localSink == null) {
      return;
    }
    try {
      await localSink(event);
    } catch (_) {
      // Local audit cache failures must not prevent backend dispatch.
    }
  }
}

String? _auditRefFrom(Object? value) {
  if (value is! Map) {
    return null;
  }
  for (final Object? candidate in <Object?>[
    value['audit_ref'],
    value['auditRef'],
    value['audit_id'],
    value['id'],
  ]) {
    final String text = candidate?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return null;
}

String _errorCode(Object error) {
  if (error is DioException) {
    final Object? mapped = error.error;
    if (mapped != null) {
      return mapped.runtimeType.toString();
    }
    return error.type.name;
  }
  return error.runtimeType.toString();
}
