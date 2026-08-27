import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'launch_control_models.dart';

class GtexLaunchControlApi {
  GtexLaunchControlApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final GtexLaunchControlFixtures? fixtures;

  factory GtexLaunchControlApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteAuthedApi? client,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexLaunchControlApi(
      client:
          client ??
          GteAuthedApi(
            config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
            transport: GteHttpTransport(),
            accessToken: accessToken,
            mode: resolvedMode,
          ),
      fixtures:
          resolvedMode == GteBackendMode.fixture
              ? GtexLaunchControlFixtures.seed()
              : null,
    );
  }

  factory GtexLaunchControlApi.fixture() {
    assertFixtureFactoryAllowed('GtexLaunchControlApi.fixture');
    return GtexLaunchControlApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: GtexLaunchControlFixtures.seed(),
    );
  }

  Future<GtexLaunchControlSnapshot> fetchDashboard() {
    return client.withFallback<GtexLaunchControlSnapshot>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/admin/launch-control',
      );
      return GtexLaunchControlSnapshot.fromJson(payload);
    }, () => _requireFixtures().dashboard());
  }

  Future<GtexLaunchControlFlag> setFlagEnabled({
    required String featureKey,
    required bool enabled,
    String? reason,
  }) {
    return client.withFallback<GtexLaunchControlFlag>(
      () async {
        final Object? payload = await client.post(
          enabled
              ? '/api/admin/feature-flags/$featureKey/enable'
              : '/api/admin/feature-flags/$featureKey/disable',
          body: <String, Object?>{'reason': reason},
        );
        return GtexLaunchControlFlag.fromJson(payload);
      },
      () => _requireFixtures().setFlagEnabled(
        featureKey: featureKey,
        enabled: enabled,
      ),
    );
  }

  Future<GtexLaunchControlFlag> setKillSwitch({
    required String featureKey,
    required bool enabled,
    String? reason,
  }) {
    return client.withFallback<GtexLaunchControlFlag>(
      () async {
        final Object? payload = await client.post(
          '/api/admin/feature-flags/$featureKey/kill-switch',
          body: <String, Object?>{'enabled': enabled, 'reason': reason},
        );
        return GtexLaunchControlFlag.fromJson(payload);
      },
      () => _requireFixtures().setKillSwitch(
        featureKey: featureKey,
        enabled: enabled,
      ),
    );
  }

  Future<GtexLaunchControlFlag> updateFlag({
    required String featureKey,
    GtexLaunchState? launchState,
    bool? betaOnly,
    String? reason,
  }) {
    return client.withFallback<GtexLaunchControlFlag>(
      () async {
        final Object? payload = await client.request(
          'PATCH',
          '/api/admin/feature-flags/$featureKey',
          body: <String, Object?>{
            if (launchState != null)
              'launch_state': gtexLaunchStateToJson(launchState),
            if (betaOnly != null) 'beta_only': betaOnly,
            'reason': reason,
          },
        );
        return GtexLaunchControlFlag.fromJson(payload);
      },
      () => _requireFixtures().updateFlag(
        featureKey: featureKey,
        launchState: launchState,
        betaOnly: betaOnly,
      ),
    );
  }

  Future<List<GtexClientFeatureFlag>> fetchClientFlags() {
    final bool useAuth =
        (client.accessToken?.trim().isNotEmpty ?? false) ||
        (client.authSession?.accessToken.trim().isNotEmpty ?? false);
    return client.withFallback<List<GtexClientFeatureFlag>>(() async {
      final List<dynamic> payload = await client.getList(
        '/api/feature-flags/client',
        auth: useAuth,
      );
      return payload
          .map(GtexClientFeatureFlag.fromJson)
          .toList(growable: false);
    }, () => _requireFixtures().clientFlags());
  }

  Future<GtexBetaAccessGrant> grantBetaAccess({
    required String featureKey,
    required String userId,
    String? notes,
    DateTime? expiresAt,
  }) {
    return client.withFallback<GtexBetaAccessGrant>(
      () async {
        final Object? payload = await client.post(
          '/api/admin/beta-access',
          body: <String, Object?>{
            'feature_key': featureKey,
            'user_id': userId,
            'active': true,
            'notes': notes,
            'expires_at': expiresAt?.toUtc().toIso8601String(),
          },
        );
        return GtexBetaAccessGrant.fromJson(payload);
      },
      () => _requireFixtures().grantBetaAccess(
        featureKey: featureKey,
        userId: userId,
        notes: notes,
        expiresAt: expiresAt,
      ),
    );
  }

  Future<GtexBetaAccessGrant> revokeBetaAccess({
    required String featureKey,
    required String userId,
  }) {
    final String encodedFeatureKey = Uri.encodeComponent(featureKey);
    final String encodedUserId = Uri.encodeComponent(userId);
    return client.withFallback<GtexBetaAccessGrant>(
      () async {
        await client.request(
          'DELETE',
          '/api/admin/beta-access/$encodedFeatureKey/$encodedUserId',
        );
        return GtexBetaAccessGrant(
          id: 'revoked-$featureKey-$userId',
          featureKey: featureKey,
          userId: userId,
          active: false,
          notes: 'Revoked from Launch Control',
          expiresAt: null,
          grantedByUserId: null,
          createdAt: DateTime.now().toUtc(),
          updatedAt: DateTime.now().toUtc(),
        );
      },
      () => _requireFixtures().revokeBetaAccess(
        featureKey: featureKey,
        userId: userId,
      ),
    );
  }

  GtexLaunchControlFixtures _requireFixtures() {
    final GtexLaunchControlFixtures? resolvedFixtures = fixtures;
    if (resolvedFixtures == null) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message:
            'Launch-control fixtures are not registered in strict-live runtime.',
      );
    }
    return resolvedFixtures;
  }
}

class GtexLaunchControlFixtures {
  GtexLaunchControlFixtures(this._snapshot);

  GtexLaunchControlSnapshot _snapshot;

  static GtexLaunchControlFixtures seed() {
    final DateTime now = DateTime.parse('2026-05-11T09:00:00Z');
    final List<GtexLaunchControlFlag> flags = <GtexLaunchControlFlag>[
      GtexLaunchControlFlag(
        id: 'flag-launch-control',
        featureKey: 'launch_control',
        title: 'Launch Control',
        description: 'Batch 34 rollout state control.',
        enabled: true,
        audience: 'admin',
        launchState: GtexLaunchState.internal,
        allowedRoles: const <String>['admin', 'super_admin'],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/admin/launch-control'},
        route: '/admin/launch-control',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-transfer-hub',
        featureKey: 'transfer_hub',
        title: 'Transfer Hub',
        description: 'Loans, swaps, private bids, and transfer deadlines.',
        enabled: false,
        audience: 'beta',
        launchState: GtexLaunchState.internal,
        allowedRoles: const <String>['admin', 'super_admin'],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/app/market'},
        route: '/app/market',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-fan-coin',
        featureKey: 'fan_coin',
        title: 'Fan Coin',
        description: 'Fan rewards, gifts, predictions, and fan wars.',
        enabled: true,
        audience: 'beta',
        launchState: GtexLaunchState.beta,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: true,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/app/community'},
        route: '/app/community',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-coin-traders',
        featureKey: 'coin_traders',
        title: 'Coin Traders',
        description: 'Approved liquidity desks, orders, and trader access.',
        enabled: true,
        audience: 'public',
        launchState: GtexLaunchState.public,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/app/coin-traders'},
        route: '/app/coin-traders',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-predictions',
        featureKey: 'predictions',
        title: 'Predictions',
        description: 'Fan prediction cards and reward settlement.',
        enabled: true,
        audience: 'public',
        launchState: GtexLaunchState.public,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/fan-predictions/matches'},
        route: '/fan-predictions/matches',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-ticketing',
        featureKey: 'ticketing',
        title: 'Ticketing',
        description: 'Stadium tickets, resale, and matchday attendance.',
        enabled: true,
        audience: 'public',
        launchState: GtexLaunchState.public,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/creator-stadium/matches'},
        route: '/creator-stadium/matches',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-player-card-marketplace',
        featureKey: 'player_card_marketplace',
        title: 'Player Card Marketplace',
        description: 'Collectible player cards, packs, listings, and offers.',
        enabled: true,
        audience: 'public',
        launchState: GtexLaunchState.public,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/player-cards'},
        route: '/player-cards',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-club-sale-market',
        featureKey: 'club_sale_market',
        title: 'Club Sale Market',
        description: 'Club listings, owner offers, and safe transfer review.',
        enabled: true,
        audience: 'public',
        launchState: GtexLaunchState.public,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/clubs/sale-market'},
        route: '/clubs/sale-market',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-broadcast',
        featureKey: 'broadcast',
        title: 'Broadcast',
        description: 'Clips, rights, highlights, and packages.',
        enabled: true,
        audience: 'beta',
        launchState: GtexLaunchState.maintenance,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: true,
        maintenanceMessage: 'Rights worker paused.',
        metadata: const <String, Object?>{'route': '/broadcast/live'},
        route: '/broadcast/live',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-viral-clips',
        featureKey: 'viral_clips',
        title: 'Viral Clips',
        description: 'Viral feed, clip moderation, and highlight distribution.',
        enabled: true,
        audience: 'public',
        launchState: GtexLaunchState.public,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/viral-feed'},
        route: '/viral-feed',
        updatedAt: now,
      ),
      GtexLaunchControlFlag(
        id: 'flag-federations',
        featureKey: 'federations',
        title: 'Federations',
        description:
            'Federation governance, national association ops, and eligibility review.',
        enabled: true,
        audience: 'public',
        launchState: GtexLaunchState.public,
        allowedRoles: const <String>[],
        allowedRegions: const <String>[],
        betaOnly: false,
        killSwitchEnabled: false,
        maintenanceMessage: null,
        metadata: const <String, Object?>{'route': '/world/federations'},
        route: '/world/federations',
        updatedAt: now,
      ),
    ];
    return GtexLaunchControlFixtures(
      GtexLaunchControlSnapshot(
        flags: flags,
        betaGrants: <GtexBetaAccessGrant>[
          GtexBetaAccessGrant(
            id: 'grant-1',
            featureKey: 'fan_coin',
            userId: 'user-beta',
            active: true,
            notes: 'Fixture beta grant',
            expiresAt: null,
            grantedByUserId: 'admin-fixture',
            createdAt: now,
            updatedAt: now,
          ),
        ],
        recentAuditEvents: <GtexFeatureFlagAuditEvent>[
          GtexFeatureFlagAuditEvent(
            id: 'audit-1',
            featureKey: 'broadcast',
            action: 'kill_switch_enabled',
            previous: const <String, Object?>{'kill_switch_enabled': false},
            next: const <String, Object?>{'kill_switch_enabled': true},
            reason: 'Fixture pause',
            actorUserId: 'admin-fixture',
            createdAt: now,
          ),
        ],
        commandRoutes: const <GtexAdminCommandRoute>[
          GtexAdminCommandRoute(
            moduleKey: 'launch_control',
            title: 'Launch Control',
            description: 'Batch 34 rollout state control.',
            route: '/admin/launch-control',
            featureKey: 'launch_control',
            launchState: GtexLaunchState.internal,
            enabled: true,
          ),
          GtexAdminCommandRoute(
            moduleKey: 'transfer_hub',
            title: 'Transfer Hub',
            description: 'Loan, swap, and transfer launch surface.',
            route: '/app/market',
            featureKey: 'transfer_hub',
            launchState: GtexLaunchState.internal,
            enabled: false,
          ),
        ],
        moduleHealth: const <GtexModuleHealth>[
          GtexModuleHealth(
            moduleKey: 'launch_control',
            status: 'gated',
            detail: 'Feature is enabled for internal rollout access.',
            featureKey: 'launch_control',
            launchState: GtexLaunchState.internal,
            killSwitchEnabled: false,
          ),
          GtexModuleHealth(
            moduleKey: 'broadcast',
            status: 'kill_switch',
            detail: 'Kill switch is active; client actions are blocked.',
            featureKey: 'broadcast',
            launchState: GtexLaunchState.maintenance,
            killSwitchEnabled: true,
          ),
        ],
      ),
    );
  }

  Future<GtexLaunchControlSnapshot> dashboard() async => _snapshot;

  Future<List<GtexClientFeatureFlag>> clientFlags() async {
    return _snapshot.flags
        .where(
          (GtexLaunchControlFlag flag) =>
              flag.launchState != GtexLaunchState.hidden &&
              flag.launchState != GtexLaunchState.disabled &&
              flag.launchState != GtexLaunchState.internal,
        )
        .map(
          (GtexLaunchControlFlag flag) => GtexClientFeatureFlag(
            featureKey: flag.featureKey,
            title: flag.title,
            enabled: flag.effectivelyEnabled,
            launchState: flag.launchState,
            route: flag.route,
            maintenanceMessage:
                flag.launchState == GtexLaunchState.maintenance
                    ? flag.maintenanceMessage
                    : null,
          ),
        )
        .toList(growable: false);
  }

  Future<GtexLaunchControlFlag> setFlagEnabled({
    required String featureKey,
    required bool enabled,
  }) async {
    final GtexLaunchControlFlag flag = _findFlag(
      featureKey,
    ).copyWith(enabled: enabled);
    _snapshot = _snapshot.replaceFlag(flag);
    return flag;
  }

  Future<GtexLaunchControlFlag> setKillSwitch({
    required String featureKey,
    required bool enabled,
  }) async {
    final GtexLaunchControlFlag flag = _findFlag(
      featureKey,
    ).copyWith(killSwitchEnabled: enabled);
    _snapshot = _snapshot.replaceFlag(flag);
    return flag;
  }

  Future<GtexLaunchControlFlag> updateFlag({
    required String featureKey,
    GtexLaunchState? launchState,
    bool? betaOnly,
  }) async {
    final GtexLaunchControlFlag flag = _findFlag(
      featureKey,
    ).copyWith(launchState: launchState, betaOnly: betaOnly);
    _snapshot = _snapshot.replaceFlag(flag);
    return flag;
  }

  Future<GtexBetaAccessGrant> grantBetaAccess({
    required String featureKey,
    required String userId,
    String? notes,
    DateTime? expiresAt,
  }) async {
    final DateTime now = DateTime.now().toUtc();
    final GtexBetaAccessGrant grant = GtexBetaAccessGrant(
      id: 'grant-$featureKey-$userId',
      featureKey: featureKey,
      userId: userId,
      active: true,
      notes: notes,
      expiresAt: expiresAt,
      grantedByUserId: 'admin-fixture',
      createdAt: now,
      updatedAt: now,
    );
    _snapshot = _snapshot.replaceGrant(grant);
    return grant;
  }

  Future<GtexBetaAccessGrant> revokeBetaAccess({
    required String featureKey,
    required String userId,
  }) async {
    final GtexBetaAccessGrant existing = _snapshot.betaGrants.firstWhere(
      (GtexBetaAccessGrant grant) =>
          grant.featureKey == featureKey && grant.userId == userId,
      orElse:
          () => GtexBetaAccessGrant(
            id: 'grant-$featureKey-$userId',
            featureKey: featureKey,
            userId: userId,
            active: true,
            notes: null,
            expiresAt: null,
            grantedByUserId: 'admin-fixture',
            createdAt: DateTime.now().toUtc(),
            updatedAt: DateTime.now().toUtc(),
          ),
    );
    final GtexBetaAccessGrant grant = existing.copyWith(active: false);
    _snapshot = _snapshot.replaceGrant(grant);
    return grant;
  }

  GtexLaunchControlFlag _findFlag(String featureKey) {
    return _snapshot.flags.firstWhere(
      (GtexLaunchControlFlag flag) => flag.featureKey == featureKey,
    );
  }
}
