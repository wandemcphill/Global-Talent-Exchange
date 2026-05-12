import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_models.dart';

enum GtexLaunchState {
  hidden,
  internal,
  beta,
  public,
  paused,
  maintenance,
  disabled,
}

GtexLaunchState gtexLaunchStateFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'hidden':
      return GtexLaunchState.hidden;
    case 'internal':
      return GtexLaunchState.internal;
    case 'beta':
      return GtexLaunchState.beta;
    case 'paused':
      return GtexLaunchState.paused;
    case 'maintenance':
      return GtexLaunchState.maintenance;
    case 'disabled':
      return GtexLaunchState.disabled;
    case 'public':
    default:
      return GtexLaunchState.public;
  }
}

String gtexLaunchStateToJson(GtexLaunchState state) => switch (state) {
  GtexLaunchState.hidden => 'hidden',
  GtexLaunchState.internal => 'internal',
  GtexLaunchState.beta => 'beta',
  GtexLaunchState.public => 'public',
  GtexLaunchState.paused => 'paused',
  GtexLaunchState.maintenance => 'maintenance',
  GtexLaunchState.disabled => 'disabled',
};

String gtexLaunchStateLabel(GtexLaunchState state) => switch (state) {
  GtexLaunchState.hidden => 'Hidden',
  GtexLaunchState.internal => 'Internal',
  GtexLaunchState.beta => 'Beta',
  GtexLaunchState.public => 'Public',
  GtexLaunchState.paused => 'Paused',
  GtexLaunchState.maintenance => 'Maintenance',
  GtexLaunchState.disabled => 'Disabled',
};

@immutable
class GtexLaunchControlFlag {
  const GtexLaunchControlFlag({
    required this.id,
    required this.featureKey,
    required this.title,
    required this.description,
    required this.enabled,
    required this.audience,
    required this.launchState,
    required this.allowedRoles,
    required this.allowedRegions,
    required this.betaOnly,
    required this.killSwitchEnabled,
    required this.maintenanceMessage,
    required this.metadata,
    required this.route,
    required this.updatedAt,
  });

  final String id;
  final String featureKey;
  final String title;
  final String? description;
  final bool enabled;
  final String audience;
  final GtexLaunchState launchState;
  final List<String> allowedRoles;
  final List<String> allowedRegions;
  final bool betaOnly;
  final bool killSwitchEnabled;
  final String? maintenanceMessage;
  final Map<String, Object?> metadata;
  final String? route;
  final DateTime updatedAt;

  bool get effectivelyEnabled {
    return enabled &&
        !killSwitchEnabled &&
        launchState != GtexLaunchState.disabled &&
        launchState != GtexLaunchState.hidden &&
        launchState != GtexLaunchState.paused &&
        launchState != GtexLaunchState.maintenance;
  }

  factory GtexLaunchControlFlag.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'launch control flag',
    );
    final Map<String, Object?> metadata = GteJson.map(
      json,
      keys: const <String>['metadata', 'metadata_json', 'metadataJson'],
      fallback: const <String, Object?>{},
    );
    final String? route =
        GteJson.stringOrNull(json, const <String>['route']) ??
        _stringFromObject(metadata['route']);
    return GtexLaunchControlFlag(
      id: GteJson.string(json, const <String>['id']),
      featureKey: GteJson.string(json, const <String>[
        'feature_key',
        'featureKey',
      ]),
      title: GteJson.string(json, const <String>['title']),
      description: GteJson.stringOrNull(json, const <String>['description']),
      enabled: GteJson.boolean(json, const <String>['enabled']),
      audience: GteJson.string(json, const <String>[
        'audience',
      ], fallback: 'global'),
      launchState: gtexLaunchStateFromString(
        GteJson.string(json, const <String>[
          'launch_state',
          'launchState',
        ], fallback: 'public'),
      ),
      allowedRoles: _stringList(json, const <String>[
        'allowed_roles',
        'allowedRoles',
        'allowed_roles_json',
      ]),
      allowedRegions: _stringList(json, const <String>[
        'allowed_regions',
        'allowedRegions',
        'allowed_regions_json',
      ]),
      betaOnly: GteJson.boolean(json, const <String>['beta_only', 'betaOnly']),
      killSwitchEnabled: GteJson.boolean(json, const <String>[
        'kill_switch_enabled',
        'killSwitchEnabled',
      ]),
      maintenanceMessage: GteJson.stringOrNull(json, const <String>[
        'maintenance_message',
        'maintenanceMessage',
      ]),
      metadata: metadata,
      route: route,
      updatedAt: GteJson.dateTime(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }

  GtexLaunchControlFlag copyWith({
    bool? enabled,
    bool? betaOnly,
    bool? killSwitchEnabled,
    GtexLaunchState? launchState,
  }) {
    return GtexLaunchControlFlag(
      id: id,
      featureKey: featureKey,
      title: title,
      description: description,
      enabled: enabled ?? this.enabled,
      audience: audience,
      launchState: launchState ?? this.launchState,
      allowedRoles: allowedRoles,
      allowedRegions: allowedRegions,
      betaOnly: betaOnly ?? this.betaOnly,
      killSwitchEnabled: killSwitchEnabled ?? this.killSwitchEnabled,
      maintenanceMessage: maintenanceMessage,
      metadata: metadata,
      route: route,
      updatedAt: DateTime.now().toUtc(),
    );
  }
}

@immutable
class GtexBetaAccessGrant {
  const GtexBetaAccessGrant({
    required this.id,
    required this.featureKey,
    required this.userId,
    required this.active,
    required this.notes,
    required this.expiresAt,
    required this.grantedByUserId,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String featureKey;
  final String userId;
  final bool active;
  final String? notes;
  final DateTime? expiresAt;
  final String? grantedByUserId;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory GtexBetaAccessGrant.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'beta access grant',
    );
    return GtexBetaAccessGrant(
      id: GteJson.string(json, const <String>['id']),
      featureKey: GteJson.string(json, const <String>[
        'feature_key',
        'featureKey',
      ]),
      userId: GteJson.string(json, const <String>['user_id', 'userId']),
      active: GteJson.boolean(json, const <String>['active'], fallback: true),
      notes: GteJson.stringOrNull(json, const <String>['notes']),
      expiresAt: GteJson.dateTimeOrNull(json, const <String>[
        'expires_at',
        'expiresAt',
      ]),
      grantedByUserId: GteJson.stringOrNull(json, const <String>[
        'granted_by_user_id',
        'grantedByUserId',
      ]),
      createdAt: GteJson.dateTime(json, const <String>[
        'created_at',
        'createdAt',
      ]),
      updatedAt: GteJson.dateTime(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }

  GtexBetaAccessGrant copyWith({
    bool? active,
    String? notes,
    DateTime? expiresAt,
    String? grantedByUserId,
  }) {
    return GtexBetaAccessGrant(
      id: id,
      featureKey: featureKey,
      userId: userId,
      active: active ?? this.active,
      notes: notes ?? this.notes,
      expiresAt: expiresAt ?? this.expiresAt,
      grantedByUserId: grantedByUserId ?? this.grantedByUserId,
      createdAt: createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
  }
}

@immutable
class GtexClientFeatureFlag {
  const GtexClientFeatureFlag({
    required this.featureKey,
    required this.title,
    required this.enabled,
    required this.launchState,
    required this.route,
    required this.maintenanceMessage,
  });

  final String featureKey;
  final String title;
  final bool enabled;
  final GtexLaunchState launchState;
  final String? route;
  final String? maintenanceMessage;

  bool get visible => launchState != GtexLaunchState.hidden;

  factory GtexClientFeatureFlag.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'client feature flag',
    );
    return GtexClientFeatureFlag(
      featureKey: GteJson.string(json, const <String>[
        'feature_key',
        'featureKey',
      ]),
      title: GteJson.string(json, const <String>['title']),
      enabled: GteJson.boolean(json, const <String>['enabled']),
      launchState: gtexLaunchStateFromString(
        GteJson.string(json, const <String>[
          'launch_state',
          'launchState',
        ], fallback: 'public'),
      ),
      route: GteJson.stringOrNull(json, const <String>['route']),
      maintenanceMessage: GteJson.stringOrNull(json, const <String>[
        'maintenance_message',
        'maintenanceMessage',
      ]),
    );
  }
}

@immutable
class GtexFeatureFlagAuditEvent {
  const GtexFeatureFlagAuditEvent({
    required this.id,
    required this.featureKey,
    required this.action,
    required this.previous,
    required this.next,
    required this.reason,
    required this.actorUserId,
    required this.createdAt,
  });

  final String id;
  final String featureKey;
  final String action;
  final Map<String, Object?> previous;
  final Map<String, Object?> next;
  final String? reason;
  final String? actorUserId;
  final DateTime createdAt;

  factory GtexFeatureFlagAuditEvent.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'feature flag audit event',
    );
    return GtexFeatureFlagAuditEvent(
      id: GteJson.string(json, const <String>['id']),
      featureKey: GteJson.string(json, const <String>[
        'feature_key',
        'featureKey',
      ]),
      action: GteJson.string(json, const <String>['action']),
      previous: GteJson.map(
        json,
        keys: const <String>['previous', 'previous_json', 'previousJson'],
        fallback: const <String, Object?>{},
      ),
      next: GteJson.map(
        json,
        keys: const <String>['next', 'next_json', 'nextJson'],
        fallback: const <String, Object?>{},
      ),
      reason: GteJson.stringOrNull(json, const <String>['reason']),
      actorUserId: GteJson.stringOrNull(json, const <String>[
        'actor_user_id',
        'actorUserId',
      ]),
      createdAt: GteJson.dateTime(json, const <String>[
        'created_at',
        'createdAt',
      ]),
    );
  }
}

@immutable
class GtexAdminCommandRoute {
  const GtexAdminCommandRoute({
    required this.moduleKey,
    required this.title,
    required this.description,
    required this.route,
    required this.featureKey,
    required this.launchState,
    required this.enabled,
  });

  final String moduleKey;
  final String title;
  final String description;
  final String route;
  final String? featureKey;
  final GtexLaunchState? launchState;
  final bool enabled;

  factory GtexAdminCommandRoute.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'admin command route',
    );
    final String? launchState = GteJson.stringOrNull(json, const <String>[
      'launch_state',
      'launchState',
    ]);
    return GtexAdminCommandRoute(
      moduleKey: GteJson.string(json, const <String>[
        'module_key',
        'moduleKey',
      ]),
      title: GteJson.string(json, const <String>['title']),
      description: GteJson.string(json, const <String>['description']),
      route: GteJson.string(json, const <String>['route']),
      featureKey: GteJson.stringOrNull(json, const <String>[
        'feature_key',
        'featureKey',
      ]),
      launchState:
          launchState == null ? null : gtexLaunchStateFromString(launchState),
      enabled: GteJson.boolean(json, const <String>['enabled']),
    );
  }
}

@immutable
class GtexModuleHealth {
  const GtexModuleHealth({
    required this.moduleKey,
    required this.status,
    required this.detail,
    required this.featureKey,
    required this.launchState,
    required this.killSwitchEnabled,
  });

  final String moduleKey;
  final String status;
  final String detail;
  final String? featureKey;
  final GtexLaunchState? launchState;
  final bool killSwitchEnabled;

  factory GtexModuleHealth.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'module health',
    );
    final String? launchState = GteJson.stringOrNull(json, const <String>[
      'launch_state',
      'launchState',
    ]);
    return GtexModuleHealth(
      moduleKey: GteJson.string(json, const <String>[
        'module_key',
        'moduleKey',
      ]),
      status: GteJson.string(json, const <String>['status']),
      detail: GteJson.string(json, const <String>['detail']),
      featureKey: GteJson.stringOrNull(json, const <String>[
        'feature_key',
        'featureKey',
      ]),
      launchState:
          launchState == null ? null : gtexLaunchStateFromString(launchState),
      killSwitchEnabled: GteJson.boolean(json, const <String>[
        'kill_switch_enabled',
        'killSwitchEnabled',
      ]),
    );
  }
}

@immutable
class GtexLaunchControlSnapshot {
  const GtexLaunchControlSnapshot({
    required this.flags,
    required this.betaGrants,
    required this.recentAuditEvents,
    required this.commandRoutes,
    required this.moduleHealth,
  });

  final List<GtexLaunchControlFlag> flags;
  final List<GtexBetaAccessGrant> betaGrants;
  final List<GtexFeatureFlagAuditEvent> recentAuditEvents;
  final List<GtexAdminCommandRoute> commandRoutes;
  final List<GtexModuleHealth> moduleHealth;

  int get enabledCount =>
      flags
          .where((GtexLaunchControlFlag flag) => flag.effectivelyEnabled)
          .length;

  int get killSwitchCount =>
      flags
          .where((GtexLaunchControlFlag flag) => flag.killSwitchEnabled)
          .length;

  int get gatedCount =>
      flags
          .where(
            (GtexLaunchControlFlag flag) =>
                flag.launchState == GtexLaunchState.beta ||
                flag.launchState == GtexLaunchState.internal ||
                flag.betaOnly,
          )
          .length;

  factory GtexLaunchControlSnapshot.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'launch control snapshot',
    );
    return GtexLaunchControlSnapshot(
      flags: GteJson.typedList(json, const <String>[
        'flags',
      ], GtexLaunchControlFlag.fromJson),
      betaGrants: GteJson.typedList(json, const <String>[
        'beta_grants',
        'betaGrants',
      ], GtexBetaAccessGrant.fromJson),
      recentAuditEvents: GteJson.typedList(json, const <String>[
        'recent_audit_events',
        'recentAuditEvents',
      ], GtexFeatureFlagAuditEvent.fromJson),
      commandRoutes: GteJson.typedList(json, const <String>[
        'command_routes',
        'commandRoutes',
      ], GtexAdminCommandRoute.fromJson),
      moduleHealth: GteJson.typedList(json, const <String>[
        'module_health',
        'moduleHealth',
      ], GtexModuleHealth.fromJson),
    );
  }

  GtexLaunchControlSnapshot replaceFlag(GtexLaunchControlFlag replacement) {
    return GtexLaunchControlSnapshot(
      flags: flags
          .map(
            (GtexLaunchControlFlag flag) =>
                flag.featureKey == replacement.featureKey ? replacement : flag,
          )
          .toList(growable: false),
      betaGrants: betaGrants,
      recentAuditEvents: recentAuditEvents,
      commandRoutes: commandRoutes,
      moduleHealth: moduleHealth,
    );
  }

  GtexLaunchControlSnapshot replaceGrant(GtexBetaAccessGrant replacement) {
    final bool exists = betaGrants.any(
      (GtexBetaAccessGrant grant) =>
          grant.featureKey == replacement.featureKey &&
          grant.userId == replacement.userId,
    );
    final List<GtexBetaAccessGrant> grants =
        exists
            ? betaGrants
                .map(
                  (GtexBetaAccessGrant grant) =>
                      grant.featureKey == replacement.featureKey &&
                              grant.userId == replacement.userId
                          ? replacement
                          : grant,
                )
                .toList(growable: false)
            : <GtexBetaAccessGrant>[replacement, ...betaGrants];
    return GtexLaunchControlSnapshot(
      flags: flags,
      betaGrants: grants,
      recentAuditEvents: recentAuditEvents,
      commandRoutes: commandRoutes,
      moduleHealth: moduleHealth,
    );
  }
}

List<String> _stringList(Map<String, Object?> json, List<String> keys) {
  return GteJson.typedList<String>(
    json,
    keys,
    (Object? value) => value?.toString() ?? '',
  ).where((String item) => item.trim().isNotEmpty).toList(growable: false);
}

String? _stringFromObject(Object? value) {
  if (value == null) {
    return null;
  }
  final String parsed = value.toString().trim();
  return parsed.isEmpty ? null : parsed;
}
