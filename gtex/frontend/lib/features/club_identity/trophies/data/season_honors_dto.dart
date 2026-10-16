import 'trophy_item_dto.dart';

class SeasonHonorsRecordDto {
  const SeasonHonorsRecordDto({
    required this.snapshotId,
    required this.clubId,
    required this.clubName,
    required this.seasonLabel,
    required this.teamScope,
    required this.honors,
    required this.totalHonorsCount,
    required this.majorHonorsCount,
    required this.eliteHonorsCount,
    required this.recordedAt,
  });

  final String snapshotId;
  final String clubId;
  final String clubName;
  final String seasonLabel;
  final TrophyTeamScope teamScope;
  final List<TrophyItemDto> honors;
  final int totalHonorsCount;
  final int majorHonorsCount;
  final int eliteHonorsCount;
  final DateTime recordedAt;

  factory SeasonHonorsRecordDto.fromJson(Map<String, dynamic> json) {
    return SeasonHonorsRecordDto(
      snapshotId: json['snapshot_id'] as String,
      clubId: json['club_id'] as String,
      clubName: json['club_name'] as String,
      seasonLabel: json['season_label'] as String,
      teamScope: parseTrophyTeamScope(json['team_scope'] as String),
      honors: (json['honors'] as List<dynamic>)
          .map((dynamic item) =>
              TrophyItemDto.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      totalHonorsCount: json['total_honors_count'] as int,
      majorHonorsCount: json['major_honors_count'] as int,
      eliteHonorsCount: json['elite_honors_count'] as int,
      recordedAt: DateTime.parse(json['recorded_at'] as String),
    );
  }
}

class SeasonHonorsArchiveDto {
  const SeasonHonorsArchiveDto({
    required this.clubId,
    required this.clubName,
    required this.seasonRecords,
  });

  final String clubId;
  final String clubName;
  final List<SeasonHonorsRecordDto> seasonRecords;

  bool get isEmpty => seasonRecords.isEmpty;

  factory SeasonHonorsArchiveDto.fromJson(Map<String, dynamic> json) {
    return SeasonHonorsArchiveDto(
      clubId: json['club_id'] as String,
      clubName: json['club_name'] as String,
      seasonRecords: (json['season_records'] as List<dynamic>)
          .map((dynamic item) =>
              SeasonHonorsRecordDto.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}
