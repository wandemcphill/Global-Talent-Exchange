import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../../ui_gtex/components/gtex_status_presenter.dart';
import '../shared/data/feature_api_provider.dart';
import '../shared/data/gte_feature_support.dart';

/// Canonical segmented views for the G10 Sporting Transfers Hub (Phase C3).
enum GtexTransferHubSegment {
  listings('listings', 'Listings'),
  offers('offers', 'Offers'),
  negotiations('negotiations', 'Negotiations'),
  windowBids('window_bids', 'Window Bids'),
  shortlist('shortlist', 'Shortlist');

  const GtexTransferHubSegment(this.slug, this.label);

  final String slug;
  final String label;

  static GtexTransferHubSegment fromSlug(String? rawSlug) {
    final String normalized = (rawSlug ?? '').trim().toLowerCase();
    for (final GtexTransferHubSegment segment in GtexTransferHubSegment.values) {
      if (segment.slug == normalized ||
          segment.name.toLowerCase() == normalized) {
        return segment;
      }
    }
    if (normalized == 'windows' || normalized == 'bids') {
      return GtexTransferHubSegment.windowBids;
    }
    return GtexTransferHubSegment.listings;
  }
}

/// Visual state of a single stage in the G10 Offer Lifecycle timeline.
enum GtexTransferOfferLifecycleStageState {
  completed,
  active,
  upcoming,
  terminalFailure,
}

/// Stage descriptor for the G10 Offer Lifecycle timeline (`draft -> open -> countered -> resolution`).
class GtexTransferOfferLifecycleStage {
  const GtexTransferOfferLifecycleStage({
    required this.id,
    required this.label,
    required this.state,
  });

  final String id;
  final String label;
  final GtexTransferOfferLifecycleStageState state;
}

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

  GtexPresentedStatus get statusView =>
      GtexStatusPresenter.present(status, context: GtexStatusContext.transfer);

  bool get isTerminal =>
      statusView.isTerminal ||
      const <String>{
        'closed',
        'sold',
        'accepted',
        'rejected',
        'cancelled',
        'expired',
      }.contains(GtexStatusPresenter.normalize(status));

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
      status: stringValue(json['status'], fallback: 'unavailable'),
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

/// Canonical model for `/api/transfer-hub/offers` (`TransferHubOfferView`, Document G10).
class TransferHubOfferRecord {
  const TransferHubOfferRecord({
    required this.id,
    required this.listingId,
    required this.offerType,
    required this.sellerClubId,
    required this.bidderClubId,
    required this.cashAmount,
    required this.status,
    this.offeredPlayerIds = const <String>[],
    this.sellOnPercentage,
    this.message,
    this.expiresAt,
    this.resolvedAt,
    this.playerId = '',
    this.playerName = '',
  });

  final String id;
  final String listingId;
  final String offerType;
  final String sellerClubId;
  final String bidderClubId;
  final double cashAmount;
  final List<String> offeredPlayerIds;
  final double? sellOnPercentage;
  final String status;
  final String? message;
  final String? expiresAt;
  final String? resolvedAt;
  final String playerId;
  final String playerName;

  String get normalizedStatus => GtexStatusPresenter.normalize(status);

  GtexPresentedStatus get statusView =>
      GtexStatusPresenter.present(status, context: GtexStatusContext.offer);

  /// Terminal offers cannot be mutated (`Accept`, `Reject`, `Counter`, `Cancel` disabled).
  bool get isTerminal =>
      statusView.isTerminal ||
      const <String>{
        'accepted',
        'rejected',
        'cancelled',
        'canceled',
        'expired',
        'completed',
      }.contains(normalizedStatus);

  /// True only when the transfer offer has been accepted/completed (never true for `pending`/`open`/`draft`).
  bool get isCompletedTransfer =>
      normalizedStatus == 'accepted' || normalizedStatus == 'completed';

  /// Role- and status-gated check for `Accept`.
  bool canAccept({String? activeClubId}) {
    if (isTerminal) {
      return false;
    }
    if (normalizedStatus != 'open' && normalizedStatus != 'countered') {
      return false;
    }
    final String club = (activeClubId ?? '').trim();
    if (club.isEmpty) {
      return true;
    }
    if (normalizedStatus == 'countered') {
      return club == sellerClubId || club == bidderClubId;
    }
    return club == sellerClubId;
  }

  /// Role- and status-gated check for `Reject`.
  bool canReject({String? activeClubId}) {
    if (isTerminal) {
      return false;
    }
    if (normalizedStatus != 'open' && normalizedStatus != 'countered') {
      return false;
    }
    final String club = (activeClubId ?? '').trim();
    if (club.isEmpty) {
      return true;
    }
    if (normalizedStatus == 'countered') {
      return club == sellerClubId || club == bidderClubId;
    }
    return club == sellerClubId;
  }

  /// Role- and status-gated check for `Counter`.
  bool canCounter({String? activeClubId}) {
    if (isTerminal) {
      return false;
    }
    if (normalizedStatus != 'open' && normalizedStatus != 'countered') {
      return false;
    }
    final String club = (activeClubId ?? '').trim();
    if (club.isEmpty) {
      return true;
    }
    return club == sellerClubId || club == bidderClubId;
  }

  /// Role- and status-gated check for `Cancel`.
  bool canCancel({String? activeClubId}) {
    if (isTerminal) {
      return false;
    }
    if (normalizedStatus != 'draft' &&
        normalizedStatus != 'open' &&
        normalizedStatus != 'countered') {
      return false;
    }
    final String club = (activeClubId ?? '').trim();
    if (club.isEmpty) {
      return true;
    }
    return club == bidderClubId;
  }

  /// 4-stage lifecycle timeline (`Draft -> Open -> Countered -> Resolution`).
  List<GtexTransferOfferLifecycleStage> get lifecycleTimeline {
    final String s = normalizedStatus;
    if (s == 'draft') {
      return const <GtexTransferOfferLifecycleStage>[
        GtexTransferOfferLifecycleStage(
          id: 'draft',
          label: 'Draft',
          state: GtexTransferOfferLifecycleStageState.active,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'open',
          label: 'Open',
          state: GtexTransferOfferLifecycleStageState.upcoming,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'countered',
          label: 'Countered',
          state: GtexTransferOfferLifecycleStageState.upcoming,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'resolution',
          label: 'Resolution',
          state: GtexTransferOfferLifecycleStageState.upcoming,
        ),
      ];
    }
    if (s == 'open' || s == 'pending') {
      return const <GtexTransferOfferLifecycleStage>[
        GtexTransferOfferLifecycleStage(
          id: 'draft',
          label: 'Draft',
          state: GtexTransferOfferLifecycleStageState.completed,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'open',
          label: 'Open',
          state: GtexTransferOfferLifecycleStageState.active,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'countered',
          label: 'Countered',
          state: GtexTransferOfferLifecycleStageState.upcoming,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'resolution',
          label: 'Resolution',
          state: GtexTransferOfferLifecycleStageState.upcoming,
        ),
      ];
    }
    if (s == 'countered') {
      return const <GtexTransferOfferLifecycleStage>[
        GtexTransferOfferLifecycleStage(
          id: 'draft',
          label: 'Draft',
          state: GtexTransferOfferLifecycleStageState.completed,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'open',
          label: 'Open',
          state: GtexTransferOfferLifecycleStageState.completed,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'countered',
          label: 'Countered',
          state: GtexTransferOfferLifecycleStageState.active,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'resolution',
          label: 'Resolution',
          state: GtexTransferOfferLifecycleStageState.upcoming,
        ),
      ];
    }
    if (s == 'accepted' || s == 'completed') {
      return const <GtexTransferOfferLifecycleStage>[
        GtexTransferOfferLifecycleStage(
          id: 'draft',
          label: 'Draft',
          state: GtexTransferOfferLifecycleStageState.completed,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'open',
          label: 'Open',
          state: GtexTransferOfferLifecycleStageState.completed,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'countered',
          label: 'Negotiated',
          state: GtexTransferOfferLifecycleStageState.completed,
        ),
        GtexTransferOfferLifecycleStage(
          id: 'resolution',
          label: 'Accepted',
          state: GtexTransferOfferLifecycleStageState.completed,
        ),
      ];
    }
    final String terminalLabel = switch (s) {
      'rejected' => 'Rejected',
      'cancelled' || 'canceled' => 'Cancelled',
      'expired' => 'Expired',
      _ => statusView.label,
    };
    return <GtexTransferOfferLifecycleStage>[
      const GtexTransferOfferLifecycleStage(
        id: 'draft',
        label: 'Draft',
        state: GtexTransferOfferLifecycleStageState.completed,
      ),
      const GtexTransferOfferLifecycleStage(
        id: 'open',
        label: 'Open',
        state: GtexTransferOfferLifecycleStageState.completed,
      ),
      const GtexTransferOfferLifecycleStage(
        id: 'countered',
        label: 'Reviewed',
        state: GtexTransferOfferLifecycleStageState.completed,
      ),
      GtexTransferOfferLifecycleStage(
        id: 'resolution',
        label: terminalLabel,
        state: GtexTransferOfferLifecycleStageState.terminalFailure,
      ),
    ];
  }

  String get expiryCountdownLabel {
    if (isTerminal) {
      final String resolved = (resolvedAt ?? '').trim();
      return resolved.isEmpty ? 'Closed' : 'Resolved $resolved';
    }
    final String rawExpiry = (expiresAt ?? '').trim();
    if (rawExpiry.isEmpty) {
      return 'Open until window close';
    }
    return 'Expires $rawExpiry';
  }

  factory TransferHubOfferRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'transfer hub offer');
    final JsonMap metadata = jsonMap(
      json['metadata_json'],
      label: 'transfer hub offer metadata',
      fallback: const <String, Object?>{},
    );
    return TransferHubOfferRecord(
      id: stringValue(json['id']),
      listingId: stringValue(json['listing_id']),
      offerType: stringValue(json['offer_type'], fallback: 'transfer'),
      sellerClubId: stringValue(json['seller_club_id']),
      bidderClubId: stringValue(json['bidder_club_id']),
      cashAmount: numberValue(json['cash_amount']),
      offeredPlayerIds: stringListValue(json['offered_player_ids']),
      sellOnPercentage:
          json['sell_on_percentage'] == null
              ? null
              : numberValue(json['sell_on_percentage']),
      status: stringValue(json['status'], fallback: 'open'),
      message: stringOrNullValue(json['message']),
      expiresAt: stringOrNullValue(json['expires_at']),
      resolvedAt: stringOrNullValue(json['resolved_at']),
      playerId:
          stringOrNullValue(json['player_id']) ??
          stringValue(metadata['player_id']),
      playerName:
          stringOrNullValue(json['player_name']) ??
          stringValue(metadata['player_name']),
    );
  }
}

/// Canonical model for `/api/transfer-market/listings/{id}/negotiation` (`TransferNegotiationView`).
class TransferNegotiationRecord {
  const TransferNegotiationRecord({
    required this.id,
    required this.listingId,
    required this.playerId,
    required this.sellingClubId,
    required this.bidderClubId,
    required this.status,
    required this.contractYears,
    this.playerName = '',
    this.wageOfferAmount,
    this.expectedRole,
    this.playerInterestLevel,
    this.playerAction,
    this.coachStance,
    this.coachReason,
    this.agentAction,
    this.concerns = const <String>[],
    this.decisionDueAt,
    this.resolvedAt,
  });

  final String id;
  final String listingId;
  final String playerId;
  final String playerName;
  final String sellingClubId;
  final String bidderClubId;
  final String status;
  final double? wageOfferAmount;
  final int contractYears;
  final String? expectedRole;
  final String? playerInterestLevel;
  final String? playerAction;
  final String? coachStance;
  final String? coachReason;
  final String? agentAction;
  final List<String> concerns;
  final String? decisionDueAt;
  final String? resolvedAt;

  String get normalizedStatus => GtexStatusPresenter.normalize(status);

  GtexPresentedStatus get statusView {
    if (normalizedStatus == 'counter_offer') {
      return GtexStatusPresenter.present(
        'countered',
        context: GtexStatusContext.offer,
      );
    }
    if (normalizedStatus == 'awaiting_contract_offer' ||
        normalizedStatus == 'player_delayed') {
      return GtexStatusPresenter.present(
        'pending',
        context: GtexStatusContext.decisionRequired,
      );
    }
    if (normalizedStatus == 'coach_blocked' ||
        normalizedStatus == 'collapsed') {
      return GtexStatusPresenter.present(
        'blocked',
        context: GtexStatusContext.offer,
      );
    }
    return GtexStatusPresenter.present(status, context: GtexStatusContext.offer);
  }

  bool get isTerminal =>
      statusView.isTerminal ||
      const <String>{
        'completed',
        'rejected',
        'collapsed',
        'coach_blocked',
      }.contains(normalizedStatus);

  factory TransferNegotiationRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'transfer negotiation');
    final JsonMap playerDecision = jsonMap(
      json['player_decision'],
      label: 'player decision',
      fallback: const <String, Object?>{},
    );
    final JsonMap coachOpinion = jsonMap(
      json['coach_opinion'],
      label: 'coach opinion',
      fallback: const <String, Object?>{},
    );
    final JsonMap agentNegotiation = jsonMap(
      json['agent_negotiation'],
      label: 'agent negotiation',
      fallback: const <String, Object?>{},
    );
    return TransferNegotiationRecord(
      id: stringValue(json['id']),
      listingId: stringValue(json['listing_id']),
      playerId: stringValue(json['player_id']),
      playerName:
          stringOrNullValue(json['player_name']) ??
          stringValue(json['player_id']),
      sellingClubId: stringValue(json['selling_club_id']),
      bidderClubId: stringValue(json['bidder_club_id']),
      status: stringValue(
        json['status'],
        fallback: 'awaiting_contract_offer',
      ),
      wageOfferAmount:
          json['wage_offer_amount'] == null
              ? null
              : numberValue(json['wage_offer_amount']),
      contractYears: intValue(json['contract_years'], fallback: 3),
      expectedRole: stringOrNullValue(json['expected_role']),
      playerInterestLevel: stringOrNullValue(playerDecision['interest_level']),
      playerAction: stringOrNullValue(playerDecision['action']),
      coachStance: stringOrNullValue(coachOpinion['stance']),
      coachReason: stringOrNullValue(coachOpinion['reason']),
      agentAction: stringOrNullValue(agentNegotiation['action']),
      concerns: stringListValue(json['concerns']),
      decisionDueAt: stringOrNullValue(json['decision_due_at']),
      resolvedAt: stringOrNullValue(json['resolved_at']),
    );
  }
}

/// Canonical model for `/api/transfer-market/watchlist` (`MarketWatchlistEntryView`).
class TransferShortlistEntryRecord {
  const TransferShortlistEntryRecord({
    required this.id,
    required this.clubId,
    required this.playerId,
    required this.playerName,
    required this.source,
    required this.discoveryScore,
    this.listingId,
    this.estimatedFeeCredits = 0,
  });

  final String id;
  final String clubId;
  final String playerId;
  final String playerName;
  final String source;
  final double discoveryScore;
  final String? listingId;
  final double estimatedFeeCredits;

  factory TransferShortlistEntryRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'watchlist entry');
    final JsonMap metadata = jsonMap(
      json['metadata_json'],
      label: 'watchlist metadata',
      fallback: const <String, Object?>{},
    );
    return TransferShortlistEntryRecord(
      id: stringValue(json['id']),
      clubId: stringValue(json['club_id']),
      playerId: stringValue(json['player_id']),
      playerName:
          stringOrNullValue(metadata['player_name']) ??
          stringValue(json['player_id']),
      source: stringValue(json['source'], fallback: 'scouting'),
      discoveryScore: numberValue(json['discovery_score']),
      listingId: stringOrNullValue(metadata['listing_id']),
      estimatedFeeCredits: numberValue(metadata['estimated_fee_credits']),
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
        auth: true,
      );
    } catch (error) {
      if (isNotFoundError(error) || isUnauthorizedError(error)) {
        return null;
      }
      rethrow;
    }
  }

  Future<List<TransferHubOfferRecord>> listOffers({
    String? listingId,
    String? clubId,
    String? status,
  }) async {
    final List<dynamic> payload = await client.getList(
      '/api/transfer-hub/offers',
      auth: true,
      query: compactQuery(<String, Object?>{
        'listing_id': listingId,
        'club_id': clubId,
        'status': status,
      }),
    );
    return payload
        .map(TransferHubOfferRecord.fromJson)
        .toList(growable: false);
  }

  Future<TransferHubOfferRecord> createOffer({
    required String listingId,
    required String bidderClubId,
    required double cashAmount,
    String offerType = 'transfer',
    String? message,
    String? idempotencyKey,
  }) async {
    final Object? response = await client.request(
      'POST',
      '/api/transfer-hub/listings/$listingId/offers',
      body: <String, Object?>{
        'bidder_club_id': bidderClubId,
        'offer_type': offerType,
        'cash_amount': cashAmount,
        if (message != null && message.trim().isNotEmpty)
          'message': message.trim(),
        if (idempotencyKey != null && idempotencyKey.trim().isNotEmpty)
          'idempotency_key': idempotencyKey.trim(),
      },
    );
    return TransferHubOfferRecord.fromJson(response);
  }

  Future<TransferHubOfferRecord> acceptOffer(String offerId) async {
    final Object? response = await client.request(
      'POST',
      '/api/transfer-hub/offers/$offerId/accept',
    );
    return TransferHubOfferRecord.fromJson(response);
  }

  Future<TransferHubOfferRecord> rejectOffer(String offerId) async {
    final Object? response = await client.request(
      'POST',
      '/api/transfer-hub/offers/$offerId/reject',
    );
    return TransferHubOfferRecord.fromJson(response);
  }

  Future<TransferHubOfferRecord> cancelOffer(String offerId) async {
    final Object? response = await client.request(
      'POST',
      '/api/transfer-hub/offers/$offerId/cancel',
    );
    return TransferHubOfferRecord.fromJson(response);
  }

  Future<TransferHubOfferRecord> counterOffer(
    String offerId, {
    required double cashAmount,
    String? message,
  }) async {
    final Object? response = await client.request(
      'POST',
      '/api/transfer-hub/offers/$offerId/counter',
      body: <String, Object?>{
        'cash_amount': cashAmount,
        if (message != null && message.trim().isNotEmpty)
          'message': message.trim(),
      },
    );
    return TransferHubOfferRecord.fromJson(response);
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

final FutureProvider<List<TransferHubOfferRecord>>
transferCenterOffersProvider =
    FutureProvider<List<TransferHubOfferRecord>>((Ref ref) async {
      return ref.watch(transferCenterApiProvider).listOffers();
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
