import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

import '../data/reputation_models.dart';
import '../data/reputation_repository.dart';

class ReputationController extends ChangeNotifier {
  ReputationController({
    required ReputationRepository repository,
    required this.clubId,
    this.clubName,
  }) : _repository = repository;

  static const int leaderboardVisibleLimit = 12;

  final ReputationRepository _repository;
  final GteRequestGate _loadGate = GteRequestGate();
  final String clubId;
  final String? clubName;

  bool isLoading = false;
  String? errorMessage;

  ReputationProfileDto? overview;
  ReputationHistoryDto? history;
  PrestigeLeaderboardDto? _globalLeaderboard;
  PrestigeLeaderboardDto? _regionalLeaderboard;
  PrestigeLeaderboardDto? _followingLeaderboard;

  ReputationHistoryFilter historyFilter = ReputationHistoryFilter.all;
  PrestigeLeaderboardScope leaderboardScope = PrestigeLeaderboardScope.global;

  bool get hasData =>
      overview != null || history != null || activeLeaderboard != null;

  String get displayClubName =>
      clubName ?? overview?.clubName ?? prettifyClubId(clubId);

  PrestigeLeaderboardDto? get activeLeaderboard {
    switch (leaderboardScope) {
      case PrestigeLeaderboardScope.global:
        return _globalLeaderboard;
      case PrestigeLeaderboardScope.region:
        return _regionalLeaderboard;
      case PrestigeLeaderboardScope.following:
        return _followingLeaderboard;
    }
  }

  List<ReputationEventDto> get recentEvents =>
      (history?.events ?? const <ReputationEventDto>[])
          .take(4)
          .toList(growable: false);

  List<ReputationEventDto> get filteredEvents {
    final List<ReputationEventDto> source =
        history?.events ?? const <ReputationEventDto>[];
    switch (historyFilter) {
      case ReputationHistoryFilter.all:
        return source;
      case ReputationHistoryFilter.league:
        return source
            .where((ReputationEventDto event) =>
                event.category == ReputationEventCategory.league)
            .toList(growable: false);
      case ReputationHistoryFilter.continental:
        return source
            .where((ReputationEventDto event) =>
                event.category == ReputationEventCategory.continental)
            .toList(growable: false);
      case ReputationHistoryFilter.worldSuperCup:
        return source
            .where((ReputationEventDto event) =>
                event.category == ReputationEventCategory.worldSuperCup)
            .toList(growable: false);
      case ReputationHistoryFilter.awards:
        return source
            .where((ReputationEventDto event) =>
                event.category == ReputationEventCategory.awards)
            .toList(growable: false);
    }
  }

  List<PrestigeLeaderboardEntryDto> get miniLeaderboardPreview =>
      (_globalLeaderboard?.entries ?? const <PrestigeLeaderboardEntryDto>[])
          .take(5)
          .toList(growable: false);

  PrestigeLeaderboardEntryDto? get globalRankEntry =>
      _findEntry(_globalLeaderboard);
  PrestigeLeaderboardEntryDto? get regionalRankEntry =>
      _findEntry(_regionalLeaderboard);

  PrestigeLeaderboardEntryDto? get pinnedLeaderboardEntry {
    final PrestigeLeaderboardDto? leaderboard = activeLeaderboard;
    if (leaderboard == null) {
      return null;
    }
    final PrestigeLeaderboardEntryDto? clubEntry = _findEntry(leaderboard);
    if (clubEntry == null) {
      return null;
    }
    final List<PrestigeLeaderboardEntryDto> visible =
        leaderboard.entries.take(leaderboardVisibleLimit).toList(growable: false);
    final bool alreadyVisible = visible
        .any((PrestigeLeaderboardEntryDto entry) => entry.clubId == clubId);
    return alreadyVisible ? null : clubEntry;
  }

  Future<void> load() async {
    final int requestId = _loadGate.begin();
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
        _repository.fetchOverview(clubId),
        _repository.fetchHistory(clubId),
        _repository.fetchLeaderboard(
          scope: PrestigeLeaderboardScope.global,
          currentClubId: clubId,
        ),
        _repository.fetchLeaderboard(
          scope: PrestigeLeaderboardScope.region,
          currentClubId: clubId,
        ),
      ]);
      if (!_loadGate.isActive(requestId)) {
        return;
      }
      overview = payload[0] as ReputationProfileDto;
      history = payload[1] as ReputationHistoryDto;
      _globalLeaderboard = payload[2] as PrestigeLeaderboardDto;
      _regionalLeaderboard = payload[3] as PrestigeLeaderboardDto;
      errorMessage = null;
    } catch (error) {
      if (_loadGate.isActive(requestId)) {
        errorMessage = error.toString();
      }
    } finally {
      if (_loadGate.isActive(requestId)) {
        isLoading = false;
        notifyListeners();
      }
    }
  }

  Future<void> refresh() => load();

  Future<void> setLeaderboardScope(PrestigeLeaderboardScope scope) async {
    leaderboardScope = scope;
    notifyListeners();
    if (scope == PrestigeLeaderboardScope.global &&
        _globalLeaderboard != null) {
      return;
    }
    if (scope == PrestigeLeaderboardScope.region &&
        _regionalLeaderboard != null) {
      return;
    }
    if (scope == PrestigeLeaderboardScope.following &&
        _followingLeaderboard != null) {
      return;
    }
    try {
      final PrestigeLeaderboardDto leaderboard =
          await _repository.fetchLeaderboard(
        scope: scope,
        currentClubId: clubId,
      );
      switch (scope) {
        case PrestigeLeaderboardScope.global:
          _globalLeaderboard = leaderboard;
          break;
        case PrestigeLeaderboardScope.region:
          _regionalLeaderboard = leaderboard;
          break;
        case PrestigeLeaderboardScope.following:
          _followingLeaderboard = leaderboard;
          break;
      }
      errorMessage = null;
    } catch (error) {
      errorMessage = error.toString();
    }
    notifyListeners();
  }

  void setHistoryFilter(ReputationHistoryFilter filter) {
    if (historyFilter == filter) {
      return;
    }
    historyFilter = filter;
    notifyListeners();
  }

  PrestigeLeaderboardEntryDto? _findEntry(PrestigeLeaderboardDto? leaderboard) {
    if (leaderboard == null) {
      return null;
    }
    for (final PrestigeLeaderboardEntryDto entry in leaderboard.entries) {
      if (entry.clubId == clubId) {
        return entry;
      }
    }
    return null;
  }
}
