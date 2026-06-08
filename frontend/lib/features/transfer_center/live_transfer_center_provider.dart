import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../shared/data/feature_api_provider.dart';
import '../shared/data/gte_feature_support.dart';
import 'transfer_center_models.dart';

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
        auth: true,
      );
    } catch (error) {
      if (isNotFoundError(error) || isUnauthorizedError(error)) {
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
    required String securityPin,
  }) async {
    await client.post(
      '/api/v2/auth/pin/verify',
      body: <String, Object?>{
        'pin': securityPin,
        'action_type': 'transfer_market.bid',
      },
    );
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
