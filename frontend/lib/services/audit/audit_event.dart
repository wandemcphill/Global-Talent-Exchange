sealed class AuditEvent {
  const AuditEvent({
    required this.type,
    required this.actorId,
    required this.entityType,
    required this.entityId,
    required this.timestamp,
    this.before,
    this.after,
    this.metadata = const <String, Object?>{},
    this.idempotencyKey,
  });

  final String type;
  final String actorId;
  final String entityType;
  final String entityId;
  final DateTime timestamp;
  final Map<String, Object?>? before;
  final Map<String, Object?>? after;
  final Map<String, Object?> metadata;
  final String? idempotencyKey;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'type': type,
      'actor_id': actorId,
      'entity_type': entityType,
      'entity_id': entityId,
      'timestamp': timestamp.toUtc().toIso8601String(),
      if (before != null) 'before': before,
      if (after != null) 'after': after,
      'metadata': metadata,
      if (idempotencyKey != null) 'idempotency_key': idempotencyKey,
    };
  }
}

final class GtexAuditEvent extends AuditEvent {
  const GtexAuditEvent({
    required super.type,
    required super.actorId,
    required super.entityType,
    required super.entityId,
    required super.timestamp,
    super.before,
    super.after,
    super.metadata = const <String, Object?>{},
    super.idempotencyKey,
  });

  factory GtexAuditEvent.majorAction({
    required String type,
    required String actorId,
    required String entityType,
    required String entityId,
    required Map<String, Object?> before,
    required Map<String, Object?> after,
    required DateTime timestamp,
    Map<String, Object?> metadata = const <String, Object?>{},
    String? idempotencyKey,
  }) {
    return GtexAuditEvent(
      type: type,
      actorId: actorId,
      entityType: entityType,
      entityId: entityId,
      timestamp: timestamp,
      before: before,
      after: after,
      metadata: metadata,
      idempotencyKey: idempotencyKey,
    );
  }
}

final class TraderDisputeFiledAuditEvent extends AuditEvent {
  const TraderDisputeFiledAuditEvent({
    required super.actorId,
    required super.entityId,
    required super.timestamp,
    super.before,
    required super.after,
    super.metadata = const <String, Object?>{},
    super.idempotencyKey,
  }) : super(type: 'trader.dispute.filed', entityType: 'trader_dispute');
}
