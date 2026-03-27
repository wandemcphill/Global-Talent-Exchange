import 'package:gte_frontend/models/player.dart';

class MatchResult {
  const MatchResult({
    required this.player,
    required this.score,
    required this.reasons,
    required this.breakdown,
    required this.flags,
    this.preferredFoot,
    this.heightMeters,
  });

  final Player player;
  final double score;
  final List<String> reasons;
  final Map<String, double> breakdown;
  final MatchFlags flags;
  final String? preferredFoot;
  final double? heightMeters;
}

class MatchFlags {
  const MatchFlags({
    required this.isFreeAgent,
    required this.isExactPosition,
    required this.isHighPotential,
  });

  final bool isFreeAgent;
  final bool isExactPosition;
  final bool isHighPotential;
}
