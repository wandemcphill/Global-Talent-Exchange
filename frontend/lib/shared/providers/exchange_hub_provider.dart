import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';

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

enum PaymentMethod { paystack, korapay, bankTransfer }

extension PaymentMethodMeta on PaymentMethod {
  String get label {
    return switch (this) {
      PaymentMethod.paystack => 'Paystack',
      PaymentMethod.korapay => 'KoraPay',
      PaymentMethod.bankTransfer => 'Bank Transfer',
    };
  }

  String get subtitle {
    return switch (this) {
      PaymentMethod.paystack => 'Instant checkout',
      PaymentMethod.korapay => 'Instant settlement',
      PaymentMethod.bankTransfer => 'Manual treasury review',
    };
  }

  bool get isInstant => this != PaymentMethod.bankTransfer;
}

enum ComplianceTier { basic, verified }

extension ComplianceTierMeta on ComplianceTier {
  String get label {
    return switch (this) {
      ComplianceTier.basic => 'Basic',
      ComplianceTier.verified => 'Verified',
    };
  }

  int get dailyLimitNaira {
    return switch (this) {
      ComplianceTier.basic => 50000,
      ComplianceTier.verified => 500000,
    };
  }

  String get summary {
    return switch (this) {
      ComplianceTier.basic => 'Name, phone, and bank verification',
      ComplianceTier.verified => 'Adds stronger checks for larger payouts',
    };
  }
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
    required this.walletBalanceGtex,
    required this.fanCoinBalance,
    required this.weeklySpendNaira,
    required this.matchesWatched,
    required this.tradesMade,
    required this.nairaPerGtex,
    required this.kycTier,
    required this.withdrawalUsedTodayNaira,
    required this.selectedBankId,
    required this.searchQuery,
    required this.activeFilter,
    required this.marketTick,
    required this.bankAccounts,
    required this.recentActivity,
    required this.players,
    required this.agents,
  });

  final double walletBalanceGtex;
  final int fanCoinBalance;
  final int weeklySpendNaira;
  final int matchesWatched;
  final int tradesMade;
  final int nairaPerGtex;
  final ComplianceTier kycTier;
  final int withdrawalUsedTodayNaira;
  final String selectedBankId;
  final String searchQuery;
  final TradingDeskFilter activeFilter;
  final int marketTick;
  final List<WalletBankAccount> bankAccounts;
  final List<WalletActivityEntry> recentActivity;
  final List<PlayerShareListing> players;
  final List<MarketAgentProfile> agents;

  int get remainingWithdrawalLimitNaira =>
      math.max(0, kycTier.dailyLimitNaira - withdrawalUsedTodayNaira);

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
    double? walletBalanceGtex,
    int? fanCoinBalance,
    int? weeklySpendNaira,
    int? matchesWatched,
    int? tradesMade,
    int? nairaPerGtex,
    ComplianceTier? kycTier,
    int? withdrawalUsedTodayNaira,
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
      walletBalanceGtex: walletBalanceGtex ?? this.walletBalanceGtex,
      fanCoinBalance: fanCoinBalance ?? this.fanCoinBalance,
      weeklySpendNaira: weeklySpendNaira ?? this.weeklySpendNaira,
      matchesWatched: matchesWatched ?? this.matchesWatched,
      tradesMade: tradesMade ?? this.tradesMade,
      nairaPerGtex: nairaPerGtex ?? this.nairaPerGtex,
      kycTier: kycTier ?? this.kycTier,
      withdrawalUsedTodayNaira:
          withdrawalUsedTodayNaira ?? this.withdrawalUsedTodayNaira,
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
  static const int _nairaPerGtex = 1000;

  @override
  ExchangeHubState build() {
    final List<PlayerShareListing> players = <PlayerShareListing>[
      const PlayerShareListing(
        id: 'market-mbappe',
        name: 'Kylian Mbappe',
        club: 'Madrid Whites',
        position: 'ST',
        country: 'France',
        age: 27,
        rating: 93,
        priceGtex: 75,
        anchorPriceGtex: 72,
        trendPercent: 5.0,
        volume: 1880,
        sharesAvailable: 320,
        userShares: 0,
        performanceLabel: 'Explosive form',
        performanceScore: 0.92,
        liquidityScore: 0.96,
        confidenceScore: 0.94,
        dominantAgent: TradingAgentType.momentumTrader,
        chartPoints: <double>[68, 69, 70, 71, 72, 73, 74, 75],
      ),
      const PlayerShareListing(
        id: 'market-yamal',
        name: 'Lamine Yamal',
        club: 'Barcelona Blau',
        position: 'RW',
        country: 'Spain',
        age: 19,
        rating: 89,
        priceGtex: 49,
        anchorPriceGtex: 46,
        trendPercent: 6.8,
        volume: 1710,
        sharesAvailable: 420,
        userShares: 0,
        performanceLabel: 'Skyline momentum',
        performanceScore: 0.90,
        liquidityScore: 0.90,
        confidenceScore: 0.91,
        dominantAgent: TradingAgentType.momentumTrader,
        chartPoints: <double>[41, 42, 43, 45, 45, 46, 48, 49],
      ),
      const PlayerShareListing(
        id: 'market-palmer',
        name: 'Cole Palmer',
        club: 'London Blue',
        position: 'CAM',
        country: 'England',
        age: 24,
        rating: 86,
        priceGtex: 8.4,
        anchorPriceGtex: 8.0,
        trendPercent: 2.4,
        volume: 940,
        sharesAvailable: 680,
        userShares: 1,
        performanceLabel: 'Reliable output',
        performanceScore: 0.79,
        liquidityScore: 0.72,
        confidenceScore: 0.80,
        dominantAgent: TradingAgentType.valueInvestor,
        chartPoints: <double>[7.4, 7.5, 7.7, 7.8, 8.0, 8.1, 8.2, 8.4],
      ),
      const PlayerShareListing(
        id: 'market-rice',
        name: 'Declan Rice',
        club: 'North London Red',
        position: 'CM',
        country: 'England',
        age: 27,
        rating: 88,
        priceGtex: 12.2,
        anchorPriceGtex: 12.8,
        trendPercent: -1.4,
        volume: 820,
        sharesAvailable: 540,
        userShares: 0,
        performanceLabel: 'Cooling week',
        performanceScore: 0.67,
        liquidityScore: 0.70,
        confidenceScore: 0.75,
        dominantAgent: TradingAgentType.arbitrage,
        chartPoints: <double>[13.4, 13.2, 13.0, 12.9, 12.8, 12.6, 12.4, 12.2],
      ),
      const PlayerShareListing(
        id: 'market-lookman',
        name: 'Ademola Lookman',
        club: 'Bergamo Pulse',
        position: 'LW',
        country: 'Nigeria',
        age: 28,
        rating: 85,
        priceGtex: 9.8,
        anchorPriceGtex: 9.2,
        trendPercent: 3.1,
        volume: 760,
        sharesAvailable: 610,
        userShares: 0,
        performanceLabel: 'Sharp finishing',
        performanceScore: 0.77,
        liquidityScore: 0.68,
        confidenceScore: 0.73,
        dominantAgent: TradingAgentType.valueInvestor,
        chartPoints: <double>[8.6, 8.7, 8.8, 9.0, 9.2, 9.4, 9.6, 9.8],
      ),
      const PlayerShareListing(
        id: 'market-saliba',
        name: 'William Saliba',
        club: 'North London Red',
        position: 'CB',
        country: 'France',
        age: 25,
        rating: 87,
        priceGtex: 10.6,
        anchorPriceGtex: 10.4,
        trendPercent: 1.8,
        volume: 640,
        sharesAvailable: 570,
        userShares: 2,
        performanceLabel: 'Locked-in defense',
        performanceScore: 0.74,
        liquidityScore: 0.66,
        confidenceScore: 0.77,
        dominantAgent: TradingAgentType.arbitrage,
        chartPoints: <double>[9.6, 9.8, 10.0, 10.1, 10.2, 10.3, 10.5, 10.6],
      ),
    ];

    return ExchangeHubState(
      walletBalanceGtex: 12.5,
      fanCoinBalance: 850,
      weeklySpendNaira: 18500,
      matchesWatched: 14,
      tradesMade: 9,
      nairaPerGtex: _nairaPerGtex,
      kycTier: ComplianceTier.basic,
      withdrawalUsedTodayNaira: 18000,
      selectedBankId: 'bank-kuda',
      searchQuery: '',
      activeFilter: TradingDeskFilter.all,
      marketTick: 0,
      bankAccounts: const <WalletBankAccount>[
        WalletBankAccount(
          id: 'bank-kuda',
          bankName: 'Kuda Bank',
          accountName: 'Ayo Manager',
          accountNumber: '1022334455',
        ),
        WalletBankAccount(
          id: 'bank-gtbank',
          bankName: 'GTBank',
          accountName: 'Ayo Manager',
          accountNumber: '0129988776',
        ),
      ],
      recentActivity: const <WalletActivityEntry>[
        WalletActivityEntry(
          id: 'activity-deposit',
          title: 'Paystack deposit',
          subtitle: 'Instant top-up landed before the market rush.',
          amountLabel: '+6 GTex',
          timeLabel: '18m ago',
          statusLabel: 'Settled',
          tone: WalletActivityTone.positive,
        ),
        WalletActivityEntry(
          id: 'activity-palmer',
          title: 'Cole Palmer shares',
          subtitle: 'Bought 1 share as midfield demand stayed calm.',
          amountLabel: '-8.4 GTex',
          timeLabel: '1h ago',
          statusLabel: 'Trade',
          tone: WalletActivityTone.negative,
        ),
        WalletActivityEntry(
          id: 'activity-convert',
          title: 'Fan Coin conversion',
          subtitle: 'Converted 2 GTex for watch-party spending.',
          amountLabel: '+200 Fan Coin',
          timeLabel: 'Today',
          statusLabel: 'Closed-loop',
          tone: WalletActivityTone.neutral,
        ),
        WalletActivityEntry(
          id: 'activity-manual',
          title: 'Bank transfer lodged',
          subtitle: 'Manual treasury confirmation is still pending.',
          amountLabel: '+4 GTex',
          timeLabel: 'Yesterday',
          statusLabel: 'Pending review',
          tone: WalletActivityTone.pending,
        ),
      ],
      players: players,
      agents: _buildAgents(players),
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
    if (amountNaira <= 0) {
      return const ExchangeActionResult(
        message: 'Enter a valid deposit amount.',
        isError: true,
      );
    }
    final double credited = amountNaira / state.nairaPerGtex;
    state = state.copyWith(
      walletBalanceGtex: state.walletBalanceGtex + credited,
      recentActivity: _prependActivity(
        WalletActivityEntry(
          id: 'activity-instant-${state.marketTick}-${method.name}',
          title: '${method.label} deposit',
          subtitle: 'Instant rails credited your wallet immediately.',
          amountLabel: '+${_formatAmount(credited)} GTex',
          timeLabel: 'Now',
          statusLabel: 'Settled',
          tone: WalletActivityTone.positive,
        ),
      ),
    );
    return ExchangeActionResult(message: '${method.label} deposit completed.');
  }

  ExchangeActionResult submitManualDeposit({required double amountNaira}) {
    if (amountNaira <= 0) {
      return const ExchangeActionResult(
        message: 'Enter a valid deposit amount.',
        isError: true,
      );
    }
    final double credited = amountNaira / state.nairaPerGtex;
    state = state.copyWith(
      recentActivity: _prependActivity(
        WalletActivityEntry(
          id: 'activity-manual-${state.marketTick}',
          title: 'Bank transfer submitted',
          subtitle: 'Receipt uploaded for treasury review and manual matching.',
          amountLabel: '+${_formatAmount(credited)} GTex',
          timeLabel: 'Now',
          statusLabel: 'Pending review',
          tone: WalletActivityTone.pending,
        ),
      ),
    );
    return const ExchangeActionResult(
      message: 'Manual deposit submitted for review.',
    );
  }

  ExchangeActionResult convertToFanCoin(double amountGtex) {
    if (amountGtex <= 0) {
      return const ExchangeActionResult(
        message: 'Enter a valid conversion amount.',
        isError: true,
      );
    }
    if (amountGtex > state.walletBalanceGtex) {
      return const ExchangeActionResult(
        message: 'Not enough GTex to convert.',
        isError: true,
      );
    }
    final int fanCoin = (amountGtex * 100).round();
    state = state.copyWith(
      walletBalanceGtex: state.walletBalanceGtex - amountGtex,
      fanCoinBalance: state.fanCoinBalance + fanCoin,
      weeklySpendNaira:
          state.weeklySpendNaira + (amountGtex * state.nairaPerGtex).round(),
      recentActivity: _prependActivity(
        WalletActivityEntry(
          id: 'activity-convert-${state.marketTick}',
          title: 'GTex to Fan Coin',
          subtitle: 'Closed-loop currency converted for in-app spend only.',
          amountLabel: '+$fanCoin Fan Coin',
          timeLabel: 'Now',
          statusLabel: 'Closed-loop',
          tone: WalletActivityTone.neutral,
        ),
      ),
    );
    return const ExchangeActionResult(message: 'Fan Coin balance updated.');
  }

  ExchangeActionResult requestWithdrawal(double amountGtex) {
    if (amountGtex <= 0) {
      return const ExchangeActionResult(
        message: 'Enter a valid withdrawal amount.',
        isError: true,
      );
    }
    if (amountGtex > state.walletBalanceGtex) {
      return const ExchangeActionResult(
        message: 'Not enough GTex available for withdrawal.',
        isError: true,
      );
    }
    if (state.selectedBank == null) {
      return const ExchangeActionResult(
        message: 'Select a bank account before requesting withdrawal.',
        isError: true,
      );
    }
    final int payoutNaira = (amountGtex * state.nairaPerGtex).round();
    if (payoutNaira > state.remainingWithdrawalLimitNaira) {
      return ExchangeActionResult(
        message:
            'This payout exceeds your ${state.kycTier.label.toLowerCase()} tier limit.',
        isError: true,
      );
    }
    state = state.copyWith(
      walletBalanceGtex: state.walletBalanceGtex - amountGtex,
      withdrawalUsedTodayNaira: state.withdrawalUsedTodayNaira + payoutNaira,
      recentActivity: _prependActivity(
        WalletActivityEntry(
          id: 'activity-withdraw-${state.marketTick}',
          title: 'Withdrawal requested',
          subtitle:
              'Payout queued to ${state.selectedBank!.bankName} ${state.selectedBank!.accountNumber}.',
          amountLabel: '-${_formatAmount(amountGtex)} GTex',
          timeLabel: 'Now',
          statusLabel: 'Processing',
          tone: WalletActivityTone.negative,
        ),
      ),
    );
    return const ExchangeActionResult(message: 'Withdrawal request submitted.');
  }

  ExchangeActionResult buyShares({
    required String playerId,
    required int shares,
  }) {
    final PlayerShareListing? player = state.playerById(playerId);
    if (player == null) {
      return const ExchangeActionResult(
        message: 'Player not found.',
        isError: true,
      );
    }
    if (shares <= 0) {
      return const ExchangeActionResult(
        message: 'Choose at least one share.',
        isError: true,
      );
    }
    if (shares > player.sharesAvailable) {
      return const ExchangeActionResult(
        message: 'Not enough shares available.',
        isError: true,
      );
    }
    final double cost = player.priceGtex * shares;
    if (cost > state.walletBalanceGtex) {
      return const ExchangeActionResult(
        message: 'Wallet balance is too low for this order.',
        isError: true,
      );
    }

    final List<PlayerShareListing> updatedPlayers = state.players
        .map((PlayerShareListing current) {
          if (current.id != playerId) {
            return current;
          }
          final double nextPrice = _boundedPrice(
            current.priceGtex + (0.2 * shares),
            current.anchorPriceGtex,
          );
          final List<double> nextChart = _pushPoint(
            current.chartPoints,
            nextPrice,
          );
          final double nextTrend = _nextTrend(current.priceGtex, nextPrice);
          return current.copyWith(
            priceGtex: nextPrice,
            trendPercent: nextTrend,
            volume: current.volume + (shares * 38),
            sharesAvailable: math.max(0, current.sharesAvailable - shares),
            userShares: current.userShares + shares,
            chartPoints: nextChart,
          );
        })
        .toList(growable: false);

    state = state.copyWith(
      walletBalanceGtex: state.walletBalanceGtex - cost,
      weeklySpendNaira:
          state.weeklySpendNaira + (cost * state.nairaPerGtex).round(),
      tradesMade: state.tradesMade + 1,
      players: updatedPlayers,
      recentActivity: _prependActivity(
        WalletActivityEntry(
          id: 'activity-buy-${state.marketTick}-$playerId',
          title: '${player.name} shares',
          subtitle:
              'Bought $shares share${shares == 1 ? '' : 's'} into the live market.',
          amountLabel: '-${_formatAmount(cost)} GTex',
          timeLabel: 'Now',
          statusLabel: 'Trade',
          tone: WalletActivityTone.negative,
        ),
      ),
    );
    return ExchangeActionResult(
      message:
          'Bought $shares share${shares == 1 ? '' : 's'} of ${player.name}.',
    );
  }

  ExchangeActionResult sellShares({
    required String playerId,
    required int shares,
  }) {
    final PlayerShareListing? player = state.playerById(playerId);
    if (player == null) {
      return const ExchangeActionResult(
        message: 'Player not found.',
        isError: true,
      );
    }
    if (shares <= 0) {
      return const ExchangeActionResult(
        message: 'Choose at least one share.',
        isError: true,
      );
    }
    if (shares > player.userShares) {
      return const ExchangeActionResult(
        message: 'You do not own that many shares.',
        isError: true,
      );
    }

    final double proceeds = player.priceGtex * shares;
    final List<PlayerShareListing> updatedPlayers = state.players
        .map((PlayerShareListing current) {
          if (current.id != playerId) {
            return current;
          }
          final double nextPrice = _boundedPrice(
            current.priceGtex - (0.16 * shares),
            current.anchorPriceGtex,
          );
          final List<double> nextChart = _pushPoint(
            current.chartPoints,
            nextPrice,
          );
          final double nextTrend = _nextTrend(current.priceGtex, nextPrice);
          return current.copyWith(
            priceGtex: nextPrice,
            trendPercent: nextTrend,
            volume: math.max(120, current.volume + (shares * 24)),
            sharesAvailable: current.sharesAvailable + shares,
            userShares: current.userShares - shares,
            chartPoints: nextChart,
          );
        })
        .toList(growable: false);

    state = state.copyWith(
      walletBalanceGtex: state.walletBalanceGtex + proceeds,
      tradesMade: state.tradesMade + 1,
      players: updatedPlayers,
      recentActivity: _prependActivity(
        WalletActivityEntry(
          id: 'activity-sell-${state.marketTick}-$playerId',
          title: '${player.name} shares',
          subtitle:
              'Sold $shares share${shares == 1 ? '' : 's'} back into the market.',
          amountLabel: '+${_formatAmount(proceeds)} GTex',
          timeLabel: 'Now',
          statusLabel: 'Trade',
          tone: WalletActivityTone.positive,
        ),
      ),
    );
    return ExchangeActionResult(
      message: 'Sold $shares share${shares == 1 ? '' : 's'} of ${player.name}.',
    );
  }

  void tickMarket() {
    final int nextTick = state.marketTick + 1;
    final List<PlayerShareListing> nextPlayers = state.players
        .asMap()
        .entries
        .map((MapEntry<int, PlayerShareListing> entry) {
          return _advanceListing(
            listing: entry.value,
            index: entry.key,
            nextTick: nextTick,
          );
        })
        .toList(growable: false);
    state = state.copyWith(
      marketTick: nextTick,
      players: nextPlayers,
      agents: _buildAgents(nextPlayers, tick: nextTick),
    );
  }

  List<WalletActivityEntry> _prependActivity(WalletActivityEntry entry) {
    return <WalletActivityEntry>[
      entry,
      ...state.recentActivity,
    ].take(6).toList(growable: false);
  }

  PlayerShareListing _advanceListing({
    required PlayerShareListing listing,
    required int index,
    required int nextTick,
  }) {
    final double previousPrice = listing.priceGtex;
    final double sentiment = listing.performanceScore - 0.5;
    double delta;
    int volumeDelta;

    switch (listing.dominantAgent) {
      case TradingAgentType.valueInvestor:
        final bool discounted = listing.priceGtex < listing.anchorPriceGtex;
        delta = discounted ? 0.28 : -0.08;
        delta += sentiment * 0.5;
        volumeDelta = 12 + ((nextTick + index) % 5) * 9;
      case TradingAgentType.momentumTrader:
        delta = 0.24 + (sentiment * 0.7);
        if ((nextTick + index) % 4 == 0) {
          delta += 0.3;
        }
        volumeDelta = 18 + ((nextTick + index) % 4) * 14;
      case TradingAgentType.arbitrage:
        final double spread = listing.anchorPriceGtex - listing.priceGtex;
        delta = (spread * 0.12) + (((nextTick + index).isEven ? 1 : -1) * 0.08);
        volumeDelta = 10 + ((nextTick + index) % 3) * 11;
    }

    final double nextPrice = _boundedPrice(
      listing.priceGtex + delta,
      listing.anchorPriceGtex,
    );
    final double nextTrend = _nextTrend(previousPrice, nextPrice);
    final List<double> nextChart = _pushPoint(listing.chartPoints, nextPrice);
    return listing.copyWith(
      priceGtex: nextPrice,
      trendPercent: nextTrend,
      volume: math.max(120, listing.volume + volumeDelta),
      chartPoints: nextChart,
    );
  }

  static List<MarketAgentProfile> _buildAgents(
    List<PlayerShareListing> players, {
    int tick = 0,
  }) {
    PlayerShareListing focusFor(TradingAgentType type) {
      final List<PlayerShareListing> scoped = players
          .where((PlayerShareListing player) => player.dominantAgent == type)
          .toList(growable: false);
      return scoped[(tick ~/ 2) % scoped.length];
    }

    final PlayerShareListing valuePick = focusFor(
      TradingAgentType.valueInvestor,
    );
    final PlayerShareListing momentumPick = focusFor(
      TradingAgentType.momentumTrader,
    );
    final PlayerShareListing arbitragePick = focusFor(
      TradingAgentType.arbitrage,
    );

    return <MarketAgentProfile>[
      MarketAgentProfile(
        type: TradingAgentType.valueInvestor,
        lastMove:
            'Accumulating ${valuePick.name} after a calmer pricing window.',
        focusPlayerId: valuePick.id,
        volumeCapPercent: 18,
        liveSharePercent: 11 + (tick % 5),
      ),
      MarketAgentProfile(
        type: TradingAgentType.momentumTrader,
        lastMove:
            'Riding ${momentumPick.name} while the chart stays above +3%.',
        focusPlayerId: momentumPick.id,
        volumeCapPercent: 22,
        liveSharePercent: 14 + (tick % 6),
      ),
      MarketAgentProfile(
        type: TradingAgentType.arbitrage,
        lastMove:
            'Tightening spread around ${arbitragePick.name} without forcing a spike.',
        focusPlayerId: arbitragePick.id,
        volumeCapPercent: 16,
        liveSharePercent: 8 + (tick % 4),
      ),
    ];
  }

  static double _boundedPrice(double value, double anchorPrice) {
    final double floor = math.max(4, anchorPrice * 0.76);
    final double ceiling = math.max(floor + 1, anchorPrice * 1.28);
    return value.clamp(floor, ceiling).toDouble();
  }

  static List<double> _pushPoint(List<double> chartPoints, double nextPrice) {
    final List<double> next = <double>[
      ...chartPoints,
      double.parse(nextPrice.toStringAsFixed(1)),
    ];
    if (next.length <= 10) {
      return next;
    }
    return next.sublist(next.length - 10);
  }

  static double _nextTrend(double previousPrice, double nextPrice) {
    if (previousPrice == 0) {
      return 0;
    }
    return (((nextPrice - previousPrice) / previousPrice) * 100)
        .clamp(-9.9, 9.9)
        .toDouble();
  }

  static String _formatAmount(double value) {
    if (value == value.truncateToDouble()) {
      return value.toStringAsFixed(0);
    }
    return value.toStringAsFixed(1);
  }
}

final NotifierProvider<ExchangeHubNotifier, ExchangeHubState>
exchangeHubProvider = NotifierProvider<ExchangeHubNotifier, ExchangeHubState>(
  ExchangeHubNotifier.new,
);
