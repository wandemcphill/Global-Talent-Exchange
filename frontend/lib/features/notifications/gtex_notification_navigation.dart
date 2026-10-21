import '../../data/gte_models.dart';
import '../global_search_redesign/global_search_models.dart';

/// Resolves only destinations the notification payload can authoritatively
/// describe. It deliberately does not infer a destination from notification
/// copy, topics, or resource labels: those values are not a routing contract.
class GtexNotificationNavigation {
  const GtexNotificationNavigation._();

  static GtexNotificationNavigationTarget? resolve(
    GteNotification notification, {
    required bool isAdmin,
  }) {
    final String? explicitRoute =
        _firstMetadataString(notification.metadata, const <String>[
          'deep_link_route',
          'deepLinkRoute',
          'deep_link',
          'deepLink',
          'action_route',
          'actionRoute',
          'route',
        ]);
    if (explicitRoute != null) {
      return _fromExplicitRoute(explicitRoute, isAdmin: isAdmin);
    }

    // `fixture_id` from legacy identifier or metadata
    final String fixtureId = notification.fixtureId?.trim().isNotEmpty == true
        ? notification.fixtureId!.trim()
        : (_firstMetadataString(notification.metadata, const <String>[
              'fixture_id',
              'fixtureId',
              'match_id',
              'matchId',
              'match_key',
              'matchKey',
            ])?.trim() ??
            '');
    if (fixtureId.isNotEmpty) {
      return GtexNotificationNavigationTarget(
        route: '/matches/viewer/${Uri.encodeComponent(fixtureId)}',
        source: GtexNotificationNavigationSource.fixtureId,
      );
    }

    // `competition_id` payload resolution beyond fixture_id
    final String competitionId =
        notification.competitionId?.trim().isNotEmpty == true
            ? notification.competitionId!.trim()
            : (_firstMetadataString(notification.metadata, const <String>[
                  'competition_id',
                  'competitionId',
                ])?.trim() ??
                '');
    if (competitionId.isNotEmpty) {
      return _fromExplicitRoute(
        '/app/play?competition=${Uri.encodeComponent(competitionId)}',
        isAdmin: isAdmin,
        source: GtexNotificationNavigationSource.competitionId,
      );
    }

    // `resource_id` payload resolution beyond fixture_id
    final String resourceId = notification.resourceId?.trim().isNotEmpty == true
        ? notification.resourceId!.trim()
        : (_firstMetadataString(notification.metadata, const <String>[
              'resource_id',
              'resourceId',
              'player_id',
              'playerId',
              'club_id',
              'clubId',
            ])?.trim() ??
            '');
    if (resourceId.isNotEmpty) {
      final String resourceType =
          _firstMetadataString(notification.metadata, const <String>[
            'resource_type',
            'resourceType',
          ])?.trim().toLowerCase() ??
          (notification.topic?.trim().toLowerCase() ?? '');

      if (resourceType.contains('player') ||
          notification.metadata.containsKey('player_id') ||
          notification.metadata.containsKey('playerId')) {
        return _fromExplicitRoute(
          '/players/${Uri.encodeComponent(resourceId)}/profile',
          isAdmin: isAdmin,
          source: GtexNotificationNavigationSource.resourceId,
        );
      }
      if (resourceType.contains('club') ||
          notification.metadata.containsKey('club_id') ||
          notification.metadata.containsKey('clubId')) {
        return _fromExplicitRoute(
          '/world/clubs/${Uri.encodeComponent(resourceId)}',
          isAdmin: isAdmin,
          source: GtexNotificationNavigationSource.resourceId,
        );
      }
      if (resourceType.contains('match') ||
          resourceType.contains('fixture') ||
          resourceType == 'competition_match') {
        return GtexNotificationNavigationTarget(
          route: '/matches/viewer/${Uri.encodeComponent(resourceId)}',
          source: GtexNotificationNavigationSource.resourceId,
        );
      }
      if (resourceType.contains('federation')) {
        return _fromExplicitRoute(
          '/world/federations/${Uri.encodeComponent(resourceId)}',
          isAdmin: isAdmin,
          source: GtexNotificationNavigationSource.resourceId,
        );
      }
    }

    return null;
  }

  static GtexNotificationNavigationTarget? _fromExplicitRoute(
    String route, {
    required bool isAdmin,
    GtexNotificationNavigationSource source =
        GtexNotificationNavigationSource.explicitRoute,
  }) {
    final String trimmed = route.trim();
    if (trimmed.isEmpty ||
        !trimmed.startsWith('/') ||
        trimmed.startsWith('//')) {
      return null;
    }
    final Uri? parsed = Uri.tryParse(trimmed);
    if (parsed == null || parsed.hasScheme || parsed.hasAuthority) {
      return null;
    }
    if (parsed.pathSegments.any(
      (String segment) => segment == '.' || segment == '..',
    )) {
      return null;
    }
    final String canonical = gtexCanonicalGlobalSearchRoute(
      trimmed,
      isAdmin: isAdmin,
    );
    if (canonical == '/app/home' && trimmed != '/app/home') {
      return null;
    }
    return GtexNotificationNavigationTarget(
      route: canonical,
      source: source,
    );
  }

  static String? _firstMetadataString(
    Map<String, Object?> metadata,
    List<String> keys,
  ) {
    for (final String key in keys) {
      final Object? value = metadata[key];
      if (value is String && value.trim().isNotEmpty) {
        return value;
      }
    }
    return null;
  }
}

class GtexNotificationNavigationTarget {
  const GtexNotificationNavigationTarget({
    required this.route,
    required this.source,
  });

  final String route;
  final GtexNotificationNavigationSource source;
}

enum GtexNotificationNavigationSource {
  explicitRoute,
  fixtureId,
  competitionId,
  resourceId,
}
