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
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'community digest',
    );
    return CommunityDigest(
      watchlistCount: GteJson.integer(json, <String>[
        'watchlist_count',
        'watchlistCount',
      ], fallback: 0),
      liveThreadCount: GteJson.integer(json, <String>[
        'live_thread_count',
        'liveThreadCount',
      ], fallback: 0),
      privateThreadCount: GteJson.integer(json, <String>[
        'private_thread_count',
        'privateThreadCount',
      ], fallback: 0),
      unreadHintCount: GteJson.integer(json, <String>[
        'unread_hint_count',
        'unreadHintCount',
      ], fallback: 0),
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
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'watchlist item',
    );
    return CommunityWatchlistItem(
      id: GteJson.string(json, <String>['id']),
      competitionKey: GteJson.string(json, <String>[
        'competition_key',
        'competitionKey',
      ]),
      competitionTitle: GteJson.string(json, <String>[
        'competition_title',
        'competitionTitle',
      ]),
      competitionType: GteJson.string(json, <String>[
        'competition_type',
        'competitionType',
      ], fallback: 'general'),
      notifyOnStory: GteJson.boolean(json, <String>[
        'notify_on_story',
        'notifyOnStory',
      ], fallback: true),
      notifyOnLaunch: GteJson.boolean(json, <String>[
        'notify_on_launch',
        'notifyOnLaunch',
      ], fallback: true),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
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
    this.threadType = 'live_thread',
    this.category = 'general',
    this.body = '',
    this.visibility = 'public',
    this.moderationStatus = 'visible',
    this.trendScore = 0,
    this.lockedAt,
  });

  final String id;
  final String threadKey;
  final String threadType;
  final String category;
  final String? competitionKey;
  final String title;
  final String body;
  final String? createdByUserId;
  final String status;
  final bool pinned;
  final String visibility;
  final String moderationStatus;
  final int trendScore;
  final DateTime? lockedAt;
  final DateTime? lastMessageAt;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory LiveThread.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'live thread');
    return LiveThread(
      id: GteJson.string(json, <String>['id']),
      threadKey: GteJson.string(json, <String>['thread_key', 'threadKey']),
      threadType: GteJson.string(json, <String>[
        'thread_type',
        'threadType',
      ], fallback: 'live_thread'),
      category: GteJson.string(json, <String>['category'], fallback: 'general'),
      competitionKey: GteJson.stringOrNull(json, <String>[
        'competition_key',
        'competitionKey',
      ]),
      title: GteJson.string(json, <String>['title']),
      body: GteJson.string(json, <String>['body'], fallback: ''),
      createdByUserId: GteJson.stringOrNull(json, <String>[
        'created_by_user_id',
        'createdByUserId',
      ]),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      pinned: GteJson.boolean(json, <String>['pinned'], fallback: false),
      visibility: GteJson.string(json, <String>[
        'visibility',
      ], fallback: 'public'),
      moderationStatus: GteJson.string(json, <String>[
        'moderation_status',
        'moderationStatus',
      ], fallback: 'visible'),
      trendScore: GteJson.integer(json, <String>[
        'trend_score',
        'trendScore',
      ], fallback: 0),
      lockedAt: GteJson.dateTimeOrNull(json, <String>['locked_at', 'lockedAt']),
      lastMessageAt: GteJson.dateTimeOrNull(json, <String>[
        'last_message_at',
        'lastMessageAt',
      ]),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
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
    this.parentMessageId,
    this.messageType = 'reply',
    this.moderationStatus = 'visible',
  });

  final String id;
  final String threadId;
  final String authorUserId;
  final String? parentMessageId;
  final String messageType;
  final String body;
  final String visibility;
  final String moderationStatus;
  final int likeCount;
  final int replyCount;
  final DateTime createdAt;
  final Map<String, Object?> metadata;

  factory LiveThreadMessage.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'live thread message',
    );
    return LiveThreadMessage(
      id: GteJson.string(json, <String>['id']),
      threadId: GteJson.string(json, <String>['thread_id', 'threadId']),
      authorUserId: GteJson.string(json, <String>[
        'author_user_id',
        'authorUserId',
      ]),
      parentMessageId: GteJson.stringOrNull(json, <String>[
        'parent_message_id',
        'parentMessageId',
      ]),
      messageType: GteJson.string(json, <String>[
        'message_type',
        'messageType',
      ], fallback: 'reply'),
      body: GteJson.string(json, <String>['body']),
      visibility: GteJson.string(json, <String>[
        'visibility',
      ], fallback: 'public'),
      moderationStatus: GteJson.string(json, <String>[
        'moderation_status',
        'moderationStatus',
      ], fallback: 'visible'),
      likeCount: GteJson.integer(json, <String>[
        'like_count',
        'likeCount',
      ], fallback: 0),
      replyCount: GteJson.integer(json, <String>[
        'reply_count',
        'replyCount',
      ], fallback: 0),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class DiscussionCategory {
  const DiscussionCategory({required this.code, required this.label});

  final String code;
  final String label;

  factory DiscussionCategory.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'discussion category',
    );
    return DiscussionCategory(
      code: GteJson.string(json, <String>['code']),
      label: GteJson.string(json, <String>['label']),
    );
  }
}

class GiftCatalogItem {
  const GiftCatalogItem({
    required this.id,
    required this.code,
    required this.displayName,
    required this.costAmount,
    required this.currencyLabel,
    required this.rarity,
    required this.tier,
    required this.isAwardPack,
    required this.legalStatus,
    this.fallbackDisplayName,
    this.description,
    this.animationKey,
    this.soundKey,
    this.durationMs = 2500,
  });

  final String id;
  final String code;
  final String displayName;
  final String? fallbackDisplayName;
  final String? description;
  final double costAmount;
  final String currencyLabel;
  final String rarity;
  final String tier;
  final String? animationKey;
  final String? soundKey;
  final int durationMs;
  final bool isAwardPack;
  final String legalStatus;

  factory GiftCatalogItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'gift catalog item',
    );
    return GiftCatalogItem(
      id: GteJson.string(json, <String>['id']),
      code: GteJson.string(json, <String>['code', 'key']),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      fallbackDisplayName: GteJson.stringOrNull(json, <String>[
        'fallback_display_name',
        'fallbackDisplayName',
      ]),
      description: GteJson.stringOrNull(json, <String>['description']),
      costAmount: GteJson.number(json, <String>[
        'cost_amount',
        'costAmount',
        'fancoin_price',
      ], fallback: 0),
      currencyLabel: GteJson.string(json, <String>[
        'currency_label',
        'currencyLabel',
      ], fallback: 'Fan Coin'),
      rarity: GteJson.string(json, <String>['rarity'], fallback: 'common'),
      tier: GteJson.string(json, <String>['tier'], fallback: 'standard'),
      animationKey: GteJson.stringOrNull(json, <String>[
        'animation_key',
        'animationKey',
      ]),
      soundKey: GteJson.stringOrNull(json, <String>['sound_key', 'soundKey']),
      durationMs: GteJson.integer(json, <String>[
        'duration_ms',
        'durationMs',
      ], fallback: 2500),
      isAwardPack: GteJson.boolean(json, <String>[
        'is_award_pack',
        'isAwardPack',
      ], fallback: false),
      legalStatus: GteJson.string(json, <String>[
        'legal_status',
        'legalStatus',
      ], fallback: 'safe'),
    );
  }
}

class GiftEvent {
  const GiftEvent._(this.raw);

  final Map<String, Object?> raw;

  factory GiftEvent.fromJson(Object? value) {
    return GiftEvent._(GteJson.map(value, label: 'gift event'));
  }

  String get id => GteJson.string(raw, <String>['id']);
  String get giftKey => GteJson.string(raw, <String>['gift_key', 'giftKey']);
  String get giftDisplayName =>
      GteJson.string(raw, <String>['gift_display_name', 'giftDisplayName']);
  String get rarity =>
      GteJson.string(raw, <String>['rarity'], fallback: 'common');
  String get recipientUserId =>
      GteJson.string(raw, <String>['recipient_user_id', 'recipientUserId']);
  String get currencyLabel => GteJson.string(raw, <String>[
    'currency_label',
    'currencyLabel',
  ], fallback: 'Fan Coin');
  double get grossAmount =>
      GteJson.number(raw, <String>['gross_amount', 'grossAmount']);
  String? get animationKey =>
      GteJson.stringOrNull(raw, <String>['animation_key', 'animationKey']);
  Map<String, Object?> get animationPayload => GteJson.map(
    raw,
    keys: <String>['animation_payload', 'animationPayload'],
    fallback: const <String, Object?>{},
  );
  String get status => GteJson.string(raw, <String>['status']);
  DateTime get createdAt =>
      GteJson.dateTime(raw, <String>['created_at', 'createdAt']);
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
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'private message participant',
    );
    return PrivateMessageParticipant(
      id: GteJson.string(json, <String>['id']),
      threadId: GteJson.string(json, <String>['thread_id', 'threadId']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      isMuted: GteJson.boolean(json, <String>[
        'is_muted',
        'isMuted',
      ], fallback: false),
      lastReadAt: GteJson.dateTimeOrNull(json, <String>[
        'last_read_at',
        'lastReadAt',
      ]),
      joinedAt: GteJson.dateTime(json, <String>['joined_at', 'joinedAt']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
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
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'private thread',
    );
    return PrivateMessageThread(
      id: GteJson.string(json, <String>['id']),
      threadKey: GteJson.string(json, <String>['thread_key', 'threadKey']),
      createdByUserId: GteJson.string(json, <String>[
        'created_by_user_id',
        'createdByUserId',
      ]),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      subject: GteJson.string(json, <String>['subject'], fallback: ''),
      lastMessageAt: GteJson.dateTimeOrNull(json, <String>[
        'last_message_at',
        'lastMessageAt',
      ]),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
      participants: GteJson.typedList(json, <String>[
        'participants',
      ], PrivateMessageParticipant.fromJson),
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
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'private message',
    );
    return PrivateMessage(
      id: GteJson.string(json, <String>['id']),
      threadId: GteJson.string(json, <String>['thread_id', 'threadId']),
      senderUserId: GteJson.string(json, <String>[
        'sender_user_id',
        'senderUserId',
      ]),
      body: GteJson.string(json, <String>['body']),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}
