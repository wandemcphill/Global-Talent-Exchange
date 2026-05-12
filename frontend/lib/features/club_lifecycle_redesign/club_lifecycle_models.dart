import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_models.dart';

enum GtexClubLifecycleState {
  draft,
  created,
  identityPending,
  walletRequired,
  squadBuilding,
  squadReady,
  competitionReady,
  active,
  restricted,
  suspended,
  sold,
  archived,
}

enum GtexSquadRegistrationStatus { draft, submitted, locked, reopened }

GtexClubLifecycleState gtexClubLifecycleStateFromString(String value) {
  switch (value.trim().toLowerCase()) {
    case 'draft':
      return GtexClubLifecycleState.draft;
    case 'identity_pending':
      return GtexClubLifecycleState.identityPending;
    case 'wallet_required':
      return GtexClubLifecycleState.walletRequired;
    case 'squad_building':
      return GtexClubLifecycleState.squadBuilding;
    case 'squad_ready':
      return GtexClubLifecycleState.squadReady;
    case 'competition_ready':
      return GtexClubLifecycleState.competitionReady;
    case 'active':
      return GtexClubLifecycleState.active;
    case 'restricted':
      return GtexClubLifecycleState.restricted;
    case 'suspended':
      return GtexClubLifecycleState.suspended;
    case 'sold':
      return GtexClubLifecycleState.sold;
    case 'archived':
      return GtexClubLifecycleState.archived;
    case 'created':
    default:
      return GtexClubLifecycleState.created;
  }
}

String gtexClubLifecycleStateToJson(GtexClubLifecycleState state) {
  return switch (state) {
    GtexClubLifecycleState.draft => 'draft',
    GtexClubLifecycleState.created => 'created',
    GtexClubLifecycleState.identityPending => 'identity_pending',
    GtexClubLifecycleState.walletRequired => 'wallet_required',
    GtexClubLifecycleState.squadBuilding => 'squad_building',
    GtexClubLifecycleState.squadReady => 'squad_ready',
    GtexClubLifecycleState.competitionReady => 'competition_ready',
    GtexClubLifecycleState.active => 'active',
    GtexClubLifecycleState.restricted => 'restricted',
    GtexClubLifecycleState.suspended => 'suspended',
    GtexClubLifecycleState.sold => 'sold',
    GtexClubLifecycleState.archived => 'archived',
  };
}

String gtexClubLifecycleStateLabel(GtexClubLifecycleState state) {
  return switch (state) {
    GtexClubLifecycleState.draft => 'Draft',
    GtexClubLifecycleState.created => 'Created',
    GtexClubLifecycleState.identityPending => 'Identity pending',
    GtexClubLifecycleState.walletRequired => 'Wallet required',
    GtexClubLifecycleState.squadBuilding => 'Squad building',
    GtexClubLifecycleState.squadReady => 'Squad ready',
    GtexClubLifecycleState.competitionReady => 'Competition ready',
    GtexClubLifecycleState.active => 'Active',
    GtexClubLifecycleState.restricted => 'Restricted',
    GtexClubLifecycleState.suspended => 'Suspended',
    GtexClubLifecycleState.sold => 'Sold',
    GtexClubLifecycleState.archived => 'Archived',
  };
}

GtexSquadRegistrationStatus gtexSquadRegistrationStatusFromString(
  String value,
) {
  switch (value.trim().toLowerCase()) {
    case 'submitted':
      return GtexSquadRegistrationStatus.submitted;
    case 'locked':
      return GtexSquadRegistrationStatus.locked;
    case 'reopened':
      return GtexSquadRegistrationStatus.reopened;
    case 'draft':
    default:
      return GtexSquadRegistrationStatus.draft;
  }
}

String gtexSquadRegistrationStatusLabel(GtexSquadRegistrationStatus status) {
  return switch (status) {
    GtexSquadRegistrationStatus.draft => 'Draft',
    GtexSquadRegistrationStatus.submitted => 'Submitted',
    GtexSquadRegistrationStatus.locked => 'Locked',
    GtexSquadRegistrationStatus.reopened => 'Reopened',
  };
}

@immutable
class GtexClubReadinessItem {
  const GtexClubReadinessItem({
    required this.key,
    required this.label,
    required this.complete,
    required this.detail,
  });

  final String key;
  final String label;
  final bool complete;
  final String detail;

  factory GtexClubReadinessItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club readiness item',
    );
    return GtexClubReadinessItem(
      key: GteJson.string(json, const <String>['key']),
      label: GteJson.string(json, const <String>['label']),
      complete: GteJson.boolean(json, const <String>['complete']),
      detail: GteJson.string(json, const <String>['detail'], fallback: ''),
    );
  }
}

@immutable
class GtexClubReadiness {
  const GtexClubReadiness({
    required this.clubId,
    required this.readinessScore,
    required this.recommendedState,
    required this.competitionEligible,
    required this.checklist,
    required this.blockers,
    required this.updatedAt,
  });

  final String clubId;
  final int readinessScore;
  final GtexClubLifecycleState recommendedState;
  final bool competitionEligible;
  final List<GtexClubReadinessItem> checklist;
  final List<String> blockers;
  final DateTime? updatedAt;

  int get completedCount =>
      checklist.where((GtexClubReadinessItem item) => item.complete).length;

  factory GtexClubReadiness.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club readiness',
    );
    return GtexClubReadiness(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      readinessScore: GteJson.integer(json, const <String>[
        'readiness_score',
        'readinessScore',
      ]),
      recommendedState: gtexClubLifecycleStateFromString(
        GteJson.string(json, const <String>[
          'recommended_state',
          'recommendedState',
        ], fallback: 'created'),
      ),
      competitionEligible: GteJson.boolean(json, const <String>[
        'competition_eligible',
        'competitionEligible',
      ]),
      checklist: GteJson.typedList(json, const <String>[
        'checklist',
      ], GtexClubReadinessItem.fromJson),
      blockers: _stringList(json, const <String>['blockers']),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

@immutable
class GtexClubLifecycle {
  const GtexClubLifecycle({
    required this.clubId,
    required this.state,
    required this.previousState,
    required this.readinessScore,
    required this.blockedReason,
    required this.metadata,
    required this.updatedAt,
    required this.readiness,
  });

  final String clubId;
  final GtexClubLifecycleState state;
  final GtexClubLifecycleState? previousState;
  final int readinessScore;
  final String? blockedReason;
  final Map<String, Object?> metadata;
  final DateTime? updatedAt;
  final GtexClubReadiness readiness;

  factory GtexClubLifecycle.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club lifecycle',
    );
    final String? previous = GteJson.stringOrNull(json, const <String>[
      'previous_state',
      'previousState',
    ]);
    return GtexClubLifecycle(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      state: gtexClubLifecycleStateFromString(
        GteJson.string(json, const <String>['state'], fallback: 'created'),
      ),
      previousState:
          previous == null ? null : gtexClubLifecycleStateFromString(previous),
      readinessScore: GteJson.integer(json, const <String>[
        'readiness_score',
        'readinessScore',
      ]),
      blockedReason: GteJson.stringOrNull(json, const <String>[
        'blocked_reason',
        'blockedReason',
      ]),
      metadata: GteJson.map(
        json,
        keys: const <String>['metadata', 'metadata_json', 'metadataJson'],
        fallback: const <String, Object?>{},
      ),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
      readiness: GtexClubReadiness.fromJson(
        GteJson.map(json, keys: const <String>['readiness']),
      ),
    );
  }
}

@immutable
class GtexClubSquadPlayer {
  const GtexClubSquadPlayer({
    required this.playerId,
    required this.name,
    required this.position,
    required this.positionGroup,
  });

  final String playerId;
  final String name;
  final String? position;
  final String positionGroup;

  factory GtexClubSquadPlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'squad registration player',
    );
    return GtexClubSquadPlayer(
      playerId: GteJson.string(json, const <String>['player_id', 'playerId']),
      name: GteJson.string(json, const <String>['name']),
      position: GteJson.stringOrNull(json, const <String>['position']),
      positionGroup: GteJson.string(json, const <String>[
        'position_group',
        'positionGroup',
      ], fallback: 'other'),
    );
  }
}

@immutable
class GtexClubSquadRegistration {
  const GtexClubSquadRegistration({
    required this.id,
    required this.clubId,
    required this.seasonLabel,
    required this.status,
    required this.players,
    required this.positionSummary,
    required this.submittedAt,
    required this.lockedAt,
    required this.updatedAt,
  });

  final String id;
  final String clubId;
  final String seasonLabel;
  final GtexSquadRegistrationStatus status;
  final List<GtexClubSquadPlayer> players;
  final Map<String, int> positionSummary;
  final DateTime? submittedAt;
  final DateTime? lockedAt;
  final DateTime? updatedAt;

  bool get isLocked => status == GtexSquadRegistrationStatus.locked;
  bool get isSubmitted => status == GtexSquadRegistrationStatus.submitted;

  factory GtexClubSquadRegistration.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club squad registration',
    );
    return GtexClubSquadRegistration(
      id: GteJson.string(json, const <String>['id']),
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      seasonLabel: GteJson.string(json, const <String>[
        'season_label',
        'seasonLabel',
      ], fallback: 'launch'),
      status: gtexSquadRegistrationStatusFromString(
        GteJson.string(json, const <String>['status'], fallback: 'draft'),
      ),
      players: GteJson.typedList(json, const <String>[
        'players',
      ], GtexClubSquadPlayer.fromJson),
      positionSummary: _intMap(
        GteJson.map(
          json,
          keys: const <String>['position_summary', 'positionSummary'],
          fallback: const <String, Object?>{},
        ),
      ),
      submittedAt: GteJson.dateTimeOrNull(json, const <String>[
        'submitted_at',
        'submittedAt',
      ]),
      lockedAt: GteJson.dateTimeOrNull(json, const <String>[
        'locked_at',
        'lockedAt',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

@immutable
class GtexClubOperatingDashboard {
  const GtexClubOperatingDashboard({
    required this.clubId,
    required this.lifecycle,
    required this.squadRegistration,
    required this.moduleLinks,
    required this.counts,
    required this.alerts,
    required this.updatedAt,
  });

  final String clubId;
  final GtexClubLifecycle lifecycle;
  final GtexClubSquadRegistration? squadRegistration;
  final List<Map<String, String>> moduleLinks;
  final Map<String, int> counts;
  final List<String> alerts;
  final DateTime? updatedAt;

  GtexClubReadiness get readiness => lifecycle.readiness;

  int get registeredPlayerCount => squadRegistration?.players.length ?? 0;

  factory GtexClubOperatingDashboard.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club operating dashboard',
    );
    final Object? rawRegistration = GteJson.value(json, const <String>[
      'squad_registration',
      'squadRegistration',
    ]);
    return GtexClubOperatingDashboard(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      lifecycle: GtexClubLifecycle.fromJson(
        GteJson.map(json, keys: const <String>['lifecycle']),
      ),
      squadRegistration:
          rawRegistration == null
              ? null
              : GtexClubSquadRegistration.fromJson(rawRegistration),
      moduleLinks: _moduleLinks(json),
      counts: _intMap(
        GteJson.map(
          json,
          keys: const <String>['counts'],
          fallback: const <String, Object?>{},
        ),
      ),
      alerts: _stringList(json, const <String>['alerts']),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

List<String> _stringList(Map<String, Object?> json, List<String> keys) {
  final Object? value = GteJson.value(json, keys);
  if (value is List) {
    return value
        .map((Object? item) => item?.toString().trim() ?? '')
        .where((String item) => item.isNotEmpty)
        .toList(growable: false);
  }
  return const <String>[];
}

Map<String, int> _intMap(Map<String, Object?> json) {
  return json.map((String key, Object? value) {
    if (value is int) {
      return MapEntry<String, int>(key, value);
    }
    if (value is num) {
      return MapEntry<String, int>(key, value.toInt());
    }
    return MapEntry<String, int>(
      key,
      int.tryParse(value?.toString() ?? '') ?? 0,
    );
  });
}

List<Map<String, String>> _moduleLinks(Map<String, Object?> json) {
  final Object? value = GteJson.value(json, const <String>[
    'module_links',
    'moduleLinks',
  ]);
  if (value is! List) {
    return const <Map<String, String>>[];
  }
  return value
      .map((Object? item) {
        final Map<String, Object?> link = GteJson.map(
          item,
          label: 'club lifecycle module link',
        );
        return <String, String>{
          'label': GteJson.string(link, const <String>['label'], fallback: ''),
          'route': GteJson.string(link, const <String>['route'], fallback: ''),
        };
      })
      .toList(growable: false);
}
