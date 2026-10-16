import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/story_feed_api.dart';
import '../../../models/story_feed_models.dart';
import '../../../shared/providers/auth_provider.dart';

/// Featured / recent story-feed headlines for the Home transfer ticker.
///
/// Same durable desk as News Agency (`GET /api/story-feed`). Failures resolve
/// to an empty list so the ticker can still show market/comp/regen chips.
final FutureProvider<List<StoryFeedItem>> storyFeedTickerProvider =
    FutureProvider<List<StoryFeedItem>>((Ref ref) async {
      final StoryFeedApi api = StoryFeedApi.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        accessToken: ref.watch(accessTokenProvider),
        mode: ref.watch(criticalBackendModeProvider),
      );
      try {
        final List<StoryFeedItem> items = await api.listFeed(limit: 12);
        final List<StoryFeedItem> sorted = List<StoryFeedItem>.from(items)
          ..sort((StoryFeedItem a, StoryFeedItem b) {
            final int featuredCmp = (b.featured ? 1 : 0) - (a.featured ? 1 : 0);
            if (featuredCmp != 0) {
              return featuredCmp;
            }
            return b.createdAt.compareTo(a.createdAt);
          });
        return List<StoryFeedItem>.unmodifiable(sorted);
      } catch (_) {
        return const <StoryFeedItem>[];
      }
    });
