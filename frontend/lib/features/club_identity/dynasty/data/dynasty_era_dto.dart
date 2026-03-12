import '../../../../data/gte_models.dart';
import 'dynasty_types.dart';

class DynastyEraDto {
  const DynastyEraDto({
    required this.eraLabel,
    required this.dynastyStatus,
    required this.startSeasonId,
    required this.startSeasonLabel,
    required this.endSeasonId,
    required this.endSeasonLabel,
    required this.peakScore,
    required this.active,
    required this.reasons,
  });

  final DynastyEraType eraLabel;
  final DynastyStatus dynastyStatus;
  final String startSeasonId;
  final String startSeasonLabel;
  final String endSeasonId;
  final String endSeasonLabel;
  final int peakScore;
  final bool active;
  final List<String> reasons;

  String get seasonSpanLabel => '$startSeasonLabel - $endSeasonLabel';

  factory DynastyEraDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'dynasty era');
    return DynastyEraDto(
      eraLabel: dynastyEraTypeFromRaw(
        GteJson.value(json, const <String>['era_label', 'eraLabel']),
      ),
      dynastyStatus: dynastyStatusFromRaw(
        GteJson.value(json, const <String>['dynasty_status', 'dynastyStatus']),
      ),
      startSeasonId: GteJson.string(
        json,
        const <String>['start_season_id', 'startSeasonId'],
      ),
      startSeasonLabel: GteJson.string(
        json,
        const <String>['start_season_label', 'startSeasonLabel'],
      ),
      endSeasonId: GteJson.string(
        json,
        const <String>['end_season_id', 'endSeasonId'],
      ),
      endSeasonLabel: GteJson.string(
        json,
        const <String>['end_season_label', 'endSeasonLabel'],
      ),
      peakScore: GteJson.integer(
        json,
        const <String>['peak_score', 'peakScore'],
      ),
      active: GteJson.boolean(
        json,
        const <String>['active'],
      ),
      reasons: GteJson.typedList<String>(
        json,
        const <String>['reasons'],
        (Object? entry) => entry.toString(),
      ),
    );
  }
}

class DynastyEraDetail {
  const DynastyEraDetail({
    required this.era,
    required this.startSeasonIndex,
    required this.endSeasonIndex,
    required this.trophiesWon,
    required this.reputationGrowth,
    required this.definingAchievements,
  });

  final DynastyEraDto era;
  final int startSeasonIndex;
  final int endSeasonIndex;
  final int trophiesWon;
  final int reputationGrowth;
  final List<String> definingAchievements;
}
