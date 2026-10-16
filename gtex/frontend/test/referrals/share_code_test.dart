import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/screens/referrals/share_code_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('share code screen exposes copy and channel actions',
      (WidgetTester tester) async {
    final ReferralController controller = ReferralController(
      api: ReferralApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ShareCodeScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Share your code'), findsWidgets);
    expect(find.text('Invite friends'), findsOneWidget);
    expect(find.text('Copy code'), findsOneWidget);
    expect(find.text('Copy link'), findsOneWidget);
    expect(find.text('Share invite'), findsOneWidget);

    await tester.tap(find.text('Share invite').first);
    await tester.pumpAndSettle();

    expect(find.text('WhatsApp'), findsOneWidget);
    expect(find.text('Telegram'), findsOneWidget);
    expect(find.text('System share'), findsOneWidget);
  });
}
