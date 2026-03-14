import 'package:gte_frontend/data/gte_models.dart';

class DisputeEngineCase {
  const DisputeEngineCase({
    required this.id,
    required this.userId,
    required this.adminUserId,
    required this.resourceType,
    required this.resourceId,
    required this.reference,
    required this.status,
    required this.subject,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
    required this.lastMessageAt,
    required this.resolvedAt,
    required this.closedAt,
  });

  final String id;
  final String userId;
  final String? adminUserId;
  final String resourceType;
  final String resourceId;
  final String reference;
  final String status;
  final String? subject;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? lastMessageAt;
  final DateTime? resolvedAt;
  final DateTime? closedAt;

  factory DisputeEngineCase.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dispute case');
    return DisputeEngineCase(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      adminUserId:
          GteJson.stringOrNull(json, <String>['admin_user_id', 'adminUserId']),
      resourceType:
          GteJson.string(json, <String>['resource_type', 'resourceType']),
      resourceId:
          GteJson.string(json, <String>['resource_id', 'resourceId']),
      reference: GteJson.string(json, <String>['reference']),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      subject: GteJson.stringOrNull(json, <String>['subject']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
      lastMessageAt: GteJson.dateTimeOrNull(
          json, <String>['last_message_at', 'lastMessageAt']),
      resolvedAt: GteJson.dateTimeOrNull(
          json, <String>['resolved_at', 'resolvedAt']),
      closedAt: GteJson.dateTimeOrNull(json, <String>['closed_at', 'closedAt']),
    );
  }
}

class DisputeEngineMessage {
  const DisputeEngineMessage({
    required this.id,
    required this.disputeId,
    required this.senderUserId,
    required this.senderRole,
    required this.message,
    required this.attachmentId,
    required this.createdAt,
  });

  final String id;
  final String disputeId;
  final String? senderUserId;
  final String senderRole;
  final String message;
  final String? attachmentId;
  final DateTime createdAt;

  factory DisputeEngineMessage.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dispute message');
    return DisputeEngineMessage(
      id: GteJson.string(json, <String>['id']),
      disputeId: GteJson.string(json, <String>['dispute_id', 'disputeId']),
      senderUserId:
          GteJson.stringOrNull(json, <String>['sender_user_id', 'senderUserId']),
      senderRole:
          GteJson.string(json, <String>['sender_role', 'senderRole'], fallback: 'user'),
      message: GteJson.string(json, <String>['message']),
      attachmentId:
          GteJson.stringOrNull(json, <String>['attachment_id', 'attachmentId']),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
    );
  }
}

class DisputeEngineDetail {
  const DisputeEngineDetail({
    required this.dispute,
    required this.messages,
  });

  final DisputeEngineCase dispute;
  final List<DisputeEngineMessage> messages;

  factory DisputeEngineDetail.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'dispute detail');
    return DisputeEngineDetail(
      dispute:
          DisputeEngineCase.fromJson(GteJson.value(json, <String>['dispute'])),
      messages: GteJson.typedList(
        json,
        <String>['messages'],
        DisputeEngineMessage.fromJson,
      ),
    );
  }
}
