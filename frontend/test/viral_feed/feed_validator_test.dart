import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/viral_feed/data/feed_validator.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_models.dart';

void main() {
  const ViralFeedValidator validator = ViralFeedValidator();

  test('accepts canonical ranking engine payloads', () {
    expect(
      () => validator.validateResponse(
        source: ViralFeedSource.forYou,
        refreshRequested: true,
        payload: <String, Object?>{
          'feed_type': 'for_you',
          'cache_hit': false,
          'clips': <Object?>[
            <String, Object?>{
              'clip_id': 'clip-1',
              'feed_source': ViralFeedValidator.rankingEngineSource,
            },
          ],
        },
      ),
      returnsNormally,
    );
  });

  test('throws when a clip is not sourced from the ranking engine', () {
    expect(
      () => validator.validateResponse(
        source: ViralFeedSource.following,
        refreshRequested: false,
        payload: <String, Object?>{
          'feed_type': 'following',
          'cache_hit': false,
          'clips': <Object?>[
            <String, Object?>{
              'clip_id': 'clip-2',
              'feed_source': 'local_ranker',
            },
          ],
        },
      ),
      throwsA(
        isA<GteApiException>().having(
          (GteApiException error) => error.type,
          'type',
          GteApiErrorType.validation,
        ),
      ),
    );
  });
}
