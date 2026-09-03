import 'package:flutter/foundation.dart';

/// One club in which the signed-in user holds ownership shares, valued at the
/// live club-token price.
///
/// This is the model PHASE4-D publishes for PHASE4-B to fold into the portfolio
/// surface as an explicitly-labelled club-ownership section. Every derived ratio
/// is `null` — never `0` — when its denominator is genuinely unknown, so the
/// interface can state "unknown" rather than imply a real zero.
@immutable
class GtexClubShareHolding {
  const GtexClubShareHolding({
    required this.clubId,
    required this.clubName,
    required this.sharesOwned,
    required this.averagePriceCoin,
    required this.sharePriceCoin,
    required this.marketValueCoin,
    required this.costBasisCoin,
    required this.unrealizedPlCoin,
    this.unrealizedPlPercent,
    this.ownershipPercent,
    this.holderCount = 0,
    this.circulatingSupply = 0,
    this.totalSupply = 0,
    this.rewardSharesEarned = 0,
    this.performanceScore,
    this.winRate,
    this.fanDemandScore,
    this.treasuryBalanceCoin,
    this.governanceEnabled = false,
  });

  factory GtexClubShareHolding.fromJson(Map<String, dynamic> json) {
    return GtexClubShareHolding(
      clubId: (json['club_id'] as Object?)?.toString() ?? '',
      clubName: (json['club_name'] as Object?)?.toString() ?? '',
      sharesOwned: _int(json['tokens_owned']),
      averagePriceCoin: _double(json['avg_price_coin']),
      sharePriceCoin: _double(json['share_price_coin']),
      marketValueCoin: _double(json['market_value_coin']),
      costBasisCoin: _double(json['cost_basis_coin']),
      unrealizedPlCoin: _double(json['unrealized_pl_coin']),
      unrealizedPlPercent: _doubleOrNull(json['unrealized_pl_pct']),
      ownershipPercent: _doubleOrNull(json['ownership_pct']),
      holderCount: _int(json['holder_count']),
      circulatingSupply: _int(json['circulating_supply']),
      totalSupply: _int(json['total_supply']),
      rewardSharesEarned: _int(json['reward_tokens_earned']),
      performanceScore: _doubleOrNull(json['performance_score']),
      winRate: _doubleOrNull(json['win_rate']),
      fanDemandScore: _doubleOrNull(json['fan_demand_score']),
      treasuryBalanceCoin: _doubleOrNull(json['treasury_balance_coin']),
      governanceEnabled: json['governance_enabled'] == true,
    );
  }

  final String clubId;
  final String clubName;
  final int sharesOwned;
  final double averagePriceCoin;
  final double sharePriceCoin;
  final double marketValueCoin;
  final double costBasisCoin;
  final double unrealizedPlCoin;
  final double? unrealizedPlPercent;
  final double? ownershipPercent;
  final int holderCount;
  final int circulatingSupply;
  final int totalSupply;
  final int rewardSharesEarned;

  /// Backend club-token performance signal in `[-1, 1]`-ish space. `null` when
  /// the club has never had a settled GTEX match — the UI must not draw a
  /// neutral bar that implies it has played.
  final double? performanceScore;
  final double? winRate;
  final double? fanDemandScore;
  final double? treasuryBalanceCoin;
  final bool governanceEnabled;

  bool get isInProfit => unrealizedPlCoin > 0;
  bool get isFlat => unrealizedPlCoin == 0;

  /// True only when the club has a settled-match performance history behind its
  /// share price. Anything else and the UI must not claim performance is driving
  /// the value.
  bool get hasPerformanceHistory {
    final double? score = performanceScore;
    final double? rate = winRate;
    return (score != null && score != 0) || (rate != null && rate != 0);
  }
}

/// The user's whole club-ownership book, already aggregated by the backend.
@immutable
class GtexClubOwnershipPortfolio {
  const GtexClubOwnershipPortfolio({
    required this.clubCount,
    required this.totalMarketValueCoin,
    required this.totalCostBasisCoin,
    required this.totalUnrealizedPlCoin,
    required this.holdings,
  });

  /// The honest empty book, used when the portfolio could not be loaded. It
  /// reports nothing held rather than inventing a position.
  factory GtexClubOwnershipPortfolio.empty() =>
      const GtexClubOwnershipPortfolio(
        clubCount: 0,
        totalMarketValueCoin: 0,
        totalCostBasisCoin: 0,
        totalUnrealizedPlCoin: 0,
        holdings: <GtexClubShareHolding>[],
      );

  factory GtexClubOwnershipPortfolio.fromJson(Map<String, dynamic> json) {
    final Object? rawHoldings = json['holdings'];
    return GtexClubOwnershipPortfolio(
      clubCount: _int(json['club_count']),
      totalMarketValueCoin: _double(json['total_market_value_coin']),
      totalCostBasisCoin: _double(json['total_cost_basis_coin']),
      totalUnrealizedPlCoin: _double(json['total_unrealized_pl_coin']),
      holdings:
          rawHoldings is List
              ? rawHoldings
                  .whereType<Map<String, dynamic>>()
                  .map(GtexClubShareHolding.fromJson)
                  .toList(growable: false)
              : const <GtexClubShareHolding>[],
    );
  }

  final int clubCount;
  final double totalMarketValueCoin;
  final double totalCostBasisCoin;
  final double totalUnrealizedPlCoin;
  final List<GtexClubShareHolding> holdings;

  bool get isEmpty => holdings.isEmpty;
  bool get isInProfit => totalUnrealizedPlCoin > 0;
}

int _int(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _double(Object? value) => _doubleOrNull(value) ?? 0;

double? _doubleOrNull(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '');
}
