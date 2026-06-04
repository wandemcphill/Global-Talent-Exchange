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
      required String? channelLabel,
      required bool isFeatured,
      required bool? isLive,
    }) {
      if (program == null) {
        return;
      }
      final String? matchKey = _nonEmptyStringValue(program['match_id']);
      if (matchKey == null || matchKey.isEmpty) {
        return;
      }
      final String? title = _nonEmptyStringValue(program['title']);
      final String? subtitle = _nonEmptyStringValue(program['subtitle']);
      final String? resolvedChannelLabel =
          _nonEmptyStringValue(program['channel_label']) ??
          _nonEmptyStringValue(program['channel_name']) ??
          _nonEmptyStringValue(program['channel']) ??
          channelLabel;
      final bool? resolvedIsLive =
          _boolOrNullValue(program['is_live']) ?? isLive;
      if (title == null ||
          subtitle == null ||
          resolvedChannelLabel == null ||
          resolvedIsLive == null) {
        return;
      }
      final _LiveMatchOverviewSeed seed =
          seeds[matchKey] ?? _LiveMatchOverviewSeed(matchKey: matchKey);
      seeds[matchKey] = seed.merge(
        title: title,
        subtitle: subtitle,
        channelLabel: resolvedChannelLabel,
        isFeatured: isFeatured,
        isLive: resolvedIsLive,
        watchRoute: stringOrNullValue(program['watch_route']),
        replayRoute: stringOrNullValue(program['replay_route']),
      );
    }

    final JsonMap? featuredChannel = jsonMapOrNull(json['featured_channel']);
    final String? featuredChannelLabel = _nonEmptyStringValue(
      featuredChannel?['name'],
    );
    final bool? featuredChannelIsLive = _boolOrNullValue(
      featuredChannel?['is_live'],
    );
    upsertProgram(
      jsonMapOrNull(featuredChannel?['current_program']),
      channelLabel: featuredChannelLabel,
      isFeatured: true,
      isLive: featuredChannelIsLive,
    );

    for (final JsonMap channel in jsonMapList(
      json['channels'],
      label: 'channels',
    )) {
      final String? channelId = _nonEmptyStringValue(channel['channel_id']);
      final String? featuredChannelId = _nonEmptyStringValue(
        featuredChannel?['channel_id'],
      );
      upsertProgram(
        jsonMapOrNull(channel['current_program']),
        channelLabel: _nonEmptyStringValue(channel['name']),
        isFeatured: featuredChannelId != null && channelId == featuredChannelId,
        isLive: _boolOrNullValue(channel['is_live']),
      );
    }

    upsertProgram(
      jsonMapOrNull(json['match_of_the_moment']),
      channelLabel: featuredChannelLabel,
      isFeatured: true,
      isLive: featuredChannelIsLive,
    );

    final List<LiveMatchOverviewEntry> entries = seeds.values
        .map((_LiveMatchOverviewSeed seed) => seed.buildOrNull())
        .whereType<LiveMatchOverviewEntry>()
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
    final JsonMap payload = await api.getMap(
      '/api/broadcast/home',
      auth: false,
    );
    return LiveMatchOverview.fromJson(payload);
  }
}

final Provider<LiveMatchOverviewRepository>
liveMatchOverviewRepositoryProvider = Provider<LiveMatchOverviewRepository>((
  Ref ref,
) {
  return ApiLiveMatchOverviewRepository(api: ref.watch(authedApiProvider));
});

final liveMatchOverviewProvider = FutureProvider.autoDispose<LiveMatchOverview>(
  (Ref ref) {
    return ref.watch(liveMatchOverviewRepositoryProvider).loadOverview();
  },
);

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

  LiveMatchOverviewEntry? buildOrNull() {
    final String? resolvedTitle = title;
    final String? resolvedSubtitle = subtitle;
    final String? resolvedChannelLabel = channelLabel;
    if (resolvedTitle == null ||
        resolvedSubtitle == null ||
        resolvedChannelLabel == null) {
      return null;
    }
    return LiveMatchOverviewEntry(
      matchKey: matchKey,
      title: resolvedTitle,
      subtitle: resolvedSubtitle,
      channelLabel: resolvedChannelLabel,
      isFeatured: isFeatured,
      isLive: isLive,
      watchRoute: watchRoute,
      replayRoute: replayRoute,
    );
  }
}

String? _nonEmptyStringValue(Object? value) {
  final String? text = stringOrNullValue(value)?.trim();
  if (text == null || text.isEmpty) {
    return null;
  }
  return text;
}

bool? _boolOrNullValue(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  final String? text = stringOrNullValue(value)?.trim().toLowerCase();
  if (text == null || text.isEmpty) {
    return null;
  }
  if (text == 'true' || text == '1' || text == 'yes') {
    return true;
  }
  if (text == 'false' || text == '0' || text == 'no') {
    return false;
  }
  return null;
}
