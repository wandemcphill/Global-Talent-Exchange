import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/screens/admin/gtex_admin_command_center_screen_v2.dart';

void main() {
  testWidgets('admin command center renders core sections', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexAdminCommandCenterScreenV2()),
    );

    expect(find.text('GTEX Admin'), findsWidgets);
    expect(find.text('Command center'), findsWidgets);
    expect(find.text('Users'), findsWidgets);
    expect(find.text('Jackpot'), findsWidgets);
    expect(find.text('Coin Economy'), findsWidgets);
  });
}
