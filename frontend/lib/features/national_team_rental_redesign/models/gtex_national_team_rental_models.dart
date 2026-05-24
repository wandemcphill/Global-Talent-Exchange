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
  final double rentalCostCredits;
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
      isPreseededRegen ? 'Pre-seeded regen' : sourceBucket;
  String get rarityLabel {
    final int? score = gsiScore;
    if (isPreseededRegen) return 'National Seed';
    if (score != null && score >= 90) return 'Legend Tier';
    if (score != null && score >= 84) return 'Elite';
    if (score != null && score >= 76) return 'Rare';
    return 'Squad Depth';
  }

  String get marketHeatLabel {
    final int? score = gsiScore;
    if (score == null) return 'Scout watch';
    if (score >= 88) return 'Hot demand';
    if (score >= 78) return 'Rising';
    return 'Value lane';
  }

  String get transferTrendLabel {
    final int? score = gsiScore;
    if (score == null) return 'Trend TBD';
    if (score >= 84) return 'Up';
    if (score < 68) return 'Sleeper';
    return 'Stable';
  }

  String get demandLabel =>
      isPreseededRegen ? 'Pool exclusive' : 'Live rental demand';
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
        total + player.rentalCostCredits,
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
    if (value == null) return 'TBD';
    if (value >= 1000000000) {
      return 'GTC ${(value / 1000000000).toStringAsFixed(1)}B';
    }
    if (value >= 1000000) {
      return 'GTC ${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (value >= 1000) {
      return 'GTC ${(value / 1000).toStringAsFixed(1)}K';
    }
    return 'GTC ${value.toStringAsFixed(0)}';
  }
}

class GtexNationalTeamRentalDemoData {
  const GtexNationalTeamRentalDemoData._();

  static const List<GtexRentalCompetitionView> competitions =
      <GtexRentalCompetitionView>[
        GtexRentalCompetitionView(
          id: 'gtex-u20-world-cup-2026',
          title: 'GTEX U20 World Cup',
          seasonLabel: '2026 Season',
          ageBand: 'U20',
          status: 'open',
          entryFeeLabel: 'GTC 25K',
          description:
              'Build a national squad with real players and pre-seeded regens.',
        ),
        GtexRentalCompetitionView(
          id: 'gtex-afcon-2026',
          title: 'GTEX AFCON',
          seasonLabel: '2026 Finals',
          ageBand: 'Senior',
          status: 'active',
          entryFeeLabel: 'GTC 40K',
          description:
              'African national-team competition with rental pool support.',
        ),
        GtexRentalCompetitionView(
          id: 'gtex-u17-world-cup-2026',
          title: 'GTEX U17 World Cup',
          seasonLabel: '2026 Youth',
          ageBand: 'U17',
          status: 'open',
          entryFeeLabel: 'GTC 15K',
          description:
              'Youth tournament powered by national pre-seeded regens.',
        ),
      ];

  static const List<GtexRentalCountryView> countries = <GtexRentalCountryView>[
    GtexRentalCountryView(
      countryCode: 'NG',
      countryName: 'Nigeria',
      confederation: 'CAF',
      eligiblePlayers: 42,
      rentalBudgetLabel: 'GTC 2.8M',
    ),
    GtexRentalCountryView(
      countryCode: 'GH',
      countryName: 'Ghana',
      confederation: 'CAF',
      eligiblePlayers: 31,
      rentalBudgetLabel: 'GTC 2.1M',
    ),
    GtexRentalCountryView(
      countryCode: 'SN',
      countryName: 'Senegal',
      confederation: 'CAF',
      eligiblePlayers: 36,
      rentalBudgetLabel: 'GTC 2.5M',
    ),
    GtexRentalCountryView(
      countryCode: 'GB-ENG',
      countryName: 'England',
      confederation: 'UEFA',
      eligiblePlayers: 58,
      rentalBudgetLabel: 'GTC 5.2M',
    ),
    GtexRentalCountryView(
      countryCode: 'BR',
      countryName: 'Brazil',
      confederation: 'CONMEBOL',
      eligiblePlayers: 64,
      rentalBudgetLabel: 'GTC 6.1M',
    ),
  ];

  static const List<GtexRentalTeamView> teams = <GtexRentalTeamView>[
    GtexRentalTeamView(
      id: 'ng-u20',
      countryCode: 'NG',
      name: 'Nigeria U20',
      ageBand: 'U20',
      competitionId: 'gtex-u20-world-cup-2026',
      eligiblePlayerCount: 24,
      minSquadSize: 16,
      maxSquadSize: 23,
    ),
    GtexRentalTeamView(
      id: 'ng-senior',
      countryCode: 'NG',
      name: 'Nigeria Senior',
      ageBand: 'Senior',
      competitionId: 'gtex-afcon-2026',
      eligiblePlayerCount: 18,
      minSquadSize: 18,
      maxSquadSize: 26,
    ),
    GtexRentalTeamView(
      id: 'gh-u20',
      countryCode: 'GH',
      name: 'Ghana U20',
      ageBand: 'U20',
      competitionId: 'gtex-u20-world-cup-2026',
      eligiblePlayerCount: 21,
      minSquadSize: 16,
      maxSquadSize: 23,
    ),
    GtexRentalTeamView(
      id: 'sn-senior',
      countryCode: 'SN',
      name: 'Senegal Senior',
      ageBand: 'Senior',
      competitionId: 'gtex-afcon-2026',
      eligiblePlayerCount: 22,
      minSquadSize: 18,
      maxSquadSize: 26,
    ),
    GtexRentalTeamView(
      id: 'eng-u20',
      countryCode: 'GB-ENG',
      name: 'England U20',
      ageBand: 'U20',
      competitionId: 'gtex-u20-world-cup-2026',
      eligiblePlayerCount: 30,
      minSquadSize: 16,
      maxSquadSize: 23,
    ),
    GtexRentalTeamView(
      id: 'br-u17',
      countryCode: 'BR',
      name: 'Brazil U17',
      ageBand: 'U17',
      competitionId: 'gtex-u17-world-cup-2026',
      eligiblePlayerCount: 33,
      minSquadSize: 16,
      maxSquadSize: 21,
    ),
  ];

  static const List<GtexRentalPlayerView> players = <GtexRentalPlayerView>[
    GtexRentalPlayerView(
      playerId: 'ng-001',
      name: 'T. Adebayo',
      position: 'ST',
      age: 19,
      rating: 78.4,
      nationality: 'Nigeria',
      countryCode: 'NG',
      clubName: 'Lagos Meteors',
      rentalCostCredits: 240000,
      sourceBucket: 'SportMonks',
      eligibilityNote: 'Eligible for Nigeria U20',
    ),
    GtexRentalPlayerView(
      playerId: 'ng-002',
      name: 'M. Okoro',
      position: 'CM',
      age: 18,
      rating: 74.8,
      nationality: 'Nigeria',
      countryCode: 'NG',
      clubName: 'GTEX National Seed',
      rentalCostCredits: 95000,
      sourceBucket: 'national_seed',
      eligibilityNote: 'Pre-seeded to fill national pool',
      isPreseededRegen: true,
    ),
    GtexRentalPlayerView(
      playerId: 'ng-003',
      name: 'S. Balogun',
      position: 'CB',
      age: 20,
      rating: 73.1,
      nationality: 'Nigeria',
      countryCode: 'NG',
      clubName: 'Abuja Royals',
      rentalCostCredits: 155000,
      sourceBucket: 'SportMonks',
      eligibilityNote: 'Senior and U20 eligible',
    ),
    GtexRentalPlayerView(
      playerId: 'gh-001',
      name: 'K. Mensah',
      position: 'LW',
      age: 19,
      rating: 76.2,
      nationality: 'Ghana',
      countryCode: 'GH',
      clubName: 'Accra Galaxy',
      rentalCostCredits: 210000,
      sourceBucket: 'SportMonks',
    ),
    GtexRentalPlayerView(
      playerId: 'sn-001',
      name: 'I. Diouf',
      position: 'DM',
      age: 24,
      rating: 81.0,
      nationality: 'Senegal',
      countryCode: 'SN',
      clubName: 'Dakar Lions',
      rentalCostCredits: 430000,
      sourceBucket: 'SportMonks',
    ),
    GtexRentalPlayerView(
      playerId: 'eng-001',
      name: 'J. Whitmore',
      position: 'RW',
      age: 19,
      rating: 79.5,
      nationality: 'England',
      countryCode: 'GB-ENG',
      clubName: 'North London Reds',
      rentalCostCredits: 520000,
      sourceBucket: 'SportMonks',
    ),
    GtexRentalPlayerView(
      playerId: 'br-001',
      name: 'L. Moreira',
      position: 'CAM',
      age: 16,
      rating: 77.7,
      nationality: 'Brazil',
      countryCode: 'BR',
      clubName: 'GTEX National Seed',
      rentalCostCredits: 185000,
      sourceBucket: 'national_seed',
      isPreseededRegen: true,
    ),
  ];
}
