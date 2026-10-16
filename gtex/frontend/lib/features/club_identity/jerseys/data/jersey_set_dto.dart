import 'jersey_variant_dto.dart';

class JerseySetDto {
  const JerseySetDto({
    required this.home,
    required this.away,
    required this.third,
    required this.goalkeeper,
  });

  final JerseyVariantDto home;
  final JerseyVariantDto away;
  final JerseyVariantDto third;
  final JerseyVariantDto goalkeeper;

  List<JerseyVariantDto> get all =>
      <JerseyVariantDto>[home, away, third, goalkeeper];

  JerseyVariantDto variantFor(JerseyType type) {
    switch (type) {
      case JerseyType.home:
        return home;
      case JerseyType.away:
        return away;
      case JerseyType.third:
        return third;
      case JerseyType.goalkeeper:
        return goalkeeper;
    }
  }

  JerseySetDto updateVariant(JerseyType type, JerseyVariantDto variant) {
    switch (type) {
      case JerseyType.home:
        return copyWith(home: variant);
      case JerseyType.away:
        return copyWith(away: variant);
      case JerseyType.third:
        return copyWith(third: variant);
      case JerseyType.goalkeeper:
        return copyWith(goalkeeper: variant);
    }
  }

  JerseySetDto copyWith({
    JerseyVariantDto? home,
    JerseyVariantDto? away,
    JerseyVariantDto? third,
    JerseyVariantDto? goalkeeper,
  }) {
    return JerseySetDto(
      home: home ?? this.home,
      away: away ?? this.away,
      third: third ?? this.third,
      goalkeeper: goalkeeper ?? this.goalkeeper,
    );
  }

  factory JerseySetDto.fromJson(Map<String, dynamic> json) {
    return JerseySetDto(
      home: JerseyVariantDto.fromJson(json['home'] as Map<String, dynamic>),
      away: JerseyVariantDto.fromJson(json['away'] as Map<String, dynamic>),
      third: JerseyVariantDto.fromJson(json['third'] as Map<String, dynamic>),
      goalkeeper:
          JerseyVariantDto.fromJson(json['goalkeeper'] as Map<String, dynamic>),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'home': home.toJson(),
      'away': away.toJson(),
      'third': third.toJson(),
      'goalkeeper': goalkeeper.toJson(),
    };
  }
}
