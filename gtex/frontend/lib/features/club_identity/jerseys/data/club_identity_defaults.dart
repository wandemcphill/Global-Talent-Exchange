import 'dart:convert';

import 'badge_profile_dto.dart';
import 'club_identity_dto.dart';
import 'jersey_set_dto.dart';
import 'jersey_variant_dto.dart';

class ClubIdentityDefaults {
  static const List<ColorPaletteProfileDto> palettes = <ColorPaletteProfileDto>[
    ColorPaletteProfileDto(
      paletteName: 'royal',
      primaryColor: '#123C73',
      secondaryColor: '#F5F7FA',
      accentColor: '#E2A400',
      shortsColor: '#0C1F3F',
      socksColor: '#F5F7FA',
    ),
    ColorPaletteProfileDto(
      paletteName: 'forest',
      primaryColor: '#0F5132',
      secondaryColor: '#F2F0E6',
      accentColor: '#D97706',
      shortsColor: '#1B4332',
      socksColor: '#E9F5DB',
    ),
    ColorPaletteProfileDto(
      paletteName: 'sunset',
      primaryColor: '#8A1538',
      secondaryColor: '#F8E16C',
      accentColor: '#FFD166',
      shortsColor: '#5C1D2B',
      socksColor: '#F8E16C',
    ),
    ColorPaletteProfileDto(
      paletteName: 'ocean',
      primaryColor: '#005F73',
      secondaryColor: '#E9D8A6',
      accentColor: '#94D2BD',
      shortsColor: '#003845',
      socksColor: '#E9D8A6',
    ),
    ColorPaletteProfileDto(
      paletteName: 'ember',
      primaryColor: '#7F1D1D',
      secondaryColor: '#F8FAFC',
      accentColor: '#F97316',
      shortsColor: '#111827',
      socksColor: '#F8FAFC',
    ),
    ColorPaletteProfileDto(
      paletteName: 'violet',
      primaryColor: '#4C1D95',
      secondaryColor: '#EDE9FE',
      accentColor: '#22C55E',
      shortsColor: '#312E81',
      socksColor: '#EDE9FE',
    ),
  ];

  static const List<String> suggestedColors = <String>[
    '#101820',
    '#123C73',
    '#0F5132',
    '#8A1538',
    '#005F73',
    '#7F1D1D',
    '#4C1D95',
    '#F5F7FA',
    '#EDE9FE',
    '#F8E16C',
    '#F97316',
    '#7DE2D1',
  ];

  static ClubIdentityDto generate({
    required String clubId,
    String? clubName,
  }) {
    final String resolvedName = clubName ?? _titleizeClubId(clubId);
    final String shortCode = buildShortCode(resolvedName);
    final ColorPaletteProfileDto palette =
        palettes[_stableIndex(clubId, palettes.length)];
    final BadgeProfileDto badge = BadgeProfileDto(
      shape: BadgeShape
          .values[_stableIndex('$clubId-shape', BadgeShape.values.length)],
      initials: shortCode,
      iconFamily: BadgeIconFamily
          .values[_stableIndex('$clubId-icon', BadgeIconFamily.values.length)],
      primaryColor: palette.primaryColor,
      secondaryColor: palette.secondaryColor,
      accentColor: palette.accentColor,
    );
    final JerseySetDto jerseys = JerseySetDto(
      home: defaultVariant(
        type: JerseyType.home,
        shortCode: shortCode,
        palette: palette,
      ),
      away: defaultVariant(
        type: JerseyType.away,
        shortCode: shortCode,
        palette: palette,
      ),
      third: defaultVariant(
        type: JerseyType.third,
        shortCode: shortCode,
        palette: palette,
      ),
      goalkeeper: defaultVariant(
        type: JerseyType.goalkeeper,
        shortCode: shortCode,
        palette: palette,
      ),
    );
    return buildIdentity(
      clubId: clubId,
      clubName: resolvedName,
      shortClubCode: shortCode,
      colorPalette: palette,
      badgeProfile: badge,
      jerseySet: jerseys,
    );
  }

  static ClubIdentityDto buildIdentity({
    required String clubId,
    required String clubName,
    required String shortClubCode,
    required ColorPaletteProfileDto colorPalette,
    required BadgeProfileDto badgeProfile,
    required JerseySetDto jerseySet,
  }) {
    return ClubIdentityDto(
      clubId: clubId,
      clubName: clubName,
      shortClubCode: shortClubCode,
      colorPalette: colorPalette,
      badgeProfile: badgeProfile,
      jerseySet: jerseySet,
      matchIdentity: MatchIdentityDto(
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
      ),
    );
  }

  static JerseyVariantDto defaultVariant({
    required JerseyType type,
    required String shortCode,
    required ColorPaletteProfileDto palette,
  }) {
    switch (type) {
      case JerseyType.home:
        return JerseyVariantDto(
          jerseyType: type,
          primaryColor: palette.primaryColor,
          secondaryColor: palette.secondaryColor,
          accentColor: palette.accentColor,
          patternType: PatternType.solid,
          collarStyle: CollarStyle.crew,
          sleeveStyle: SleeveStyle.short,
          badgePlacement: 'left_chest',
          frontText: shortCode,
          shortsColor: palette.shortsColor,
          socksColor: palette.socksColor,
          themeTags: const <String>['core'],
        );
      case JerseyType.away:
        return JerseyVariantDto(
          jerseyType: type,
          primaryColor: palette.secondaryColor,
          secondaryColor: palette.primaryColor,
          accentColor: palette.accentColor,
          patternType: PatternType.sash,
          collarStyle: CollarStyle.vNeck,
          sleeveStyle: SleeveStyle.raglan,
          badgePlacement: 'left_chest',
          frontText: shortCode,
          shortsColor: palette.secondaryColor,
          socksColor: palette.primaryColor,
          themeTags: const <String>['road'],
        );
      case JerseyType.third:
        return JerseyVariantDto(
          jerseyType: type,
          primaryColor: palette.accentColor,
          secondaryColor: palette.primaryColor,
          accentColor: palette.secondaryColor,
          patternType: PatternType.gradient,
          collarStyle: CollarStyle.wrap,
          sleeveStyle: SleeveStyle.cuffed,
          badgePlacement: 'center_chest',
          frontText: '$shortCode ALT',
          shortsColor: palette.primaryColor,
          socksColor: palette.accentColor,
          themeTags: const <String>['limited', 'unlockable'],
        );
      case JerseyType.goalkeeper:
        return const JerseyVariantDto(
          jerseyType: JerseyType.goalkeeper,
          primaryColor: '#1F2937',
          secondaryColor: '#A7F3D0',
          accentColor: '#F9FAFB',
          patternType: PatternType.chevron,
          collarStyle: CollarStyle.crew,
          sleeveStyle: SleeveStyle.long,
          badgePlacement: 'left_chest',
          frontText: 'GK',
          shortsColor: '#111827',
          socksColor: '#A7F3D0',
          themeTags: <String>['keeper'],
        ).copyWith(frontText: '$shortCode GK');
    }
  }

  static int _stableIndex(String source, int length) {
    final List<int> bytes = utf8.encode(source);
    int hash = 17;
    for (final int byte in bytes) {
      hash = 37 * hash + byte;
    }
    return hash.abs() % length;
  }

  static String buildShortCode(String clubName) {
    final List<String> words = clubName
        .replaceAll('-', ' ')
        .split(' ')
        .where((String word) => word.isNotEmpty)
        .toList();
    if (words.length >= 2) {
      return words.take(3).map((String word) => word[0]).join().toUpperCase();
    }
    final String condensed = clubName.replaceAll(' ', '');
    final int end = condensed.length < 3 ? condensed.length : 3;
    return condensed.substring(0, end).toUpperCase();
  }

  static String _titleizeClubId(String clubId) {
    return clubId
        .replaceAll('_', ' ')
        .replaceAll('-', ' ')
        .split(' ')
        .where((String part) => part.isNotEmpty)
        .map(
          (String part) =>
              '${part.substring(0, 1).toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }
}
