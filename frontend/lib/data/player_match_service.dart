import 'dart:async';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/match/match_dto.dart';
import 'package:gte_frontend/data/match/match_mapper.dart';
import 'package:gte_frontend/domain/match/match_result.dart';
import 'package:gte_frontend/domain/match/match_weights.dart';

class GteScoutMatchFilters {
  const GteScoutMatchFilters({
    this.position,
    this.minAge,
    this.maxAge,
    this.country,
    this.preferredFoot,
    this.minHeightMeters,
  });

  const GteScoutMatchFilters.defaultBrief()
      : position = 'ST',
        minAge = 18,
        maxAge = 27,
        country = 'Nigeria',
        preferredFoot = 'Right',
        minHeightMeters = 1.75;

  final String? position;
  final int? minAge;
  final int? maxAge;
  final String? country;
  final String? preferredFoot;
  final double? minHeightMeters;

  factory GteScoutMatchFilters.fromJson(Map<String, dynamic> json) {
    return GteScoutMatchFilters(
      position: _cleanString(json['position']),
      minAge: _toInt(json['min_age'] ?? json['minAge']),
      maxAge: _toInt(json['max_age'] ?? json['maxAge']),
      country: _cleanString(json['country']),
      preferredFoot:
          _cleanString(json['preferred_foot'] ?? json['preferredFoot']),
      minHeightMeters: _toDouble(json['min_height'] ?? json['minHeight']),
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      if (position != null) 'position': position,
      if (minAge != null) 'min_age': minAge,
      if (maxAge != null) 'max_age': maxAge,
      if (country != null) 'country': country,
      if (preferredFoot != null) 'preferred_foot': preferredFoot,
      if (minHeightMeters != null) 'min_height': minHeightMeters,
    };
  }

  Map<String, Object?> toBriefJson() {
    return <String, Object?>{
      if (position != null) 'positions': <String>[position!],
      if (minAge != null || maxAge != null)
        'age': <String, Object?>{
          if (minAge != null) 'min': minAge,
          if (maxAge != null) 'max': maxAge,
        },
      if (country != null) 'countries': <String>[country!],
      if (preferredFoot != null) 'preferred_foot': <String>[preferredFoot!],
      if (minHeightMeters != null)
        'height_cm': <String, Object?>{
          'min': (minHeightMeters! * 100).round(),
        },
    };
  }

  Map<String, Object?> toBackendFilters() {
    return <String, Object?>{
      if (position != null) 'position': position,
      if (minAge != null) 'min_age': minAge,
      if (maxAge != null) 'max_age': maxAge,
      if (country != null) 'country': country,
      if (preferredFoot != null) 'preferred_foot': preferredFoot,
      if (minHeightMeters != null)
        'min_height': (minHeightMeters! * 100).round(),
    };
  }

  List<String> summaryLabels() {
    return <String>[
      if (position != null) position!,
      if (minAge != null || maxAge != null) _ageLabel(),
      if (country != null) country!,
      if (preferredFoot != null) '$preferredFoot foot',
      if (minHeightMeters != null) '${minHeightMeters!.toStringAsFixed(2)}m+',
    ];
  }

  String get cacheKey => <Object?>[
        position?.trim().toUpperCase(),
        minAge,
        maxAge,
        country?.trim().toLowerCase(),
        preferredFoot?.trim().toLowerCase(),
        minHeightMeters?.toStringAsFixed(2),
      ].join('|');

  String _ageLabel() {
    if (minAge != null && maxAge != null) {
      return '$minAge-$maxAge';
    }
    if (minAge != null) {
      return '$minAge+';
    }
    return 'Under $maxAge';
  }
}

class PlayerMatchViewModel {
  const PlayerMatchViewModel({
    required this.player,
    required this.score,
    required this.reasons,
    this.preferredFoot,
    this.heightMeters,
    this.isFreeAgent = false,
  });

  final GteMarketPlayerListItem player;
  final double score;
  final List<String> reasons;
  final String? preferredFoot;
  final double? heightMeters;
  final bool isFreeAgent;

  factory PlayerMatchViewModel.fromDomain(MatchResult match) {
    return PlayerMatchViewModel(
      player: GteMarketPlayerListItem(
        playerId: match.player.id,
        playerName: match.player.name,
        position: match.player.position,
        nationality: match.player.country,
        currentClubName: match.player.club,
        age: match.player.age,
        currentValueCredits: null,
        movementPct: null,
        trendScore: null,
        marketInterestScore: null,
        averageRating: null,
        isAvailable: true,
        availabilityLabel:
            match.flags.isFreeAgent ? 'Free agent' : 'Open market profile',
        askingType: 'match',
        agentUserId: '',
        agentName: match.player.club ?? 'Scout board',
      ),
      score: match.score.clamp(0, 1).toDouble(),
      reasons: match.reasons,
      preferredFoot: match.preferredFoot,
      heightMeters: match.heightMeters,
      isFreeAgent: match.flags.isFreeAgent,
    );
  }
}

class GtePlayerMatchResponse {
  const GtePlayerMatchResponse({
    required this.matches,
  });

  final List<GtePlayerMatchResult> matches;

  factory GtePlayerMatchResponse.fromJson(Map<String, dynamic> json) {
    final Object? rawMatches = json['matches'];
    final List<Object?> list =
        rawMatches is List ? rawMatches : const <Object?>[];
    return GtePlayerMatchResponse(
      matches: list
          .map((Object? entry) => GtePlayerMatchResult.fromJson(entry))
          .toList(growable: false),
    );
  }
}

class GtePlayerMatchResult {
  const GtePlayerMatchResult({
    required this.player,
    required this.score,
    required this.reasons,
    this.preferredFoot,
    this.heightMeters,
    this.isFreeAgent = false,
  });

  final GteMarketPlayerListItem player;
  final double score;
  final List<String> reasons;
  final String? preferredFoot;
  final double? heightMeters;
  final bool isFreeAgent;

  factory GtePlayerMatchResult.fromJson(Object? value) {
    final Map<Object?, Object?> json =
        value is Map<Object?, Object?> ? value : const <Object?, Object?>{};
    final Map<Object?, Object?> player = json['player'] is Map<Object?, Object?>
        ? json['player'] as Map<Object?, Object?>
        : const <Object?, Object?>{};
    return GtePlayerMatchResult(
      player: GteMarketPlayerListItem.fromJson(player),
      score: _toDouble(json['score']) ?? 0,
      reasons: _extractReasonLabels(json['reasons']),
      preferredFoot: _cleanString(
        json['preferred_foot'] ??
            json['preferredFoot'] ??
            player['dominant_foot'] ??
            player['preferred_foot'],
      ),
      heightMeters: _toHeightMeters(
        json['height_meters'] ?? json['heightMeters'] ?? player['height_cm'],
      ),
      isFreeAgent: json['is_free_agent'] == true ||
          json['isFreeAgent'] == true ||
          player['is_free_agent'] == true,
    );
  }

  factory GtePlayerMatchResult.fromViewModel(PlayerMatchViewModel viewModel) {
    return GtePlayerMatchResult(
      player: viewModel.player,
      score: viewModel.score,
      reasons: viewModel.reasons,
      preferredFoot: viewModel.preferredFoot,
      heightMeters: viewModel.heightMeters,
      isFreeAgent: viewModel.isFreeAgent,
    );
  }
}

class GtePlayerMatchService {
  GtePlayerMatchService({
    GteExchangeApiClient? api,
    this.latency = const Duration(milliseconds: 500),
  }) : _api = api;

  final GteExchangeApiClient? _api;
  final Duration latency;

  Future<GtePlayerMatchResponse> fetchMatches({
    required Iterable<GteMarketPlayerListItem> players,
    required GteScoutMatchFilters filters,
    MatchWeights? weights,
    int limit = 20,
  }) async {
    final List<GteMarketPlayerListItem> candidates =
        players.toList(growable: false);
    final MatchWeights resolvedWeights =
        (weights ?? MatchWeights.defaultWeights()).normalize();
    if (candidates.isEmpty) {
      return const GtePlayerMatchResponse(matches: <GtePlayerMatchResult>[]);
    }

    try {
      final List<MatchResult> backendMatches = await _getBackendMatches(
        filters: filters,
        weights: resolvedWeights,
        limit: limit,
      );
      return GtePlayerMatchResponse(
        matches: backendMatches
            .map(PlayerMatchViewModel.fromDomain)
            .map(GtePlayerMatchResult.fromViewModel)
            .toList(growable: false),
      );
    } catch (_) {
      return _scoreMatchesLocally(
        players: candidates,
        filters: filters,
        weights: resolvedWeights,
        limit: limit,
      );
    }
  }

  Future<List<GtePlayerMatchResult>> getMatches({
    required Iterable<GteMarketPlayerListItem> players,
    required GteScoutMatchFilters filters,
    MatchWeights? weights,
    int limit = 20,
  }) async {
    final GtePlayerMatchResponse response = await fetchMatches(
      players: players,
      filters: filters,
      weights: weights,
      limit: limit,
    );
    return response.matches;
  }

  Future<List<MatchResult>> _getBackendMatches({
    required GteScoutMatchFilters filters,
    required MatchWeights weights,
    required int limit,
  }) async {
    final _BackendMatchClient backend = await _buildBackendClient();
    final Object? payload = await _postMatchRequest(
      backend: backend,
      filters: filters,
      weights: weights,
      limit: limit,
    );
    if (payload is! Map) {
      throw const GteApiException(
        type: GteApiErrorType.parsing,
        message: 'Unexpected player match response shape.',
      );
    }
    final MatchResponseDto dto =
        MatchResponseDto.fromJson(Map<String, dynamic>.from(payload));
    return dto.matches.map(MatchMapper.toDomain).toList(growable: false);
  }

  Future<_BackendMatchClient> _buildBackendClient() async {
    final GteExchangeApiClient? api = _api;
    if (api == null) {
      throw StateError(
          'Backend player matching is unavailable without an API.');
    }
    String? accessToken;
    final GteApiRepository repository = api.repository;
    if (repository is GteReliableApiRepository) {
      accessToken = await repository.tokenStore.readToken();
    }
    return _BackendMatchClient(
      client: GteAuthedApi(
        config: api.config,
        transport: api.transport,
        accessToken: accessToken,
        mode: api.config.mode,
      ),
      auth: accessToken != null && accessToken.isNotEmpty,
    );
  }

  Future<Object?> _postMatchRequest({
    required _BackendMatchClient backend,
    required GteScoutMatchFilters filters,
    required MatchWeights weights,
    required int limit,
  }) async {
    try {
      return await backend.client.post(
        '/players/match',
        body: <String, Object?>{
          'brief': filters.toBriefJson(),
          'weights': weights.toJson(),
          'pagination': <String, Object?>{
            'limit': limit,
          },
        },
        auth: backend.auth,
      );
    } on GteApiException catch (error) {
      if (error.type != GteApiErrorType.validation) {
        rethrow;
      }
    }
    return backend.client.post(
      '/players/match',
      body: <String, Object?>{
        'filters': filters.toBackendFilters(),
        'weights': weights.toJson(),
        'limit': limit,
      },
      auth: backend.auth,
    );
  }

  Future<GtePlayerMatchResponse> _scoreMatchesLocally({
    required List<GteMarketPlayerListItem> players,
    required GteScoutMatchFilters filters,
    required MatchWeights weights,
    required int limit,
  }) async {
    await Future<void>.delayed(latency);
    final List<_ScoutCandidate> enriched = await Future.wait<_ScoutCandidate>(
      players
          .map((playerItem) => _enrichCandidate(playerItem, filters))
          .toList(growable: false),
    );

    final List<GtePlayerMatchResult> matches = enriched
        .map((candidate) => _scoreCandidate(candidate, filters, weights))
        .where((GtePlayerMatchResult result) => result.score > 0)
        .toList(growable: false)
      ..sort((GtePlayerMatchResult left, GtePlayerMatchResult right) {
        final int scoreCompare = right.score.compareTo(left.score);
        if (scoreCompare != 0) {
          return scoreCompare;
        }
        final int interestCompare = (right.player.marketInterestScore ?? 0)
            .compareTo(left.player.marketInterestScore ?? 0);
        if (interestCompare != 0) {
          return interestCompare;
        }
        final double rightTrend = right.player.trendScore ?? 0;
        final double leftTrend = left.player.trendScore ?? 0;
        final int trendCompare = rightTrend.compareTo(leftTrend);
        if (trendCompare != 0) {
          return trendCompare;
        }
        return left.player.playerName
            .toLowerCase()
            .compareTo(right.player.playerName.toLowerCase());
      });

    return GtePlayerMatchResponse(
      matches: matches.take(limit).toList(growable: false),
    );
  }

  Future<_ScoutCandidate> _enrichCandidate(
    GteMarketPlayerListItem player,
    GteScoutMatchFilters filters,
  ) async {
    String? preferredFoot = _defaultPreferredFoot(player.position);
    double? heightMeters = _defaultHeightMeters(player.position);
    if (_api != null &&
        (filters.preferredFoot != null || filters.minHeightMeters != null)) {
      try {
        final GteMarketPlayerDetailView detail =
            await _api.fetchPlayerDetail(player.playerId);
        preferredFoot =
            _cleanString(detail.identity.preferredFoot) ?? preferredFoot;
        final int? heightCm = detail.identity.heightCm;
        if (heightCm != null && heightCm > 0) {
          heightMeters = heightCm / 100;
        }
      } catch (_) {
        // Keep local scoring resilient while the dedicated backend route is rolling out.
      }
    }

    final String normalizedClub =
        (player.currentClubName ?? '').trim().toLowerCase();
    final bool isFreeAgent =
        normalizedClub.isEmpty || normalizedClub == 'free agent';
    return _ScoutCandidate(
      player: player,
      preferredFoot: preferredFoot,
      heightMeters: heightMeters,
      isFreeAgent: isFreeAgent,
    );
  }

  GtePlayerMatchResult _scoreCandidate(
    _ScoutCandidate candidate,
    GteScoutMatchFilters filters,
    MatchWeights weights,
  ) {
    double score = 0;
    final List<String> reasons = <String>[];

    if (_matchesPosition(candidate.player.position, filters.position)) {
      score += weights.position;
      reasons.add('Perfect position match');
    }

    final double ageFit = _ageFit(candidate.player.age, filters);
    if (ageFit > 0) {
      score += weights.age * ageFit;
      reasons.add(
        ageFit >= 1 ? 'Age within range' : 'Age is close to target band',
      );
    }

    if (_matchesText(candidate.player.nationality, filters.country)) {
      score += weights.country;
      reasons.add('Same country');
    }

    if (filters.minHeightMeters != null &&
        candidate.heightMeters != null &&
        candidate.heightMeters! >= filters.minHeightMeters!) {
      score += weights.height;
      reasons.add('Height meets physical target');
    }

    if (_matchesText(candidate.preferredFoot, filters.preferredFoot)) {
      score += weights.foot;
      reasons.add('Preferred foot matches');
    }

    if (candidate.isFreeAgent) {
      score += weights.availability;
      reasons.add('Free-agent bonus');
    }

    return GtePlayerMatchResult(
      player: candidate.player,
      score: score.clamp(0, 1).toDouble(),
      reasons: reasons,
      preferredFoot: candidate.preferredFoot,
      heightMeters: candidate.heightMeters,
      isFreeAgent: candidate.isFreeAgent,
    );
  }

  bool _matchesPosition(String? playerPosition, String? filterPosition) {
    if (filterPosition == null || filterPosition.trim().isEmpty) {
      return false;
    }
    return _positionAliases(playerPosition)
        .intersection(
          _positionAliases(filterPosition),
        )
        .isNotEmpty;
  }

  Set<String> _positionAliases(String? value) {
    final String normalized = (value ?? '').trim().toUpperCase();
    if (normalized.isEmpty) {
      return const <String>{};
    }
    const Map<String, Set<String>> aliases = <String, Set<String>>{
      'GK': <String>{'GK', 'GOALKEEPER'},
      'CB': <String>{'CB', 'CENTER BACK', 'CENTRE BACK'},
      'LB': <String>{'LB', 'LEFT BACK'},
      'RB': <String>{'RB', 'RIGHT BACK'},
      'DM': <String>{'DM', 'CDM', 'DEFENSIVE MIDFIELDER'},
      'CM': <String>{'CM', 'CENTRAL MIDFIELDER'},
      'AM': <String>{'AM', 'CAM', 'ATTACKING MIDFIELDER'},
      'LW': <String>{'LW', 'LEFT WING', 'WINGER'},
      'RW': <String>{'RW', 'RIGHT WING', 'WINGER'},
      'ST': <String>{'ST', 'CF', 'STRIKER', 'CENTRE FORWARD', 'CENTER FORWARD'},
    };
    for (final MapEntry<String, Set<String>> entry in aliases.entries) {
      if (entry.value.contains(normalized)) {
        return entry.value;
      }
    }
    return <String>{normalized};
  }

  double _ageFit(int age, GteScoutMatchFilters filters) {
    final int? minAge = filters.minAge;
    final int? maxAge = filters.maxAge;
    if (minAge == null && maxAge == null) {
      return 0;
    }
    if ((minAge == null || age >= minAge) &&
        (maxAge == null || age <= maxAge)) {
      return 1;
    }
    final int distance;
    if (minAge != null && age < minAge) {
      distance = minAge - age;
    } else if (maxAge != null && age > maxAge) {
      distance = age - maxAge;
    } else {
      distance = 0;
    }
    if (distance <= 2) {
      return 0.5;
    }
    return 0;
  }

  bool _matchesText(String? left, String? right) {
    if (left == null || right == null) {
      return false;
    }
    return left.trim().toLowerCase() == right.trim().toLowerCase();
  }

  String? _defaultPreferredFoot(String? position) {
    final String normalized = (position ?? '').trim().toUpperCase();
    switch (normalized) {
      case 'LB':
      case 'LWB':
      case 'LW':
      case 'RW':
        return 'Left';
      default:
        return 'Right';
    }
  }

  double _defaultHeightMeters(String? position) {
    final String normalized = (position ?? '').trim().toUpperCase();
    switch (normalized) {
      case 'GK':
        return 1.9;
      case 'CB':
        return 1.87;
      case 'LB':
      case 'RB':
      case 'LWB':
      case 'RWB':
        return 1.78;
      case 'DM':
      case 'CM':
        return 1.81;
      case 'AM':
      case 'LW':
      case 'RW':
        return 1.77;
      case 'ST':
      case 'CF':
        return 1.83;
      default:
        return 1.8;
    }
  }
}

class _BackendMatchClient {
  const _BackendMatchClient({
    required this.client,
    required this.auth,
  });

  final GteAuthedApi client;
  final bool auth;
}

class _ScoutCandidate {
  const _ScoutCandidate({
    required this.player,
    required this.preferredFoot,
    required this.heightMeters,
    required this.isFreeAgent,
  });

  final GteMarketPlayerListItem player;
  final String? preferredFoot;
  final double? heightMeters;
  final bool isFreeAgent;
}

List<String> _extractReasonLabels(Object? value) {
  if (value is! List) {
    return const <String>[];
  }
  return value
      .map((Object? entry) {
        if (entry is String) {
          return entry.trim();
        }
        if (entry is Map<Object?, Object?>) {
          final Object? label = entry['label'] ?? entry['reason'];
          return label?.toString().trim() ?? '';
        }
        return '';
      })
      .where((String reason) => reason.isNotEmpty)
      .toList(growable: false);
}

String? _cleanString(Object? value) {
  if (value == null) {
    return null;
  }
  final String text = value.toString().trim();
  return text.isEmpty ? null : text;
}

int? _toInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value.trim());
  }
  return null;
}

double? _toDouble(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value.trim());
  }
  return null;
}

double? _toHeightMeters(Object? value) {
  final double? height = _toDouble(value);
  if (height == null || height <= 0) {
    return null;
  }
  return height > 10 ? height / 100 : height;
}
