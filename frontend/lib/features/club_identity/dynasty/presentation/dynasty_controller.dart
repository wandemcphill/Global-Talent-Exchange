import 'package:flutter/foundation.dart';

import '../../../../data/gte_api_repository.dart';
import '../data/dynasty_api_repository.dart';
import '../data/dynasty_era_dto.dart';
import '../data/dynasty_leaderboard_entry_dto.dart';
import '../data/dynasty_profile_dto.dart';
import '../data/dynasty_response_mapper.dart';
import '../data/dynasty_repository.dart';
import '../data/dynasty_types.dart';

class DynastyController extends ChangeNotifier {
  DynastyController({
    required DynastyRepository repository,
  }) : _repository = repository;

  factory DynastyController.standard({
    required String baseUrl,
    GteBackendMode backendMode = GteBackendMode.liveThenFixture,
  }) {
    return DynastyController(
      repository: DynastyApiRepository.standard(
        baseUrl: baseUrl,
        mode: backendMode,
      ),
    );
  }

  final DynastyRepository _repository;
  final GteRequestGate _overviewGate = GteRequestGate();
  final GteRequestGate _historyGate = GteRequestGate();
  final GteRequestGate _leaderboardGate = GteRequestGate();

  String? currentClubId;

  bool isLoadingOverview = false;
  bool isLoadingHistory = false;
  bool isLoadingLeaderboard = false;

  String? overviewError;
  String? historyError;
  String? leaderboardError;

  DynastyProfileDto? profile;
  DynastyHistoryDto? history;
  List<DynastyEraDto> fallbackEras = const <DynastyEraDto>[];
  List<DynastyLeaderboardEntryDto> leaderboard =
      const <DynastyLeaderboardEntryDto>[];
  DynastyLeaderboardFilter leaderboardFilter =
      DynastyLeaderboardFilter.activeDynasties;

  List<DynastyLeaderboardEntryDto> get filteredLeaderboard {
    return leaderboard
        .where(
          (DynastyLeaderboardEntryDto entry) =>
              entry.matchesFilter(leaderboardFilter),
        )
        .toList(growable: false);
  }

  List<DynastySnapshotDto> get chronologicalTimeline {
    final List<DynastySnapshotDto> timeline = List<DynastySnapshotDto>.of(
      history?.dynastyTimeline ??
          profile?.dynastyTimeline ??
          const <DynastySnapshotDto>[],
    );
    timeline.sort((DynastySnapshotDto left, DynastySnapshotDto right) {
      return left.metrics.endSeasonIndex
          .compareTo(right.metrics.endSeasonIndex);
    });
    return timeline;
  }

  List<DynastyEraDetail> get eraDetails {
    final List<DynastyEraDto> eras = _effectiveEras();
    if (eras.isEmpty) {
      return const <DynastyEraDetail>[];
    }

    final Map<String, DynastySeasonSummaryDto> seasonsById =
        <String, DynastySeasonSummaryDto>{};
    for (final DynastySnapshotDto snapshot in chronologicalTimeline) {
      for (final DynastySeasonSummaryDto season in snapshot.metrics.seasons) {
        seasonsById[season.seasonId] = season;
      }
    }
    for (final DynastySeasonSummaryDto season
        in profile?.lastFourSeasonSummary ??
            const <DynastySeasonSummaryDto>[]) {
      seasonsById[season.seasonId] = season;
    }

    final List<DynastySeasonSummaryDto> orderedSeasons =
        seasonsById.values.toList(growable: true)
          ..sort(
            (DynastySeasonSummaryDto left, DynastySeasonSummaryDto right) =>
                left.seasonIndex.compareTo(right.seasonIndex),
          );
    final Map<String, int> seasonIndexById = <String, int>{
      for (final DynastySeasonSummaryDto season in orderedSeasons)
        season.seasonId: season.seasonIndex,
    };
    final List<DynastyEventDto> events =
        history?.events ?? profile?.events ?? const <DynastyEventDto>[];

    final List<DynastyEraDetail> details = eras.map((DynastyEraDto era) {
      final int startIndex = seasonIndexById[era.startSeasonId] ??
          orderedSeasons.firstOrNull?.seasonIndex ??
          0;
      final int endIndex = seasonIndexById[era.endSeasonId] ??
          orderedSeasons.lastOrNull?.seasonIndex ??
          startIndex;
      final List<DynastySeasonSummaryDto> eraSeasons = orderedSeasons
          .where(
            (DynastySeasonSummaryDto season) =>
                season.seasonIndex >= startIndex &&
                season.seasonIndex <= endIndex,
          )
          .toList(growable: false);
      final int trophiesWon = eraSeasons.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) => sum + season.trophyCount,
      );
      final int reputationGrowth = eraSeasons.fold<int>(
        0,
        (int sum, DynastySeasonSummaryDto season) =>
            sum + season.reputationGain,
      );
      final List<String> achievements = <String>[
        ...era.reasons,
        ...events.where((DynastyEventDto event) {
          final int? eventIndex = seasonIndexById[event.seasonId];
          return eventIndex != null &&
              eventIndex >= startIndex &&
              eventIndex <= endIndex;
        }).map((DynastyEventDto event) => event.title),
      ];
      return DynastyEraDetail(
        era: era,
        startSeasonIndex: startIndex,
        endSeasonIndex: endIndex,
        trophiesWon: trophiesWon,
        reputationGrowth: reputationGrowth,
        definingAchievements: achievements.toSet().toList(growable: false),
      );
    }).toList(growable: true)
      ..sort(
        (DynastyEraDetail left, DynastyEraDetail right) =>
            left.startSeasonIndex.compareTo(right.startSeasonIndex),
      );

    return details;
  }

  Future<void> loadOverview(String clubId) async {
    final int requestId = _overviewGate.begin();
    currentClubId = clubId;
    overviewError = null;
    isLoadingOverview = true;
    notifyListeners();

    try {
      final DynastyProfileDto response =
          await _repository.fetchDynastyProfile(clubId);
      if (!_overviewGate.isActive(requestId)) {
        return;
      }
      profile = response;
    } catch (error) {
      if (_overviewGate.isActive(requestId)) {
        overviewError = error.toString();
      }
    } finally {
      if (_overviewGate.isActive(requestId)) {
        isLoadingOverview = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadHistory(String clubId) async {
    final int requestId = _historyGate.begin();
    currentClubId = clubId;
    historyError = null;
    isLoadingHistory = true;
    notifyListeners();

    try {
      final DynastyHistoryDto historyResponse =
          await _repository.fetchDynastyHistory(clubId);
      DynastyHistoryDto resolvedHistory =
          dynastyResponseMapper.applyEraOverride(historyResponse);
      try {
        final List<DynastyEraDto> explicitEras =
            await _repository.fetchEras(clubId);
        resolvedHistory = dynastyResponseMapper.applyEraOverride(
          historyResponse,
          explicitEras: explicitEras,
        );
      } catch (_) {
        // Keep history-derived eras if the dedicated eras endpoint is unavailable.
      }
      if (!_historyGate.isActive(requestId)) {
        return;
      }
      history = resolvedHistory;
      fallbackEras = resolvedHistory.eras;
    } catch (error) {
      if (_historyGate.isActive(requestId)) {
        historyError = error.toString();
      }
    } finally {
      if (_historyGate.isActive(requestId)) {
        isLoadingHistory = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadLeaderboard({int limit = 24}) async {
    final int requestId = _leaderboardGate.begin();
    leaderboardError = null;
    isLoadingLeaderboard = true;
    notifyListeners();

    try {
      final List<DynastyLeaderboardEntryDto> response =
          await _repository.fetchDynastyLeaderboard(limit: limit);
      if (!_leaderboardGate.isActive(requestId)) {
        return;
      }
      leaderboard = response;
    } catch (error) {
      if (_leaderboardGate.isActive(requestId)) {
        leaderboardError = error.toString();
      }
    } finally {
      if (_leaderboardGate.isActive(requestId)) {
        isLoadingLeaderboard = false;
        notifyListeners();
      }
    }
  }

  void setLeaderboardFilter(DynastyLeaderboardFilter filter) {
    if (leaderboardFilter == filter) {
      return;
    }
    leaderboardFilter = filter;
    notifyListeners();
  }

  List<DynastyEraDto> _effectiveEras() {
    if (history != null && history!.eras.isNotEmpty) {
      return history!.eras;
    }
    if (fallbackEras.isNotEmpty) {
      return fallbackEras;
    }
    return profile?.eras ?? const <DynastyEraDto>[];
  }
}

extension _ListFirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;

  T? get lastOrNull => isEmpty ? null : last;
}
