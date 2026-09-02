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
    required this.price,
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
  final double? price;
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
      price: player.currentValueCredits,
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

  String get priceLabel =>
      marketValueEur == null
          ? GtexMarketFormatters.credits(price)
          : GtexMarketFormatters.euros(marketValueEur);
  String get internalPriceLabel => GtexMarketFormatters.credits(price);
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
  String? get movementLabel {
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

  double get totalCredits => items.fold<double>(
    0,
    (double total, GtexMarketPlayerView player) => total + (player.price ?? 0),
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

class GtexMarketFormatters {
  const GtexMarketFormatters._();

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
