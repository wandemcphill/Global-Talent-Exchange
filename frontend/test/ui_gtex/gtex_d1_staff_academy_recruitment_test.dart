import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_growth_redesign/club_growth_redesign.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  group('Phase D1 — Staff, Academy & Recruitment Journeys (H6 / H7)', () {
    late GtexClubGrowthController growthController;

    setUp(() {
      growthController = GtexClubGrowthController(
        api: GtexClubGrowthApi.fixture(),
        clubId: 'fixture-club',
      );
    });

    testWidgets(
      'H7 Staff journey: shows suitability/reputation only when returned, hires via financial confirm sheet, and fires via destructive confirm sheet',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1280, 1200);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await growthController.load();

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: SingleChildScrollView(
                child: GtexClubGrowthJourneyPanel(controller: growthController),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        // staff-agent has suitability & reputation in metadata; staff-scout does not
        expect(
          find.byKey(const Key('gtex-d1-staff-suitability-staff-agent')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-d1-staff-reputation-staff-agent')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-d1-staff-suitability-staff-scout')),
          findsNothing,
        );
        expect(
          find.byKey(const Key('gtex-d1-staff-personality-staff-scout')),
          findsNothing,
        );

        // Hire staff-agent via financial confirm sheet
        await tester.tap(find.byKey(const Key('gtex-d1-hire-staff-staff-agent')));
        await tester.pumpAndSettle();

        expect(find.text('Hire Launch Negotiation Agent'), findsWidgets);
        expect(
          find.byKey(const Key('gtex-confirm-financial-box')),
          findsOneWidget,
        );
        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();

        expect(growthController.dashboard!.activeStaffCount, equals(1));
        expect(
          find.byKey(const Key('gtex-d1-contract-contract-staff-agent')),
          findsOneWidget,
        );

        // Fire staff-agent via destructive confirm sheet requiring a reason
        final Finder fireBtn = find.byKey(
          const Key('gtex-d1-fire-staff-contract-staff-agent'),
        );
        expect(fireBtn, findsOneWidget);
        await tester.tap(fireBtn);
        await tester.pumpAndSettle();

        expect(
          find.text('Terminate Launch Negotiation Agent?'),
          findsOneWidget,
        );
        // Submitting without reason shows validation error
        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();
        expect(
          find.byKey(const Key('gtex-confirm-error-banner')),
          findsOneWidget,
        );

        // Enter audit reason and confirm termination
        await tester.enterText(
          find.byKey(const Key('gtex-confirm-reason-input')),
          'Restructuring scouting & negotiation department',
        );
        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();

        expect(growthController.dashboard!.activeStaffCount, equals(0));
        expect(
          growthController.dashboard!.staffContracts.first.status,
          equals('terminated'),
        );
      },
    );

    testWidgets(
      'H6 Academy journey: generates prospects with server regen portraits, signs youth contract, and promotes to senior squad preserving portrait URL',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1280, 1200);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await growthController.load();

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: SingleChildScrollView(
                child: GtexClubGrowthJourneyPanel(controller: growthController),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(growthController.dashboard!.academyProspects, isEmpty);

        // Step 1: Generate prospects
        await tester.tap(
          find.byKey(const Key('gtex-d1-generate-prospects-btn')),
        );
        await tester.pumpAndSettle();

        expect(growthController.dashboard!.academyProspects.length, equals(3));
        final GtexAcademyProspect firstProspect =
            growthController.dashboard!.academyProspects.first;
        final String? initialPortraitUrl = firstProspect.resolvedPortraitUrl;
        expect(
          initialPortraitUrl,
          equals('/generated-media/newgen/ng-academy-001'),
        );
        expect(
          find.byKey(Key('gtex-d1-prospect-portrait-${firstProspect.id}')),
          findsOneWidget,
        );

        // Step 2: Offer & accept youth contract
        await tester.tap(
          find.byKey(Key('gtex-d1-offer-prospect-${firstProspect.id}')),
        );
        await tester.pumpAndSettle();

        final GtexAcademyProspect signedProspect = growthController
            .dashboard!
            .academyProspects
            .firstWhere((GtexAcademyProspect p) => p.id == firstProspect.id);
        expect(signedProspect.status, equals('youth_signed'));
        expect(signedProspect.promotable, isTrue);

        // Step 3: Promote to senior squad — preserves id & portrait URL
        await tester.tap(
          find.byKey(Key('gtex-d1-promote-prospect-${firstProspect.id}')),
        );
        await tester.pumpAndSettle();

        final GtexAcademyProspect promotedProspect = growthController
            .dashboard!
            .academyProspects
            .firstWhere((GtexAcademyProspect p) => p.id == firstProspect.id);
        expect(promotedProspect.promoted, isTrue);
        expect(promotedProspect.id, equals(firstProspect.id));
        expect(
          promotedProspect.resolvedPortraitUrl,
          equals(initialPortraitUrl),
        );
        expect(
          promotedProspect.seniorPlayerId,
          equals('senior-${firstProspect.id}'),
        );
        expect(
          find.byKey(Key('gtex-d1-promoted-badge-${firstProspect.id}')),
          findsOneWidget,
        );
      },
    );
  });
}
