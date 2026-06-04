import 'package:gte_frontend/data/gte_models.dart';

class CapitalWalletAvailability {
  const CapitalWalletAvailability({
    required this.isAvailable,
    required this.availableBalanceCoin,
    required this.reservedBalanceCoin,
    required this.lockedBalanceCoin,
    required this.pendingWithdrawalBalanceCoin,
    this.totalBalanceCoin,
    this.currency = GteLedgerUnit.coin,
    this.blockedReason,
    this.lockReasons = const <String>[],
  });

  final bool isAvailable;
  final double availableBalanceCoin;
  final double reservedBalanceCoin;
  final double lockedBalanceCoin;
  final double pendingWithdrawalBalanceCoin;
  final double? totalBalanceCoin;
  final GteLedgerUnit currency;
  final String? blockedReason;
  final List<String> lockReasons;

  bool get hasBackendEvidence {
    if ((blockedReason ?? '').trim().isNotEmpty || lockReasons.isNotEmpty) {
      return true;
    }
    return availableBalanceCoin != 0 ||
        reservedBalanceCoin != 0 ||
        lockedBalanceCoin != 0 ||
        pendingWithdrawalBalanceCoin != 0 ||
        (totalBalanceCoin ?? 0) != 0;
  }

  bool coversCoinAmount(double amountCoin) {
    return isAvailable && availableBalanceCoin >= amountCoin;
  }

  factory CapitalWalletAvailability.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'capital wallet availability',
    );
    return CapitalWalletAvailability(
      isAvailable: GteJson.requiredBoolean(json, <String>[
        'is_available',
        'isAvailable',
        'can_afford',
        'canAfford',
        'can_pay_with_wallet',
        'canPayWithWallet',
        'wallet_available',
        'walletAvailable',
      ]),
      availableBalanceCoin: GteJson.requiredNumber(json, <String>[
        'available_balance_coin',
        'availableBalanceCoin',
        'available_balance',
        'availableBalance',
      ]),
      reservedBalanceCoin: GteJson.requiredNumber(json, <String>[
        'reserved_balance_coin',
        'reservedBalanceCoin',
        'reserved_balance',
        'reservedBalance',
      ]),
      lockedBalanceCoin: GteJson.requiredNumber(json, <String>[
        'locked_balance_coin',
        'lockedBalanceCoin',
        'locked_balance',
        'lockedBalance',
      ]),
      pendingWithdrawalBalanceCoin: GteJson.requiredNumber(json, <String>[
        'pending_withdrawal_balance_coin',
        'pendingWithdrawalBalanceCoin',
        'pending_withdrawal_balance',
        'pendingWithdrawalBalance',
      ]),
      totalBalanceCoin: _numberOrNull(json, <String>[
        'total_balance_coin',
        'totalBalanceCoin',
        'total_balance',
        'totalBalance',
      ]),
      currency: _ledgerUnitFromJson(json),
      blockedReason: GteJson.stringOrNull(json, <String>[
        'blocked_reason',
        'blockedReason',
        'reason',
      ]),
      lockReasons: _stringList(json, <String>['lock_reasons', 'lockReasons']),
    );
  }

  factory CapitalWalletAvailability.fromWalletSummary(
    GteWalletSummary summary, {
    double pendingWithdrawalBalanceCoin = 0,
    bool? isAvailable,
    String? blockedReason,
  }) {
    return CapitalWalletAvailability(
      isAvailable: isAvailable ?? summary.availableBalance > 0,
      availableBalanceCoin: summary.availableBalance,
      reservedBalanceCoin: summary.reservedBalance,
      lockedBalanceCoin: summary.lockedBalance,
      pendingWithdrawalBalanceCoin: pendingWithdrawalBalanceCoin,
      totalBalanceCoin: summary.totalBalance,
      currency: summary.currency,
      blockedReason: blockedReason,
      lockReasons: summary.lockReasons,
    );
  }

  factory CapitalWalletAvailability.fromWalletOverview(
    GteWalletOverview overview,
  ) {
    final String? policyReason = overview.policyBlockReason?.trim();
    return CapitalWalletAvailability(
      isAvailable:
          !overview.policyBlocked &&
          overview.availableBalance > 0 &&
          overview.withdrawableNow >= 0,
      availableBalanceCoin: overview.availableBalance,
      reservedBalanceCoin: overview.reservedBalance,
      lockedBalanceCoin: overview.lockedBalance,
      pendingWithdrawalBalanceCoin: overview.pendingWithdrawals,
      currency: overview.currency,
      blockedReason:
          policyReason == null || policyReason.isEmpty ? null : policyReason,
      lockReasons: overview.lockReasons,
    );
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'is_available': isAvailable,
    'available_balance_coin': availableBalanceCoin,
    'reserved_balance_coin': reservedBalanceCoin,
    'locked_balance_coin': lockedBalanceCoin,
    'pending_withdrawal_balance_coin': pendingWithdrawalBalanceCoin,
    if (totalBalanceCoin != null) 'total_balance_coin': totalBalanceCoin,
    'currency': currency.name,
    if ((blockedReason ?? '').trim().isNotEmpty)
      'blocked_reason': blockedReason!.trim(),
    if (lockReasons.isNotEmpty) 'lock_reasons': lockReasons,
  };
}

GteLedgerUnit _ledgerUnitFromJson(Map<String, Object?> json) {
  final String raw =
      GteJson.stringOrNull(json, <String>[
        'currency',
        'unit',
      ])?.trim().toLowerCase() ??
      GteLedgerUnit.coin.name;
  for (final GteLedgerUnit unit in GteLedgerUnit.values) {
    if (unit.name.toLowerCase() == raw) {
      return unit;
    }
  }
  return GteLedgerUnit.coin;
}

List<String> _stringList(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue == null) {
    return const <String>[];
  }
  if (rawValue is Iterable) {
    return rawValue
        .map((Object? value) => value?.toString().trim() ?? '')
        .where((String value) => value.isNotEmpty)
        .toList(growable: false);
  }
  if (rawValue is Map) {
    return rawValue.values
        .where(
          (Object? value) =>
              value != null &&
              value is! Iterable &&
              value is! Map &&
              value.toString().trim().isNotEmpty,
        )
        .map((Object? value) => value.toString().trim())
        .toList(growable: false);
  }
  final String parsed = rawValue.toString().trim();
  return parsed.isEmpty ? const <String>[] : <String>[parsed];
}

double? _numberOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? value = GteJson.value(json, keys);
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}
