import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_contracts.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/viral_feed/data/feed_validator.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_models.dart';

void main() {
  const ViralFeedValidator validator = ViralFeedValidator();

  test('accepts canonical personalized feed payloads', () {
    expect(
      () => validator.validateResponse(
        source: ViralFeedSource.forYou,
        refreshRequested: true,
        payload: <String, Object?>{
          FeedContractKeys.feedSource: FeedSource.forYou,
          'cache_hit': false,
          FeedContractKeys.items: <Object?>[
            <String, Object?>{
              'clip_id': 'clip-1',
              FeedContractKeys.feedSource: FeedSource.forYou,
            },
            <String, Object?>{
              'clip_id': 'clip-2',
              FeedContractKeys.feedSource: FeedSource.following,
            },
          ],
        },
      ),
      returnsNormally,
    );
  });

  test('throws when a feed item has an unsupported source', () {
    expect(
      () => validator.validateResponse(
        source: ViralFeedSource.following,
        refreshRequested: false,
        payload: <String, Object?>{
          FeedContractKeys.feedSource: FeedSource.following,
          'cache_hit': false,
          FeedContractKeys.items: <Object?>[
            <String, Object?>{
              'clip_id': 'clip-2',
              FeedContractKeys.feedSource: 'local_ranker',
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
