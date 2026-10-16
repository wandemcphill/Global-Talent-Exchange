import 'package:flutter/foundation.dart';

import '../../data/gte_models.dart';

/// The signed-in user's economic stake in one player.
///
/// PHASE4-B publishes this from `GET /api/portfolio`; PHASE4-A / C / D / F read
/// it to badge a player as owned. Only B writes it.
///
/// Every derived ratio is `null` — never `0` — when its denominator is
/// genuinely unknown, so a consumer can state "unknown" instead of implying a
/// real zero (P6).
@immutable
class GtexOwnershipStake {
  const GtexOwnershipStake({
    required this.playerId,
    required this.quantity,
    required this.averageCost,
    required this.marketValue,
    required this.unrealizedPl,
    this.unrealizedPlPercent,
    this.currentPrice,
    this.playerName,
    this.clubName,
  });

  /// Builds a stake from a portfolio holding. `unrealizedPlPercent` is dropped
  /// to `null` when there is no cost basis to divide by, and `currentPrice` is
  /// dropped when the mark could not be resolved (backend sends `0`).
  factory GtexOwnershipStake.fromHolding(GtePortfolioHolding holding) {
    final double costBasis = holding.averageCost * holding.quantity;
    return GtexOwnershipStake(
      playerId: holding.playerId,
      quantity: holding.quantity,
      averageCost: holding.averageCost,
      marketValue: holding.marketValue,
      unrealizedPl: holding.unrealizedPl,
      unrealizedPlPercent: costBasis > 0 ? holding.unrealizedPlPercent : null,
      currentPrice: holding.currentPrice > 0 ? holding.currentPrice : null,
      playerName: holding.playerName,
      clubName: holding.clubName,
    );
  }

  final String playerId;
  final double quantity;
  final double averageCost;
  final double marketValue;
  final double unrealizedPl;

  /// `null` — never `0` — when there is no cost basis behind the position.
  final double? unrealizedPlPercent;

  /// The live mark, or `null` when the backend could not resolve a price.
  final double? currentPrice;

  final String? playerName;
  final String? clubName;

  double get costBasis => averageCost * quantity;
  bool get isInProfit => unrealizedPl > 0;
  bool get isFlat => unrealizedPl == 0;

  /// A quantity string with no trailing `.00` noise: `2`, `2.5`, `0.25`.
  String get quantityLabel {
    if (quantity == quantity.roundToDouble()) {
      return quantity.toStringAsFixed(0);
    }
    return quantity
        .toStringAsFixed(2)
        .replaceFirst(RegExp(r'0$'), '')
        .replaceFirst(RegExp(r'\.$'), '');
  }

  /// e.g. `"You own 2.5 shares"` — the label B contributes to the canonical
  /// player card (§4.1).
  String get ownershipLabel {
    final String qty = quantityLabel;
    return 'You own $qty share${qty == '1' ? '' : 's'}';
  }
}

/// A read-only lookup of the user's player stakes, keyed by player id.
@immutable
class GtexOwnershipBook {
  const GtexOwnershipBook(this._stakes);

  factory GtexOwnershipBook.empty() =>
      const GtexOwnershipBook(<String, GtexOwnershipStake>{});

  factory GtexOwnershipBook.fromPortfolio(GtePortfolioView? portfolio) {
    if (portfolio == null || portfolio.holdings.isEmpty) {
      return GtexOwnershipBook.empty();
    }
    return GtexOwnershipBook(<String, GtexOwnershipStake>{
      for (final GtePortfolioHolding holding in portfolio.holdings)
        holding.playerId: GtexOwnershipStake.fromHolding(holding),
    });
  }

  final Map<String, GtexOwnershipStake> _stakes;

  GtexOwnershipStake? stakeFor(String playerId) => _stakes[playerId];
  bool owns(String playerId) => _stakes.containsKey(playerId);
  Iterable<GtexOwnershipStake> get stakes => _stakes.values;
  int get length => _stakes.length;
  bool get isEmpty => _stakes.isEmpty;
  bool get isNotEmpty => _stakes.isNotEmpty;
}
