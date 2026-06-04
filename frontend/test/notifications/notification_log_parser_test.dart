import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/notifications/notifications.dart';

void main() {
  test('parses persisted backend notification payload as unread log item', () {
    final NotificationLogEvent? event = parseNotificationLogBackendMessage(
      _backendNotificationPayload(),
      receivedAt: DateTime.utc(2026, 5, 29, 12),
    );

    expect(event, isNotNull);
    expect(event!.type, NotificationLogEventType.upsert);
    expect(event.notification!.notificationId, 'notif-live-001');
    expect(event.notification!.topic, 'match');
    expect(event.notification!.templateKey, 'LIVE_MATCH_STARTED');
    expect(event.notification!.message, 'Lagos Royals v Accra Lions is live.');
    expect(event.notification!.isUnread, isTrue);
    expect(event.notification!.groupKey, 'match:fixture-771');
    expect(event.notification!.groupLabel, 'Live Match Ops');
  });

  test('parses websocket snapshot envelope with explicit backend rows', () {
    final String message = jsonEncode(<String, Object?>{
      'type': 'notifications_snapshot',
      'topic': 'notifications',
      'sent_at': '2026-05-29T12:05:00Z',
      'payload': <String, Object?>{
        'notifications': <Object?>[
          _backendNotificationPayload(),
          <String, Object?>{
            'notification_id': 'notif-wallet-002',
            'user_id': 'user-1',
            'topic': 'wallet',
            'template_key': 'WITHDRAWAL_APPROVED',
            'resource_id': 'withdrawal-12',
            'fixture_id': null,
            'competition_id': null,
            'message': 'Withdrawal withdrawal-12 was approved.',
            'metadata': <String, Object?>{
              'group_key': 'wallet:payouts',
              'group_label': 'Wallet Payouts',
            },
            'created_at': '2026-05-29T12:04:00Z',
            'read_at': '2026-05-29T12:04:30Z',
            'is_read': true,
          },
        ],
        'unread_count': 1,
      },
    });

    final NotificationLogEvent? event = parseNotificationLogBackendMessage(
      message,
    );

    expect(event, isNotNull);
    expect(event!.type, NotificationLogEventType.snapshot);
    expect(event.notifications, hasLength(2));
    expect(event.notifications.first.notificationId, 'notif-live-001');
    expect(event.notifications.last.isRead, isTrue);
  });

  test('parses read and degraded websocket events', () {
    final NotificationLogEvent? readEvent = parseNotificationLogBackendMessage(
      <String, Object?>{
        'type': 'notification_read',
        'topic': 'notifications',
        'payload': <String, Object?>{
          'notification_id': 'notif-live-001',
          'read_at': '2026-05-29T12:10:00Z',
        },
      },
    );
    final NotificationLogEvent? degradedEvent =
        parseNotificationLogBackendMessage(<String, Object?>{
          'type': 'notification_stream_degraded',
          'topic': 'notifications',
          'payload': <String, Object?>{
            'status': 'degraded',
            'reason': 'websocket backlog exceeded live window',
          },
        });

    expect(readEvent, isNotNull);
    expect(readEvent!.type, NotificationLogEventType.markRead);
    expect(readEvent.notificationId, 'notif-live-001');
    expect(readEvent.readAt, DateTime.parse('2026-05-29T12:10:00Z'));

    expect(degradedEvent, isNotNull);
    expect(degradedEvent!.type, NotificationLogEventType.connectionChanged);
    expect(
      degradedEvent.connectionState,
      NotificationLogConnectionState.degraded,
    );
    expect(degradedEvent.degradedReason, contains('websocket backlog'));
  });
}

Map<String, Object?> _backendNotificationPayload() {
  return <String, Object?>{
    'notification_id': 'notif-live-001',
    'user_id': 'user-1',
    'topic': 'match',
    'template_key': 'LIVE_MATCH_STARTED',
    'resource_id': 'match-771',
    'fixture_id': 'fixture-771',
    'competition_id': 'competition-9',
    'message': 'Lagos Royals v Accra Lions is live.',
    'metadata': <String, Object?>{
      'group_key': 'match:fixture-771',
      'group_label': 'Live Match Ops',
      'source': 'match_engine',
    },
    'created_at': '2026-05-29T12:00:00Z',
    'read_at': null,
    'is_read': false,
  };
}
