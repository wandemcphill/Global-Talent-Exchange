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
    return DynastyLeaderboardEntryDto(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, const <String>['club_name', 'clubName']),
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
      reasons: GteJson.typedList<String>(
        json,
        const <String>['reasons'],
        (Object? entry) => entry.toString(),
      ),
    );
  }
}
