import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/screens/notifications/gte_notifications_screen_v2.dart';

void main() {
  testWidgets('notifications screen renders GTEX notifications title', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: GteNotificationsScreenV2())),
    );

    expect(find.text('GTEX Notifications'), findsOneWidget);
    expect(find.textContaining('Shortlist total changed'), findsWidgets);
  });

  test(
    'notification deep links canonicalize and block unsafe admin routes',
    () {
      GteNotification notificationWith({
        String? route,
        String topic = 'broadcast',
        String? templateKey,
        String? message = 'Broadcast route',
      }) {
        return GteNotification(
          notificationId: 'notification-1',
          userId: 'user-1',
          topic: topic,
          templateKey: templateKey,
          resourceId: null,
          fixtureId: null,
          competitionId: null,
          message: message,
          metadata: <String, Object?>{
            if (route != null) 'deep_link_route': route,
          },
          createdAt: null,
          readAt: null,
          isRead: false,
        );
      }

      expect(
        gtexNotificationDeepLinkRoute(
          notificationWith(route: '/broadcast?competition=final'),
          isAdmin: false,
        ),
        '/broadcast/live?competition=final',
      );
      expect(
        gtexNotificationDeepLinkRoute(
          notificationWith(route: '/admin/launch-control'),
          isAdmin: false,
        ),
        isNull,
      );
      expect(
        gtexNotificationDeepLinkRoute(
          notificationWith(route: 'https://example.test/admin/launch-control'),
          isAdmin: true,
        ),
        isNull,
      );
      expect(
        gtexNotificationDeepLinkRoute(
          notificationWith(
            topic: 'player_cards',
            templateKey: 'card.offer.received',
            message: 'A collectible card offer is waiting.',
          ),
          isAdmin: false,
        ),
        '/player-cards',
      );
      expect(
        gtexNotificationDeepLinkRoute(
          notificationWith(
            topic: 'admin',
            templateKey: 'kill_switch.enabled',
            message: 'A launch-control kill switch has been enabled.',
          ),
          isAdmin: true,
        ),
        '/admin/launch-control',
      );
      expect(
        gtexNotificationDeepLinkRoute(
          notificationWith(
            topic: 'admin',
            templateKey: 'operations.readiness.blocked',
            message: 'Operations readiness blocked.',
          ),
          isAdmin: false,
        ),
        isNull,
      );
    },
  );
}
