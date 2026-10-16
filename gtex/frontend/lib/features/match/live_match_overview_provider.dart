import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../../shared/providers/auth_provider.dart';
import '../shared/data/gte_feature_support.dart';

class LiveMatchOverviewEntry {
  const LiveMatchOverviewEntry({
    required this.matchKey,
    required this.title,
    required this.subtitle,
    required this.channelLabel,
    required this.isFeatured,
    required this.isLive,
    this.watchRoute,
    this.replayRoute,
  });

  final String matchKey;
  final String title;
  final String subtitle;
  final String channelLabel;
  final bool isFeatured;
  final bool isLive;
  final String? watchRoute;
  final String? replayRoute;
}

class LiveMatchOverview {
  const LiveMatchOverview({
    required this.entries,
    required this.generatedAt,
    required this.sourcePath,
  });

  final List<LiveMatchOverviewEntry> entries;
  final DateTime? generatedAt;
  final String sourcePath;

  bool get isEmpty => entries.isEmpty;

  factory LiveMatchOverview.fromJson(JsonMap json) {
    final Map<String, _LiveMatchOverviewSeed> seeds =
        <String, _LiveMatchOverviewSeed>{};

    void upsertProgram(
      JsonMap? program, {
      required String channelLabel,
      required bool isFeatured,
      required bool isLive,
    }) {
      if (program == null) {
        return;
      }
      final String? matchKey = stringOrNullValue(program['match_id']);
      if (matchKey == null || matchKey.isEmpty) {
        return;
      }
      final _LiveMatchOverviewSeed seed =
          seeds[matchKey] ?? _LiveMatchOverviewSeed(matchKey: matchKey);
      final String title = stringValue(
        program['title'],
        fallback: 'Live match $matchKey',
      );
      final String subtitle = stringValue(
        program['subtitle'],
        fallback:
            stringOrNullValue(
              jsonMapOrNull(program['metadata'])?['focus_reason'],
            ) ??
            'Active broadcast program',
      );
      seeds[matchKey] = seed.merge(
        title: title,
        subtitle: subtitle,
        channelLabel: channelLabel,
        isFeatured: isFeatured,
        isLive: isLive || boolValue(program['is_live']),
        watchRoute: stringOrNullValue(program['watch_route']),
        replayRoute: stringOrNullValue(program['replay_route']),
      );
    }

    final JsonMap? featuredChannel = jsonMapOrNull(json['featured_channel']);
    final String featuredChannelLabel = stringValue(
      featuredChannel?['name'],
      fallback: 'Featured channel',
    );
    upsertProgram(
      jsonMapOrNull(featuredChannel?['current_program']),
      channelLabel: featuredChannelLabel,
      isFeatured: true,
      isLive: boolValue(featuredChannel?['is_live'], fallback: true),
    );

    for (final JsonMap channel in jsonMapList(
      json['channels'],
      label: 'channels',
    )) {
      upsertProgram(
        jsonMapOrNull(channel['current_program']),
        channelLabel: stringValue(channel['name'], fallback: 'Broadcast'),
        isFeatured:
            featuredChannel != null &&
            stringValue(channel['channel_id']) ==
                stringValue(featuredChannel['channel_id']),
        isLive: boolValue(channel['is_live'], fallback: true),
      );
    }

    upsertProgram(
      jsonMapOrNull(json['match_of_the_moment']),
      channelLabel: featuredChannelLabel,
      isFeatured: true,
      isLive: true,
    );

    final List<LiveMatchOverviewEntry> entries = seeds.values
        .map((_LiveMatchOverviewSeed seed) => seed.build())
        .toList(growable: false)
      ..sort((LiveMatchOverviewEntry left, LiveMatchOverviewEntry right) {
        final int featuredCompare = (right.isFeatured ? 1 : 0).compareTo(
          left.isFeatured ? 1 : 0,
        );
        if (featuredCompare != 0) {
          return featuredCompare;
        }
        final int liveCompare = (right.isLive ? 1 : 0).compareTo(
          left.isLive ? 1 : 0,
        );
        if (liveCompare != 0) {
          return liveCompare;
        }
        return left.title.compareTo(right.title);
      });

    return LiveMatchOverview(
      entries: entries,
      generatedAt: dateTimeValue(json['generated_at']),
      sourcePath: '/api/broadcast/home',
    );
  }
}

abstract class LiveMatchOverviewRepository {
  Future<LiveMatchOverview> loadOverview();
}

class ApiLiveMatchOverviewRepository implements LiveMatchOverviewRepository {
  const ApiLiveMatchOverviewRepository({required this.api});

  final GteAuthedApi api;

  @override
  Future<LiveMatchOverview> loadOverview() async {
    final JsonMap payload = await api.getMap('/api/broadcast/home', auth: false);
    return LiveMatchOverview.fromJson(payload);
  }
}

final Provider<LiveMatchOverviewRepository>
liveMatchOverviewRepositoryProvider = Provider<LiveMatchOverviewRepository>((
  Ref ref,
) {
  return ApiLiveMatchOverviewRepository(api: ref.watch(authedApiProvider));
});

final liveMatchOverviewProvider =
    FutureProvider.autoDispose<LiveMatchOverview>((Ref ref) {
      return ref.watch(liveMatchOverviewRepositoryProvider).loadOverview();
    });

class _LiveMatchOverviewSeed {
  const _LiveMatchOverviewSeed({
    required this.matchKey,
    this.title,
    this.subtitle,
    this.channelLabel,
    this.isFeatured = false,
    this.isLive = false,
    this.watchRoute,
    this.replayRoute,
  });

  final String matchKey;
  final String? title;
  final String? subtitle;
  final String? channelLabel;
  final bool isFeatured;
  final bool isLive;
  final String? watchRoute;
  final String? replayRoute;

  _LiveMatchOverviewSeed merge({
    required String title,
    required String subtitle,
    required String channelLabel,
    required bool isFeatured,
    required bool isLive,
    String? watchRoute,
    String? replayRoute,
  }) {
    return _LiveMatchOverviewSeed(
      matchKey: matchKey,
      title: this.title ?? title,
      subtitle: this.subtitle ?? subtitle,
      channelLabel: this.channelLabel ?? channelLabel,
      isFeatured: this.isFeatured || isFeatured,
      isLive: this.isLive || isLive,
      watchRoute: this.watchRoute ?? watchRoute,
      replayRoute: this.replayRoute ?? replayRoute,
    );
  }

  LiveMatchOverviewEntry build() {
    return LiveMatchOverviewEntry(
      matchKey: matchKey,
      title: title ?? 'Live match $matchKey',
      subtitle: subtitle ?? 'Active broadcast program',
      channelLabel: channelLabel ?? 'Broadcast',
      isFeatured: isFeatured,
      isLive: isLive,
      watchRoute: watchRoute,
      replayRoute: replayRoute,
    );
  }
}
