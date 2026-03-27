import 'match_weights.dart';

class MatchWeightPreset {
  const MatchWeightPreset({
    required this.label,
    required this.badgeLabel,
    required this.weights,
  });

  final String label;
  final String badgeLabel;
  final MatchWeights weights;
}

class MatchWeightPresets {
  const MatchWeightPresets._();

  static MatchWeights balanced() => MatchWeights.defaultWeights();

  static MatchWeights youthFocus() => const MatchWeights(
        position: 0.35,
        age: 0.35,
        country: 0.05,
        height: 0.10,
        foot: 0.05,
        availability: 0.10,
      );

  static MatchWeights readyNow() => const MatchWeights(
        position: 0.45,
        age: 0.10,
        country: 0.05,
        height: 0.10,
        foot: 0.10,
        availability: 0.20,
      );

  static MatchWeights undervalued() => const MatchWeights(
        position: 0.30,
        age: 0.15,
        country: 0.20,
        height: 0.05,
        foot: 0.05,
        availability: 0.25,
      );

  static const List<MatchWeightPreset> all = <MatchWeightPreset>[
    MatchWeightPreset(
      label: 'Balanced',
      badgeLabel: 'Balanced',
      weights: MatchWeights(
        position: 0.40,
        age: 0.20,
        country: 0.10,
        height: 0.10,
        foot: 0.10,
        availability: 0.10,
      ),
    ),
    MatchWeightPreset(
      label: 'Youth Focus',
      badgeLabel: 'Youth Focus',
      weights: MatchWeights(
        position: 0.35,
        age: 0.35,
        country: 0.05,
        height: 0.10,
        foot: 0.05,
        availability: 0.10,
      ),
    ),
    MatchWeightPreset(
      label: 'Ready Now',
      badgeLabel: 'Ready Now',
      weights: MatchWeights(
        position: 0.45,
        age: 0.10,
        country: 0.05,
        height: 0.10,
        foot: 0.10,
        availability: 0.20,
      ),
    ),
    MatchWeightPreset(
      label: 'Undervalued',
      badgeLabel: 'Undervalued',
      weights: MatchWeights(
        position: 0.30,
        age: 0.15,
        country: 0.20,
        height: 0.05,
        foot: 0.05,
        availability: 0.25,
      ),
    ),
  ];

  static MatchWeightPreset? resolve(MatchWeights weights) {
    final String cacheKey = weights.cacheKey;
    for (final MatchWeightPreset preset in all) {
      if (preset.weights.cacheKey == cacheKey) {
        return preset;
      }
    }
    return null;
  }
}
