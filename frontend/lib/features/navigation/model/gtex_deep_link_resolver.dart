import 'package:flutter/foundation.dart';

import 'gtex_route_alias_table.dart';

enum GtexDeepLinkSource {
  inboxItem,
  notification,
  tickerBroadcast,
  newsroomArticle,
  directPath,
}

@immutable
class GtexResolvedDeepLink {
  const GtexResolvedDeepLink({
    required this.source,
    required this.canonicalRoute,
    required this.usedFallback,
  });

  final GtexDeepLinkSource source;
  final String canonicalRoute;
  final bool usedFallback;
}

/// Deterministic server-payload to canonical-route resolver (Master Plan
/// Document E5, Decision O-11, Phase A3).
///
/// Guarantees that unknown or partially populated payloads resolve to a valid,
/// safe destination (`/app/inbox/:itemId`, `/app/inbox`, or `/app/home`) and
/// never navigate to an error screen.
class GtexDeepLinkResolver {
  const GtexDeepLinkResolver._();

  /// Resolves an Owner Console inbox item (`GET /api/v2/owner/inbox` or
  /// `OwnerInboxItemRecord`) into its canonical route.
  static GtexResolvedDeepLink resolveInboxItem(
    Map<String, Object?> payload, {
    String? activeClubId,
  }) {
    final String itemId = _stringOf(
      payload,
      const <String>['id', 'item_id', 'inbox_item_id', 'decision_id'],
    );
    final String clubId = _resolveClubId(payload, activeClubId);
    final Map<String, Object?> meta = _nestedMap(payload, const <String>[
      'metadata_json',
      'metadata',
      'payload',
      'context',
    ]);

    final String explicitRoute = _stringOf(
      meta,
      const <String>['deep_link_route', 'deepLinkRoute', 'route'],
      fallback: _stringOf(
        payload,
        const <String>['deep_link_route', 'deepLinkRoute', 'route'],
      ),
    );
    if (explicitRoute.isNotEmpty) {
      final GtexRouteAliasResolution resolved = GtexRouteAliasTable.resolve(
        explicitRoute,
        activeClubId: clubId,
      );
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.inboxItem,
        canonicalRoute: resolved.canonicalPath,
        usedFallback: false,
      );
    }

    final String kind = _stringOf(
      payload,
      const <String>['kind', 'category', 'action_type', 'type'],
      fallback: _stringOf(meta, const <String>['kind', 'category', 'type']),
    ).toLowerCase();
    final String respondBy = _stringOf(
      payload,
      const <String>['respond_by', 'respondBy', 'deadline_at'],
      fallback: _stringOf(meta, const <String>['respond_by', 'respondBy']),
    );

    // Decision-bearing or approval items always open the decision detail in Inbox.
    if (kind.contains('approval') ||
        kind.contains('decision') ||
        kind.contains('policy') ||
        respondBy.isNotEmpty) {
      if (itemId.isNotEmpty) {
        return GtexResolvedDeepLink(
          source: GtexDeepLinkSource.inboxItem,
          canonicalRoute: GtexCanonicalRoutes.inboxItem(itemId),
          usedFallback: false,
        );
      }
      return const GtexResolvedDeepLink(
        source: GtexDeepLinkSource.inboxItem,
        canonicalRoute: GtexCanonicalRoutes.inbox,
        usedFallback: true,
      );
    }

    if (kind.contains('scout') || kind.contains('recruitment')) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.inboxItem,
        canonicalRoute: GtexCanonicalRoutes.clubRecruitment(clubId),
        usedFallback: false,
      );
    }

    final String offerId = _stringOf(
      meta,
      const <String>['offer_id', 'transfer_offer_id', 'listing_id'],
      fallback: _stringOf(
        payload,
        const <String>['offer_id', 'transfer_offer_id', 'listing_id'],
      ),
    );
    if (kind.contains('transfer') ||
        kind.contains('offer') ||
        offerId.isNotEmpty) {
      final String target =
          offerId.isNotEmpty
              ? GtexCanonicalRoutes.clubTransferOffer(clubId, offerId)
              : GtexCanonicalRoutes.clubTransfers(clubId);
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.inboxItem,
        canonicalRoute: target,
        usedFallback: false,
      );
    }

    if (kind.contains('facility') ||
        kind.contains('showroom') ||
        kind.contains('boardroom') ||
        kind.contains('luxury')) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.inboxItem,
        canonicalRoute: GtexCanonicalRoutes.clubBoardroom(clubId),
        usedFallback: false,
      );
    }

    if (kind.contains('finance') ||
        kind.contains('budget') ||
        kind.contains('ledger')) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.inboxItem,
        canonicalRoute: GtexCanonicalRoutes.clubFinance(clubId),
        usedFallback: false,
      );
    }

    // Document E5 rule: unknown inbox targets -> Inbox item detail (never error screen).
    if (itemId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.inboxItem,
        canonicalRoute: GtexCanonicalRoutes.inboxItem(itemId),
        usedFallback: true,
      );
    }
    return const GtexResolvedDeepLink(
      source: GtexDeepLinkSource.inboxItem,
      canonicalRoute: GtexCanonicalRoutes.inbox,
      usedFallback: true,
    );
  }

  /// Resolves a platform `NotificationRecord` (`/api/v2/notifications/me` or
  /// `/api/notifications/me`) into its canonical route (`Document E5`, `O-11`).
  static GtexResolvedDeepLink resolveNotification(
    Map<String, Object?> payload, {
    String? activeClubId,
  }) {
    final String clubId = _resolveClubId(payload, activeClubId);
    final Map<String, Object?> meta = _nestedMap(payload, const <String>[
      'metadata_json',
      'metadata',
      'data',
    ]);

    final String explicitRoute = _stringOf(
      meta,
      const <String>[
        'deep_link_route',
        'deepLinkRoute',
        'route',
        'target_route',
      ],
      fallback: _stringOf(
        payload,
        const <String>[
          'deep_link_route',
          'deepLinkRoute',
          'route',
          'target_route',
        ],
      ),
    );
    if (explicitRoute.isNotEmpty) {
      final GtexRouteAliasResolution resolved = GtexRouteAliasTable.resolve(
        explicitRoute,
        activeClubId: clubId,
      );
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: resolved.canonicalPath,
        usedFallback: false,
      );
    }

    final String matchKey = _stringOf(
      meta,
      const <String>['fixture_id', 'match_id', 'match_key', 'matchKey'],
      fallback: _stringOf(
        payload,
        const <String>['fixture_id', 'match_id', 'match_key', 'matchKey'],
      ),
    );
    if (matchKey.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: GtexCanonicalRoutes.matchdayMatch(matchKey),
        usedFallback: false,
      );
    }

    final String offerId = _stringOf(
      meta,
      const <String>['offer_id', 'transfer_offer_id'],
      fallback: _stringOf(payload, const <String>['offer_id']),
    );
    if (offerId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: GtexCanonicalRoutes.clubTransferOffer(clubId, offerId),
        usedFallback: false,
      );
    }

    final String inboxItemId = _stringOf(
      meta,
      const <String>['inbox_item_id', 'decision_id'],
      fallback: _stringOf(payload, const <String>['inbox_item_id']),
    );
    if (inboxItemId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: GtexCanonicalRoutes.inboxItem(inboxItemId),
        usedFallback: false,
      );
    }

    final String articleId = _stringOf(
      meta,
      const <String>['article_id', 'news_item_id', 'story_id'],
      fallback: _stringOf(payload, const <String>['article_id', 'story_id']),
    );
    if (articleId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: GtexCanonicalRoutes.newsroomArticle(articleId),
        usedFallback: false,
      );
    }

    final String playerId = _stringOf(
      meta,
      const <String>['player_id', 'regen_id'],
      fallback: _stringOf(payload, const <String>['player_id']),
    );
    if (playerId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: GtexCanonicalRoutes.playerProfile(playerId),
        usedFallback: false,
      );
    }

    final String competitionId = _stringOf(
      payload,
      const <String>['competition_id', 'competitionId'],
      fallback: _stringOf(
        meta,
        const <String>['competition_id', 'competitionId'],
      ),
    );
    if (competitionId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: GtexCanonicalRoutes.matchdayCompetition(competitionId),
        usedFallback: false,
      );
    }

    final String resourceType = _stringOf(
      payload,
      const <String>['resource_type', 'entity_type'],
      fallback: _stringOf(meta, const <String>['resource_type', 'entity_type']),
    ).toLowerCase();
    final String resourceId = _stringOf(
      payload,
      const <String>['resource_id', 'entity_id'],
      fallback: _stringOf(meta, const <String>['resource_id', 'entity_id']),
    );
    if (resourceType.isNotEmpty && resourceId.isNotEmpty) {
      if (resourceType.contains('match') || resourceType.contains('fixture')) {
        return GtexResolvedDeepLink(
          source: GtexDeepLinkSource.notification,
          canonicalRoute: GtexCanonicalRoutes.matchdayMatch(resourceId),
          usedFallback: false,
        );
      }
      if (resourceType.contains('competition')) {
        return GtexResolvedDeepLink(
          source: GtexDeepLinkSource.notification,
          canonicalRoute: GtexCanonicalRoutes.matchdayCompetition(resourceId),
          usedFallback: false,
        );
      }
      if (resourceType.contains('player')) {
        return GtexResolvedDeepLink(
          source: GtexDeepLinkSource.notification,
          canonicalRoute: GtexCanonicalRoutes.playerProfile(resourceId),
          usedFallback: false,
        );
      }
      if (resourceType.contains('inbox') || resourceType.contains('decision')) {
        return GtexResolvedDeepLink(
          source: GtexDeepLinkSource.notification,
          canonicalRoute: GtexCanonicalRoutes.inboxItem(resourceId),
          usedFallback: false,
        );
      }
    }

    final String fallbackItemId = _stringOf(payload, const <String>['id']);
    if (fallbackItemId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.notification,
        canonicalRoute: GtexCanonicalRoutes.inboxItem(fallbackItemId),
        usedFallback: true,
      );
    }
    return const GtexResolvedDeepLink(
      source: GtexDeepLinkSource.notification,
      canonicalRoute: GtexCanonicalRoutes.inbox,
      usedFallback: true,
    );
  }

  /// Resolves a global broadcast ticker item (`GET /api/v2/owner/ticker`) or
  /// newsroom headline into its canonical route (`Document E5`).
  static GtexResolvedDeepLink resolveTickerEvent(
    Map<String, Object?> payload, {
    String? activeClubId,
  }) {
    final Map<String, Object?> meta = _nestedMap(payload, const <String>[
      'metadata_json',
      'metadata',
      'payload',
    ]);

    final String articleId = _stringOf(
      payload,
      const <String>['article_id', 'news_item_id', 'story_id'],
      fallback: _stringOf(
        meta,
        const <String>['article_id', 'news_item_id', 'story_id'],
      ),
    );
    if (articleId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.tickerBroadcast,
        canonicalRoute: GtexCanonicalRoutes.newsroomArticle(articleId),
        usedFallback: false,
      );
    }

    final String matchKey = _stringOf(
      payload,
      const <String>['match_key', 'fixture_id', 'match_id'],
      fallback: _stringOf(
        meta,
        const <String>['match_key', 'fixture_id', 'match_id'],
      ),
    );
    if (matchKey.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.tickerBroadcast,
        canonicalRoute: GtexCanonicalRoutes.matchdayMatch(matchKey),
        usedFallback: false,
      );
    }

    final String playerId = _stringOf(
      payload,
      const <String>['player_id', 'gifted_player_id'],
      fallback: _stringOf(
        meta,
        const <String>['player_id', 'gifted_player_id'],
      ),
    );
    if (playerId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.tickerBroadcast,
        canonicalRoute: GtexCanonicalRoutes.playerProfile(playerId),
        usedFallback: false,
      );
    }

    final String clubId = _stringOf(
      payload,
      const <String>['club_id', 'subject_club_id'],
      fallback: _stringOf(meta, const <String>['club_id', 'subject_club_id']),
    );
    if (clubId.isNotEmpty) {
      return GtexResolvedDeepLink(
        source: GtexDeepLinkSource.tickerBroadcast,
        canonicalRoute: GtexCanonicalRoutes.worldClub(clubId),
        usedFallback: false,
      );
    }

    return const GtexResolvedDeepLink(
      source: GtexDeepLinkSource.tickerBroadcast,
      canonicalRoute: GtexCanonicalRoutes.newsroom,
      usedFallback: true,
    );
  }

  static String _resolveClubId(
    Map<String, Object?> payload,
    String? activeClubId,
  ) {
    final String fromPayload = _stringOf(payload, const <String>[
      'club_id',
      'clubId',
      'current_club_id',
    ]);
    if (fromPayload.isNotEmpty) {
      return fromPayload;
    }
    if (activeClubId != null && activeClubId.trim().isNotEmpty) {
      return activeClubId.trim();
    }
    return GtexRouteAliasTable.defaultClubPlaceholder;
  }

  static Map<String, Object?> _nestedMap(
    Map<String, Object?> source,
    List<String> keys,
  ) {
    for (final String key in keys) {
      final Object? value = source[key];
      if (value is Map<String, Object?>) {
        return value;
      }
      if (value is Map) {
        return value.map(
          (Object? k, Object? v) => MapEntry<String, Object?>(k.toString(), v),
        );
      }
    }
    return const <String, Object?>{};
  }

  static String _stringOf(
    Map<String, Object?> source,
    List<String> keys, {
    String fallback = '',
  }) {
    for (final String key in keys) {
      final Object? value = source[key];
      if (value != null) {
        final String text = value.toString().trim();
        if (text.isNotEmpty) {
          return text;
        }
      }
    }
    return fallback;
  }
}
