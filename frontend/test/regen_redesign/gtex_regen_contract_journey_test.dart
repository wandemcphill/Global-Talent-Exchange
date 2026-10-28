import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_demo_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_wire_models.dart';
import 'package:gte_frontend/features/regen_redesign/widgets/gtex_regen_dossier_panel.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  group('Regen Contract & Recruitment Journey (Agent B4 Integration)', () {
    testWidgets('GtexRegenDossierPanel renders connected journey steps with canonical player ID and honesty', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(420, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      String? openedHubPlayerId;
      String? openedSquadPlayerId;

      final GtexRegenDossier dossier = demoRegenDossier('r-001');

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: GtexRegenDossierPanel(
                result: GtexRegenDossierResult.loaded(dossier),
                onOpenTransfersHub: (String id) => openedHubPlayerId = id,
                onOpenSquad: (String id) => openedSquadPlayerId = id,
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Stage 1: Discovery & Scout Intel
      expect(find.text('Recruitment & Contract Journey'), findsOneWidget);
      expect(find.text('1. Discovery & Scout Intel'), findsOneWidget);
      expect(find.text('Verified Intel'), findsOneWidget);

      // Stage 2: Market Availability
      expect(find.text('2. Market Availability'), findsOneWidget);

      // Stage 3: Transfer Room & Offers
      expect(find.text('3. Transfer Room & Offers'), findsOneWidget);
      expect(find.text('Open Transfers Hub'), findsOneWidget);

      // Stage 4: Contract & Agent Terms
      expect(find.text('4. Contract & Agent Terms'), findsOneWidget);

      // Stage 5: Squad & Match Registration
      expect(find.text('5. Squad & Match Registration'), findsOneWidget);
      expect(find.text('View Squad Room'), findsOneWidget);
      expect(find.text('Awaiting Club Sync'), findsOneWidget);

      // Verify that tapping Transfer Hub CTA forwards the exact canonical ID
      await tester.tap(find.text('Open Transfers Hub'));
      await tester.pumpAndSettle();
      expect(openedHubPlayerId, equals('r-001'));

      // Verify that tapping Squad Room CTA forwards the exact canonical ID
      await tester.tap(find.text('View Squad Room'));
      await tester.pumpAndSettle();
      expect(openedSquadPlayerId, equals('r-001'));
    });

    test('GtexStatusPresenter faithfully maps all intermediate negotiation decision states', () {
      // Pending/Actionable decision loop states
      final GtexPresentedStatus awaiting = GtexStatusPresenter.present(
        'awaiting_contract_offer',
        context: GtexStatusContext.offer,
      );
      expect(awaiting.label, equals('Awaiting Contract Offer'));
      expect(awaiting.kind, equals(GtexSemanticStatusKind.warning));
      expect(awaiting.isTerminal, isFalse);

      final GtexPresentedStatus delayed = GtexStatusPresenter.present(
        'player_delayed',
        context: GtexStatusContext.offer,
      );
      expect(delayed.label, equals('Player Delayed'));
      expect(delayed.kind, equals(GtexSemanticStatusKind.warning));
      expect(delayed.isTerminal, isFalse);

      final GtexPresentedStatus counter = GtexStatusPresenter.present(
        'counter_offer',
        context: GtexStatusContext.offer,
      );
      expect(counter.label, equals('Counter Offer'));
      expect(counter.kind, equals(GtexSemanticStatusKind.warning));
      expect(counter.isTerminal, isFalse);

      // Terminal negative/danger decision states
      final GtexPresentedStatus blocked = GtexStatusPresenter.present(
        'coach_blocked',
        context: GtexStatusContext.offer,
      );
      expect(blocked.label, equals('Coach Blocked'));
      expect(blocked.kind, equals(GtexSemanticStatusKind.danger));
      expect(blocked.isTerminal, isTrue);

      final GtexPresentedStatus collapsed = GtexStatusPresenter.present(
        'collapsed',
        context: GtexStatusContext.offer,
      );
      expect(collapsed.label, equals('Collapsed'));
      expect(collapsed.kind, equals(GtexSemanticStatusKind.danger));
      expect(collapsed.isTerminal, isTrue);

      // Completed transfer state
      final GtexPresentedStatus completed = GtexStatusPresenter.present(
        'completed',
        context: GtexStatusContext.offer,
      );
      expect(completed.label, equals('Done'));
      expect(completed.kind, equals(GtexSemanticStatusKind.success));
      expect(completed.isTerminal, isTrue);
    });

    test('TransferNegotiationRecord models intermediate agent/coach opinions honestly without synthetic registration', () {
      final TransferNegotiationRecord negotiation = TransferNegotiationRecord(
        id: 'neg-101',
        listingId: 'list-501',
        playerId: 'player-b4-canonical',
        playerName: 'Victor Osimhen Regen',
        sellingClubId: 'club-seller',
        bidderClubId: 'club-buyer',
        contractYears: 4,
        status: 'awaiting_contract_offer',
        wageOfferAmount: 85000,
        playerInterestLevel: 'high',
        coachStance: 'warn',
        coachReason: 'High squad competition in primary position',
        agentAction: 'demands_appearance_bonus',
        concerns: const <String>['Squad depth', 'International release'],
      );

      expect(negotiation.playerId, equals('player-b4-canonical'));
      expect(negotiation.isTerminal, isFalse);
      expect(negotiation.coachStance, equals('warn'));
      expect(negotiation.agentAction, equals('demands_appearance_bonus'));
      expect(negotiation.concerns, contains('Squad depth'));
    });
  });
}
