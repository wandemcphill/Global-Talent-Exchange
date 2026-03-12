import 'dart:async';

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
