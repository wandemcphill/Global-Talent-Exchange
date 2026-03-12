import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/screens/referrals/referral_rewards_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('reward history screen keeps community reward copy',
      (WidgetTester tester) async {
    final ReferralController controller = ReferralController(
      api: ReferralApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ReferralRewardsScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Referral rewards'), findsOneWidget);
    expect(find.text('Community reward summary'), findsOneWidget);
    expect(find.text('Milestone progress'), findsOneWidget);
    expect(find.text('Reward history'), findsOneWidget);
    expect(find.text('Welcome bonus'), findsOneWidget);
    expect(find.text('Participation credit'), findsOneWidget);
    expect(find.text('Creator community reward'), findsWidgets);
    expect(find.textContaining('competition credits'), findsWidgets);
  });
}
