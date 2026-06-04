import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/notifications/notifications.dart';

void main() {
  test(
    'toast hook exposes unread backend upserts without synthetic events',
    () {
      final NotificationLogItem notification =
          NotificationLogItem.fromBackendJson(<String, Object?>{
            'notification_id': 'notif-live-001',
            'topic': 'match',
            'template_key': 'LIVE_MATCH_STARTED',
            'message': 'Lagos Royals v Accra Lions is live.',
            'metadata': <String, Object?>{
              'group_key': 'match:fixture-771',
              'group_label': 'Live Match Ops',
            },
            'created_at': '2026-05-29T12:00:00Z',
            'is_read': false,
          });
      final NotificationLogEvent event = NotificationLogEvent(
        type: NotificationLogEventType.upsert,
        notification: notification,
        receivedAt: DateTime.utc(2026, 5, 29, 12),
        rawType: 'notification_created',
      );

      final NotificationLogToastIntent? intent =
          notificationToastIntentForEvent(event);

      expect(intent, isNotNull);
      expect(intent!.id, 'notification:notif-live-001');
      expect(intent.title, 'Live Match Ops');
      expect(intent.message, 'Lagos Royals v Accra Lions is live.');
      expect(intent.groupKey, 'match:fixture-771');

      final toast = intent.toGtexToastEntry(onAction: () {});
      expect(toast.id, 'notification:notif-live-001');
      expect(toast.title, 'Live Match Ops');
      expect(toast.message, 'Lagos Royals v Accra Lions is live.');
      expect(toast.actionLabel, 'Open');
    },
  );

  test(
    'toast hook ignores snapshots, read updates, and read upserts by default',
    () {
      final NotificationLogItem readNotification =
          NotificationLogItem.fromBackendJson(<String, Object?>{
            'notification_id': 'notif-read-001',
            'topic': 'wallet',
            'message': 'Withdrawal withdrawal-12 was approved.',
            'created_at': '2026-05-29T12:04:00Z',
            'read_at': '2026-05-29T12:04:30Z',
            'is_read': true,
          });

      expect(
        notificationToastIntentForEvent(
          NotificationLogEvent(
            type: NotificationLogEventType.upsert,
            notification: readNotification,
          ),
        ),
        isNull,
      );
      expect(
        notificationToastIntentForEvent(
          NotificationLogEvent(
            type: NotificationLogEventType.snapshot,
            notifications: <NotificationLogItem>[readNotification],
          ),
        ),
        isNull,
      );
      expect(
        notificationToastIntentForEvent(
          const NotificationLogEvent(
            type: NotificationLogEventType.markRead,
            notificationId: 'notif-read-001',
          ),
        ),
        isNull,
      );
    },
  );
}
