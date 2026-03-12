import 'dynasty_era_dto.dart';
import 'dynasty_leaderboard_entry_dto.dart';
import 'dynasty_profile_dto.dart';

abstract class DynastyRepository {
  Future<DynastyProfileDto> fetchDynastyProfile(String clubId);

  Future<DynastyHistoryDto> fetchDynastyHistory(String clubId);

  Future<List<DynastyEraDto>> fetchEras(String clubId);

  Future<List<DynastyLeaderboardEntryDto>> fetchDynastyLeaderboard({
    int limit = 25,
  });
}
