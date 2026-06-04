import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/models/creator_models.dart';
import 'package:gte_frontend/screens/creators/creator_dashboard_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('creator dashboard shows growth and finance summary', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);
    final CreatorController controller = CreatorController(
      api: CreatorApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CreatorDashboardScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Maya Scout'), findsOneWidget);
    expect(find.text('Share code: MAYA-GROWTH'), findsOneWidget);
    expect(find.text('Creator canonical surface'), findsOneWidget);
    expect(find.text('Growth'), findsOneWidget);
    expect(find.text('Finance'), findsOneWidget);
  });

  testWidgets('creator dashboard renders current creator growth copy', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);
    final CreatorController controller = CreatorController(
      api: CreatorApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CreatorDashboardScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Community captain for creator competitions'),
      findsOneWidget,
    );
    expect(find.text('+18 qualified joins this week'), findsOneWidget);
    expect(find.text('39% invite attribution rate'), findsOneWidget);
  });

  testWidgets(
    'creator dashboard finance card prefers dedicated finance payload',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final CreatorController controller = CreatorController(
        api: CreatorApi.fixture(
          financeSummary: const CreatorFinanceSummary(
            currency: 'credits',
            totalGiftIncome: 901,
            totalRewardIncome: 0,
            totalClipIncome: 77,
            totalClipViews: 0,
            monetizedClips: 0,
            viralClipCount: 0,
            totalViralBonus: 0,
            totalReferralBonus: 0,
            totalWeeklyTopCreatorBonus: 0,
            totalWithdrawnGross: 0,
            totalWithdrawalFees: 0,
            totalWithdrawnNet: 0,
            pendingWithdrawals: 0,
            walletBalance: 999,
            walletAvailableBalance: 999,
            walletCurrency: 'credits',
            activeCompetitions: 0,
            attributedSignups: 0,
            qualifiedJoins: 0,
            insights: <String>['Dedicated finance endpoint value'],
          ),
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: CreatorDashboardScreen(controller: controller),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Gift income: 901 Fan Coin'), findsOneWidget);
      expect(find.text('Wallet available: 999 Fan Coin'), findsOneWidget);
      expect(find.text('Reward income: 0 Fan Coin'), findsOneWidget);
    },
  );

  testWidgets('creator dashboard locks studio surfaces for non-creators', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);
    final CreatorController controller = CreatorController(
      api: CreatorApi.fixture(),
    );
    bool openedCreatorAccess = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CreatorDashboardScreen(
          controller: controller,
          hasApprovedCreatorAccess: false,
          onOpenCreatorAccessRequest: () {
            openedCreatorAccess = true;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Creator access required'), findsOneWidget);
    expect(find.text('Growth'), findsNothing);

    await tester.tap(find.text('Request access'));
    await tester.pump();

    expect(openedCreatorAccess, isTrue);
  });

  testWidgets('creator dashboard exposes canonical partial finance state', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);
    final CreatorController controller = CreatorController(
      api: CreatorApi.fixture(
        financeSummary: const CreatorFinanceSummary(
          currency: 'credits',
          totalGiftIncome: 0,
          totalRewardIncome: 0,
          totalClipIncome: 0,
          totalClipViews: 0,
          monetizedClips: 0,
          viralClipCount: 0,
          totalViralBonus: 0,
          totalReferralBonus: 0,
          totalWeeklyTopCreatorBonus: 0,
          totalWithdrawnGross: 0,
          totalWithdrawalFees: 0,
          totalWithdrawnNet: 0,
          pendingWithdrawals: 0,
          walletBalance: 0,
          walletAvailableBalance: 0,
          walletCurrency: 'credits',
          activeCompetitions: 0,
          attributedSignups: 0,
          qualifiedJoins: 0,
          insights: <String>[],
          hasCompleteBackendPayload: false,
          hasWalletPayload: false,
          hasClipEarningsPayload: false,
        ),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CreatorDashboardScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text(
        'Finance payload is partial; wallet values stay marked as provisional.',
      ),
      findsOneWidget,
    );
    expect(
      find.text(
        'Clip earnings endpoint has not returned sponsored clip fields.',
      ),
      findsOneWidget,
    );
  });
}

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1600, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}
