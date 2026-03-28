import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_http_transport.dart';
import '../../../services/frontend_audit_hooks.dart';
import '../../shared/data/gte_feature_support.dart';
import 'feed_validator.dart';
import 'viral_feed_models.dart';

abstract class ViralFeedRepository {
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
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
    String baseUrl = _apiBaseUrl,
    String? accessToken,
  }) {
    return ViralFeedApiRepository(
      client: GteAuthedApi(
        config: GteRepositoryConfig(
          baseUrl: baseUrl,
          mode: GteBackendMode.live,
        ),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: GteBackendMode.live,
      ),
      validator: const ViralFeedValidator(),
      auditHooks: FrontendAuditHooks(
        baseUrl: baseUrl,
        accessToken: accessToken,
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
    _validator.validateRequestSource(source);
    try {
      final JsonMap payload = await _client.getMap(
        source.path,
        query: compactQuery(<String, Object?>{
          'limit': limit,
          'refresh': refresh,
        }),
      );
      _validator.validateResponse(
        source: source,
        payload: payload,
        refreshRequested: refresh,
      );

      final List<ViralClip> clips = parseList(
        payload['clips'],
        ViralClip.fromJson,
        label: 'personalized feed clips',
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
        target: source.feedType,
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
        target: source.feedType,
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
          target: source.feedType,
          metadata: <String, Object?>{
            'feed_source_path': source.path,
            'refresh_requested': refresh,
          },
        );
      }
      return deck;
    } catch (error) {
      final int latencyMs = stopwatch.elapsedMilliseconds;
      await _auditHooks.trackApiResult(
        screen: 'viral_feed',
        flow: 'feed_load',
        target: source.feedType,
        success: false,
        latencyMs: latencyMs,
        metadata: <String, Object?>{
          'error': error.toString(),
          'feed_source_path': source.path,
          'refresh_requested': refresh,
        },
      );
      await _auditHooks.trackLatency(
        screen: 'viral_feed',
        flow: 'feed_load',
        target: source.feedType,
        latencyMs: latencyMs,
        metadata: <String, Object?>{
          'success': false,
          'feed_source_path': source.path,
        },
      );
      rethrow;
    }
  }
}

const String _apiBaseUrl = String.fromEnvironment(
  'GTE_API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);
