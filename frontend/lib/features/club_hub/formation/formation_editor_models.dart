import 'package:gte_frontend/data/gte_models.dart';

enum FormationSnapshotState { draft, published, empty, blocked, degraded }

class FormationEditorSnapshot {
  const FormationEditorSnapshot({
    required this.clubId,
    required this.snapshotState,
    required this.slots,
    required this.auditTrail,
    required this.health,
    this.formationId,
    this.version,
    this.shape,
    this.updatedAt,
    this.updatedBy,
    this.publishedAt,
    this.publishedBy,
    this.syncToken,
    this.canSaveDraft = false,
    this.canPublish = false,
  });

  factory FormationEditorSnapshot.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    final Map<String, Object?> healthJson = GteJson.map(
      GteJson.value(json, const <String>['health', 'formation_health']),
      fallback: const <String, Object?>{},
    );
    final List<FormationBoardSlot> slots = GteJson.list(
      GteJson.value(json, const <String>['slots', 'lineup_slots', 'roles']) ??
          const <Object?>[],
      label: 'formation slots',
    ).map(FormationBoardSlot.fromJson).toList(growable: false);
    final FormationHealth health = FormationHealth.fromJson(healthJson, slots);

    return FormationEditorSnapshot(
      clubId: GteJson.string(json, const <String>[
        'club_id',
        'clubId',
      ], fallback: ''),
      formationId: GteJson.stringOrNull(json, const <String>[
        'id',
        'formation_id',
      ]),
      version: GteJson.integerOrNull(json, const <String>['version']),
      shape: GteJson.stringOrNull(json, const <String>['shape', 'formation']),
      snapshotState: _snapshotState(json, slots, health),
      slots: slots,
      health: health,
      auditTrail: GteJson.list(
        GteJson.value(json, const <String>['audit_trail', 'auditTrail']) ??
            const <Object?>[],
        label: 'formation audit trail',
      ).map(FormationAuditEvent.fromJson).toList(growable: false),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
      updatedBy: GteJson.stringOrNull(json, const <String>[
        'updated_by',
        'updatedBy',
      ]),
      publishedAt: GteJson.dateTimeOrNull(json, const <String>[
        'published_at',
        'publishedAt',
      ]),
      publishedBy: GteJson.stringOrNull(json, const <String>[
        'published_by',
        'publishedBy',
      ]),
      syncToken: GteJson.stringOrNull(json, const <String>[
        'sync_token',
        'syncToken',
      ]),
      canSaveDraft: GteJson.boolean(json, const <String>[
        'can_save_draft',
        'canSaveDraft',
      ], fallback: false),
      canPublish: GteJson.boolean(json, const <String>[
        'can_publish',
        'canPublish',
      ], fallback: false),
    );
  }

  final String clubId;
  final String? formationId;
  final int? version;
  final String? shape;
  final FormationSnapshotState snapshotState;
  final List<FormationBoardSlot> slots;
  final FormationHealth health;
  final List<FormationAuditEvent> auditTrail;
  final DateTime? updatedAt;
  final String? updatedBy;
  final DateTime? publishedAt;
  final String? publishedBy;
  final String? syncToken;
  final bool canSaveDraft;
  final bool canPublish;

  bool get hasBoardData => slots.isNotEmpty;
  bool get hasPublishAudit => auditTrail.isNotEmpty || publishedAt != null;
  List<FormationBoardSlot> get positionedSlots =>
      slots.where((FormationBoardSlot slot) => slot.hasPitchPosition).toList();
  List<FormationBoardSlot> get unpositionedSlots =>
      slots.where((FormationBoardSlot slot) => !slot.hasPitchPosition).toList();

  static FormationSnapshotState _snapshotState(
    Map<String, Object?> json,
    List<FormationBoardSlot> slots,
    FormationHealth health,
  ) {
    final String status =
        (GteJson.stringOrNull(json, const <String>[
                  'status',
                  'state',
                  'snapshot_state',
                  'snapshotState',
                ]) ??
                '')
            .toLowerCase();
    if (status.contains('block')) {
      return FormationSnapshotState.blocked;
    }
    if (status.contains('degrad')) {
      return FormationSnapshotState.degraded;
    }
    if (health.isBlocked) {
      return FormationSnapshotState.blocked;
    }
    if (health.warnings.isNotEmpty) {
      return FormationSnapshotState.degraded;
    }
    if (status.contains('publish')) {
      return FormationSnapshotState.published;
    }
    if (status.contains('draft')) {
      return FormationSnapshotState.draft;
    }
    if (slots.isEmpty) {
      return FormationSnapshotState.empty;
    }
    return health.isHealthy
        ? FormationSnapshotState.published
        : FormationSnapshotState.degraded;
  }
}

class FormationBoardSlot {
  const FormationBoardSlot({
    required this.id,
    this.roleCode,
    this.roleLabel,
    this.playerId,
    this.playerName,
    this.positionGroup,
    this.x,
    this.y,
    this.lockedReason,
  });

  factory FormationBoardSlot.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return FormationBoardSlot(
      id: GteJson.string(json, const <String>['id', 'slot_id', 'slotId']),
      roleCode: GteJson.stringOrNull(json, const <String>[
        'role_code',
        'roleCode',
      ]),
      roleLabel: GteJson.stringOrNull(json, const <String>[
        'role_label',
        'roleLabel',
        'role',
      ]),
      playerId: GteJson.stringOrNull(json, const <String>[
        'player_id',
        'playerId',
      ]),
      playerName: GteJson.stringOrNull(json, const <String>[
        'player_name',
        'playerName',
      ]),
      positionGroup: GteJson.stringOrNull(json, const <String>[
        'position_group',
        'positionGroup',
      ]),
      x: _numberOrNull(json, const <String>['x', 'pitch_x', 'pitchX']),
      y: _numberOrNull(json, const <String>['y', 'pitch_y', 'pitchY']),
      lockedReason: GteJson.stringOrNull(json, const <String>[
        'locked_reason',
        'lockedReason',
      ]),
    );
  }

  final String id;
  final String? roleCode;
  final String? roleLabel;
  final String? playerId;
  final String? playerName;
  final String? positionGroup;
  final double? x;
  final double? y;
  final String? lockedReason;

  bool get hasPitchPosition => x != null && y != null;
  bool get hasAssignedPlayer => playerId != null || playerName != null;
  String get displayRole => roleLabel ?? roleCode ?? 'Role pending';
  String get displayPlayer => playerName ?? 'Unassigned';
}

class FormationHealth {
  const FormationHealth({
    required this.score,
    required this.blockers,
    required this.warnings,
  });

  factory FormationHealth.fromJson(
    Map<String, Object?> json,
    List<FormationBoardSlot> slots,
  ) {
    final int? score = GteJson.integerOrNull(json, const <String>['score']);
    return FormationHealth(
      score: score,
      blockers: _stringList(
        GteJson.value(json, const <String>['blockers', 'blocking_reasons']),
      ),
      warnings: _stringList(
        GteJson.value(json, const <String>['warnings', 'degraded_reasons']),
      ),
    );
  }

  final int? score;
  final List<String> blockers;
  final List<String> warnings;

  bool get isBlocked => blockers.isNotEmpty;
  bool get isHealthy => !isBlocked && warnings.isEmpty;
}

class FormationAuditEvent {
  const FormationAuditEvent({
    required this.id,
    required this.action,
    this.actor,
    this.occurredAt,
    this.note,
    this.version,
  });

  factory FormationAuditEvent.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return FormationAuditEvent(
      id: GteJson.string(json, const <String>['id', 'event_id', 'eventId']),
      action: GteJson.string(json, const <String>[
        'action',
        'event_type',
        'eventType',
      ]),
      actor: GteJson.stringOrNull(json, const <String>[
        'actor',
        'actor_name',
        'actorName',
      ]),
      occurredAt: GteJson.dateTimeOrNull(json, const <String>[
        'occurred_at',
        'occurredAt',
      ]),
      note: GteJson.stringOrNull(json, const <String>['note', 'summary']),
      version: GteJson.integerOrNull(json, const <String>['version']),
    );
  }

  final String id;
  final String action;
  final String? actor;
  final DateTime? occurredAt;
  final String? note;
  final int? version;
}

List<String> _stringList(Object? value) {
  if (value == null) {
    return const <String>[];
  }
  return GteJson.list(value)
      .map((Object? item) => item?.toString().trim() ?? '')
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

double? _numberOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? raw = GteJson.value(json, keys);
  if (raw == null) {
    return null;
  }
  if (raw is num) {
    return raw.toDouble();
  }
  return double.tryParse(raw.toString());
}
