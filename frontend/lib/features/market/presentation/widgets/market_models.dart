import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';

enum MarketAccessLevel { owner, manager, scout, guest, suspended, blocked }

class MarketAccessPolicy {
  const MarketAccessPolicy({
    required this.level,
    required this.roleLabel,
    required this.canView,
    required this.canBid,
    required this.canUseBasket,
    required this.canCheckout,
    required this.canActOnBids,
    this.blockReason,
    this.checkoutBlockReason,
    this.actionBlockReason,
  });

  final MarketAccessLevel level;
  final String roleLabel;
  final bool canView;
  final bool canBid;
  final bool canUseBasket;
  final bool canCheckout;
  final bool canActOnBids;
  final String? blockReason;
  final String? checkoutBlockReason;
  final String? actionBlockReason;

  bool get isBlocked => !canView;
  bool get isScout => level == MarketAccessLevel.scout;
  bool get isManager => level == MarketAccessLevel.manager;

  static MarketAccessPolicy resolve({
    required String role,
    required bool authenticated,
    required bool hasClubContext,
  }) {
    final String normalized = role.trim().toLowerCase();
    final String dotted = normalized.replaceAll('_', '.').replaceAll('-', '.');

    if (dotted.contains('suspended')) {
      return const MarketAccessPolicy(
        level: MarketAccessLevel.suspended,
        roleLabel: 'Suspended',
        canView: false,
        canBid: false,
        canUseBasket: false,
        canCheckout: false,
        canActOnBids: false,
        blockReason: 'Account suspended - contact support',
      );
    }

    if (!authenticated ||
        dotted.isEmpty ||
        dotted == 'guest' ||
        dotted == 'unauthenticated') {
      return const MarketAccessPolicy(
        level: MarketAccessLevel.guest,
        roleLabel: 'Guest',
        canView: false,
        canBid: false,
        canUseBasket: false,
        canCheckout: false,
        canActOnBids: false,
        blockReason: 'Create an account to access the transfer market.',
      );
    }

    if (!hasClubContext) {
      return const MarketAccessPolicy(
        level: MarketAccessLevel.blocked,
        roleLabel: 'Club required',
        canView: false,
        canBid: false,
        canUseBasket: false,
        canCheckout: false,
        canActOnBids: false,
        blockReason: 'Club context required for market operations.',
      );
    }

    if (dotted == 'club.owner' ||
        dotted.endsWith('.owner') ||
        dotted == 'owner') {
      return const MarketAccessPolicy(
        level: MarketAccessLevel.owner,
        roleLabel: 'Club owner',
        canView: true,
        canBid: true,
        canUseBasket: true,
        canCheckout: true,
        canActOnBids: true,
      );
    }

    if (dotted == 'club.manager' ||
        dotted.endsWith('.manager') ||
        dotted == 'manager') {
      return const MarketAccessPolicy(
        level: MarketAccessLevel.manager,
        roleLabel: 'Club manager',
        canView: true,
        canBid: true,
        canUseBasket: true,
        canCheckout: false,
        canActOnBids: true,
        checkoutBlockReason: 'Owner approval required',
      );
    }

    if (dotted == 'club.scout' ||
        dotted.endsWith('.scout') ||
        dotted == 'scout') {
      return const MarketAccessPolicy(
        level: MarketAccessLevel.scout,
        roleLabel: 'Club scout',
        canView: true,
        canBid: false,
        canUseBasket: false,
        canCheckout: false,
        canActOnBids: false,
        actionBlockReason: 'Scout read-only access',
        checkoutBlockReason: 'Scout read-only access',
      );
    }

    return const MarketAccessPolicy(
      level: MarketAccessLevel.blocked,
      roleLabel: 'Unsupported role',
      canView: false,
      canBid: false,
      canUseBasket: false,
      canCheckout: false,
      canActOnBids: false,
      blockReason: 'Account role is not eligible for market operations.',
    );
  }
}

enum MarketBidLifecycleStatus {
  pending,
  counter,
  accepted,
  rejected,
  withdrawn,
  unknown,
}

extension MarketBidLifecycleStatusLabel on MarketBidLifecycleStatus {
  String get label {
    return switch (this) {
      MarketBidLifecycleStatus.pending => 'Pending',
      MarketBidLifecycleStatus.counter => 'Counter',
      MarketBidLifecycleStatus.accepted => 'Accepted',
      MarketBidLifecycleStatus.rejected => 'Rejected',
      MarketBidLifecycleStatus.withdrawn => 'Withdrawn',
      MarketBidLifecycleStatus.unknown => 'Unknown',
    };
  }
}

MarketBidLifecycleStatus marketBidLifecycleStatusFrom(String? value) {
  final String normalized =
      value?.trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_') ??
      '';
  return switch (normalized) {
    '' => MarketBidLifecycleStatus.pending,
    'pending' ||
    'submitted' ||
    'open' ||
    'active' ||
    'bid_placed' ||
    'reserved' ||
    'partially_reserved' ||
    'awaiting_contract_offer' ||
    'player_delayed' => MarketBidLifecycleStatus.pending,
    'counter' ||
    'countered' ||
    'counter_offer' ||
    'counter_offer_sent' => MarketBidLifecycleStatus.counter,
    'accepted' ||
    'accept' ||
    'completed' ||
    'sold' ||
    'settled' ||
    'moved_to_lifecycle' => MarketBidLifecycleStatus.accepted,
    'rejected' ||
    'reject' ||
    'coach_blocked' ||
    'collapsed' ||
    'failed' => MarketBidLifecycleStatus.rejected,
    'withdrawn' ||
    'retracted' ||
    'cancelled' ||
    'canceled' ||
    'released' ||
    'expired' => MarketBidLifecycleStatus.withdrawn,
    _ => MarketBidLifecycleStatus.unknown,
  };
}

class MarketBidViewModel {
  const MarketBidViewModel({
    required this.id,
    required this.clubId,
    required this.clubName,
    required this.amount,
    required this.status,
    required this.statusLabel,
    required this.isHighest,
    required this.timestamp,
    required this.walletReservationStatus,
    required this.walletReservedAmount,
    required this.walletReservationReference,
  });

  final String id;
  final String clubId;
  final String clubName;
  final double? amount;
  final MarketBidLifecycleStatus status;
  final String statusLabel;
  final bool isHighest;
  final DateTime? timestamp;
  final String? walletReservationStatus;
  final double? walletReservedAmount;
  final String? walletReservationReference;

  factory MarketBidViewModel.fromJson(JsonMap json, {String? fallbackStatus}) {
    final String? rawStatus =
        stringOrNullValue(json['status']) ??
        stringOrNullValue(json['bid_status']) ??
        stringOrNullValue(json['lifecycle_status']) ??
        fallbackStatus;
    final MarketBidLifecycleStatus status = marketBidLifecycleStatusFrom(
      rawStatus,
    );
    return MarketBidViewModel(
      id: stringValue(json['bid_id'], fallback: stringValue(json['id'])),
      clubId: stringValue(json['club_id']),
      clubName: stringValue(
        json['club_name'],
        fallback: stringValue(json['club_id'], fallback: 'Club pending'),
      ),
      amount: _optionalNumber(json['amount']),
      status: status,
      statusLabel:
          status == MarketBidLifecycleStatus.unknown
              ? stringValue(rawStatus, fallback: 'Unknown')
              : status.label,
      isHighest: boolValue(json['is_highest']),
      timestamp:
          dateTimeValue(json['timestamp']) ?? dateTimeValue(json['created_at']),
      walletReservationStatus:
          stringOrNullValue(json['wallet_reservation_status']) ??
          stringOrNullValue(json['walletReservationStatus']),
      walletReservedAmount:
          _optionalNumber(json['wallet_reserved_amount']) ??
          _optionalNumber(json['walletReservedAmount']),
      walletReservationReference:
          stringOrNullValue(json['wallet_reservation_reference']) ??
          stringOrNullValue(json['walletReservationReference']),
    );
  }
}

class MarketListingViewModel {
  const MarketListingViewModel({
    required this.id,
    required this.playerId,
    required this.playerName,
    required this.position,
    required this.currentClubName,
    required this.basePrice,
    required this.currentHighestBid,
    required this.status,
    required this.watchlistCount,
    required this.bidCount,
    required this.marketSignal,
    required this.channel,
    required this.timeRemaining,
    required this.negotiationId,
    required this.expiresAt,
    required this.bids,
    required this.raw,
  });

  final String id;
  final String playerId;
  final String playerName;
  final String? position;
  final String? currentClubName;
  final double basePrice;
  final double currentHighestBid;
  final String status;
  final int watchlistCount;
  final int bidCount;
  final String marketSignal;
  final String channel;
  final int timeRemaining;
  final String? negotiationId;
  final DateTime? expiresAt;
  final List<MarketBidViewModel> bids;
  final JsonMap raw;

  factory MarketListingViewModel.fromRecord(TransferCenterListingRecord item) {
    return MarketListingViewModel(
      id: item.id,
      playerId: item.playerId,
      playerName: item.playerName,
      position: null,
      currentClubName: item.currentClubName,
      basePrice: item.basePrice,
      currentHighestBid: item.currentHighestBid,
      status: item.status,
      watchlistCount: item.watchlistCount,
      bidCount: item.bidCount,
      marketSignal: item.marketSignal,
      channel: item.channel,
      timeRemaining: item.timeRemaining,
      negotiationId: item.negotiationId,
      expiresAt: null,
      bids: item.bidders
          .map(
            (JsonMap bidder) =>
                MarketBidViewModel.fromJson(bidder, fallbackStatus: 'pending'),
          )
          .toList(growable: false),
      raw: const <String, Object?>{},
    );
  }

  factory MarketListingViewModel.fromJson(
    JsonMap json, {
    JsonMap? negotiation,
  }) {
    final JsonMap player = jsonMap(
      json['player'],
      label: 'market listing player',
      fallback: const <String, Object?>{},
    );
    final String? negotiationStatus =
        negotiation == null ? null : stringOrNullValue(negotiation['status']);
    final List<JsonMap> rawBids = <JsonMap>[
      if (jsonMapOrNull(json['current_bid']) case final JsonMap currentBid)
        currentBid,
      ...jsonMapList(json['bidders'], label: 'market bidders'),
    ];
    final Set<String> seenBidIds = <String>{};
    final List<MarketBidViewModel> bids = rawBids
        .map((JsonMap bidder) {
          final bool highest = boolValue(bidder['is_highest']);
          return MarketBidViewModel.fromJson(
            bidder,
            fallbackStatus: highest ? negotiationStatus : 'pending',
          );
        })
        .where((MarketBidViewModel bid) {
          if (bid.id.isEmpty) {
            return true;
          }
          return seenBidIds.add(bid.id);
        })
        .toList(growable: false);

    return MarketListingViewModel(
      id: stringValue(json['id']),
      playerId: stringValue(json['player_id']),
      playerName:
          stringOrNullValue(player['full_name']) ??
          stringValue(json['player_id'], fallback: 'Player pending'),
      position: stringOrNullValue(player['normalized_position']),
      currentClubName: stringOrNullValue(player['current_club_name']),
      basePrice: numberValue(json['base_price']),
      currentHighestBid: numberValue(json['current_highest_bid']),
      status: stringValue(json['status'], fallback: 'unknown'),
      watchlistCount: intValue(json['watchlist_count']),
      bidCount: intValue(json['bid_count'], fallback: bids.length),
      marketSignal: stringValue(
        json['market_signal'],
        fallback: 'Market signal not returned',
      ),
      channel: stringValue(json['channel'], fallback: 'channel pending'),
      timeRemaining: intValue(json['time_remaining']),
      negotiationId: stringOrNullValue(json['negotiation_id']),
      expiresAt: dateTimeValue(json['expires_at']),
      bids: bids,
      raw: json,
    );
  }

  MarketBidViewModel? bidById(String bidId) {
    for (final MarketBidViewModel bid in bids) {
      if (bid.id == bidId) {
        return bid;
      }
    }
    return null;
  }
}

class MarketDetailViewModel {
  const MarketDetailViewModel({
    required this.listing,
    required this.negotiation,
  });

  final MarketListingViewModel listing;
  final JsonMap? negotiation;

  factory MarketDetailViewModel.fromTransferCenter(
    TransferCenterDetailData detail,
  ) {
    return MarketDetailViewModel(
      listing: MarketListingViewModel.fromJson(
        detail.listing,
        negotiation: detail.negotiation,
      ),
      negotiation: detail.negotiation,
    );
  }
}

class MarketBidDetailViewModel {
  const MarketBidDetailViewModel({
    required this.listing,
    required this.bid,
    required this.negotiation,
  });

  final MarketListingViewModel listing;
  final MarketBidViewModel bid;
  final JsonMap? negotiation;
}

String marketMoney(num value) {
  final double amount = value.toDouble();
  final bool whole = amount == amount.roundToDouble();
  return '${amount.toStringAsFixed(whole ? 0 : 2)} GTex';
}

String marketOptionalMoney(double? value) {
  if (value == null) {
    return 'Amount not reported';
  }
  return marketMoney(value);
}

String marketDurationLabel(int seconds) {
  if (seconds <= 0) {
    return 'Expired';
  }
  final int days = seconds ~/ 86400;
  if (days > 0) {
    return '${days}d';
  }
  final int hours = seconds ~/ 3600;
  if (hours > 0) {
    return '${hours}h';
  }
  final int minutes = seconds ~/ 60;
  return '${minutes}m';
}

String marketDateLabel(DateTime? value) {
  if (value == null) {
    return 'Timestamp not reported';
  }
  final DateTime local = value.toLocal();
  return '${local.year.toString().padLeft(4, '0')}-'
      '${local.month.toString().padLeft(2, '0')}-'
      '${local.day.toString().padLeft(2, '0')}';
}

double? _optionalNumber(Object? value) {
  if (value == null) {
    return null;
  }
  return numberValue(value);
}
