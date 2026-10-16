enum BadgeShape { shield, round, diamond, pennant }

enum BadgeIconFamily { star, lion, eagle, crown, oak, bolt }

class BadgeProfileDto {
  const BadgeProfileDto({
    required this.shape,
    required this.initials,
    required this.iconFamily,
    required this.primaryColor,
    required this.secondaryColor,
    required this.accentColor,
    this.badgeUrl,
    this.trophyStarCount = 0,
    this.commemorativePatch,
  });

  final BadgeShape shape;
  final String initials;
  final BadgeIconFamily iconFamily;
  final String primaryColor;
  final String secondaryColor;
  final String accentColor;
  final String? badgeUrl;
  final int trophyStarCount;
  final String? commemorativePatch;

  BadgeProfileDto copyWith({
    BadgeShape? shape,
    String? initials,
    BadgeIconFamily? iconFamily,
    String? primaryColor,
    String? secondaryColor,
    String? accentColor,
    String? badgeUrl,
    int? trophyStarCount,
    String? commemorativePatch,
  }) {
    return BadgeProfileDto(
      shape: shape ?? this.shape,
      initials: initials ?? this.initials,
      iconFamily: iconFamily ?? this.iconFamily,
      primaryColor: primaryColor ?? this.primaryColor,
      secondaryColor: secondaryColor ?? this.secondaryColor,
      accentColor: accentColor ?? this.accentColor,
      badgeUrl: badgeUrl ?? this.badgeUrl,
      trophyStarCount: trophyStarCount ?? this.trophyStarCount,
      commemorativePatch: commemorativePatch ?? this.commemorativePatch,
    );
  }

  factory BadgeProfileDto.fromJson(Map<String, dynamic> json) {
    return BadgeProfileDto(
      shape: BadgeShape.values.byName(json['shape'] as String),
      initials: json['initials'] as String? ?? '',
      iconFamily: BadgeIconFamily.values.byName(json['icon_family'] as String),
      primaryColor: json['primary_color'] as String? ?? '#123C73',
      secondaryColor: json['secondary_color'] as String? ?? '#F5F7FA',
      accentColor: json['accent_color'] as String? ?? '#E2A400',
      badgeUrl: json['badge_url'] as String?,
      trophyStarCount: json['trophy_star_count'] as int? ?? 0,
      commemorativePatch: json['commemorative_patch'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'shape': shape.name,
      'initials': initials,
      'icon_family': iconFamily.name,
      'primary_color': primaryColor,
      'secondary_color': secondaryColor,
      'accent_color': accentColor,
      'badge_url': badgeUrl,
      'trophy_star_count': trophyStarCount,
      'commemorative_patch': commemorativePatch,
    };
  }
}
