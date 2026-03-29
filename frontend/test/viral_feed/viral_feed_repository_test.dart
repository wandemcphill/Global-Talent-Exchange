import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_contracts.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/viral_feed/data/feed_validator.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_models.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_repository.dart';
import 'package:gte_frontend/services/frontend_audit_hooks.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('repository logs and rethrows malformed feed responses', () async {
    final List<Map<String, Object?>> analyticsEvents = <Map<String, Object?>>[];
    final MockClient auditClient = MockClient((http.Request request) async {
      analyticsEvents.add(
        Map<String, Object?>.from(
          jsonDecode(request.body) as Map<String, dynamic>,
        ),
      );
      return http.Response('{}', 200);
    });
    final ViralFeedApiRepository repository = ViralFeedApiRepository(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(baseUrl: 'http://example.com'),
        transport: _FakeTransport(<String, Object?>{
          FeedContractKeys.feedSource: FeedSource.forYou,
          'feed_key': 'feed-key',
          'generated_at': '2026-03-28T00:00:00Z',
          'cache_hit': false,
          FeedContractKeys.items: <Object?>[
            <String, Object?>{
              'clip_id': 'clip-1',
              FeedContractKeys.feedSource: 'legacy_source',
            },
          ],
        }),
        accessToken: 'token',
        mode: GteBackendMode.live,
      ),
      validator: const ViralFeedValidator(),
      auditHooks: FrontendAuditHooks(
        baseUrl: 'http://example.com',
        accessToken: 'token',
        client: auditClient,
      ),
    );

    await expectLater(
      repository.fetchDeck(source: ViralFeedSource.forYou),
      throwsA(
        isA<GteApiException>()
            .having(
              (GteApiException error) => error.type,
              'type',
              GteApiErrorType.validation,
            )
            .having(
              (GteApiException error) => error.message,
              'message',
              contains('unsupported source'),
            ),
      ),
    );

    expect(
      analyticsEvents.where(
        (Map<String, Object?> event) =>
            event['category'] == 'api_result' &&
            event['success'] == false &&
            (event['metadata'] as Map<String, Object?>)['failure_kind'] ==
                'contract_validation',
      ),
      isNotEmpty,
    );
  });
}

class _FakeTransport implements GteTransport {
  const _FakeTransport(this._body);

  final Object? _body;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return GteTransportResponse(statusCode: 200, body: _body);
  }
}
