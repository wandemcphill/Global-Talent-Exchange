import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';

import '../../../app/gte_app_config.dart';
import '../../../data/gte_api_contracts.dart';
import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_http_transport.dart';
import '../../../data/gte_models.dart';
import '../../../services/frontend_audit_hooks.dart';
import '../../../shared/models/auth_session.dart';
import '../../shared/data/gte_feature_support.dart';
import 'feed_validator.dart';
import 'viral_feed_models.dart';

abstract class ViralFeedRepository {
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
  });

  Future<ViralFeedDeckRefresh> refreshForYou({
    required int cursor,
    int limit = 10,
  });
}

class ViralFeedApiRepository implements ViralFeedRepository {
  ViralFeedApiRepository({
    required GteAuthedApi client,
    required ViralFeedValidator validator,
    required FrontendAuditHooks auditHooks,
  }) : _client = client,
       _validator = validator,
       _auditHooks = auditHooks;

  factory ViralFeedApiRepository.standard({
    String? baseUrl,
    String? accessToken,
    AuthSession? authSession,
    String? deviceId,
  }) {
    final String resolvedBaseUrl =
        baseUrl ?? resolveGteApiBaseUrlFromEnvironment();
    return ViralFeedApiRepository(
      client: GteAuthedApi(
        config: GteRepositoryConfig(
          baseUrl: resolvedBaseUrl,
          mode: GteBackendMode.live,
        ),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        authSession: authSession,
        deviceId: deviceId,
        mode: GteBackendMode.live,
      ),
      validator: const ViralFeedValidator(),
      auditHooks: FrontendAuditHooks(
        baseUrl: resolvedBaseUrl,
        accessToken: authSession?.accessToken ?? accessToken,
      ),
    );
  }

  final GteAuthedApi _client;
  final ViralFeedValidator _validator;
  final FrontendAuditHooks _auditHooks;

  @override
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
  }) async {
    final Stopwatch stopwatch = Stopwatch()..start();
    JsonMap? payload;
    _validator.validateRequestSource(source);
    try {
      payload = await _client.getMap(
        source.path,
        query: compactQuery(<String, Object?>{
          'limit': limit,
          'refresh': refresh,
          'session_id': _sessionId(),
        }),
      );
      _validator.validateResponse(
        source: source,
        payload: payload,
        refreshRequested: refresh,
      );

      final List<ViralClip> clips = parseList(
        payload[FeedContractKeys.items],
        ViralClip.fromJson,
        label: 'personalized feed items',
      );
      final ViralFeedDeck deck = ViralFeedDeck(
        source: source,
        feedKey: stringValue(payload['feed_key']),
        generatedAt:
            dateTimeValue(payload['generated_at']) ?? DateTime.now().toUtc(),
        cacheHit: boolValue(payload['cache_hit']),
        clips: clips,
      );

      final int latencyMs = stopwatch.elapsedMilliseconds;
      await _auditHooks.trackApiResult(
        screen: 'viral_feed',
        flow: 'feed_load',
        target: source.feedSource,
        success: true,
        latencyMs: latencyMs,
        metadata: <String, Object?>{
          'clip_count': clips.length,
          'feed_key': deck.feedKey,
          'feed_source_path': source.path,
          'cache_hit': deck.cacheHit,
          'refresh_requested': refresh,
        },
      );
      await _auditHooks.trackLatency(
        screen: 'viral_feed',
        flow: 'feed_load',
        target: source.feedSource,
        latencyMs: latencyMs,
        metadata: <String, Object?>{
          'clip_count': clips.length,
          'feed_source_path': source.path,
        },
      );
      if (clips.isEmpty) {
        await _auditHooks.trackDropOff(
          screen: 'viral_feed',
          flow: 'feed_load',
          stage: 'empty_state',
          target: source.feedSource,
          metadata: <String, Object?>{
            'feed_source_path': source.path,
            'refresh_requested': refresh,
          },
        );
      }
      return deck;
    } on GteParsingException catch (error) {
      final GteApiException contractError = GteApiException(
        type: GteApiErrorType.validation,
        message: error.message,
        cause: error,
      );
      await _trackContractFailure(
        source: source,
        refresh: refresh,
        latencyMs: stopwatch.elapsedMilliseconds,
        error: contractError,
        payload: payload,
      );
      throw contractError;
    } on GteApiException catch (error) {
      if (error.type == GteApiErrorType.validation) {
        await _trackContractFailure(
          source: source,
          refresh: refresh,
          latencyMs: stopwatch.elapsedMilliseconds,
          error: error,
          payload: payload,
        );
        rethrow;
      }
      await _trackFailure(
        source: source,
        refresh: refresh,
        latencyMs: stopwatch.elapsedMilliseconds,
        error: error,
      );
      rethrow;
    } catch (error) {
      await _trackFailure(
        source: source,
        refresh: refresh,
        latencyMs: stopwatch.elapsedMilliseconds,
        error: error,
      );
      rethrow;
    }
  }

  @override
  Future<ViralFeedDeckRefresh> refreshForYou({
    required int cursor,
    int limit = 10,
  }) async {
    final JsonMap payload = await _client.getMap(
      '/feed/for-you/refresh',
      query: compactQuery(<String, Object?>{
        'cursor': cursor,
        'limit': limit,
        'session_id': _sessionId(),
      }),
    );
    return ViralFeedDeckRefresh(
      replaceIndices: _intListValue(payload['replace_indices']),
      newItems: parseList(
        payload['new_items'],
        ViralClip.fromJson,
        label: 'personalized feed refresh items',
      ),
    );
  }

  Future<void> _trackContractFailure({
    required ViralFeedSource source,
    required bool refresh,
    required int latencyMs,
    required GteApiException error,
    JsonMap? payload,
  }) async {
    debugPrint(
      'ViralFeedApiRepository contract failure for ${source.path}: ${error.message}',
    );
    developer.log(
      'Viral feed contract failure',
      name: 'viral_feed.contract',
      error: error,
    );
    await _trackFailure(
      source: source,
      refresh: refresh,
      latencyMs: latencyMs,
      error: error,
      extraMetadata: <String, Object?>{
        'failure_kind': 'contract_validation',
        'expected_feed_source': source.feedSource,
        'payload_feed_source':
            payload?[FeedContractKeys.feedSource]?.toString(),
        'payload_keys':
            payload?.keys.toList(growable: false) ?? const <String>[],
      },
    );
  }

  Future<void> _trackFailure({
    required ViralFeedSource source,
    required bool refresh,
    required int latencyMs,
    required Object error,
    Map<String, Object?> extraMetadata = const <String, Object?>{},
  }) async {
    await _auditHooks.trackApiResult(
      screen: 'viral_feed',
      flow: 'feed_load',
      target: source.feedSource,
      success: false,
      latencyMs: latencyMs,
      metadata: <String, Object?>{
        'error': error.toString(),
        'feed_source_path': source.path,
        'refresh_requested': refresh,
        ...extraMetadata,
      },
    );
    await _auditHooks.trackLatency(
      screen: 'viral_feed',
      flow: 'feed_load',
      target: source.feedSource,
      latencyMs: latencyMs,
      metadata: <String, Object?>{
        'success': false,
        'feed_source_path': source.path,
        if (extraMetadata.isNotEmpty)
          'failure_kind': extraMetadata['failure_kind'],
      },
    );
  }

  String? _sessionId() {
    final String sessionId = _client.authSession?.sessionId.trim() ?? '';
    return sessionId.isEmpty ? null : sessionId;
  }
}

List<int> _intListValue(Object? value) {
  if (value is! List) {
    return const <int>[];
  }
  return value
      .map((Object? item) {
        if (item is int) {
          return item;
        }
        if (item is num) {
          return item.toInt();
        }
        return int.tryParse(item?.toString() ?? '');
      })
      .whereType<int>()
      .toList(growable: false);
}
