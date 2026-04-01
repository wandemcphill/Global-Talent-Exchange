import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/gte_models.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';

class MarketSearchQueryController extends Notifier<String> {
  @override
  String build() => '';

  void setQuery(String value) {
    state = value;
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
  });

  final List<PlayerShareSummary> playerShares;
  final List<PlayerShareHoldingSummary> holdings;
  final List<TransferListingSummary> transferListings;
  final MarketWalletSnapshot? wallet;
  final bool authenticated;
  final List<String> warnings;

  List<PlayerShareSummary> get tradablePlayerShares => playerShares
      .where((PlayerShareSummary item) => item.isTradable)
      .toList(growable: false);

  List<PlayerShareSummary> get upcomingPlayerShares => playerShares
      .where((PlayerShareSummary item) => !item.isTradable)
      .toList(growable: false);
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

final FutureProvider<MarketDashboardData>
marketDashboardProvider = FutureProvider<MarketDashboardData>((Ref ref) async {
  final GteAuthedApi api = ref.watch(authedApiProvider);
  bool authenticated = ref.watch(isAuthenticatedProvider);
  final String query = ref.watch(marketSearchQueryProvider).trim();
  final JsonMap playerPayload = await api.getMap(
    query.isEmpty ? '/players/real-universe' : '/players/real-universe/search',
    auth: false,
    query: <String, Object?>{
      'limit': 12,
      if (query.isNotEmpty) 'search': query,
    },
  );
  final List<JsonMap> playerItems = jsonMapList(
    playerPayload['items'],
    label: 'real player universe items',
  );
  final List<String> warnings = <String>[];
  final List<PlayerShareSummary> players =
      await Future.wait<PlayerShareSummary>(
        playerItems.map((JsonMap item) async {
          final String playerId = stringValue(item['player_id']);
          final JsonMap market = await api.getMap(
            '/players/$playerId/shares/market',
            auth: false,
          );
          final bool marketIssued = boolValue(market['market_issued']);
          final String marketStatus = stringValue(
            market['status'],
            fallback: marketIssued ? 'blocked' : 'unissued',
          );
          return PlayerShareSummary(
            playerId: playerId,
            playerName: stringValue(item['player_name']),
            position: stringOrNullValue(item['position']),
            nationality: stringOrNullValue(item['nationality']),
            currentClubName: stringOrNullValue(item['current_club_name']),
            age: item['age'] == null ? null : intValue(item['age']),
            currentValueCredits:
                item['current_value_credits'] == null
                    ? null
                    : numberValue(item['current_value_credits']),
            marketInterestScore:
                item['market_interest_score'] == null
                    ? null
                    : intValue(item['market_interest_score']),
            marketStatus: marketStatus,
            marketMessage:
                !marketIssued
                    ? 'Not tradable yet: no issued share market.'
                    : 'Share market is live.',
            sharePriceCoin:
                !marketIssued ? null : numberValue(market['share_price_coin']),
            totalShares:
                !marketIssued ? null : intValue(market['total_shares']),
            circulatingShares:
                !marketIssued ? null : intValue(market['circulating_shares']),
          );
        }),
      );

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
        final GteExchangeApiClient exchangeApi = ref.read(
          exchangeApiClientProvider,
        );
        final GteWalletSummary summary = await exchangeApi.fetchWalletSummary();
        final GteWalletOverview overview =
            await exchangeApi.fetchWalletOverview();
        final GteComplianceStatus compliance =
            await exchangeApi.fetchComplianceStatus();
        wallet = MarketWalletSnapshot(
          coinBalance:
              summary.currency == GteLedgerUnit.coin
                  ? summary.availableBalance
                  : 0,
          creditBalance:
              summary.currency == GteLedgerUnit.credit
                  ? summary.availableBalance
                  : 0,
          totalEquity: summary.totalBalance,
          canTradeMarket: compliance.canTradeMarket,
          canDeposit: compliance.canDeposit,
          canWithdraw: compliance.canWithdrawPlatformRewards,
          complianceMessage:
              overview.policyBlocked
                  ? overview.policyBlockReason ??
                      'Policy restrictions are blocking wallet actions.'
                  : compliance.hasMissingRequiredPolicies
                  ? 'Compliance action required before full trading is enabled.'
                  : 'Wallet and compliance state loaded from live backend.',
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

  final List<dynamic> listingsPayload = await api.getList(
    '/api/transfer-market/listings',
    auth: false,
  );
  final List<TransferListingSummary> transferListings = listingsPayload
      .map((dynamic item) => jsonMap(item, label: 'transfer listing'))
      .map(_transferListingFromJson)
      .toList(growable: false);

  return MarketDashboardData(
    playerShares: players,
    holdings: holdings,
    transferListings: transferListings,
    wallet: wallet,
    authenticated: authenticated,
    warnings: warnings,
  );
});

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
