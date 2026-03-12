import '../../../../data/gte_models.dart';
import 'dynasty_types.dart';

class DynastyLeaderboardEntryDto {
  const DynastyLeaderboardEntryDto({
    required this.clubId,
    required this.clubName,
    required this.dynastyStatus,
    required this.currentEraLabel,
    required this.activeDynastyFlag,
    required this.dynastyScore,
    required this.reasons,
  });

  final String clubId;
  final String clubName;
  final DynastyStatus dynastyStatus;
  final DynastyEraType currentEraLabel;
  final bool activeDynastyFlag;
  final int dynastyScore;
  final List<String> reasons;

  bool get isRisingPower =>
      currentEraLabel == DynastyEraType.emergingPower ||
      (!activeDynastyFlag &&
          dynastyStatus == DynastyStatus.none &&
          dynastyScore >= 40);

  bool matchesFilter(DynastyLeaderboardFilter filter) {
    switch (filter) {
      case DynastyLeaderboardFilter.activeDynasties:
        return activeDynastyFlag;
      case DynastyLeaderboardFilter.allTimeDynasties:
        return true;
      case DynastyLeaderboardFilter.risingPowers:
        return isRisingPower;
    }
  }

  factory DynastyLeaderboardEntryDto.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dynasty leaderboard entry');
    final String clubId = GteJson.stringOrNull(
          json,
          const <String>['club_id', 'clubId'],
        ) ??
        'unknown-club';
    final String clubName = GteJson.stringOrNull(
          json,
          const <String>['club_name', 'clubName'],
        ) ??
        clubId;
    final List<String> reasons = GteJson.typedList<String>(
      json,
      const <String>['reasons'],
      (Object? entry) => entry == null ? '' : entry.toString().trim(),
    ).where((String value) => value.isNotEmpty).toList(growable: false);
    return DynastyLeaderboardEntryDto(
      clubId: clubId,
      clubName: clubName,
      dynastyStatus: dynastyStatusFromRaw(
        GteJson.value(json, const <String>['dynasty_status', 'dynastyStatus']),
      ),
      currentEraLabel: dynastyEraTypeFromRaw(
        GteJson.value(
          json,
          const <String>['current_era_label', 'currentEraLabel', 'era_label'],
        ),
      ),
      activeDynastyFlag: GteJson.boolean(
        json,
        const <String>['active_dynasty_flag', 'activeDynastyFlag'],
      ),
      dynastyScore: GteJson.integer(
        json,
        const <String>['dynasty_score', 'dynastyScore'],
      ),
      reasons: reasons,
    );
  }
}
