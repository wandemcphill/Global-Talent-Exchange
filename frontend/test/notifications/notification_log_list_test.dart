import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/notifications/notifications.dart';

void main() {
  testWidgets(
    'notification log list renders groups, unread labels, and degraded state',
    (WidgetTester tester) async {
      final NotificationLogState state = NotificationLogState(
        connectionState: NotificationLogConnectionState.degraded,
        degradedReason: 'websocket backlog exceeded live window',
        notifications: <NotificationLogItem>[
          NotificationLogItem.fromBackendJson(<String, Object?>{
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
            },
            'created_at': '2026-05-29T12:00:00Z',
            'read_at': null,
            'is_read': false,
          }),
          NotificationLogItem.fromBackendJson(<String, Object?>{
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
          }),
        ],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NotificationLogList(
              state: state,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
            ),
          ),
        ),
      );

      expect(find.text('Notification stream degraded'), findsOneWidget);
      expect(
        find.text('websocket backlog exceeded live window'),
        findsOneWidget,
      );
      expect(find.text('Live Match Ops'), findsOneWidget);
      expect(find.text('Wallet Payouts'), findsOneWidget);
      expect(find.text('1 unread'), findsOneWidget);
      expect(find.text('All read'), findsOneWidget);
      expect(find.text('Unread'), findsOneWidget);
      expect(find.text('Read'), findsOneWidget);
      expect(find.text('Lagos Royals v Accra Lions is live.'), findsOneWidget);
      expect(
        find.text('Withdrawal withdrawal-12 was approved.'),
        findsOneWidget,
      );
    },
  );

  testWidgets('notification log list renders empty backend state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: NotificationLogList(
            state: NotificationLogState(),
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
          ),
        ),
      ),
    );

    expect(find.text('No notifications'), findsOneWidget);
    expect(
      find.text('Backend notifications will appear here after delivery.'),
      findsOneWidget,
    );
  });
}
