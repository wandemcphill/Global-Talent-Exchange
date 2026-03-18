import '../../shared/data/gte_feature_support.dart';

class CreatorMatchAccessQuery {
  const CreatorMatchAccessQuery({
    this.durationMinutes = 90,
  });

  final int durationMinutes;

  Map<String, Object?> toQuery() => <String, Object?>{
        'duration_minutes': durationMinutes,
      };
}

class CreatorMatchAnalyticsQuery {
  const CreatorMatchAnalyticsQuery({
    this.clubId,
  });

  final String? clubId;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'club_id': clubId,
      });
}

class CreatorClubStadiumQuery {
  const CreatorClubStadiumQuery({
    required this.seasonId,
  });

  final String seasonId;

  Map<String, Object?> toQuery() => <String, Object?>{'season_id': seasonId};
}

class CreatorBroadcastPurchaseRequest {
  const CreatorBroadcastPurchaseRequest({
    required this.durationMinutes,
  });

  final int durationMinutes;

  JsonMap toJson() => <String, Object?>{
        'duration_minutes': durationMinutes,
      };
}

class CreatorSeasonPassCreateRequest {
  const CreatorSeasonPassCreateRequest({
    required this.seasonId,
    required this.clubId,
  });

  final String seasonId;
  final String clubId;

  JsonMap toJson() => <String, Object?>{
        'season_id': seasonId,
        'club_id': clubId,
      };
}

class CreatorStadiumConfigUpdateRequest {
  const CreatorStadiumConfigUpdateRequest({
    required this.seasonId,
    required this.matchdayTicketPriceCoin,
    required this.seasonPassPriceCoin,
    required this.vipTicketPriceCoin,
    this.visualUpgradeLevel = 1,
    this.customChantText,
    this.customVisuals = const <String, Object?>{},
  });

  final String seasonId;
  final double matchdayTicketPriceCoin;
  final double seasonPassPriceCoin;
  final double vipTicketPriceCoin;
  final int visualUpgradeLevel;
  final String? customChantText;
  final JsonMap customVisuals;

  JsonMap toJson() => <String, Object?>{
        'season_id': seasonId,
        'matchday_ticket_price_coin': matchdayTicketPriceCoin,
        'season_pass_price_coin': seasonPassPriceCoin,
        'vip_ticket_price_coin': vipTicketPriceCoin,
        'visual_upgrade_level': visualUpgradeLevel,
        if (customChantText != null) 'custom_chant_text': customChantText,
        'custom_visuals_json': customVisuals,
      };
}

class CreatorStadiumTicketPurchaseRequest {
  const CreatorStadiumTicketPurchaseRequest({
    required this.ticketType,
  });

  final String ticketType;

  JsonMap toJson() => <String, Object?>{
        'ticket_type': ticketType,
      };
}

class CreatorStadiumPlacementCreateRequest {
  const CreatorStadiumPlacementCreateRequest({
    required this.placementType,
    required this.slotKey,
    required this.sponsorName,
    required this.priceCoin,
    this.creativeAssetUrl,
    this.copyText,
    this.auditNote,
  });

  final String placementType;
  final String slotKey;
  final String sponsorName;
  final double priceCoin;
  final String? creativeAssetUrl;
  final String? copyText;
  final String? auditNote;

  JsonMap toJson() => <String, Object?>{
        'placement_type': placementType,
        'slot_key': slotKey,
        'sponsor_name': sponsorName,
        'price_coin': priceCoin,
        if (creativeAssetUrl != null) 'creative_asset_url': creativeAssetUrl,
        if (copyText != null) 'copy_text': copyText,
        if (auditNote != null) 'audit_note': auditNote,
      };
}

class CreatorStadiumControlUpdateRequest {
  const CreatorStadiumControlUpdateRequest({
    required this.maxMatchdayTicketPriceCoin,
    required this.maxSeasonPassPriceCoin,
    required this.maxVipTicketPriceCoin,
    required this.maxStadiumLevel,
    required this.vipSeatRatioBps,
    required this.maxInStadiumAdSlots,
    required this.maxSponsorBannerSlots,
    required this.adPlacementEnabled,
    required this.ticketSalesEnabled,
    required this.maxPlacementPriceCoin,
  });

  final double maxMatchdayTicketPriceCoin;
  final double maxSeasonPassPriceCoin;
  final double maxVipTicketPriceCoin;
  final int maxStadiumLevel;
  final int vipSeatRatioBps;
  final int maxInStadiumAdSlots;
  final int maxSponsorBannerSlots;
  final bool adPlacementEnabled;
  final bool ticketSalesEnabled;
  final double maxPlacementPriceCoin;

  JsonMap toJson() => <String, Object?>{
        'max_matchday_ticket_price_coin': maxMatchdayTicketPriceCoin,
        'max_season_pass_price_coin': maxSeasonPassPriceCoin,
        'max_vip_ticket_price_coin': maxVipTicketPriceCoin,
        'max_stadium_level': maxStadiumLevel,
        'vip_seat_ratio_bps': vipSeatRatioBps,
        'max_in_stadium_ad_slots': maxInStadiumAdSlots,
        'max_sponsor_banner_slots': maxSponsorBannerSlots,
        'ad_placement_enabled': adPlacementEnabled,
        'ticket_sales_enabled': ticketSalesEnabled,
        'max_placement_price_coin': maxPlacementPriceCoin,
      };
}

class CreatorStadiumLevelUpdateRequest {
  const CreatorStadiumLevelUpdateRequest({
    required this.level,
  });

  final int level;

  JsonMap toJson() => <String, Object?>{'level': level};
}

class CreatorMatchGiftRequest {
  const CreatorMatchGiftRequest({
    required this.clubId,
    required this.amountCoin,
    required this.giftLabel,
    this.note,
  });

  final String clubId;
  final double amountCoin;
  final String giftLabel;
  final String? note;

  JsonMap toJson() => <String, Object?>{
        'club_id': clubId,
        'amount_coin': amountCoin,
        'gift_label': giftLabel,
        if (note != null) 'note': note,
      };
}

class CreatorBroadcastMode {
  const CreatorBroadcastMode._(this.raw);

  final JsonMap raw;

  factory CreatorBroadcastMode.fromJson(Object? value) {
    return CreatorBroadcastMode._(
      jsonMap(value, label: 'creator broadcast mode'),
    );
  }

  String get modeKey => stringValue(raw['mode_key']);
  String get name => stringValue(raw['name']);
  String? get description => stringOrNullValue(raw['description']);
  int get minDurationMinutes => intValue(raw['min_duration_minutes']);
  int get maxDurationMinutes => intValue(raw['max_duration_minutes']);
  double get minPriceCoin => numberValue(raw['min_price_coin']);
  double get maxPriceCoin => numberValue(raw['max_price_coin']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorMatchAccess {
  const CreatorMatchAccess._(this.raw);

  final JsonMap raw;

  factory CreatorMatchAccess.fromJson(Object? value) {
    return CreatorMatchAccess._(
      jsonMap(value, label: 'creator match access'),
    );
  }

  String get matchId => stringValue(raw['match_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get seasonId => stringValue(raw['season_id']);
  String get homeClubId => stringValue(raw['home_club_id']);
  String get awayClubId => stringValue(raw['away_club_id']);
  String get modeKey => stringValue(raw['mode_key']);
  String get modeName => stringValue(raw['mode_name']);
  int get durationMinutes => intValue(raw['duration_minutes']);
  double get priceCoin => numberValue(raw['price_coin']);
  bool get hasAccess => boolValue(raw['has_access']);
  String? get accessSource => stringOrNullValue(raw['access_source']);
  String? get passClubId => stringOrNullValue(raw['pass_club_id']);
  String? get stadiumTicketType =>
      stringOrNullValue(raw['stadium_ticket_type']);
  bool get includesPremiumSeating => boolValue(raw['includes_premium_seating']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorBroadcastPurchase {
  const CreatorBroadcastPurchase._(this.raw);

  final JsonMap raw;

  factory CreatorBroadcastPurchase.fromJson(Object? value) {
    return CreatorBroadcastPurchase._(
      jsonMap(value, label: 'creator broadcast purchase'),
    );
  }

  String get id => stringValue(raw['id']);
  String get seasonId => stringValue(raw['season_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get matchId => stringValue(raw['match_id']);
  String get modeKey => stringValue(raw['mode_key']);
  int get durationMinutes => intValue(raw['duration_minutes']);
  double get priceCoin => numberValue(raw['price_coin']);
  double get platformShareCoin => numberValue(raw['platform_share_coin']);
  double get homeCreatorShareCoin =>
      numberValue(raw['home_creator_share_coin']);
  double get awayCreatorShareCoin =>
      numberValue(raw['away_creator_share_coin']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorSeasonPass {
  const CreatorSeasonPass._(this.raw);

  final JsonMap raw;

  factory CreatorSeasonPass.fromJson(Object? value) {
    return CreatorSeasonPass._(
      jsonMap(value, label: 'creator season pass'),
    );
  }

  String get id => stringValue(raw['id']);
  String get seasonId => stringValue(raw['season_id']);
  String get clubId => stringValue(raw['club_id']);
  String get creatorUserId => stringValue(raw['creator_user_id']);
  String get accessScope => stringValue(raw['access_scope']);
  double get priceCoin => numberValue(raw['price_coin']);
  double get creatorShareCoin => numberValue(raw['creator_share_coin']);
  double get platformShareCoin => numberValue(raw['platform_share_coin']);
  bool get includesFullSeason => boolValue(raw['includes_full_season']);
  bool get includesHomeAway => boolValue(raw['includes_home_away']);
  bool get includesLiveHighlights => boolValue(raw['includes_live_highlights']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorStadiumControl {
  const CreatorStadiumControl._(this.raw);

  final JsonMap raw;

  factory CreatorStadiumControl.fromJson(Object? value) {
    return CreatorStadiumControl._(
      jsonMap(value, label: 'creator stadium control'),
    );
  }

  String get id => stringValue(raw['id']);
  String get controlKey => stringValue(raw['control_key']);
  double get maxMatchdayTicketPriceCoin =>
      numberValue(raw['max_matchday_ticket_price_coin']);
  double get maxSeasonPassPriceCoin =>
      numberValue(raw['max_season_pass_price_coin']);
  double get maxVipTicketPriceCoin =>
      numberValue(raw['max_vip_ticket_price_coin']);
  int get maxStadiumLevel => intValue(raw['max_stadium_level']);
  int get vipSeatRatioBps => intValue(raw['vip_seat_ratio_bps']);
  int get maxInStadiumAdSlots => intValue(raw['max_in_stadium_ad_slots']);
  int get maxSponsorBannerSlots => intValue(raw['max_sponsor_banner_slots']);
  bool get adPlacementEnabled => boolValue(raw['ad_placement_enabled']);
  bool get ticketSalesEnabled => boolValue(raw['ticket_sales_enabled']);
  double get maxPlacementPriceCoin =>
      numberValue(raw['max_placement_price_coin']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorStadiumProfile {
  const CreatorStadiumProfile._(this.raw);

  final JsonMap raw;

  factory CreatorStadiumProfile.fromJson(Object? value) {
    return CreatorStadiumProfile._(
      jsonMap(value, label: 'creator stadium profile'),
    );
  }

  String get id => stringValue(raw['id']);
  String get clubId => stringValue(raw['club_id']);
  String get creatorUserId => stringValue(raw['creator_user_id']);
  String? get clubStadiumId => stringOrNullValue(raw['club_stadium_id']);
  int get level => intValue(raw['level']);
  int get capacity => intValue(raw['capacity']);
  int get premiumSeatCapacity => intValue(raw['premium_seat_capacity']);
  int get visualUpgradeLevel => intValue(raw['visual_upgrade_level']);
  String? get customChantText => stringOrNullValue(raw['custom_chant_text']);
  JsonMap get customVisuals =>
      jsonMap(raw['custom_visuals_json'], fallback: const <String, Object?>{});
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorStadiumMonetization {
  const CreatorStadiumMonetization._(this.raw);

  final JsonMap raw;

  factory CreatorStadiumMonetization.fromJson(Object? value) {
    return CreatorStadiumMonetization._(
      jsonMap(value, label: 'creator stadium monetization'),
    );
  }

  String get seasonId => stringValue(raw['season_id']);
  String get clubId => stringValue(raw['club_id']);
  CreatorStadiumControl get control =>
      CreatorStadiumControl.fromJson(raw['control']);
  CreatorStadiumProfile get stadium =>
      CreatorStadiumProfile.fromJson(raw['stadium']);
  JsonMap? get pricing => jsonMapOrNull(raw['pricing']);
}

class CreatorStadiumPlacement {
  const CreatorStadiumPlacement._(this.raw);

  final JsonMap raw;

  factory CreatorStadiumPlacement.fromJson(Object? value) {
    return CreatorStadiumPlacement._(
      jsonMap(value, label: 'creator stadium placement'),
    );
  }

  String get id => stringValue(raw['id']);
  String get seasonId => stringValue(raw['season_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get matchId => stringValue(raw['match_id']);
  String get clubId => stringValue(raw['club_id']);
  String get creatorUserId => stringValue(raw['creator_user_id']);
  String get placementType => stringValue(raw['placement_type']);
  String get slotKey => stringValue(raw['slot_key']);
  String get sponsorName => stringValue(raw['sponsor_name']);
  String? get creativeAssetUrl => stringOrNullValue(raw['creative_asset_url']);
  String? get copyText => stringOrNullValue(raw['copy_text']);
  double get priceCoin => numberValue(raw['price_coin']);
  double get creatorShareCoin => numberValue(raw['creator_share_coin']);
  double get platformShareCoin => numberValue(raw['platform_share_coin']);
  String get status => stringValue(raw['status']);
  String? get auditNote => stringOrNullValue(raw['audit_note']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorStadiumTicketPurchase {
  const CreatorStadiumTicketPurchase._(this.raw);

  final JsonMap raw;

  factory CreatorStadiumTicketPurchase.fromJson(Object? value) {
    return CreatorStadiumTicketPurchase._(
      jsonMap(value, label: 'creator stadium ticket purchase'),
    );
  }

  String get id => stringValue(raw['id']);
  String get seasonId => stringValue(raw['season_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get matchId => stringValue(raw['match_id']);
  String get clubId => stringValue(raw['club_id']);
  String get ticketType => stringValue(raw['ticket_type']);
  String get seatTier => stringValue(raw['seat_tier']);
  double get priceCoin => numberValue(raw['price_coin']);
  double get creatorShareCoin => numberValue(raw['creator_share_coin']);
  double get platformShareCoin => numberValue(raw['platform_share_coin']);
  bool get includesLiveVideoAccess =>
      boolValue(raw['includes_live_video_access']);
  bool get includesPremiumSeating => boolValue(raw['includes_premium_seating']);
  bool get includesStadiumVisualUpgrades =>
      boolValue(raw['includes_stadium_visual_upgrades']);
  bool get includesCustomChants => boolValue(raw['includes_custom_chants']);
  bool get includesCustomVisuals => boolValue(raw['includes_custom_visuals']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorMatchStadiumOffer {
  const CreatorMatchStadiumOffer._(this.raw);

  final JsonMap raw;

  factory CreatorMatchStadiumOffer.fromJson(Object? value) {
    return CreatorMatchStadiumOffer._(
      jsonMap(value, label: 'creator match stadium offer'),
    );
  }

  String get matchId => stringValue(raw['match_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get seasonId => stringValue(raw['season_id']);
  String get clubId => stringValue(raw['club_id']);
  CreatorStadiumProfile get stadium =>
      CreatorStadiumProfile.fromJson(raw['stadium']);
  JsonMap get pricing =>
      jsonMap(raw['pricing'], fallback: const <String, Object?>{});
  CreatorStadiumControl get control =>
      CreatorStadiumControl.fromJson(raw['control']);
  int get remainingCapacity => intValue(raw['remaining_capacity']);
  int get remainingVipCapacity => intValue(raw['remaining_vip_capacity']);
  List<CreatorStadiumPlacement> get placements => parseList(
        raw['placements'],
        CreatorStadiumPlacement.fromJson,
        label: 'creator stadium placements',
      );
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorMatchGift {
  const CreatorMatchGift._(this.raw);

  final JsonMap raw;

  factory CreatorMatchGift.fromJson(Object? value) {
    return CreatorMatchGift._(
      jsonMap(value, label: 'creator match gift'),
    );
  }

  String get id => stringValue(raw['id']);
  String get seasonId => stringValue(raw['season_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get matchId => stringValue(raw['match_id']);
  String get senderUserId => stringValue(raw['sender_user_id']);
  String get recipientCreatorUserId =>
      stringValue(raw['recipient_creator_user_id']);
  String get clubId => stringValue(raw['club_id']);
  String get giftLabel => stringValue(raw['gift_label']);
  double get grossAmountCoin => numberValue(raw['gross_amount_coin']);
  double get creatorShareCoin => numberValue(raw['creator_share_coin']);
  double get platformShareCoin => numberValue(raw['platform_share_coin']);
  String? get note => stringOrNullValue(raw['note']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorRevenueSettlement {
  const CreatorRevenueSettlement._(this.raw);

  final JsonMap raw;

  factory CreatorRevenueSettlement.fromJson(Object? value) {
    return CreatorRevenueSettlement._(
      jsonMap(value, label: 'creator revenue settlement'),
    );
  }

  String get id => stringValue(raw['id']);
  String get seasonId => stringValue(raw['season_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get matchId => stringValue(raw['match_id']);
  double get totalRevenueCoin => numberValue(raw['total_revenue_coin']);
  double get totalCreatorShareCoin =>
      numberValue(raw['total_creator_share_coin']);
  double get totalPlatformShareCoin =>
      numberValue(raw['total_platform_share_coin']);
  double get shareholderTotalDistributionCoin =>
      numberValue(raw['shareholder_total_distribution_coin']);
  String get reviewStatus => stringValue(raw['review_status']);
  List<String> get reviewReasonCodes =>
      stringListValue(raw['review_reason_codes_json']);
  JsonMap get policySnapshot =>
      jsonMap(raw['policy_snapshot_json'], fallback: const <String, Object?>{});
  DateTime? get reviewedAt => dateTimeValue(raw['reviewed_at']);
  String? get reviewNote => stringOrNullValue(raw['review_note']);
  DateTime? get settledAt => dateTimeValue(raw['settled_at']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class CreatorAnalyticsDashboard {
  const CreatorAnalyticsDashboard._(this.raw);

  final JsonMap raw;

  factory CreatorAnalyticsDashboard.fromJson(Object? value) {
    return CreatorAnalyticsDashboard._(
      jsonMap(value, label: 'creator analytics dashboard'),
    );
  }

  String get matchId => stringValue(raw['match_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String get seasonId => stringValue(raw['season_id']);
  String? get clubId => stringOrNullValue(raw['club_id']);
  int get totalViewers => intValue(raw['total_viewers']);
  int get videoViewers => intValue(raw['video_viewers']);
  double get giftTotalsCoin => numberValue(raw['gift_totals_coin']);
  List<JsonMap> get topGifters =>
      jsonMapList(raw['top_gifters'], label: 'creator top gifters');
  double get fanEngagementPct => numberValue(raw['fan_engagement_pct']);
  int get engagedFans => intValue(raw['engaged_fans']);
  int get totalWatchSeconds => intValue(raw['total_watch_seconds']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}
