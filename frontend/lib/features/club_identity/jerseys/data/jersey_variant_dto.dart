enum JerseyType { home, away, third, goalkeeper }

enum PatternType { solid, stripes, hoops, sash, chevron, gradient }

enum CollarStyle { crew, vNeck, polo, wrap }

enum SleeveStyle { short, long, raglan, cuffed }

class JerseyVariantDto {
  const JerseyVariantDto({
    required this.jerseyType,
    required this.primaryColor,
    required this.secondaryColor,
    required this.accentColor,
    required this.patternType,
    required this.collarStyle,
    required this.sleeveStyle,
    required this.badgePlacement,
    required this.frontText,
    required this.shortsColor,
    required this.socksColor,
    this.themeTags = const <String>[],
    this.commemorativePatch,
  });

  final JerseyType jerseyType;
  final String primaryColor;
  final String secondaryColor;
  final String accentColor;
  final PatternType patternType;
  final CollarStyle collarStyle;
  final SleeveStyle sleeveStyle;
  final String badgePlacement;
  final String frontText;
  final String shortsColor;
  final String socksColor;
  final List<String> themeTags;
  final String? commemorativePatch;

  String get label {
    switch (jerseyType) {
      case JerseyType.home:
        return 'Home';
      case JerseyType.away:
        return 'Away';
      case JerseyType.third:
        return 'Third';
      case JerseyType.goalkeeper:
        return 'Goalkeeper';
    }
  }

  JerseyVariantDto copyWith({
    String? primaryColor,
    String? secondaryColor,
    String? accentColor,
    PatternType? patternType,
    CollarStyle? collarStyle,
    SleeveStyle? sleeveStyle,
    String? badgePlacement,
    String? frontText,
    String? shortsColor,
    String? socksColor,
    List<String>? themeTags,
    String? commemorativePatch,
  }) {
    return JerseyVariantDto(
      jerseyType: jerseyType,
      primaryColor: primaryColor ?? this.primaryColor,
      secondaryColor: secondaryColor ?? this.secondaryColor,
      accentColor: accentColor ?? this.accentColor,
      patternType: patternType ?? this.patternType,
      collarStyle: collarStyle ?? this.collarStyle,
      sleeveStyle: sleeveStyle ?? this.sleeveStyle,
      badgePlacement: badgePlacement ?? this.badgePlacement,
      frontText: frontText ?? this.frontText,
      shortsColor: shortsColor ?? this.shortsColor,
      socksColor: socksColor ?? this.socksColor,
      themeTags: themeTags ?? this.themeTags,
      commemorativePatch: commemorativePatch ?? this.commemorativePatch,
    );
  }

  factory JerseyVariantDto.fromJson(Map<String, dynamic> json) {
    return JerseyVariantDto(
      jerseyType: JerseyType.values.byName(json['jersey_type'] as String),
      primaryColor: json['primary_color'] as String? ?? '#123C73',
      secondaryColor: json['secondary_color'] as String? ?? '#F5F7FA',
      accentColor: json['accent_color'] as String? ?? '#E2A400',
      patternType:
          PatternType.values.byName(json['pattern_type'] as String? ?? 'solid'),
      collarStyle: CollarStyle.values
          .byName(_normalizeCollar(json['collar_style'] as String? ?? 'crew')),
      sleeveStyle: SleeveStyle.values
          .byName(_normalizeSleeve(json['sleeve_style'] as String? ?? 'short')),
      badgePlacement: json['badge_placement'] as String? ?? 'left_chest',
      frontText: json['front_text'] as String? ?? '',
      shortsColor: json['shorts_color'] as String? ?? '#123C73',
      socksColor: json['socks_color'] as String? ?? '#F5F7FA',
      themeTags: (json['theme_tags'] as List<dynamic>? ?? const <dynamic>[])
          .map((dynamic tag) => tag.toString())
          .toList(growable: false),
      commemorativePatch: json['commemorative_patch'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'jersey_type': jerseyType.name,
      'primary_color': primaryColor,
      'secondary_color': secondaryColor,
      'accent_color': accentColor,
      'pattern_type': patternType.name,
      'collar_style': _collarWireValue(collarStyle),
      'sleeve_style': _sleeveWireValue(sleeveStyle),
      'badge_placement': badgePlacement,
      'front_text': frontText,
      'shorts_color': shortsColor,
      'socks_color': socksColor,
      'theme_tags': themeTags,
      'commemorative_patch': commemorativePatch,
    };
  }
}

String _normalizeCollar(String value) {
  switch (value) {
    case 'v_neck':
      return 'vNeck';
    default:
      return value;
  }
}

String _normalizeSleeve(String value) {
  return value;
}

String _collarWireValue(CollarStyle value) {
  switch (value) {
    case CollarStyle.vNeck:
      return 'v_neck';
    case CollarStyle.crew:
      return 'crew';
    case CollarStyle.polo:
      return 'polo';
    case CollarStyle.wrap:
      return 'wrap';
  }
}

String _sleeveWireValue(SleeveStyle value) {
  switch (value) {
    case SleeveStyle.short:
      return 'short';
    case SleeveStyle.long:
      return 'long';
    case SleeveStyle.raglan:
      return 'raglan';
    case SleeveStyle.cuffed:
      return 'cuffed';
  }
}
