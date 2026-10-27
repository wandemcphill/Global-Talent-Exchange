import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/story_feed_api.dart';
import '../../../models/story_feed_models.dart';
import '../../../shared/providers/auth_provider.dart';

/// Maximum number of ticker items retained in memory on the client (Document I3).
const int kGtexMaxTickerItems = 50;

/// Broadcast event types eligible for Decision O-09 verified price & owner display.
const Set<String> kGtexVerifiedBroadcastEventTypes = <String>{
  'private_jet_purchase',
  'facility_upgrade',
  'player_gift',
};

const Set<String> _kExcludedTickerStatuses = <String>{
  'reversed',
  'retracted',
};

const Set<String> _kConfidentialOwnerKeys = <String>{
  'owner_user_id',
  'ownerUserId',
  'club_cash',
  'clubCash',
  'cash_balance',
  'cashBalance',
  'transfer_budget',
  'transferBudget',
  'wage_budget',
  'wageBudget',
};

/// Injectable [StoryFeedApi] provider for the global / home story-feed ticker.
final Provider<StoryFeedApi> storyFeedTickerApiProvider =
    Provider<StoryFeedApi>((Ref ref) {
      return StoryFeedApi.standard(
        baseUrl: ref.watch(apiBaseUrlProvider),
        accessToken: ref.watch(accessTokenProvider),
        mode: ref.watch(criticalBackendModeProvider),
      );
    });

/// Featured / recent story-feed headlines for the Home and Global transfer ticker.
///
/// Same durable desk as News Agency (`GET /api/story-feed`).
/// Enforces Document I3 & Decision O-09:
/// - Excludes `reversed` and `retracted` ticker events.
/// - Deduplicates ticker items by `id` and caps retained items at [kGtexMaxTickerItems] (50).
/// - Surfaces formatted `verified_price_gtex` and `owner_display_name` on
///   `private_jet_purchase`, `facility_upgrade`, and `player_gift` broadcasts
///   while stripping any raw `owner_user_id`.
final FutureProvider<List<StoryFeedItem>> storyFeedTickerProvider =
    FutureProvider<List<StoryFeedItem>>((Ref ref) async {
      final StoryFeedApi api = ref.watch(storyFeedTickerApiProvider);
      try {
        final List<StoryFeedItem> items = await api.listFeed(
          limit: kGtexMaxTickerItems,
        );
        return normalizeStoryFeedTickerItems(items);
      } catch (_) {
        return const <StoryFeedItem>[];
      }
    });

/// Deduplicates ticker [items] by `id`, filters out `reversed` / `retracted`
/// events, applies Decision O-09 formatting + `owner_user_id` scrubbing, and
/// caps the retained list at [maxItems] (default [kGtexMaxTickerItems] = 50).
List<StoryFeedItem> normalizeStoryFeedTickerItems(
  Iterable<StoryFeedItem> items, {
  int maxItems = kGtexMaxTickerItems,
}) {
  final int effectiveCap = maxItems.clamp(0, kGtexMaxTickerItems);
  if (effectiveCap == 0) {
    return const <StoryFeedItem>[];
  }

  final List<StoryFeedItem> rawList = items.toList(growable: false);

  // If any update for a given id marks it reversed/retracted, exclude that id.
  final Set<String> excludedIds = <String>{};
  for (final StoryFeedItem item in rawList) {
    final String id = item.id.trim();
    if (id.isEmpty || isTickerItemReversedOrRetracted(item)) {
      if (id.isNotEmpty) {
        excludedIds.add(id);
      }
    }
  }

  final Map<String, StoryFeedItem> dedupedById = <String, StoryFeedItem>{};
  for (final StoryFeedItem item in rawList) {
    final String id = item.id.trim();
    if (id.isEmpty ||
        excludedIds.contains(id) ||
        isTickerItemReversedOrRetracted(item)) {
      continue;
    }
    final StoryFeedItem sanitized = sanitizeAndFormatTickerItem(item);
    final StoryFeedItem? existing = dedupedById[id];
    if (existing == null) {
      dedupedById[id] = sanitized;
    } else if (sanitized.createdAt.isAfter(existing.createdAt) ||
        (sanitized.featured && !existing.featured)) {
      dedupedById[id] = sanitized;
    }
  }

  final List<StoryFeedItem> sorted = dedupedById.values.toList(growable: true)
    ..sort((StoryFeedItem a, StoryFeedItem b) {
      final int featuredCmp = (b.featured ? 1 : 0) - (a.featured ? 1 : 0);
      if (featuredCmp != 0) {
        return featuredCmp;
      }
      return b.createdAt.compareTo(a.createdAt);
    });

  if (sorted.length > effectiveCap) {
    return List<StoryFeedItem>.unmodifiable(sorted.take(effectiveCap));
  }
  return List<StoryFeedItem>.unmodifiable(sorted);
}

/// Returns `true` when [item] has a reversed or retracted status in either
/// [StoryFeedItem.moderationStatus] or its `metadata` map.
bool isTickerItemReversedOrRetracted(StoryFeedItem item) {
  final String modStatus = _normalizeToken(item.moderationStatus);
  if (_kExcludedTickerStatuses.contains(modStatus)) {
    return true;
  }
  final String? metaStatus = _metadataString(item.metadata, const <String>[
    'status',
    'moderation_status',
    'moderationStatus',
    'broadcast_status',
    'broadcastStatus',
  ]);
  if (metaStatus != null &&
      _kExcludedTickerStatuses.contains(_normalizeToken(metaStatus))) {
    return true;
  }
  return false;
}

/// Applies Decision O-09 privacy and broadcast formatting rules to a single
/// [StoryFeedItem]:
/// - Strips `owner_user_id` / `ownerUserId` and confidential budget keys from
///   `metadata`, and scrubs any raw `owner_user_id` value from `title`/`body`/`subjectId`.
/// - Surfaces `owner_display_name` and cleanly formatted `verified_price_gtex`
///   when present on `private_jet_purchase`, `facility_upgrade`, or `player_gift`
///   broadcasts (or whenever `verified_price_gtex` is provided).
StoryFeedItem sanitizeAndFormatTickerItem(StoryFeedItem item) {
  final Map<String, Object?> rawMeta = item.metadata;
  final String? rawOwnerUserId = _metadataString(rawMeta, const <String>[
    'owner_user_id',
    'ownerUserId',
  ]);
  final String? ownerDisplayName = _metadataString(rawMeta, const <String>[
    'owner_display_name',
    'ownerDisplayName',
  ]);
  final String eventType = _resolveBroadcastEventType(item);
  final bool isEligibleBroadcast =
      kGtexVerifiedBroadcastEventTypes.contains(eventType);

  final Object? rawVerifiedPrice =
      rawMeta['verified_price_gtex'] ?? rawMeta['verifiedPriceGtex'];
  final String currency =
      _metadataString(rawMeta, const <String>['currency']) ?? 'GTX';
  final String? formattedPrice = formatVerifiedPriceGtex(
    rawVerifiedPrice,
    currency: currency,
  );

  final Map<String, Object?> cleanMeta = <String, Object?>{};
  for (final MapEntry<String, Object?> entry in rawMeta.entries) {
    if (_kConfidentialOwnerKeys.contains(entry.key)) {
      continue;
    }
    if (rawOwnerUserId != null &&
        rawOwnerUserId.isNotEmpty &&
        entry.value is String &&
        (entry.value as String).contains(rawOwnerUserId)) {
      cleanMeta[entry.key] = (entry.value as String).replaceAll(
        rawOwnerUserId,
        ownerDisplayName ?? 'Club Ownership',
      );
      continue;
    }
    cleanMeta[entry.key] = entry.value;
  }

  if (ownerDisplayName != null) {
    cleanMeta['owner_display_name'] = ownerDisplayName;
  }
  if (formattedPrice != null) {
    cleanMeta['verified_price_gtex'] = formattedPrice;
    cleanMeta['formatted_price_gtex'] = formattedPrice;
  }

  String cleanTitle = _scrubOwnerUserId(
    item.title,
    rawOwnerUserId: rawOwnerUserId,
    ownerDisplayName: ownerDisplayName,
  );
  String cleanBody = _scrubOwnerUserId(
    item.body,
    rawOwnerUserId: rawOwnerUserId,
    ownerDisplayName: ownerDisplayName,
  );

  if (isEligibleBroadcast || formattedPrice != null || ownerDisplayName != null) {
    if (ownerDisplayName != null &&
        !cleanTitle.toLowerCase().contains(ownerDisplayName.toLowerCase())) {
      cleanTitle = '$cleanTitle · $ownerDisplayName';
    }
    if (formattedPrice != null &&
        (isEligibleBroadcast || rawVerifiedPrice != null) &&
        !cleanTitle.toLowerCase().contains(formattedPrice.toLowerCase())) {
      cleanTitle = '$cleanTitle ($formattedPrice)';
    }
    if (ownerDisplayName != null &&
        cleanBody.isNotEmpty &&
        !cleanBody.toLowerCase().contains(ownerDisplayName.toLowerCase())) {
      cleanBody = '$cleanBody · Owner: $ownerDisplayName';
    }
    if (formattedPrice != null &&
        cleanBody.isNotEmpty &&
        !cleanBody.toLowerCase().contains(formattedPrice.toLowerCase())) {
      cleanBody = '$cleanBody · Verified price: $formattedPrice';
    }
  }

  final String? cleanSubjectId =
      (rawOwnerUserId != null && item.subjectId == rawOwnerUserId)
          ? null
          : item.subjectId;

  return StoryFeedItem(
    id: item.id.trim(),
    storyType: item.storyType,
    title: cleanTitle,
    body: cleanBody,
    audience: item.audience,
    subjectType: item.subjectType,
    subjectId: cleanSubjectId,
    countryCode: item.countryCode,
    featured: item.featured,
    createdAt: item.createdAt,
    metadata: Map<String, Object?>.unmodifiable(cleanMeta),
    moderationStatus: item.moderationStatus,
    scheduledFor: item.scheduledFor,
  );
}

/// Formats a raw `verified_price_gtex` value into a clean display string
/// (e.g., `4800.0000` -> `'4,800 GTX'`, `1250.5` -> `'1,250.50 GTX'`).
/// Returns `null` when [rawPrice] is null, non-numeric, or `<= 0`.
String? formatVerifiedPriceGtex(
  Object? rawPrice, {
  String currency = 'GTX',
}) {
  if (rawPrice == null) {
    return null;
  }
  double? numericValue;
  if (rawPrice is num) {
    numericValue = rawPrice.toDouble();
  } else if (rawPrice is String) {
    final String cleaned = rawPrice
        .replaceAll(',', '')
        .replaceAll(RegExp(r'[A-Za-z\s]+'), '')
        .trim();
    if (cleaned.isEmpty) {
      return null;
    }
    numericValue = double.tryParse(cleaned);
  }
  if (numericValue == null || !numericValue.isFinite || numericValue <= 0) {
    return null;
  }

  final String resolvedUnit =
      currency.trim().toUpperCase() == 'GTEX' || currency.trim().isEmpty
          ? 'GTX'
          : currency.trim().toUpperCase();
  final bool isWhole = numericValue == numericValue.roundToDouble();
  final String fixed =
      isWhole ? numericValue.round().toString() : numericValue.toStringAsFixed(2);
  final List<String> parts = fixed.split('.');
  final String integerPart = parts.first.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (Match _) => ',',
  );
  final String formattedNumber =
      parts.length > 1 ? '$integerPart.${parts[1]}' : integerPart;
  return '$formattedNumber $resolvedUnit';
}

String _resolveBroadcastEventType(StoryFeedItem item) {
  final String? fromMeta = _metadataString(item.metadata, const <String>[
    'event_type',
    'eventType',
  ]);
  return _normalizeToken(fromMeta ?? item.storyType);
}

String _scrubOwnerUserId(
  String input, {
  required String? rawOwnerUserId,
  required String? ownerDisplayName,
}) {
  if (rawOwnerUserId == null || rawOwnerUserId.isEmpty) {
    return input;
  }
  return input.replaceAll(
    rawOwnerUserId,
    ownerDisplayName ?? 'Club Ownership',
  );
}

String _normalizeToken(String? raw) {
  return (raw ?? '')
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[\s\-]+'), '_');
}

String? _metadataString(Map<String, Object?> metadata, List<String> keys) {
  for (final String key in keys) {
    final Object? value = metadata[key];
    if (value is String && value.trim().isNotEmpty) {
      return value.trim();
    }
  }
  return null;
}
