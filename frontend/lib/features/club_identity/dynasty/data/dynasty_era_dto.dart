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
    final String startSeasonId =
        GteJson.stringOrNull(json, const <String>['start_season_id', 'startSeasonId']) ??
            '';
    final String endSeasonId =
        GteJson.stringOrNull(json, const <String>['end_season_id', 'endSeasonId']) ??
            startSeasonId;
    final String startSeasonLabel =
        GteJson.stringOrNull(json, const <String>['start_season_label', 'startSeasonLabel']) ??
            (startSeasonId.isEmpty ? 'Unknown season' : startSeasonId);
    final String endSeasonLabel =
        GteJson.stringOrNull(json, const <String>['end_season_label', 'endSeasonLabel']) ??
            (endSeasonId.isEmpty ? startSeasonLabel : endSeasonId);
    final List<String> reasons = GteJson.typedList<String>(
      json,
      const <String>['reasons'],
      (Object? entry) => entry == null ? '' : entry.toString().trim(),
    ).where((String value) => value.isNotEmpty).toList(growable: false);
    return DynastyEraDto(
      eraLabel: dynastyEraTypeFromRaw(
        GteJson.value(json, const <String>['era_label', 'eraLabel']),
      ),
      dynastyStatus: dynastyStatusFromRaw(
        GteJson.value(json, const <String>['dynasty_status', 'dynastyStatus']),
      ),
      startSeasonId: startSeasonId,
      startSeasonLabel: startSeasonLabel,
      endSeasonId: endSeasonId,
      endSeasonLabel: endSeasonLabel,
      peakScore: GteJson.integer(
        json,
        const <String>['peak_score', 'peakScore'],
      ),
      active: GteJson.boolean(
        json,
        const <String>['active'],
      ),
      reasons: reasons,
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
