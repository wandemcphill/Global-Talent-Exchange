/// Batch 3 route-compatible view models for the GTEX national-team rental flow.
///
/// These are intentionally frontend view models. They do not replace existing
/// backend DTOs such as NationalTeamCompetition or NationalTeamEntry. Codex can
/// map the live national-team engine payloads into these types while preserving
/// the current business logic.
class GtexRentalCompetitionView {
  const GtexRentalCompetitionView({
    required this.id,
    required this.title,
    required this.seasonLabel,
    required this.ageBand,
    required this.status,
    required this.entryFeeLabel,
    this.description,
  });

  final String id;
  final String title;
  final String seasonLabel;
  final String ageBand;
  final String status;
  final String entryFeeLabel;
  final String? description;

  bool get isOpen =>
      status.toLowerCase() == 'open' || status.toLowerCase() == 'active';
}

class GtexRentalCountryView {
  const GtexRentalCountryView({
    required this.countryCode,
    required this.countryName,
    required this.confederation,
    required this.eligiblePlayers,
    required this.rentalBudgetLabel,
    this.flagEmoji,
  });

  final String countryCode;
  final String countryName;
  final String confederation;
  final int eligiblePlayers;
  final String rentalBudgetLabel;
  final String? flagEmoji;

  String get displayFlag =>
      flagEmoji == null || flagEmoji!.trim().isEmpty ? '' : flagEmoji!;
}

class GtexRentalTeamView {
  const GtexRentalTeamView({
    required this.id,
    required this.countryCode,
    required this.name,
    required this.ageBand,
    required this.competitionId,
    required this.eligiblePlayerCount,
    required this.minSquadSize,
    required this.maxSquadSize,
    this.entryId,
  });

  final String id;
  final String countryCode;
  final String name;
  final String ageBand;
  final String competitionId;
  final int eligiblePlayerCount;
  final int minSquadSize;
  final int maxSquadSize;
  final String? entryId;

  String get squadRuleLabel => '$minSquadSize-$maxSquadSize players';
}

class GtexRentalPlayerView {
  const GtexRentalPlayerView({
    required this.playerId,
    required this.name,
    required this.position,
    required this.age,
    required this.rating,
    required this.nationality,
    required this.countryCode,
    required this.clubName,
    required this.rentalCostCredits,
    required this.sourceBucket,
    this.imageUrl,
    this.portraitUrl,
    this.portraitStatus,
    this.portraitMissingReason,
    this.eligibilityNote,
    this.rentalEligible = true,
    this.eligibilityReasons = const <String>[],
    this.isPreseededRegen = false,
  });

  final String playerId;
  final String name;
  final String position;
  final int? age;
  final double? rating;
  final String nationality;
  final String countryCode;
  final String clubName;
  final double? rentalCostCredits;
  final String sourceBucket;
  final String? imageUrl;
  final String? portraitUrl;
  final String? portraitStatus;
  final String? portraitMissingReason;
  final String? eligibilityNote;
  final bool rentalEligible;
  final List<String> eligibilityReasons;
  final bool isPreseededRegen;

  String get priceLabel => GtexRentalFormatters.credits(rentalCostCredits);
  String get ageLabel => age == null ? 'Age TBD' : 'Age $age';
  int? get gsiScore => rating?.round();
  String get gsiLabel => rating == null ? 'GSI TBD' : 'GSI ${rating!.round()}';
  String? get gsiTierLabel {
    final int? score = gsiScore;
    if (score == null) return null;
    if (score >= 90) return 'Elite GSI';
    if (score >= 82) return 'High-grade GSI';
    if (score >= 74) return 'First-team GSI';
    if (score >= 66) return 'Developing GSI';
    return 'Prospect GSI';
  }

  String get ratingLabel =>
      rating == null ? 'GSI TBD' : 'GSI ${rating!.round()}';
  String get sourceLabel =>
      isPreseededRegen ? 'NATIONAL SEED' : _sourceBucketLabel(sourceBucket);
  String get rarityLabel {
    if (isPreseededRegen) return 'NATIONAL SEED';
    return 'RENTAL POOL';
  }

  String get marketHeatLabel {
    if (rentalEligible) return 'BACKEND ELIGIBLE';
    return 'BACKEND LOCKED';
  }

  String get transferTrendLabel => 'LIVE POOL';

  String get demandLabel =>
      isPreseededRegen ? 'NATIONAL SEED' : 'BACKEND ELIGIBLE';

  String get availabilityLabel {
    if (rentalEligible) return 'AVAILABLE';
    final String reason =
        eligibilityReasons.isNotEmpty
            ? eligibilityReasons.first
            : (eligibilityNote ?? 'Backend locked');
    return 'LOCKED - ${reason.toUpperCase()}';
  }

  String get ruleSourceLabel =>
      eligibilityReasons.isEmpty
          ? 'Backend rules clear'
          : eligibilityReasons.join(' | ');

  static String _sourceBucketLabel(String value) {
    final String normalized = value.trim().replaceAll('_', ' ');
    if (normalized.isEmpty) return 'BACKEND SOURCE';
    return normalized.toUpperCase();
  }
}

class GtexRentalBasketState {
  const GtexRentalBasketState(this.itemsById);

  final Map<String, GtexRentalPlayerView> itemsById;

  List<GtexRentalPlayerView> get items =>
      itemsById.values.toList(growable: false);

  int get squadCount => items.length;

  bool get allEligible =>
      items.every((GtexRentalPlayerView player) => player.rentalEligible);

  double get totalCredits => items.fold<double>(
    0,
    (double total, GtexRentalPlayerView player) =>
        total + (player.rentalCostCredits ?? 0),
  );

  String get totalLabel => GtexRentalFormatters.credits(totalCredits);

  bool contains(String playerId) => itemsById.containsKey(playerId);

  GtexRentalBasketState toggled(GtexRentalPlayerView player) {
    if (!player.rentalEligible) {
      return this;
    }
    final Map<String, GtexRentalPlayerView> next =
        Map<String, GtexRentalPlayerView>.of(itemsById);
    if (next.containsKey(player.playerId)) {
      next.remove(player.playerId);
    } else {
      next[player.playerId] = player;
    }
    return GtexRentalBasketState(next);
  }

  GtexRentalBasketState removed(String playerId) {
    final Map<String, GtexRentalPlayerView> next =
        Map<String, GtexRentalPlayerView>.of(itemsById)..remove(playerId);
    return GtexRentalBasketState(next);
  }
}

class GtexRentalFormatters {
  const GtexRentalFormatters._();

  static String credits(double? value) {
    if (value == null) return 'GTEX TBD';
    if (value >= 1000000000) {
      return 'GTEX ${(value / 1000000000).toStringAsFixed(1)}B';
    }
    if (value >= 1000000) {
      return 'GTEX ${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (value >= 1000) {
      return 'GTEX ${(value / 1000).toStringAsFixed(1)}K';
    }
    return 'GTEX ${value.toStringAsFixed(0)}';
  }
}
