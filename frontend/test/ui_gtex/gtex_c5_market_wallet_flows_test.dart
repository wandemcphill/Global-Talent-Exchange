import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/gtex_watchlist_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/data/player_card_watchlist_api.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/player_market_redesign/models/gtex_market_browse_models.dart';
import 'package:gte_frontend/features/player_market_redesign/presentation/gtex_market_ownership_desk_screen.dart';
import 'package:gte_frontend/features/player_market_redesign/widgets/gtex_market_selected_player_panel.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/wallet/gtex_wallet_overview_screen_v2.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

GteAuthSession _traderSession() {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'c5-trader-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    'user': <String, Object?>{
      'id': 'c5-trader',
      'email': 'c5-trader@gtex.test',
      'username': 'c5-trader',
      'display_name': 'C5 Trader',
      'role': 'coin_trader',
    },
  });
}

void main() {
  group('Phase C5 — Market & Wallet Status Flows (G16–G17 / G19)', () {
    late GteExchangeController exchangeController;
    late GtexWatchlistController watchlistController;

    setUp(() {
      exchangeController = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      watchlistController = GtexWatchlistController(
        api: FixturePlayerCardWatchlistApi(),
      );
    });

    testWidgets(
      'G16 Market renders Player shares, Cards, Creators sub-tabs and financial market banner',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1440, 900);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        bool walletOpened = false;
        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: GtexMarketOwnershipDeskScreen(
              controller: exchangeController,
              watchlistController: watchlistController,
              initialMode: GtexMarketDeskMode.market,
              onOpenPlayer: (_) {},
              onOpenLogin: () {},
              onOpenWallet: () {
                walletOpened = true;
              },
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-market-financial-banner')),
          findsOneWidget,
        );
        expect(
          find.text('Financial market — not sporting transfers'),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-market-subtab-playerShares')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-market-subtab-cards')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-market-subtab-creators')),
          findsOneWidget,
        );

        // Scroll to and tap Wallet shortcut
        final Finder walletBtn = find.byKey(
          const Key('gtex-market-open-wallet-btn'),
        );
        await tester.ensureVisible(walletBtn);
        await tester.pumpAndSettle();
        await tester.tap(walletBtn);
        await tester.pumpAndSettle();
        expect(walletOpened, isTrue);

        // Switch to Creators sub-tab
        final Finder creatorsTab = find.byKey(
          const Key('gtex-market-subtab-creators'),
        );
        await tester.ensureVisible(creatorsTab);
        await tester.pumpAndSettle();
        await tester.tap(creatorsTab);
        await tester.pumpAndSettle();
        expect(
          find.byKey(const Key('gtex-market-creators-view')),
          findsOneWidget,
        );
        expect(find.text('Creator Share Market'), findsOneWidget);

        // Switch back to Player shares sub-tab
        final Finder sharesTab = find.byKey(
          const Key('gtex-market-subtab-playerShares'),
        );
        await tester.ensureVisible(sharesTab);
        await tester.pumpAndSettle();
        await tester.tap(sharesTab);
        await tester.pumpAndSettle();
        expect(find.text('Transfer Hub'), findsWidgets);
      },
    );

    testWidgets(
      'GtexMarketSelectedPlayerPanel invokes GtexConfirmSheet with idempotency key on share trade',
      (WidgetTester tester) async {
        final GteMarketPlayerListItem rawPlayer = GteMarketPlayerListItem(
          playerId: 'player-101',
          playerName: 'Victor Osimhen',
          position: 'ST',
          nationality: 'Nigeria',
          currentClubName: 'Lagos Stars FC',
          age: 25,
          currentValueCredits: 1850,
          sharePriceCoin: 18.5,
          movementPct: 4.2,
          isTradable: true,
          trendScore: 88.0,
          marketInterestScore: 84,
          averageRating: 7.8,
        );
        final GtexMarketPlayerView player = GtexMarketPlayerView.fromListItem(
          rawPlayer,
        );
        String? confirmedPlayerId;
        String? confirmedIdempotencyKey;

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: Scaffold(
              body: SizedBox(
                width: 440,
                height: 820,
                child: GtexMarketSelectedPlayerPanel(
                  selectedPlayer: player,
                  basketState: const GtexMarketBasketState(
                    <String, GtexMarketPlayerView>{},
                  ),
                  isAuthenticated: true,
                  onOpenLogin: () {},
                  onOpenPlayer: (_) {},
                  onToggleBasket: (_) {},
                  onRemoveFromBasket: (_) {},
                  onCheckout: () {},
                  onQuickTradeConfirmed: (
                    GtexMarketPlayerView p,
                    String idempotencyKey,
                  ) {
                    confirmedPlayerId = p.playerId;
                    confirmedIdempotencyKey = idempotencyKey;
                  },
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final Finder tradeBtn = find.byKey(
          const Key('gtex-market-confirm-share-trade-btn'),
        );
        expect(tradeBtn, findsOneWidget);
        await tester.tap(tradeBtn);
        await tester.pumpAndSettle();

        // Confirm sheet should open with financial terms and idempotency key
        expect(find.text('Buy ${player.name} Shares'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-confirm-financial-box')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-confirm-idempotency-ref')),
          findsOneWidget,
        );

        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();

        expect(confirmedPlayerId, equals(player.playerId));
        expect(confirmedIdempotencyKey, isNotNull);
        expect(
          confirmedIdempotencyKey!.startsWith('mkt-share-${player.playerId}-'),
          isTrue,
        );
      },
    );

    testWidgets(
      'G17 Wallet Overview renders O-02 currency separation banner, KYC posture panel, and status presenter mapping',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1280, 900);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        exchangeController.session = _traderSession();

        await tester.pumpWidget(
          MaterialApp(
            theme: GteShellTheme.build(),
            home: GtexWalletOverviewScreenV2(
              controller: exchangeController,
              backendMode: GteBackendMode.fixture,
            ),
          ),
        );
        for (int pump = 0; pump < 40; pump += 1) {
          await tester.pump(const Duration(milliseconds: 50));
        }

        expect(
          find.byKey(const Key('gtex-wallet-currency-separation-banner')),
          findsOneWidget,
        );
        expect(
          find.textContaining(
            'Main ledger (GTC / FNC) is separate from Owner Console ledger (GTX / FAN)',
          ),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-wallet-kyc-posture-panel')),
          findsOneWidget,
        );
        expect(find.text('Compliance & KYC posture'), findsOneWidget);
      },
    );

    test(
      'GtexStatusPresenter never marks pending / awaiting_payment / payment_submitted / under_review as settled',
      () {
        for (final String raw in <String>[
          'pending',
          'awaiting_payment',
          'payment_submitted',
          'under_review',
        ]) {
          final GtexPresentedStatus desc = GtexStatusPresenter.present(
            raw,
            context: GtexStatusContext.financial,
          );
          expect(
            desc.kind,
            equals(GtexSemanticStatusKind.warning),
            reason: '$raw must map to warning kind, never settled/success',
          );
          expect(desc.isPendingLike, isTrue);
          expect(desc.isTerminal, isFalse);
          expect(desc.label.toLowerCase(), isNot(equals('settled')));
          expect(desc.label.toLowerCase(), isNot(equals('confirmed')));
        }

        final GtexPresentedStatus confirmed = GtexStatusPresenter.present(
          'confirmed',
          context: GtexStatusContext.financial,
        );
        expect(confirmed.kind, equals(GtexSemanticStatusKind.success));
        expect(confirmed.isTerminal, isTrue);
      },
    );
  });
}
