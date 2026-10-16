import '../../../../data/gte_models.dart';
import 'dynasty_era_dto.dart';
import 'dynasty_leaderboard_entry_dto.dart';
import 'dynasty_profile_dto.dart';
import 'dynasty_types.dart';

const DynastyResponseMapper dynastyResponseMapper = DynastyResponseMapper();

class DynastyResponseMapper {
  const DynastyResponseMapper();

  DynastyProfileDto mapProfile(
    Object? payload, {
    DynastyHistoryDto? history,
    List<DynastyEraDto> explicitEras = const <DynastyEraDto>[],
  }) {
    final Map<String, Object?> json =
        GteJson.map(payload, label: 'dynasty profile');
    final DynastyProfileDto parsed = DynastyProfileDto.fromJson(json);
    final DynastyHistoryDto resolvedHistory = applyEraOverride(
      history ??
          DynastyHistoryDto(
            clubId: parsed.clubId,
            clubName: parsed.clubName,
            dynastyTimeline: parsed.dynastyTimeline,
            eras: parsed.eras,
            events: parsed.events,
          ),
      explicitEras: explicitEras,
    );
    final List<DynastySeasonSummaryDto> resolvedSeasons =
        _collectSeasons(resolvedHistory);
    final DynastySnapshotDto? currentSnapshot =
        parsed.currentSnapshot ?? resolvedHistory.dynastyTimeline.lastOrNull;
    final List<DynastySeasonSummaryDto> lastFourSeasonSummary =
        parsed.lastFourSeasonSummary.isNotEmpty
            ? _sortSeasons(parsed.lastFourSeasonSummary)
            : _lastFourSeasons(resolvedSeasons);
    final DynastyStreaksDto activeStreaks =
        json.containsKey('progress') || _isEmptyStreaks(parsed.activeStreaks)
            ? (resolvedSeasons.isEmpty
                ? parsed.activeStreaks
                : deriveStreaks(resolvedSeasons))
            : parsed.activeStreaks;
    final List<String> reasons = _dedupeStrings(
      parsed.reasons.isNotEmpty
          ? parsed.reasons
          : currentSnapshot?.reasons ?? const <String>[],
    );

    return DynastyProfileDto(
      clubId: currentSnapshot?.clubId ?? parsed.clubId,
      clubName: currentSnapshot?.clubName ?? parsed.clubName,
      dynastyStatus: currentSnapshot?.dynastyStatus ?? parsed.dynastyStatus,
      currentEraLabel: currentSnapshot?.eraLabel ?? parsed.currentEraLabel,
      activeDynastyFlag:
          currentSnapshot?.activeDynasty ?? parsed.activeDynastyFlag,
      dynastyScore: currentSnapshot?.dynastyScore ?? parsed.dynastyScore,
      activeStreaks: activeStreaks,
      lastFourSeasonSummary: lastFourSeasonSummary,
      reasons: reasons,
      currentSnapshot: currentSnapshot,
      dynastyTimeline: resolvedHistory.dynastyTimeline,
      eras: resolvedHistory.eras,
      events: resolvedHistory.events,
    );
  }

  DynastyHistoryDto mapHistory(Object? payload) {
    final DynastyHistoryDto parsed = DynastyHistoryDto.fromJson(payload);
    return normalizeHistory(parsed);
  }

  List<DynastyEraDto> mapEras(Object? payload) {
    return _extractList(
      payload,
      label: 'dynasty eras',
      collectionKeys: const <String>['eras', 'items'],
    ).map<DynastyEraDto>(DynastyEraDto.fromJson).toList(growable: false);
  }

  List<DynastyLeaderboardEntryDto> mapLeaderboard(Object? payload) {
    final List<DynastyLeaderboardEntryDto> entries = _extractList(
      payload,
      label: 'dynasty leaderboard',
      collectionKeys: const <String>['entries', 'leaderboard', 'items'],
    )
        .map<DynastyLeaderboardEntryDto>(
          DynastyLeaderboardEntryDto.fromJson,
        )
        .toList(growable: true)
      ..sort(_compareLeaderboardEntries);
    return entries;
  }

  DynastyHistoryDto normalizeHistory(DynastyHistoryDto history) {
    final List<DynastySnapshotDto> orderedTimeline =
        List<DynastySnapshotDto>.of(history.dynastyTimeline)
          ..sort((DynastySnapshotDto left, DynastySnapshotDto right) {
            final int byEndSeason = left.metrics.endSeasonIndex
                .compareTo(right.metrics.endSeasonIndex);
            if (byEndSeason != 0) {
              return byEndSeason;
            }
            return left.dynastyScore.compareTo(right.dynastyScore);
          });
    final Map<String, int> seasonIndexById = _seasonIndexById(orderedTimeline);
    final List<DynastyEventDto> orderedEvents = List<DynastyEventDto>.of(
        history.events)
      ..sort((DynastyEventDto left, DynastyEventDto right) {
        final int leftIndex =
            seasonIndexById[left.seasonId] ?? _coerceSeasonKey(left.seasonId);
        final int rightIndex =
            seasonIndexById[right.seasonId] ?? _coerceSeasonKey(right.seasonId);
        if (leftIndex != rightIndex) {
          return leftIndex.compareTo(rightIndex);
        }
        return left.title.compareTo(right.title);
      });
    final List<DynastyEraDto> orderedEras = history.eras.isNotEmpty
        ? _sortEras(history.eras, seasonIndexById)
        : deriveEras(
            history.copyWith(
              dynastyTimeline: orderedTimeline,
              events: orderedEvents,
            ),
          );
    return history.copyWith(
      dynastyTimeline: orderedTimeline,
      eras: orderedEras,
      events: orderedEvents,
    );
  }

  DynastyHistoryDto applyEraOverride(
    DynastyHistoryDto history, {
    List<DynastyEraDto> explicitEras = const <DynastyEraDto>[],
  }) {
    final DynastyHistoryDto normalizedHistory = normalizeHistory(history);
    if (explicitEras.isEmpty) {
      return normalizedHistory;
    }
    return normalizedHistory.copyWith(
      eras: _sortEras(
        explicitEras,
        _seasonIndexById(normalizedHistory.dynastyTimeline),
      ),
    );
  }

  List<DynastyEraDto> deriveEras(DynastyHistoryDto history) {
    final List<DynastySnapshotDto> timeline =
        List<DynastySnapshotDto>.of(history.dynastyTimeline)
          ..sort((DynastySnapshotDto left, DynastySnapshotDto right) {
            return left.metrics.endSeasonIndex
                .compareTo(right.metrics.endSeasonIndex);
          });
    if (timeline.isEmpty) {
      return const <DynastyEraDto>[];
    }

    final List<DynastyEraDto> eras = <DynastyEraDto>[];
    final List<DynastySnapshotDto> activeGroup = <DynastySnapshotDto>[];

    void flushGroup() {
      if (activeGroup.isEmpty) {
        return;
      }
      final DynastySnapshotDto startSnapshot = activeGroup.first;
      final DynastySnapshotDto endSnapshot = activeGroup.last;
      DynastySnapshotDto peakSnapshot = activeGroup.first;
      for (final DynastySnapshotDto candidate in activeGroup.skip(1)) {
        if (candidate.dynastyScore > peakSnapshot.dynastyScore) {
          peakSnapshot = candidate;
        }
      }
      eras.add(
        DynastyEraDto(
          eraLabel: endSnapshot.eraLabel,
          dynastyStatus: endSnapshot.dynastyStatus,
          startSeasonId: _windowSeasonId(startSnapshot.metrics),
          startSeasonLabel: _windowSeasonLabel(startSnapshot.metrics),
          endSeasonId: _windowSeasonId(endSnapshot.metrics),
          endSeasonLabel: _windowSeasonLabel(endSnapshot.metrics),
          peakScore: peakSnapshot.dynastyScore,
          active: identical(endSnapshot, timeline.last),
          reasons: _dedupeStrings(peakSnapshot.reasons),
        ),
      );
      activeGroup.clear();
    }

    for (final DynastySnapshotDto snapshot in timeline) {
      if (snapshot.eraLabel == DynastyEraType.none) {
        flushGroup();
        continue;
      }
      if (activeGroup.isNotEmpty &&
          activeGroup.last.eraLabel == snapshot.eraLabel) {
        activeGroup.add(snapshot);
        continue;
      }
      flushGroup();
      activeGroup.add(snapshot);
    }
    flushGroup();

    return eras;
  }

  DynastyStreaksDto deriveStreaks(Iterable<DynastySeasonSummaryDto> seasons) {
    final List<DynastySeasonSummaryDto> ordered =
        List<DynastySeasonSummaryDto>.of(seasons)
          ..sort((DynastySeasonSummaryDto left, DynastySeasonSummaryDto right) {
            return right.seasonIndex.compareTo(left.seasonIndex);
          });
    return DynastyStreaksDto(
      topFour: _countStreak(
        ordered,
        (DynastySeasonSummaryDto season) => season.topFourFinish,
      ),
      trophySeasons: _countStreak(
        ordered,
        (DynastySeasonSummaryDto season) => season.trophyCount > 0,
      ),
      worldSuperCupQualification: _countStreak(
        ordered,
        (DynastySeasonSummaryDto season) => season.worldSuperCupQualified,
      ),
      positiveReputation: _countStreak(
        ordered,
        (DynastySeasonSummaryDto season) => season.reputationGain > 0,
      ),
    );
  }

  List<Object?> _extractList(
    Object? payload, {
    required String label,
    List<String> collectionKeys = const <String>[],
  }) {
    if (payload is List) {
      return GteJson.list(payload, label: label);
    }
    final Map<String, Object?> json = GteJson.map(payload, label: label);
    for (final String key in collectionKeys) {
      final Object? value = GteJson.value(json, <String>[key]);
      if (value != null) {
        return GteJson.list(value, label: label);
      }
    }
    return GteJson.list(payload, label: label);
  }

  List<DynastySeasonSummaryDto> _collectSeasons(DynastyHistoryDto history) {
    final Map<String, DynastySeasonSummaryDto> seasonsById =
        <String, DynastySeasonSummaryDto>{};
    for (final DynastySnapshotDto snapshot in history.dynastyTimeline) {
      for (final DynastySeasonSummaryDto season in snapshot.metrics.seasons) {
        seasonsById[_seasonKey(season)] = season;
      }
    }
    return _sortSeasons(seasonsById.values);
  }

  Map<String, int> _seasonIndexById(Iterable<DynastySnapshotDto> timeline) {
    final Map<String, int> seasonIndexById = <String, int>{};
    for (final DynastySnapshotDto snapshot in timeline) {
      for (final DynastySeasonSummaryDto season in snapshot.metrics.seasons) {
        seasonIndexById[_seasonKey(season)] = season.seasonIndex;
      }
    }
    return seasonIndexById;
  }

  List<DynastyEraDto> _sortEras(
    Iterable<DynastyEraDto> eras,
    Map<String, int> seasonIndexById,
  ) {
    final List<DynastyEraDto> ordered = List<DynastyEraDto>.of(eras);
    if (seasonIndexById.isEmpty) {
      return ordered;
    }
    ordered.sort((DynastyEraDto left, DynastyEraDto right) {
      final int leftStart = seasonIndexById[left.startSeasonId] ??
          _coerceSeasonKey(left.startSeasonId);
      final int rightStart = seasonIndexById[right.startSeasonId] ??
          _coerceSeasonKey(right.startSeasonId);
      if (leftStart != rightStart) {
        return leftStart.compareTo(rightStart);
      }
      final int leftEnd = seasonIndexById[left.endSeasonId] ??
          _coerceSeasonKey(left.endSeasonId);
      final int rightEnd = seasonIndexById[right.endSeasonId] ??
          _coerceSeasonKey(right.endSeasonId);
      if (leftEnd != rightEnd) {
        return leftEnd.compareTo(rightEnd);
      }
      return left.peakScore.compareTo(right.peakScore);
    });
    return ordered;
  }

  List<DynastySeasonSummaryDto> _sortSeasons(
    Iterable<DynastySeasonSummaryDto> seasons,
  ) {
    return List<DynastySeasonSummaryDto>.of(seasons)
      ..sort((DynastySeasonSummaryDto left, DynastySeasonSummaryDto right) {
        return left.seasonIndex.compareTo(right.seasonIndex);
      });
  }

  List<DynastySeasonSummaryDto> _lastFourSeasons(
    List<DynastySeasonSummaryDto> seasons,
  ) {
    if (seasons.length <= 4) {
      return List<DynastySeasonSummaryDto>.of(seasons);
    }
    return seasons.sublist(seasons.length - 4);
  }

  List<String> _dedupeStrings(Iterable<String> values) {
    final Set<String> seen = <String>{};
    final List<String> ordered = <String>[];
    for (final String value in values) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty || seen.contains(trimmed)) {
        continue;
      }
      seen.add(trimmed);
      ordered.add(trimmed);
    }
    return ordered;
  }

  bool _isEmptyStreaks(DynastyStreaksDto streaks) {
    return streaks.topFour == 0 &&
        streaks.trophySeasons == 0 &&
        streaks.worldSuperCupQualification == 0 &&
        streaks.positiveReputation == 0;
  }

  int _countStreak(
    List<DynastySeasonSummaryDto> seasons,
    bool Function(DynastySeasonSummaryDto season) predicate,
  ) {
    int streak = 0;
    for (final DynastySeasonSummaryDto season in seasons) {
      if (!predicate(season)) {
        break;
      }
      streak += 1;
    }
    return streak;
  }

  int _compareLeaderboardEntries(
    DynastyLeaderboardEntryDto left,
    DynastyLeaderboardEntryDto right,
  ) {
    if (left.activeDynastyFlag != right.activeDynastyFlag) {
      return left.activeDynastyFlag ? -1 : 1;
    }
    final int byScore = right.dynastyScore.compareTo(left.dynastyScore);
    if (byScore != 0) {
      return byScore;
    }
    return left.clubName.compareTo(right.clubName);
  }

  int _coerceSeasonKey(String rawValue) {
    return int.tryParse(rawValue.replaceAll(RegExp(r'[^0-9-]'), '')) ?? 1 << 20;
  }

  String _seasonKey(DynastySeasonSummaryDto season) {
    return season.seasonId.isEmpty ? season.seasonLabel : season.seasonId;
  }

  String _windowSeasonId(DynastyWindowMetricsDto metrics) {
    if (metrics.windowEndSeasonId.isNotEmpty) {
      return metrics.windowEndSeasonId;
    }
    return metrics.seasons.isEmpty ? '' : metrics.seasons.last.seasonId;
  }

  String _windowSeasonLabel(DynastyWindowMetricsDto metrics) {
    if (metrics.windowEndSeasonLabel.isNotEmpty) {
      return metrics.windowEndSeasonLabel;
    }
    return metrics.seasons.isEmpty
        ? 'Unknown season'
        : metrics.seasons.last.seasonLabel;
  }
}

extension _LastOrNull<T> on List<T> {
  T? get lastOrNull => isEmpty ? null : last;
}
