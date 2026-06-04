import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/player_service.dart';
import '../../features/capital/wallet/data/capital_wallet_api.dart';
import '../../features/capital/wallet/providers/capital_wallet_providers.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../models/player.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';

const int _initialMarketResultWindow = 24;
const int _marketResultWindowStep = 24;

class MarketSearchQueryController extends Notifier<String> {
  @override
  String build() => '';

  void setQuery(String value) {
    state = value;
  }
}

class MarketResultWindowController extends Notifier<int> {
  @override
  int build() => _initialMarketResultWindow;

  void reset() {
    if (state != _initialMarketResultWindow) {
      state = _initialMarketResultWindow;
    }
  }

  void loadMore() {
    state += _marketResultWindowStep;
  }
}

class PlayerShareSummary {
  const PlayerShareSummary({
    required this.playerId,
    required this.playerName,
    required this.position,
    required this.nationality,
    required this.currentClubName,
    required this.age,
    required this.currentValueCredits,
    required this.marketInterestScore,
    required this.marketStatus,
    required this.marketMessage,
    this.sharePriceCoin,
    this.totalShares,
    this.circulatingShares,
  });

  final String playerId;
  final String playerName;
  final String? position;
  final String? nationality;
  final String? currentClubName;
  final int? age;
  final double? currentValueCredits;
  final int? marketInterestScore;
  final String marketStatus;
  final String marketMessage;
  final double? sharePriceCoin;
  final int? totalShares;
  final int? circulatingShares;

  bool get isTradable => marketStatus.toLowerCase() == 'active';
}

class PlayerShareHoldingSummary {
  const PlayerShareHoldingSummary({
    required this.playerId,
    required this.shareCount,
    required this.averageCostCoin,
    required this.dividendsEarnedCoin,
  });

  final String playerId;
  final int shareCount;
  final double averageCostCoin;
  final double dividendsEarnedCoin;
}

class TransferListingSummary {
  const TransferListingSummary({
    required this.id,
    required this.playerId,
    required this.playerName,
    required this.currentClubName,
    required this.currentHighestBid,
    required this.basePrice,
    required this.status,
    required this.watchlistCount,
    required this.bidCount,
    required this.marketSignal,
    required this.channel,
    required this.timeRemaining,
  });

  final String id;
  final String playerId;
  final String playerName;
  final String? currentClubName;
  final double currentHighestBid;
  final double basePrice;
  final String status;
  final int watchlistCount;
  final int bidCount;
  final String marketSignal;
  final String channel;
  final int timeRemaining;
}

class MarketWalletSnapshot {
  const MarketWalletSnapshot({
    required this.coinBalance,
    required this.creditBalance,
    required this.totalEquity,
    required this.canTradeMarket,
    required this.canDeposit,
    required this.canWithdraw,
    required this.complianceMessage,
  });

  final double coinBalance;
  final double creditBalance;
  final double totalEquity;
  final bool canTradeMarket;
  final bool canDeposit;
  final bool canWithdraw;
  final String complianceMessage;
}

class MarketDashboardData {
  const MarketDashboardData({
    required this.playerShares,
    required this.holdings,
    required this.transferListings,
    required this.wallet,
    required this.authenticated,
    required this.warnings,
    this.searchQuery = '',
    this.totalTradablePlayerShares,
    this.hasMorePlayerShareResults = false,
  });

  final List<PlayerShareSummary> playerShares;
  final List<PlayerShareHoldingSummary> holdings;
  final List<TransferListingSummary> transferListings;
  final MarketWalletSnapshot? wallet;
  final bool authenticated;
  final List<String> warnings;
  final String searchQuery;
  final int? totalTradablePlayerShares;
  final bool hasMorePlayerShareResults;

  List<PlayerShareSummary> get tradablePlayerShares => playerShares
      .where((PlayerShareSummary item) => item.isTradable)
      .toList(growable: false);

  List<PlayerShareSummary> get upcomingPlayerShares => playerShares
      .where((PlayerShareSummary item) => !item.isTradable)
      .toList(growable: false);

  List<PlayerShareSummary> get discoveryOnlyPlayerShares =>
      upcomingPlayerShares;
}

class PlayerShareDetailData {
  const PlayerShareDetailData({
    required this.summary,
    required this.playerDetail,
    required this.events,
    required this.listings,
  });

  final PlayerShareSummary summary;
  final JsonMap playerDetail;
  final List<JsonMap> events;
  final List<TransferListingSummary> listings;
}

final NotifierProvider<MarketSearchQueryController, String>
marketSearchQueryProvider =
    NotifierProvider<MarketSearchQueryController, String>(
      MarketSearchQueryController.new,
    );

final NotifierProvider<MarketResultWindowController, int>
marketResultWindowProvider =
    NotifierProvider<MarketResultWindowController, int>(
      MarketResultWindowController.new,
    );

final FutureProvider<MarketDashboardData>
marketDashboardProvider = FutureProvider<MarketDashboardData>((Ref ref) async {
  final GteAuthedApi api = ref.watch(authedApiProvider);
  final PlayerService playerService = ref.watch(livePlayerServiceProvider);
  bool authenticated = ref.watch(isAuthenticatedProvider);
  final String query = ref.watch(marketSearchQueryProvider).trim();
  final int resultWindow = ref.watch(marketResultWindowProvider);
  final List<dynamic> marketPayloads = await Future.wait<dynamic>(
    <Future<dynamic>>[
      api.getMap(
        '/players/markets',
        auth: false,
        query: <String, Object?>{
          'page': 1,
          'per_page': resultWindow,
          if (query.isNotEmpty) 'search': query,
        },
      ),
      api.getList('/api/transfer-market/listings', auth: false),
      query.isEmpty
          ? Future<PaginatedPlayers?>.value(null)
          : playerService.getPlayers(search: query, limit: resultWindow),
    ],
    eagerError: true,
  );
  final JsonMap playerMarketPayload = jsonMap(
    marketPayloads[0],
    label: 'player share markets',
  );
  final List<PlayerShareSummary> tradablePlayers = jsonMapList(
    playerMarketPayload['items'],
    label: 'player share market items',
  ).map(_playerShareSummaryFromMarketListItem).toList(growable: false);
  final Set<String> tradablePlayerIds =
      tradablePlayers.map((PlayerShareSummary item) => item.playerId).toSet();
  final PaginatedPlayers? discoveryPage =
      marketPayloads[2] as PaginatedPlayers?;
  final List<PlayerShareSummary> discoveryOnlyPlayers =
      (discoveryPage?.players ?? const <Player>[])
          .where((Player player) => !tradablePlayerIds.contains(player.id))
          .map(_playerShareSummaryFromDiscoveryPlayer)
          .toList(growable: false);
  final List<String> warnings = <String>[];
  final int totalTradablePlayerShares =
      playerMarketPayload['total'] == null
          ? tradablePlayers.length
          : intValue(playerMarketPayload['total']);

  List<PlayerShareHoldingSummary> holdings =
      const <PlayerShareHoldingSummary>[];
  MarketWalletSnapshot? wallet;
  if (authenticated) {
    try {
      final List<dynamic> holdingsPayload = await api.getList(
        '/players/me/shares/holdings',
      );
      holdings = holdingsPayload
          .map((dynamic item) => jsonMap(item, label: 'share holding'))
          .map(
            (JsonMap item) => PlayerShareHoldingSummary(
              playerId: stringValue(item['player_id']),
              shareCount: intValue(item['share_count']),
              averageCostCoin: numberValue(item['average_cost_coin']),
              dividendsEarnedCoin: numberValue(item['dividends_earned_coin']),
            ),
          )
          .toList(growable: false);
    } catch (error) {
      if (await _expireProtectedMarketSession(ref, error)) {
        authenticated = false;
        holdings = const <PlayerShareHoldingSummary>[];
      } else {
        warnings.add(
          'Share holdings unavailable: ${AppFeedback.messageFor(error)}',
        );
      }
    }

    if (authenticated) {
      try {
        final CapitalWalletMarketSnapshot walletSnapshot =
            await ref.read(capitalWalletApiProvider).fetchMarketSnapshot();
        wallet = MarketWalletSnapshot(
          coinBalance: walletSnapshot.coinAvailableBalance,
          creditBalance: walletSnapshot.creditAvailableBalance,
          totalEquity: walletSnapshot.totalCoinBalance,
          canTradeMarket: walletSnapshot.canTradeMarket,
          canDeposit: walletSnapshot.canDeposit,
          canWithdraw: walletSnapshot.canWithdraw,
          complianceMessage: walletSnapshot.complianceMessage,
        );
      } catch (error) {
        if (await _expireProtectedMarketSession(ref, error)) {
          authenticated = false;
          holdings = const <PlayerShareHoldingSummary>[];
          wallet = null;
        } else {
          warnings.add(
            'Wallet/compliance unavailable: ${AppFeedback.messageFor(error)}',
          );
        }
      }
    }
  }

  final List<TransferListingSummary> transferListings = (marketPayloads[1]
          as List<dynamic>)
      .map((dynamic item) => jsonMap(item, label: 'transfer listing'))
      .map(_transferListingFromJson)
      .toList(growable: false);

  return MarketDashboardData(
    playerShares: <PlayerShareSummary>[
      ...tradablePlayers,
      ...discoveryOnlyPlayers,
    ],
    holdings: holdings,
    transferListings: transferListings,
    wallet: wallet,
    authenticated: authenticated,
    warnings: warnings,
    searchQuery: query,
    totalTradablePlayerShares: totalTradablePlayerShares,
    hasMorePlayerShareResults:
        tradablePlayers.length < totalTradablePlayerShares ||
        (discoveryPage?.hasMore ?? false),
  );
});

PlayerShareSummary _playerShareSummaryFromMarketListItem(JsonMap item) {
  final String marketStatus = stringValue(item['status'], fallback: 'active');
  return PlayerShareSummary(
    playerId: stringValue(item['player_id']),
    playerName: stringValue(item['player_name']),
    position: stringOrNullValue(item['position']),
    nationality: stringOrNullValue(item['nationality']),
    currentClubName: stringOrNullValue(item['current_club_name']),
    age: item['age'] == null ? null : intValue(item['age']),
    currentValueCredits: null,
    marketInterestScore: null,
    marketStatus: marketStatus,
    marketMessage:
        marketStatus.toLowerCase() == 'active'
            ? 'Share market is live.'
            : 'Share market is ${marketStatus.toLowerCase()}.',
    sharePriceCoin: numberValue(item['share_price_coin']),
    totalShares: intValue(item['total_shares']),
    circulatingShares: intValue(item['circulating_shares']),
  );
}

PlayerShareSummary _playerShareSummaryFromDiscoveryPlayer(Player player) {
  return PlayerShareSummary(
    playerId: player.id,
    playerName: player.name,
    position: player.position,
    nationality: player.country,
    currentClubName: player.club,
    age: player.age,
    currentValueCredits: player.currentValueCredits,
    marketInterestScore: player.marketInterestScore,
    marketStatus: 'inactive',
    marketMessage:
        'No live buyable share market was returned for this player on the current search.',
  );
}

Future<bool> _expireProtectedMarketSession(Ref ref, Object error) async {
  if (error is! GteApiException || error.type != GteApiErrorType.unauthorized) {
    return false;
  }
  await ref.read(exchangeApiClientProvider).logout();
  await ref.read(appSessionControllerProvider.notifier).clear();
  return true;
}

final playerShareDetailProvider =
    FutureProvider.family<PlayerShareDetailData, PlayerShareSummary>((
      Ref ref,
      PlayerShareSummary summary,
    ) async {
      final GteAuthedApi api = ref.watch(authedApiProvider);
      final JsonMap detail = await api.getMap(
        '/players/real-universe/${summary.playerId}',
        auth: false,
      );
      List<JsonMap> events = const <JsonMap>[];
      try {
        events = (await api.getList(
              '/players/${summary.playerId}/shares/events',
              auth: false,
            ))
            .map((dynamic item) => jsonMap(item, label: 'share event'))
            .toList(growable: false);
      } on GteApiException catch (error) {
        if (error.type != GteApiErrorType.notFound) {
          rethrow;
        }
      }
      final List<TransferListingSummary> listings = (await api.getList(
            '/api/transfer-market/listings',
            auth: false,
            query: <String, Object?>{'player_id': summary.playerId},
          ))
          .map((dynamic item) => jsonMap(item, label: 'transfer listing'))
          .map(_transferListingFromJson)
          .toList(growable: false);
      return PlayerShareDetailData(
        summary: summary,
        playerDetail: detail,
        events: events,
        listings: listings,
      );
    });

TransferListingSummary _transferListingFromJson(JsonMap json) {
  final JsonMap player = jsonMap(
    json['player'],
    label: 'transfer market player',
    fallback: const <String, Object?>{},
  );
  return TransferListingSummary(
    id: stringValue(json['id']),
    playerId: stringValue(json['player_id']),
    playerName:
        stringOrNullValue(player['full_name']) ??
        stringValue(json['player_id']),
    currentClubName: stringOrNullValue(player['current_club_name']),
    currentHighestBid: numberValue(json['current_highest_bid']),
    basePrice: numberValue(json['base_price']),
    status: stringValue(json['status']),
    watchlistCount: intValue(json['watchlist_count']),
    bidCount: intValue(json['bid_count']),
    marketSignal: stringValue(
      json['market_signal'],
      fallback: 'Live transfer listing',
    ),
    channel: stringValue(json['channel']),
    timeRemaining: intValue(json['time_remaining']),
  );
}
