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
    final String clubId = json['club_id'] as String? ?? '';
    final String clubName = json['club_name'] as String? ?? '';
    final String shortClubCode = json['short_club_code'] as String? ?? '';
    final ColorPaletteProfileDto colorPalette = ColorPaletteProfileDto.fromJson(
        json['color_palette'] as Map<String, dynamic>);
    final BadgeProfileDto badgeProfile = BadgeProfileDto.fromJson(
        json['badge_profile'] as Map<String, dynamic>);
    final JerseySetDto jerseySet =
        JerseySetDto.fromJson(json['jersey_set'] as Map<String, dynamic>);
    final Map<String, dynamic>? matchIdentityJson =
        json['match_identity'] as Map<String, dynamic>?;
    final MatchIdentityDto matchIdentity = matchIdentityJson == null
        ? MatchIdentityDto(
            clubName: clubName,
            shortClubCode: shortClubCode,
            homeKitColors: <String>[
              jerseySet.home.primaryColor,
              jerseySet.home.secondaryColor,
              jerseySet.home.accentColor,
            ],
            awayKitColors: <String>[
              jerseySet.away.primaryColor,
              jerseySet.away.secondaryColor,
              jerseySet.away.accentColor,
            ],
            generatedBadge: badgeProfile,
            badgeUrl: badgeProfile.badgeUrl,
          )
        : MatchIdentityDto.fromJson(matchIdentityJson);
    return ClubIdentityDto(
      clubId: clubId,
      clubName: clubName,
      shortClubCode: shortClubCode,
      colorPalette: colorPalette,
      badgeProfile: badgeProfile,
      jerseySet: jerseySet,
      matchIdentity: matchIdentity,
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


class ClubDnaPolicyDto {
  const ClubDnaPolicyDto({
    required this.clubId,
    this.primaryPhilosophy = 'balanced',
    this.secondaryPhilosophies = const <String>[],
    this.nationalityMode = 'none',
    this.targetNationalities = const <String>[],
    this.allowDualNationality = true,
    this.ageMode = 'none',
    this.preferredMaxAge,
    this.allowAgeExceptions = true,
    this.transferStrategy = 'balanced',
    this.financialPhilosophy = 'sustainable',
    this.clubVisionNarrative,
    this.metadata = const <String, dynamic>{},
  });

  final String clubId;
  final String primaryPhilosophy;
  final List<String> secondaryPhilosophies;
  final String nationalityMode;
  final List<String> targetNationalities;
  final bool allowDualNationality;
  final String ageMode;
  final int? preferredMaxAge;
  final bool allowAgeExceptions;
  final String transferStrategy;
  final String financialPhilosophy;
  final String? clubVisionNarrative;
  final Map<String, dynamic> metadata;

  factory ClubDnaPolicyDto.fromJson(Map<String, dynamic> json) {
    return ClubDnaPolicyDto(
      clubId: json['club_id'] as String? ?? '',
      primaryPhilosophy: json['primary_philosophy'] as String? ?? 'balanced',
      secondaryPhilosophies: (json['secondary_philosophies'] as List<dynamic>? ?? const <dynamic>[])
          .map((dynamic e) => e.toString())
          .toList(growable: false),
      nationalityMode: json['nationality_mode'] as String? ?? 'none',
      targetNationalities: (json['target_nationalities'] as List<dynamic>? ?? const <dynamic>[])
          .map((dynamic e) => e.toString())
          .toList(growable: false),
      allowDualNationality: json['allow_dual_nationality'] as bool? ?? true,
      ageMode: json['age_mode'] as String? ?? 'none',
      preferredMaxAge: (json['preferred_max_age'] as num?)?.toInt(),
      allowAgeExceptions: json['allow_age_exceptions'] as bool? ?? true,
      transferStrategy: json['transfer_strategy'] as String? ?? 'balanced',
      financialPhilosophy: json['financial_philosophy'] as String? ?? 'sustainable',
      clubVisionNarrative: json['club_vision_narrative'] as String?,
      metadata: json['metadata'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['metadata'] as Map<String, dynamic>)
          : const <String, dynamic>{},
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'club_id': clubId,
      'primary_philosophy': primaryPhilosophy,
      'secondary_philosophies': secondaryPhilosophies,
      'nationality_mode': nationalityMode,
      'target_nationalities': targetNationalities,
      'allow_dual_nationality': allowDualNationality,
      'age_mode': ageMode,
      'preferred_max_age': preferredMaxAge,
      'allow_age_exceptions': allowAgeExceptions,
      'transfer_strategy': transferStrategy,
      'financial_philosophy': financialPhilosophy,
      'club_vision_narrative': clubVisionNarrative,
      'metadata': metadata,
    };
  }
}

class StudioConversationalEditResultDto {
  const StudioConversationalEditResultDto({
    required this.kit,
    required this.crest,
    required this.summary,
  });

  final Map<String, dynamic> kit;
  final Map<String, dynamic> crest;
  final String summary;

  factory StudioConversationalEditResultDto.fromJson(Map<String, dynamic> json) {
    return StudioConversationalEditResultDto(
      kit: json['kit'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['kit'] as Map<String, dynamic>)
          : const <String, dynamic>{},
      crest: json['crest'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['crest'] as Map<String, dynamic>)
          : const <String, dynamic>{},
      summary: json['summary'] as String? ?? 'Applied studio adjustments.',
    );
  }
}
