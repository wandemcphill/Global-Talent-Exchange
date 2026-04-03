import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('creator referral route shows live creator community data', (
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
    await tester.pumpAndSettle();

    expect(find.text('Maya Scout community desk'), findsOneWidget);
    expect(find.text('Share code: MAYA-GROWTH'), findsOneWidget);
    expect(find.text('Performance snapshot'), findsOneWidget);
    expect(find.text('Sign in'), findsNothing);
  });

  testWidgets('unauthenticated users still get a sign-in action', (
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

    expect(find.text('Sign in to open community tools'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);

    await tester.tap(find.text('Sign in'));
    await tester.pump();

    expect(openedLogin, isTrue);
  });

  testWidgets(
    'non-creator users see creator-access gating instead of community data',
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

      expect(find.text('Apply for creator access'), findsOneWidget);
      expect(find.text('Request access'), findsOneWidget);
      expect(find.text('MAYA-GROWTH'), findsNothing);
      expect(find.text('Maya Scout community desk'), findsNothing);

      await tester.tap(find.text('Request access'));
      await tester.pump();

      expect(openedCreatorAccess, isTrue);
    },
  );

  testWidgets(
    'approved users still render creator tools when fixture data is present',
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

      expect(find.text('Maya Scout community desk'), findsOneWidget);
      expect(find.text('Share code: MAYA-GROWTH'), findsOneWidget);
      expect(find.text('Performance snapshot'), findsOneWidget);
      expect(find.text('Referral runtime is not enabled yet'), findsNothing);
    },
  );
}
