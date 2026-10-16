import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/featured_trophy_shelf.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_redesign_models.dart';
import 'package:gte_frontend/features/club_redesign/presentation/gtex_club_owner_dashboard_v2.dart';
import 'package:gte_frontend/features/club_redesign/widgets/gtex_club_workspace_widgets.dart';
import 'package:gte_frontend/design_lab/gtex_club_player_progression_design_lab_screen.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  group('GTEX Club + Player Identity + Progression UI Primitives', () {
    testWidgets('GtexIdentityHeader renders title, country token, and prestige tier',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: GtexIdentityHeader(
              title: 'Royal Lagos FC',
              subtitle: 'Division 1 • Owner: Amara',
              countryToken: 'NGA',
              prestigeTier: 'Global Powerhouse',
              secondaryTag: 'RLG',
            ),
          ),
        ),
      );

      expect(find.text('Royal Lagos FC'), findsOneWidget);
      expect(find.text('Division 1 • Owner: Amara'), findsOneWidget);
      expect(find.text('NGA'), findsOneWidget);
      expect(find.text('Global Powerhouse'), findsOneWidget);
      expect(find.text('RLG'), findsOneWidget);
    });

    testWidgets('GtexProgressionBar displays normalized percentage and helper text',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: GtexProgressionBar(
              label: 'Academy Level',
              tierLabel: 'Level 4',
              currentStep: 4,
              totalSteps: 10,
              helperText: 'Boosts prospect generation quality',
            ),
          ),
        ),
      );

      expect(find.text('ACADEMY LEVEL'), findsOneWidget);
      expect(find.text('Level 4'), findsOneWidget);
      expect(find.text('4 / 10 (40%)'), findsOneWidget);
      expect(find.text('Boosts prospect generation quality'), findsOneWidget);
    });

    testWidgets('GtexOwnershipIndicatorTile calculates total valuation and shows squad tier',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: GtexOwnershipIndicatorTile(
              name: 'Victor Osimhen',
              quantity: 10,
              sharePriceCoin: 25000,
              contractDurationYears: 4,
              squadTier: 'first_team',
            ),
          ),
        ),
      );

      expect(find.text('Victor Osimhen'), findsOneWidget);
      expect(find.text('10 Shares Held'), findsOneWidget);
      expect(find.text('🪙 250000'), findsOneWidget);
      expect(find.text('4 Years'), findsOneWidget);
      expect(find.text('FIRST TEAM'), findsOneWidget);
    });

    testWidgets('GtexSilverwareShelf renders trophy count and trophy items',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GtexSilverwareShelf(
              title: 'Honours Shelf',
              trophies: const <SilverwareItem>[
                SilverwareItem(
                  name: 'Premier League',
                  category: 'senior',
                  count: 3,
                  latestSeason: '2025/26',
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('HONOURS SHELF'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.text('x3'), findsOneWidget);
      expect(find.text('Premier League'), findsOneWidget);
      expect(find.text('2025/26'), findsOneWidget);
    });
  });

  group('GTEX Production Integration & Responsive Layout Tests', () {
    testWidgets('GtexClubOwnerDashboardV2 renders GtexIdentityHeader and GtexSilverwareShelf across viewports',
        (WidgetTester tester) async {
      final snapshot = GtexClubWorkspaceSnapshot.fixtureSeed(
        clubId: 'royal-lagos-fc',
        clubName: 'Royal Lagos FC',
      );

      for (final Size size in const <Size>[
        Size(390, 844),
        Size(768, 1024),
        Size(1440, 900),
      ]) {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);

        await tester.pumpWidget(
          MaterialApp(
            home: GtexClubOwnerDashboardV2(
              clubId: 'royal-lagos-fc',
              clubName: 'Royal Lagos FC',
              initialSnapshot: snapshot,
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('Royal Lagos FC'), findsWidgets);
        expect(find.byType(GtexIdentityHeader), findsOneWidget);
      }
    });

    testWidgets('GtexClubTrophyGrid integrates GtexSilverwareShelf in Club HQ',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: GtexClubTrophyGrid(
              trophies: <GtexClubTrophy>[
                GtexClubTrophy(
                  id: 't-01',
                  title: 'GTEX Founder Cup',
                  season: '2026',
                  tier: 'Senior',
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.byType(GtexSilverwareShelf), findsOneWidget);
      expect(find.text('GTEX Founder Cup'), findsWidgets);
    });
  });

  group('GTEX Design Lab Compositions', () {
    testWidgets('GtexClubPlayerProgressionDesignLabScreen renders 3 composition tabs across viewports',
        (WidgetTester tester) async {
      for (final Size size in const <Size>[
        Size(390, 844),
        Size(768, 1024),
        Size(1440, 900),
      ]) {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);

        await tester.pumpWidget(
          const MaterialApp(
            home: GtexClubPlayerProgressionDesignLabScreen(),
          ),
        );

        expect(find.text('Design Lab · Club, Player & Progression'), findsOneWidget);
        expect(find.text('Composition 1 · Club Universe'), findsOneWidget);
        expect(find.text('Composition 2 · Player Universe'), findsOneWidget);
        expect(find.text('Composition 3 · Football Identity (Selected)'), findsOneWidget);

        expect(find.text('Royal Lagos FC'), findsOneWidget);
        expect(find.text('CLUB REPUTATION & PRESTIGE'), findsOneWidget);
      }
    });
  });
}
