import 'dart:async';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';

import 'badge_profile_dto.dart';
import 'club_identity_defaults.dart';
import 'club_identity_dto.dart';
import 'jersey_set_dto.dart';
import 'jersey_variant_dto.dart';

abstract class ClubIdentityRepository {
  const ClubIdentityRepository();

  Future<ClubIdentityDto> fetchIdentity(String clubId);

  Future<ClubIdentityDto> patchIdentity({
    required String clubId,
    required Map<String, dynamic> patch,
  });

  Future<JerseySetDto> fetchJerseys(String clubId);

  Future<JerseySetDto> patchJerseys({
    required String clubId,
    required Map<String, dynamic> patch,
  });

  Future<BadgeProfileDto> fetchBadge(String clubId);
}

class ClubIdentityApiRepository extends ClubIdentityRepository {
  ClubIdentityApiRepository({
    required this.config,
    required this.transport,
    ClubIdentityRepository? fixtures,
  }) : fixtures = fixtures ?? MockClubIdentityRepository();

  final GteRepositoryConfig config;
  final GteTransport transport;
  final ClubIdentityRepository fixtures;

  factory ClubIdentityApiRepository.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
    ClubIdentityRepository? fixtures,
    GteTransport? transport,
  }) {
    final GteRepositoryConfig config =
        GteRepositoryConfig(baseUrl: baseUrl, mode: mode);
    return ClubIdentityApiRepository(
      config: config,
      transport: transport ?? GteHttpTransport(),
      fixtures: fixtures,
    );
  }

  @override
  Future<BadgeProfileDto> fetchBadge(String clubId) {
    return _withFallback<BadgeProfileDto>(
      () async => BadgeProfileDto.fromJson(
        _asMap(await _request('GET', '/api/clubs/$clubId/badge')),
      ),
      () => fixtures.fetchBadge(clubId),
    );
  }

  @override
  Future<ClubIdentityDto> fetchIdentity(String clubId) {
    return _withFallback<ClubIdentityDto>(
      () async => ClubIdentityDto.fromJson(
        _asMap(await _request('GET', '/api/clubs/$clubId/identity')),
      ),
      () => fixtures.fetchIdentity(clubId),
    );
  }

  @override
  Future<JerseySetDto> fetchJerseys(String clubId) {
    return _withFallback<JerseySetDto>(
      () async => JerseySetDto.fromJson(
        _asMap(await _request('GET', '/api/clubs/$clubId/jerseys')),
      ),
      () => fixtures.fetchJerseys(clubId),
    );
  }

  @override
  Future<ClubIdentityDto> patchIdentity({
    required String clubId,
    required Map<String, dynamic> patch,
  }) {
    return _withFallback<ClubIdentityDto>(
      () async => ClubIdentityDto.fromJson(
        _asMap(await _request(
          'PATCH',
          '/api/clubs/$clubId/identity',
          body: patch,
        )),
      ),
      () => fixtures.patchIdentity(clubId: clubId, patch: patch),
    );
  }

  @override
  Future<JerseySetDto> patchJerseys({
    required String clubId,
    required Map<String, dynamic> patch,
  }) {
    return _withFallback<JerseySetDto>(
      () async => JerseySetDto.fromJson(
        _asMap(await _request(
          'PATCH',
          '/api/clubs/$clubId/jerseys',
          body: patch,
        )),
      ),
      () => fixtures.patchJerseys(clubId: clubId, patch: patch),
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
          (error.supportsFixtureFallback ||
              error.type == GteApiErrorType.notFound ||
              error.type == GteApiErrorType.unknown)) {
        return fixtureCall();
      }
      rethrow;
    } on GteParsingException {
      if (config.mode == GteBackendMode.liveThenFixture) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  Future<Object?> _request(
    String method,
    String path, {
    Object? body,
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: method,
          uri: config.uriFor(path),
          headers: const <String, String>{'Accept': 'application/json'},
          body: body,
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
        message: 'Unable to load club identity right now.',
        cause: error,
      );
    }
  }
}

class MockClubIdentityRepository extends ClubIdentityRepository {
  MockClubIdentityRepository({
    Map<String, ClubIdentityDto>? seededProfiles,
    this.latency = const Duration(milliseconds: 180),
  }) : _profiles = <String, ClubIdentityDto>{...?(seededProfiles)};

  final Map<String, ClubIdentityDto> _profiles;
  final Duration latency;

  @override
  Future<ClubIdentityDto> fetchIdentity(String clubId) async {
    await Future<void>.delayed(latency);
    return _profiles.putIfAbsent(
      clubId,
      () => ClubIdentityDefaults.generate(clubId: clubId),
    );
  }

  @override
  Future<ClubIdentityDto> patchIdentity({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    await Future<void>.delayed(latency);
    final ClubIdentityDto current = await fetchIdentity(clubId);
    final ClubIdentityDto updated = ClubIdentityDefaults.buildIdentity(
      clubId: current.clubId,
      clubName: patch['club_name'] as String? ?? current.clubName,
      shortClubCode:
          patch['short_club_code'] as String? ?? current.shortClubCode,
      colorPalette: patch['color_palette'] is Map<String, dynamic>
          ? ColorPaletteProfileDto.fromJson(
              patch['color_palette'] as Map<String, dynamic>)
          : current.colorPalette,
      badgeProfile: patch['badge_profile'] is Map<String, dynamic>
          ? BadgeProfileDto.fromJson(
              patch['badge_profile'] as Map<String, dynamic>)
          : current.badgeProfile,
      jerseySet: current.jerseySet,
    );
    _profiles[clubId] = updated;
    return updated;
  }

  @override
  Future<JerseySetDto> fetchJerseys(String clubId) async {
    await Future<void>.delayed(latency);
    return (await fetchIdentity(clubId)).jerseySet;
  }

  @override
  Future<JerseySetDto> patchJerseys({
    required String clubId,
    required Map<String, dynamic> patch,
  }) async {
    await Future<void>.delayed(latency);
    final ClubIdentityDto current = await fetchIdentity(clubId);
    final JerseySetDto currentSet = current.jerseySet;
    final JerseySetDto updatedSet = JerseySetDto(
      home: patch['home'] is Map<String, dynamic>
          ? _copyVariantFromJson(
              currentSet.home, patch['home'] as Map<String, dynamic>)
          : currentSet.home,
      away: patch['away'] is Map<String, dynamic>
          ? _copyVariantFromJson(
              currentSet.away, patch['away'] as Map<String, dynamic>)
          : currentSet.away,
      third: patch['third'] is Map<String, dynamic>
          ? _copyVariantFromJson(
              currentSet.third, patch['third'] as Map<String, dynamic>)
          : currentSet.third,
      goalkeeper: patch['goalkeeper'] is Map<String, dynamic>
          ? _copyVariantFromJson(currentSet.goalkeeper,
              patch['goalkeeper'] as Map<String, dynamic>)
          : currentSet.goalkeeper,
    );
    _profiles[clubId] = ClubIdentityDefaults.buildIdentity(
      clubId: current.clubId,
      clubName: current.clubName,
      shortClubCode: current.shortClubCode,
      colorPalette: current.colorPalette,
      badgeProfile: current.badgeProfile,
      jerseySet: updatedSet,
    );
    return updatedSet;
  }

  @override
  Future<BadgeProfileDto> fetchBadge(String clubId) async {
    await Future<void>.delayed(latency);
    return (await fetchIdentity(clubId)).badgeProfile;
  }
}

CollarStyle _collarStyleFromWire(String value) {
  switch (value) {
    case 'v_neck':
      return CollarStyle.vNeck;
    case 'crew':
      return CollarStyle.crew;
    case 'polo':
      return CollarStyle.polo;
    case 'wrap':
      return CollarStyle.wrap;
    default:
      return CollarStyle.crew;
  }
}

JerseyVariantDto _copyVariantFromJson(
  JerseyVariantDto value,
  Map<String, dynamic> json,
) {
  return value.copyWith(
    primaryColor: json['primary_color'] as String?,
    secondaryColor: json['secondary_color'] as String?,
    accentColor: json['accent_color'] as String?,
    patternType: json['pattern_type'] == null
        ? null
        : PatternType.values.byName(json['pattern_type'] as String),
    collarStyle: json['collar_style'] == null
        ? null
        : _collarStyleFromWire(json['collar_style'] as String),
    sleeveStyle: json['sleeve_style'] == null
        ? null
        : SleeveStyle.values.byName(json['sleeve_style'] as String),
    badgePlacement: json['badge_placement'] as String?,
    frontText: json['front_text'] as String?,
    shortsColor: json['shorts_color'] as String?,
    socksColor: json['socks_color'] as String?,
    themeTags: (json['theme_tags'] as List<dynamic>?)
        ?.map((dynamic value) => value.toString())
        .toList(growable: false),
    commemorativePatch: json['commemorative_patch'] as String?,
  );
}

Map<String, Object?> _asMap(Object? value) {
  return GteJson.map(value, label: 'club identity payload');
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
  if (payload is String && payload.trim().isNotEmpty) {
    return payload;
  }
  if (payload is Map) {
    final Map<String, Object?> json = GteJson.map(payload);
    final String? detail = GteJson.stringOrNull(
      json,
      const <String>['detail', 'message', 'error'],
    );
    if (detail != null && detail.isNotEmpty) {
      return detail;
    }
  }
  return 'Club request failed.';
}
