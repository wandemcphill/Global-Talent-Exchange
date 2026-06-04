import 'dart:math' as math;

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_fixture_store.dart';

class CapitalPortfolioFixtureStore {
  CapitalPortfolioFixtureStore.seeded({required this.wallet})
    : portfolio = GtePortfolioView(
        holdings: List<GtePortfolioHolding>.of(
          seedPortfolioHoldings,
          growable: false,
        ),
      ),
      summary = seedPortfolioSummary;

  final CapitalWalletFixtureStore wallet;
  GtePortfolioView portfolio;
  GtePortfolioSummary summary;

  GtePortfolioView fetchPortfolio() {
    return GtePortfolioView(
      holdings: List<GtePortfolioHolding>.of(
        portfolio.holdings,
        growable: false,
      ),
    );
  }

  GtePortfolioSummary fetchPortfolioSummary() {
    return summary;
  }

  void adjustHoldingQuantity(
    String playerId,
    double deltaQuantity, {
    required double currentPrice,
  }) {
    final List<GtePortfolioHolding> nextHoldings = List<GtePortfolioHolding>.of(
      portfolio.holdings,
      growable: true,
    );
    final int index = nextHoldings.indexWhere(
      (GtePortfolioHolding holding) => holding.playerId == playerId,
    );
    if (index == -1) {
      return;
    }
    final GtePortfolioHolding existing = nextHoldings[index];
    final double nextQuantity = math.max(0, existing.quantity + deltaQuantity);
    if (nextQuantity <= 0) {
      nextHoldings.removeAt(index);
    } else {
      final double marketValue = nextQuantity * currentPrice;
      final double unrealizedPl =
          (currentPrice - existing.averageCost) * nextQuantity;
      final double costBasis = existing.averageCost * nextQuantity;
      nextHoldings[index] = GtePortfolioHolding(
        playerId: existing.playerId,
        quantity: nextQuantity,
        averageCost: existing.averageCost,
        currentPrice: currentPrice,
        marketValue: marketValue,
        unrealizedPl: unrealizedPl,
        unrealizedPlPercent:
            costBasis <= 0 ? 0 : (unrealizedPl / costBasis) * 100,
      );
    }
    portfolio = GtePortfolioView(
      holdings: List<GtePortfolioHolding>.unmodifiable(nextHoldings),
    );
  }

  void rebuildPortfolioSummary() {
    final double totalMarketValue = portfolio.holdings.fold<double>(
      0.0,
      (double sum, GtePortfolioHolding holding) => sum + holding.marketValue,
    );
    final double unrealizedPlTotal = portfolio.holdings.fold<double>(
      0.0,
      (double sum, GtePortfolioHolding holding) => sum + holding.unrealizedPl,
    );
    summary = GtePortfolioSummary(
      totalMarketValue: totalMarketValue,
      cashBalance: wallet.coinSummary.availableBalance,
      totalEquity: totalMarketValue + wallet.coinSummary.availableBalance,
      unrealizedPlTotal: unrealizedPlTotal,
      realizedPlTotal: seedPortfolioSummary.realizedPlTotal,
    );
  }

  static const List<GtePortfolioHolding> seedPortfolioHoldings =
      <GtePortfolioHolding>[
        GtePortfolioHolding(
          playerId: 'lamine-yamal',
          quantity: 1,
          averageCost: 1095,
          currentPrice: 1180,
          marketValue: 1180,
          unrealizedPl: 85,
          unrealizedPlPercent: 7.8,
        ),
        GtePortfolioHolding(
          playerId: 'victor-osimhen',
          quantity: 1.2,
          averageCost: 850,
          currentPrice: 920,
          marketValue: 1104,
          unrealizedPl: 84,
          unrealizedPlPercent: 8.2,
        ),
      ];

  static const GtePortfolioSummary seedPortfolioSummary = GtePortfolioSummary(
    totalMarketValue: 2284,
    cashBalance: 1200,
    totalEquity: 3484,
    unrealizedPlTotal: 169,
    realizedPlTotal: 42,
  );
}
