import 'badge_profile_dto.dart';
import 'jersey_set_dto.dart';

class ColorPaletteProfileDto {
  const ColorPaletteProfileDto({
    required this.paletteName,
    required this.primaryColor,
    required this.secondaryColor,
    required this.accentColor,
    required this.shortsColor,
    required this.socksColor,
  });

  final String paletteName;
  final String primaryColor;
  final String secondaryColor;
  final String accentColor;
  final String shortsColor;
  final String socksColor;

  ColorPaletteProfileDto copyWith({
    String? paletteName,
    String? primaryColor,
    String? secondaryColor,
    String? accentColor,
    String? shortsColor,
    String? socksColor,
  }) {
    return ColorPaletteProfileDto(
      paletteName: paletteName ?? this.paletteName,
      primaryColor: primaryColor ?? this.primaryColor,
      secondaryColor: secondaryColor ?? this.secondaryColor,
      accentColor: accentColor ?? this.accentColor,
      shortsColor: shortsColor ?? this.shortsColor,
      socksColor: socksColor ?? this.socksColor,
    );
  }

  factory ColorPaletteProfileDto.fromJson(Map<String, dynamic> json) {
    return ColorPaletteProfileDto(
      paletteName: json['palette_name'] as String? ?? 'royal',
      primaryColor: json['primary_color'] as String? ?? '#123C73',
      secondaryColor: json['secondary_color'] as String? ?? '#F5F7FA',
      accentColor: json['accent_color'] as String? ?? '#E2A400',
      shortsColor: json['shorts_color'] as String? ?? '#0C1F3F',
      socksColor: json['socks_color'] as String? ?? '#F5F7FA',
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'palette_name': paletteName,
      'primary_color': primaryColor,
      'secondary_color': secondaryColor,
      'accent_color': accentColor,
      'shorts_color': shortsColor,
      'socks_color': socksColor,
    };
  }
}

class MatchIdentityDto {
  const MatchIdentityDto({
    required this.clubName,
    required this.shortClubCode,
    required this.homeKitColors,
    required this.awayKitColors,
    required this.generatedBadge,
    this.badgeUrl,
  });

  final String clubName;
  final String shortClubCode;
  final List<String> homeKitColors;
  final List<String> awayKitColors;
  final BadgeProfileDto generatedBadge;
  final String? badgeUrl;

  MatchIdentityDto copyWith({
    String? clubName,
    String? shortClubCode,
    List<String>? homeKitColors,
    List<String>? awayKitColors,
    BadgeProfileDto? generatedBadge,
    String? badgeUrl,
  }) {
    return MatchIdentityDto(
      clubName: clubName ?? this.clubName,
      shortClubCode: shortClubCode ?? this.shortClubCode,
      homeKitColors: homeKitColors ?? this.homeKitColors,
      awayKitColors: awayKitColors ?? this.awayKitColors,
      generatedBadge: generatedBadge ?? this.generatedBadge,
      badgeUrl: badgeUrl ?? this.badgeUrl,
    );
  }

  factory MatchIdentityDto.fromJson(Map<String, dynamic> json) {
    return MatchIdentityDto(
      clubName: json['club_name'] as String? ?? '',
      shortClubCode: json['short_club_code'] as String? ?? '',
      homeKitColors:
          (json['home_kit_colors'] as List<dynamic>? ?? const <dynamic>[])
              .map((dynamic value) => value.toString())
              .toList(growable: false),
      awayKitColors:
          (json['away_kit_colors'] as List<dynamic>? ?? const <dynamic>[])
              .map((dynamic value) => value.toString())
              .toList(growable: false),
      generatedBadge: BadgeProfileDto.fromJson(
          json['generated_badge'] as Map<String, dynamic>),
      badgeUrl: json['badge_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'club_name': clubName,
      'short_club_code': shortClubCode,
      'home_kit_colors': homeKitColors,
      'away_kit_colors': awayKitColors,
      'generated_badge': generatedBadge.toJson(),
      'badge_url': badgeUrl,
    };
  }
}

class ClubIdentityDto {
  const ClubIdentityDto({
    required this.clubId,
    required this.clubName,
    required this.shortClubCode,
    required this.colorPalette,
    required this.badgeProfile,
    required this.jerseySet,
    required this.matchIdentity,
  });

  final String clubId;
  final String clubName;
  final String shortClubCode;
  final ColorPaletteProfileDto colorPalette;
  final BadgeProfileDto badgeProfile;
  final JerseySetDto jerseySet;
  final MatchIdentityDto matchIdentity;

  ClubIdentityDto copyWith({
    String? clubName,
    String? shortClubCode,
    ColorPaletteProfileDto? colorPalette,
    BadgeProfileDto? badgeProfile,
    JerseySetDto? jerseySet,
    MatchIdentityDto? matchIdentity,
  }) {
    return ClubIdentityDto(
      clubId: clubId,
      clubName: clubName ?? this.clubName,
      shortClubCode: shortClubCode ?? this.shortClubCode,
      colorPalette: colorPalette ?? this.colorPalette,
      badgeProfile: badgeProfile ?? this.badgeProfile,
      jerseySet: jerseySet ?? this.jerseySet,
      matchIdentity: matchIdentity ?? this.matchIdentity,
    );
  }

  factory ClubIdentityDto.fromJson(Map<String, dynamic> json) {
    return ClubIdentityDto(
      clubId: json['club_id'] as String? ?? '',
      clubName: json['club_name'] as String? ?? '',
      shortClubCode: json['short_club_code'] as String? ?? '',
      colorPalette: ColorPaletteProfileDto.fromJson(
          json['color_palette'] as Map<String, dynamic>),
      badgeProfile: BadgeProfileDto.fromJson(
          json['badge_profile'] as Map<String, dynamic>),
      jerseySet:
          JerseySetDto.fromJson(json['jersey_set'] as Map<String, dynamic>),
      matchIdentity: MatchIdentityDto.fromJson(
          json['match_identity'] as Map<String, dynamic>),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'club_id': clubId,
      'club_name': clubName,
      'short_club_code': shortClubCode,
      'color_palette': colorPalette.toJson(),
      'badge_profile': badgeProfile.toJson(),
      'jersey_set': jerseySet.toJson(),
      'match_identity': matchIdentity.toJson(),
    };
  }

  Map<String, dynamic> toIdentityPatchJson() {
    return <String, dynamic>{
      'club_name': clubName,
      'short_club_code': shortClubCode,
      'color_palette': colorPalette.toJson(),
      'badge_profile': badgeProfile.toJson(),
    };
  }
}
