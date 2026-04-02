import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('creator referral route is preview-only for approved creators', (
    WidgetTester tester,
  ) async {
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

    expect(find.text('Creator referrals preview'), findsOneWidget);
    expect(find.textContaining('preview-only'), findsOneWidget);
    expect(find.text('Sign in'), findsNothing);
  });

  testWidgets('unauthenticated users still get a sign-in action on preview', (
    WidgetTester tester,
  ) async {
    final ReferralController referralController = ReferralController(
      api: ReferralApi.fixture(),
    );
    final CreatorController creatorController = CreatorController(
      api: CreatorApi.fixture(),
    );
    bool openedLogin = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ReferralHubScreen(
          referralController: referralController,
          creatorController: creatorController,
          isAuthenticated: false,
          hasApprovedCreatorAccess: false,
          isReferralRuntimeAvailable: false,
          onOpenLogin: () {
            openedLogin = true;
          },
        ),
      ),
    );

    expect(find.text('Creator referrals preview'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);

    await tester.tap(find.text('Sign in'));
    await tester.pump();

    expect(openedLogin, isTrue);
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

    expect(find.text('Creator referrals preview'), findsOneWidget);
    expect(find.textContaining('preview-only'), findsOneWidget);
    expect(find.text('MAYA-GROWTH'), findsNothing);
    expect(find.text('@maya_scout'), findsNothing);
    expect(find.text('Creator dashboard'), findsNothing);
    expect(find.text('Share creator competition'), findsNothing);
    expect(find.text('Request creator access'), findsNothing);
    expect(openedCreatorAccess, isFalse);
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

    expect(find.text('Creator referrals preview'), findsOneWidget);
    expect(find.textContaining('preview-only'), findsOneWidget);
    expect(find.text('MAYA-GROWTH'), findsNothing);
    expect(find.text('@maya_scout'), findsNothing);
    expect(find.text('Creator dashboard'), findsNothing);
    expect(find.text('Share creator competition'), findsNothing);
  });
}
