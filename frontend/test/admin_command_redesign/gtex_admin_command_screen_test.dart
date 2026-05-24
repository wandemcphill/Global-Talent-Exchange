import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/admin_command_redesign/models/gtex_admin_command_models.dart';
import 'package:gte_frontend/features/admin_command_redesign/presentation/gtex_admin_command_controller.dart';
import 'package:gte_frontend/screens/admin/gtex_admin_command_center_screen_v2.dart';

import 'admin_command_test_fixtures.dart';

void main() {
  testWidgets('admin command center renders core sections', (tester) async {
    final controller = GtexAdminCommandController(
      initialSnapshot: adminCommandTestSnapshot(),
    );

    await tester.pumpWidget(
      MaterialApp(home: GtexAdminCommandCenterScreenV2(controller: controller)),
    );

    expect(find.text('GTEX Admin'), findsWidgets);
    expect(find.text('Command center'), findsWidgets);
    expect(find.text('Users'), findsWidgets);
    expect(find.text('Jackpot'), findsWidgets);
    expect(find.text('Coin Economy'), findsWidgets);
  });
}
