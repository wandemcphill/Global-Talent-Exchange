import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_showroom.dart';
import 'package:gte_frontend/features/owner_console/widgets/gtex_boardroom_delegation_panel.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

Widget _wrapBoardroom(Widget child) {
  return MaterialApp(
    theme: ThemeData.dark(),
    home: Scaffold(
      backgroundColor: GtexColors.navy.bgBase,
      body: SingleChildScrollView(child: child),
    ),
  );
}

void main() {
  group('Phase F1 — Boardroom Delegation & Club Facilities (H3 & H9)', () {
    testWidgets(
      'renders truthful feature-flagged state when clubLegacyEnabled is false',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          _wrapBoardroom(
            const GtexBoardroomDelegationPanel(
              clubLegacyEnabled: false,
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-f1-delegation-flag-off')),
          findsOneWidget,
        );
        expect(
          find.text('Executive Delegation (Club Legacy)'),
          findsOneWidget,
        );
        expect(
          find.text(
            'NPC executive delegation is currently behind the club_legacy launch flag.',
          ),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-f1-facilities-section')),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'renders Who acts next, GM status, GtexPolicyChip, blocked over-cap details, and executes recommendation when clubLegacyEnabled is true',
      (WidgetTester tester) async {
        String? appliedPreset;
        String? executedRecId;
        String? executedIdempotencyKey;

        await tester.pumpWidget(
          _wrapBoardroom(
            GtexBoardroomDelegationPanel(
              clubLegacyEnabled: true,
              gmHired: false,
              policies: const <Map<String, dynamic>>[
                <String, dynamic>{
                  'task_key': 'operating_spend',
                  'label': 'Operating Spend',
                  'mode': 'automatic',
                  'cap_amount': '5,000',
                },
                <String, dynamic>{
                  'task_key': 'sponsor_deals',
                  'label': 'Sponsor Deals',
                  'mode': 'approval_required',
                  'cap_amount': '10,000',
                },
              ],
              recommendations: const <Map<String, dynamic>>[
                <String, dynamic>{
                  'id': 'rec-blocked-1',
                  'title': 'Acquire regional training ground',
                  'status': 'blocked',
                  'amount': '8,500',
                  'cap': '5,000',
                },
                <String, dynamic>{
                  'id': 'rec-open-2',
                  'title': 'Sign front-of-shirt sponsor Harbour Trust',
                  'status': 'recommended',
                  'amount': '4,000',
                },
              ],
              onApplyPreset: (String preset) async {
                appliedPreset = preset;
              },
              onExecuteRecommendation: (
                String recommendationId, {
                String? idempotencyKey,
              }) async {
                executedRecId = recommendationId;
                executedIdempotencyKey = idempotencyKey;
              },
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-f1-who-acts-next')),
          findsOneWidget,
        );
        expect(
          find.textContaining('Who acts next:'),
          findsOneWidget,
        );
        expect(find.byKey(const Key('gtex-f1-gm-status')), findsOneWidget);
        expect(
          find.text(
            'Pre-season delegation tasks require hiring a General Manager (GM).',
          ),
          findsOneWidget,
        );

        // Policy chips
        expect(
          find.byKey(const Key('gtex-f1-policy-operating_spend')),
          findsOneWidget,
        );
        expect(find.text('Automatic <= 5,000 GTX'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-f1-policy-sponsor_deals')),
          findsOneWidget,
        );
        expect(find.text('Approval required'), findsOneWidget);

        // Blocked over-cap recommendation details
        expect(
          find.byKey(const Key('gtex-f1-rec-rec-blocked-1')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-f1-rec-blocked-rec-blocked-1')),
          findsOneWidget,
        );
        expect(
          find.textContaining('8,500 GTX exceeds cap of 5,000 GTX'),
          findsOneWidget,
        );

        //Preset button
        await tester.tap(find.byKey(const Key('gtex-f1-preset-balanced')));
        await tester.pumpAndSettle();
        expect(appliedPreset, 'balanced');

        // Execute open recommendation
        final Finder execBtn = find.byKey(
          const Key('gtex-f1-rec-exec-rec-open-2'),
        );
        await tester.ensureVisible(execBtn);
        await tester.pumpAndSettle();
        await tester.tap(execBtn);
        await tester.pumpAndSettle();
        expect(executedRecId, 'rec-open-2');
        expect(executedIdempotencyKey, 'rec-exec-rec-open-2');
      },
    );

    testWidgets(
      'facility upgrade opens GtexConfirmSheet with global infrastructure broadcast notice',
      (WidgetTester tester) async {
        String? upgradedFacility;
        String? capturedKey;

        await tester.pumpWidget(
          _wrapBoardroom(
            GtexBoardroomDelegationPanel(
              clubLegacyEnabled: true,
              gmHired: true,
              onUpgradeFacility: (
                String facilityKind, {
                String? idempotencyKey,
              }) async {
                upgradedFacility = facilityKind;
                capturedKey = idempotencyKey;
              },
            ),
          ),
        );
        await tester.pumpAndSettle();

        final Finder upgradeStadiumBtn = find.byKey(
          const Key('gtex-f1-facility-upgrade-stadium'),
        );
        await tester.ensureVisible(upgradeStadiumBtn);
        await tester.pumpAndSettle();
        await tester.tap(upgradeStadiumBtn);
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-confirm-financial-box')),
          findsOneWidget,
        );
        expect(
          find.text(GtexBoardroomDelegationPanel.facilityBroadcastNotice),
          findsOneWidget,
        );

        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();

        expect(upgradedFacility, 'stadium');
        expect(capturedKey, 'facility:stadium:lv2');
      },
    );
  });

  group('Phase F1 — Showroom Broadcast & Private Collection Rules (H9)', () {
    testWidgets(
      'ClubLegacyShowroom with requirePurchaseConfirm distinguishes jet global broadcast from watch private collection',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(900, 1400);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.reset);

        final List<Map<String, Object?>> purchases = <Map<String, Object?>>[];

        await tester.pumpWidget(
          MaterialApp(
            theme: ThemeData.dark(),
            home: Scaffold(
              body: ClubLegacyShowroom(
                forceStatic: true,
                requirePurchaseConfirm: true,
                exhibits: const <ShowroomExhibit>[
                  ShowroomExhibit(
                    id: 'catalogue:gtex-jet-harbour',
                    sku: 'gtex-jet-harbour',
                    name: 'Harbour Jet',
                    category: 'jet',
                    price: '12,000',
                    ownershipLabel: 'Not owned',
                    fallbackLabel: 'Static jet card',
                    owned: false,
                  ),
                  ShowroomExhibit(
                    id: 'catalogue:gtex-watch-icon',
                    sku: 'gtex-watch-icon',
                    name: 'Icon Watch',
                    category: 'watch',
                    price: '1,800',
                    ownershipLabel: 'Not owned',
                    fallbackLabel: 'Static watch card',
                    owned: false,
                  ),
                ],
                onAction: (String action, Map<String, Object?> payload) async {
                  if (action == 'purchase') {
                    purchases.add(payload);
                  }
                },
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        // 1. Jet shows 'Public Broadcast · Fleet Aviation' badge and broadcast notice in confirm sheet
        expect(
          find.byKey(const Key('club-showroom-category-badge')),
          findsOneWidget,
        );
        expect(
          find.text('Public Broadcast · Fleet Aviation'),
          findsOneWidget,
        );

        await tester.tap(
          find.byKey(const Key('club-showroom-buy-gtex-jet-harbour')),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-confirm-financial-box')),
          findsOneWidget,
        );
        expect(
          find.text(
            'Private jet purchases broadcast globally to the ticker and newsroom with verified price.',
          ),
          findsOneWidget,
        );

        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();

        expect(purchases, hasLength(1));
        expect(purchases.first['sku'], 'gtex-jet-harbour');

        // Acquisition now has an explicit success receipt before returning
        // to the showroom, so dismiss it before switching exhibits.
        await tester.tap(find.byKey(const Key('club-showroom-arrival-close')));
        await tester.pumpAndSettle();

        // 2. Switch to Watch: shows 'Private Collection · No Global Broadcast' and NO public broadcast notice
        await tester.tap(
          find.byKey(const Key('club-showroom-pick-catalogue:gtex-watch-icon')),
        );
        await tester.pumpAndSettle();

        expect(
          find.text('Private Collection · No Global Broadcast'),
          findsOneWidget,
        );

        await tester.tap(
          find.byKey(const Key('club-showroom-buy-gtex-watch-icon')),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-confirm-financial-box')),
          findsOneWidget,
        );
        expect(
          find.text(
            'Private jet purchases broadcast globally to the ticker and newsroom with verified price.',
          ),
          findsNothing,
        );

        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();

        expect(purchases, hasLength(2));
        expect(purchases.last['sku'], 'gtex-watch-icon');
      },
    );
  });
}
