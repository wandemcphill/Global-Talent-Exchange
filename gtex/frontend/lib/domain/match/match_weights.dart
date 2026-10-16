class MatchWeights {
  const MatchWeights({
    required this.position,
    required this.age,
    required this.country,
    required this.height,
    required this.foot,
    required this.availability,
  });

  factory MatchWeights.defaultWeights() {
    return const MatchWeights(
      position: 0.40,
      age: 0.20,
      country: 0.10,
      height: 0.10,
      foot: 0.10,
      availability: 0.10,
    );
  }

  final double position;
  final double age;
  final double country;
  final double height;
  final double foot;
  final double availability;

  double get total => position + age + country + height + foot + availability;

  MatchWeights normalize() {
    final double safeTotal = total <= 0 ? 1 : total;
    return MatchWeights(
      position: position / safeTotal,
      age: age / safeTotal,
      country: country / safeTotal,
      height: height / safeTotal,
      foot: foot / safeTotal,
      availability: availability / safeTotal,
    );
  }

  Map<String, double> toJson() {
    final MatchWeights normalized = normalize();
    return <String, double>{
      'position': normalized.position,
      'age': normalized.age,
      'country': normalized.country,
      'height': normalized.height,
      'foot': normalized.foot,
      'availability': normalized.availability,
    };
  }

  String get cacheKey {
    final MatchWeights normalized = normalize();
    return <double>[
      normalized.position,
      normalized.age,
      normalized.country,
      normalized.height,
      normalized.foot,
      normalized.availability,
    ].map((double value) => value.toStringAsFixed(4)).join('|');
  }

  MatchWeights copyWith({
    double? position,
    double? age,
    double? country,
    double? height,
    double? foot,
    double? availability,
  }) {
    return MatchWeights(
      position: position ?? this.position,
      age: age ?? this.age,
      country: country ?? this.country,
      height: height ?? this.height,
      foot: foot ?? this.foot,
      availability: availability ?? this.availability,
    );
  }
}
