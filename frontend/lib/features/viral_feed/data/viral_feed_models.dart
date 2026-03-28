import '../../shared/data/gte_feature_support.dart';

enum ViralFeedSource { forYou, following }

extension ViralFeedSourceX on ViralFeedSource {
  String get path {
    switch (this) {
      case ViralFeedSource.forYou:
        return '/feed/for-you';
      case ViralFeedSource.following:
        return '/feed/following';
    }
  }

  String get feedType {
    switch (this) {
      case ViralFeedSource.forYou:
        return 'for_you';
      case ViralFeedSource.following:
        return 'following';
    }
  }

  String get label {
    switch (this) {
      case ViralFeedSource.forYou:
        return 'FOR YOU';
      case ViralFeedSource.following:
        return 'FOLLOWING';
    }
  }
}

class ViralFeedDeck {
  const ViralFeedDeck({
    required this.source,
    required this.feedKey,
    required this.generatedAt,
    required this.cacheHit,
    required this.clips,
    this.debatesByMatch = const <String, PunditDebate>{},
  });

  final ViralFeedSource source;
  final String feedKey;
  final DateTime generatedAt;
  final bool cacheHit;
  final List<ViralClip> clips;
  final Map<String, PunditDebate> debatesByMatch;
}

class ViralClip {
  const ViralClip({
    required this.clipId,
    required this.matchId,
    required this.highlightId,
    required this.title,
    required this.eventType,
    required this.minute,
    required this.viralScore,
    required this.rankingScore,
    required this.caption,
    required this.tags,
    required this.rank,
    required this.score,
    required this.feedSource,
    required this.metadata,
    this.teamName,
    this.playerName,
    this.scorelineLabel,
    this.videoUrl,
    this.durationSeconds,
    this.shareChannel = 'whatsapp',
  });

  factory ViralClip.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'viral clip');
    final String matchId = stringValue(json['match_id']);
    final String highlightId = stringValue(json['highlight_id']);
    return ViralClip(
      clipId: stringValue(
        json['clip_id'],
        fallback: '$matchId::$highlightId',
      ),
      matchId: matchId,
      highlightId: highlightId,
      title: stringValue(json['title']),
      eventType: stringValue(json['event_type']),
      minute: intValue(json['minute']),
      viralScore: intValue(json['viral_score']),
      rankingScore: numberValue(json['ranking_score']),
      caption: ViralCaption.fromJson(json['caption']),
      tags: stringListValue(json['tags']),
      rank: intValue(json['rank']),
      score: numberValue(json['score']),
      feedSource: stringValue(json['feed_source']),
      metadata: jsonMap(
        json['metadata'],
        label: 'viral clip metadata',
        fallback: const <String, Object?>{},
      ),
      teamName: stringOrNullValue(json['team_name']),
      playerName: stringOrNullValue(json['player_name']),
      scorelineLabel: stringOrNullValue(json['scoreline_label']),
      videoUrl: stringOrNullValue(json['video_url']),
      durationSeconds: _numberOrNullValue(json['duration_seconds']),
      shareChannel: stringValue(json['share_channel'], fallback: 'whatsapp'),
    );
  }

  final String clipId;
  final String matchId;
  final String highlightId;
  final String title;
  final String eventType;
  final int minute;
  final int viralScore;
  final double rankingScore;
  final ViralCaption caption;
  final List<String> tags;
  final int rank;
  final double score;
  final String feedSource;
  final JsonMap metadata;
  final String? teamName;
  final String? playerName;
  final String? scorelineLabel;
  final String? videoUrl;
  final double? durationSeconds;
  final String shareChannel;

  int? get videoLengthMs {
    if (durationSeconds == null || durationSeconds! <= 0) {
      return null;
    }
    return (durationSeconds! * 1000).round();
  }

  String? get summaryLine => stringOrNullValue(metadata['summary_line']);

  String? get creatorId => _firstString(
    metadata,
    const <String>['creator_user_id', 'creator_id', 'author_user_id'],
  );
}

double? _numberOrNullValue(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

String? _firstString(JsonMap payload, List<String> keys) {
  for (final String key in keys) {
    final String? resolved = stringOrNullValue(payload[key]);
    if (resolved != null) {
      return resolved;
    }
  }
  return null;
}

class ViralCaption {
  const ViralCaption({
    required this.hook,
    required this.caption,
    required this.cta,
    required this.hashtags,
  });

  factory ViralCaption.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'viral caption');
    return ViralCaption(
      hook: stringValue(json['hook']),
      caption: stringValue(json['caption']),
      cta: stringValue(json['cta'], fallback: 'Share to WhatsApp'),
      hashtags: stringListValue(json['hashtags']),
    );
  }

  final String hook;
  final String caption;
  final String cta;
  final List<String> hashtags;
}

class PunditDebate {
  const PunditDebate({
    required this.matchId,
    required this.headline,
    required this.hotTakes,
    required this.lines,
  });

  factory PunditDebate.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'pundit debate');
    return PunditDebate(
      matchId: stringValue(json['match_id']),
      headline: stringValue(json['headline']),
      hotTakes: stringListValue(json['hot_takes']),
      lines: parseList(
        json['lines'],
        PunditDebateLine.fromJson,
        label: 'pundit lines',
      ),
    );
  }

  final String matchId;
  final String headline;
  final List<String> hotTakes;
  final List<PunditDebateLine> lines;
}

class PunditDebateLine {
  const PunditDebateLine({
    required this.speaker,
    required this.line,
    required this.emphasis,
  });

  factory PunditDebateLine.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'pundit line');
    return PunditDebateLine(
      speaker: stringValue(json['speaker']),
      line: stringValue(json['line']),
      emphasis: stringValue(json['emphasis'], fallback: 'medium'),
    );
  }

  final String speaker;
  final String line;
  final String emphasis;
}
