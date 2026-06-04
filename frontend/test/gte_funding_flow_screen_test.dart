import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_funding_flow_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'funding screen repaints into compliance-gated state after deferred refresh',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: _fixtureClient(
          _BlockedComplianceApi(latency: const Duration(milliseconds: 10)),
        ),
      );
      controller.session = _authenticatedSession(
        userId: 'fixture-user',
        userName: 'Ayo Martins',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteFundWalletScreen(controller: controller),
        ),
      );

      expect(find.text('Deposit'), findsOneWidget);
      expect(find.text('Choose a deposit method'), findsOneWidget);
      expect(find.text('Continue to KoraPay'), findsOneWidget);
      expect(find.text('Wallet sync pending'), findsOneWidget);
      expect(find.text('Compliance action required'), findsNothing);
      Finder createBankTransferButton = find.widgetWithText(
        FilledButton,
        'Create bank transfer request',
      );
      expect(createBankTransferButton, findsOneWidget);
      expect(
        tester.widget<FilledButton>(createBankTransferButton).onPressed,
        isNull,
      );

      await _pumpUntil(
        tester,
        () => find.text('Compliance action required').evaluate().isNotEmpty,
      );

      expect(find.text('Compliance action required'), findsOneWidget);
      expect(find.text('Open compliance center'), findsOneWidget);
      expect(
        find.text('Complete 1 policy item to unlock deposits.'),
        findsOneWidget,
      );
      expect(find.text('Instant payment'), findsOneWidget);
      createBankTransferButton = find.widgetWithText(
        FilledButton,
        'Create bank transfer request',
      );
      expect(createBankTransferButton, findsOneWidget);
      expect(
        tester.widget<FilledButton>(createBankTransferButton).onPressed,
        isNull,
      );
    },
  );

  testWidgets(
    'funding screen renders canonical KoraPay and manual bank-transfer states',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: _fixtureClient(
          _ManualDepositApi(
            deposits: <GteDepositRequest>[
              _depositFixture(status: GteDepositStatus.awaitingPayment),
            ],
          ),
        ),
      );
      controller.session = _authenticatedSession(
        userId: 'fixture-user',
        userName: 'Ayo Martins',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteFundWalletScreen(controller: controller),
        ),
      );

      await _pumpUntil(
        tester,
        () => find.text('KoraPay flow state').evaluate().isNotEmpty,
      );
      await _pumpUntil(
        tester,
        () => find.text('Awaiting bank transfer').evaluate().isNotEmpty,
      );

      expect(find.text('KoraPay flow state'), findsOneWidget);
      expect(find.text('Backend wallet truth'), findsOneWidget);
      expect(find.text('Available'), findsWidgets);
      expect(find.text('Pending deposits'), findsOneWidget);
      expect(find.text('Pending withdrawals'), findsOneWidget);
      expect(find.text('Amount entry'), findsOneWidget);
      expect(find.text('Validation'), findsOneWidget);
      expect(find.text('Redirect'), findsOneWidget);
      expect(find.text('Processing'), findsOneWidget);
      expect(find.text('Confirmation wait'), findsOneWidget);
      expect(find.text('Success'), findsOneWidget);
      expect(find.text('Failed / retry'), findsOneWidget);
      expect(find.text('Dispute escalation'), findsOneWidget);

      expect(find.text('Awaiting bank transfer'), findsOneWidget);
      expect(find.text('Audit reference'), findsOneWidget);
      expect(find.text('Upload image/PDF proof'), findsOneWidget);
      expect(
        find.textContaining('Instructions: transfer the exact amount'),
        findsOneWidget,
      );
      expect(find.text('Bank: GTEX Treasury Bank'), findsOneWidget);
    },
  );

  testWidgets(
    'manual deposit with proof exposes OCR pending and audit attachment state',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: _fixtureClient(
          _ManualDepositApi(
            deposits: <GteDepositRequest>[
              _depositFixture(
                status: GteDepositStatus.paymentSubmitted,
                proofAttachmentId: 'proof-attachment-1',
                submittedAt: DateTime.utc(2026, 5, 27, 10, 30),
              ),
            ],
          ),
        ),
      );
      controller.session = _authenticatedSession(
        userId: 'fixture-user',
        userName: 'Ayo Martins',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteFundWalletScreen(controller: controller),
        ),
      );

      await _pumpUntil(
        tester,
        () => find.text('Proof received - OCR pending').evaluate().isNotEmpty,
      );

      expect(find.text('Proof received - OCR pending'), findsOneWidget);
      expect(find.text('Proof attachment'), findsOneWidget);
      expect(find.text('proof-attachment-1'), findsOneWidget);
      expect(find.text('Submitted'), findsOneWidget);
      expect(find.text('2026-05-27 10:30 UTC'), findsOneWidget);
    },
  );

  testWidgets(
    'non-live KoraPay session is blocked without local payment controls',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: _fixtureClient(_NonLiveKoraPayApi()),
      );
      controller.session = _authenticatedSession(
        userId: 'fixture-user',
        userName: 'Ayo Martins',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteFundWalletScreen(controller: controller),
        ),
      );

      await _pumpUntil(
        tester,
        () =>
            find
                .text('KoraPay checkout is ready for deposits.')
                .evaluate()
                .isNotEmpty,
      );
      await tester.enterText(find.byType(TextField).first, '5000');
      await tester.tap(find.text('Continue to KoraPay'));
      await _pumpUntil(
        tester,
        () => find.text('KoraPay session unavailable').evaluate().isNotEmpty,
      );

      expect(find.text('KoraPay session unavailable'), findsOneWidget);
      expect(find.textContaining('non-live payment session'), findsOneWidget);
      expect(find.text('Verify payment'), findsNothing);
      expect(find.text('Start again'), findsOneWidget);
    },
  );
}

class _BlockedComplianceApi extends GteMockApi {
  _BlockedComplianceApi({super.latency = Duration.zero});

  static const GtePolicyRequirementSummary _missingRequirement =
      GtePolicyRequirementSummary(
        documentKey: 'wallet-policy',
        title: 'Wallet policy acceptance',
        versionLabel: 'v2',
        isMandatory: true,
      );

  static const List<GtePolicyRequirementSummary> _missingRequirements =
      <GtePolicyRequirementSummary>[_missingRequirement];

  @override
  Future<GteComplianceStatus> fetchComplianceStatus() async {
    await Future<void>.delayed(latency);
    return const GteComplianceStatus(
      countryCode: 'NG',
      countryPolicyBucket: 'regulated_market_disabled',
      depositsEnabled: true,
      marketTradingEnabled: false,
      platformRewardWithdrawalsEnabled: false,
      requiredPolicyAcceptancesMissing: 1,
      missingPolicyAcceptances: _missingRequirements,
      canDeposit: false,
      canWithdrawPlatformRewards: false,
      canTradeMarket: false,
    );
  }

  @override
  Future<List<GtePolicyRequirementSummary>> fetchPolicyRequirements() async {
    await Future<void>.delayed(latency);
    return _missingRequirements;
  }

  @override
  Future<GteWalletOverview> fetchWalletOverview() async {
    await Future<void>.delayed(latency);
    return const GteWalletOverview(
      availableBalance: 1200,
      reservedBalance: 0,
      lockedBalance: 0,
      lockReasons: <String>[],
      pendingDeposits: 0,
      pendingWithdrawals: 0,
      totalInflow: 1200,
      totalOutflow: 0,
      withdrawableNow: 0,
      currency: GteLedgerUnit.coin,
      countryCode: 'NG',
      requiredPolicyAcceptancesMissing: 1,
      policyBlocked: false,
      depositMode: 'hybrid',
      withdrawalMode: 'bank_transfer',
      paymentProviderStatus: <String, String>{
        'bank_transfer_manual': 'ready',
        'korapay': 'ready',
      },
    );
  }

  @override
  Future<List<GteDepositRequest>> listDepositRequests() async {
    await Future<void>.delayed(latency);
    return const <GteDepositRequest>[];
  }
}

class _ManualDepositApi extends GteMockApi {
  _ManualDepositApi({required this.deposits, super.latency = Duration.zero});

  final List<GteDepositRequest> deposits;

  @override
  Future<GteComplianceStatus> fetchComplianceStatus() async {
    await Future<void>.delayed(latency);
    return const GteComplianceStatus(
      countryCode: 'NG',
      countryPolicyBucket: 'wallet_ready',
      depositsEnabled: true,
      marketTradingEnabled: true,
      platformRewardWithdrawalsEnabled: true,
      requiredPolicyAcceptancesMissing: 0,
      missingPolicyAcceptances: <GtePolicyRequirementSummary>[],
      canDeposit: true,
      canWithdrawPlatformRewards: true,
      canTradeMarket: true,
    );
  }

  @override
  Future<GteWalletOverview> fetchWalletOverview() async {
    await Future<void>.delayed(latency);
    return const GteWalletOverview(
      availableBalance: 1200,
      reservedBalance: 0,
      lockedBalance: 0,
      lockReasons: <String>[],
      pendingDeposits: 0,
      pendingWithdrawals: 0,
      totalInflow: 1200,
      totalOutflow: 0,
      withdrawableNow: 1200,
      currency: GteLedgerUnit.coin,
      countryCode: 'NG',
      depositMode: 'hybrid',
      withdrawalMode: 'bank_transfer',
      paymentProviderStatus: <String, String>{
        'bank_transfer_manual': 'ready',
        'korapay': 'ready',
      },
    );
  }

  @override
  Future<List<GteDepositRequest>> listDepositRequests() async {
    await Future<void>.delayed(latency);
    return deposits;
  }
}

class _NonLiveKoraPayApi extends _ManualDepositApi {
  _NonLiveKoraPayApi() : super(deposits: <GteDepositRequest>[]);

  @override
  Future<GteWalletTopUpSession> initiateWalletTopUp(
    GteWalletTopUpInitiateRequest request,
  ) async {
    await Future<void>.delayed(latency);
    return GteWalletTopUpSession(
      reference: 'KORA-NONLIVE-1',
      paymentLink: 'https://non-live.korapay.local/KORA-NONLIVE-1',
      amount: request.amount,
      currency: 'NGN',
      provider: 'korapay',
      status: 'non_live',
      mockMode: false,
    );
  }
}

GteDepositRequest _depositFixture({
  required GteDepositStatus status,
  String? proofAttachmentId,
  DateTime? submittedAt,
}) {
  return GteDepositRequest(
    id: 'deposit-fixture-1',
    reference: 'DEP-20260527-1',
    status: status,
    amountFiat: 5000,
    amountCoin: 5.56,
    currencyCode: 'NGN',
    rateValue: 900,
    rateDirection: GteRateDirection.fiatPerCoin,
    bankName: 'GTEX Treasury Bank',
    bankAccountNumber: '0123456789',
    bankAccountName: 'Global Talent Exchange',
    bankCode: '999',
    payerName: null,
    senderBank: null,
    transferReference: null,
    proofAttachmentId: proofAttachmentId,
    adminNotes: null,
    createdAt: DateTime.utc(2026, 5, 27, 10),
    submittedAt: submittedAt,
    reviewedAt: null,
    confirmedAt: null,
    rejectedAt: null,
    expiresAt: DateTime.utc(2026, 5, 28, 10),
  );
}

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1400, 1800);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

GteAuthSession _authenticatedSession({
  required String userId,
  required String userName,
  String? clubId,
  String? clubName,
}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'test-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    if (clubId != null) 'current_club_id': clubId,
    if (clubName != null) 'current_club_name': clubName,
    'user': <String, Object?>{
      'id': userId,
      'email': '$userId@gtex.test',
      'username': userId,
      'display_name': userName,
      'role': 'user',
      if (clubId != null) 'current_club_id': clubId,
      if (clubName != null) 'current_club_name': clubName,
    },
  });
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

Future<void> _pumpUntil(
  WidgetTester tester,
  bool Function() condition, {
  Duration step = const Duration(milliseconds: 20),
  int maxPumps = 60,
}) async {
  for (int pump = 0; pump < maxPumps; pump += 1) {
    await tester.pump(step);
    if (condition()) {
      return;
    }
  }
  throw TestFailure('Timed out waiting for condition.');
}
