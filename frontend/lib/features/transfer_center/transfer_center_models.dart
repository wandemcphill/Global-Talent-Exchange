import '../shared/data/gte_json_support.dart';

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
