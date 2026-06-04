import 'package:gte_frontend/data/gte_models.dart';

const String insufficientEligiblePlayersMessage =
    'Insufficient eligible players - update squad before editing formation.';
const String noActiveFormationMessage = 'No active formation - create one.';
const String scoutFormationBlockedMessage =
    'Club scouts can view formations but cannot edit or publish.';
const String roleFormationBlockedMessage =
    'Formation editing requires club owner or club manager access.';

enum FormationStatus {
  draft,
  published,
  archived;

  static FormationStatus fromJson(Object? value) {
    final String normalized = value?.toString().trim().toLowerCase() ?? '';
    return switch (normalized) {
      'draft' => FormationStatus.draft,
      'published' => FormationStatus.published,
      'archived' => FormationStatus.archived,
      _ => FormationStatus.draft,
    };
  }

  String get jsonName => name;
}

class FormationDto {
  const FormationDto({
    required this.id,
    required this.clubId,
    required this.name,
    required this.scheme,
    required this.slots,
    required this.chemistryScore,
    required this.warnings,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.publishedAt,
    this.auditRef,
  });

  final String id;
  final String clubId;
  final String name;
  final String scheme;
  final List<FormationSlotDto> slots;
  final double chemistryScore;
  final List<String> warnings;
  final FormationStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? publishedAt;
  final String? auditRef;

  bool get hasStartingXi =>
      slots.where((FormationSlotDto slot) {
        return slot.filled &&
            (slot.assignedPlayerId?.trim().isNotEmpty ?? false);
      }).length >=
      11;

  FormationDto copyWith({
    String? id,
    String? clubId,
    String? name,
    String? scheme,
    List<FormationSlotDto>? slots,
    double? chemistryScore,
    List<String>? warnings,
    FormationStatus? status,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? publishedAt,
    String? auditRef,
  }) {
    return FormationDto(
      id: id ?? this.id,
      clubId: clubId ?? this.clubId,
      name: name ?? this.name,
      scheme: scheme ?? this.scheme,
      slots: slots ?? this.slots,
      chemistryScore: chemistryScore ?? this.chemistryScore,
      warnings: warnings ?? this.warnings,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      publishedAt: publishedAt ?? this.publishedAt,
      auditRef: auditRef ?? this.auditRef,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'club_id': clubId,
      'name': name,
      'scheme': scheme,
      'slots': slots.map((FormationSlotDto slot) => slot.toJson()).toList(),
      'chemistry_score': chemistryScore,
      'warnings': warnings,
      'status': status.jsonName,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      if (publishedAt != null) 'published_at': publishedAt!.toIso8601String(),
      if (auditRef != null) 'audit_ref': auditRef,
    };
  }

  factory FormationDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'formation');
    return FormationDto(
      id: GteJson.string(json, const <String>['id']),
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      name: GteJson.string(json, const <String>['name'], fallback: 'Untitled'),
      scheme: GteJson.string(json, const <String>['scheme'], fallback: '4-3-3'),
      slots: GteJson.typedList<FormationSlotDto>(json, const <String>[
        'slots',
      ], FormationSlotDto.fromJson),
      chemistryScore: GteJson.number(json, const <String>[
        'chemistry_score',
        'chemistryScore',
      ]),
      warnings: GteJson.typedList<String>(
        json,
        const <String>['warnings'],
        (Object? item) => item?.toString() ?? '',
      ).where((String item) => item.trim().isNotEmpty).toList(growable: false),
      status: FormationStatus.fromJson(
        GteJson.value(json, const <String>['status']),
      ),
      createdAt: GteJson.dateTime(json, const <String>[
        'created_at',
        'createdAt',
      ]),
      updatedAt: GteJson.dateTime(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
      publishedAt: GteJson.dateTimeOrNull(json, const <String>[
        'published_at',
        'publishedAt',
      ]),
      auditRef: GteJson.stringOrNull(json, const <String>[
        'audit_ref',
        'auditRef',
      ]),
    );
  }
}

class FormationSlotDto {
  const FormationSlotDto({
    required this.slotId,
    required this.position,
    required this.x,
    required this.y,
    required this.role,
    required this.filled,
    this.assignedPlayerId,
  });

  final String slotId;
  final String position;
  final String? assignedPlayerId;
  final double x;
  final double y;
  final String role;
  final bool filled;

  FormationSlotDto copyWith({
    String? slotId,
    String? position,
    String? assignedPlayerId,
    double? x,
    double? y,
    String? role,
    bool? filled,
  }) {
    return FormationSlotDto(
      slotId: slotId ?? this.slotId,
      position: position ?? this.position,
      assignedPlayerId: assignedPlayerId ?? this.assignedPlayerId,
      x: x ?? this.x,
      y: y ?? this.y,
      role: role ?? this.role,
      filled: filled ?? this.filled,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'slot_id': slotId,
      'position': position,
      if (assignedPlayerId != null) 'assigned_player_id': assignedPlayerId,
      'x': x,
      'y': y,
      'role': role,
      'filled': filled,
    };
  }

  factory FormationSlotDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'formation slot',
    );
    return FormationSlotDto(
      slotId: GteJson.string(json, const <String>['slot_id', 'slotId']),
      position: GteJson.string(json, const <String>['position']),
      assignedPlayerId: GteJson.stringOrNull(json, const <String>[
        'assigned_player_id',
        'assignedPlayerId',
      ]),
      x: GteJson.number(json, const <String>['x']),
      y: GteJson.number(json, const <String>['y']),
      role: GteJson.string(json, const <String>['role'], fallback: 'balanced'),
      filled: GteJson.boolean(json, const <String>['filled']),
    );
  }
}

class FormationHistoryItemDto {
  const FormationHistoryItemDto({
    required this.id,
    required this.name,
    required this.scheme,
    required this.chemistryScore,
    required this.status,
    this.publishedAt,
  });

  final String id;
  final String name;
  final String scheme;
  final DateTime? publishedAt;
  final double chemistryScore;
  final FormationStatus status;

  factory FormationHistoryItemDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'formation history item',
    );
    return FormationHistoryItemDto(
      id: GteJson.string(json, const <String>['id']),
      name: GteJson.string(json, const <String>['name'], fallback: 'Untitled'),
      scheme: GteJson.string(json, const <String>['scheme'], fallback: '4-3-3'),
      publishedAt: GteJson.dateTimeOrNull(json, const <String>[
        'published_at',
        'publishedAt',
      ]),
      chemistryScore: GteJson.number(json, const <String>[
        'chemistry_score',
        'chemistryScore',
      ]),
      status: FormationStatus.fromJson(
        GteJson.value(json, const <String>['status']),
      ),
    );
  }
}

class FormationSelectionReadyPlayerDto {
  const FormationSelectionReadyPlayerDto({
    required this.id,
    required this.name,
    required this.position,
    required this.eligible,
  });

  final String id;
  final String name;
  final String position;
  final bool eligible;

  factory FormationSelectionReadyPlayerDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'selection-ready player',
    );
    return FormationSelectionReadyPlayerDto(
      id: GteJson.string(json, const <String>['id', 'player_id', 'playerId']),
      name: GteJson.string(json, const <String>[
        'name',
        'display_name',
        'displayName',
      ]),
      position: GteJson.string(json, const <String>[
        'position',
      ], fallback: 'UNK'),
      eligible: GteJson.boolean(json, const <String>[
        'eligible',
        'squad_eligible',
        'squadEligible',
      ], fallback: true),
    );
  }
}

class FormationSaveRequest {
  const FormationSaveRequest({
    required this.name,
    required this.scheme,
    required this.slots,
    this.sourceFormationId,
  });

  final String name;
  final String scheme;
  final List<FormationSlotDto> slots;
  final String? sourceFormationId;

  factory FormationSaveRequest.fromDraft(
    FormationDto draft, {
    String? sourceFormationId,
  }) {
    return FormationSaveRequest(
      name: draft.name,
      scheme: draft.scheme,
      slots: draft.slots,
      sourceFormationId: sourceFormationId,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'name': name,
      'scheme': scheme,
      'slots': slots.map((FormationSlotDto slot) => slot.toJson()).toList(),
      if (sourceFormationId != null) 'source_formation_id': sourceFormationId,
    };
  }
}

class FormationEditorBlock {
  const FormationEditorBlock({required this.reason, this.ctaRoute});

  final String reason;
  final String? ctaRoute;
}

FormationEditorBlock? evaluateFormationEditorBlock({
  required int eligiblePlayerCount,
  required String role,
}) {
  if (eligiblePlayerCount < 11) {
    return const FormationEditorBlock(
      reason: insufficientEligiblePlayersMessage,
      ctaRoute: '/app/squad',
    );
  }
  final String normalizedRole = role.trim().toLowerCase();
  if (normalizedRole == 'club.owner' || normalizedRole == 'club.manager') {
    return null;
  }
  if (normalizedRole == 'club.scout') {
    return const FormationEditorBlock(reason: scoutFormationBlockedMessage);
  }
  return const FormationEditorBlock(reason: roleFormationBlockedMessage);
}

class FormationPublishReadiness {
  const FormationPublishReadiness({
    required this.canPublish,
    required this.blockedReasons,
  });

  final bool canPublish;
  final List<String> blockedReasons;

  bool get isBlocked => !canPublish;

  static FormationPublishReadiness evaluate({
    required FormationDto? draft,
    required int eligiblePlayerCount,
    required String role,
    required bool pending,
  }) {
    final List<String> reasons = <String>[];
    final FormationEditorBlock? block = evaluateFormationEditorBlock(
      eligiblePlayerCount: eligiblePlayerCount,
      role: role,
    );
    if (block != null) {
      reasons.add(block.reason);
    }
    if (draft == null) {
      reasons.add('No draft formation is ready to publish.');
    } else if (!draft.hasStartingXi) {
      reasons.add('Publish requires 11 filled formation slots.');
    }
    if (pending) {
      reasons.add('Publish is already pending backend confirmation.');
    }
    return FormationPublishReadiness(
      canPublish: reasons.isEmpty,
      blockedReasons: List<String>.unmodifiable(reasons),
    );
  }
}
