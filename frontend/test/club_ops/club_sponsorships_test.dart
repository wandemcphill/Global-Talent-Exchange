import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/club_ops_fixtures.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:gte_frontend/screens/clubs/club_sponsorship_catalog_screen.dart';
import 'package:gte_frontend/screens/clubs/club_sponsorship_contract_screen.dart';
import 'package:gte_frontend/screens/clubs/club_sponsorships_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'club sponsorships screen shows contracts and opens catalog and detail',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: ClubSponsorshipsScreen(api: ClubOpsApi.fixture()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Sponsorship contracts'), findsOneWidget);
      expect(find.text('North Star Mobility'), findsOneWidget);

      await tester.tap(find.text('North Star Mobility'));
      await tester.pumpAndSettle();
      expect(find.text('Sponsorship contract'), findsOneWidget);
      expect(find.text('Settlement status'), findsOneWidget);

      await tester.pageBack();
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.text('Open catalog'));
      await tester.tap(find.text('Open catalog'));
      await tester.pumpAndSettle();
      expect(find.text('Sponsorship catalog'), findsOneWidget);
      expect(find.text('Principal partnership'), findsOneWidget);

      await tester.pageBack();
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(find.text('Asset slot visibility'), 300);
      expect(find.text('Asset slot visibility'), findsOneWidget);
    },
  );

  testWidgets(
    'catalog screen submits a sponsorship application through the controller',
    (WidgetTester tester) async {
      final _TestClubOpsController controller = _TestClubOpsController();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: ClubSponsorshipCatalogScreen(controller: controller),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Apply').first);
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Sponsor name'),
        'Harbor Energy',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Duration (months)'),
        '6',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Custom copy (optional)'),
        'Harbor Energy Academy',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
      await tester.pumpAndSettle();

      expect(controller.lastDraft, isNotNull);
      expect(controller.lastDraft!.packageCode, 'principal-partnership');
      expect(controller.lastDraft!.sponsorName, 'Harbor Energy');
      expect(controller.lastDraft!.durationMonths, 6);
      expect(controller.lastDraft!.customCopy, 'Harbor Energy Academy');
      expect(
        find.text('Principal partnership submitted for approval.'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'contract screen submits a creative update through the controller',
    (WidgetTester tester) async {
      final _TestClubOpsController controller = _TestClubOpsController();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: ClubSponsorshipContractScreen(
            contractId: 'contract-greenroots',
            controller: controller,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(FilledButton, 'Resubmit creative'), findsOne);

      await tester.tap(find.widgetWithText(FilledButton, 'Resubmit creative'));
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Custom copy'),
        'GreenRoots Academy Fuel',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Logo URL'),
        'https://cdn.example.com/greenroots-refresh.png',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Submit update'));
      await tester.pumpAndSettle();

      expect(controller.lastUpdatedContractId, 'contract-greenroots');
      expect(controller.lastUpdateDraft, isNotNull);
      expect(controller.lastUpdateDraft!.customCopy, 'GreenRoots Academy Fuel');
      expect(
        controller.lastUpdateDraft!.customLogoUrl,
        'https://cdn.example.com/greenroots-refresh.png',
      );
      expect(controller.lastUpdateDraft!.moderationStatus, 'pending');
      expect(controller.lastUpdateDraft!.settleDuePayouts, isFalse);
      expect(
        find.text('Creative update sent for moderation review.'),
        findsOneWidget,
      );
    },
  );

  testWidgets('contract screen posts due payouts through the controller', (
    WidgetTester tester,
  ) async {
    final _TestClubOpsController controller = _TestClubOpsController();

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubSponsorshipContractScreen(
          contractId: 'contract-north-star',
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.widgetWithText(FilledButton, 'Update creative'), findsNothing);
    expect(
      find.widgetWithText(FilledButton, 'Post due payouts'),
      findsOneWidget,
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Post due payouts'));
    await tester.pumpAndSettle();

    expect(controller.lastUpdatedContractId, 'contract-north-star');
    expect(controller.lastUpdateDraft, isNotNull);
    expect(controller.lastUpdateDraft!.settleDuePayouts, isTrue);
    expect(
      find.text(
        'Due sponsorship payouts were checked and any matured installments were posted.',
      ),
      findsOneWidget,
    );
  });
}

class _TestClubOpsController extends ClubOpsController {
  _TestClubOpsController()
    : super(api: ClubOpsApi.fixture(), clubId: 'royal-lagos-fc') {
    sponsorships = fixtureSponsorships(clubId, null);
  }

  SponsorshipApplicationDraft? lastDraft;
  SponsorshipContractUpdateDraft? lastUpdateDraft;
  String? lastUpdatedContractId;

  @override
  Future<SponsorshipContract> applySponsorship({
    required SponsorshipApplicationDraft draft,
  }) async {
    lastDraft = draft;
    final SponsorshipPackage package = sponsorships!.packages.firstWhere(
      (SponsorshipPackage item) => item.code == draft.packageCode,
    );
    return SponsorshipContract(
      id: 'contract-submitted',
      sponsorName: draft.sponsorName,
      packageCode: draft.packageCode,
      packageName: package.name,
      status: SponsorshipContractStatus.pendingApproval,
      totalValue: package.value,
      currency: package.currency,
      payoutSchedule: package.payoutSchedule,
      startDate: DateTime.utc(2026, 4, 13),
      endDate: DateTime.utc(2026, 10, 13),
      assetSlotCodes: const <String>['submission-slot'],
      renewalWindowLabel: 'Submitted for moderation review',
      visibilityLabel: 'Awaiting approval',
      contactName: '',
      moderationState: SponsorModerationState.underReview,
      moderationRequired:
          draft.customCopy != null || draft.customLogoUrl != null,
      settledValue: 0,
      outstandingValue: package.value,
      deliverables: const <String>['Moderation review'],
      notes: const <String>['Application received.'],
      customCopy: draft.customCopy,
      customLogoUrl: draft.customLogoUrl,
    );
  }

  @override
  Future<SponsorshipContract> updateSponsorshipContract({
    required String contractId,
    required SponsorshipContractUpdateDraft draft,
  }) async {
    lastUpdatedContractId = contractId;
    lastUpdateDraft = draft;
    return contractById(contractId)!;
  }
}
