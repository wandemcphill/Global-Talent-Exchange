import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_growth_redesign/club_growth_redesign.dart';
import 'package:gte_frontend/features/club_hub/presentation/club_hub_screen.dart';
import 'package:gte_frontend/features/club_lifecycle_redesign/club_lifecycle_redesign.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  group('Phase C2 — Club Lane Tabs & Re-homing Orphaned Club Screens', () {
    test('GtexClubOwnerSection.canonicalTabs defines the 9 Document G7 tabs', () {
      expect(
        GtexClubOwnerSection.canonicalTabs
            .map((GtexClubOwnerSection s) => s.label)
            .toList(),
        <String>[
          'Overview',
          'Squad',
          'Staff',
          'Academy',
          'Recruitment',
          'Transfers',
          'Finances',
          'Boardroom',
          'Identity',
        ],
      );
    });

    testWidgets(
      'Squad tab re-homes Lineup & Tactics and gates squad lock behind GtexConfirmSheet',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1440, 1200);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GtexClubOperatingDashboard lifecycle =
            await GtexClubLifecycleFixtures.seed().dashboard('club-1');
        int lineupOpens = 0;
        int squadLocks = 0;

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: GtexClubOwnerDashboardV2(
                clubId: 'club-1',
                clubName: 'Lagos Eclipse FC',
                initialSnapshot: GtexClubWorkspaceSnapshot.demo(
                  clubId: 'club-1',
                  clubName: 'Lagos Eclipse FC',
                ),
                lifecycleDashboard: lifecycle,
                initialSection: GtexClubOwnerSection.squad,
                confirmConsequentialLifecycleActions: true,
                onOpenLineup: () => lineupOpens += 1,
                onLockSquadRegistration: () => squadLocks += 1,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('Lineup & squad registration'), findsOneWidget);
        final Finder lineupBtn = find.byKey(
          const Key('gtex-club-open-lineup-btn'),
        );
        expect(lineupBtn, findsOneWidget);
        await tester.tap(lineupBtn);
        await tester.pumpAndSettle();
        expect(lineupOpens, 1);

        final Finder lockBtn = find.byKey(
          const Key('gtex-club-squad-lock-btn'),
        );
        expect(lockBtn, findsOneWidget);
        await tester.tap(lockBtn);
        await tester.pumpAndSettle();

        // Confirm sheet appears before lock executes
        expect(find.text('Lock squad registration?'), findsOneWidget);
        expect(squadLocks, 0);

        await tester.tap(find.text('Lock squad'));
        await tester.pumpAndSettle();
        expect(squadLocks, 1);
      },
    );

    testWidgets(
      'Staff tab re-homes Manager & Coach Market (/coaches) and Recruitment tab bridges to Transfers',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1440, 1200);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GtexClubGrowthDashboard growth =
            await GtexClubGrowthFixtures.seed().dashboard('club-1');
        int coachMarketOpens = 0;

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: GtexClubOwnerDashboardV2(
                clubId: 'club-1',
                clubName: 'Lagos Eclipse FC',
                initialSnapshot: GtexClubWorkspaceSnapshot.demo(
                  clubId: 'club-1',
                  clubName: 'Lagos Eclipse FC',
                ),
                growthDashboard: growth,
                initialSection: GtexClubOwnerSection.staff,
                onOpenCoachMarket: () => coachMarketOpens += 1,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final Finder coachBtn = find.byKey(
          const Key('gtex-club-open-coaches-btn'),
        );
        expect(coachBtn, findsOneWidget);
        await tester.tap(coachBtn);
        await tester.pumpAndSettle();
        expect(coachMarketOpens, 1);

        // Switch to Recruitment tab
        await tester.tap(find.text('Recruitment'));
        await tester.pumpAndSettle();

        expect(find.text('Recruitment & scouting'), findsOneWidget);
        expect(find.text('Discovery to bid pipeline'), findsOneWidget);

        // Tap "Move to Transfers" CTA -> transitions to Transfer room
        await tester.tap(
          find.byKey(const Key('gtex-club-recruitment-to-transfers-btn')),
        );
        await tester.pumpAndSettle();

        expect(find.text('Transfer room'), findsOneWidget);
        expect(find.text('Shortlist basket'), findsOneWidget);
      },
    );

    testWidgets(
      'Finances and Boardroom tabs render unified commercial, status, and policy widgets',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1440, 1400);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final GtexClubGrowthDashboard growth =
            await GtexClubGrowthFixtures.seed().dashboard('club-1');
        final GtexClubOperatingDashboard lifecycle =
            await GtexClubLifecycleFixtures.seed().dashboard('club-1');

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: GtexClubOwnerDashboardV2(
                clubId: 'club-1',
                clubName: 'Lagos Eclipse FC',
                initialSnapshot: GtexClubWorkspaceSnapshot.demo(
                  clubId: 'club-1',
                  clubName: 'Lagos Eclipse FC',
                ),
                growthDashboard: growth,
                lifecycleDashboard: lifecycle,
                initialSection: GtexClubOwnerSection.finances,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('Club finance'), findsOneWidget);
        expect(find.text('Commercial dashboard'), findsOneWidget);
        expect(find.text('Shortlist basket: Arsenal prospects'), findsOneWidget);

        // Switch to Boardroom tab
        await tester.tap(find.text('Boardroom'));
        await tester.pumpAndSettle();

        expect(find.text('Boardroom & executive desk'), findsOneWidget);
        expect(find.text('Delegation & executive policies'), findsOneWidget);
        expect(find.byType(GtexPolicyChip), findsNWidgets(2));
        expect(find.byType(GtexSilverwareShelf), findsOneWidget);
      },
    );

    testWidgets(
      'Decision O-12: ClubHubScreen hides AI assistant by default until reviewed',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: const ClubHubScreen(
              clubId: 'club-1',
              clubName: 'Lagos Eclipse FC',
              isAuthenticated: true,
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('AI assistant'), findsNothing);
      },
    );
  });
}
