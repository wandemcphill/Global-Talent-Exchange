import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/capital/trader/data/trader_api.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

const String traderBalanceBlockedReason =
    'Balance data unavailable - sync in progress.';

enum TradingDeskFilter { all, forwards, midfielders, defenders, rising, owned }

extension TradingDeskFilterLabel on TradingDeskFilter {
  String get label {
    return switch (this) {
      TradingDeskFilter.all => 'All',
      TradingDeskFilter.forwards => 'Forwards',
      TradingDeskFilter.midfielders => 'Midfield',
      TradingDeskFilter.defenders => 'Defense',
      TradingDeskFilter.rising => 'Rising',
      TradingDeskFilter.owned => 'Owned',
    };
  }
}

enum PaymentMethod { korapay, bankTransfer }

extension PaymentMethodMeta on PaymentMethod {
  String get label {
    return switch (this) {
      PaymentMethod.korapay => 'KoraPay',
      PaymentMethod.bankTransfer => 'Manual bank transfer',
    };
  }

  String get subtitle {
    return switch (this) {
      PaymentMethod.korapay => 'Instant settlement',
      PaymentMethod.bankTransfer => 'Manual treasury review',
    };
  }

  bool get isInstant => this != PaymentMethod.bankTransfer;
}

final Provider<TraderApi> capitalTraderApiProvider = Provider<TraderApi>((
  Ref ref,
) {
  return createCapitalTraderApi(
    baseUrl: ref.watch(apiBaseUrlProvider),
    accessToken: ref.watch(accessTokenProvider),
    backendMode: ref.watch(criticalBackendModeProvider),
  );
});

final FutureProvider<GtexSurfaceState<TraderOverview>>
traderMarketplaceProvider = FutureProvider<GtexSurfaceState<TraderOverview>>((
  Ref ref,
) async {
  try {
    return GtexData<TraderOverview>(
      data: await ref.watch(capitalTraderApiProvider).getMarketplace(),
    );
  } catch (error) {
    return _blockedFromTraderError<TraderOverview>(error);
  }
});

final FutureProvider<GtexSurfaceState<TraderProfile>> traderProfileProvider =
    FutureProvider<GtexSurfaceState<TraderProfile>>((Ref ref) async {
      try {
        return GtexData<TraderProfile>(
          data: await ref.watch(capitalTraderApiProvider).getProfile(),
        );
      } catch (error) {
        return _blockedFromTraderError<TraderProfile>(error);
      }
    });

final FutureProvider<GtexSurfaceState<TraderDashboard>>
traderDashboardProvider = FutureProvider<GtexSurfaceState<TraderDashboard>>((
  Ref ref,
) async {
  try {
    final TraderDashboard dashboard =
        await ref.watch(capitalTraderApiProvider).getDashboard();
    final GtexSurfaceState<TraderBalance> balanceState =
        traderBalanceSurfaceFromBackend(dashboard.balance);
    if (balanceState is GtexBlocked<TraderBalance>) {
      return GtexBlocked<TraderDashboard>(reason: balanceState.reason);
    }
    return GtexData<TraderDashboard>(data: dashboard);
  } catch (error) {
    return _blockedFromTraderError<TraderDashboard>(error);
  }
});

final FutureProvider<GtexSurfaceState<TraderBalance>> traderBalanceProvider =
    FutureProvider<GtexSurfaceState<TraderBalance>>((Ref ref) async {
      try {
        final TraderBalance balance =
            await ref.watch(capitalTraderApiProvider).getBalance();
        return traderBalanceSurfaceFromBackend(balance);
      } catch (error) {
        return _blockedFromTraderError<TraderBalance>(error);
      }
    });

final orderBookProvider = FutureProvider.family<
  GtexSurfaceState<TraderOrderBook>,
  String
>((Ref ref, String marketId) async {
  try {
    return GtexData<TraderOrderBook>(
      data: await ref.watch(capitalTraderApiProvider).getOrderBook(marketId),
    );
  } catch (error) {
    return _blockedFromTraderError<TraderOrderBook>(error);
  }
});

final FutureProvider<GtexSurfaceState<List<TraderOrder>>> activeOrdersProvider =
    FutureProvider<GtexSurfaceState<List<TraderOrder>>>((Ref ref) async {
      try {
        return GtexData<List<TraderOrder>>(
          data: await ref
              .watch(capitalTraderApiProvider)
              .getOrders(status: 'active'),
        );
      } catch (error) {
        return _blockedFromTraderError<List<TraderOrder>>(error);
      }
    });

final FutureProvider<GtexSurfaceState<List<TraderDispute>>>
traderDisputesProvider = FutureProvider<GtexSurfaceState<List<TraderDispute>>>((
  Ref ref,
) async {
  try {
    return GtexData<List<TraderDispute>>(
      data: await ref.watch(capitalTraderApiProvider).getDisputes(),
    );
  } catch (error) {
    return _blockedFromTraderError<List<TraderDispute>>(error);
  }
});

final FutureProvider<GtexSurfaceState<List<TraderSettlement>>>
traderSettlementsProvider =
    FutureProvider<GtexSurfaceState<List<TraderSettlement>>>((Ref ref) async {
      try {
        return GtexData<List<TraderSettlement>>(
          data: await ref.watch(capitalTraderApiProvider).getSettlements(),
        );
      } catch (error) {
        return _blockedFromTraderError<List<TraderSettlement>>(error);
      }
    });

GtexSurfaceState<TraderBalance> traderBalanceSurfaceFromBackend(
  TraderBalance balance,
) {
  if (balance.available == null) {
    return const GtexBlocked<TraderBalance>(reason: traderBalanceBlockedReason);
  }
  if (balance.currency.trim().isEmpty) {
    return const GtexBlocked<TraderBalance>(
      reason: 'Balance currency unavailable - sync in progress.',
    );
  }
  return GtexData<TraderBalance>(data: balance);
}

bool traderBalanceAllowsActions(GtexSurfaceState<TraderBalance> state) {
  return state is GtexData<TraderBalance> ||
      state is GtexConfirmed<TraderBalance>;
}

enum CapitalQuoteLockPhase { idle, locked, expired }

class CapitalQuoteLockState {
  const CapitalQuoteLockState._({
    required this.phase,
    this.quote,
    this.secondsRemaining,
    this.totalSeconds,
    this.message,
  });

  const CapitalQuoteLockState.idle()
    : this._(
        phase: CapitalQuoteLockPhase.idle,
        message: 'Request a backend quote to lock the price.',
      );

  const CapitalQuoteLockState.expired({TraderQuote? quote, String? message})
    : this._(
        phase: CapitalQuoteLockPhase.expired,
        quote: quote,
        secondsRemaining: 0,
        totalSeconds: 1,
        message: message ?? 'Quote expired - refresh for new price.',
      );

  const CapitalQuoteLockState.locked({
    required TraderQuote quote,
    required int secondsRemaining,
    int? totalSeconds,
  }) : this._(
         phase: CapitalQuoteLockPhase.locked,
         quote: quote,
         secondsRemaining: secondsRemaining,
         totalSeconds: totalSeconds,
         message: 'Quote locked by backend.',
       );

  factory CapitalQuoteLockState.fromBackend(
    TraderQuote? quote, {
    DateTime? now,
  }) {
    if (quote == null) {
      return const CapitalQuoteLockState.idle();
    }
    final int? secondsRemaining = quote.secondsRemaining(now: now);
    if (secondsRemaining == null) {
      return CapitalQuoteLockState.expired(
        quote: quote,
        message: 'Quote lock unavailable - refresh for backend lock.',
      );
    }
    if (secondsRemaining <= 0 || quote.isExpired(now: now)) {
      return CapitalQuoteLockState.expired(quote: quote);
    }
    return CapitalQuoteLockState.locked(
      quote: quote,
      secondsRemaining: secondsRemaining,
      totalSeconds: math.max(secondsRemaining, 1),
    );
  }

  final CapitalQuoteLockPhase phase;
  final TraderQuote? quote;
  final int? secondsRemaining;
  final int? totalSeconds;
  final String? message;

  bool get canPlaceOrder {
    return phase == CapitalQuoteLockPhase.locked &&
        quote != null &&
        (secondsRemaining ?? 0) > 0;
  }

  double get progress {
    final int remaining = secondsRemaining ?? 0;
    final int total = math.max(totalSeconds ?? remaining, 1);
    return (remaining / total).clamp(0, 1).toDouble();
  }
}

class QuoteLockNotifier extends Notifier<CapitalQuoteLockState> {
  @override
  CapitalQuoteLockState build() => const CapitalQuoteLockState.idle();

  void applyBackendQuote(TraderQuote quote, {DateTime? now}) {
    state = CapitalQuoteLockState.fromBackend(quote, now: now);
  }

  void refreshFromBackendClock({DateTime? now}) {
    state = CapitalQuoteLockState.fromBackend(state.quote, now: now);
  }

  void expire() {
    state = CapitalQuoteLockState.expired(quote: state.quote);
  }
}

final NotifierProvider<QuoteLockNotifier, CapitalQuoteLockState>
quoteLockProvider = NotifierProvider<QuoteLockNotifier, CapitalQuoteLockState>(
  QuoteLockNotifier.new,
);

GtexSurfaceState<T> _blockedFromTraderError<T>(Object error) {
  if (error is TraderContractGapException) {
    return GtexBlocked<T>(reason: error.message);
  }
  return GtexBlocked<T>(
    reason: 'Trader backend data unavailable - sync in progress.',
  );
}

enum TradingAgentType { valueInvestor, momentumTrader, arbitrage }

extension TradingAgentTypeMeta on TradingAgentType {
  String get label {
    return switch (this) {
      TradingAgentType.valueInvestor => 'Value Investor',
      TradingAgentType.momentumTrader => 'Momentum Trader',
      TradingAgentType.arbitrage => 'Arbitrage Agent',
    };
  }

  String get summary {
    return switch (this) {
      TradingAgentType.valueInvestor =>
        'Accumulates undervalued players after soft form patches.',
      TradingAgentType.momentumTrader =>
        'Leans into rising charts and rides the hot tape.',
      TradingAgentType.arbitrage =>
        'Balances pricing gaps before spreads get distorted.',
    };
  }

  String get guardrail {
    return switch (this) {
      TradingAgentType.valueInvestor =>
        'Keeps to capped inventory so one bot cannot corner a player.',
      TradingAgentType.momentumTrader =>
        'Stays below the live volume ceiling to avoid synthetic spikes.',
      TradingAgentType.arbitrage =>
        'Only tightens spread inside the platform range controls.',
    };
  }
}

enum WalletActivityTone { positive, negative, neutral, pending }

class ExchangeActionResult {
  const ExchangeActionResult({required this.message, this.isError = false});

  final String message;
  final bool isError;
}

class WalletBankAccount {
  const WalletBankAccount({
    required this.id,
    required this.bankName,
    required this.accountName,
    required this.accountNumber,
  });

  final String id;
  final String bankName;
  final String accountName;
  final String accountNumber;
}

class WalletActivityEntry {
  const WalletActivityEntry({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.amountLabel,
    required this.timeLabel,
    required this.statusLabel,
    required this.tone,
  });

  final String id;
  final String title;
  final String subtitle;
  final String amountLabel;
  final String timeLabel;
  final String statusLabel;
  final WalletActivityTone tone;
}

class MarketAgentProfile {
  const MarketAgentProfile({
    required this.type,
    required this.lastMove,
    required this.focusPlayerId,
    required this.volumeCapPercent,
    required this.liveSharePercent,
  });

  final TradingAgentType type;
  final String lastMove;
  final String focusPlayerId;
  final int volumeCapPercent;
  final int liveSharePercent;

  MarketAgentProfile copyWith({
    String? lastMove,
    String? focusPlayerId,
    int? volumeCapPercent,
    int? liveSharePercent,
  }) {
    return MarketAgentProfile(
      type: type,
      lastMove: lastMove ?? this.lastMove,
      focusPlayerId: focusPlayerId ?? this.focusPlayerId,
      volumeCapPercent: volumeCapPercent ?? this.volumeCapPercent,
      liveSharePercent: liveSharePercent ?? this.liveSharePercent,
    );
  }
}

class PlayerShareListing {
  const PlayerShareListing({
    required this.id,
    required this.name,
    required this.club,
    required this.position,
    required this.country,
    required this.age,
    required this.rating,
    required this.priceGtex,
    required this.anchorPriceGtex,
    required this.trendPercent,
    required this.volume,
    required this.sharesAvailable,
    required this.userShares,
    required this.performanceLabel,
    required this.performanceScore,
    required this.liquidityScore,
    required this.confidenceScore,
    required this.dominantAgent,
    required this.chartPoints,
  });

  final String id;
  final String name;
  final String club;
  final String position;
  final String country;
  final int age;
  final int rating;
  final double priceGtex;
  final double anchorPriceGtex;
  final double trendPercent;
  final int volume;
  final int sharesAvailable;
  final int userShares;
  final String performanceLabel;
  final double performanceScore;
  final double liquidityScore;
  final double confidenceScore;
  final TradingAgentType dominantAgent;
  final List<double> chartPoints;

  bool matchesFilter(TradingDeskFilter filter) {
    return switch (filter) {
      TradingDeskFilter.all => true,
      TradingDeskFilter.forwards => <String>{
        'ST',
        'RW',
        'LW',
        'CF',
      }.contains(position),
      TradingDeskFilter.midfielders => <String>{
        'CM',
        'CDM',
        'CAM',
      }.contains(position),
      TradingDeskFilter.defenders => <String>{
        'CB',
        'RB',
        'LB',
      }.contains(position),
      TradingDeskFilter.rising => trendPercent >= 3,
      TradingDeskFilter.owned => userShares > 0,
    };
  }

  PlayerShareListing copyWith({
    double? priceGtex,
    double? anchorPriceGtex,
    double? trendPercent,
    int? volume,
    int? sharesAvailable,
    int? userShares,
    String? performanceLabel,
    double? performanceScore,
    double? liquidityScore,
    double? confidenceScore,
    TradingAgentType? dominantAgent,
    List<double>? chartPoints,
  }) {
    return PlayerShareListing(
      id: id,
      name: name,
      club: club,
      position: position,
      country: country,
      age: age,
      rating: rating,
      priceGtex: priceGtex ?? this.priceGtex,
      anchorPriceGtex: anchorPriceGtex ?? this.anchorPriceGtex,
      trendPercent: trendPercent ?? this.trendPercent,
      volume: volume ?? this.volume,
      sharesAvailable: sharesAvailable ?? this.sharesAvailable,
      userShares: userShares ?? this.userShares,
      performanceLabel: performanceLabel ?? this.performanceLabel,
      performanceScore: performanceScore ?? this.performanceScore,
      liquidityScore: liquidityScore ?? this.liquidityScore,
      confidenceScore: confidenceScore ?? this.confidenceScore,
      dominantAgent: dominantAgent ?? this.dominantAgent,
      chartPoints: chartPoints ?? this.chartPoints,
    );
  }
}

class ExchangeHubState {
  const ExchangeHubState({
    required this.selectedBankId,
    required this.searchQuery,
    required this.activeFilter,
    required this.marketTick,
    required this.bankAccounts,
    required this.recentActivity,
    required this.players,
    required this.agents,
  });

  final String selectedBankId;
  final String searchQuery;
  final TradingDeskFilter activeFilter;
  final int marketTick;
  final List<WalletBankAccount> bankAccounts;
  final List<WalletActivityEntry> recentActivity;
  final List<PlayerShareListing> players;
  final List<MarketAgentProfile> agents;

  WalletBankAccount? get selectedBank {
    for (final WalletBankAccount account in bankAccounts) {
      if (account.id == selectedBankId) {
        return account;
      }
    }
    return bankAccounts.isEmpty ? null : bankAccounts.first;
  }

  List<PlayerShareListing> get filteredPlayers {
    final String query = searchQuery.trim().toLowerCase();
    return players
        .where((PlayerShareListing player) {
          if (!player.matchesFilter(activeFilter)) {
            return false;
          }
          if (query.isEmpty) {
            return true;
          }
          final String haystack =
              <String>[
                player.name,
                player.club,
                player.position,
                player.country,
              ].join(' ').toLowerCase();
          return haystack.contains(query);
        })
        .toList(growable: false);
  }

  PlayerShareListing? playerById(String id) {
    for (final PlayerShareListing player in players) {
      if (player.id == id) {
        return player;
      }
    }
    return null;
  }

  MarketAgentProfile? agentFor(TradingAgentType type) {
    for (final MarketAgentProfile agent in agents) {
      if (agent.type == type) {
        return agent;
      }
    }
    return null;
  }

  ExchangeHubState copyWith({
    String? selectedBankId,
    String? searchQuery,
    TradingDeskFilter? activeFilter,
    int? marketTick,
    List<WalletBankAccount>? bankAccounts,
    List<WalletActivityEntry>? recentActivity,
    List<PlayerShareListing>? players,
    List<MarketAgentProfile>? agents,
  }) {
    return ExchangeHubState(
      selectedBankId: selectedBankId ?? this.selectedBankId,
      searchQuery: searchQuery ?? this.searchQuery,
      activeFilter: activeFilter ?? this.activeFilter,
      marketTick: marketTick ?? this.marketTick,
      bankAccounts: bankAccounts ?? this.bankAccounts,
      recentActivity: recentActivity ?? this.recentActivity,
      players: players ?? this.players,
      agents: agents ?? this.agents,
    );
  }
}

class ExchangeHubNotifier extends Notifier<ExchangeHubState> {
  @override
  ExchangeHubState build() {
    return const ExchangeHubState(
      selectedBankId: '',
      searchQuery: '',
      activeFilter: TradingDeskFilter.all,
      marketTick: 0,
      bankAccounts: <WalletBankAccount>[],
      recentActivity: <WalletActivityEntry>[
        WalletActivityEntry(
          id: 'capital-wallet-sync-required',
          title: 'Capital backend sync required',
          subtitle:
              'Wallet, reserve, payout, and trader balances are hidden until backend-authoritative capital data is available.',
          amountLabel: 'Backend required',
          timeLabel: 'Now',
          statusLabel: 'Blocked',
          tone: WalletActivityTone.pending,
        ),
      ],
      players: <PlayerShareListing>[],
      agents: <MarketAgentProfile>[],
    );
  }

  void setSearchQuery(String value) {
    state = state.copyWith(searchQuery: value);
  }

  void setFilter(TradingDeskFilter filter) {
    state = state.copyWith(activeFilter: filter);
  }

  void selectBank(String bankId) {
    state = state.copyWith(selectedBankId: bankId);
  }

  ExchangeActionResult fundInstantWallet({
    required PaymentMethod method,
    required double amountNaira,
  }) {
    return _backendRequired();
  }

  ExchangeActionResult submitManualDeposit({required double amountNaira}) {
    return _backendRequired();
  }

  ExchangeActionResult convertToFanCoin(double amountGtex) {
    return _backendRequired();
  }

  ExchangeActionResult requestWithdrawal(double amountGtex) {
    return _backendRequired();
  }

  ExchangeActionResult buyShares({
    required String playerId,
    required int shares,
  }) {
    return _backendRequired();
  }

  ExchangeActionResult sellShares({
    required String playerId,
    required int shares,
  }) {
    return _backendRequired();
  }

  void tickMarket() {
    // Market and liquidity movement must come from backend capital services.
  }

  static ExchangeActionResult _backendRequired() {
    return const ExchangeActionResult(
      message:
          'Capital backend sync required before wallet or trader actions can run.',
      isError: true,
    );
  }
}

final NotifierProvider<ExchangeHubNotifier, ExchangeHubState>
exchangeHubProvider = NotifierProvider<ExchangeHubNotifier, ExchangeHubState>(
  ExchangeHubNotifier.new,
);
