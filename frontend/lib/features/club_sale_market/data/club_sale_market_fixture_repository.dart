part of 'club_sale_market_repository.dart';

class ClubSaleMarketFixtureRepository implements ClubSaleMarketRepository {
  final Map<String, _ClubSaleFixtureState> _states =
      <String, _ClubSaleFixtureState>{};
  int _sequence = 0;

  @override
  Future<ClubSaleValuation> fetchValuation(String clubId) async {
    return ClubSaleValuation.fromJson(_stateFor(clubId).valuation);
  }

  @override
  Future<ClubSaleListingCollection> listPublicListings(
    ClubSaleListingsQuery query,
  ) async {
    _stateFor('royal-lagos-fc');
    final List<Map<String, Object?>> listings = _states.values
        .map((_ClubSaleFixtureState state) => state.listing)
        .whereType<Map<String, Object?>>()
        .where(
          (Map<String, Object?> listing) =>
              stringValue(listing['status']).toLowerCase() == 'active',
        )
        .toList(growable: false);
    final int start = query.offset < 0
        ? 0
        : (query.offset > listings.length ? listings.length : query.offset);
    final int end = start + query.limit > listings.length
        ? listings.length
        : start + query.limit;
    return ClubSaleListingCollection.fromJson(<String, Object?>{
      'total': listings.length,
      'items': listings.sublist(start, end),
    });
  }

  @override
  Future<ClubSaleListing?> fetchPublicListing(String clubId) async {
    final Map<String, Object?>? listing = _stateFor(clubId).listing;
    if (listing == null) {
      return null;
    }
    return ClubSaleListing.fromJson(listing);
  }

  @override
  Future<ClubSaleListing> createListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final DateTime now = _now();
    state.listing = <String, Object?>{
      'listing_id': 'fixture-listing-${_nextId()}',
      'club_id': clubId,
      'club_name': state.clubName,
      'seller_user_id': state.ownerUserId,
      'status': 'active',
      'visibility': request.visibility,
      'currency': state.currency,
      'asking_price': request.askingPrice,
      'system_valuation': numberValue(state.valuation['system_valuation']),
      'system_valuation_minor':
          intValue(state.valuation['system_valuation_minor']),
      'valuation_last_refreshed_at': state.valuation['last_refreshed_at'],
      'created_at': now.toIso8601String(),
      'updated_at': now.toIso8601String(),
      'valuation_breakdown': state.valuation['breakdown'],
      'note': request.note,
      'metadata_json': request.metadata,
    };
    return ClubSaleListing.fromJson(state.listing);
  }

  @override
  Future<ClubSaleListing> updateListing(
    String clubId,
    ClubSaleListingUpsertRequest request,
  ) async {
    final Map<String, Object?> listing = _requireListing(_stateFor(clubId));
    listing['asking_price'] = request.askingPrice;
    listing['visibility'] = request.visibility;
    listing['note'] = request.note;
    listing['metadata_json'] = request.metadata;
    listing['updated_at'] = _now().toIso8601String();
    return ClubSaleListing.fromJson(listing);
  }

  @override
  Future<ClubSaleListing> cancelListing(
    String clubId,
    ClubSaleListingCancelRequest request,
  ) async {
    final Map<String, Object?> listing = _requireListing(_stateFor(clubId));
    listing['status'] = 'cancelled';
    listing['note'] = request.reason ?? listing['note'];
    listing['updated_at'] = _now().toIso8601String();
    return ClubSaleListing.fromJson(listing);
  }

  @override
  Future<ClubSaleListingCollection> listMyListings() async {
    _stateFor('royal-lagos-fc');
    final List<Map<String, Object?>> items = _states.values
        .map((_ClubSaleFixtureState state) => state.listing)
        .whereType<Map<String, Object?>>()
        .toList(growable: false);
    return ClubSaleListingCollection.fromJson(<String, Object?>{
      'total': items.length,
      'items': items,
    });
  }

  @override
  Future<ClubSaleInquiry> createInquiry(
    String clubId,
    ClubSaleInquiryCreateRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final DateTime now = _now();
    final Map<String, Object?> inquiry = <String, Object?>{
      'inquiry_id': 'fixture-inquiry-${_nextId()}',
      'club_id': clubId,
      'listing_id': state.listing?['listing_id'],
      'seller_user_id': state.ownerUserId,
      'buyer_user_id': 'fixture-buyer',
      'status': 'open',
      'message': request.message,
      'response_message': null,
      'responded_by_user_id': null,
      'responded_at': null,
      'metadata_json': request.metadata,
      'created_at': now.toIso8601String(),
      'updated_at': now.toIso8601String(),
    };
    state.inquiries.insert(0, inquiry);
    return ClubSaleInquiry.fromJson(inquiry);
  }

  @override
  Future<ClubSaleInquiryCollection> listInquiries(String clubId) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    return ClubSaleInquiryCollection.fromJson(<String, Object?>{
      'total': state.inquiries.length,
      'items': state.inquiries,
    });
  }

  @override
  Future<ClubSaleInquiry> respondInquiry(
    String clubId,
    String inquiryId,
    ClubSaleInquiryRespondRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final Map<String, Object?> inquiry = state.inquiries.firstWhere(
      (Map<String, Object?> item) =>
          stringValue(item['inquiry_id']) == inquiryId,
      orElse: () => throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Inquiry not found.',
      ),
    );
    final DateTime now = _now();
    inquiry['status'] = request.closeThread ? 'closed' : 'responded';
    inquiry['response_message'] = request.responseMessage;
    inquiry['responded_by_user_id'] = state.ownerUserId;
    inquiry['responded_at'] = now.toIso8601String();
    inquiry['metadata_json'] = request.metadata;
    inquiry['updated_at'] = now.toIso8601String();
    return ClubSaleInquiry.fromJson(inquiry);
  }

  @override
  Future<ClubSaleOffer> createOffer(
    String clubId,
    ClubSaleOfferCreateRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final DateTime now = _now();
    final Map<String, Object?> offer = <String, Object?>{
      'offer_id': 'fixture-offer-${_nextId()}',
      'club_id': clubId,
      'listing_id': state.listing?['listing_id'],
      'inquiry_id': request.inquiryId,
      'parent_offer_id': null,
      'seller_user_id': state.ownerUserId,
      'buyer_user_id': 'fixture-buyer',
      'proposer_user_id': 'fixture-buyer',
      'counterparty_user_id': state.ownerUserId,
      'offer_type': 'direct',
      'status': 'open',
      'currency': state.currency,
      'offer_price': request.offerPrice,
      'message': request.message,
      'responded_message': null,
      'responded_by_user_id': null,
      'responded_at': null,
      'accepted_at': null,
      'rejected_at': null,
      'expires_at': request.expiresAt?.toUtc().toIso8601String(),
      'metadata_json': request.metadata,
      'created_at': now.toIso8601String(),
      'updated_at': now.toIso8601String(),
    };
    state.openOffers.insert(0, offer);
    return ClubSaleOffer.fromJson(offer);
  }

  @override
  Future<ClubSaleOfferCollection> listOffers(String clubId) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    return ClubSaleOfferCollection.fromJson(<String, Object?>{
      'total': state.openOffers.length,
      'items': state.openOffers,
    });
  }

  @override
  Future<ClubSaleOfferCollection> listMyOffers() async {
    return const ClubSaleOfferCollection.empty();
  }

  @override
  Future<ClubSaleOffer> counterOffer(
    String clubId,
    String offerId,
    ClubSaleOfferCounterRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final Map<String, Object?> currentOffer = _findOpenOffer(state, offerId);
    final DateTime now = _now();
    currentOffer['status'] = 'countered';
    currentOffer['updated_at'] = now.toIso8601String();
    final Map<String, Object?> counter = <String, Object?>{
      'offer_id': 'fixture-offer-${_nextId()}',
      'club_id': clubId,
      'listing_id': currentOffer['listing_id'],
      'inquiry_id': currentOffer['inquiry_id'],
      'parent_offer_id': offerId,
      'seller_user_id': state.ownerUserId,
      'buyer_user_id': stringValue(currentOffer['buyer_user_id']),
      'proposer_user_id': state.ownerUserId,
      'counterparty_user_id': stringValue(currentOffer['buyer_user_id']),
      'offer_type': 'counter',
      'status': 'open',
      'currency': state.currency,
      'offer_price': request.offerPrice,
      'message': request.message,
      'responded_message': null,
      'responded_by_user_id': null,
      'responded_at': null,
      'accepted_at': null,
      'rejected_at': null,
      'expires_at': request.expiresAt?.toUtc().toIso8601String(),
      'metadata_json': request.metadata,
      'created_at': now.toIso8601String(),
      'updated_at': now.toIso8601String(),
    };
    state.openOffers
      ..removeWhere(
        (Map<String, Object?> item) => stringValue(item['offer_id']) == offerId,
      )
      ..insert(0, counter);
    return ClubSaleOffer.fromJson(counter);
  }

  @override
  Future<ClubSaleOffer> acceptOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final Map<String, Object?> offer = _findOpenOffer(state, offerId);
    final DateTime now = _now();
    offer['status'] = 'accepted';
    offer['responded_message'] = request.message;
    offer['responded_by_user_id'] = state.ownerUserId;
    offer['responded_at'] = now.toIso8601String();
    offer['accepted_at'] = now.toIso8601String();
    offer['updated_at'] = now.toIso8601String();
    return ClubSaleOffer.fromJson(offer);
  }

  @override
  Future<ClubSaleOffer> rejectOffer(
    String clubId,
    String offerId,
    ClubSaleOfferRespondRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final Map<String, Object?> offer = _findOpenOffer(state, offerId);
    final DateTime now = _now();
    offer['status'] = 'rejected';
    offer['responded_message'] = request.message;
    offer['responded_by_user_id'] = state.ownerUserId;
    offer['responded_at'] = now.toIso8601String();
    offer['rejected_at'] = now.toIso8601String();
    offer['updated_at'] = now.toIso8601String();
    return ClubSaleOffer.fromJson(offer);
  }

  @override
  Future<ClubSaleTransferExecution> executeTransfer(
    String clubId,
    ClubSaleTransferExecuteRequest request,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final Map<String, Object?> offer = _findOpenOffer(state, request.offerId);
    final DateTime now = _now();
    final double price = request.executedSalePrice;
    final double fee = price * 0.025;
    final Map<String, Object?> transfer = <String, Object?>{
      'transfer_id': 'fixture-transfer-${_nextId()}',
      'club_id': clubId,
      'listing_id': offer['listing_id'],
      'offer_id': offer['offer_id'],
      'seller_user_id': state.ownerUserId,
      'buyer_user_id': offer['buyer_user_id'],
      'currency': state.currency,
      'executed_sale_price': price,
      'platform_fee_amount': fee,
      'seller_net_amount': price - fee,
      'platform_fee_bps': 250,
      'status': 'settled',
      'settlement_reference': 'FIXTURE-${_nextId()}',
      'ledger_transaction_id': 'ledger-${_nextId()}',
      'story_feed_item_id': 'story-${_nextId()}',
      'calendar_event_id': 'calendar-${_nextId()}',
      'metadata_json': request.metadata,
      'ownership_transition': <String, Object?>{
        'previous_owner_user_id': state.ownerUserId,
        'new_owner_user_id': offer['buyer_user_id'],
        'ownership_lineage_index': intValue(
              state.ownershipHistory['ownership_eras'],
            ) +
            1,
        'shareholder_count_preserved': intValue(
          state.ownershipHistory['shareholder_count'],
        ),
        'shareholder_rights_preserved': true,
      },
      'created_at': now.toIso8601String(),
    };
    offer['status'] = 'accepted';
    offer['accepted_at'] = now.toIso8601String();
    offer['updated_at'] = now.toIso8601String();
    state.transfers.insert(0, transfer);
    state.listing?['status'] = 'sold';
    state.listing?['updated_at'] = now.toIso8601String();
    state.ownershipHistory['current_owner_user_id'] =
        stringValue(offer['buyer_user_id']);
    state.ownershipHistory['transfer_count'] =
        intValue(state.ownershipHistory['transfer_count']) + 1;
    state.ownershipHistory['ownership_eras'] =
        intValue(state.ownershipHistory['ownership_eras']) + 1;
    state.ownershipHistory['last_transfer_id'] = transfer['transfer_id'];
    state.ownershipHistory['last_transfer_at'] = now.toIso8601String();
    state.ownershipHistory['recent_transfers'] = state.transfers
        .take(3)
        .map(_ownershipHistoryEventForTransfer)
        .toList(growable: false);
    return ClubSaleTransferExecution.fromJson(transfer);
  }

  @override
  Future<ClubSaleHistory> fetchHistory(
    String clubId,
    ClubSaleHistoryQuery query,
  ) async {
    final _ClubSaleFixtureState state = _stateFor(clubId);
    final List<Map<String, Object?>> offers = <Map<String, Object?>>[
      ...state.openOffers,
      ...state.historicalOffers,
    ];
    return ClubSaleHistory.fromJson(<String, Object?>{
      'club_id': clubId,
      'listings': <Map<String, Object?>>[
        if (state.listing != null) state.listing!,
      ],
      'offers': offers.take(query.limit).toList(growable: false),
      'transfers': state.transfers.take(query.limit).toList(growable: false),
      'audit_events':
          state.auditEvents.take(query.limit).toList(growable: false),
      'ownership_history': state.ownershipHistory,
      'dynasty_snapshot': state.dynastySnapshot,
    });
  }

  _ClubSaleFixtureState _stateFor(String clubId) {
    return _states.putIfAbsent(
      clubId,
      () => _ClubSaleFixtureState.seed(
        clubId: clubId,
        clubName: _clubNameFor(clubId),
      ),
    );
  }

  Map<String, Object?> _requireListing(_ClubSaleFixtureState state) {
    final Map<String, Object?>? listing = state.listing;
    if (listing == null) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Listing not found.',
      );
    }
    return listing;
  }

  Map<String, Object?> _findOpenOffer(
    _ClubSaleFixtureState state,
    String offerId,
  ) {
    return state.openOffers.firstWhere(
      (Map<String, Object?> offer) => stringValue(offer['offer_id']) == offerId,
      orElse: () => throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Offer not found.',
      ),
    );
  }

  Map<String, Object?> _ownershipHistoryEventForTransfer(
    Map<String, Object?> transfer,
  ) {
    return <String, Object?>{
      'transfer_id': transfer['transfer_id'],
      'seller_user_id': transfer['seller_user_id'],
      'buyer_user_id': transfer['buyer_user_id'],
      'executed_sale_price': transfer['executed_sale_price'],
      'created_at': transfer['created_at'],
      'metadata_json': transfer['metadata_json'],
    };
  }

  DateTime _now() => DateTime.now().toUtc();

  String _nextId() {
    _sequence += 1;
    return _sequence.toString().padLeft(4, '0');
  }

  String _clubNameFor(String clubId) {
    if (clubId == 'royal-lagos-fc') {
      return 'Royal Lagos FC';
    }
    return clubId
        .split('-')
        .where((String part) => part.isNotEmpty)
        .map(
          (String part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }
}

class _ClubSaleFixtureState {
  _ClubSaleFixtureState({
    required this.clubName,
    required this.ownerUserId,
    required this.currency,
    required this.valuation,
    required this.listing,
    required this.inquiries,
    required this.openOffers,
    required this.historicalOffers,
    required this.transfers,
    required this.auditEvents,
    required this.ownershipHistory,
    required this.dynastySnapshot,
  });

  factory _ClubSaleFixtureState.seed({
    required String clubId,
    required String clubName,
  }) {
    const String ownerUserId = 'user-1';
    const String currency = 'USD';
    final Map<String, Object?> breakdown = <String, Object?>{
      'first_team_value': 112000000.0,
      'reserve_squad_value': 21000000.0,
      'u19_squad_value': 14000000.0,
      'academy_value': 18000000.0,
      'stadium_value': 24000000.0,
      'paid_enhancements_value': 6000000.0,
      'metadata_json': <String, Object?>{'fixture_seed': true},
    };
    final Map<String, Object?> valuation = <String, Object?>{
      'club_id': clubId,
      'club_name': clubName,
      'currency': currency,
      'system_valuation': 195000000.0,
      'system_valuation_minor': 195000000,
      'breakdown': breakdown,
      'last_refreshed_at': '2026-03-15T12:00:00Z',
    };
    final Map<String, Object?> listing = <String, Object?>{
      'listing_id': 'fixture-listing-$clubId',
      'club_id': clubId,
      'club_name': clubName,
      'seller_user_id': ownerUserId,
      'status': 'active',
      'visibility': 'public',
      'currency': currency,
      'asking_price': 210000000.0,
      'system_valuation': 195000000.0,
      'system_valuation_minor': 195000000,
      'valuation_last_refreshed_at': '2026-03-15T12:00:00Z',
      'created_at': '2026-03-12T09:00:00Z',
      'updated_at': '2026-03-17T09:00:00Z',
      'valuation_breakdown': breakdown,
      'note': 'Final-round owner review is in progress.',
      'metadata_json': <String, Object?>{'fixture_seed': true},
    };
    final List<Map<String, Object?>> inquiries = <Map<String, Object?>>[
      <String, Object?>{
        'inquiry_id': 'fixture-inquiry-$clubId-1',
        'club_id': clubId,
        'listing_id': listing['listing_id'],
        'seller_user_id': ownerUserId,
        'buyer_user_id': 'buyer-7',
        'status': 'open',
        'message': 'Share seller diligence pack and debt schedule.',
        'response_message': null,
        'responded_by_user_id': null,
        'responded_at': null,
        'metadata_json': <String, Object?>{'fixture_seed': true},
        'created_at': '2026-03-16T11:00:00Z',
        'updated_at': '2026-03-16T11:00:00Z',
      },
    ];
    final List<Map<String, Object?>> openOffers = <Map<String, Object?>>[
      <String, Object?>{
        'offer_id': 'fixture-offer-$clubId-open',
        'club_id': clubId,
        'listing_id': listing['listing_id'],
        'inquiry_id': inquiries.first['inquiry_id'],
        'parent_offer_id': null,
        'seller_user_id': ownerUserId,
        'buyer_user_id': 'buyer-7',
        'proposer_user_id': 'buyer-7',
        'counterparty_user_id': ownerUserId,
        'offer_type': 'direct',
        'status': 'open',
        'currency': currency,
        'offer_price': 198500000.0,
        'message': 'Ready to close inside seven days.',
        'responded_message': null,
        'responded_by_user_id': null,
        'responded_at': null,
        'accepted_at': null,
        'rejected_at': null,
        'expires_at': '2026-03-25T00:00:00Z',
        'metadata_json': <String, Object?>{'fixture_seed': true},
        'created_at': '2026-03-17T13:00:00Z',
        'updated_at': '2026-03-17T13:00:00Z',
      },
    ];
    final List<Map<String, Object?>> historicalOffers = <Map<String, Object?>>[
      <String, Object?>{
        'offer_id': 'fixture-offer-$clubId-history',
        'club_id': clubId,
        'listing_id': 'fixture-listing-$clubId-history',
        'inquiry_id': null,
        'parent_offer_id': null,
        'seller_user_id': 'seller-legacy',
        'buyer_user_id': ownerUserId,
        'proposer_user_id': ownerUserId,
        'counterparty_user_id': 'seller-legacy',
        'offer_type': 'direct',
        'status': 'accepted',
        'currency': currency,
        'offer_price': 174000000.0,
        'message': 'Historical control acquisition.',
        'responded_message': 'Accepted after treasury approval.',
        'responded_by_user_id': 'seller-legacy',
        'responded_at': '2026-02-20T11:00:00Z',
        'accepted_at': '2026-02-20T11:00:00Z',
        'rejected_at': null,
        'expires_at': '2026-02-24T00:00:00Z',
        'metadata_json': <String, Object?>{'fixture_seed': true},
        'created_at': '2026-02-18T09:00:00Z',
        'updated_at': '2026-02-20T11:00:00Z',
      },
    ];
    final List<Map<String, Object?>> transfers = <Map<String, Object?>>[
      <String, Object?>{
        'transfer_id': 'fixture-transfer-$clubId-1',
        'club_id': clubId,
        'listing_id': 'fixture-listing-$clubId-history',
        'offer_id': historicalOffers.first['offer_id'],
        'seller_user_id': 'seller-legacy',
        'buyer_user_id': ownerUserId,
        'currency': currency,
        'executed_sale_price': 174000000.0,
        'platform_fee_amount': 4350000.0,
        'seller_net_amount': 169650000.0,
        'platform_fee_bps': 250,
        'status': 'settled',
        'settlement_reference': 'FIXTURE-TRS-001',
        'ledger_transaction_id': 'ledger-royal-001',
        'story_feed_item_id': 'story-royal-001',
        'calendar_event_id': 'calendar-royal-001',
        'metadata_json': <String, Object?>{'fixture_seed': true},
        'ownership_transition': <String, Object?>{
          'previous_owner_user_id': 'seller-legacy',
          'new_owner_user_id': ownerUserId,
          'ownership_lineage_index': 2,
          'shareholder_count_preserved': 1420,
          'shareholder_rights_preserved': true,
        },
        'created_at': '2026-02-20T12:00:00Z',
      },
    ];
    return _ClubSaleFixtureState(
      clubName: clubName,
      ownerUserId: ownerUserId,
      currency: currency,
      valuation: valuation,
      listing: listing,
      inquiries: inquiries,
      openOffers: openOffers,
      historicalOffers: historicalOffers,
      transfers: transfers,
      auditEvents: <Map<String, Object?>>[
        <String, Object?>{
          'id': 'fixture-audit-$clubId-1',
          'club_id': clubId,
          'listing_id': listing['listing_id'],
          'inquiry_id': null,
          'offer_id': openOffers.first['offer_id'],
          'transfer_id': null,
          'actor_user_id': 'buyer-7',
          'action': 'offer_created',
          'status_from': null,
          'status_to': 'open',
          'payload_json': <String, Object?>{'offer_price': 198500000.0},
          'created_at': '2026-03-17T13:00:00Z',
        },
      ],
      ownershipHistory: <String, Object?>{
        'current_owner_user_id': ownerUserId,
        'transfer_count': 1,
        'ownership_eras': 2,
        'shareholder_count': 1420,
        'active_governance_proposal_count': 1,
        'last_transfer_id': transfers.first['transfer_id'],
        'last_transfer_at': transfers.first['created_at'],
        'previous_owner_user_ids': <String>['seller-legacy'],
        'recent_transfers': transfers
            .map(
              (Map<String, Object?> transfer) => <String, Object?>{
                'transfer_id': transfer['transfer_id'],
                'seller_user_id': transfer['seller_user_id'],
                'buyer_user_id': transfer['buyer_user_id'],
                'executed_sale_price': transfer['executed_sale_price'],
                'created_at': transfer['created_at'],
                'metadata_json': transfer['metadata_json'],
              },
            )
            .toList(growable: false),
      },
      dynastySnapshot: <String, Object?>{
        'dynasty_score': 88,
        'dynasty_level': 4,
        'dynasty_title': 'Premier Ascension',
        'seasons_completed': 6,
        'last_season_label': '2025',
        'ownership_eras': 2,
        'shareholder_continuity_transfers': 1,
        'showcase_summary_json': <String, Object?>{
          'fixture_seed': true,
          'headline': 'Ownership continuity preserved through the last sale.',
        },
      },
    );
  }

  final String clubName;
  final String ownerUserId;
  final String currency;
  final Map<String, Object?> valuation;
  Map<String, Object?>? listing;
  final List<Map<String, Object?>> inquiries;
  final List<Map<String, Object?>> openOffers;
  final List<Map<String, Object?>> historicalOffers;
  final List<Map<String, Object?>> transfers;
  final List<Map<String, Object?>> auditEvents;
  final Map<String, Object?> ownershipHistory;
  final Map<String, Object?> dynastySnapshot;
}
