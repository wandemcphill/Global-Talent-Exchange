enum NotificationLogConnectionState { disconnected, connecting, live, degraded }

extension NotificationLogConnectionStateX on NotificationLogConnectionState {
  String get label {
    switch (this) {
      case NotificationLogConnectionState.disconnected:
        return 'Disconnected';
      case NotificationLogConnectionState.connecting:
        return 'Connecting';
      case NotificationLogConnectionState.live:
        return 'Live';
      case NotificationLogConnectionState.degraded:
        return 'Degraded';
    }
  }

  bool get isDegraded => this == NotificationLogConnectionState.degraded;
}

enum NotificationLogEventType {
  snapshot,
  upsert,
  markRead,
  markAllRead,
  remove,
  connectionChanged,
  noop,
}

class NotificationLogItem {
  NotificationLogItem({
    required this.notificationId,
    required this.userId,
    required this.topic,
    required this.templateKey,
    required this.resourceId,
    required this.fixtureId,
    required this.competitionId,
    required this.message,
    required Map<String, Object?> metadata,
    required this.createdAt,
    required this.readAt,
    required bool isRead,
  }) : metadata = Map<String, Object?>.unmodifiable(metadata),
       isRead = isRead || readAt != null;

  final String notificationId;
  final String? userId;
  final String topic;
  final String? templateKey;
  final String? resourceId;
  final String? fixtureId;
  final String? competitionId;
  final String message;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime? readAt;
  final bool isRead;

  bool get isUnread => !isRead;

  String get groupKey {
    return _firstNonEmptyString(<Object?>[
          metadata['group_key'],
          metadata['groupKey'],
          metadata['notification_group'],
          metadata['notificationGroup'],
          topic,
          templateKey,
        ]) ??
        'general';
  }

  String get groupLabel {
    return _firstNonEmptyString(<Object?>[
          metadata['group_label'],
          metadata['groupLabel'],
          metadata['group_name'],
          metadata['groupName'],
        ]) ??
        _labelFromKey(groupKey);
  }

  String get statusLabel => isRead ? 'Read' : 'Unread';

  factory NotificationLogItem.fromBackendJson(
    Object? value, {
    DateTime? fallbackCreatedAt,
  }) {
    final Map<String, Object?> json = _stringMap(value);
    final Map<String, Object?> metadata = _stringMap(json['metadata']);
    final String? groupKey = _firstNonEmptyString(<Object?>[
      json['group_key'],
      json['groupKey'],
    ]);
    final String? groupLabel = _firstNonEmptyString(<Object?>[
      json['group_label'],
      json['groupLabel'],
    ]);
    final Map<String, Object?> resolvedMetadata = <String, Object?>{
      ...metadata,
      if (groupKey != null && !metadata.containsKey('group_key'))
        'group_key': groupKey,
      if (groupLabel != null && !metadata.containsKey('group_label'))
        'group_label': groupLabel,
    };
    final DateTime createdAt =
        _parseDateTime(
          _firstValue(json, <String>['created_at', 'createdAt', 'timestamp']),
        ) ??
        fallbackCreatedAt ??
        DateTime.now().toUtc();
    final DateTime? readAt = _parseDateTime(
      _firstValue(json, <String>['read_at', 'readAt']),
    );
    return NotificationLogItem(
      notificationId:
          _firstNonEmptyString(<Object?>[
            json['notification_id'],
            json['notificationId'],
            json['id'],
          ]) ??
          '',
      userId: _firstNonEmptyString(<Object?>[json['user_id'], json['userId']]),
      topic:
          _firstNonEmptyString(<Object?>[json['topic'], json['channel']]) ??
          'notifications',
      templateKey: _firstNonEmptyString(<Object?>[
        json['template_key'],
        json['templateKey'],
        json['type'],
      ]),
      resourceId: _firstNonEmptyString(<Object?>[
        json['resource_id'],
        json['resourceId'],
      ]),
      fixtureId: _firstNonEmptyString(<Object?>[
        json['fixture_id'],
        json['fixtureId'],
      ]),
      competitionId: _firstNonEmptyString(<Object?>[
        json['competition_id'],
        json['competitionId'],
      ]),
      message:
          _firstNonEmptyString(<Object?>[
            json['message'],
            json['body'],
            json['title'],
          ]) ??
          'New notification',
      metadata: resolvedMetadata,
      createdAt: createdAt,
      readAt: readAt,
      isRead:
          _booleanValue(_firstValue(json, <String>['is_read', 'isRead'])) ??
          readAt != null,
    );
  }

  NotificationLogItem copyWith({
    String? notificationId,
    String? userId,
    String? topic,
    String? templateKey,
    String? resourceId,
    String? fixtureId,
    String? competitionId,
    String? message,
    Map<String, Object?>? metadata,
    DateTime? createdAt,
    DateTime? readAt,
    bool? isRead,
  }) {
    final DateTime? resolvedReadAt = readAt ?? this.readAt;
    return NotificationLogItem(
      notificationId: notificationId ?? this.notificationId,
      userId: userId ?? this.userId,
      topic: topic ?? this.topic,
      templateKey: templateKey ?? this.templateKey,
      resourceId: resourceId ?? this.resourceId,
      fixtureId: fixtureId ?? this.fixtureId,
      competitionId: competitionId ?? this.competitionId,
      message: message ?? this.message,
      metadata: metadata ?? this.metadata,
      createdAt: createdAt ?? this.createdAt,
      readAt: resolvedReadAt,
      isRead: isRead ?? this.isRead || resolvedReadAt != null,
    );
  }
}

class NotificationLogGroup {
  NotificationLogGroup({
    required this.groupKey,
    required this.label,
    required Iterable<NotificationLogItem> notifications,
  }) : notifications = List<NotificationLogItem>.unmodifiable(notifications);

  final String groupKey;
  final String label;
  final List<NotificationLogItem> notifications;

  int get unreadCount =>
      notifications.where((NotificationLogItem item) => item.isUnread).length;

  int get totalCount => notifications.length;
}

class NotificationLogState {
  NotificationLogState({
    Iterable<NotificationLogItem> notifications = const <NotificationLogItem>[],
    this.connectionState = NotificationLogConnectionState.disconnected,
    this.degradedReason,
    this.lastEventAt,
  }) : notifications = List<NotificationLogItem>.unmodifiable(
         _sortNotifications(notifications),
       );

  final List<NotificationLogItem> notifications;
  final NotificationLogConnectionState connectionState;
  final String? degradedReason;
  final DateTime? lastEventAt;

  bool get isEmpty => notifications.isEmpty;

  bool get isDegraded => connectionState.isDegraded;

  int get unreadCount =>
      notifications.where((NotificationLogItem item) => item.isUnread).length;

  List<NotificationLogGroup> get groups {
    final Map<String, List<NotificationLogItem>> grouped =
        <String, List<NotificationLogItem>>{};
    final Map<String, String> labels = <String, String>{};
    for (final NotificationLogItem item in notifications) {
      grouped
          .putIfAbsent(item.groupKey, () => <NotificationLogItem>[])
          .add(item);
      labels.putIfAbsent(item.groupKey, () => item.groupLabel);
    }
    return List<NotificationLogGroup>.unmodifiable(
      grouped.entries.map((MapEntry<String, List<NotificationLogItem>> entry) {
        return NotificationLogGroup(
          groupKey: entry.key,
          label: labels[entry.key] ?? _labelFromKey(entry.key),
          notifications: entry.value,
        );
      }),
    );
  }

  NotificationLogState copyWith({
    Iterable<NotificationLogItem>? notifications,
    NotificationLogConnectionState? connectionState,
    String? degradedReason,
    bool clearDegradedReason = false,
    DateTime? lastEventAt,
  }) {
    return NotificationLogState(
      notifications: notifications ?? this.notifications,
      connectionState: connectionState ?? this.connectionState,
      degradedReason:
          clearDegradedReason ? null : degradedReason ?? this.degradedReason,
      lastEventAt: lastEventAt ?? this.lastEventAt,
    );
  }
}

class NotificationLogEvent {
  const NotificationLogEvent({
    required this.type,
    this.notification,
    this.notifications = const <NotificationLogItem>[],
    this.notificationId,
    this.readAt,
    this.connectionState,
    this.degradedReason,
    this.receivedAt,
    this.rawType,
  });

  final NotificationLogEventType type;
  final NotificationLogItem? notification;
  final List<NotificationLogItem> notifications;
  final String? notificationId;
  final DateTime? readAt;
  final NotificationLogConnectionState? connectionState;
  final String? degradedReason;
  final DateTime? receivedAt;
  final String? rawType;

  static const NotificationLogEvent noop = NotificationLogEvent(
    type: NotificationLogEventType.noop,
  );
}

List<NotificationLogItem> _sortNotifications(
  Iterable<NotificationLogItem> notifications,
) {
  final List<NotificationLogItem> sorted = List<NotificationLogItem>.of(
    notifications,
  );
  sorted.sort((NotificationLogItem a, NotificationLogItem b) {
    final int createdComparison = b.createdAt.compareTo(a.createdAt);
    if (createdComparison != 0) {
      return createdComparison;
    }
    return b.notificationId.compareTo(a.notificationId);
  });
  return sorted;
}

Map<String, Object?> _stringMap(Object? value) {
  if (value is! Map) {
    return <String, Object?>{};
  }
  return <String, Object?>{
    for (final MapEntry<dynamic, dynamic> entry in value.entries)
      entry.key.toString(): entry.value,
  };
}

Object? _firstValue(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    if (json.containsKey(key)) {
      return json[key];
    }
  }
  return null;
}

String? _firstNonEmptyString(List<Object?> values) {
  for (final Object? value in values) {
    final String text = value?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return null;
}

DateTime? _parseDateTime(Object? value) {
  final String? raw = _firstNonEmptyString(<Object?>[value]);
  if (raw == null) {
    return null;
  }
  return DateTime.tryParse(raw);
}

bool? _booleanValue(Object? value) {
  if (value is bool) {
    return value;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  if (normalized == 'true' || normalized == '1' || normalized == 'yes') {
    return true;
  }
  if (normalized == 'false' || normalized == '0' || normalized == 'no') {
    return false;
  }
  return null;
}

String _labelFromKey(String value) {
  final String normalized = value
      .trim()
      .replaceAll('-', ' ')
      .replaceAll('_', ' ');
  if (normalized.isEmpty) {
    return 'General';
  }
  return normalized
      .split(RegExp(r'\s+'))
      .where((String part) => part.isNotEmpty)
      .map((String part) {
        if (part.length == 1) {
          return part.toUpperCase();
        }
        return '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}';
      })
      .join(' ');
}
