import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/features/transfer_center/presentation/gtex_transfers_hub_panel.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

Widget _wrapWithNavyTheme(Widget child) {
  return MaterialApp(
    theme: ThemeData.dark(),
    home: Scaffold(body: SingleChildScrollView(child: child)),
  );
}

void main() {
  group('Phase C3 — Transfers Hub & Market Naming (G10)', () {
    test(
      'GtePrimaryDestination.market distinguishes canonical Market label in Shell V3 while preserving legacy label',
      () {
        expect(GtePrimaryDestination.market.canonicalShellLabel, 'Market');
        expect(
          GtePrimaryDestination.market.labelForShell(enableShellV3: true),
          'Market',
        );
        expect(
          GtePrimaryDestination.market.labelForShell(enableShellV3: false),
          'Transfer Hub',
        );
        expect(GtePrimaryDestination.home.accentColor, GtexColors.pitch);
        expect(GtePrimaryDestination.wallet.accentColor, GtexNavyColors.gold500);
      },
    );

    test(
      'TransferHubOfferRecord maps every backend offer status truthfully and disables mutations on terminal states',
      () {
        const List<String> nonTerminalStatuses = <String>[
          'draft',
          'open',
          'countered',
        ];
        for (final String status in nonTerminalStatuses) {
          final TransferHubOfferRecord offer = TransferHubOfferRecord(
            id: 'offer-$status',
            listingId: 'listing-1',
            offerType: 'transfer',
            sellerClubId: 'club-seller',
            bidderClubId: 'club-bidder',
            cashAmount: 1500000,
            status: status,
          );
          expect(
            offer.isTerminal,
            isFalse,
            reason: '$status must not be terminal',
          );
          expect(
            offer.isCompletedTransfer,
            isFalse,
            reason: '$status must never be marked completed',
          );
          expect(
            offer.statusView.label,
            isNot(anyOf('Done', 'Confirmed')),
            reason: '$status must never display as Done or Confirmed',
          );
          expect(offer.lifecycleTimeline, hasLength(4));
        }

        const Map<String, String> terminalExpectedLabels = <String, String>{
          'accepted': 'Confirmed',
          'rejected': 'Rejected',
          'cancelled': 'Cancelled',
          'expired': 'Expired',
        };
        terminalExpectedLabels.forEach((String status, String expectedLabel) {
          final TransferHubOfferRecord offer = TransferHubOfferRecord(
            id: 'offer-$status',
            listingId: 'listing-1',
            offerType: 'transfer',
            sellerClubId: 'club-seller',
            bidderClubId: 'club-bidder',
            cashAmount: 1500000,
            status: status,
            playerId: 'player-9',
            playerName: 'Victor Osimhen',
          );
          expect(offer.isTerminal, isTrue, reason: '$status must be terminal');
          expect(offer.statusView.label, expectedLabel);
          expect(offer.canAccept(activeClubId: 'club-seller'), isFalse);
          expect(offer.canReject(activeClubId: 'club-seller'), isFalse);
          expect(offer.canCounter(activeClubId: 'club-seller'), isFalse);
          expect(offer.canCancel(activeClubId: 'club-bidder'), isFalse);
          expect(offer.isCompletedTransfer, status == 'accepted');
        });
      },
    );

    testWidgets(
      'GtexTransfersHubPanel renders Sporting Transfers banner and switches across all 5 segments',
      (WidgetTester tester) async {
        String? openedPlayerId;
        bool acceptedCalled = false;

        final List<TransferCenterListingRecord> listings =
            <TransferCenterListingRecord>[
              const TransferCenterListingRecord(
                id: 'listing-1',
                playerId: 'player-osimhen',
                playerName: 'Victor Osimhen',
                sellingClubId: 'club-galata',
                currentClubName: 'Galata Lions',
                basePrice: 7500000,
                currentHighestBid: 8200000,
                highestBidderId: 'club-lagos',
                status: 'open',
                watchlistCount: 5,
                bidCount: 3,
                marketSignal: 'High demand striker',
                channel: 'market:listing-1',
                timeRemaining: 3600,
                negotiationId: 'neg-1',
                bidders: <Map<String, Object?>>[],
              ),
            ];

        final List<TransferHubOfferRecord> offers = <TransferHubOfferRecord>[
          const TransferHubOfferRecord(
            id: 'offer-open',
            listingId: 'listing-1',
            offerType: 'transfer',
            sellerClubId: 'club-lagos',
            bidderClubId: 'club-accra',
            cashAmount: 8200000,
            sellOnPercentage: 10,
            status: 'open',
            playerId: 'player-osimhen',
            playerName: 'Victor Osimhen',
            message: 'Initial structured bid',
          ),
          const TransferHubOfferRecord(
            id: 'offer-accepted',
            listingId: 'listing-2',
            offerType: 'loan_to_buy',
            sellerClubId: 'club-lagos',
            bidderClubId: 'club-cairo',
            cashAmount: 4500000,
            status: 'accepted',
            playerId: 'player-lookman',
            playerName: 'Ademola Lookman',
            resolvedAt: '2026-10-20',
          ),
          const TransferHubOfferRecord(
            id: 'offer-expired',
            listingId: 'listing-3',
            offerType: 'transfer',
            sellerClubId: 'club-lagos',
            bidderClubId: 'club-kano',
            cashAmount: 2100000,
            status: 'expired',
            playerId: 'player-boniface',
            playerName: 'Victor Boniface',
          ),
        ];

        final List<TransferNegotiationRecord> negotiations =
            <TransferNegotiationRecord>[
              const TransferNegotiationRecord(
                id: 'neg-active',
                listingId: 'listing-1',
                playerId: 'player-osimhen',
                playerName: 'Victor Osimhen',
                sellingClubId: 'club-galata',
                bidderClubId: 'club-lagos',
                status: 'awaiting_contract_offer',
                wageOfferAmount: 185000,
                contractYears: 4,
                expectedRole: 'Star Striker',
                playerInterestLevel: 'high',
                coachStance: 'approve',
                coachReason: 'Ideal vertical number nine for our system.',
                agentAction: 'counter_offer',
                concerns: <String>['Release clause requested'],
              ),
              const TransferNegotiationRecord(
                id: 'neg-collapsed',
                listingId: 'listing-3',
                playerId: 'player-boniface',
                playerName: 'Victor Boniface',
                sellingClubId: 'club-bayer',
                bidderClubId: 'club-lagos',
                status: 'collapsed',
                contractYears: 3,
              ),
            ];

        final List<TransferShortlistEntryRecord> shortlist =
            <TransferShortlistEntryRecord>[
              const TransferShortlistEntryRecord(
                id: 'short-1',
                clubId: 'club-lagos',
                playerId: 'player-osimhen',
                playerName: 'Victor Osimhen',
                source: 'scouting',
                discoveryScore: 92,
                listingId: 'listing-1',
                estimatedFeeCredits: 7500000,
              ),
            ];

        await tester.pumpWidget(
          _wrapWithNavyTheme(
            GtexTransfersHubPanel(
              activeClubId: 'club-lagos',
              listings: listings,
              offers: offers,
              negotiations: negotiations,
              shortlist: shortlist,
              onAcceptOffer: (_) async {
                acceptedCalled = true;
              },
              onRejectOffer: (_) async {},
              onCounterOffer: (_) async {},
              onCancelOffer: (_) async {},
              onSubmitContractOffer: (_) {},
              onOpenPlayer: (String playerId) {
                openedPlayerId = playerId;
              },
            ),
          ),
        );
        await tester.pumpAndSettle();

        // 1. Sporting Transfers banner is visible
        expect(
          find.byKey(const Key('gtex-sporting-transfers-banner')),
          findsOneWidget,
        );
        expect(
          find.text('Sporting Transfers — Club Roster & Registration'),
          findsOneWidget,
        );

        // 2. Listings segment is active by default
        expect(
          find.byKey(const Key('gtex-transfer-listing-listing-1')),
          findsOneWidget,
        );
        expect(find.text('Victor Osimhen'), findsOneWidget);

        // 3. Switch to Offers segment
        await tester.tap(
          find.byKey(const Key('gtex-transfers-segment-offers')),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-transfer-offer-offer-open')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-offer-timeline-offer-open')),
          findsOneWidget,
        );

        // Active offer has Accept enabled for seller club ('club-lagos')
        final ButtonStyleButton openAcceptBtn = tester
            .widget<ButtonStyleButton>(
              find.byKey(const Key('gtex-offer-accept-offer-open')),
            );
        expect(openAcceptBtn.onPressed, isNotNull);

        // Terminal offers ('accepted' and 'expired') have all mutation actions disabled
        for (final String terminalOfferId in <String>[
          'offer-accepted',
          'offer-expired',
        ]) {
          expect(
            tester
                .widget<ButtonStyleButton>(
                  find.byKey(Key('gtex-offer-accept-$terminalOfferId')),
                )
                .onPressed,
            isNull,
          );
          expect(
            tester
                .widget<ButtonStyleButton>(
                  find.byKey(Key('gtex-offer-counter-$terminalOfferId')),
                )
                .onPressed,
            isNull,
          );
          expect(
            tester
                .widget<ButtonStyleButton>(
                  find.byKey(Key('gtex-offer-reject-$terminalOfferId')),
                )
                .onPressed,
            isNull,
          );
          expect(
            tester
                .widget<ButtonStyleButton>(
                  find.byKey(Key('gtex-offer-cancel-$terminalOfferId')),
                )
                .onPressed,
            isNull,
          );
        }

        // Completed/accepted offer shows 'Open player profile' link
        final Finder openPlayerFinder = find.byKey(
          const Key('gtex-offer-open-player-offer-accepted'),
        );
        await tester.ensureVisible(openPlayerFinder);
        await tester.pumpAndSettle();
        await tester.tap(openPlayerFinder);
        await tester.pumpAndSettle();
        expect(openedPlayerId, 'player-lookman');

        // Tapping Accept on active offer opens GtexConfirmSheet before mutating
        final Finder acceptOfferFinder = find.byKey(
          const Key('gtex-offer-accept-offer-open'),
        );
        await tester.ensureVisible(acceptOfferFinder);
        await tester.pumpAndSettle();
        await tester.tap(acceptOfferFinder);
        await tester.pumpAndSettle();
        expect(find.text('Accept transfer offer?'), findsOneWidget);
        expect(acceptedCalled, isFalse);

        await tester.tap(find.text('Accept offer'));
        await tester.pumpAndSettle();
        expect(acceptedCalled, isTrue);
        if (find.text('Done').evaluate().isNotEmpty) {
          await tester.tap(find.text('Done').last);
          await tester.pumpAndSettle();
        }

        // 4. Switch to Negotiations segment
        final Finder negotiationsChip = find.byKey(
          const Key('gtex-transfers-segment-negotiations'),
        );
        await tester.ensureVisible(negotiationsChip);
        await tester.pumpAndSettle();
        await tester.tap(negotiationsChip);
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-transfer-negotiation-neg-active')),
          findsOneWidget,
        );
        expect(
          tester
              .widget<ButtonStyleButton>(
                find.byKey(
                  const Key('gtex-negotiation-submit-contract-neg-active'),
                ),
              )
              .onPressed,
          isNotNull,
        );
        // Collapsed negotiation disables 'Submit contract offer'
        expect(
          tester
              .widget<ButtonStyleButton>(
                find.byKey(
                  const Key('gtex-negotiation-submit-contract-neg-collapsed'),
                ),
              )
              .onPressed,
          isNull,
        );

        // 5. Switch to Window Bids segment
        await tester.tap(
          find.byKey(const Key('gtex-transfers-segment-window_bids')),
        );
        await tester.pumpAndSettle();
        expect(
          find.text(
            'Select an active transfer window to inspect or place window bids.',
          ),
          findsOneWidget,
        );

        // 6. Switch to Shortlist segment
        await tester.tap(
          find.byKey(const Key('gtex-transfers-segment-shortlist')),
        );
        await tester.pumpAndSettle();
        expect(
          find.text('Recruitment Shortlist & Transfer Basket'),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-transfer-shortlist-short-1')),
          findsOneWidget,
        );
      },
    );
  });
}
