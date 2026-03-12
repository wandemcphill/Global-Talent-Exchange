import 'dart:async';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'reputation_models.dart';

abstract class ReputationRepository {
  Future<ReputationProfileDto> fetchOverview(String clubId);

  Future<ReputationHistoryDto> fetchHistory(String clubId);

  Future<PrestigeLeaderboardDto> fetchLeaderboard({
    required PrestigeLeaderboardScope scope,
    required String currentClubId,
  });
}

class ReputationApiRepository implements ReputationRepository {
  ReputationApiRepository({
    required this.config,
    required this.transport,
    required this.fixtures,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final ReputationRepository fixtures;

  factory ReputationApiRepository.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return ReputationApiRepository(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
      transport: GteHttpTransport(),
      fixtures: FixtureReputationRepository(),
    );
  }

  @override
  Future<ReputationProfileDto> fetchOverview(String clubId) {
    return _withFallback<ReputationProfileDto>(
      () async => _mapOverview(
        _asMap(await _request('GET', '/api/clubs/$clubId/reputation')),
      ),
      () => fixtures.fetchOverview(clubId),
    );
  }

  @override
  Future<ReputationHistoryDto> fetchHistory(String clubId) {
    return _withFallback<ReputationHistoryDto>(
      () async => _mapHistory(
        _asMap(await _request('GET', '/api/clubs/$clubId/reputation/history')),
      ),
      () => fixtures.fetchHistory(clubId),
    );
  }

  @override
  Future<PrestigeLeaderboardDto> fetchLeaderboard({
    required PrestigeLeaderboardScope scope,
    required String currentClubId,
  }) {
    return _withFallback<PrestigeLeaderboardDto>(
      () async {
        final Map<String, Object?> payload =
            _asMap(await _request('GET', '/api/leaderboards/prestige'));
        final List<PrestigeLeaderboardEntryDto> entries =
            _mapLeaderboardEntries(
          _asList(payload['leaderboard']),
        );
        final List<PrestigeLeaderboardEntryDto> scopedEntries =
            _applyScope(entries, scope: scope, currentClubId: currentClubId);
        return PrestigeLeaderboardDto(
          scope: scope,
          entries: scopedEntries,
          note: scope == PrestigeLeaderboardScope.global
              ? null
              : 'Regional and following filters are temporarily backed by fixture scope rules until the backend exposes those fields.',
        );
      },
      () =>
          fixtures.fetchLeaderboard(scope: scope, currentClubId: currentClubId),
    );
  }

  Future<T> _withFallback<T>(
    Future<T> Function() liveCall,
    Future<T> Function() fixtureCall,
  ) async {
    if (config.mode == GteBackendMode.fixture) {
      return fixtureCall();
    }
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (config.mode == GteBackendMode.liveThenFixture &&
          error.supportsFixtureFallback) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: method,
          uri: config.uriFor(path, query),
          headers: const <String, String>{'Accept': 'application/json'},
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorType(response.statusCode),
          message: _errorMessage(response.body),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return response.body;
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to load club reputation right now.',
        cause: error,
      );
    }
  }

  ReputationProfileDto _mapOverview(Map<String, Object?> json) {
    final List<Object?> milestonePayload = _asList(json['biggest_milestones']);
    final String clubId = _asString(json['club_id'], fallback: 'unknown-club');
    return ReputationProfileDto(
      clubId: clubId,
      clubName: prettifyClubId(clubId),
      regionLabel: 'Global',
      currentScore: _asInt(json['current_score']),
      highestScore: _asInt(json['highest_score']),
      currentPrestigeTier: prestigeTierFromRaw(
          _asString(json['current_prestige_tier'], fallback: 'Local')),
      lastActiveSeason: _asNullableInt(json['last_active_season']),
      badgesEarned: _asStringList(json['badges_earned']),
      biggestMilestones: milestonePayload
          .map((Object? value) => _mapMilestone(_asMap(value)))
          .toList(growable: false),
    );
  }

  ReputationHistoryDto _mapHistory(Map<String, Object?> json) {
    final String clubId = _asString(json['club_id'], fallback: 'unknown-club');
    final List<ReputationEventDto> events = _asList(json['history'])
        .map((Object? value) => _mapHistoryEvent(_asMap(value), clubId))
        .toList(growable: false)
      ..sort((ReputationEventDto left, ReputationEventDto right) {
        if (left.season != right.season) {
          return right.season.compareTo(left.season);
        }
        return right.occurredAt.compareTo(left.occurredAt);
      });
    return ReputationHistoryDto(
      clubId: clubId,
      currentScore: _asInt(json['current_score']),
      currentPrestigeTier: prestigeTierFromRaw(
          _asString(json['current_prestige_tier'], fallback: 'Local')),
      events: events,
    );
  }

  ReputationMilestoneDto _mapMilestone(Map<String, Object?> json) {
    return ReputationMilestoneDto(
      title: _asString(json['title'], fallback: 'Reputation milestone'),
      badgeCode: _asNullableString(json['badge_code']),
      season: _asNullableInt(json['season']),
      delta: _asInt(json['delta']),
      occurredAt: _asDateTime(json['occurred_at']),
    );
  }

  ReputationEventDto _mapHistoryEvent(
      Map<String, Object?> json, String clubId) {
    final int season = _asInt(json['season']);
    final List<String> milestones = _asStringList(json['milestones']);
    final List<String> badges = _asStringList(json['badges']);
    final ReputationEventCategory category =
        _inferCategory(milestones: milestones, badges: badges);
    final int delta = _asInt(json['season_delta']);
    final String title = milestones.isNotEmpty
        ? milestones.first
        : 'Season $season reputation update';
    final String description = _buildHistoryDescription(
      scoreAfter: _asInt(json['score_after']),
      prestigeTier: _asString(json['prestige_tier'], fallback: 'Local'),
      badges: badges,
      milestones: milestones,
    );
    return ReputationEventDto(
      id: '$clubId-$season',
      season: season,
      title: title,
      description: description,
      delta: delta,
      category: category,
      occurredAt: _asDateTime(json['rolled_up_at']),
      badges: badges,
      milestones: milestones,
    );
  }

  List<PrestigeLeaderboardEntryDto> _mapLeaderboardEntries(
      List<Object?> payload) {
    final List<PrestigeLeaderboardEntryDto> entries =
        <PrestigeLeaderboardEntryDto>[];
    for (int index = 0; index < payload.length; index += 1) {
      final Map<String, Object?> item = _asMap(payload[index]);
      final String clubId = _asString(item['club_id'], fallback: 'club-$index');
      entries.add(
        PrestigeLeaderboardEntryDto(
          clubId: clubId,
          clubName: prettifyClubId(clubId),
          regionLabel: 'Global',
          currentScore: _asInt(item['current_score']),
          currentPrestigeTier: prestigeTierFromRaw(
              _asString(item['current_prestige_tier'], fallback: 'Local')),
          highestScore: _asInt(item['highest_score']),
          totalSeasons: _asInt(item['total_seasons']),
          rank: index + 1,
        ),
      );
    }
    return entries;
  }
}

class FixtureReputationRepository implements ReputationRepository {
  FixtureReputationRepository({
    this.latency = const Duration(milliseconds: 220),
  });

  final Duration latency;

  static final Map<String, ReputationProfileDto> _profiles =
      <String, ReputationProfileDto>{
    'royal-lagos-fc': ReputationProfileDto(
      clubId: 'royal-lagos-fc',
      clubName: 'Royal Lagos FC',
      regionLabel: 'West Africa',
      currentScore: 1184,
      highestScore: 1184,
      currentPrestigeTier: PrestigeTier.legendary,
      lastActiveSeason: 12,
      badgesEarned: const <String>[
        'continental_champion',
        'back_to_back_champion',
        'golden_attack',
        'invincibles',
      ],
      biggestMilestones: <ReputationMilestoneDto>[
        ReputationMilestoneDto(
          title: 'Continental Champion',
          badgeCode: 'continental_champion',
          season: 11,
          delta: 180,
          occurredAt: DateTime.utc(2026, 5, 30),
        ),
        ReputationMilestoneDto(
          title: 'Back-to-Back Champion',
          badgeCode: 'back_to_back_champion',
          season: 12,
          delta: 30,
          occurredAt: DateTime.utc(2026, 6, 14),
        ),
        ReputationMilestoneDto(
          title: 'Invincibles',
          badgeCode: 'invincibles',
          season: 10,
          delta: 40,
          occurredAt: DateTime.utc(2025, 5, 28),
        ),
      ],
    ),
  };

  static final Map<String, ReputationHistoryDto> _historyByClub =
      <String, ReputationHistoryDto>{
    'royal-lagos-fc': ReputationHistoryDto(
      clubId: 'royal-lagos-fc',
      currentScore: 1184,
      currentPrestigeTier: PrestigeTier.legendary,
      events: <ReputationEventDto>[
        ReputationEventDto(
          id: 'royal-lagos-fc-12',
          season: 12,
          title: 'Back-to-Back Champion',
          description:
              'League title retained, Golden Attack secured, and the club stayed in the continental picture.',
          delta: 132,
          category: ReputationEventCategory.league,
          occurredAt: DateTime.utc(2026, 6, 14),
          badges: const <String>['back_to_back_champion', 'golden_attack'],
          milestones: const <String>['Back-to-Back Champion'],
        ),
        ReputationEventDto(
          id: 'royal-lagos-fc-11',
          season: 11,
          title: 'Continental Champion',
          description:
              'Champions League run ended with silverware and a surge in global respect.',
          delta: 244,
          category: ReputationEventCategory.continental,
          occurredAt: DateTime.utc(2026, 5, 30),
          badges: const <String>['continental_champion'],
          milestones: const <String>['Continental Champion'],
        ),
        ReputationEventDto(
          id: 'royal-lagos-fc-10',
          season: 10,
          title: 'Invincibles',
          description: 'Unbeaten league campaign with a ruthless front line.',
          delta: 186,
          category: ReputationEventCategory.awards,
          occurredAt: DateTime.utc(2025, 5, 28),
          badges: const <String>['invincibles', 'golden_attack'],
          milestones: const <String>['Invincibles'],
        ),
        ReputationEventDto(
          id: 'royal-lagos-fc-9',
          season: 9,
          title: 'World stage qualification',
          description:
              'League finish was strong enough to open the World Super Cup door.',
          delta: 88,
          category: ReputationEventCategory.worldSuperCup,
          occurredAt: DateTime.utc(2024, 6, 2),
        ),
        ReputationEventDto(
          id: 'royal-lagos-fc-8',
          season: 8,
          title: 'Reset season',
          description:
              'A quieter year slowed momentum without erasing the club identity already built.',
          delta: -18,
          category: ReputationEventCategory.general,
          occurredAt: DateTime.utc(2023, 5, 22),
        ),
      ],
    ),
  };

  static final List<PrestigeLeaderboardEntryDto> _leaderboard =
      <PrestigeLeaderboardEntryDto>[
    PrestigeLeaderboardEntryDto(
      clubId: 'monte-carlo-athletic',
      clubName: 'Monte Carlo Athletic',
      regionLabel: 'Europe',
      currentScore: 1462,
      currentPrestigeTier: PrestigeTier.legendary,
      highestScore: 1490,
      totalSeasons: 14,
      rank: 1,
      isFollowing: true,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'royal-lagos-fc',
      clubName: 'Royal Lagos FC',
      regionLabel: 'West Africa',
      currentScore: 1184,
      currentPrestigeTier: PrestigeTier.legendary,
      highestScore: 1184,
      totalSeasons: 12,
      rank: 2,
      isFollowing: true,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'porto-imperial',
      clubName: 'Porto Imperial',
      regionLabel: 'Europe',
      currentScore: 1112,
      currentPrestigeTier: PrestigeTier.legendary,
      highestScore: 1140,
      totalSeasons: 11,
      rank: 3,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'rio-crown-united',
      clubName: 'Rio Crown United',
      regionLabel: 'South America',
      currentScore: 1028,
      currentPrestigeTier: PrestigeTier.elite,
      highestScore: 1090,
      totalSeasons: 10,
      rank: 4,
      isFollowing: true,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'ankara-sun',
      clubName: 'Ankara Sun',
      regionLabel: 'Europe',
      currentScore: 948,
      currentPrestigeTier: PrestigeTier.elite,
      highestScore: 980,
      totalSeasons: 9,
      rank: 5,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'casablanca-royals',
      clubName: 'Casablanca Royals',
      regionLabel: 'North Africa',
      currentScore: 904,
      currentPrestigeTier: PrestigeTier.elite,
      highestScore: 918,
      totalSeasons: 9,
      rank: 6,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'lagos-harbour-sc',
      clubName: 'Lagos Harbour SC',
      regionLabel: 'West Africa',
      currentScore: 782,
      currentPrestigeTier: PrestigeTier.elite,
      highestScore: 816,
      totalSeasons: 8,
      rank: 7,
      isFollowing: true,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'doha-summit',
      clubName: 'Doha Summit',
      regionLabel: 'Middle East',
      currentScore: 721,
      currentPrestigeTier: PrestigeTier.elite,
      highestScore: 760,
      totalSeasons: 8,
      rank: 8,
    ),
    PrestigeLeaderboardEntryDto(
      clubId: 'accra-constellation',
      clubName: 'Accra Constellation',
      regionLabel: 'West Africa',
      currentScore: 664,
      currentPrestigeTier: PrestigeTier.elite,
      highestScore: 664,
      totalSeasons: 6,
      rank: 9,
    ),
  ];

  @override
  Future<ReputationProfileDto> fetchOverview(String clubId) async {
    await Future<void>.delayed(latency);
    return _profiles[clubId] ?? _fallbackProfile(clubId);
  }

  @override
  Future<ReputationHistoryDto> fetchHistory(String clubId) async {
    await Future<void>.delayed(latency);
    return _historyByClub[clubId] ??
        ReputationHistoryDto(
          clubId: clubId,
          currentScore: 0,
          currentPrestigeTier: PrestigeTier.local,
          events: const <ReputationEventDto>[],
        );
  }

  @override
  Future<PrestigeLeaderboardDto> fetchLeaderboard({
    required PrestigeLeaderboardScope scope,
    required String currentClubId,
  }) async {
    await Future<void>.delayed(latency);
    final List<PrestigeLeaderboardEntryDto> filtered =
        _applyScope(_leaderboard, scope: scope, currentClubId: currentClubId);
    return PrestigeLeaderboardDto(
      scope: scope,
      entries: filtered,
      note: scope == PrestigeLeaderboardScope.following
          ? 'Following is mocked from your watch circle until social graph data is available.'
          : null,
    );
  }

  ReputationProfileDto _fallbackProfile(String clubId) {
    return ReputationProfileDto(
      clubId: clubId,
      clubName: prettifyClubId(clubId),
      regionLabel: 'Global',
      currentScore: 0,
      highestScore: 0,
      currentPrestigeTier: PrestigeTier.local,
      badgesEarned: const <String>[],
      biggestMilestones: const <ReputationMilestoneDto>[],
    );
  }
}

List<PrestigeLeaderboardEntryDto> _applyScope(
  List<PrestigeLeaderboardEntryDto> entries, {
  required PrestigeLeaderboardScope scope,
  required String currentClubId,
}) {
  switch (scope) {
    case PrestigeLeaderboardScope.global:
      return List<PrestigeLeaderboardEntryDto>.from(entries, growable: false);
    case PrestigeLeaderboardScope.region:
      String currentRegion = 'Global';
      for (final PrestigeLeaderboardEntryDto entry in entries) {
        if (entry.clubId == currentClubId) {
          currentRegion = entry.regionLabel;
          break;
        }
      }
      final List<PrestigeLeaderboardEntryDto> regionalEntries = entries
          .where((PrestigeLeaderboardEntryDto entry) =>
              entry.regionLabel == currentRegion)
          .toList(growable: false);
      return regionalEntries.isEmpty
          ? List<PrestigeLeaderboardEntryDto>.from(entries)
          : regionalEntries;
    case PrestigeLeaderboardScope.following:
      final List<PrestigeLeaderboardEntryDto> followingEntries = entries
          .where((PrestigeLeaderboardEntryDto entry) =>
              entry.isFollowing || entry.clubId == currentClubId)
          .toList(growable: false);
      return followingEntries.isEmpty
          ? List<PrestigeLeaderboardEntryDto>.from(entries)
          : followingEntries;
  }
}

ReputationEventCategory _inferCategory({
  required List<String> milestones,
  required List<String> badges,
}) {
  final String milestoneText = milestones.join(' ').toLowerCase();
  final String badgeText = badges.join(' ').toLowerCase();
  final String combined = '$milestoneText $badgeText';
  if (combined.contains('world super cup')) {
    return ReputationEventCategory.worldSuperCup;
  }
  if (combined.contains('continental')) {
    return ReputationEventCategory.continental;
  }
  if (combined.contains('golden') ||
      combined.contains('assist') ||
      combined.contains('scorer') ||
      combined.contains('award')) {
    return ReputationEventCategory.awards;
  }
  if (combined.contains('league') ||
      combined.contains('invincibles') ||
      combined.contains('champion')) {
    return ReputationEventCategory.league;
  }
  return ReputationEventCategory.general;
}

String _buildHistoryDescription({
  required int scoreAfter,
  required String prestigeTier,
  required List<String> badges,
  required List<String> milestones,
}) {
  final List<String> fragments = <String>[
    'Closed the season on $scoreAfter reputation in $prestigeTier tier.',
  ];
  if (milestones.isNotEmpty) {
    fragments.add(milestones.join(' • '));
  }
  if (badges.isNotEmpty) {
    fragments.add(
      badges.map(prettifyBadgeCode).join(' • '),
    );
  }
  return fragments.join(' ');
}

Map<String, Object?> _asMap(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map((Object? key, Object? nestedValue) =>
        MapEntry<String, Object?>(key.toString(), nestedValue));
  }
  return <String, Object?>{};
}

List<Object?> _asList(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return List<Object?>.from(value);
  }
  return const <Object?>[];
}

String _asString(Object? value, {required String fallback}) {
  if (value is String && value.trim().isNotEmpty) {
    return value;
  }
  return fallback;
}

String? _asNullableString(Object? value) {
  if (value is String && value.trim().isNotEmpty) {
    return value;
  }
  return null;
}

int _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  if (value is String) {
    return int.tryParse(value) ?? 0;
  }
  return 0;
}

int? _asNullableInt(Object? value) {
  if (value == null) {
    return null;
  }
  return _asInt(value);
}

DateTime _asDateTime(Object? value) {
  if (value is DateTime) {
    return value;
  }
  if (value is String) {
    return DateTime.tryParse(value)?.toUtc() ??
        DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
  }
  return DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
}

List<String> _asStringList(Object? value) {
  return _asList(value)
      .map((Object? item) => item?.toString() ?? '')
      .where((String item) => item.trim().isNotEmpty)
      .toList(growable: false);
}

GteApiErrorType _errorType(int statusCode) {
  if (statusCode == 404) {
    return GteApiErrorType.notFound;
  }
  if (statusCode == 422) {
    return GteApiErrorType.validation;
  }
  if (statusCode >= 500) {
    return GteApiErrorType.unavailable;
  }
  return GteApiErrorType.unknown;
}

String _errorMessage(Object? payload) {
  if (payload is Map) {
    final Map<String, Object?> map = _asMap(payload);
    final String? detail =
        _asNullableString(map['detail']) ?? _asNullableString(map['message']);
    if (detail != null) {
      return detail;
    }
  }
  if (payload is String && payload.trim().isNotEmpty) {
    return payload;
  }
  return 'Unable to load reputation data.';
}
