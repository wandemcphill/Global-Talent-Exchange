import 'package:gte_frontend/data/gte_models.dart';

class AdminFinanceDailyStat {
  const AdminFinanceDailyStat({
    required this.date,
    required this.gtexMinted,
    required this.gtexBurned,
    required this.fanMinted,
    required this.fanBurned,
    required this.revenueNaira,
    required this.marketplaceFeeAmount,
    required this.matchSpendAmount,
    required this.tournamentPoolAmount,
    required this.gtexSupply,
    required this.fanSupply,
    required this.metadata,
  });

  final DateTime date;
  final double gtexMinted;
  final double gtexBurned;
  final double fanMinted;
  final double fanBurned;
  final double revenueNaira;
  final double marketplaceFeeAmount;
  final double matchSpendAmount;
  final double tournamentPoolAmount;
  final double gtexSupply;
  final double fanSupply;
  final Map<String, Object?> metadata;

  factory AdminFinanceDailyStat.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'finance daily stat',
    );
    return AdminFinanceDailyStat(
      date: _dateOnlyFromJson(json, <String>['date']),
      gtexMinted: GteJson.number(json, <String>['gtex_minted', 'gtexMinted']),
      gtexBurned: GteJson.number(json, <String>['gtex_burned', 'gtexBurned']),
      fanMinted: GteJson.number(json, <String>['fan_minted', 'fanMinted']),
      fanBurned: GteJson.number(json, <String>['fan_burned', 'fanBurned']),
      revenueNaira: GteJson.number(json, <String>[
        'revenue_naira',
        'revenueNaira',
      ]),
      marketplaceFeeAmount: GteJson.number(json, <String>[
        'marketplace_fee_amount',
        'marketplaceFeeAmount',
      ]),
      matchSpendAmount: GteJson.number(json, <String>[
        'match_spend_amount',
        'matchSpendAmount',
      ]),
      tournamentPoolAmount: GteJson.number(json, <String>[
        'tournament_pool_amount',
        'tournamentPoolAmount',
      ]),
      gtexSupply: GteJson.number(json, <String>['gtex_supply', 'gtexSupply']),
      fanSupply: GteJson.number(json, <String>['fan_supply', 'fanSupply']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class AdminFinanceLargeTransaction {
  const AdminFinanceLargeTransaction({
    required this.transactionId,
    required this.reference,
    required this.accountCode,
    required this.unit,
    required this.amount,
    required this.reason,
    required this.sourceTag,
    required this.createdAt,
  });

  final String transactionId;
  final String? reference;
  final String accountCode;
  final String unit;
  final double amount;
  final String reason;
  final String sourceTag;
  final DateTime createdAt;

  factory AdminFinanceLargeTransaction.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'finance transaction',
    );
    return AdminFinanceLargeTransaction(
      transactionId: GteJson.string(json, <String>[
        'transaction_id',
        'transactionId',
      ]),
      reference: GteJson.stringOrNull(json, <String>['reference']),
      accountCode: GteJson.string(json, <String>[
        'account_code',
        'accountCode',
      ]),
      unit: GteJson.string(json, <String>['unit']),
      amount: GteJson.number(json, <String>['amount']),
      reason: GteJson.string(json, <String>['reason']),
      sourceTag: GteJson.string(json, <String>['source_tag', 'sourceTag']),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
    );
  }
}

class AdminFinanceAlert {
  const AdminFinanceAlert({
    required this.level,
    required this.title,
    required this.message,
    required this.metricKey,
    required this.createdAt,
  });

  final String level;
  final String title;
  final String message;
  final String metricKey;
  final DateTime? createdAt;

  factory AdminFinanceAlert.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'finance alert',
    );
    return AdminFinanceAlert(
      level: GteJson.string(json, <String>['level'], fallback: 'info'),
      title: GteJson.string(json, <String>['title']),
      message: GteJson.string(json, <String>['message']),
      metricKey: GteJson.string(json, <String>['metric_key', 'metricKey']),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
    );
  }
}

class AdminFinancePlayerTrend {
  const AdminFinancePlayerTrend({
    required this.playerId,
    required this.trendDirection,
    required this.momentum7dPct,
    required this.momentum30dPct,
    required this.lastTradePriceCredits,
  });

  final String playerId;
  final String trendDirection;
  final double momentum7dPct;
  final double momentum30dPct;
  final double? lastTradePriceCredits;

  factory AdminFinancePlayerTrend.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'player price trend',
    );
    return AdminFinancePlayerTrend(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      trendDirection: GteJson.string(json, <String>[
        'trend_direction',
        'trendDirection',
      ], fallback: 'flat'),
      momentum7dPct: GteJson.number(json, <String>[
        'momentum_7d_pct',
        'momentum7dPct',
      ]),
      momentum30dPct: GteJson.number(json, <String>[
        'momentum_30d_pct',
        'momentum30dPct',
      ]),
      lastTradePriceCredits:
          GteJson.value(json, <String>[
                    'last_trade_price_credits',
                    'lastTradePriceCredits',
                  ]) ==
                  null
              ? null
              : GteJson.number(json, <String>[
                'last_trade_price_credits',
                'lastTradePriceCredits',
              ]),
    );
  }
}

class AdminFinanceTournamentPool {
  const AdminFinanceTournamentPool({
    required this.competitionId,
    required this.poolType,
    required this.currency,
    required this.amount,
    required this.status,
  });

  final String competitionId;
  final String poolType;
  final String currency;
  final double amount;
  final String status;

  factory AdminFinanceTournamentPool.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'tournament pool',
    );
    return AdminFinanceTournamentPool(
      competitionId: GteJson.string(json, <String>[
        'competition_id',
        'competitionId',
      ]),
      poolType: GteJson.string(json, <String>['pool_type', 'poolType']),
      currency: GteJson.string(json, <String>['currency']),
      amount: GteJson.number(json, <String>['amount']),
      status: GteJson.string(json, <String>['status']),
    );
  }
}

class AdminFinanceCashRail {
  const AdminFinanceCashRail({
    required this.paymentMethods,
    required this.depositMode,
    required this.withdrawalMode,
    required this.currencyCode,
    required this.minWithdrawal,
    required this.maxWithdrawal,
    required this.pendingPurchaseOrders,
    required this.pendingWithdrawals,
    required this.pendingKyc,
    required this.automaticDepositsEnabled,
    required this.automaticWithdrawalsEnabled,
  });

  final List<String> paymentMethods;
  final String depositMode;
  final String withdrawalMode;
  final String currencyCode;
  final double minWithdrawal;
  final double maxWithdrawal;
  final int pendingPurchaseOrders;
  final int pendingWithdrawals;
  final int pendingKyc;
  final bool automaticDepositsEnabled;
  final bool automaticWithdrawalsEnabled;

  factory AdminFinanceCashRail.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'cash rails');
    return AdminFinanceCashRail(
      paymentMethods: GteJson.typedList<String>(json, <String>[
        'payment_methods',
        'paymentMethods',
      ], (Object? item) => item.toString()),
      depositMode: GteJson.string(json, <String>[
        'deposit_mode',
        'depositMode',
      ]),
      withdrawalMode: GteJson.string(json, <String>[
        'withdrawal_mode',
        'withdrawalMode',
      ]),
      currencyCode: GteJson.string(json, <String>[
        'currency_code',
        'currencyCode',
      ]),
      minWithdrawal: GteJson.number(json, <String>[
        'min_withdrawal',
        'minWithdrawal',
      ]),
      maxWithdrawal: GteJson.number(json, <String>[
        'max_withdrawal',
        'maxWithdrawal',
      ]),
      pendingPurchaseOrders: GteJson.integer(json, <String>[
        'pending_purchase_orders',
        'pendingPurchaseOrders',
      ]),
      pendingWithdrawals: GteJson.integer(json, <String>[
        'pending_withdrawals',
        'pendingWithdrawals',
      ]),
      pendingKyc: GteJson.integer(json, <String>['pending_kyc', 'pendingKyc']),
      automaticDepositsEnabled: GteJson.boolean(json, <String>[
        'automatic_deposits_enabled',
        'automaticDepositsEnabled',
      ]),
      automaticWithdrawalsEnabled: GteJson.boolean(json, <String>[
        'automatic_withdrawals_enabled',
        'automaticWithdrawalsEnabled',
      ]),
    );
  }
}

class AdminFinanceProjectionSummary {
  const AdminFinanceProjectionSummary({
    required this.days,
    required this.endingGtexSupply,
    required this.endingFanSupply,
    required this.gtexBurnMintRatio,
    required this.fanBurnMintRatio,
    required this.inflationRisk,
    required this.recommendations,
  });

  final int days;
  final double endingGtexSupply;
  final double endingFanSupply;
  final double? gtexBurnMintRatio;
  final double? fanBurnMintRatio;
  final String inflationRisk;
  final List<String> recommendations;

  factory AdminFinanceProjectionSummary.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'projection summary',
    );
    return AdminFinanceProjectionSummary(
      days: GteJson.integer(json, <String>['days'], fallback: 30),
      endingGtexSupply: GteJson.number(json, <String>[
        'ending_gtex_supply',
        'endingGtexSupply',
      ]),
      endingFanSupply: GteJson.number(json, <String>[
        'ending_fan_supply',
        'endingFanSupply',
      ]),
      gtexBurnMintRatio:
          GteJson.value(json, <String>[
                    'gtex_burn_mint_ratio',
                    'gtexBurnMintRatio',
                  ]) ==
                  null
              ? null
              : GteJson.number(json, <String>[
                'gtex_burn_mint_ratio',
                'gtexBurnMintRatio',
              ]),
      fanBurnMintRatio:
          GteJson.value(json, <String>[
                    'fan_burn_mint_ratio',
                    'fanBurnMintRatio',
                  ]) ==
                  null
              ? null
              : GteJson.number(json, <String>[
                'fan_burn_mint_ratio',
                'fanBurnMintRatio',
              ]),
      inflationRisk: GteJson.string(json, <String>[
        'inflation_risk',
        'inflationRisk',
      ]),
      recommendations: GteJson.typedList<String>(json, <String>[
        'recommendations',
      ], (Object? item) => item.toString()),
    );
  }
}

class AdminFinanceControlTower {
  const AdminFinanceControlTower({
    required this.generatedAt,
    required this.gtexSupply,
    required this.fanSupply,
    required this.dailyRevenueNaira,
    required this.marketplaceFeeAmount,
    required this.fanCoinBurnedToday,
    required this.gtexMintedToday,
    required this.gtexBurnedToday,
    required this.fanMintedToday,
    required this.fanBurnedToday,
    required this.gtexBurnMintRatio,
    required this.fanBurnMintRatio,
    required this.inflationRisk,
    required this.liquidityStatus,
    required this.userSpendTrend,
    required this.avgSpendPerMatch,
    required this.pendingPurchaseOrders,
    required this.pendingWithdrawals,
    required this.pendingKyc,
    required this.history,
    required this.topTransactions,
    required this.alerts,
    required this.playerPriceTrends,
    required this.tournamentPoolSizes,
    required this.cashRails,
    required this.projection,
  });

  final DateTime generatedAt;
  final double gtexSupply;
  final double fanSupply;
  final double dailyRevenueNaira;
  final double marketplaceFeeAmount;
  final double fanCoinBurnedToday;
  final double gtexMintedToday;
  final double gtexBurnedToday;
  final double fanMintedToday;
  final double fanBurnedToday;
  final double? gtexBurnMintRatio;
  final double? fanBurnMintRatio;
  final String inflationRisk;
  final String liquidityStatus;
  final String userSpendTrend;
  final double avgSpendPerMatch;
  final int pendingPurchaseOrders;
  final int pendingWithdrawals;
  final int pendingKyc;
  final List<AdminFinanceDailyStat> history;
  final List<AdminFinanceLargeTransaction> topTransactions;
  final List<AdminFinanceAlert> alerts;
  final List<AdminFinancePlayerTrend> playerPriceTrends;
  final List<AdminFinanceTournamentPool> tournamentPoolSizes;
  final AdminFinanceCashRail cashRails;
  final AdminFinanceProjectionSummary? projection;

  factory AdminFinanceControlTower.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'control tower',
    );
    return AdminFinanceControlTower(
      generatedAt: GteJson.dateTime(json, <String>[
        'generated_at',
        'generatedAt',
      ]),
      gtexSupply: GteJson.number(json, <String>['gtex_supply', 'gtexSupply']),
      fanSupply: GteJson.number(json, <String>['fan_supply', 'fanSupply']),
      dailyRevenueNaira: GteJson.number(json, <String>[
        'daily_revenue_naira',
        'dailyRevenueNaira',
      ]),
      marketplaceFeeAmount: GteJson.number(json, <String>[
        'marketplace_fee_amount',
        'marketplaceFeeAmount',
      ]),
      fanCoinBurnedToday: GteJson.number(json, <String>[
        'fan_coin_burned_today',
        'fanCoinBurnedToday',
      ]),
      gtexMintedToday: GteJson.number(json, <String>[
        'gtex_minted_today',
        'gtexMintedToday',
      ]),
      gtexBurnedToday: GteJson.number(json, <String>[
        'gtex_burned_today',
        'gtexBurnedToday',
      ]),
      fanMintedToday: GteJson.number(json, <String>[
        'fan_minted_today',
        'fanMintedToday',
      ]),
      fanBurnedToday: GteJson.number(json, <String>[
        'fan_burned_today',
        'fanBurnedToday',
      ]),
      gtexBurnMintRatio:
          GteJson.value(json, <String>[
                    'gtex_burn_mint_ratio',
                    'gtexBurnMintRatio',
                  ]) ==
                  null
              ? null
              : GteJson.number(json, <String>[
                'gtex_burn_mint_ratio',
                'gtexBurnMintRatio',
              ]),
      fanBurnMintRatio:
          GteJson.value(json, <String>[
                    'fan_burn_mint_ratio',
                    'fanBurnMintRatio',
                  ]) ==
                  null
              ? null
              : GteJson.number(json, <String>[
                'fan_burn_mint_ratio',
                'fanBurnMintRatio',
              ]),
      inflationRisk: GteJson.string(json, <String>[
        'inflation_risk',
        'inflationRisk',
      ]),
      liquidityStatus: GteJson.string(json, <String>[
        'liquidity_status',
        'liquidityStatus',
      ]),
      userSpendTrend: GteJson.string(json, <String>[
        'user_spend_trend',
        'userSpendTrend',
      ]),
      avgSpendPerMatch: GteJson.number(json, <String>[
        'avg_spend_per_match',
        'avgSpendPerMatch',
      ]),
      pendingPurchaseOrders: GteJson.integer(json, <String>[
        'pending_purchase_orders',
        'pendingPurchaseOrders',
      ]),
      pendingWithdrawals: GteJson.integer(json, <String>[
        'pending_withdrawals',
        'pendingWithdrawals',
      ]),
      pendingKyc: GteJson.integer(json, <String>['pending_kyc', 'pendingKyc']),
      history: GteJson.typedList(json, <String>[
        'history',
      ], AdminFinanceDailyStat.fromJson),
      topTransactions: GteJson.typedList(json, <String>[
        'top_transactions',
        'topTransactions',
      ], AdminFinanceLargeTransaction.fromJson),
      alerts: GteJson.typedList(json, <String>[
        'alerts',
      ], AdminFinanceAlert.fromJson),
      playerPriceTrends: GteJson.typedList(json, <String>[
        'player_price_trends',
        'playerPriceTrends',
      ], AdminFinancePlayerTrend.fromJson),
      tournamentPoolSizes: GteJson.typedList(json, <String>[
        'tournament_pool_sizes',
        'tournamentPoolSizes',
      ], AdminFinanceTournamentPool.fromJson),
      cashRails: AdminFinanceCashRail.fromJson(
        GteJson.value(json, <String>['cash_rails', 'cashRails']) ??
            const <String, Object?>{},
      ),
      projection:
          GteJson.value(json, <String>['projection']) == null
              ? null
              : AdminFinanceProjectionSummary.fromJson(
                GteJson.value(json, <String>['projection']),
              ),
    );
  }
}

class AdminEconomySimulationConfig {
  const AdminEconomySimulationConfig({
    required this.dailyActiveUsers,
    required this.avgMatchesPerUser,
    required this.fanSpendPerMatch,
    required this.fanMintPerMatch,
    required this.gtexPurchaseRate,
    required this.gtexPurchaseAmount,
    required this.tournamentEntryGtex,
    required this.tournamentParticipationRate,
    required this.gtexRewardPayoutPerMatch,
  });

  final int dailyActiveUsers;
  final double avgMatchesPerUser;
  final double fanSpendPerMatch;
  final double fanMintPerMatch;
  final double gtexPurchaseRate;
  final double gtexPurchaseAmount;
  final double tournamentEntryGtex;
  final double tournamentParticipationRate;
  final double gtexRewardPayoutPerMatch;

  const AdminEconomySimulationConfig.defaults()
    : dailyActiveUsers = 100000,
      avgMatchesPerUser = 5,
      fanSpendPerMatch = 10,
      fanMintPerMatch = 0,
      gtexPurchaseRate = 0.02,
      gtexPurchaseAmount = 1,
      tournamentEntryGtex = 2,
      tournamentParticipationRate = 0.12,
      gtexRewardPayoutPerMatch = 0;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'daily_active_users': dailyActiveUsers,
      'avg_matches_per_user': avgMatchesPerUser.toStringAsFixed(4),
      'fan_spend_per_match': fanSpendPerMatch.toStringAsFixed(4),
      'fan_mint_per_match': fanMintPerMatch.toStringAsFixed(4),
      'gtex_purchase_rate': gtexPurchaseRate.toStringAsFixed(4),
      'gtex_purchase_amount': gtexPurchaseAmount.toStringAsFixed(4),
      'tournament_entry_gtex': tournamentEntryGtex.toStringAsFixed(4),
      'tournament_participation_rate': tournamentParticipationRate
          .toStringAsFixed(4),
      'gtex_reward_payout_per_match': gtexRewardPayoutPerMatch.toStringAsFixed(
        4,
      ),
    };
  }
}

class AdminEconomySimulationPoint {
  const AdminEconomySimulationPoint({
    required this.day,
    required this.gtexSupply,
    required this.fanSupply,
    required this.gtexMinted,
    required this.gtexBurned,
    required this.fanMinted,
    required this.fanBurned,
    required this.gtexBurnMintRatio,
    required this.fanBurnMintRatio,
    required this.inflationRisk,
  });

  final int day;
  final double gtexSupply;
  final double fanSupply;
  final double gtexMinted;
  final double gtexBurned;
  final double fanMinted;
  final double fanBurned;
  final double? gtexBurnMintRatio;
  final double? fanBurnMintRatio;
  final String inflationRisk;

  factory AdminEconomySimulationPoint.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'simulation point',
    );
    return AdminEconomySimulationPoint(
      day: GteJson.integer(json, <String>['day']),
      gtexSupply: GteJson.number(json, <String>['gtex_supply', 'gtexSupply']),
      fanSupply: GteJson.number(json, <String>['fan_supply', 'fanSupply']),
      gtexMinted: GteJson.number(json, <String>['gtex_minted', 'gtexMinted']),
      gtexBurned: GteJson.number(json, <String>['gtex_burned', 'gtexBurned']),
      fanMinted: GteJson.number(json, <String>['fan_minted', 'fanMinted']),
      fanBurned: GteJson.number(json, <String>['fan_burned', 'fanBurned']),
      gtexBurnMintRatio:
          GteJson.value(json, <String>[
                    'gtex_burn_mint_ratio',
                    'gtexBurnMintRatio',
                  ]) ==
                  null
              ? null
              : GteJson.number(json, <String>[
                'gtex_burn_mint_ratio',
                'gtexBurnMintRatio',
              ]),
      fanBurnMintRatio:
          GteJson.value(json, <String>[
                    'fan_burn_mint_ratio',
                    'fanBurnMintRatio',
                  ]) ==
                  null
              ? null
              : GteJson.number(json, <String>[
                'fan_burn_mint_ratio',
                'fanBurnMintRatio',
              ]),
      inflationRisk: GteJson.string(json, <String>[
        'inflation_risk',
        'inflationRisk',
      ]),
    );
  }
}

class AdminEconomySimulationResult {
  const AdminEconomySimulationResult({
    required this.days,
    required this.startingGtexSupply,
    required this.startingFanSupply,
    required this.summary,
    required this.projections,
  });

  final int days;
  final double startingGtexSupply;
  final double startingFanSupply;
  final AdminFinanceProjectionSummary summary;
  final List<AdminEconomySimulationPoint> projections;

  factory AdminEconomySimulationResult.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'simulation result',
    );
    return AdminEconomySimulationResult(
      days: GteJson.integer(json, <String>['days'], fallback: 30),
      startingGtexSupply: GteJson.number(json, <String>[
        'starting_gtex_supply',
        'startingGtexSupply',
      ]),
      startingFanSupply: GteJson.number(json, <String>[
        'starting_fan_supply',
        'startingFanSupply',
      ]),
      summary: AdminFinanceProjectionSummary.fromJson(
        GteJson.value(json, <String>['summary']) ?? const <String, Object?>{},
      ),
      projections: GteJson.typedList(json, <String>[
        'projections',
      ], AdminEconomySimulationPoint.fromJson),
    );
  }
}

DateTime _dateOnlyFromJson(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue is DateTime) {
    return DateTime.utc(rawValue.year, rawValue.month, rawValue.day);
  }
  final DateTime? parsed =
      rawValue == null ? null : DateTime.tryParse(rawValue.toString())?.toUtc();
  if (parsed == null) {
    return DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
  }
  return DateTime.utc(parsed.year, parsed.month, parsed.day);
}
