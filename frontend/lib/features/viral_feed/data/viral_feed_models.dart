import '../../shared/data/gte_feature_support.dart';

class ViralFeedDeck {
  const ViralFeedDeck({required this.clips, required this.debatesByMatch});

  final List<ViralClip> clips;
  final Map<String, PunditDebate> debatesByMatch;
}

class ViralClip {
  const ViralClip({
    required this.matchId,
    required this.highlightId,
    required this.title,
    required this.eventType,
    required this.minute,
    required this.viralScore,
    required this.rankingScore,
    required this.caption,
    required this.tags,
    this.teamName,
    this.playerName,
    this.scorelineLabel,
    this.videoUrl,
    this.shareChannel = 'whatsapp',
  });

  factory ViralClip.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'viral clip');
    return ViralClip(
      matchId: stringValue(json['match_id']),
      highlightId: stringValue(json['highlight_id']),
      title: stringValue(json['title']),
      eventType: stringValue(json['event_type']),
      minute: intValue(json['minute']),
      viralScore: intValue(json['viral_score']),
      rankingScore: numberValue(json['ranking_score']),
      caption: ViralCaption.fromJson(json['caption']),
      tags: stringListValue(json['tags']),
      teamName: stringOrNullValue(json['team_name']),
      playerName: stringOrNullValue(json['player_name']),
      scorelineLabel: stringOrNullValue(json['scoreline_label']),
      videoUrl: stringOrNullValue(json['video_url']),
      shareChannel: stringValue(json['share_channel'], fallback: 'whatsapp'),
    );
  }

  final String matchId;
  final String highlightId;
  final String title;
  final String eventType;
  final int minute;
  final int viralScore;
  final double rankingScore;
  final ViralCaption caption;
  final List<String> tags;
  final String? teamName;
  final String? playerName;
  final String? scorelineLabel;
  final String? videoUrl;
  final String shareChannel;
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
