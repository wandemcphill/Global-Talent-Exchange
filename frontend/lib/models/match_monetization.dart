import 'package:gte_frontend/data/gte_models.dart';

enum MatchAdPlacementType {
  sponsoredHighlight,
  preRoll,
  liveBanner,
  rewardedAd,
}

MatchAdPlacementType matchAdPlacementTypeFromString(String? value) {
  switch (value?.trim().toLowerCase()) {
    case 'sponsored_highlight':
      return MatchAdPlacementType.sponsoredHighlight;
    case 'pre_roll':
      return MatchAdPlacementType.preRoll;
    case 'live_banner':
      return MatchAdPlacementType.liveBanner;
    case 'rewarded_ad':
      return MatchAdPlacementType.rewardedAd;
    default:
      return MatchAdPlacementType.preRoll;
  }
}

class MatchAdPlacement {
  const MatchAdPlacement({
    required this.id,
    required this.type,
    required this.placement,
    required this.brand,
    required this.message,
    required this.targetingTags,
    this.eventId,
    this.activeFromSecond,
    this.activeUntilSecond,
    this.rewardCoins,
    this.ctaLabel,
    this.pricingCpmUsd,
    this.estimatedValueUsd,
    this.metadata = const <String, Object?>{},
  });

  final String id;
  final MatchAdPlacementType type;
  final String placement;
  final String brand;
  final String message;
  final String? eventId;
  final int? activeFromSecond;
  final int? activeUntilSecond;
  final int? rewardCoins;
  final String? ctaLabel;
  final double? pricingCpmUsd;
  final double? estimatedValueUsd;
  final List<String> targetingTags;
  final Map<String, Object?> metadata;

  bool isActiveAt(double positionSeconds) {
    final int second = positionSeconds.floor();
    final int start = activeFromSecond ?? 0;
    final int end = activeUntilSecond ?? 1 << 20;
    return second >= start && second <= end;
  }

  factory MatchAdPlacement.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'match ad');
    final List<Object?> rawTags = GteJson.list(
      GteJson.value(json, <String>['targeting_tags', 'targetingTags']) ??
          const <Object?>[],
      label: 'match ad tags',
    );
    final Object? rawMetadata =
        GteJson.value(json, <String>['metadata']) ?? const <String, Object?>{};
    return MatchAdPlacement(
      id: GteJson.string(json, <String>['ad_id', 'adId']),
      type: matchAdPlacementTypeFromString(
        GteJson.stringOrNull(json, <String>['ad_type', 'adType']),
      ),
      placement: GteJson.string(json, <String>[
        'placement',
      ], fallback: 'match_viewer'),
      brand: GteJson.string(json, <String>['brand']),
      message: GteJson.string(json, <String>['message']),
      eventId: GteJson.stringOrNull(json, <String>['event_id', 'eventId']),
      activeFromSecond: GteJson.integerOrNull(json, <String>[
        'active_from_second',
        'activeFromSecond',
      ]),
      activeUntilSecond: GteJson.integerOrNull(json, <String>[
        'active_until_second',
        'activeUntilSecond',
      ]),
      rewardCoins: GteJson.integerOrNull(json, <String>[
        'reward_coins',
        'rewardCoins',
      ]),
      ctaLabel: GteJson.stringOrNull(json, <String>['cta_label', 'ctaLabel']),
      pricingCpmUsd: _doubleOrNull(json, <String>[
        'pricing_cpm_usd',
        'pricingCpmUsd',
      ]),
      estimatedValueUsd: _doubleOrNull(json, <String>[
        'estimated_value_usd',
        'estimatedValueUsd',
      ]),
      targetingTags: rawTags
          .map((Object? item) => item.toString())
          .where((String item) => item.trim().isNotEmpty)
          .toList(growable: false),
      metadata: Map<String, Object?>.from(
        rawMetadata is Map ? rawMetadata : const <String, Object?>{},
      ),
    );
  }
}

class MatchViewerMonetization {
  const MatchViewerMonetization({
    this.adsEnabled = false,
    this.premiumAdFree = false,
    this.placements = const <MatchAdPlacement>[],
    this.metadata = const <String, Object?>{},
  });

  final bool adsEnabled;
  final bool premiumAdFree;
  final List<MatchAdPlacement> placements;
  final Map<String, Object?> metadata;

  bool get hasPlacements => placements.isNotEmpty;

  MatchAdPlacement? firstOfType(MatchAdPlacementType type) {
    for (final MatchAdPlacement placement in placements) {
      if (placement.type == type) {
        return placement;
      }
    }
    return null;
  }

  MatchAdPlacement? firstActiveOfType(
    MatchAdPlacementType type,
    double positionSeconds,
  ) {
    for (final MatchAdPlacement placement in placements) {
      if (placement.type == type && placement.isActiveAt(positionSeconds)) {
        return placement;
      }
    }
    return null;
  }

  MatchAdPlacement? sponsoredPlacementForEvent(String? eventId) {
    if (eventId == null || eventId.trim().isEmpty) {
      return null;
    }
    for (final MatchAdPlacement placement in placements) {
      if (placement.type == MatchAdPlacementType.sponsoredHighlight &&
          placement.eventId == eventId) {
        return placement;
      }
    }
    return null;
  }

  factory MatchViewerMonetization.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value ?? const <String, Object?>{},
      label: 'match monetization',
    );
    final List<Object?> rawPlacements = GteJson.list(
      GteJson.value(json, <String>['placements']) ?? const <Object?>[],
      label: 'match ad placements',
    );
    final Object? rawMetadata =
        GteJson.value(json, <String>['metadata']) ?? const <String, Object?>{};
    return MatchViewerMonetization(
      adsEnabled: GteJson.boolean(json, <String>[
        'ads_enabled',
        'adsEnabled',
      ], fallback: rawPlacements.isNotEmpty),
      premiumAdFree: GteJson.boolean(json, <String>[
        'premium_ad_free',
        'premiumAdFree',
      ], fallback: false),
      placements: rawPlacements
          .map(MatchAdPlacement.fromJson)
          .toList(growable: false),
      metadata: Map<String, Object?>.from(
        rawMetadata is Map ? rawMetadata : const <String, Object?>{},
      ),
    );
  }
}

double? _doubleOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? raw = GteJson.value(json, keys);
  if (raw == null) {
    return null;
  }
  if (raw is num) {
    return raw.toDouble();
  }
  return double.tryParse(raw.toString());
}
