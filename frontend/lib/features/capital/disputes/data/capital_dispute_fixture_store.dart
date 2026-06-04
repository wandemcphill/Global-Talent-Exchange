import 'package:gte_frontend/data/gte_models.dart';

typedef CapitalDisputeNotificationSink =
    void Function({
      required String topic,
      required String message,
      String? resourceId,
    });

class CapitalDisputeFixtureStore {
  CapitalDisputeFixtureStore.seeded()
    : _disputes = List<GteDispute>.of(seedDisputes, growable: true),
      _disputeSequence = seedDisputes.length;

  final List<GteDispute> _disputes;
  int _disputeSequence;

  int get openCount =>
      _disputes
          .where(
            (GteDispute dispute) => dispute.status != GteDisputeStatus.closed,
          )
          .length;

  List<GteDispute> listDisputes() {
    return List<GteDispute>.of(_disputes, growable: false);
  }

  GteDispute openDispute({
    required GteDisputeCreateRequest request,
    required GteCurrentUser user,
    required DateTime createdAt,
    required CapitalDisputeNotificationSink notify,
  }) {
    final int sequence = ++_disputeSequence;
    final String disputeId = 'dispute-$sequence';
    final GteDisputeMessage message = GteDisputeMessage(
      id: 'dispute-msg-$sequence-1',
      senderUserId: user.id,
      senderRole: 'user',
      message: request.message,
      attachmentId: request.attachmentId,
      createdAt: createdAt,
    );
    final GteDispute dispute = GteDispute(
      id: disputeId,
      status: GteDisputeStatus.open,
      reference: request.reference,
      resourceType: request.resourceType,
      resourceId: request.resourceId,
      subject: request.subject,
      createdAt: createdAt,
      updatedAt: createdAt,
      lastMessageAt: createdAt,
      userId: user.id,
      userEmail: user.email,
      userFullName: user.fullName,
      userPhoneNumber: user.phoneNumber,
      messages: <GteDisputeMessage>[message],
    );
    _disputes.insert(0, dispute);
    notify(
      topic: 'dispute_opened',
      message: 'Support dispute opened for ${request.reference}.',
      resourceId: dispute.id,
    );
    return dispute;
  }

  GteDispute fetchDispute(String disputeId) {
    return _disputes.firstWhere(
      (GteDispute dispute) => dispute.id == disputeId,
    );
  }

  GteDisputeMessage sendUserMessage({
    required String disputeId,
    required GteDisputeMessageRequest request,
    required GteCurrentUser user,
    required DateTime createdAt,
    required CapitalDisputeNotificationSink notify,
  }) {
    return _sendMessage(
      disputeId: disputeId,
      request: request,
      senderUserId: user.id,
      senderRole: 'user',
      nextStatus: GteDisputeStatus.awaitingAdmin,
      createdAt: createdAt,
      messageIdPrefix: 'dispute-msg',
      notify: notify,
      notificationTopic: 'dispute_opened',
      notificationMessage: 'Your message was sent to support.',
    );
  }

  GteAdminQueuePage<GteDispute> fetchAdminDisputes({
    int limit = 50,
    int offset = 0,
    String? status,
    String? query,
  }) {
    Iterable<GteDispute> items = _disputes;
    if (status != null) {
      final GteDisputeStatus parsed = _disputeStatusFromString(status);
      items = items.where((GteDispute dispute) => dispute.status == parsed);
    }
    if (query != null && query.isNotEmpty) {
      final String needle = query.toLowerCase();
      items = items.where(
        (GteDispute dispute) =>
            dispute.reference.toLowerCase().contains(needle),
      );
    }
    final List<GteDispute> paged = items
        .skip(offset)
        .take(limit)
        .toList(growable: false);
    return GteAdminQueuePage<GteDispute>(
      items: paged,
      total: items.length,
      limit: limit,
      offset: offset,
    );
  }

  GteDisputeMessage sendAdminMessage({
    required String disputeId,
    required GteDisputeMessageRequest request,
    required DateTime createdAt,
    required CapitalDisputeNotificationSink notify,
  }) {
    return _sendMessage(
      disputeId: disputeId,
      request: request,
      senderUserId: 'admin-1',
      senderRole: 'admin',
      nextStatus: GteDisputeStatus.awaitingUser,
      createdAt: createdAt,
      messageIdPrefix: 'dispute-admin-msg',
      notify: notify,
      notificationTopic: 'dispute_reply',
      notificationMessage:
          'Support replied to dispute ${fetchDispute(disputeId).reference}.',
    );
  }

  GteDisputeMessage _sendMessage({
    required String disputeId,
    required GteDisputeMessageRequest request,
    required String senderUserId,
    required String senderRole,
    required GteDisputeStatus nextStatus,
    required DateTime createdAt,
    required String messageIdPrefix,
    required CapitalDisputeNotificationSink notify,
    required String notificationTopic,
    required String notificationMessage,
  }) {
    final int index = _disputes.indexWhere(
      (GteDispute dispute) => dispute.id == disputeId,
    );
    if (index == -1) {
      throw StateError('Dispute not found');
    }
    final GteDispute existing = _disputes[index];
    final GteDisputeMessage message = GteDisputeMessage(
      id: '$messageIdPrefix-$disputeId-${createdAt.millisecondsSinceEpoch}',
      senderUserId: senderUserId,
      senderRole: senderRole,
      message: request.message,
      attachmentId: request.attachmentId,
      createdAt: createdAt,
    );
    final GteDispute updated = GteDispute(
      id: existing.id,
      status: nextStatus,
      reference: existing.reference,
      resourceType: existing.resourceType,
      resourceId: existing.resourceId,
      subject: existing.subject,
      createdAt: existing.createdAt,
      updatedAt: createdAt,
      lastMessageAt: createdAt,
      userId: existing.userId,
      userEmail: existing.userEmail,
      userFullName: existing.userFullName,
      userPhoneNumber: existing.userPhoneNumber,
      messages: <GteDisputeMessage>[...existing.messages, message],
    );
    _disputes[index] = updated;
    notify(
      topic: notificationTopic,
      message: notificationMessage,
      resourceId: updated.id,
    );
    return message;
  }

  static final List<GteDispute> seedDisputes = <GteDispute>[
    GteDispute(
      id: 'dispute-1',
      status: GteDisputeStatus.awaitingAdmin,
      reference: 'DEP-1001',
      resourceType: 'deposit',
      resourceId: 'deposit-1',
      subject: 'Deposit still pending',
      createdAt: DateTime.utc(2026, 3, 11, 9),
      updatedAt: DateTime.utc(2026, 3, 11, 9, 5),
      lastMessageAt: DateTime.utc(2026, 3, 11, 9, 5),
      userId: 'fixture-user',
      userEmail: 'fixture.trader@gte.local',
      userFullName: 'Fixture Trader',
      userPhoneNumber: '+2347000000000',
      messages: <GteDisputeMessage>[
        GteDisputeMessage(
          id: 'dispute-msg-1',
          senderUserId: 'fixture-user',
          senderRole: 'user',
          message: 'I paid 30 minutes ago, please confirm.',
          attachmentId: null,
          createdAt: DateTime.utc(2026, 3, 11, 9, 5),
        ),
      ],
    ),
  ];
}

GteDisputeStatus _disputeStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'awaiting_user':
      return GteDisputeStatus.awaitingUser;
    case 'awaiting_admin':
      return GteDisputeStatus.awaitingAdmin;
    case 'resolved':
      return GteDisputeStatus.resolved;
    case 'closed':
      return GteDisputeStatus.closed;
    case 'open':
    default:
      return GteDisputeStatus.open;
  }
}
