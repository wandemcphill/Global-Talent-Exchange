class MatchResponseDto {
  MatchResponseDto({required this.matches, required this.meta, this.summary});

  final List<MatchItemDto> matches;
  final MatchMetaDto meta;
  final MatchSummaryDto? summary;

  factory MatchResponseDto.fromJson(Map<String, dynamic> json) {
    final List<MatchItemDto> matches = _asList(
      json['matches'],
    ).map(MatchItemDto.fromJson).toList(growable: false);
    final Map<String, dynamic> metaJson =
        _asMapOrNull(json['meta']) ??
        <String, dynamic>{'total': matches.length};
    final Map<String, dynamic>? summaryJson = _asMapOrNull(json['summary']);
    return MatchResponseDto(
      matches: matches,
      meta: MatchMetaDto.fromJson(metaJson),
      summary:
          summaryJson == null ? null : MatchSummaryDto.fromJson(summaryJson),
    );
  }
}

class MatchItemDto {
  MatchItemDto({
    required this.playerId,
    required this.score,
    required this.scoreBreakdown,
    required this.reasons,
    required this.player,
    this.flags,
  });

  final String playerId;
  final double score;
  final Map<String, dynamic> scoreBreakdown;
  final List<ReasonDto> reasons;
  final Map<String, dynamic>? flags;
  final Map<String, dynamic> player;

  factory MatchItemDto.fromJson(Object? value) {
    final Map<String, dynamic> json = _asMap(value);
    final Map<String, dynamic> player =
        _asMapOrNull(json['player']) ?? const <String, dynamic>{};
    return MatchItemDto(
      playerId:
          _asString(json['player_id']) ??
          _asString(player['player_id']) ??
          _asString(player['id']) ??
          '',
      score: _asDouble(json['score']) ?? 0,
      scoreBreakdown:
          _asMapOrNull(json['score_breakdown']) ??
          _asMapOrNull(json['breakdown']) ??
          const <String, dynamic>{},
      reasons: _asList(
        json['reasons'],
      ).map(ReasonDto.fromJson).toList(growable: false),
      flags: _asMapOrNull(json['flags']),
      player: player,
    );
  }
}

class ReasonDto {
  ReasonDto({required this.type, required this.label, required this.impact});

  final String type;
  final String label;
  final String impact;

  factory ReasonDto.fromJson(Object? value) {
    if (value is String) {
      final String label = value.trim();
      return ReasonDto(type: 'label', label: label, impact: 'neutral');
    }
    final Map<String, dynamic> json = _asMap(value);
    final String label =
        _asString(json['label']) ??
        _asString(json['reason']) ??
        _asString(json['message']) ??
        '';
    return ReasonDto(
      type: _asString(json['type']) ?? 'label',
      label: label,
      impact: _asString(json['impact']) ?? 'neutral',
    );
  }
}

class MatchMetaDto {
  MatchMetaDto({required this.total, required this.raw});

  final int total;
  final Map<String, dynamic> raw;

  factory MatchMetaDto.fromJson(Map<String, dynamic> json) {
    return MatchMetaDto(
      total:
          _asInt(json['total']) ??
          _asInt(json['count']) ??
          _asInt(json['matched']) ??
          0,
      raw: Map<String, dynamic>.from(json),
    );
  }
}

class MatchSummaryDto {
  MatchSummaryDto({required this.raw});

  final Map<String, dynamic> raw;

  factory MatchSummaryDto.fromJson(Map<String, dynamic> json) {
    return MatchSummaryDto(raw: Map<String, dynamic>.from(json));
  }
}

Map<String, dynamic> _asMap(Object? value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? entry) => MapEntry(key.toString(), entry),
    );
  }
  return <String, dynamic>{};
}

Map<String, dynamic>? _asMapOrNull(Object? value) {
  final Map<String, dynamic> json = _asMap(value);
  return json.isEmpty ? null : json;
}

List<Object?> _asList(Object? value) {
  if (value is List) {
    return value.cast<Object?>();
  }
  return const <Object?>[];
}

String? _asString(Object? value) {
  if (value == null) {
    return null;
  }
  final String text = value.toString().trim();
  return text.isEmpty ? null : text;
}

int? _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value.trim());
  }
  return null;
}

double? _asDouble(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value.trim());
  }
  return null;
}
