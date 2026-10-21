import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';

import 'launch_control_api.dart';
import 'launch_control_models.dart';

enum GtexFeatureGateBlockReason {
  hidden,
  disabled,
  paused,
  maintenance,
  killed,
  unavailable,
}

class GtexFeatureGateDecision {
  const GtexFeatureGateDecision({
    required this.featureKey,
    required this.title,
    required this.route,
    required this.allowed,
    this.reason,
    this.message,
  });

  final String? featureKey;
  final String title;
  final String route;
  final bool allowed;
  final GtexFeatureGateBlockReason? reason;
  final String? message;

  bool get blocked => !allowed;
}

class _CachedClientFlagsEntry {
  const _CachedClientFlagsEntry({
    required this.flags,
    required this.fetchedAt,
  });

  final List<GtexClientFeatureFlag> flags;
  final DateTime fetchedAt;
}

class GtexLaunchControlFeatureGate {
  const GtexLaunchControlFeatureGate._();

  static const Duration _defaultCacheTtl = Duration(minutes: 5);
  static final Map<String, _CachedClientFlagsEntry> _sessionFlagCache =
      <String, _CachedClientFlagsEntry>{};
  static int _networkFetchCountForTesting = 0;

  /// Number of network/API flag fetches executed since last [clearCache].
  static int get networkFetchCountForTesting => _networkFetchCountForTesting;

  /// Clear all session-cached launch-control flags.
  static void clearCache() {
    _sessionFlagCache.clear();
    _networkFetchCountForTesting = 0;
  }

  /// Prime the session-scoped launch-control flag cache (useful for initial
  /// shell bootstrap or deterministic tests).
  static void primeFlags({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
    required List<GtexClientFeatureFlag> flags,
    DateTime? now,
  }) {
    final String key = _cacheKey(
      baseUrl: baseUrl,
      backendMode: backendMode,
      accessToken: accessToken,
    );
    _sessionFlagCache[key] = _CachedClientFlagsEntry(
      flags: List<GtexClientFeatureFlag>.unmodifiable(flags),
      fetchedAt: now ?? DateTime.now(),
    );
  }

  static String _cacheKey({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
  }) {
    return '${baseUrl.trim()}|${backendMode.name}|${(accessToken ?? '').trim()}';
  }

  static Future<List<GtexClientFeatureFlag>> _fetchOrReadCachedFlags({
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
    bool forceRefresh = false,
  }) async {
    final String key = _cacheKey(
      baseUrl: baseUrl,
      backendMode: backendMode,
      accessToken: accessToken,
    );
    final DateTime now = DateTime.now();
    if (!forceRefresh) {
      final _CachedClientFlagsEntry? cached = _sessionFlagCache[key];
      if (cached != null &&
          now.difference(cached.fetchedAt) <= _defaultCacheTtl) {
        return cached.flags;
      }
    }

    _networkFetchCountForTesting += 1;
    final GtexLaunchControlApi api =
        backendMode == GteBackendMode.fixture
            ? GtexLaunchControlApi.fixture()
            : GtexLaunchControlApi.standard(
              baseUrl: baseUrl,
              accessToken: accessToken,
              mode: backendMode,
            );
    final List<GtexClientFeatureFlag> flags = await api.fetchClientFlags();
    _sessionFlagCache[key] = _CachedClientFlagsEntry(
      flags: List<GtexClientFeatureFlag>.unmodifiable(flags),
      fetchedAt: now,
    );
    return flags;
  }

  static String? featureKeyForRouteData(GteAppRouteData route) {
    switch (route.name) {
      case GteAppRouteNames.broadcastDesk:
        return 'broadcast';
      case GteAppRouteNames.viralFeed:
        return 'viral_clips';
      case GteAppRouteNames.clubSaleMarketListings:
      case GteAppRouteNames.clubSaleMarketDetail:
      case GteAppRouteNames.clubSaleMarketOwnerOffers:
        return 'club_sale_market';
      case GteAppRouteNames.creatorStadiumClub:
      case GteAppRouteNames.creatorStadiumMatch:
        return 'ticketing';
      case GteAppRouteNames.fanPredictionMatch:
        return 'predictions';
      case GteAppRouteNames.fanWars:
        return 'fan_coin';
      case GteAppRouteNames.footballTransferCenter:
        return 'transfer_hub';
      case GteAppRouteNames.playerCardsBrowse:
      case GteAppRouteNames.playerCardDetail:
      case GteAppRouteNames.playerCardsInventory:
        return 'player_card_marketplace';
      case GteAppRouteNames.worldFederations:
        return 'federations';
      default:
        return null;
    }
  }

  static String? featureKeyForPath(String routeOrPath) {
    final String trimmed = routeOrPath.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    final Uri? parsed = Uri.tryParse(trimmed);
    final Uri uri =
        parsed ?? Uri(path: trimmed.startsWith('/') ? trimmed : '/$trimmed');
    final String path = uri.path.toLowerCase();

    if (path == '/broadcast' || path == '/broadcast/live') {
      return 'broadcast';
    }
    if (path == '/viral-feed' || path == '/viral') {
      return 'viral_clips';
    }
    if (path == '/football/transfer-center') {
      return 'transfer_hub';
    }
    if (path.startsWith('/player-cards')) {
      return 'player_card_marketplace';
    }
    if (path == '/world/federations' || path == '/federations') {
      return 'federations';
    }
    if (path == '/clubs/sale-market' ||
        RegExp(r'^/clubs/[^/]+/sale-market(/offers)?$').hasMatch(path)) {
      return 'club_sale_market';
    }
    if (path.startsWith('/fan-predictions/')) {
      return 'predictions';
    }
    if (path == '/fan-wars') {
      return 'fan_coin';
    }
    if (path.startsWith('/creator-stadium/')) {
      return 'ticketing';
    }
    if (path == '/app/coin-traders' || path == '/app/trader-dashboard') {
      return 'coin_traders';
    }
    return null;
  }

  static Future<GtexFeatureGateDecision> resolveRouteData({
    required GteAppRouteData route,
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
    required bool isAdmin,
    bool forceRefresh = false,
  }) async {
    final String routePath = route.toUri().toString();
    return resolveFeatureKey(
      featureKey: featureKeyForRouteData(route),
      route: routePath,
      baseUrl: baseUrl,
      backendMode: backendMode,
      accessToken: accessToken,
      isAdmin: isAdmin,
      forceRefresh: forceRefresh,
    );
  }

  static Future<GtexFeatureGateDecision> resolveRoutePath({
    required String route,
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
    required bool isAdmin,
    bool forceRefresh = false,
  }) {
    return resolveFeatureKey(
      featureKey: featureKeyForPath(route),
      route: route,
      baseUrl: baseUrl,
      backendMode: backendMode,
      accessToken: accessToken,
      isAdmin: isAdmin,
      forceRefresh: forceRefresh,
    );
  }

  static Future<GtexFeatureGateDecision> resolveFeatureKey({
    required String? featureKey,
    required String route,
    required String baseUrl,
    required GteBackendMode backendMode,
    required String? accessToken,
    required bool isAdmin,
    bool forceRefresh = false,
  }) async {
    if (featureKey == null) {
      return GtexFeatureGateDecision(
        featureKey: null,
        title: 'Ungated route',
        route: route,
        allowed: true,
      );
    }
    if (isAdmin) {
      return GtexFeatureGateDecision(
        featureKey: featureKey,
        title: _titleForFeatureKey(featureKey),
        route: route,
        allowed: true,
      );
    }
    try {
      final List<GtexClientFeatureFlag> flags = await _fetchOrReadCachedFlags(
        baseUrl: baseUrl,
        backendMode: backendMode,
        accessToken: accessToken,
        forceRefresh: forceRefresh,
      );
      return resolveFromClientFlags(
        featureKey: featureKey,
        route: route,
        isAdmin: isAdmin,
        flags: flags,
      );
    } catch (_) {
      return _blocked(
        featureKey: featureKey,
        title: _titleForFeatureKey(featureKey),
        route: route,
        reason: GtexFeatureGateBlockReason.unavailable,
        message:
            'Launch status for ${_titleForFeatureKey(featureKey)} could not be confirmed.',
      );
    }
  }

  static GtexFeatureGateDecision resolveFromClientFlags({
    required String? featureKey,
    required String route,
    required bool isAdmin,
    required List<GtexClientFeatureFlag> flags,
  }) {
    if (featureKey == null || isAdmin) {
      return GtexFeatureGateDecision(
        featureKey: featureKey,
        title:
            featureKey == null
                ? 'Ungated route'
                : _titleForFeatureKey(featureKey),
        route: route,
        allowed: true,
      );
    }

    final GtexClientFeatureFlag? flag = _findFlag(flags, featureKey);
    if (flag == null) {
      final String title = _titleForFeatureKey(featureKey);
      return _blocked(
        featureKey: featureKey,
        title: title,
        route: route,
        reason: GtexFeatureGateBlockReason.hidden,
        message: '$title is not available for this account yet.',
      );
    }

    switch (flag.launchState) {
      case GtexLaunchState.hidden:
      case GtexLaunchState.internal:
        return _blocked(
          featureKey: featureKey,
          title: flag.title,
          route: route,
          reason: GtexFeatureGateBlockReason.hidden,
          message: '${flag.title} is not available for this account yet.',
        );
      case GtexLaunchState.disabled:
        return _blocked(
          featureKey: featureKey,
          title: flag.title,
          route: route,
          reason: GtexFeatureGateBlockReason.disabled,
          message: '${flag.title} is disabled by Launch Control.',
        );
      case GtexLaunchState.paused:
        return _blocked(
          featureKey: featureKey,
          title: flag.title,
          route: route,
          reason: GtexFeatureGateBlockReason.paused,
          message: '${flag.title} is paused by Launch Control.',
        );
      case GtexLaunchState.maintenance:
        return _blocked(
          featureKey: featureKey,
          title: flag.title,
          route: route,
          reason: GtexFeatureGateBlockReason.maintenance,
          message:
              flag.maintenanceMessage?.trim().isNotEmpty == true
                  ? flag.maintenanceMessage!.trim()
                  : '${flag.title} is currently in maintenance.',
        );
      case GtexLaunchState.beta:
      case GtexLaunchState.public:
        if (!flag.enabled) {
          return _blocked(
            featureKey: featureKey,
            title: flag.title,
            route: route,
            reason: GtexFeatureGateBlockReason.disabled,
            message: '${flag.title} is disabled by Launch Control.',
          );
        }
        return GtexFeatureGateDecision(
          featureKey: featureKey,
          title: flag.title,
          route: route,
          allowed: true,
        );
    }
  }

  static GtexClientFeatureFlag? _findFlag(
    List<GtexClientFeatureFlag> flags,
    String featureKey,
  ) {
    for (final GtexClientFeatureFlag flag in flags) {
      if (flag.featureKey == featureKey) {
        return flag;
      }
    }
    return null;
  }

  static GtexFeatureGateDecision _blocked({
    required String featureKey,
    required String title,
    required String route,
    required GtexFeatureGateBlockReason reason,
    required String message,
  }) {
    return GtexFeatureGateDecision(
      featureKey: featureKey,
      title: title,
      route: route,
      allowed: false,
      reason: reason,
      message: message,
    );
  }

  static String _titleForFeatureKey(String featureKey) {
    return featureKey
        .replaceAll('_', ' ')
        .replaceAll('-', ' ')
        .split(RegExp(r'\s+'))
        .where((String part) => part.isNotEmpty)
        .map(
          (String part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }
}
