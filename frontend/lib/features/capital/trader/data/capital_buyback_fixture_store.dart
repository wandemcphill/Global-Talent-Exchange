import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/trader/data/capital_portfolio_fixture_store.dart';
import 'package:gte_frontend/features/capital/trader/data/capital_trader_fixture_store.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_fixture_store.dart';

class CapitalBuybackFixtureStore {
  CapitalBuybackFixtureStore({
    required this.trader,
    required this.portfolio,
    required this.wallet,
  });

  final CapitalTraderFixtureStore trader;
  final CapitalPortfolioFixtureStore portfolio;
  final CapitalWalletFixtureStore wallet;

  GteAdminBuybackPreview fetchAdminBuybackPreview({
    required String orderId,
    required DateTime now,
  }) {
    final GteOrderRecord order = trader.fetchOrder(orderId);
    final double fairValue =
        order.maxPrice ??
        trader.referencePriceFor(order.playerId, GteOrderSide.sell) ??
        0;
    final double remainingQuantity =
        order.remainingQuantity < 0 ? 0 : order.remainingQuantity;
    final double estimatedP2pTotal = remainingQuantity * fairValue;
    final double payoutRatio = _adminBuybackPayoutRatio(fairValue);
    final double adminUnitPrice = fairValue * payoutRatio;
    final double adminTotal = remainingQuantity * adminUnitPrice;
    final DateTime? windowEndsAt = order.createdAt?.add(
      const Duration(hours: 48),
    );
    final bool windowElapsed =
        windowEndsAt == null || !now.isBefore(windowEndsAt);
    final List<String> reasons = <String>[
      if (order.side != GteOrderSide.sell)
        'Admin quick exit is only available for sell orders.',
      if (!order.canCancel) 'Only open sell orders can use admin quick exit.',
      if (!windowElapsed)
        'P2P remains the default path until ${windowEndsAt.toIso8601String()}.',
    ];
    return GteAdminBuybackPreview(
      orderId: order.id,
      playerId: order.playerId,
      eligible: reasons.isEmpty,
      reasons: reasons,
      message:
          'P2P listings usually pay more. Admin quick exit is a lower fallback after the priority window ends.',
      country: 'Nigeria',
      fairValue: fairValue,
      estimatedP2pUnitPrice: fairValue,
      estimatedP2pTotal: estimatedP2pTotal,
      adminUnitPrice: adminUnitPrice,
      adminTotal: adminTotal,
      payoutRatio: payoutRatio,
      liquidityBand: _liquidityBandForPrice(fairValue),
      payoutBand: _payoutBandForPrice(fairValue),
      p2pPriorityWindowHours: 48,
      p2pPriorityWindowEndsAt: windowEndsAt,
      minimumHoldDays: 7,
      minimumHoldExpiresAt: order.createdAt?.subtract(const Duration(days: 1)),
      holdDaysRemaining: 0,
    );
  }

  GteAdminBuybackExecution executeAdminBuyback({
    required String orderId,
    required DateTime now,
    required DateTime executedAt,
  }) {
    final GteAdminBuybackPreview preview = fetchAdminBuybackPreview(
      orderId: orderId,
      now: now,
    );
    if (!preview.eligible) {
      throw GteApiException(
        type: GteApiErrorType.validation,
        message:
            preview.reasons.isEmpty
                ? 'Admin buyback is unavailable.'
                : preview.reasons.first,
      );
    }
    late final GteOrderRecord existing;
    final GteOrderRecord updated = trader.updateOrder(orderId, (
      GteOrderRecord current,
    ) {
      existing = current;
      return GteOrderRecord(
        id: current.id,
        userId: current.userId,
        playerId: current.playerId,
        side: current.side,
        status: GteOrderStatus.filled,
        quantity: current.quantity,
        filledQuantity: current.quantity,
        remainingQuantity: 0.0,
        maxPrice: current.maxPrice,
        reservedAmount: 0.0,
        currency: current.currency,
        holdTransactionId: current.holdTransactionId,
        createdAt: current.createdAt,
        updatedAt: executedAt,
        executionSummary: current.executionSummary,
      );
    });
    wallet.creditCoin(
      amount: preview.adminTotal,
      reason: 'admin_buyback_settlement',
      description: 'Admin quick exit credited for ${existing.playerId}',
      createdAt: executedAt,
    );
    portfolio.adjustHoldingQuantity(
      existing.playerId,
      -existing.remainingQuantity,
      currentPrice: preview.fairValue,
    );
    portfolio.rebuildPortfolioSummary();
    return GteAdminBuybackExecution(
      preview: preview,
      order: updated,
      quantity: existing.remainingQuantity,
      unitPrice: preview.adminUnitPrice,
      total: preview.adminTotal,
      executedAt: executedAt,
    );
  }
}

String _liquidityBandForPrice(double fairValue) {
  if (fairValue >= 1000) {
    return 'marquee';
  }
  if (fairValue >= 400) {
    return 'bluechip';
  }
  if (fairValue >= 150) {
    return 'premium';
  }
  if (fairValue >= 50) {
    return 'growth';
  }
  return 'entry';
}

String _payoutBandForPrice(double fairValue) {
  switch (_liquidityBandForPrice(fairValue)) {
    case 'entry':
      return 'A';
    case 'growth':
      return 'B';
    case 'premium':
      return 'C';
    case 'bluechip':
      return 'D';
    case 'marquee':
      return 'E';
  }
  return 'C';
}

double _adminBuybackPayoutRatio(double fairValue) {
  switch (_payoutBandForPrice(fairValue)) {
    case 'A':
      return 0.45;
    case 'B':
      return 0.58;
    case 'C':
      return 0.66;
    case 'D':
      return 0.72;
    case 'E':
      return 0.75;
  }
  return 0.66;
}
