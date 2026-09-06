import '../../../data/gte_exchange_models.dart';

/// View-model adapter for the redesigned GTEX player market.
///
/// This intentionally wraps the existing [GteMarketPlayerListItem] instead of
/// replacing it, so Batch 2 can be mounted on the current `/app/market` route
/// without changing business logic.
class GtexMarketPlayerView {
  const GtexMarketPlayerView({
    required this.raw,
    required this.playerId,
    required this.name,
    required this.position,
    required this.nationality,
    required this.clubName,
    required this.age,
    required this.marketValueEur,
    required this.estimatedValueCredits,
    required this.sharePriceCoin,
    required this.movementPct,
    required this.interestScore,
    required this.rating,
    required this.globalScoutingIndex,
    required this.globalScoutingIndexMovementPct,
    required this.isTradable,
    required this.availabilityLabel,
    required this.askingType,
    this.transferListingId,
    this.transferListingStatus,
    this.sellingClubId,
    this.imageUrl,
    this.leagueName,
    this.leagueCountryName,
    this.divisionName,
    this.countryCode,
    this.clubId,
    this.salaryAmount,
    this.contractYearsRemaining,
    this.buyClauseAmount,
    this.loanTerms = const <String, Object?>{},
    this.swapTerms = const <String, Object?>{},
    this.availabilityTerms = const <String, Object?>{},
  });

  final GteMarketPlayerListItem raw;
  final String playerId;
  final String name;
  final String position;
  final String nationality;
  final String clubName;
  final int? age;
  final double? marketValueEur;

  /// Valuation in credits from the value engine. A valuation - it is not
  /// what a trade settles at, and it is never quoted as a price.
  final double? estimatedValueCredits;

  /// `PlayerShareMarket.share_price_coin`: the coin amount one share settles
  /// at. Null when the player has no issued share market.
  final double? sharePriceCoin;

  /// Movement of the *valuation*, from the backend's own movement figure.
  /// It is not a share-price move, and nothing here labels it as one.
  final double? movementPct;
  final int? interestScore;
  final double? rating;
  final double? globalScoutingIndex;
  final double? globalScoutingIndexMovementPct;
  final bool isTradable;
  final String availabilityLabel;
  final String askingType;
  final String? transferListingId;
  final String? transferListingStatus;
  final String? sellingClubId;
  final String? imageUrl;
  final String? leagueName;
  final String? leagueCountryName;
  final String? divisionName;
  final String? countryCode;
  final String? clubId;
  final double? salaryAmount;
  final double? contractYearsRemaining;
  final double? buyClauseAmount;
  final Map<String, Object?> loanTerms;
  final Map<String, Object?> swapTerms;
  final Map<String, Object?> availabilityTerms;

  factory GtexMarketPlayerView.fromListItem(GteMarketPlayerListItem player) {
    return GtexMarketPlayerView(
      raw: player,
      playerId: player.playerId,
      name: player.playerName,
      position:
          player.position?.trim().isNotEmpty == true
              ? player.position!.trim()
              : 'TBC',
      nationality:
          player.nationality?.trim().isNotEmpty == true
              ? player.nationality!.trim()
              : 'Unknown nationality',
      clubName:
          player.currentClubName?.trim().isNotEmpty == true
              ? player.currentClubName!.trim()
              : 'Unattached / unknown club',
      age: player.age,
      marketValueEur: player.marketValueEur,
      estimatedValueCredits: player.currentValueCredits,
      sharePriceCoin: player.sharePriceCoin,
      movementPct: player.movementPct,
      interestScore: player.marketInterestScore,
      rating: player.averageRating,
      globalScoutingIndex: player.globalScoutingIndex,
      globalScoutingIndexMovementPct: player.globalScoutingIndexMovementPct,
      isTradable: player.isTradable,
      availabilityLabel: player.availabilityLabel,
      askingType: player.askingType,
      transferListingId: player.transferListingId,
      transferListingStatus: player.transferListingStatus,
      sellingClubId: player.sellingClubId,
      imageUrl: player.imageUrl,
      leagueName: player.currentCompetitionName,
      leagueCountryName: player.currentCompetitionCountryName,
      divisionName: player.currentDivisionName,
      countryCode: player.nationalityCode,
      clubId: player.currentClubId,
      salaryAmount: player.salaryAmount,
      contractYearsRemaining: player.contractYearsRemaining,
      buyClauseAmount: player.buyClauseAmount,
      loanTerms: player.loanTerms,
      swapTerms: player.swapTerms,
      availabilityTerms: player.availabilityTerms,
    );
  }

  bool get hasImage => imageUrl != null && imageUrl!.trim().isNotEmpty;
  bool get hasOpenTransferListing =>
      transferListingId != null && transferListingId!.trim().isNotEmpty;
  bool get isRising => (movementPct ?? 0) > 0;
  bool get isFalling => (movementPct ?? 0) < 0;
  bool get hasMovement => movementPct != null;

  /// Global Scouting Index direction, from the backend's own GSI movement
  /// figure. Null movement is not treated as a direction.
  bool get isGsiRising => (globalScoutingIndexMovementPct ?? 0) > 0;
  bool get isGsiFalling => (globalScoutingIndexMovementPct ?? 0) < 0;

  /// An opportunity is a player the market price *and* the scouting index
  /// agree is trending up. Both inputs are real backend signals; when either
  /// is missing the player is simply not an opportunity rather than a guess.
  bool get isOpportunity =>
      isRising &&
      isGsiRising &&
      movementPct != null &&
      globalScoutingIndexMovementPct != null;

  /// The tradable price, in GTEX Coin. This is the only number in the Market
  /// that a buy or sell settles at, and the only one the card quotes.
  String get sharePriceLabel => GtexMarketFormatters.coin(sharePriceCoin);

  /// The canonical valuation, preferring the ingested EUR figure and falling
  /// back to the value engine's credits. Null when neither exists - an
  /// unknown valuation is never rendered as zero.
  String? get estimatedValueLabel {
    if (marketValueEur != null) {
      return GtexMarketFormatters.euros(marketValueEur);
    }
    if (estimatedValueCredits != null) {
      return GtexMarketFormatters.credits(estimatedValueCredits);
    }
    return null;
  }

  /// The valuation and its movement in one chip, explicitly named "Value" so
  /// it can never be read as the price standing next to it.
  String? get valueBadgeLabel {
    final String? value = estimatedValueLabel;
    if (value == null) {
      return null;
    }
    final String? movement = valueMovementLabel;
    return movement == null ? 'Value $value' : 'Value $value $movement';
  }
  String get ageLabel => age == null || age! <= 0 ? 'Age TBC' : 'Age $age';
  String? get heightLabel =>
      raw.heightCm == null || raw.heightCm! <= 0 ? null : '${raw.heightCm} cm';
  String? get footLabel {
    final String? foot = raw.preferredFoot?.trim();
    if (foot == null || foot.isEmpty) {
      return null;
    }
    return foot[0].toUpperCase() + foot.substring(1).toLowerCase();
  }

  List<String> get secondaryPositions => raw.secondaryPositions;
  int? get gsiScore => globalScoutingIndex?.round();
  String? get gsiLabel =>
      globalScoutingIndex == null
          ? null
          : 'GSI ${globalScoutingIndex!.round()}';
  String? get gsiTierLabel {
    final int? score = gsiScore;
    if (score == null) return null;
    if (score >= 90) return 'Elite GSI';
    if (score >= 82) return 'High-grade GSI';
    if (score >= 74) return 'First-team GSI';
    if (score >= 66) return 'Developing GSI';
    return 'Prospect GSI';
  }

  String? get gsiTrendLabel {
    final double? value = globalScoutingIndexMovementPct;
    if (value == null) return null;
    final String prefix = value > 0 ? '+' : '';
    return 'GSI $prefix${value.toStringAsFixed(1)}%';
  }

  String get gsiDetailLabel {
    final int? score = gsiScore;
    if (score == null) return 'GSI TBC';
    final String? tier = gsiTierLabel;
    return tier == null ? 'GSI $score' : 'GSI $score - $tier';
  }

  String get ratingLabel =>
      rating == null ? 'Form TBC' : 'Form ${rating!.toStringAsFixed(1)}';
  String get availabilityTypeLabel =>
      availabilityLabel.trim().isNotEmpty
          ? availabilityLabel.trim()
          : GtexMarketFormatters.labelFromToken(askingType);

  /// Signed value movement, or null when the backend has no movement for
  /// this player. A missing movement is not a flat one: rendering "0.0%"
  /// would assert a price history that does not exist.
  String? get valueMovementLabel {
    final double? value = movementPct;
    if (value == null) {
      return null;
    }
    final String prefix = value > 0 ? '+' : '';
    return '$prefix${value.toStringAsFixed(1)}%';
  }

  /// Age as a fact rather than a placeholder - null when it is unknown, so
  /// callers can omit it instead of printing "Age TBC" into a dense row.
  String? get ageValueLabel => age == null || age! <= 0 ? null : '$age yrs';

  /// Market attention, straight from the backend's interest score. Only
  /// surfaced once there is genuine interest to report.
  String? get interestLabel {
    final int? score = interestScore;
    if (score == null || score <= 0) {
      return null;
    }
    return 'Watched $score';
  }

  String get leagueLabel =>
      leagueName?.trim().isNotEmpty == true
          ? leagueName!.trim()
          : 'League metadata pending';
  String get leagueDetailLabel {
    final String league = leagueLabel;
    final String? country = leagueCountryName?.trim();
    if (country == null ||
        country.isEmpty ||
        league.toLowerCase().contains(country.toLowerCase())) {
      return league;
    }
    return '$league ($country)';
  }

  String get divisionLabel =>
      divisionName?.trim().isNotEmpty == true
          ? divisionName!.trim()
          : 'Division metadata pending';
}

class GtexMarketBrowseOption {
  const GtexMarketBrowseOption({
    required this.id,
    required this.label,
    required this.count,
    this.subtitle,
    this.parentId,
    this.countryId,
    this.leagueId,
    this.divisionId,
  });

  final String id;
  final String label;
  final int count;
  final String? subtitle;
  final String? parentId;
  final String? countryId;
  final String? leagueId;
  final String? divisionId;
}

class GtexMarketBrowseSummary {
  const GtexMarketBrowseSummary({
    required this.countries,
    required this.leagues,
    required this.divisions,
    required this.clubs,
  });

  final List<GtexMarketBrowseOption> countries;
  final List<GtexMarketBrowseOption> leagues;
  final List<GtexMarketBrowseOption> divisions;
  final List<GtexMarketBrowseOption> clubs;

  factory GtexMarketBrowseSummary.fromPlayers(
    List<GtexMarketPlayerView> players,
  ) {
    return GtexMarketBrowseSummary(
      countries: _options(
        players.map((GtexMarketPlayerView p) => p.nationality),
      ),
      leagues: _options(
        players
            .map((GtexMarketPlayerView p) => p.leagueName)
            .whereType<String>()
            .where((String value) => value.trim().isNotEmpty),
      ),
      divisions: _options(
        players
            .map((GtexMarketPlayerView p) => p.divisionName)
            .whereType<String>()
            .where((String value) => value.trim().isNotEmpty),
      ),
      clubs: _options(players.map((GtexMarketPlayerView p) => p.clubName)),
    );
  }

  factory GtexMarketBrowseSummary.fromCatalog(GteMarketBrowseCatalog catalog) {
    return GtexMarketBrowseSummary(
      countries: _fromCatalogOptions(catalog.countries),
      leagues: _fromCatalogOptions(catalog.leagues),
      divisions: _fromCatalogOptions(catalog.divisions),
      clubs: _fromCatalogOptions(catalog.clubs),
    );
  }

  static List<GtexMarketBrowseOption> _fromCatalogOptions(
    List<GteMarketBrowseOption> options,
  ) {
    return options
        .map(
          (GteMarketBrowseOption option) => GtexMarketBrowseOption(
            id: option.id,
            label: option.label,
            count: option.count,
            subtitle: option.subtitle,
            parentId: option.parentId,
            countryId: option.countryId,
            leagueId: option.leagueId,
            divisionId: option.divisionId,
          ),
        )
        .toList(growable: false);
  }

  static List<GtexMarketBrowseOption> _options(Iterable<String> values) {
    final Map<String, int> counts = <String, int>{};
    for (final String raw in values) {
      final String label = raw.trim();
      if (label.isEmpty) {
        continue;
      }
      counts[label] = (counts[label] ?? 0) + 1;
    }
    final List<MapEntry<String, int>> entries =
        counts.entries.toList()
          ..sort((MapEntry<String, int> a, MapEntry<String, int> b) {
            final int byCount = b.value.compareTo(a.value);
            if (byCount != 0) {
              return byCount;
            }
            return a.key.compareTo(b.key);
          });
    return entries
        .map(
          (MapEntry<String, int> entry) => GtexMarketBrowseOption(
            id: entry.key,
            label: entry.key,
            count: entry.value,
          ),
        )
        .toList(growable: false);
  }
}

class GtexMarketBasketState {
  const GtexMarketBasketState(this.itemsById);

  final Map<String, GtexMarketPlayerView> itemsById;

  List<GtexMarketPlayerView> get items =>
      itemsById.values.toList(growable: false);

  /// Sum of the shortlisted players' *valuations*, in credits. The shortlist
  /// is a negotiation board, not a cart: this is not a purchase cost, and the
  /// surface that renders it says "Shortlist value".
  double get totalCredits => items.fold<double>(
    0,
    (double total, GtexMarketPlayerView player) =>
        total + (player.estimatedValueCredits ?? 0),
  );

  String get totalLabel => GtexMarketFormatters.credits(totalCredits);

  bool contains(String playerId) => itemsById.containsKey(playerId);

  GtexMarketBasketState toggled(GtexMarketPlayerView player) {
    final Map<String, GtexMarketPlayerView> next =
        Map<String, GtexMarketPlayerView>.of(itemsById);
    if (next.containsKey(player.playerId)) {
      next.remove(player.playerId);
    } else {
      next[player.playerId] = player;
    }
    return GtexMarketBasketState(next);
  }

  GtexMarketBasketState removed(String playerId) {
    final Map<String, GtexMarketPlayerView> next =
        Map<String, GtexMarketPlayerView>.of(itemsById)..remove(playerId);
    return GtexMarketBasketState(next);
  }
}

/// Sort orders offered over the loaded market listings.
///
/// Every order is computed from a field the backend already returned for the
/// listing. Like the discovery lanes, this sorts the listings currently
/// loaded rather than issuing a server-side ordered query - the label makes
/// no claim the data cannot keep.
enum GtexMarketSort {
  relevance,
  sharePriceHighToLow,
  sharePriceLowToHigh,
  valueHighToLow,
  valueLowToHigh,
  biggestRisers,
  biggestFallers,
  mostWatched,
  topRated,
}

extension GtexMarketSortX on GtexMarketSort {
  /// Every label names the number it ordered by. "Price" is the tradable
  /// share price and "value" is the valuation: an order that says "price"
  /// while sorting a valuation is the same defect as printing one as the
  /// other, one step removed.
  String get label => switch (this) {
    GtexMarketSort.relevance => 'Market order',
    GtexMarketSort.sharePriceHighToLow => 'Share price: high to low',
    GtexMarketSort.sharePriceLowToHigh => 'Share price: low to high',
    GtexMarketSort.valueHighToLow => 'Estimated value: high to low',
    GtexMarketSort.valueLowToHigh => 'Estimated value: low to high',
    GtexMarketSort.biggestRisers => 'Biggest value risers',
    GtexMarketSort.biggestFallers => 'Biggest value fallers',
    GtexMarketSort.mostWatched => 'Most watched',
    GtexMarketSort.topRated => 'Top rated',
  };

  /// Sorts a nullable numeric key with missing values always last, keeping the
  /// input order among equal keys (stable).
  static List<GtexMarketPlayerView> _byKey(
    List<GtexMarketPlayerView> players,
    double? Function(GtexMarketPlayerView) key, {
    required bool descending,
  }) {
    final List<MapEntry<int, GtexMarketPlayerView>> indexed = <
      MapEntry<int, GtexMarketPlayerView>
    >[
      for (int i = 0; i < players.length; i++) MapEntry<int, GtexMarketPlayerView>(i, players[i]),
    ];
    indexed.sort((
      MapEntry<int, GtexMarketPlayerView> a,
      MapEntry<int, GtexMarketPlayerView> b,
    ) {
      final double? ka = key(a.value);
      final double? kb = key(b.value);
      if (ka == null && kb == null) return a.key.compareTo(b.key);
      if (ka == null) return 1;
      if (kb == null) return -1;
      final int cmp = descending ? kb.compareTo(ka) : ka.compareTo(kb);
      return cmp != 0 ? cmp : a.key.compareTo(b.key);
    });
    return indexed
        .map((MapEntry<int, GtexMarketPlayerView> e) => e.value)
        .toList(growable: false);
  }

  List<GtexMarketPlayerView> applyTo(List<GtexMarketPlayerView> players) {
    switch (this) {
      case GtexMarketSort.relevance:
        return players;
      case GtexMarketSort.sharePriceHighToLow:
        return _byKey(
          players,
          (GtexMarketPlayerView p) => p.sharePriceCoin,
          descending: true,
        );
      case GtexMarketSort.sharePriceLowToHigh:
        return _byKey(
          players,
          (GtexMarketPlayerView p) => p.sharePriceCoin,
          descending: false,
        );
      case GtexMarketSort.valueHighToLow:
        return _byKey(
          players,
          (GtexMarketPlayerView p) => p.estimatedValueCredits,
          descending: true,
        );
      case GtexMarketSort.valueLowToHigh:
        return _byKey(
          players,
          (GtexMarketPlayerView p) => p.estimatedValueCredits,
          descending: false,
        );
      case GtexMarketSort.biggestRisers:
        return _byKey(players, (GtexMarketPlayerView p) => p.movementPct, descending: true);
      case GtexMarketSort.biggestFallers:
        return _byKey(players, (GtexMarketPlayerView p) => p.movementPct, descending: false);
      case GtexMarketSort.mostWatched:
        return _byKey(
          players,
          (GtexMarketPlayerView p) => p.interestScore?.toDouble(),
          descending: true,
        );
      case GtexMarketSort.topRated:
        return _byKey(
          players,
          (GtexMarketPlayerView p) => p.rating,
          descending: true,
        );
    }
  }
}

class GtexMarketFormatters {
  const GtexMarketFormatters._();

  /// The tradable share price, in GTEX Coin.
  ///
  /// Share prices live in a small range, so the exact figure is shown rather
  /// than a compact one - this is the number the user is charged. Above the
  /// range where that stays readable it compacts like every other figure.
  /// A player with no issued share market has no price, and says so.
  static String coin(double? value) {
    if (value == null) {
      return 'No share market';
    }
    if (value.abs() >= 10000) {
      return 'GTEX ${compactNumber(value)}';
    }
    final bool whole = value == value.roundToDouble();
    return 'GTEX ${value.toStringAsFixed(whole ? 0 : 2)}';
  }

  static String credits(double? value) {
    if (value == null) {
      return 'TBD';
    }
    return 'GTEX ${compactNumber(value)}';
  }

  static String euros(double? value) {
    if (value == null) {
      return 'Market value TBD';
    }
    return 'EUR ${compactNumber(value)}';
  }

  static String compactNumber(double value) {
    final double absValue = value.abs();
    if (absValue >= 1000000000) {
      return '${(value / 1000000000).toStringAsFixed(1)}B';
    }
    if (absValue >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (absValue >= 1000) {
      return '${(value / 1000).toStringAsFixed(1)}K';
    }
    return value.toStringAsFixed(0);
  }

  static String labelFromToken(String value) {
    final String normalized = value.trim().replaceAll('_', ' ');
    if (normalized.isEmpty) {
      return 'Pending';
    }
    return normalized
        .split(' ')
        .where((String word) => word.isNotEmpty)
        .map(
          (String word) =>
              '${word[0].toUpperCase()}${word.length == 1 ? '' : word.substring(1)}',
        )
        .join(' ');
  }
}
