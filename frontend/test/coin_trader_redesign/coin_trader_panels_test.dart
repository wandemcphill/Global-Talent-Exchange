import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/coin_trader_redesign/coin_trader_redesign.dart';

void main() {
  testWidgets('coin trader marketplace panel renders live traders and orders', (
    WidgetTester tester,
  ) async {
    _setDesktopSurface(tester);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1200,
            height: 900,
            child: GtexCoinTraderMarketplacePanel(
              baseUrl: 'https://api.test',
              backendMode: GteBackendMode.live,
              accessToken: 'token',
              isAuthenticated: true,
              api: _FakeCoinTraderApi(),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Lagos OTC Desk'), findsWidgets);
    expect(find.text('My coin orders'), findsOneWidget);
    expect(find.text('Payment Pending'), findsOneWidget);
    expect(find.text('Verified'), findsWidgets);
    expect(find.text('BUY GTEX COIN FROM TRADER'), findsWidgets);
    expect(find.text('SELL GTEX COIN TO TRADER'), findsWidgets);
    expect(find.text('TREASURY TOP-UP'), findsWidgets);
  });

  testWidgets('coin trader dashboard panel renders profile and rate tools', (
    WidgetTester tester,
  ) async {
    _setDesktopSurface(tester);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1000,
            height: 900,
            child: GtexCoinTraderDashboardPanel(
              baseUrl: 'https://api.test',
              backendMode: GteBackendMode.live,
              accessToken: 'token',
              isAuthenticated: true,
              api: _FakeCoinTraderApi(),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Lagos OTC Desk'), findsWidgets);
    expect(find.text('Rates and liquidity'), findsOneWidget);
    expect(find.textContaining('Buy from user 820-890'), findsOneWidget);
    expect(find.text('Trader orders', skipOffstage: false), findsOneWidget);
  });

  testWidgets('coin trader admin screen renders approvals and escrow orders', (
    WidgetTester tester,
  ) async {
    _setDesktopSurface(tester);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1300,
            height: 900,
            child: GtexCoinTraderAdminScreen(
              baseUrl: 'https://api.test',
              backendMode: GteBackendMode.live,
              accessToken: 'token',
              isAdmin: true,
              api: _FakeCoinTraderApi(),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Coin Trader Ops'), findsOneWidget);
    expect(find.text('Admin actions'), findsOneWidget);
    expect(find.text('Escrow orders', skipOffstage: false), findsOneWidget);
    expect(find.text('Resolve'), findsOneWidget);
  });
}

void _setDesktopSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1400, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

class _FakeCoinTraderApi extends GtexCoinTraderApi {
  _FakeCoinTraderApi() : super(client: GtexCoinTraderApi.fixture().client);

  @override
  Future<List<GtexCoinTraderProfile>> listTraders({
    String? countryCode,
    String? coinUnit,
  }) async {
    return <GtexCoinTraderProfile>[_profile()];
  }

  @override
  Future<GtexCoinTraderProfile> fetchMyProfile() async {
    return _profile();
  }

  @override
  Future<List<GtexCoinTradeOrder>> listMyOrders({bool asTrader = false}) async {
    return <GtexCoinTradeOrder>[
      _order(status: asTrader ? 'created' : 'payment_pending'),
    ];
  }

  @override
  Future<List<GtexCoinTraderProfile>> adminListTraders() async {
    return <GtexCoinTraderProfile>[_profile(status: 'applied')];
  }

  @override
  Future<List<GtexCoinTradeOrder>> adminListOrders() async {
    return <GtexCoinTradeOrder>[_order(status: 'disputed')];
  }
}

GtexCoinTraderProfile _profile({String status = 'approved'}) {
  return GtexCoinTraderProfile(
    id: 'trader-profile-1',
    userId: 'trader-user-1',
    displayName: 'Lagos OTC Desk',
    countryCode: 'NG',
    status: status,
    tier: 'gold',
    verificationLevel: 'standard',
    completionRate: 98,
    averageReleaseMinutes: 7,
    rating: 4.8,
    completedVolumeFiat: 12400000,
    disputeScore: 0.2,
    terms: const <String, Object?>{
      'same_name_account_only': true,
      'payment_proof_required': true,
    },
    paymentMethods: const <Map<String, Object?>>[
      <String, Object?>{'label': 'Bank transfer', 'type': 'bank_transfer'},
    ],
    bankAccounts: const <Map<String, Object?>>[
      <String, Object?>{'bank': 'GTBank'},
    ],
    rates: <GtexCoinTraderRate>[
      const GtexCoinTraderRate(
        id: 'rate-1',
        traderProfileId: 'trader-profile-1',
        coinUnit: 'COIN',
        fiatCurrency: 'NGN',
        buyRateFiat: 860,
        sellRateFiat: 920,
        minCoinAmount: 100,
        maxCoinAmount: 50000,
        availableLiquidity: 100000,
        isActive: true,
        spreadFiat: 60,
        treasuryDepositRateFiat: 900,
        treasuryWithdrawalRateFiat: 880,
        minTraderBuyRateFiat: 820,
        maxTraderBuyRateFiat: 890,
        minTraderSellRateFiat: 900,
        maxTraderSellRateFiat: 980,
        maxTraderSpreadFiat: 120,
        governanceStatus: 'compliant',
      ),
    ],
  );
}

GtexCoinTradeOrder _order({required String status}) {
  return GtexCoinTradeOrder(
    id: 'order-1',
    traderProfileId: 'trader-profile-1',
    userId: 'buyer-user-1',
    direction: 'user_buys',
    coinUnit: 'COIN',
    coinAmount: 500,
    quotedRateFiat: 920,
    fiatTotal: 460000,
    fiatCurrency: 'NGN',
    status: status,
    paymentMethod: 'bank_transfer',
    acceptedAt: DateTime(2026, 5, 11, 10),
    paymentWindowExpiresAt: DateTime(2026, 5, 11, 10, 45),
    termsSnapshot: const <String, Object?>{'same_name_account_only': true},
    proof:
        status == 'disputed'
            ? const <String, Object?>{'proof_reference': 'receipt-1'}
            : const <String, Object?>{},
    ledgerRefs:
        status == 'disputed'
            ? const <String, Object?>{
              'escrow_lock_entry_ids': <String>['entry-1'],
            }
            : const <String, Object?>{},
  );
}
