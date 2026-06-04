import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/notifications/live_notification_log.dart';

void main() {
  test('notification reducer groups backend events and tracks unread', () {
    const LiveNotificationLogReducer reducer = LiveNotificationLogReducer();
    final LiveNotificationLogState state = reducer.reduce(
      const LiveNotificationLogState(groups: <LiveNotificationGroup>[]),
      <String, Object?>{
        'id': 'evt-1',
        'group_key': 'match:1',
        'title': 'Goal alert',
        'body': 'Backend notification event.',
        'is_read': false,
      },
    );

    expect(state.groups.single.key, 'match:1');
    expect(state.unreadCount, 1);
  });

  test('notification reducer marks malformed payloads degraded', () {
    final LiveNotificationLogState state = const LiveNotificationLogReducer()
        .reduce(
          const LiveNotificationLogState(groups: <LiveNotificationGroup>[]),
          <String, Object?>{'group_key': 'match:1'},
        );

    expect(state.degradedMessage, isNotNull);
  });

  testWidgets('notification log view renders grouped unread backend events', (
    WidgetTester tester,
  ) async {
    const LiveNotificationEvent event = LiveNotificationEvent(
      id: 'evt-1',
      groupKey: 'match:1',
      title: 'Goal alert',
      body: 'Backend notification event.',
      isRead: false,
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: LiveNotificationLogView(
            state: LiveNotificationLogState(
              groups: <LiveNotificationGroup>[
                LiveNotificationGroup(
                  key: 'match:1',
                  events: <LiveNotificationEvent>[event],
                ),
              ],
            ),
          ),
        ),
      ),
    );

    expect(find.text('match:1 (1 unread)'), findsOneWidget);
    await tester.tap(find.text('match:1 (1 unread)'));
    await tester.pumpAndSettle();
    expect(find.text('Goal alert'), findsOneWidget);
  });
}
