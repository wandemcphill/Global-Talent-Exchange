import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/engagement_redesign/engagement_controller.dart';

void main() {
  test('engagement controller exposes demo notifications, conversations, and articles', () {
    final controller = GtexEngagementController();

    expect(controller.loadDemoNotifications(), isNotEmpty);
    expect(controller.loadDemoConversations(), isNotEmpty);
    expect(controller.loadDemoArticles(), isNotEmpty);
    expect(controller.loadDemoNewsroomQueue(), isNotEmpty);
  });
}
