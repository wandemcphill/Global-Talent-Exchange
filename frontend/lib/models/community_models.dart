import 'package:gte_frontend/data/gte_models.dart';

class CommunityDigest {
  const CommunityDigest({
    required this.watchlistCount,
    required this.liveThreadCount,
    required this.privateThreadCount,
    required this.unreadHintCount,
  });

  final int watchlistCount;
  final int liveThreadCount;
  final int privateThreadCount;
  final int unreadHintCount;

  factory CommunityDigest.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'community digest');
    return CommunityDigest(
      watchlistCount: GteJson.integer(
        json,
        <String>['watchlist_count', 'watchlistCount'],
        fallback: 0,
      ),
      liveThreadCount: GteJson.integer(
        json,
        <String>['live_thread_count', 'liveThreadCount'],
        fallback: 0,
      ),
      privateThreadCount: GteJson.integer(
        json,
        <String>['private_thread_count', 'privateThreadCount'],
        fallback: 0,
      ),
      unreadHintCount: GteJson.integer(
        json,
        <String>['unread_hint_count', 'unreadHintCount'],
        fallback: 0,
      ),
    );
  }
}

class CommunityWatchlistItem {
  const CommunityWatchlistItem({
    required this.id,
    required this.competitionKey,
    required this.competitionTitle,
    required this.competitionType,
    required this.notifyOnStory,
    required this.notifyOnLaunch,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String competitionKey;
  final String competitionTitle;
  final String competitionType;
  final bool notifyOnStory;
  final bool notifyOnLaunch;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory CommunityWatchlistItem.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'watchlist item');
    return CommunityWatchlistItem(
      id: GteJson.string(json, <String>['id']),
      competitionKey:
          GteJson.string(json, <String>['competition_key', 'competitionKey']),
      competitionTitle: GteJson.string(
          json, <String>['competition_title', 'competitionTitle']),
      competitionType: GteJson.string(
          json, <String>['competition_type', 'competitionType'],
          fallback: 'general'),
      notifyOnStory: GteJson.boolean(
          json, <String>['notify_on_story', 'notifyOnStory'],
          fallback: true),
      notifyOnLaunch: GteJson.boolean(
          json, <String>['notify_on_launch', 'notifyOnLaunch'],
          fallback: true),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class LiveThread {
  const LiveThread({
    required this.id,
    required this.threadKey,
    required this.competitionKey,
    required this.title,
    required this.createdByUserId,
    required this.status,
    required this.pinned,
    required this.lastMessageAt,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String threadKey;
  final String? competitionKey;
  final String title;
  final String? createdByUserId;
  final String status;
  final bool pinned;
  final DateTime? lastMessageAt;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory LiveThread.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'live thread');
    return LiveThread(
      id: GteJson.string(json, <String>['id']),
      threadKey: GteJson.string(json, <String>['thread_key', 'threadKey']),
      competitionKey: GteJson.stringOrNull(
          json, <String>['competition_key', 'competitionKey']),
      title: GteJson.string(json, <String>['title']),
      createdByUserId:
          GteJson.stringOrNull(json, <String>['created_by_user_id', 'createdByUserId']),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      pinned: GteJson.boolean(json, <String>['pinned'], fallback: false),
      lastMessageAt: GteJson.dateTimeOrNull(
          json, <String>['last_message_at', 'lastMessageAt']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class LiveThreadMessage {
  const LiveThreadMessage({
    required this.id,
    required this.threadId,
    required this.authorUserId,
    required this.body,
    required this.visibility,
    required this.likeCount,
    required this.replyCount,
    required this.createdAt,
    required this.metadata,
  });

  final String id;
  final String threadId;
  final String authorUserId;
  final String body;
  final String visibility;
  final int likeCount;
  final int replyCount;
  final DateTime createdAt;
  final Map<String, Object?> metadata;

  factory LiveThreadMessage.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'live thread message');
    return LiveThreadMessage(
      id: GteJson.string(json, <String>['id']),
      threadId: GteJson.string(json, <String>['thread_id', 'threadId']),
      authorUserId:
          GteJson.string(json, <String>['author_user_id', 'authorUserId']),
      body: GteJson.string(json, <String>['body']),
      visibility:
          GteJson.string(json, <String>['visibility'], fallback: 'public'),
      likeCount: GteJson.integer(json, <String>['like_count', 'likeCount'], fallback: 0),
      replyCount: GteJson.integer(json, <String>['reply_count', 'replyCount'], fallback: 0),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
    );
  }
}

class PrivateMessageParticipant {
  const PrivateMessageParticipant({
    required this.id,
    required this.threadId,
    required this.userId,
    required this.isMuted,
    required this.lastReadAt,
    required this.joinedAt,
    required this.metadata,
  });

  final String id;
  final String threadId;
  final String userId;
  final bool isMuted;
  final DateTime? lastReadAt;
  final DateTime joinedAt;
  final Map<String, Object?> metadata;

  factory PrivateMessageParticipant.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'private message participant');
    return PrivateMessageParticipant(
      id: GteJson.string(json, <String>['id']),
      threadId: GteJson.string(json, <String>['thread_id', 'threadId']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      isMuted:
          GteJson.boolean(json, <String>['is_muted', 'isMuted'], fallback: false),
      lastReadAt: GteJson.dateTimeOrNull(
          json, <String>['last_read_at', 'lastReadAt']),
      joinedAt: GteJson.dateTime(json, <String>['joined_at', 'joinedAt']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
    );
  }
}

class PrivateMessageThread {
  const PrivateMessageThread({
    required this.id,
    required this.threadKey,
    required this.createdByUserId,
    required this.status,
    required this.subject,
    required this.lastMessageAt,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
    required this.participants,
  });

  final String id;
  final String threadKey;
  final String createdByUserId;
  final String status;
  final String subject;
  final DateTime? lastMessageAt;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<PrivateMessageParticipant> participants;

  factory PrivateMessageThread.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'private thread');
    return PrivateMessageThread(
      id: GteJson.string(json, <String>['id']),
      threadKey: GteJson.string(json, <String>['thread_key', 'threadKey']),
      createdByUserId:
          GteJson.string(json, <String>['created_by_user_id', 'createdByUserId']),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      subject: GteJson.string(json, <String>['subject'], fallback: ''),
      lastMessageAt: GteJson.dateTimeOrNull(
          json, <String>['last_message_at', 'lastMessageAt']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
      participants: GteJson.typedList(
        json,
        <String>['participants'],
        PrivateMessageParticipant.fromJson,
      ),
    );
  }
}

class PrivateMessage {
  const PrivateMessage({
    required this.id,
    required this.threadId,
    required this.senderUserId,
    required this.body,
    required this.createdAt,
    required this.metadata,
  });

  final String id;
  final String threadId;
  final String senderUserId;
  final String body;
  final DateTime createdAt;
  final Map<String, Object?> metadata;

  factory PrivateMessage.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'private message');
    return PrivateMessage(
      id: GteJson.string(json, <String>['id']),
      threadId: GteJson.string(json, <String>['thread_id', 'threadId']),
      senderUserId:
          GteJson.string(json, <String>['sender_user_id', 'senderUserId']),
      body: GteJson.string(json, <String>['body']),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
    );
  }
}
