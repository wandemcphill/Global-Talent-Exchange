part of 'package:gte_frontend/data/gte_models.dart';

enum GteLedgerUnit { credit, coin, unknown }

String _walletLockReasonText(Object? value) {
  if (value == null) {
    return '';
  }
  if (value is Map) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet lock reason',
    );
    final String? message = GteJson.stringOrNull(json, <String>['message']);
    final String? label = GteJson.stringOrNull(json, <String>['label']);
    final String? amount = GteJson.value(json, <String>['amount'])?.toString();
    final String? currency = GteJson.stringOrNull(json, <String>['currency']);
    final String? reference = GteJson.stringOrNull(json, <String>[
      'reference',
      'audit_reference',
      'auditReference',
    ]);
    String text =
        message ??
        [
          if (label != null) label,
          if (amount != null && amount.trim().isNotEmpty)
            '${amount.trim()}${currency == null ? '' : ' ${currency.trim()}'}',
        ].join(': ');
    if (text.trim().isEmpty) {
      text = reference ?? '';
    } else if (reference != null && !text.contains(reference)) {
      text = '$text | Ref $reference';
    }
    return text.trim();
  }
  return value.toString().trim();
}

const Set<String> _canonicalWalletPaymentProviderKeys = <String>{
  'bank_transfer_manual',
  'korapay',
};

Map<String, String> _canonicalWalletProviderStatus(
  Map<String, Object?> providerStatusJson,
) {
  final Map<String, String> normalized = <String, String>{};
  for (final MapEntry<String, Object?> entry in providerStatusJson.entries) {
    final String key = entry.key.trim().toLowerCase();
    if (!_canonicalWalletPaymentProviderKeys.contains(key)) {
      throw GteParsingException(
        'Wallet overview exposed non-canonical payment provider "$key".',
        providerStatusJson,
      );
    }
    normalized[key] = entry.value?.toString() ?? 'unknown';
  }
  return Map<String, String>.unmodifiable(normalized);
}

class GteWalletSummary {
  const GteWalletSummary({
    required this.availableBalance,
    required this.reservedBalance,
    this.lockedBalance = 0,
    this.lockReasons = const <String>[],
    required this.totalBalance,
    required this.currency,
  });

  final double availableBalance;
  final double reservedBalance;
  final double lockedBalance;
  final List<String> lockReasons;
  final double totalBalance;
  final GteLedgerUnit currency;

  factory GteWalletSummary.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet summary',
    );
    return GteWalletSummary(
      availableBalance: GteJson.requiredNumber(json, <String>[
        'available_balance',
        'availableBalance',
      ]),
      reservedBalance: GteJson.requiredNumber(json, <String>[
        'reserved_balance',
        'reservedBalance',
      ]),
      lockedBalance: GteJson.requiredNumber(json, <String>[
        'locked_balance',
        'lockedBalance',
      ]),
      lockReasons: GteJson.typedList<String>(
        json,
        <String>['lock_reasons', 'lockReasons'],
        _walletLockReasonText,
      ).where((String item) => item.trim().isNotEmpty).toList(growable: false),
      totalBalance: GteJson.requiredNumber(json, <String>[
        'total_balance',
        'totalBalance',
      ]),
      currency: _ledgerUnitFromString(
        GteJson.string(json, <String>['currency']),
      ),
    );
  }
}

class GteWalletLedgerEntry {
  const GteWalletLedgerEntry({
    required this.id,
    required this.amount,
    required this.reason,
    required this.description,
    required this.createdAt,
  });

  final String id;
  final double amount;
  final String reason;
  final String? description;
  final DateTime? createdAt;

  factory GteWalletLedgerEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet ledger entry',
    );
    return GteWalletLedgerEntry(
      id: GteJson.string(json, <String>['id']),
      amount: GteJson.requiredNumber(json, <String>['amount']),
      reason: GteJson.string(json, <String>['reason']),
      description: GteJson.stringOrNull(json, <String>['description']),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
    );
  }
}

class GteWalletLedgerPage {
  const GteWalletLedgerPage({
    required this.page,
    required this.pageSize,
    required this.total,
    required this.items,
  });

  final int page;
  final int pageSize;
  final int total;
  final List<GteWalletLedgerEntry> items;

  factory GteWalletLedgerPage.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet ledger page',
    );
    return GteWalletLedgerPage(
      page: GteJson.integer(json, <String>['page'], fallback: 1),
      pageSize: GteJson.integer(json, <String>[
        'page_size',
        'pageSize',
      ], fallback: 20),
      total: GteJson.requiredInteger(json, <String>['total']),
      items: GteJson.typedList(json, <String>[
        'items',
      ], GteWalletLedgerEntry.fromJson),
    );
  }
}

class GteWalletOverview {
  const GteWalletOverview({
    required this.availableBalance,
    this.reservedBalance = 0,
    this.lockedBalance = 0,
    this.lockReasons = const <String>[],
    required this.pendingDeposits,
    required this.pendingWithdrawals,
    required this.totalInflow,
    required this.totalOutflow,
    required this.withdrawableNow,
    required this.currency,
    this.countryCode,
    this.requiredPolicyAcceptancesMissing = 0,
    this.policyBlocked = false,
    this.policyBlockReason,
    this.depositMode = 'unavailable',
    this.withdrawalMode = 'unavailable',
    this.paymentProviderStatus = const <String, String>{},
  });

  final double availableBalance;
  final double reservedBalance;
  final double lockedBalance;
  final List<String> lockReasons;
  final double pendingDeposits;
  final double pendingWithdrawals;
  final double totalInflow;
  final double totalOutflow;
  final double withdrawableNow;
  final GteLedgerUnit currency;
  final String? countryCode;
  final int requiredPolicyAcceptancesMissing;
  final bool policyBlocked;
  final String? policyBlockReason;
  final String depositMode;
  final String withdrawalMode;
  final Map<String, String> paymentProviderStatus;

  factory GteWalletOverview.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet overview',
    );
    final Map<String, Object?> providerStatusJson = GteJson.map(
      GteJson.value(json, <String>[
        'payment_provider_status',
        'paymentProviderStatus',
      ]),
      label: 'wallet provider status',
    );
    return GteWalletOverview(
      availableBalance: GteJson.requiredNumber(json, <String>[
        'available_balance',
        'availableBalance',
      ]),
      reservedBalance: GteJson.requiredNumber(json, <String>[
        'reserved_balance',
        'reservedBalance',
      ]),
      lockedBalance: GteJson.requiredNumber(json, <String>[
        'locked_balance',
        'lockedBalance',
      ]),
      lockReasons: GteJson.typedList<String>(
        json,
        <String>['lock_reasons', 'lockReasons'],
        _walletLockReasonText,
      ).where((String item) => item.trim().isNotEmpty).toList(growable: false),
      pendingDeposits: GteJson.requiredNumber(json, <String>[
        'pending_deposits',
        'pendingDeposits',
      ]),
      pendingWithdrawals: GteJson.requiredNumber(json, <String>[
        'pending_withdrawal_balance',
        'pendingWithdrawalBalance',
      ]),
      totalInflow: GteJson.requiredNumber(json, <String>[
        'total_inflow',
        'totalInflow',
      ]),
      totalOutflow: GteJson.requiredNumber(json, <String>[
        'total_outflow',
        'totalOutflow',
      ]),
      withdrawableNow: GteJson.requiredNumber(json, <String>[
        'withdrawable_now',
        'withdrawableNow',
      ]),
      currency: _ledgerUnitFromString(
        GteJson.string(json, <String>['currency']),
      ),
      countryCode: GteJson.stringOrNull(json, <String>[
        'country_code',
        'countryCode',
      ]),
      requiredPolicyAcceptancesMissing: GteJson.requiredInteger(json, <String>[
        'required_policy_acceptances_missing',
        'requiredPolicyAcceptancesMissing',
      ]),
      policyBlocked: GteJson.requiredBoolean(json, <String>[
        'policy_blocked',
        'policyBlocked',
      ]),
      policyBlockReason: GteJson.stringOrNull(json, <String>[
        'policy_block_reason',
        'policyBlockReason',
      ]),
      depositMode: GteJson.string(json, <String>[
        'deposit_mode',
        'depositMode',
      ], fallback: 'unavailable'),
      withdrawalMode: GteJson.string(json, <String>[
        'withdrawal_mode',
        'withdrawalMode',
      ], fallback: 'unavailable'),
      paymentProviderStatus: _canonicalWalletProviderStatus(providerStatusJson),
    );
  }
}

class GteUserWallet {
  const GteUserWallet({
    required this.id,
    required this.userId,
    required this.balance,
    required this.currency,
    required this.complianceStatus,
    this.createdAt,
  });

  final String id;
  final String userId;
  final double balance;
  final String currency;
  final String complianceStatus;
  final DateTime? createdAt;

  factory GteUserWallet.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'user wallet');
    return GteUserWallet(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      balance: GteJson.requiredNumber(json, <String>['balance']),
      currency: GteJson.string(json, <String>['currency']),
      complianceStatus: GteJson.string(json, <String>[
        'compliance_status',
        'complianceStatus',
      ], fallback: 'unknown'),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
    );
  }
}

class GteWalletTransactionRecord {
  const GteWalletTransactionRecord({
    required this.id,
    required this.userId,
    required this.type,
    required this.amount,
    required this.status,
    required this.reference,
    this.createdAt,
  });

  final String id;
  final String userId;
  final String type;
  final double amount;
  final String status;
  final String reference;
  final DateTime? createdAt;

  factory GteWalletTransactionRecord.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet transaction',
    );
    return GteWalletTransactionRecord(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      type: GteJson.string(json, <String>['type']),
      amount: GteJson.requiredNumber(json, <String>['amount']),
      status: GteJson.string(json, <String>['status']),
      reference: GteJson.string(json, <String>['reference']),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
    );
  }
}

class GteWalletTopUpSession {
  const GteWalletTopUpSession({
    required this.reference,
    required this.paymentLink,
    required this.amount,
    required this.currency,
    required this.provider,
    required this.status,
    this.mockMode = false,
  });

  final String reference;
  final String paymentLink;
  final double amount;
  final String currency;
  final String provider;
  final String status;
  final bool mockMode;

  factory GteWalletTopUpSession.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet top-up session',
    );
    return GteWalletTopUpSession(
      reference: GteJson.string(json, <String>['reference']),
      paymentLink: GteJson.string(json, <String>[
        'payment_link',
        'paymentLink',
      ]),
      amount: GteJson.requiredNumber(json, <String>['amount']),
      currency: GteJson.string(json, <String>['currency']),
      provider: GteJson.string(json, <String>[
        'provider',
      ], fallback: 'unavailable'),
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      mockMode: GteJson.requiredBoolean(json, <String>[
        'mock_mode',
        'mockMode',
      ]),
    );
  }
}

class GteWalletTopUpInitiateRequest {
  const GteWalletTopUpInitiateRequest({
    required this.amount,
    this.provider = 'korapay',
    this.unit = GteLedgerUnit.coin,
    this.callbackUrl,
  });

  final double amount;
  final String provider;
  final GteLedgerUnit unit;
  final String? callbackUrl;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'amount': amount,
      'provider': provider,
      'unit': unit.name,
      if (callbackUrl != null && callbackUrl!.trim().isNotEmpty)
        'callback_url': callbackUrl!.trim(),
    };
  }
}

class GteWalletTopUpVerificationResult {
  const GteWalletTopUpVerificationResult({
    required this.wallet,
    required this.transaction,
  });

  final GteUserWallet wallet;
  final GteWalletTransactionRecord transaction;

  factory GteWalletTopUpVerificationResult.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet top-up verification',
    );
    return GteWalletTopUpVerificationResult(
      wallet: GteUserWallet.fromJson(
        GteJson.value(json, <String>['wallet']) ?? const <String, Object?>{},
      ),
      transaction: GteWalletTransactionRecord.fromJson(
        GteJson.value(json, <String>['transaction']) ??
            const <String, Object?>{},
      ),
    );
  }
}

class GteWalletConversionQuoteRequest {
  const GteWalletConversionQuoteRequest({
    required this.amount,
    this.sourceUnit = GteLedgerUnit.coin,
  });

  final double amount;
  final GteLedgerUnit sourceUnit;

  Map<String, Object?> toJson() => <String, Object?>{
    'amount': amount,
    'source_unit': sourceUnit.name,
  };
}

class GteWalletConversionRequest extends GteWalletConversionQuoteRequest {
  const GteWalletConversionRequest({
    required super.amount,
    super.sourceUnit = GteLedgerUnit.coin,
    this.idempotencyKey,
  });

  final String? idempotencyKey;

  @override
  Map<String, Object?> toJson() => <String, Object?>{
    ...super.toJson(),
    if (idempotencyKey != null && idempotencyKey!.trim().isNotEmpty)
      'idempotency_key': idempotencyKey!.trim(),
  };
}

class GteWalletConversionQuote {
  const GteWalletConversionQuote({
    required this.sourceUnit,
    required this.sourceAmount,
    required this.targetUnit,
    required this.targetAmount,
    required this.rate,
  });

  final GteLedgerUnit sourceUnit;
  final double sourceAmount;
  final GteLedgerUnit targetUnit;
  final double targetAmount;
  final double rate;

  factory GteWalletConversionQuote.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet conversion quote',
    );
    return GteWalletConversionQuote(
      sourceUnit: _ledgerUnitFromString(
        GteJson.string(json, <String>['source_unit', 'sourceUnit']),
      ),
      sourceAmount: GteJson.requiredNumber(json, <String>[
        'source_amount',
        'sourceAmount',
      ]),
      targetUnit: _ledgerUnitFromString(
        GteJson.string(json, <String>['target_unit', 'targetUnit']),
      ),
      targetAmount: GteJson.requiredNumber(json, <String>[
        'target_amount',
        'targetAmount',
      ]),
      rate: GteJson.requiredNumber(json, <String>['rate']),
    );
  }
}

class GteWalletConversion extends GteWalletConversionQuote {
  const GteWalletConversion({
    required this.transactionId,
    required this.reference,
    required super.sourceUnit,
    required super.sourceAmount,
    required super.targetUnit,
    required super.targetAmount,
    required super.rate,
  });

  final String transactionId;
  final String reference;

  factory GteWalletConversion.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'wallet conversion',
    );
    return GteWalletConversion(
      transactionId: GteJson.string(json, <String>[
        'transaction_id',
        'transactionId',
      ]),
      reference: GteJson.string(json, <String>['reference']),
      sourceUnit: _ledgerUnitFromString(
        GteJson.string(json, <String>['source_unit', 'sourceUnit']),
      ),
      sourceAmount: GteJson.requiredNumber(json, <String>[
        'source_amount',
        'sourceAmount',
      ]),
      targetUnit: _ledgerUnitFromString(
        GteJson.string(json, <String>['target_unit', 'targetUnit']),
      ),
      targetAmount: GteJson.requiredNumber(json, <String>[
        'target_amount',
        'targetAmount',
      ]),
      rate: GteJson.requiredNumber(json, <String>['rate']),
    );
  }
}

class GteWithdrawalEligibility {
  const GteWithdrawalEligibility({
    required this.availableBalance,
    required this.withdrawableNow,
    required this.remainingAllowance,
    required this.nextEligibleAt,
    required this.kycStatus,
    required this.requiresKyc,
    required this.requiresBankAccount,
    required this.pendingWithdrawals,
    this.countryCode,
    this.countryWithdrawalsEnabled = false,
    this.missingRequiredPolicies = const <String>[],
    this.policyBlocked = false,
    this.policyBlockReason,
  });

  final double availableBalance;
  final double withdrawableNow;
  final double remainingAllowance;
  final DateTime? nextEligibleAt;
  final GteKycStatus kycStatus;
  final bool requiresKyc;
  final bool requiresBankAccount;
  final double pendingWithdrawals;
  final String? countryCode;
  final bool countryWithdrawalsEnabled;
  final List<String> missingRequiredPolicies;
  final bool policyBlocked;
  final String? policyBlockReason;

  factory GteWithdrawalEligibility.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'withdrawal eligibility',
    );
    return GteWithdrawalEligibility(
      availableBalance: GteJson.requiredNumber(json, <String>[
        'available_balance',
        'availableBalance',
      ]),
      withdrawableNow: GteJson.requiredNumber(json, <String>[
        'withdrawable_now',
        'withdrawableNow',
      ]),
      remainingAllowance: GteJson.requiredNumber(json, <String>[
        'remaining_allowance',
        'remainingAllowance',
      ]),
      nextEligibleAt: GteJson.dateTimeOrNull(json, <String>[
        'next_eligible_at',
        'nextEligibleAt',
      ]),
      kycStatus: _kycStatusFromString(
        GteJson.string(json, <String>[
          'kyc_status',
          'kycStatus',
        ], fallback: 'unverified'),
      ),
      requiresKyc: GteJson.requiredBoolean(json, <String>[
        'requires_kyc',
        'requiresKyc',
      ]),
      requiresBankAccount: GteJson.requiredBoolean(json, <String>[
        'requires_bank_account',
        'requiresBankAccount',
      ]),
      pendingWithdrawals: GteJson.requiredNumber(json, <String>[
        'pending_withdrawals',
        'pendingWithdrawals',
      ]),
      countryCode: GteJson.stringOrNull(json, <String>[
        'country_code',
        'countryCode',
      ]),
      countryWithdrawalsEnabled: GteJson.requiredBoolean(json, <String>[
        'country_withdrawals_enabled',
        'countryWithdrawalsEnabled',
      ]),
      missingRequiredPolicies: GteJson.typedList(json, <String>[
            'missing_required_policies',
            'missingRequiredPolicies',
          ], (Object? value) => value?.toString() ?? '')
          .where((String value) => value.trim().isNotEmpty)
          .toList(growable: false),
      policyBlocked: GteJson.requiredBoolean(json, <String>[
        'policy_blocked',
        'policyBlocked',
      ]),
      policyBlockReason: GteJson.stringOrNull(json, <String>[
        'policy_block_reason',
        'policyBlockReason',
      ]),
    );
  }
}

class GteWithdrawalQuote {
  const GteWithdrawalQuote({
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.totalDebit,
    required this.sourceScope,
    required this.currencyCode,
    required this.rateValue,
    required this.rateDirection,
    required this.estimatedFiatPayout,
    required this.processorMode,
    required this.payoutChannel,
    required this.feeBps,
    required this.minimumFee,
    required this.eligibility,
    this.blockedReason,
  });

  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final double totalDebit;
  final String sourceScope;
  final String currencyCode;
  final double rateValue;
  final GteRateDirection rateDirection;
  final double estimatedFiatPayout;
  final String processorMode;
  final String payoutChannel;
  final int feeBps;
  final double minimumFee;
  final GteWithdrawalEligibility eligibility;
  final String? blockedReason;

  factory GteWithdrawalQuote.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'withdrawal quote',
    );
    return GteWithdrawalQuote(
      grossAmount: GteJson.requiredNumber(json, <String>[
        'gross_amount',
        'grossAmount',
      ]),
      feeAmount: GteJson.requiredNumber(json, <String>[
        'fee_amount',
        'feeAmount',
      ]),
      netAmount: GteJson.requiredNumber(json, <String>[
        'net_amount',
        'netAmount',
      ]),
      totalDebit: GteJson.requiredNumber(json, <String>[
        'total_debit',
        'totalDebit',
      ]),
      sourceScope: GteJson.string(json, <String>[
        'source_scope',
        'sourceScope',
      ]),
      currencyCode: GteJson.string(json, <String>[
        'currency_code',
        'currencyCode',
      ]),
      rateValue: GteJson.requiredNumber(json, <String>[
        'rate_value',
        'rateValue',
      ]),
      rateDirection: _rateDirectionFromString(
        GteJson.string(json, <String>['rate_direction', 'rateDirection']),
      ),
      estimatedFiatPayout: GteJson.requiredNumber(json, <String>[
        'estimated_fiat_payout',
        'estimatedFiatPayout',
      ]),
      processorMode: GteJson.string(json, <String>[
        'processor_mode',
        'processorMode',
      ]),
      payoutChannel: GteJson.string(json, <String>[
        'payout_channel',
        'payoutChannel',
      ]),
      feeBps: GteJson.requiredInteger(json, <String>['fee_bps', 'feeBps']),
      minimumFee: GteJson.requiredNumber(json, <String>[
        'minimum_fee',
        'minimumFee',
      ]),
      eligibility: GteWithdrawalEligibility.fromJson(
        GteJson.value(json, <String>['eligibility']),
      ),
      blockedReason: GteJson.stringOrNull(json, <String>[
        'blocked_reason',
        'blockedReason',
      ]),
    );
  }
}

class GteWithdrawalQuoteRequest {
  const GteWithdrawalQuoteRequest({
    required this.amountCoin,
    this.sourceScope = 'trade',
  });

  final double amountCoin;
  final String sourceScope;

  Map<String, Object?> toJson() => <String, Object?>{
    'amount_coin': amountCoin,
    'source_scope': sourceScope,
  };
}

class GteWithdrawalReceipt {
  const GteWithdrawalReceipt({
    required this.withdrawal,
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.totalDebit,
    required this.sourceScope,
    required this.processorMode,
    required this.payoutChannel,
  });

  final GteTreasuryWithdrawalRequest withdrawal;
  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final double totalDebit;
  final String sourceScope;
  final String processorMode;
  final String payoutChannel;

  factory GteWithdrawalReceipt.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'withdrawal receipt',
    );
    return GteWithdrawalReceipt(
      withdrawal: GteTreasuryWithdrawalRequest.fromJson(
        GteJson.value(json, <String>['withdrawal']),
      ),
      grossAmount: GteJson.requiredNumber(json, <String>[
        'gross_amount',
        'grossAmount',
      ]),
      feeAmount: GteJson.requiredNumber(json, <String>[
        'fee_amount',
        'feeAmount',
      ]),
      netAmount: GteJson.requiredNumber(json, <String>[
        'net_amount',
        'netAmount',
      ]),
      totalDebit: GteJson.requiredNumber(json, <String>[
        'total_debit',
        'totalDebit',
      ]),
      sourceScope: GteJson.string(json, <String>[
        'source_scope',
        'sourceScope',
      ]),
      processorMode: GteJson.string(json, <String>[
        'processor_mode',
        'processorMode',
      ]),
      payoutChannel: GteJson.string(json, <String>[
        'payout_channel',
        'payoutChannel',
      ]),
    );
  }
}
