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

    // `fixture_id` is the one legacy identifier with an exact, registered
    // route convention. Other IDs require an explicit backend route so that
    // an offer, club, or competition is never sent to an invented surface.
    final String fixtureId = notification.fixtureId?.trim() ?? '';
    if (fixtureId.isEmpty) {
      return null;
    }
    return GtexNotificationNavigationTarget(
      route: '/matches/viewer/${Uri.encodeComponent(fixtureId)}',
      source: GtexNotificationNavigationSource.fixtureId,
    );
  }

  static GtexNotificationNavigationTarget? _fromExplicitRoute(
    String route, {
    required bool isAdmin,
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
      source: GtexNotificationNavigationSource.explicitRoute,
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

enum GtexNotificationNavigationSource { explicitRoute, fixtureId }
