import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('referral hub shows share code, milestones, and creator actions',
      (WidgetTester tester) async {
    final ReferralController referralController = ReferralController(
      api: ReferralApi.fixture(),
    );
    final CreatorController creatorController = CreatorController(
      api: CreatorApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ReferralHubScreen(
          referralController: referralController,
          creatorController: creatorController,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Community invites'), findsOneWidget);
    expect(find.text('Share your code'), findsWidgets);
    expect(find.text('MAYA-GROWTH'), findsWidgets);
    expect(find.text('Community reward summary'), findsOneWidget);
    expect(find.text('Milestone progress'), findsOneWidget);
    expect(find.text('Creator dashboard'), findsOneWidget);
    expect(find.text('Join creator competition'), findsOneWidget);
  });
}
