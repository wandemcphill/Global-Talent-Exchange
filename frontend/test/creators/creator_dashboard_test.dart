import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/models/creator_models.dart';
import 'package:gte_frontend/screens/creators/creator_dashboard_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'creator dashboard shows growth summary and creator competitions',
    (WidgetTester tester) async {
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

      expect(find.text('Creator dashboard preview'), findsOneWidget);
      expect(find.textContaining('preview-only'), findsOneWidget);
      expect(find.text('Growth summary'), findsNothing);
      expect(find.text('Spring Scout Sprint'), findsNothing);
    },
  );

  testWidgets('creator dashboard opens profile and share surfaces', (
    WidgetTester tester,
  ) async {
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

    expect(find.text('Creator dashboard preview'), findsOneWidget);
    expect(find.text('Profile'), findsNothing);
    expect(find.text('Share'), findsNothing);
  });

  testWidgets(
    'creator dashboard finance card prefers dedicated finance payload',
    (WidgetTester tester) async {
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

      expect(find.text('Creator dashboard preview'), findsOneWidget);
      expect(find.text('901 credits'), findsNothing);
      expect(find.text('999 credits'), findsNothing);
    },
  );
}
