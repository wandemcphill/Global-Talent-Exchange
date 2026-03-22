import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
      'approved fixture creator sees referral preview without hidden gating',
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
          isAuthenticated: true,
          hasApprovedCreatorAccess: true,
          isReferralRuntimeAvailable: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Community invites'), findsOneWidget);
    expect(find.text('Share your code'), findsWidgets);
    expect(find.text('MAYA-GROWTH'), findsWidgets);
    expect(find.text('@maya_scout'), findsWidgets);
    expect(find.text('Community reward summary'), findsOneWidget);
    expect(find.text('Milestone progress'), findsOneWidget);
    expect(find.text('Creator dashboard'), findsOneWidget);
    expect(find.text('Share creator competition'), findsOneWidget);
  });

  testWidgets(
      'non-creator users see creator-access gating instead of fixture identities',
      (WidgetTester tester) async {
    final ReferralController referralController = ReferralController(
      api: ReferralApi.fixture(),
    );
    final CreatorController creatorController = CreatorController(
      api: CreatorApi.fixture(),
    );
    bool openedCreatorAccess = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ReferralHubScreen(
          referralController: referralController,
          creatorController: creatorController,
          isAuthenticated: true,
          hasApprovedCreatorAccess: false,
          isReferralRuntimeAvailable: false,
          onOpenCreatorAccessRequest: () {
            openedCreatorAccess = true;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Creator access required'), findsOneWidget);
    expect(find.text('MAYA-GROWTH'), findsNothing);
    expect(find.text('@maya_scout'), findsNothing);
    expect(find.text('Creator dashboard'), findsNothing);
    expect(find.text('Share creator competition'), findsNothing);

    await tester.tap(find.text('Request creator access'));
    await tester.pumpAndSettle();

    expect(openedCreatorAccess, isTrue);
  });

  testWidgets(
      'approved users see runtime unavailable state outside fixture mode',
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
          isAuthenticated: true,
          hasApprovedCreatorAccess: true,
          isReferralRuntimeAvailable: false,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Referral runtime unavailable'), findsOneWidget);
    expect(find.text('MAYA-GROWTH'), findsNothing);
    expect(find.text('@maya_scout'), findsNothing);
    expect(find.text('Creator dashboard'), findsNothing);
    expect(find.text('Share creator competition'), findsNothing);
  });
}
