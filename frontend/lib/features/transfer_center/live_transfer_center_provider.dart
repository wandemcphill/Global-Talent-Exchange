import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../shared/data/feature_api_provider.dart';
import '../shared/data/gte_feature_support.dart';

class TransferCenterListingRecord {
  const TransferCenterListingRecord({
    required this.id,
    required this.playerId,
    required this.playerName,
    required this.sellingClubId,
    required this.currentClubName,
    required this.basePrice,
    required this.currentHighestBid,
    required this.highestBidderId,
    required this.status,
    required this.watchlistCount,
    required this.bidCount,
    required this.marketSignal,
    required this.channel,
    required this.timeRemaining,
    required this.negotiationId,
    required this.bidders,
  });

  final String id;
  final String playerId;
  final String playerName;
  final String sellingClubId;
  final String? currentClubName;
  final double basePrice;
  final double currentHighestBid;
  final String? highestBidderId;
  final String status;
  final int watchlistCount;
  final int bidCount;
  final String marketSignal;
  final String channel;
  final int timeRemaining;
  final String? negotiationId;
  final List<JsonMap> bidders;

  factory TransferCenterListingRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'transfer listing');
    final JsonMap player = jsonMap(
      json['player'],
      label: 'transfer listing player',
      fallback: const <String, Object?>{},
    );
    return TransferCenterListingRecord(
      id: stringValue(json['id']),
      playerId: stringValue(json['player_id']),
      playerName:
          stringOrNullValue(player['full_name']) ??
          stringValue(json['player_id']),
      sellingClubId: stringValue(json['selling_club_id']),
      currentClubName: stringOrNullValue(player['current_club_name']),
      basePrice: numberValue(json['base_price']),
      currentHighestBid: numberValue(json['current_highest_bid']),
      highestBidderId: stringOrNullValue(json['highest_bidder_id']),
      status: stringValue(json['status'], fallback: 'open'),
      watchlistCount: intValue(json['watchlist_count']),
      bidCount: intValue(json['bid_count']),
      marketSignal: stringValue(
        json['market_signal'],
        fallback: 'Live transfer listing',
      ),
      channel: stringValue(json['channel']),
      timeRemaining: intValue(json['time_remaining']),
      negotiationId: stringOrNullValue(json['negotiation_id']),
      bidders: jsonMapList(json['bidders'], label: 'transfer bidders'),
    );
  }
}

class TransferCenterDetailData {
  const TransferCenterDetailData({
    required this.listing,
    required this.negotiation,
  });

  final JsonMap listing;
  final JsonMap? negotiation;
}

class TransferCenterApi {
  const TransferCenterApi({required this.client});

  final GteAuthedApi client;

  Future<List<TransferCenterListingRecord>> listListings({
    String? status,
    String? playerId,
  }) async {
    final List<dynamic> payload = await client.getList(
      '/api/transfer-market/listings',
      auth: false,
      query: compactQuery(<String, Object?>{
        'status': status,
        'player_id': playerId,
      }),
    );
    return payload
        .map(TransferCenterListingRecord.fromJson)
        .toList(growable: false);
  }

  Future<JsonMap> fetchListing(String listingId) {
    return client.getMap(
      '/api/transfer-market/listings/$listingId',
      auth: false,
    );
  }

  Future<JsonMap?> fetchNegotiation(String listingId) async {
    try {
      return await client.getMap(
        '/api/transfer-market/listings/$listingId/negotiation',
        auth: false,
      );
    } catch (error) {
      if (isNotFoundError(error)) {
        return null;
      }
      rethrow;
    }
  }

  Future<void> addToWatchlist({
    required String clubId,
    required String playerId,
    required String listingId,
  }) async {
    await client.post(
      '/api/transfer-market/watchlist',
      body: <String, Object?>{
        'club_id': clubId,
        'player_id': playerId,
        'source': 'transfer_center',
        'discovery_score': 82,
        'metadata_json': <String, Object?>{'listing_id': listingId},
      },
    );
  }

  Future<void> placeBid({
    required String listingId,
    required String clubId,
    required double amount,
  }) async {
    await client.post(
      '/api/transfer-market/listings/$listingId/bids',
      body: <String, Object?>{
        'bidder_club_id': clubId,
        'amount': amount,
        'activity_context': 'transfer_center',
      },
    );
  }

  Future<void> submitContractOffer({
    required String listingId,
    required String clubId,
    required double wageOfferAmount,
    required int contractYears,
    String? expectedRole,
  }) async {
    await client.post(
      '/api/transfer-market/listings/$listingId/contract-offer',
      body: <String, Object?>{
        'bidder_club_id': clubId,
        'wage_offer_amount': wageOfferAmount,
        'contract_years': contractYears,
        if (expectedRole != null && expectedRole.trim().isNotEmpty)
          'expected_role': expectedRole.trim(),
        'notes': 'Submitted from transfer center route.',
      },
    );
  }
}

final Provider<TransferCenterApi> transferCenterApiProvider =
    createFeatureApiProvider<TransferCenterApi>(
      (GteAuthedApi client) => TransferCenterApi(client: client),
    );

final FutureProvider<List<TransferCenterListingRecord>>
transferCenterListingsProvider =
    FutureProvider<List<TransferCenterListingRecord>>((Ref ref) async {
      return ref.watch(transferCenterApiProvider).listListings(status: 'open');
    });

final dynamic transferCenterDetailProvider = FutureProvider.family<
  TransferCenterDetailData,
  String
>((Ref ref, String listingId) async {
  final TransferCenterApi api = ref.watch(transferCenterApiProvider);
  final Future<JsonMap> listingFuture = api.fetchListing(listingId);
  final Future<JsonMap?> negotiationFuture = api.fetchNegotiation(listingId);
  return TransferCenterDetailData(
    listing: await listingFuture,
    negotiation: await negotiationFuture,
  );
});
