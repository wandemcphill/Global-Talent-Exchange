import 'package:gte_frontend/data/gte_models.dart';

import 'capital_wallet_availability.dart';

class CapitalWalletDisplaySnapshot {
  const CapitalWalletDisplaySnapshot({
    required this.availableBalance,
    required this.reservedBalance,
    required this.lockedBalance,
    required this.totalBalance,
    required this.currency,
    this.pendingWithdrawalBalance,
    this.lockReasons = const <String>[],
  });

  final double availableBalance;
  final double reservedBalance;
  final double lockedBalance;
  final double totalBalance;
  final GteLedgerUnit currency;
  final double? pendingWithdrawalBalance;
  final List<String> lockReasons;

  bool get hasAvailableBalance => availableBalance > 0;
  bool get hasLockedBalance => lockedBalance > 0 || lockReasons.isNotEmpty;
  bool get hasPendingWithdrawals => (pendingWithdrawalBalance ?? 0) > 0;
  String get currencyCode => currency.name.toUpperCase();

  factory CapitalWalletDisplaySnapshot.fromSummary(GteWalletSummary summary) {
    return CapitalWalletDisplaySnapshot(
      availableBalance: summary.availableBalance,
      reservedBalance: summary.reservedBalance,
      lockedBalance: summary.lockedBalance,
      totalBalance: summary.totalBalance,
      currency: summary.currency,
      lockReasons: summary.lockReasons,
    );
  }

  factory CapitalWalletDisplaySnapshot.fromAvailability(
    CapitalWalletAvailability availability,
  ) {
    final double? totalBalance = availability.totalBalanceCoin;
    if (totalBalance == null) {
      throw StateError(
        'Capital wallet display requires backend-derived total balance.',
      );
    }
    return CapitalWalletDisplaySnapshot(
      availableBalance: availability.availableBalanceCoin,
      reservedBalance: availability.reservedBalanceCoin,
      lockedBalance: availability.lockedBalanceCoin,
      totalBalance: totalBalance,
      currency: availability.currency,
      pendingWithdrawalBalance: availability.pendingWithdrawalBalanceCoin,
      lockReasons: availability.lockReasons,
    );
  }
}
