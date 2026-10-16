import 'dart:math' as math;

import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/models/admin_finance_models.dart';

class AdminFinanceApi {
  AdminFinanceApi({
    required this.client,
    required AdminFinanceFixtures? fixtures,
  }) : _fixtures = fixtures;

  final GteAuthedApi client;
  final AdminFinanceFixtures? _fixtures;

  factory AdminFinanceApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteTransport? transport,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return AdminFinanceApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: transport ?? GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      fixtures: null,
    );
  }

  factory AdminFinanceApi.fixture() {
    assertFixtureFactoryAllowed('AdminFinanceApi.fixture');
    return AdminFinanceApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: AdminFinanceFixtures.seed(),
    );
  }

  Future<AdminFinanceControlTower> fetchControlTower({
    int historyDays = 30,
    int transactionLimit = 12,
  }) {
    return client.withFallback<AdminFinanceControlTower>(
      () async {
        final Map<String, dynamic> payload = await client.getMap(
          '/api/admin/finance/control-tower',
          query: <String, Object?>{
            'history_days': historyDays,
            'transaction_limit': transactionLimit,
          },
        );
        return AdminFinanceControlTower.fromJson(payload);
      },
      () async => _requireFixtures().controlTower(
        historyDays: historyDays,
        transactionLimit: transactionLimit,
      ),
    );
  }

  Future<AdminEconomySimulationResult> simulate({
    AdminEconomySimulationConfig config =
        const AdminEconomySimulationConfig.defaults(),
  }) {
    return client.withFallback<AdminEconomySimulationResult>(() async {
      final Object? payload = await client.post(
        '/api/admin/finance/simulate',
        body: config.toJson(),
      );
      return AdminEconomySimulationResult.fromJson(payload);
    }, () async => _requireFixtures().simulate(config: config));
  }

  AdminFinanceFixtures _requireFixtures() {
    final AdminFinanceFixtures? fixtures = _fixtures;
    if (fixtures == null) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message:
            'Admin finance fixtures are not registered in strict-live runtime.',
      );
    }
    return fixtures;
  }
}

class AdminFinanceFixtures {
  AdminFinanceFixtures._();

  static AdminFinanceFixtures seed() => AdminFinanceFixtures._();

  Future<AdminFinanceControlTower> controlTower({
    int historyDays = 30,
    int transactionLimit = 12,
  }) async {
    final DateTime now = DateTime.now().toUtc();
    final List<AdminFinanceDailyStat> history =
        List<AdminFinanceDailyStat>.generate(historyDays, (int index) {
          final int offset = historyDays - index - 1;
          final DateTime date = DateTime.utc(
            now.year,
            now.month,
            now.day,
          ).subtract(Duration(days: offset));
          final double revenue =
              420000 + (index * 18500) + ((index % 4) * 12000);
          final double gtexMinted = 320 + (index * 8);
          final double gtexBurned = 170 + ((index % 5) * 18);
          final double fanMinted = 500 + ((index % 3) * 35);
          final double fanBurned = 1100 + (index * 26);
          final double gtexSupply = 210000 + (index * 140);
          final double fanSupply = 1480000 - (index * 680);
          return AdminFinanceDailyStat(
            date: date,
            gtexMinted: _round(gtexMinted),
            gtexBurned: _round(gtexBurned),
            fanMinted: _round(fanMinted),
            fanBurned: _round(fanBurned),
            revenueNaira: _round(revenue),
            marketplaceFeeAmount: _round(revenue * 0.08),
            matchSpendAmount: _round(9200 + (index * 240)),
            tournamentPoolAmount: _round(8500 + ((index % 6) * 700)),
            gtexSupply: _round(gtexSupply),
            fanSupply: _round(math.max(320000, fanSupply)),
            metadata: <String, Object?>{
              'burn_heat': fanBurned > 1500 ? 'high' : 'normal',
            },
          );
        });
    final AdminFinanceDailyStat today = history.last;
    final AdminEconomySimulationResult projection = await simulate();
    final List<AdminFinanceAlert> alerts = <AdminFinanceAlert>[
      if ((_ratio(today.gtexBurned, today.gtexMinted) ?? 0) < 0.65)
        AdminFinanceAlert(
          level: 'high',
          title: 'Inflation pressure building',
          message:
              'GTex mint is outpacing burn. Tighten sinks before tournament demand weakens.',
          metricKey: 'gtex_burn_mint_ratio',
          createdAt: now.subtract(const Duration(minutes: 11)),
        ),
      AdminFinanceAlert(
        level: 'medium',
        title: 'Withdrawal queue elevated',
        message:
            'Manual review volume is rising. Keep KYC throughput above payout demand.',
        metricKey: 'pending_withdrawals',
        createdAt: now.subtract(const Duration(minutes: 34)),
      ),
      AdminFinanceAlert(
        level: 'low',
        title: 'Fan Coin sink healthy',
        message:
            'Burn velocity remains ahead of mint, which is keeping engagement spend tight.',
        metricKey: 'fan_burn_mint_ratio',
        createdAt: now.subtract(const Duration(hours: 2)),
      ),
    ];

    return AdminFinanceControlTower(
      generatedAt: now,
      gtexSupply: today.gtexSupply,
      fanSupply: today.fanSupply,
      dailyRevenueNaira: today.revenueNaira,
      marketplaceFeeAmount: today.marketplaceFeeAmount,
      fanCoinBurnedToday: today.fanBurned,
      gtexMintedToday: today.gtexMinted,
      gtexBurnedToday: today.gtexBurned,
      fanMintedToday: today.fanMinted,
      fanBurnedToday: today.fanBurned,
      gtexBurnMintRatio: _ratio(today.gtexBurned, today.gtexMinted),
      fanBurnMintRatio: _ratio(today.fanBurned, today.fanMinted),
      inflationRisk: projection.summary.inflationRisk,
      liquidityStatus: 'HEALTHY',
      userSpendTrend: 'UP',
      avgSpendPerMatch: _round(today.matchSpendAmount / 280),
      pendingPurchaseOrders: 14,
      pendingWithdrawals: 7,
      pendingKyc: 19,
      history: history,
      topTransactions: List<AdminFinanceLargeTransaction>.generate(
        math.min(transactionLimit, 6),
        (int index) {
          final List<AdminFinanceLargeTransaction> seeded =
              <AdminFinanceLargeTransaction>[
                AdminFinanceLargeTransaction(
                  transactionId: 'tx-9001',
                  reference: 'PO-20260327-A1B2C3',
                  accountCode: 'user:wallet',
                  unit: 'coin',
                  amount: 145.5,
                  reason: 'deposit',
                  sourceTag: 'fancoin_purchase',
                  createdAt: now.subtract(const Duration(minutes: 6)),
                ),
                AdminFinanceLargeTransaction(
                  transactionId: 'tx-9002',
                  reference: 'WD-20260327-LIQ01',
                  accountCode: 'treasury:payout',
                  unit: 'coin',
                  amount: -94.0,
                  reason: 'withdrawal',
                  sourceTag: 'treasury_withdrawal',
                  createdAt: now.subtract(const Duration(minutes: 18)),
                ),
                AdminFinanceLargeTransaction(
                  transactionId: 'tx-9003',
                  reference: 'MATCH-POOL-402',
                  accountCode: 'competition:pool',
                  unit: 'coin',
                  amount: 62.0,
                  reason: 'competition_entry',
                  sourceTag: 'user_competition_entry_spend',
                  createdAt: now.subtract(const Duration(minutes: 42)),
                ),
                AdminFinanceLargeTransaction(
                  transactionId: 'tx-9004',
                  reference: 'GIFT-BURN-118',
                  accountCode: 'economy:burn',
                  unit: 'credit',
                  amount: -480.0,
                  reason: 'burn',
                  sourceTag: 'fan_gift_burn',
                  createdAt: now.subtract(const Duration(hours: 1, minutes: 9)),
                ),
                AdminFinanceLargeTransaction(
                  transactionId: 'tx-9005',
                  reference: 'SALE-FEE-78',
                  accountCode: 'platform:fees',
                  unit: 'coin',
                  amount: 31.4,
                  reason: 'platform_fee',
                  sourceTag: 'club_sale_platform_fee',
                  createdAt: now.subtract(
                    const Duration(hours: 2, minutes: 16),
                  ),
                ),
                AdminFinanceLargeTransaction(
                  transactionId: 'tx-9006',
                  reference: 'POOL-BOOST-44',
                  accountCode: 'competition:pool',
                  unit: 'coin',
                  amount: 88.0,
                  reason: 'reward_pool',
                  sourceTag: 'competition_reward',
                  createdAt: now.subtract(const Duration(hours: 3, minutes: 3)),
                ),
              ];
          return seeded[index];
        },
      ),
      alerts: alerts,
      playerPriceTrends: const <AdminFinancePlayerTrend>[
        AdminFinancePlayerTrend(
          playerId: 'player-9',
          trendDirection: 'up',
          momentum7dPct: 18.4,
          momentum30dPct: 26.0,
          lastTradePriceCredits: 72.5,
        ),
        AdminFinancePlayerTrend(
          playerId: 'player-17',
          trendDirection: 'up',
          momentum7dPct: 11.2,
          momentum30dPct: 19.7,
          lastTradePriceCredits: 64.0,
        ),
        AdminFinancePlayerTrend(
          playerId: 'player-44',
          trendDirection: 'down',
          momentum7dPct: -6.4,
          momentum30dPct: 3.1,
          lastTradePriceCredits: 28.6,
        ),
      ],
      tournamentPoolSizes: const <AdminFinanceTournamentPool>[
        AdminFinanceTournamentPool(
          competitionId: 'lagos-open',
          poolType: 'entry_fee',
          currency: 'coin',
          amount: 125000,
          status: 'planned',
        ),
        AdminFinanceTournamentPool(
          competitionId: 'africa-cup-daily',
          poolType: 'sponsored',
          currency: 'coin',
          amount: 86000,
          status: 'active',
        ),
        AdminFinanceTournamentPool(
          competitionId: 'creator-derby',
          poolType: 'entry_fee',
          currency: 'coin',
          amount: 44000,
          status: 'active',
        ),
      ],
      cashRails: const AdminFinanceCashRail(
        paymentMethods: <String>['KoraPay', 'Bank transfer', 'USDT'],
        depositMode: 'automatic',
        withdrawalMode: 'manual',
        currencyCode: 'NGN',
        minWithdrawal: 10,
        maxWithdrawal: 500000,
        pendingPurchaseOrders: 14,
        pendingWithdrawals: 7,
        pendingKyc: 19,
        automaticDepositsEnabled: true,
        automaticWithdrawalsEnabled: false,
      ),
      projection: projection.summary,
    );
  }

  Future<AdminEconomySimulationResult> simulate({
    AdminEconomySimulationConfig config =
        const AdminEconomySimulationConfig.defaults(),
  }) async {
    const int days = 30;
    const double startingGtexSupply = 240000;
    const double startingFanSupply = 1560000;
    double gtexSupply = startingGtexSupply;
    double fanSupply = startingFanSupply;
    final List<AdminEconomySimulationPoint> projections =
        <AdminEconomySimulationPoint>[];

    for (int day = 1; day <= days; day += 1) {
      final double matches = config.dailyActiveUsers * config.avgMatchesPerUser;
      final double fanBurn = matches * config.fanSpendPerMatch;
      final double fanMint = matches * config.fanMintPerMatch;
      final double gtexPurchases =
          config.dailyActiveUsers *
          config.gtexPurchaseRate *
          config.gtexPurchaseAmount;
      final double tournamentEntries =
          config.dailyActiveUsers * config.tournamentParticipationRate;
      final double gtexBurn = tournamentEntries * config.tournamentEntryGtex;
      final double rewardPayout = matches * config.gtexRewardPayoutPerMatch;
      final double gtexMint = gtexPurchases + rewardPayout;

      gtexSupply = _round(gtexSupply + gtexMint - gtexBurn);
      fanSupply = _round(math.max(0, fanSupply + fanMint - fanBurn));

      projections.add(
        AdminEconomySimulationPoint(
          day: day,
          gtexSupply: gtexSupply,
          fanSupply: fanSupply,
          gtexMinted: _round(gtexMint),
          gtexBurned: _round(gtexBurn),
          fanMinted: _round(fanMint),
          fanBurned: _round(fanBurn),
          gtexBurnMintRatio: _ratio(gtexBurn, gtexMint),
          fanBurnMintRatio: _ratio(fanBurn, fanMint),
          inflationRisk: _inflationRisk(gtexMint: gtexMint, gtexBurn: gtexBurn),
        ),
      );
    }

    final AdminEconomySimulationPoint ending = projections.last;
    return AdminEconomySimulationResult(
      days: days,
      startingGtexSupply: startingGtexSupply,
      startingFanSupply: startingFanSupply,
      summary: AdminFinanceProjectionSummary(
        days: days,
        endingGtexSupply: ending.gtexSupply,
        endingFanSupply: ending.fanSupply,
        gtexBurnMintRatio: ending.gtexBurnMintRatio,
        fanBurnMintRatio: ending.fanBurnMintRatio,
        inflationRisk: ending.inflationRisk,
        recommendations: _recommendations(
          inflationRisk: ending.inflationRisk,
          fanSupply: ending.fanSupply,
          startingFanSupply: startingFanSupply,
        ),
      ),
      projections: projections,
    );
  }

  List<String> _recommendations({
    required String inflationRisk,
    required double fanSupply,
    required double startingFanSupply,
  }) {
    final List<String> output = <String>[];
    if (inflationRisk == 'HIGH') {
      output.add('Increase tournament entry sinks or reduce GTex reward mint.');
      output.add(
        'Throttle promotional purchase bonuses until burn catches up.',
      );
    } else if (inflationRisk == 'MEDIUM') {
      output.add(
        'Monitor GTex mint closely and tighten reward loops if needed.',
      );
    } else {
      output.add('Current GTex sink mix is stable. Keep monitoring daily.');
    }
    if (fanSupply < startingFanSupply * 0.55) {
      output.add(
        'Fan Coin supply is draining fast. Add controlled mint sources.',
      );
    } else {
      output.add('Fan Coin spend remains healthy for match engagement.');
    }
    return output;
  }
}

double? _ratio(double numerator, double denominator) {
  if (denominator == 0) {
    return null;
  }
  return _round(numerator / denominator);
}

String _inflationRisk({required double gtexMint, required double gtexBurn}) {
  if (gtexMint > gtexBurn * 2) {
    return 'HIGH';
  }
  if (gtexMint > gtexBurn * 1.2) {
    return 'MEDIUM';
  }
  return 'LOW';
}

double _round(double value) {
  return double.parse(value.toStringAsFixed(2));
}
