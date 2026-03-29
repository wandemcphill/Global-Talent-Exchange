import '../../../data/gte_api_contracts.dart';
import '../../../data/gte_api_repository.dart';
import '../../shared/data/gte_feature_support.dart';
import 'viral_feed_models.dart';

class ViralFeedValidator {
  const ViralFeedValidator();

  static const Set<String> allowedSources = FeedSource.values;

  static const Set<String> _allowedPaths = <String>{
    '/feed/for-you',
    '/feed/following',
  };

  void validateRequestSource(ViralFeedSource source) {
    if (_allowedPaths.contains(source.path)) {
      return;
    }
    throw GteApiException(
      type: GteApiErrorType.validation,
      message: 'Unsupported feed source path "${source.path}".',
    );
  }

  void validateResponse({
    required ViralFeedSource source,
    required JsonMap payload,
    required bool refreshRequested,
  }) {
    final String feedSource = stringValue(payload[FeedContractKeys.feedSource]);
    if (feedSource != source.feedSource) {
      throw GteApiException(
        type: GteApiErrorType.validation,
        message:
            'Feed source mismatch. Expected "${source.feedSource}" but received "$feedSource".',
      );
    }

    if (refreshRequested && boolValue(payload['cache_hit'])) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Feed refresh returned a cached payload.',
      );
    }

    final List<JsonMap> items = jsonMapList(
      payload[FeedContractKeys.items],
      label: 'personalized feed items',
    );
    for (int index = 0; index < items.length; index += 1) {
      final JsonMap clip = items[index];
      final String clipId = stringValue(
        clip['clip_id'],
        fallback: 'clip-$index',
      );
      final String itemSource = stringValue(clip[FeedContractKeys.feedSource]);
      if (!allowedSources.contains(itemSource)) {
        throw GteApiException(
          type: GteApiErrorType.validation,
          message: 'Feed item "$clipId" has unsupported source "$itemSource".',
        );
      }
    }
  }
}
