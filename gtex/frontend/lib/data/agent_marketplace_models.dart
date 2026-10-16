import 'gte_models.dart';

class GteConversationPlayerContext {
  const GteConversationPlayerContext({
    required this.playerId,
    required this.playerName,
    required this.position,
    required this.currentClubName,
    required this.askingType,
    required this.marketplaceNote,
    required this.agentName,
  });

  final String playerId;
  final String playerName;
  final String? position;
  final String? currentClubName;
  final String askingType;
  final String? marketplaceNote;
  final String agentName;

  factory GteConversationPlayerContext.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'conversation player context');
    return GteConversationPlayerContext(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      position: GteJson.stringOrNull(json, <String>['position']),
      currentClubName: GteJson.stringOrNull(
        json,
        <String>['current_club_name', 'currentClubName'],
      ),
      askingType: GteJson.string(
        json,
        <String>['asking_type', 'askingType'],
        fallback: 'transfer',
      ),
      marketplaceNote: GteJson.stringOrNull(
        json,
        <String>['marketplace_note', 'marketplaceNote'],
      ),
      agentName: GteJson.string(json, <String>['agent_name', 'agentName']),
    );
  }
}

class GteConversationParticipant {
  const GteConversationParticipant({
    required this.userId,
    required this.displayName,
    required this.role,
    required this.lastReadAt,
  });

  final String userId;
  final String displayName;
  final String role;
  final DateTime? lastReadAt;

  factory GteConversationParticipant.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'conversation participant');
    return GteConversationParticipant(
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      displayName:
          GteJson.string(json, <String>['display_name', 'displayName']),
      role: GteJson.string(json, <String>['role'], fallback: 'scout'),
      lastReadAt: GteJson.dateTimeOrNull(
        json,
        <String>['last_read_at', 'lastReadAt'],
      ),
    );
  }
}

class GteConversationMessage {
  const GteConversationMessage({
    required this.id,
    required this.conversationId,
    required this.senderId,
    required this.senderName,
    required this.senderRole,
    required this.message,
    required this.createdAt,
  });

  final String id;
  final String conversationId;
  final String senderId;
  final String senderName;
  final String senderRole;
  final String message;
  final DateTime createdAt;

  factory GteConversationMessage.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'conversation message');
    return GteConversationMessage(
      id: GteJson.string(json, <String>['id']),
      conversationId: GteJson.string(
        json,
        <String>['conversation_id', 'conversationId'],
      ),
      senderId: GteJson.string(json, <String>['sender_id', 'senderId']),
      senderName: GteJson.string(json, <String>['sender_name', 'senderName']),
      senderRole: GteJson.string(json, <String>['sender_role', 'senderRole']),
      message: GteJson.string(json, <String>['message']),
      createdAt: GteJson.dateTimeOrNull(
            json,
            <String>['created_at', 'createdAt'],
          ) ??
          DateTime.now().toUtc(),
    );
  }
}

class GteConversationSummary {
  const GteConversationSummary({
    required this.id,
    required this.player,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.lastMessageAt,
    required this.latestMessagePreview,
    required this.unreadCount,
    required this.participants,
  });

  final String id;
  final GteConversationPlayerContext player;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? lastMessageAt;
  final String? latestMessagePreview;
  final int unreadCount;
  final List<GteConversationParticipant> participants;

  GteConversationParticipant? participantFor(String userId) {
    for (final GteConversationParticipant participant in participants) {
      if (participant.userId == userId) {
        return participant;
      }
    }
    return null;
  }

  factory GteConversationSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'conversation summary');
    return GteConversationSummary(
      id: GteJson.string(json, <String>['id']),
      player: GteConversationPlayerContext.fromJson(
        GteJson.value(json, <String>['player']),
      ),
      status: GteJson.string(json, <String>['status'], fallback: 'active'),
      createdAt: GteJson.dateTimeOrNull(
            json,
            <String>['created_at', 'createdAt'],
          ) ??
          DateTime.now().toUtc(),
      updatedAt: GteJson.dateTimeOrNull(
            json,
            <String>['updated_at', 'updatedAt'],
          ) ??
          DateTime.now().toUtc(),
      lastMessageAt: GteJson.dateTimeOrNull(
        json,
        <String>['last_message_at', 'lastMessageAt'],
      ),
      latestMessagePreview: GteJson.stringOrNull(
        json,
        <String>['latest_message_preview', 'latestMessagePreview'],
      ),
      unreadCount:
          GteJson.integer(json, <String>['unread_count', 'unreadCount']),
      participants: GteJson.typedList(
        json,
        <String>['participants'],
        GteConversationParticipant.fromJson,
      ),
    );
  }
}

class GteConversationDetail {
  const GteConversationDetail({
    required this.conversation,
    required this.messages,
  });

  final GteConversationSummary conversation;
  final List<GteConversationMessage> messages;

  factory GteConversationDetail.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'conversation detail');
    return GteConversationDetail(
      conversation: GteConversationSummary.fromJson(
        GteJson.value(json, <String>['conversation']),
      ),
      messages: GteJson.typedList(
        json,
        <String>['messages'],
        GteConversationMessage.fromJson,
      ),
    );
  }
}

String gteAskingTypeLabel(String? askingType) {
  switch (askingType?.trim().toLowerCase()) {
    case 'loan':
      return 'Loan';
    case 'trial':
      return 'Trial';
    case 'transfer':
    default:
      return 'Transfer';
  }
}
