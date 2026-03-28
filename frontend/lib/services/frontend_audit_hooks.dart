import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class FrontendAuditHooks {
  FrontendAuditHooks({
    required String baseUrl,
    String? accessToken,
    http.Client? client,
  }) : _baseUri = Uri.parse(baseUrl),
       _accessToken = accessToken,
       _client = client ?? http.Client();

  final Uri _baseUri;
  final String? _accessToken;
  final http.Client _client;

  Future<void> trackButtonClick({
    required String screen,
    required String flow,
    required String target,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    return _post(
      name: _eventName(target),
      category: 'button_click',
      screen: screen,
      flow: flow,
      target: target,
      success: true,
      metadata: metadata,
    );
  }

  Future<void> trackApiResult({
    required String screen,
    required String flow,
    required String target,
    required bool success,
    int? statusCode,
    int? latencyMs,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    return _post(
      name: _eventName(target),
      category: 'api_result',
      screen: screen,
      flow: flow,
      target: target,
      success: success,
      statusCode: statusCode,
      latencyMs: latencyMs,
      metadata: metadata,
    );
  }

  Future<void> trackLatency({
    required String screen,
    required String flow,
    required String target,
    required int latencyMs,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    return _post(
      name: _eventName(target),
      category: 'latency',
      screen: screen,
      flow: flow,
      target: target,
      success: true,
      latencyMs: latencyMs,
      metadata: metadata,
    );
  }

  Future<void> trackDropOff({
    required String screen,
    required String flow,
    required String stage,
    String? target,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    return _post(
      name: _eventName(stage),
      category: 'drop_off',
      screen: screen,
      flow: flow,
      target: target,
      stage: stage,
      success: false,
      metadata: metadata,
    );
  }

  Future<void> _post({
    required String name,
    required String category,
    required String screen,
    required String flow,
    String? target,
    String? stage,
    bool? success,
    int? statusCode,
    int? latencyMs,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) async {
    final Uri uri = _baseUri.resolve('/analytics/frontend');
    final Map<String, String> headers = <String, String>{
      'Content-Type': 'application/json',
    };
    final String? token = _accessToken?.trim();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    try {
      await _client
          .post(
            uri,
            headers: headers,
            body: jsonEncode(<String, Object?>{
              'name': name,
              'category': category,
              'screen': screen,
              'flow': flow,
              if (target != null && target.isNotEmpty) 'target': target,
              if (stage != null && stage.isNotEmpty) 'stage': stage,
              if (success != null) 'success': success,
              if (statusCode != null) 'status_code': statusCode,
              if (latencyMs != null) 'latency_ms': latencyMs,
              'metadata': metadata,
            }),
          )
          .timeout(const Duration(seconds: 3));
    } catch (error) {
      if (kDebugMode) {
        debugPrint('frontend_audit_hooks post failed: $error');
      }
    }
  }

  static String _eventName(String value) {
    final String normalized = value.trim().toLowerCase().replaceAll(
      RegExp(r'[^a-z0-9]+'),
      '_',
    );
    return normalized.isEmpty
        ? 'event'
        : normalized.substring(
          0,
          normalized.length > 64 ? 64 : normalized.length,
        );
  }
}
