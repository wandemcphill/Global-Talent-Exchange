enum TrophyTeamScope {
  senior,
  academy,
}

enum TrophyScopeFilter {
  all,
  senior,
  academy,
}

extension TrophyTeamScopeX on TrophyTeamScope {
  String get wireValue => name;

  String get label => this == TrophyTeamScope.senior ? 'Senior' : 'Academy';
}

extension TrophyScopeFilterX on TrophyScopeFilter {
  String? get queryValue {
    switch (this) {
      case TrophyScopeFilter.all:
        return null;
      case TrophyScopeFilter.senior:
        return TrophyTeamScope.senior.wireValue;
      case TrophyScopeFilter.academy:
        return TrophyTeamScope.academy.wireValue;
    }
  }

  String get label {
    switch (this) {
      case TrophyScopeFilter.all:
        return 'All';
      case TrophyScopeFilter.senior:
        return 'Senior';
      case TrophyScopeFilter.academy:
        return 'Academy';
    }
  }
}

TrophyTeamScope parseTrophyTeamScope(String raw) {
  return raw == TrophyTeamScope.academy.wireValue
      ? TrophyTeamScope.academy
      : TrophyTeamScope.senior;
}

class TrophyItemDto {
  const TrophyItemDto({
    required this.trophyWinId,
    required this.clubId,
    required this.clubName,
    required this.trophyType,
    required this.trophyName,
    required this.seasonLabel,
    required this.competitionRegion,
    required this.competitionTier,
    required this.finalResultSummary,
    required this.earnedAt,
    required this.captainName,
    required this.topPerformerName,
    required this.teamScope,
    required this.isMajorHonor,
    required this.isEliteHonor,
  });

  final String trophyWinId;
  final String clubId;
  final String clubName;
  final String trophyType;
  final String trophyName;
  final String seasonLabel;
  final String competitionRegion;
  final String competitionTier;
  final String finalResultSummary;
  final DateTime earnedAt;
  final String? captainName;
  final String? topPerformerName;
  final TrophyTeamScope teamScope;
  final bool isMajorHonor;
  final bool isEliteHonor;

  bool get isAcademy => teamScope == TrophyTeamScope.academy;

  String get prestigeLabel {
    if (isEliteHonor) {
      return 'Elite';
    }
    if (isMajorHonor) {
      return 'Major';
    }
    return 'Honor';
  }

  factory TrophyItemDto.fromJson(Map<String, dynamic> json) {
    return TrophyItemDto(
      trophyWinId: json['trophy_win_id'] as String,
      clubId: json['club_id'] as String,
      clubName: json['club_name'] as String,
      trophyType: json['trophy_type'] as String,
      trophyName: json['trophy_name'] as String,
      seasonLabel: json['season_label'] as String,
      competitionRegion: json['competition_region'] as String,
      competitionTier: json['competition_tier'] as String,
      finalResultSummary: json['final_result_summary'] as String,
      earnedAt: DateTime.parse(json['earned_at'] as String),
      captainName: json['captain_name'] as String?,
      topPerformerName: json['top_performer_name'] as String?,
      teamScope: parseTrophyTeamScope(json['team_scope'] as String),
      isMajorHonor: json['is_major_honor'] as bool? ?? false,
      isEliteHonor: json['is_elite_honor'] as bool? ?? false,
    );
  }
}
