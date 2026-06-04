import 'package:flutter/material.dart';

import '../../data/gte_models.dart';

class LiveNotificationEvent {
  const LiveNotificationEvent({
    required this.id,
    required this.groupKey,
    required this.title,
    required this.body,
    required this.isRead,
    this.occurredAt,
  });

  final String id;
  final String groupKey;
  final String title;
  final String body;
  final bool isRead;
  final DateTime? occurredAt;

  LiveNotificationEvent copyWith({bool? isRead}) {
    return LiveNotificationEvent(
      id: id,
      groupKey: groupKey,
      title: title,
      body: body,
      isRead: isRead ?? this.isRead,
      occurredAt: occurredAt,
    );
  }

  static LiveNotificationEvent? fromPayload(Object? value) {
    final Map<String, Object?> payload = _optionalMap(value);
    if (payload.isEmpty) {
      return null;
    }
    final String? id = GteJson.stringOrNull(payload, const <String>[
      'id',
      'notification_id',
      'notificationId',
      'event_id',
      'eventId',
    ]);
    final String? title = GteJson.stringOrNull(payload, const <String>[
      'title',
      'headline',
      'label',
    ]);
    if (id == null || title == null) {
      return null;
    }
    return LiveNotificationEvent(
      id: id,
      groupKey:
          GteJson.stringOrNull(payload, const <String>[
            'group_key',
            'groupKey',
            'type',
            'topic',
          ]) ??
          'general',
      title: title,
      body:
          GteJson.stringOrNull(payload, const <String>[
            'body',
            'message',
            'detail',
            'description',
          ]) ??
          '',
      isRead: GteJson.boolean(payload, const <String>[
        'is_read',
        'isRead',
        'read',
      ]),
      occurredAt: _dateTimeOrNull(
        GteJson.value(payload, const <String>[
          'occurred_at',
          'occurredAt',
          'created_at',
          'createdAt',
        ]),
      ),
    );
  }
}

class LiveNotificationGroup {
  const LiveNotificationGroup({required this.key, required this.events});

  final String key;
  final List<LiveNotificationEvent> events;

  int get unreadCount =>
      events.where((LiveNotificationEvent event) => !event.isRead).length;
}

class LiveNotificationLogState {
  const LiveNotificationLogState({required this.groups, this.degradedMessage});

  final List<LiveNotificationGroup> groups;
  final String? degradedMessage;

  int get unreadCount => groups.fold<int>(
    0,
    (int total, LiveNotificationGroup group) => total + group.unreadCount,
  );
}

class LiveNotificationLogReducer {
  const LiveNotificationLogReducer();

  LiveNotificationLogState reduce(
    LiveNotificationLogState current,
    Object? backendPayload,
  ) {
    final LiveNotificationEvent? incoming = LiveNotificationEvent.fromPayload(
      backendPayload,
    );
    if (incoming == null) {
      return LiveNotificationLogState(
        groups: current.groups,
        degradedMessage: 'Notification payload missing required fields',
      );
    }
    final Map<String, List<LiveNotificationEvent>> grouped =
        <String, List<LiveNotificationEvent>>{
          for (final LiveNotificationGroup group in current.groups)
            group.key: List<LiveNotificationEvent>.of(group.events),
        };
    final List<LiveNotificationEvent> events =
        grouped[incoming.groupKey] ?? <LiveNotificationEvent>[];
    final int existingIndex = events.indexWhere(
      (LiveNotificationEvent event) => event.id == incoming.id,
    );
    if (existingIndex >= 0) {
      events[existingIndex] = incoming;
    } else {
      events.insert(0, incoming);
    }
    grouped[incoming.groupKey] = events;
    return LiveNotificationLogState(
      groups: grouped.entries
          .map(
            (MapEntry<String, List<LiveNotificationEvent>> entry) =>
                LiveNotificationGroup(
                  key: entry.key,
                  events: List<LiveNotificationEvent>.unmodifiable(entry.value),
                ),
          )
          .toList(growable: false),
    );
  }
}

class LiveNotificationLogView extends StatelessWidget {
  const LiveNotificationLogView({super.key, required this.state});

  final LiveNotificationLogState state;

  @override
  Widget build(BuildContext context) {
    if (state.degradedMessage != null) {
      return Text('Notification log degraded: ${state.degradedMessage}');
    }
    if (state.groups.isEmpty) {
      return const Text('Notification log empty');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: state.groups
          .map((LiveNotificationGroup group) {
            return ExpansionTile(
              title: Text('${group.key} (${group.unreadCount} unread)'),
              children: group.events
                  .map((LiveNotificationEvent event) {
                    return ListTile(
                      leading: Icon(
                        event.isRead
                            ? Icons.mark_email_read_outlined
                            : Icons.mark_email_unread_outlined,
                      ),
                      title: Text(event.title),
                      subtitle: Text(event.body),
                    );
                  })
                  .toList(growable: false),
            );
          })
          .toList(growable: false),
    );
  }
}

Map<String, Object?> _optionalMap(Object? value) {
  try {
    return GteJson.map(value, fallback: const <String, Object?>{});
  } catch (_) {
    return const <String, Object?>{};
  }
}

DateTime? _dateTimeOrNull(Object? value) {
  if (value is DateTime) {
    return value;
  }
  final String text = value?.toString().trim() ?? '';
  return text.isEmpty ? null : DateTime.tryParse(text);
}
