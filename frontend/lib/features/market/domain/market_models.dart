typedef JsonMap = Map<String, Object?>;

enum MarketBidStatus {
  pending,
  counter,
  accepted,
  rejected,
  withdrawn;

  static MarketBidStatus fromBackend(Object? value) {
    final String normalized = _requiredString(
      value,
      'bid status',
    ).trim().toLowerCase().replaceAll('-', '_');
    return switch (normalized) {
      'pending' || 'submitted' || 'draft' => MarketBidStatus.pending,
      'counter' || 'counter_offer' => MarketBidStatus.counter,
      'accepted' || 'completed' => MarketBidStatus.accepted,
      'rejected' => MarketBidStatus.rejected,
      'withdrawn' => MarketBidStatus.withdrawn,
      _ => throw FormatException('Unsupported market bid status: $value'),
    };
  }

  String get backendValue {
    return switch (this) {
      MarketBidStatus.pending => 'pending',
      MarketBidStatus.counter => 'counter',
      MarketBidStatus.accepted => 'accepted',
      MarketBidStatus.rejected => 'rejected',
      MarketBidStatus.withdrawn => 'withdrawn',
    };
  }

  bool canTransitionTo(MarketBidStatus next) {
    return switch (this) {
      MarketBidStatus.pending =>
        next == MarketBidStatus.counter ||
            next == MarketBidStatus.accepted ||
            next == MarketBidStatus.rejected ||
            next == MarketBidStatus.withdrawn,
      MarketBidStatus.counter =>
        next == MarketBidStatus.accepted ||
            next == MarketBidStatus.rejected ||
            next == MarketBidStatus.withdrawn,
      MarketBidStatus.accepted ||
      MarketBidStatus.rejected ||
      MarketBidStatus.withdrawn => false,
    };
  }

  bool get isTerminal =>
      this == MarketBidStatus.accepted ||
      this == MarketBidStatus.rejected ||
      this == MarketBidStatus.withdrawn;

  bool get requiresReservationTruth =>
      this == MarketBidStatus.pending ||
      this == MarketBidStatus.counter ||
      this == MarketBidStatus.accepted;
}

class MarketFilters {
  const MarketFilters({
    this.query,
    this.positions = const <String>[],
    this.nationalities = const <String>[],
    this.minAge,
    this.maxAge,
    this.minValue,
    this.maxValue,
    this.availabilityTypes = const <String>[],
    this.status,
    this.playerId,
    this.clubId,
  });

  factory MarketFilters.empty() => const MarketFilters();

  final String? query;
  final List<String> positions;
  final List<String> nationalities;
  final int? minAge;
  final int? maxAge;
  final double? minValue;
  final double? maxValue;
  final List<String> availabilityTypes;
  final String? status;
  final String? playerId;
  final String? clubId;

  MarketFilters copyWith({
    String? query,
    List<String>? positions,
    List<String>? nationalities,
    int? minAge,
    int? maxAge,
    double? minValue,
    double? maxValue,
    List<String>? availabilityTypes,
    String? status,
    String? playerId,
    String? clubId,
  }) {
    return MarketFilters(
      query: query ?? this.query,
      positions: positions ?? this.positions,
      nationalities: nationalities ?? this.nationalities,
      minAge: minAge ?? this.minAge,
      maxAge: maxAge ?? this.maxAge,
      minValue: minValue ?? this.minValue,
      maxValue: maxValue ?? this.maxValue,
      availabilityTypes: availabilityTypes ?? this.availabilityTypes,
      status: status ?? this.status,
      playerId: playerId ?? this.playerId,
      clubId: clubId ?? this.clubId,
    );
  }

  JsonMap toQuery({int page = 1, int pageSize = 24}) {
    return _compact(<String, Object?>{
      'page': page,
      'page_size': pageSize,
      'per_page': pageSize,
      'search': query,
      'q': query,
      'position': positions,
      'nationality': nationalities,
      'min_age': minAge,
      'max_age': maxAge,
      'min_value': minValue,
      'max_value': maxValue,
      'availability': availabilityTypes,
      'status': status,
      'player_id': playerId,
      'club_id': clubId,
    });
  }
}

class MarketPage<T> {
  const MarketPage({
    required this.items,
    required this.page,
    required this.pageSize,
    required this.total,
  });

  final List<T> items;
  final int page;
  final int pageSize;
  final int total;

  bool get isEmpty => items.isEmpty;

  static MarketPage<T> fromJson<T>(
    Object? payload,
    T Function(Object? value) parser,
  ) {
    if (payload is List) {
      final List<T> items = payload.map(parser).toList(growable: false);
      return MarketPage<T>(
        items: items,
        page: 1,
        pageSize: items.length,
        total: items.length,
      );
    }
    final JsonMap json = _map(payload, 'market page');
    final Object? rawItems =
        json['items'] ??
        json['data'] ??
        json['results'] ??
        json['players'] ??
        json['listings'] ??
        json['bids'] ??
        json['watchlist'];
    final List<Object?> itemPayload = _list(rawItems, 'market page items');
    return MarketPage<T>(
      items: itemPayload.map(parser).toList(growable: false),
      page: _optionalInt(json['page']) ?? 1,
      pageSize:
          _optionalInt(json['page_size']) ??
          _optionalInt(json['per_page']) ??
          itemPayload.length,
      total: _optionalInt(json['total']) ?? itemPayload.length,
    );
  }
}

class MarketPlayerDTO {
  const MarketPlayerDTO({
    required this.id,
    required this.name,
    this.age,
    this.position,
    this.clubId,
    this.clubName,
    this.nationality,
    this.value,
    this.availability,
    this.contractEnd,
    this.stats = const <String, Object?>{},
    this.listingId,
    this.listingStatus,
    this.askingPrice,
  });

  final String id;
  final String name;
  final int? age;
  final String? position;
  final String? clubId;
  final String? clubName;
  final String? nationality;
  final double? value;
  final String? availability;
  final DateTime? contractEnd;
  final JsonMap stats;
  final String? listingId;
  final String? listingStatus;
  final double? askingPrice;

  factory MarketPlayerDTO.fromJson(Object? value) {
    final JsonMap json = _map(value, 'market player');
    final JsonMap player = _optionalMap(json['player']) ?? json;
    final String? playerId = _firstString(<Object?>[
      player['id'],
      json['player_id'],
      json['playerId'],
      json.containsKey('player') ? null : json['id'],
    ]);
    final String id = _requiredString(playerId, 'market player id');
    final String name = _requiredString(
      _firstString(<Object?>[
        json['name'],
        json['player_name'],
        json['playerName'],
        json['full_name'],
        player['name'],
        player['full_name'],
        player['display_name'],
      ]),
      'market player name',
    );
    final JsonMap? availabilityMap = _optionalMap(
      json['availability'] ?? player['availability'],
    );
    final JsonMap? clubRef = _optionalMap(json['club'] ?? player['club']);
    final JsonMap? contractSummary = _optionalMap(
      json['contract_summary'] ?? player['contract_summary'],
    );
    final String? listingId =
        _firstString(<Object?>[json['listing_id'], json['listingId']]) ??
        (json['player_id'] != null && json['id'] != null
            ? _optionalString(json['id'])
            : null);
    return MarketPlayerDTO(
      id: id,
      name: name,
      age: _optionalInt(json['age'] ?? player['age']),
      position: _firstString(<Object?>[
        json['position'],
        json['normalized_position'],
        player['position'],
        player['normalized_position'],
      ]),
      clubId: _firstString(<Object?>[
        clubRef?['id'],
        json['club_id'],
        json['current_club_id'],
        player['club_id'],
        player['current_club_id'],
      ]),
      clubName: _firstString(<Object?>[
        clubRef?['name'],
        json['club'],
        json['club_name'],
        json['current_club_name'],
        player['club'],
        player['club_name'],
        player['current_club_name'],
      ]),
      nationality: _firstString(<Object?>[
        json['nationality'],
        player['nationality'],
        player['country'],
        player['country_code'],
      ]),
      value: _optionalNumber(
        json['value'] ??
            json['current_value'] ??
            json['base_price'] ??
            json['suggested_price'] ??
            player['value'] ??
            player['current_value'],
      ),
      availability: _firstString(<Object?>[
        availabilityMap?['status'],
        availabilityMap?['label'],
        json['availability_status'],
        player['availability_status'],
        json['status_reason'],
      ]),
      contractEnd: _optionalDateTime(
        json['contract_end'] ??
            json['contractEnd'] ??
            contractSummary?['ends_on'] ??
            contractSummary?['endsOn'],
      ),
      stats:
          _optionalMap(json['stats'] ?? player['stats']) ??
          _optionalMap(json['totals'] ?? player['totals']) ??
          const <String, Object?>{},
      listingId: listingId,
      listingStatus: _optionalString(json['status']),
      askingPrice: _optionalNumber(json['base_price'] ?? json['asking_price']),
    );
  }

  JsonMap toJson() {
    return _compact(<String, Object?>{
      'id': id,
      'name': name,
      'age': age,
      'position': position,
      'club_id': clubId,
      'club_name': clubName,
      'nationality': nationality,
      'value': value,
      'availability': availability,
      'contract_end': contractEnd?.toIso8601String(),
      'stats': stats,
      'listing_id': listingId,
      'listing_status': listingStatus,
      'asking_price': askingPrice,
    });
  }
}

class MarketPlayerDetailDTO {
  const MarketPlayerDetailDTO({
    required this.player,
    this.contractSummary,
    this.availability,
    this.recentEvents = const <TransferActivityDTO>[],
    this.activeBids = const <MarketBidDTO>[],
  });

  final MarketPlayerDTO player;
  final JsonMap? contractSummary;
  final JsonMap? availability;
  final List<TransferActivityDTO> recentEvents;
  final List<MarketBidDTO> activeBids;

  bool get hasBackendDetailTruth =>
      contractSummary != null ||
      availability != null ||
      recentEvents.isNotEmpty;

  factory MarketPlayerDetailDTO.fromJson(Object? value) {
    final JsonMap json = _map(value, 'market player detail');
    final JsonMap? overviewPlayer =
        _optionalMap(json['player']) ??
        _optionalMap(json['profile']) ??
        _optionalMap(json['summary']);
    final MarketPlayerDTO player = MarketPlayerDTO.fromJson(
      overviewPlayer ?? json,
    );
    return MarketPlayerDetailDTO(
      player: player,
      contractSummary: _optionalMap(json['contract_summary']),
      availability: _optionalMap(json['availability']),
      recentEvents: _list(
        json['events'] ?? json['recent_events'],
        'market player events',
        fallback: const <Object?>[],
      ).map(TransferActivityDTO.fromJson).toList(growable: false),
      activeBids: _list(
        json['active_bids'] ?? json['recent_bids'],
        'market player bids',
        fallback: const <Object?>[],
      ).map(MarketBidDTO.fromJson).toList(growable: false),
    );
  }
}

class MarketWalletReservationDTO {
  const MarketWalletReservationDTO({
    this.status,
    this.reservedAmount,
    this.reference,
    this.raw = const <String, Object?>{},
  });

  final String? status;
  final double? reservedAmount;
  final String? reference;
  final JsonMap raw;

  bool get isBackendConfirmed =>
      status != null && status!.isNotEmpty && reservedAmount != null;

  static MarketWalletReservationDTO? maybeFromBidJson(Object? value) {
    final JsonMap json = _map(value, 'market bid');
    final JsonMap structuredTerms =
        _optionalMap(json['structured_terms_json']) ??
        _optionalMap(json['structuredTerms']) ??
        const <String, Object?>{};
    final JsonMap nested =
        _optionalMap(json['wallet_reservation']) ??
        _optionalMap(structuredTerms['wallet_reservation']) ??
        const <String, Object?>{};
    final String? status = _firstString(<Object?>[
      json['wallet_reservation_status'],
      json['walletReservationStatus'],
      nested['status'],
    ]);
    final double? amount = _optionalNumber(
      json['wallet_reserved_amount'] ??
          json['walletReservedAmount'] ??
          nested['actual_reserved_gtex_coin'] ??
          nested['amount_gtex_coin'] ??
          nested['reserved_amount'],
    );
    final String? reference = _firstString(<Object?>[
      json['wallet_reservation_reference'],
      json['walletReservationReference'],
      nested['reference'],
    ]);
    if (status == null &&
        amount == null &&
        reference == null &&
        nested.isEmpty) {
      return null;
    }
    return MarketWalletReservationDTO(
      status: status,
      reservedAmount: amount,
      reference: reference,
      raw: nested,
    );
  }

  JsonMap toJson() {
    return _compact(<String, Object?>{
      'status': status,
      'reserved_amount': reservedAmount,
      'reference': reference,
      'raw': raw,
    });
  }
}

class MarketBidEventDTO {
  const MarketBidEventDTO({
    required this.id,
    required this.type,
    this.status,
    this.summary,
    this.timestamp,
  });

  final String id;
  final String type;
  final String? status;
  final String? summary;
  final DateTime? timestamp;

  factory MarketBidEventDTO.fromJson(Object? value) {
    final JsonMap json = _map(value, 'market bid event');
    return MarketBidEventDTO(
      id: _requiredString(
        _firstString(<Object?>[json['id'], json['event_id']]),
        'market bid event id',
      ),
      type: _requiredString(
        _firstString(<Object?>[json['type'], json['event_type']]),
        'market bid event type',
      ),
      status: _optionalString(json['status'] ?? json['event_status']),
      summary: _optionalString(json['summary']),
      timestamp: _optionalDateTime(json['timestamp'] ?? json['updated_at']),
    );
  }
}

class MarketBidDTO {
  const MarketBidDTO({
    required this.id,
    required this.playerId,
    required this.amount,
    required this.status,
    required this.rawStatus,
    this.windowId,
    this.listingId,
    this.fromClubId,
    this.fromClubName,
    this.toClubId,
    this.toClubName,
    this.createdAt,
    this.expiresAt,
    this.updatedAt,
    this.walletReservation,
    this.events = const <MarketBidEventDTO>[],
    this.notes,
  });

  final String id;
  final String? windowId;
  final String? listingId;
  final String playerId;
  final String? fromClubId;
  final String? fromClubName;
  final String? toClubId;
  final String? toClubName;
  final double amount;
  final MarketBidStatus status;
  final String rawStatus;
  final DateTime? createdAt;
  final DateTime? expiresAt;
  final DateTime? updatedAt;
  final MarketWalletReservationDTO? walletReservation;
  final List<MarketBidEventDTO> events;
  final String? notes;

  bool get hasBackendReservationTruth =>
      !status.requiresReservationTruth ||
      rawStatus.trim().toLowerCase() == 'draft' ||
      (walletReservation?.isBackendConfirmed ?? false);

  factory MarketBidDTO.fromJson(Object? value) {
    final JsonMap json = _map(value, 'market bid');
    final Object? statusValue = json['status'] ?? json['bid_status'];
    final String rawStatus = _requiredString(statusValue, 'market bid status');
    final JsonMap? fromClub = _optionalMap(json['from_club']);
    final JsonMap? toClub = _optionalMap(json['to_club']);
    return MarketBidDTO(
      id: _requiredString(
        _firstString(<Object?>[json['id'], json['bid_id'], json['bidId']]),
        'market bid id',
      ),
      windowId: _optionalString(json['window_id'] ?? json['windowId']),
      listingId: _optionalString(json['listing_id'] ?? json['listingId']),
      playerId: _requiredString(
        _firstString(<Object?>[json['player_id'], json['playerId']]),
        'market bid player id',
      ),
      fromClubId: _firstString(<Object?>[
        fromClub?['id'],
        json['from_club_id'],
        json['fromClubId'],
        json['buying_club_id'],
        json['club_id'],
      ]),
      fromClubName: _firstString(<Object?>[
        fromClub?['name'],
        json['from_club'],
        json['fromClub'],
        json['buying_club_name'],
        json['club_name'],
      ]),
      toClubId: _firstString(<Object?>[
        toClub?['id'],
        json['to_club_id'],
        json['toClubId'],
        json['selling_club_id'],
      ]),
      toClubName: _firstString(<Object?>[
        toClub?['name'],
        json['to_club'],
        json['toClub'],
        json['selling_club_name'],
      ]),
      amount: _requiredNumber(
        json['amount'] ?? json['bid_amount'],
        'market bid amount',
      ),
      status: MarketBidStatus.fromBackend(statusValue),
      rawStatus: rawStatus,
      createdAt: _optionalDateTime(json['created_at'] ?? json['createdAt']),
      expiresAt: _optionalDateTime(json['expires_at'] ?? json['expiresAt']),
      updatedAt: _optionalDateTime(json['updated_at'] ?? json['updatedAt']),
      walletReservation: MarketWalletReservationDTO.maybeFromBidJson(json),
      events: _list(
        json['events'],
        'market bid events',
        fallback: const <Object?>[],
      ).map(MarketBidEventDTO.fromJson).toList(growable: false),
      notes: _optionalString(json['notes']),
    );
  }

  factory MarketBidDTO.fromListingBid(Object? value, Object? listing) {
    final JsonMap bid = _map(value, 'transfer listing bid');
    final JsonMap listingJson = _map(listing, 'transfer listing');
    final JsonMap merged = <String, Object?>{
      ...bid,
      'id': bid['bid_id'] ?? bid['id'],
      'listing_id': listingJson['id'],
      'player_id': listingJson['player_id'],
      'selling_club_id': listingJson['selling_club_id'],
      'status': bid['status'] ?? 'pending',
      'amount': bid['amount'],
      'club_id': bid['club_id'],
      'club_name': bid['club_name'],
      'created_at': bid['timestamp'],
    };
    return MarketBidDTO.fromJson(merged);
  }

  JsonMap toJson() {
    return _compact(<String, Object?>{
      'id': id,
      'window_id': windowId,
      'listing_id': listingId,
      'player_id': playerId,
      'from_club_id': fromClubId,
      'from_club_name': fromClubName,
      'to_club_id': toClubId,
      'to_club_name': toClubName,
      'amount': amount,
      'status': status.backendValue,
      'raw_status': rawStatus,
      'created_at': createdAt?.toIso8601String(),
      'expires_at': expiresAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'wallet_reservation': walletReservation?.toJson(),
      'events': events
          .map(
            (MarketBidEventDTO event) => _compact(<String, Object?>{
              'id': event.id,
              'type': event.type,
              'status': event.status,
              'summary': event.summary,
              'timestamp': event.timestamp?.toIso8601String(),
            }),
          )
          .toList(growable: false),
      'notes': notes,
    });
  }
}

class MarketBasketItemDTO {
  const MarketBasketItemDTO({
    required this.playerId,
    this.addedAt,
    this.checkoutEligible,
    this.blockedReason,
    this.player,
    this.watchlistId,
  });

  final String playerId;
  final DateTime? addedAt;
  final bool? checkoutEligible;
  final String? blockedReason;
  final MarketPlayerDTO? player;
  final String? watchlistId;

  factory MarketBasketItemDTO.fromJson(Object? value) {
    final JsonMap json = _map(value, 'market basket item');
    final JsonMap? playerJson = _optionalMap(json['player']);
    return MarketBasketItemDTO(
      playerId: _requiredString(
        _firstString(<Object?>[
          json['player_id'],
          json['playerId'],
          playerJson?['id'],
        ]),
        'basket player id',
      ),
      addedAt: _optionalDateTime(json['added_at'] ?? json['created_at']),
      checkoutEligible: _optionalBool(json['checkout_eligible']),
      blockedReason: _optionalString(
        json['blocked_reason'] ?? json['blockedReason'],
      ),
      player: playerJson == null ? null : MarketPlayerDTO.fromJson(playerJson),
      watchlistId: _optionalString(json['id'] ?? json['watchlist_id']),
    );
  }
}

class MarketCheckoutDTO {
  const MarketCheckoutDTO({
    required this.items,
    required this.walletCurrency,
    this.ready = false,
    this.blockedReasons = const <String>[],
    this.walletAvailableBalance,
    this.walletReservedBalance,
    this.walletReservationStatus,
    this.blockedReason,
  });

  final List<MarketBasketItemDTO> items;
  final String walletCurrency;
  final bool ready;
  final List<String> blockedReasons;
  final double? walletAvailableBalance;
  final double? walletReservedBalance;
  final String? walletReservationStatus;
  final String? blockedReason;

  bool get hasWalletTruth =>
      walletAvailableBalance != null && walletReservedBalance != null;

  factory MarketCheckoutDTO.fromBackend({
    List<MarketBasketItemDTO>? items,
    Object? readinessPayload,
    Object? walletPayload,
  }) {
    final JsonMap readiness =
        readinessPayload == null
            ? const <String, Object?>{}
            : _map(readinessPayload, 'market checkout readiness');
    final JsonMap wallet =
        walletPayload == null
            ? const <String, Object?>{}
            : _map(walletPayload, 'market checkout wallet');
    final List<MarketBasketItemDTO> resolvedItems =
        items ??
        _list(
          readiness['items'],
          'market checkout items',
          fallback: const <Object?>[],
        ).map(MarketBasketItemDTO.fromJson).toList(growable: false);
    final double? available = _optionalNumber(
      wallet['available_balance'] ??
          wallet['availableBalance'] ??
          wallet['available'],
    );
    final double? reserved = _optionalNumber(
      wallet['reserved_balance'] ?? wallet['reservedBalance'],
    );
    return MarketCheckoutDTO(
      items: resolvedItems,
      walletCurrency:
          _optionalString(wallet['currency'] ?? wallet['unit']) ?? 'coin',
      ready: _optionalBool(readiness['ready']) ?? false,
      blockedReasons: _stringList(
        readiness['blocked_reasons'] ?? readiness['blockedReasons'],
      ),
      walletAvailableBalance: available,
      walletReservedBalance: reserved,
      walletReservationStatus: _optionalString(wallet['reservation_status']),
      blockedReason:
          _optionalString(readiness['blocked_reason']) ??
          _optionalString(wallet['blocked_reason']),
    );
  }
}

class TransferActivityDTO {
  const TransferActivityDTO({
    required this.id,
    required this.type,
    this.timestamp,
    this.fromClub,
    this.toClub,
    this.playerId,
    this.playerName,
    this.amount,
    this.status,
  });

  final String id;
  final String type;
  final DateTime? timestamp;
  final String? fromClub;
  final String? toClub;
  final String? playerId;
  final String? playerName;
  final double? amount;
  final String? status;

  factory TransferActivityDTO.fromJson(Object? value) {
    final JsonMap json = _map(value, 'transfer activity');
    final JsonMap? player = _optionalMap(json['player']);
    return TransferActivityDTO(
      id: _requiredString(
        _firstString(<Object?>[json['id'], json['event_id']]),
        'transfer activity id',
      ),
      type: _requiredString(
        _firstString(<Object?>[json['type'], json['event_type']]),
        'transfer activity type',
      ),
      timestamp: _optionalDateTime(
        json['timestamp'] ?? json['created_at'] ?? json['updated_at'],
      ),
      fromClub: _optionalString(json['from_club'] ?? json['fromClub']),
      toClub: _optionalString(json['to_club'] ?? json['toClub']),
      playerId: _optionalString(json['player_id'] ?? player?['id']),
      playerName: _optionalString(json['player_name'] ?? player?['name']),
      amount: _optionalNumber(json['amount'] ?? json['bid_amount']),
      status: _optionalString(json['status']),
    );
  }

  factory TransferActivityDTO.fromBid(MarketBidDTO bid) {
    return TransferActivityDTO(
      id: bid.id,
      type: 'market.bid.${bid.status.backendValue}',
      timestamp: bid.updatedAt ?? bid.createdAt,
      fromClub: bid.fromClubName ?? bid.fromClubId,
      toClub: bid.toClubName ?? bid.toClubId,
      playerId: bid.playerId,
      amount: bid.amount,
      status: bid.status.backendValue,
    );
  }
}

class MarketFilterMetaDTO {
  const MarketFilterMetaDTO({
    required this.positions,
    required this.nationalities,
    required this.minAge,
    required this.maxAge,
    required this.valueBrackets,
    required this.availabilityTypes,
  });

  final List<String> positions;
  final List<String> nationalities;
  final int minAge;
  final int maxAge;
  final List<String> valueBrackets;
  final List<String> availabilityTypes;

  factory MarketFilterMetaDTO.fromJson(Object? value) {
    final JsonMap json = _map(value, 'market filter metadata');
    final JsonMap? ageRange = _optionalMap(json['age_range']);
    return MarketFilterMetaDTO(
      positions: _stringList(json['positions']),
      nationalities: _stringList(json['nationalities']),
      minAge: _optionalInt(json['min_age'] ?? ageRange?['min']) ?? 0,
      maxAge: _optionalInt(json['max_age'] ?? ageRange?['max']) ?? 99,
      valueBrackets: _list(
            json['value_brackets'],
            'market value brackets',
            fallback: const <Object?>[],
          )
          .map((Object? item) {
            final JsonMap? bracket = _optionalMap(item);
            return bracket == null
                ? _optionalString(item)
                : _firstString(<Object?>[bracket['label'], bracket['name']]);
          })
          .whereType<String>()
          .toList(growable: false),
      availabilityTypes: _stringList(json['availability_types']),
    );
  }
}

class MarketHubDTO {
  const MarketHubDTO({
    required this.players,
    this.activeBids,
    this.basketItems,
    this.activity,
    this.generatedAt,
  });

  final MarketPage<MarketPlayerDTO> players;
  final List<MarketBidDTO>? activeBids;
  final List<MarketBasketItemDTO>? basketItems;
  final List<TransferActivityDTO>? activity;
  final DateTime? generatedAt;

  bool get hasPartialBackendData =>
      activeBids == null || basketItems == null || activity == null;
}

class MarketBidsRequest {
  const MarketBidsRequest({this.windowId, this.clubId});

  final String? windowId;
  final String? clubId;
}

class MarketBidDetailRequest {
  const MarketBidDetailRequest({required this.bidId, this.windowId});

  final String bidId;
  final String? windowId;
}

class PlaceBidRequest {
  const PlaceBidRequest({
    required this.amount,
    this.listingId,
    this.windowId,
    this.playerId,
    this.sellingClubId,
    this.buyingClubId,
    this.wageOfferAmount,
    this.contractYears,
    this.sellOnClausePct,
    this.notes,
  });

  final String? listingId;
  final String? windowId;
  final String? playerId;
  final String? sellingClubId;
  final String? buyingClubId;
  final double amount;
  final double? wageOfferAmount;
  final int? contractYears;
  final double? sellOnClausePct;
  final String? notes;

  JsonMap toLifecycleJson() {
    return _compact(<String, Object?>{
      'player_id': playerId,
      'selling_club_id': sellingClubId,
      'buying_club_id': buyingClubId,
      'bid_amount': amount,
      'wage_offer_amount': wageOfferAmount,
      'contract_years': contractYears,
      'sell_on_clause_pct': sellOnClausePct,
      'notes': notes,
    });
  }

  JsonMap toListingJson() {
    return _compact(<String, Object?>{
      'bidder_club_id': buyingClubId,
      'amount': amount,
      'activity_context': 'market',
    });
  }
}

class CounterBidRequest {
  const CounterBidRequest({
    required this.windowId,
    required this.bidId,
    this.amount,
    this.wageOfferAmount,
    this.contractYears,
    this.sellOnClausePct,
    this.notes,
  });

  final String windowId;
  final String bidId;
  final double? amount;
  final double? wageOfferAmount;
  final int? contractYears;
  final double? sellOnClausePct;
  final String? notes;

  JsonMap toJson() {
    return _compact(<String, Object?>{
      'bid_amount': amount,
      'wage_offer_amount': wageOfferAmount,
      'contract_years': contractYears,
      'sell_on_clause_pct': sellOnClausePct,
      'notes': notes,
    });
  }
}

class AcceptBidRequest {
  const AcceptBidRequest({
    required this.windowId,
    required this.bidId,
    required this.contractEndsOn,
    this.contractStartsOn,
    this.wageAmount,
    this.bonusTerms,
    this.releaseClauseAmount,
  });

  final String windowId;
  final String bidId;
  final DateTime contractEndsOn;
  final DateTime? contractStartsOn;
  final double? wageAmount;
  final String? bonusTerms;
  final double? releaseClauseAmount;

  JsonMap toJson() {
    return _compact(<String, Object?>{
      'contract_ends_on': _dateOnly(contractEndsOn),
      'contract_starts_on':
          contractStartsOn == null ? null : _dateOnly(contractStartsOn!),
      'wage_amount': wageAmount,
      'bonus_terms': bonusTerms,
      'release_clause_amount': releaseClauseAmount,
    });
  }
}

class RejectBidRequest {
  const RejectBidRequest({
    required this.windowId,
    required this.bidId,
    this.reason,
  });

  final String windowId;
  final String bidId;
  final String? reason;

  JsonMap toJson() => _compact(<String, Object?>{'reason': reason});
}

class WithdrawBidRequest {
  const WithdrawBidRequest({required this.bidId, this.windowId, this.reason});

  final String? windowId;
  final String bidId;
  final String? reason;

  JsonMap toJson() => _compact(<String, Object?>{'reason': reason});
}

JsonMap _map(Object? value, String label) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? item) => MapEntry(key.toString(), item),
    );
  }
  throw FormatException('Expected $label object from backend.');
}

JsonMap? _optionalMap(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is! Map) {
    return null;
  }
  return _map(value, 'market nested object');
}

List<Object?> _list(Object? value, String label, {List<Object?>? fallback}) {
  if (value == null) {
    if (fallback != null) {
      return fallback;
    }
    throw FormatException('Expected $label list from backend.');
  }
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  throw FormatException('Expected $label list from backend.');
}

String? _firstString(List<Object?> values) {
  for (final Object? value in values) {
    final String? parsed = _optionalString(value);
    if (parsed != null) {
      return parsed;
    }
  }
  return null;
}

String _requiredString(Object? value, String label) {
  final String? parsed = _optionalString(value);
  if (parsed == null) {
    throw FormatException('Missing $label from backend.');
  }
  return parsed;
}

String? _optionalString(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is Map) {
    return null;
  }
  final String parsed = value.toString().trim();
  return parsed.isEmpty ? null : parsed;
}

double _requiredNumber(Object? value, String label) {
  final double? parsed = _optionalNumber(value);
  if (parsed == null) {
    throw FormatException('Missing $label from backend.');
  }
  return parsed;
}

double? _optionalNumber(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString().trim());
}

int? _optionalInt(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value.toString().trim());
}

bool? _optionalBool(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is bool) {
    return value;
  }
  final String normalized = value.toString().trim().toLowerCase();
  if (<String>{'1', 'true', 'yes'}.contains(normalized)) {
    return true;
  }
  if (<String>{'0', 'false', 'no'}.contains(normalized)) {
    return false;
  }
  return null;
}

DateTime _requiredDateTime(Object? value, String label) {
  final DateTime? parsed = _optionalDateTime(value);
  if (parsed == null) {
    throw FormatException('Missing $label from backend.');
  }
  return parsed;
}

DateTime? _optionalDateTime(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value.toUtc();
  }
  return DateTime.tryParse(value.toString())?.toUtc();
}

List<String> _stringList(Object? value) {
  if (value == null) {
    return const <String>[];
  }
  return _list(
    value,
    'market string list',
  ).map(_optionalString).whereType<String>().toList(growable: false);
}

JsonMap _compact(JsonMap value) {
  final JsonMap result = <String, Object?>{};
  for (final MapEntry<String, Object?> entry in value.entries) {
    final Object? item = entry.value;
    if (item == null) {
      continue;
    }
    if (item is String && item.trim().isEmpty) {
      continue;
    }
    if (item is Iterable && item.isEmpty) {
      continue;
    }
    result[entry.key] = item;
  }
  return result;
}

String _dateOnly(DateTime value) =>
    value.toUtc().toIso8601String().split('T').first;
