import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_funding_flow_screen.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_wallet_overview_screen.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_withdrawal_flow_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('wallet overview renders canonical KoraPay/manual restrictions', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(_WalletRestrictionApi()),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteWalletOverviewScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Club Wallet'), findsOneWidget);
    expect(find.text('Club funds'), findsOneWidget);
    expect(find.text('1200 GTEX Coin'), findsWidgets);
    expect(find.text('250 GTEX Coin'), findsWidgets);
    expect(find.text('Locked funds: 250 GTEX Coin'), findsOneWidget);
    expect(find.text('Pending transfer escrow'), findsOneWidget);
    expect(
      find.text(
        'Transfer bid reservations: 250.0000 coin | Ref transfer_bid:bid-123',
      ),
      findsOneWidget,
    );

    expect(find.text('Current restrictions'), findsOneWidget);
    expect(
      find.text('Accept the updated wallet terms before deposits resume.'),
      findsOneWidget,
    );
    expect(find.text('DEPOSIT RAIL'), findsOneWidget);
    expect(find.text('Manual bank transfer review'), findsWidgets);
    expect(find.text('KORAPAY'), findsOneWidget);
    expect(find.text('BANK TRANSFER'), findsOneWidget);
    expect(find.text('Ready'), findsNWidgets(2));
    expect(
      find.textContaining('Instant provider status: KoraPay Ready.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Manual transfer status: Ready.'),
      findsOneWidget,
    );
    expect(
      find.textContaining(
        'Pay'
        'stack',
      ),
      findsNothing,
    );

    expect(find.text('Transaction History'), findsWidgets);
    expect(find.text('Credit | Verified'), findsOneWidget);
    expect(find.text('Audit reference: topup-verified-1'), findsOneWidget);
    expect(find.text('Debit | Pending'), findsOneWidget);
    expect(find.text('Audit reference: withdrawal-pending-1'), findsOneWidget);
  });

  testWidgets('wallet overview uses overview as GTEX Coin balance authority', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final _DivergentWalletApi repository = _DivergentWalletApi();
    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(repository),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteWalletOverviewScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(repository.coinSummaryRequested, isFalse);
    expect(repository.creditSummaryRequested, isTrue);
    expect(find.text('1200 GTEX Coin'), findsWidgets);
    expect(find.text('7777 Fan Coin'), findsOneWidget);
    expect(find.text('Locked funds: 250 GTEX Coin'), findsOneWidget);
    expect(find.text('Pending transfer escrow'), findsOneWidget);
    expect(find.text('7777 GTEX Coin'), findsNothing);
    expect(find.text('999 GTEX Coin'), findsNothing);
    expect(find.text('Stale summary reservation'), findsNothing);
    expect(find.text('Stale credit summary lock'), findsNothing);
  });

  testWidgets('funding flow exposes KoraPay and manual bank transfer only', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 2200);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = _authenticatedController(
      _WalletRestrictionApi(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteFundWalletScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Deposit'), findsOneWidget);
    expect(find.text('Backend wallet truth'), findsOneWidget);
    expect(find.text('1200 GTEX Coin'), findsOneWidget);
    expect(find.text('250 GTEX Coin'), findsWidgets);
    expect(find.text('125 GTEX Coin'), findsOneWidget);
    expect(find.text('Instant payment'), findsOneWidget);
    expect(find.text('KoraPay'), findsWidgets);
    expect(find.text('Bank transfer'), findsOneWidget);
    expect(find.text('Create bank transfer request'), findsOneWidget);
    expect(
      find.textContaining(
        'Pay'
        'stack',
      ),
      findsNothing,
    );
  });

  testWidgets('withdrawal eligibility renders backend balance truth', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(_WalletRestrictionApi()),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteWithdrawalEligibilityScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Withdrawable now'), findsOneWidget);
    expect(find.text('Backend available'), findsOneWidget);
    expect(find.text('Remaining allowance'), findsOneWidget);
    expect(find.text('Pending withdrawals'), findsOneWidget);
    expect(find.text('Country'), findsOneWidget);
    expect(find.text('1200 GTEX Coin'), findsWidgets);
    expect(find.text('125 GTEX Coin'), findsOneWidget);
    expect(find.text('NG'), findsOneWidget);
  });

  testWidgets('withdrawal request blocks submit when bank sync fails', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(_BankSyncFailureApi()),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteWithdrawalRequestScreen(
          controller: controller,
          eligibility: const GteWithdrawalEligibility(
            availableBalance: 1200,
            withdrawableNow: 900,
            remainingAllowance: 900,
            nextEligibleAt: null,
            kycStatus: GteKycStatus.fullyVerified,
            requiresKyc: false,
            requiresBankAccount: false,
            pendingWithdrawals: 0,
            countryCode: 'NG',
            countryWithdrawalsEnabled: true,
            policyBlocked: false,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Bank details unavailable'), findsOneWidget);
    expect(
      find.text(
        'Bank account sync must complete before submitting a withdrawal.',
      ),
      findsOneWidget,
    );
    final Finder submitButton = find.widgetWithText(FilledButton, 'Submit');
    expect(submitButton, findsOneWidget);
    expect(tester.widget<FilledButton>(submitButton).onPressed, isNull);
  });
}

class _WalletRestrictionApi extends GteMockApi {
  @override
  Future<GteWalletOverview> fetchWalletOverview() async {
    return const GteWalletOverview(
      availableBalance: 1200,
      reservedBalance: 250,
      lockedBalance: 250,
      lockReasons: <String>[
        'Pending transfer escrow',
        'Transfer bid reservations: 250.0000 coin | Ref transfer_bid:bid-123',
      ],
      pendingDeposits: 75,
      pendingWithdrawals: 125,
      totalInflow: 2000,
      totalOutflow: 800,
      withdrawableNow: 900,
      currency: GteLedgerUnit.coin,
      countryCode: 'NG',
      requiredPolicyAcceptancesMissing: 1,
      policyBlocked: true,
      policyBlockReason:
          'Accept the updated wallet terms before deposits resume.',
      depositMode: 'bank_transfer',
      withdrawalMode: 'bank_transfer',
      paymentProviderStatus: <String, String>{
        'bank_transfer_manual': 'ready',
        'korapay': 'ready',
      },
    );
  }

  @override
  Future<GteWalletSummary> fetchWalletSummary({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    if (currency == GteLedgerUnit.credit) {
      return const GteWalletSummary(
        availableBalance: 320,
        reservedBalance: 0,
        totalBalance: 320,
        currency: GteLedgerUnit.credit,
      );
    }
    return const GteWalletSummary(
      availableBalance: 1200,
      reservedBalance: 250,
      lockedBalance: 250,
      lockReasons: <String>['Pending transfer escrow'],
      totalBalance: 1450,
      currency: GteLedgerUnit.coin,
    );
  }

  @override
  Future<List<GteWalletTransactionRecord>> listWalletTransactions({
    int limit = 20,
  }) async {
    return <GteWalletTransactionRecord>[
      GteWalletTransactionRecord(
        id: 'txn-1',
        userId: 'user-1',
        type: 'credit',
        amount: 500,
        status: 'verified',
        reference: 'topup-verified-1',
        createdAt: DateTime.utc(2026, 5, 28, 9),
      ),
      GteWalletTransactionRecord(
        id: 'txn-2',
        userId: 'user-1',
        type: 'debit',
        amount: 125,
        status: 'pending',
        reference: 'withdrawal-pending-1',
        createdAt: DateTime.utc(2026, 5, 28, 10),
      ),
    ];
  }

  @override
  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() async {
    return const GteWithdrawalEligibility(
      availableBalance: 1200,
      withdrawableNow: 900,
      remainingAllowance: 900,
      nextEligibleAt: null,
      kycStatus: GteKycStatus.fullyVerified,
      requiresKyc: false,
      requiresBankAccount: false,
      pendingWithdrawals: 125,
      countryCode: 'NG',
      countryWithdrawalsEnabled: true,
      policyBlocked: false,
    );
  }
}

class _DivergentWalletApi extends _WalletRestrictionApi {
  bool coinSummaryRequested = false;
  bool creditSummaryRequested = false;

  @override
  Future<GteWalletSummary> fetchWalletSummary({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    if (currency == GteLedgerUnit.credit) {
      creditSummaryRequested = true;
      return const GteWalletSummary(
        availableBalance: 7777,
        reservedBalance: 7777,
        lockedBalance: 7777,
        lockReasons: <String>['Stale credit summary lock'],
        totalBalance: 7777,
        currency: GteLedgerUnit.coin,
      );
    }
    if (currency == GteLedgerUnit.coin) {
      coinSummaryRequested = true;
      return const GteWalletSummary(
        availableBalance: 7777,
        reservedBalance: 7777,
        lockedBalance: 7777,
        lockReasons: <String>['Stale summary reservation'],
        totalBalance: 7777,
        currency: GteLedgerUnit.coin,
      );
    }
    return super.fetchWalletSummary(currency: currency);
  }

  @override
  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() async {
    final GteWithdrawalEligibility base =
        await super.fetchWithdrawalEligibility();
    return GteWithdrawalEligibility(
      availableBalance: base.availableBalance,
      withdrawableNow: base.withdrawableNow,
      remainingAllowance: base.remainingAllowance,
      nextEligibleAt: base.nextEligibleAt,
      kycStatus: base.kycStatus,
      requiresKyc: base.requiresKyc,
      requiresBankAccount: base.requiresBankAccount,
      pendingWithdrawals: 999,
      countryCode: base.countryCode,
      countryWithdrawalsEnabled: base.countryWithdrawalsEnabled,
      policyBlocked: base.policyBlocked,
      policyBlockReason: base.policyBlockReason,
    );
  }
}

class _BankSyncFailureApi extends GteMockApi {
  @override
  Future<List<GteUserBankAccount>> listUserBankAccounts() async {
    throw StateError('bank route unavailable');
  }
}

GteExchangeApiClient _fixtureClient(GteMockApi repository) {
  return GteExchangeApiClient(
    config: const GteRepositoryConfig(
      baseUrl: 'http://127.0.0.1:8000',
      mode: GteBackendMode.fixture,
    ),
    transport: GteHttpTransport(),
    repository: repository,
  );
}

GteExchangeController _authenticatedController(GteMockApi repository) {
  final GteExchangeController controller = GteExchangeController(
    api: _fixtureClient(repository),
  );
  controller.syncSession(
    const GteAuthSession(
      accessToken: 'wallet-test-access-token',
      refreshToken: 'wallet-test-refresh-token',
      sessionId: 'wallet-test-session',
      tokenType: 'bearer',
      expiresIn: 3600,
      refreshExpiresIn: 7200,
      user: GteCurrentUser(
        id: 'wallet-user-1',
        email: 'wallet@example.com',
        username: 'wallet-user',
        fullName: 'Wallet User',
        phoneNumber: null,
        displayName: 'Wallet User',
        role: 'user',
      ),
    ),
  );
  return controller;
}
