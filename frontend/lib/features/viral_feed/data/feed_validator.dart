import '../../../data/gte_api_repository.dart';
import '../../shared/data/gte_feature_support.dart';
import 'viral_feed_models.dart';

class ViralFeedValidator {
  const ViralFeedValidator();

  static const String rankingEngineSource = 'ranking_engine';

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
    final String feedType = stringValue(payload['feed_type']);
    if (feedType != source.feedType) {
      throw GteApiException(
        type: GteApiErrorType.validation,
        message:
            'Feed type mismatch. Expected "${source.feedType}" but received "$feedType".',
      );
    }

    if (refreshRequested && boolValue(payload['cache_hit'])) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Feed refresh returned a cached payload.',
      );
    }

    final List<JsonMap> clips = jsonMapList(
      payload['clips'],
      label: 'personalized feed clips',
    );
    for (int index = 0; index < clips.length; index += 1) {
      final JsonMap clip = clips[index];
      final String clipId = stringValue(
        clip['clip_id'],
        fallback: 'clip-$index',
      );
      final String feedSource = stringValue(clip['feed_source']);
      if (feedSource != rankingEngineSource) {
        throw GteApiException(
          type: GteApiErrorType.validation,
          message:
              'Feed clip "$clipId" must come from "$rankingEngineSource".',
        );
      }
    }
  }
}
