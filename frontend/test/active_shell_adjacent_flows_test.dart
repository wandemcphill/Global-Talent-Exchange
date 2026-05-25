import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_exchange_shell_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen_v2.dart';
import 'package:gte_frontend/screens/gte_portfolio_screen.dart';
import 'package:gte_frontend/screens/notifications/gte_notifications_screen.dart';
import 'package:gte_frontend/screens/wallet/gte_withdrawal_flow_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  test('community route parses to the live Social shell lane', () {
    expect(
      GteNavigationRoute.parse('/app/community').primaryDestination,
      GtePrimaryDestination.community,
    );
    expect(
      GteNavigationRoute.parse('/app/social').primaryDestination,
      GtePrimaryDestination.community,
    );
  });

  testWidgets('active shell mounts the GTEX V2 transfer market route', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteExchangeShellScreen.fromPath(
          controller: controller,
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          initialPath: '/app/market',
        ),
      ),
    );
    await _pumpUntilText(tester, 'Transfer Hub');

    expect(find.byType(GteMarketPlayersScreenV2), findsOneWidget);
    expect(find.byType(GteMarketPlayersScreen), findsNothing);
    expect(find.text('My Shortlist'), findsOneWidget);
  });

  testWidgets(
    'active shell keeps creator community hidden for non-creators while preserving adjacent flows',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'user-ibadan',
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Club funds'));
      await _pumpUntilText(tester, 'GTC capital rail');
      expect(find.text('Wallet & Capital'), findsWidgets);
      expect(find.text('Top up GTC'), findsOneWidget);

      expect(find.byTooltip('Creator community'), findsNothing);

      await tester.tap(find.byTooltip('Creator access request'));
      await tester.pumpAndSettle();
      expect(find.text('Creator access request'), findsOneWidget);
    },
  );

  testWidgets(
    'live shell keeps portfolio visible in primary nav and preserves wallet deep links',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'user-ibadan',
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteExchangeShellScreen.fromPath(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialPath: '/app/wallet',
          ),
        ),
      );
      await _pumpUntilText(tester, 'Wallet & Capital');

      expect(find.text('Wallet'), findsWidgets);
      final Finder walletNavChip = find.text('Wallet').last;
      expect(walletNavChip, findsOneWidget);

      await tester.tap(find.text('Home').last);
      await tester.pumpAndSettle();
      expect(find.text('Home sync'), findsOneWidget);

      await tester.ensureVisible(walletNavChip);
      await tester.tap(walletNavChip);
      await _pumpUntilText(tester, 'GTC capital rail');
      expect(find.text('Top up GTC'), findsOneWidget);
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'portfolio wallet actions open overview, funding, withdrawals, history, notifications, and disputes',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'user-ibadan',
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: AnimatedBuilder(
            animation: controller,
            builder:
                (BuildContext context, Widget? child) => GtePortfolioScreen(
                  controller: controller,
                  onOpenPlayer: (_) {},
                  onOpenLogin: () {},
                ),
          ),
        ),
      );
      controller.refreshAccount();
      await _pumpUntilText(tester, 'Money moves');

      final Finder walletOverviewButton = find.text('Wallet overview');
      await tester.ensureVisible(walletOverviewButton);
      await tester.tap(walletOverviewButton);
      await _pumpUntilText(tester, 'Wallet command desk');
      expect(find.text('Club Wallet'), findsOneWidget);
      expect(find.text('Wallet command desk'), findsOneWidget);
      expect(find.text('GTC'), findsWidgets);
      expect(find.text('FNC'), findsWidgets);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await _pumpUntilText(tester, 'Money moves');

      final Finder fundWalletButton = find.text('Fund wallet');
      await tester.ensureVisible(fundWalletButton);
      await tester.tap(fundWalletButton);
      await _pumpUntilText(tester, 'Choose live funding rail');
      expect(find.text('Deposit'), findsOneWidget);
      expect(find.text('Continue to KoraPay'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await _pumpUntilText(tester, 'Money moves');

      final Finder withdrawButton = find.text('Withdraw');
      await tester.ensureVisible(withdrawButton);
      await tester.tap(withdrawButton);
      await _pumpUntilText(tester, 'Request withdrawal');
      expect(find.text('Request withdrawal'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await _pumpUntilText(tester, 'Money moves');

      final Finder historyButton = find.text('History and support');
      await tester.ensureVisible(historyButton);
      await tester.tap(historyButton);
      await _pumpUntilText(tester, 'Transaction History');
      expect(find.text('No wallet activity yet'), findsOneWidget);
      expect(find.text('Deposit'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await _pumpUntilText(tester, 'Money moves');

      final Finder notificationsButton = find.widgetWithText(
        OutlinedButton,
        'Notifications',
      );
      await tester.ensureVisible(notificationsButton);
      await tester.tap(notificationsButton);
      await _pumpUntilText(tester, 'Mark all read');
      expect(find.text('Mark all read'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await _pumpUntilText(tester, 'Money moves');

      final Finder supportButton = find.widgetWithText(
        OutlinedButton,
        'Support',
      );
      await tester.ensureVisible(supportButton);
      await tester.tap(supportButton);
      await _pumpUntilText(tester, 'Deposit still pending');
      expect(find.text('Deposit still pending'), findsOneWidget);

      final Finder openThreadButton = find.widgetWithText(
        OutlinedButton,
        'Open thread',
      );
      await tester.ensureVisible(openThreadButton);
      await tester.tap(openThreadButton);
      await _pumpUntilText(tester, 'Deposit still pending');
      expect(find.text('Deposit still pending'), findsOneWidget);
      await tester.pumpAndSettle();
      await tester.pageBack();
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'wallet actions disable manual funding when compliance blocks deposits',
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
          home: AnimatedBuilder(
            animation: controller,
            builder:
                (BuildContext context, Widget? child) => GtePortfolioScreen(
                  controller: controller,
                  onOpenPlayer: (_) {},
                  onOpenLogin: () {},
                ),
          ),
        ),
      );
      controller.refreshAccount();

      await _pumpUntil(
        tester,
        () =>
            controller.complianceStatus != null &&
            controller.complianceStatus!.canDeposit == false &&
            !controller.isLoadingCompliance,
      );
      await _pumpUntilText(tester, 'Money moves');

      final Finder fundWalletButton = find.text('Fund wallet');
      expect(fundWalletButton, findsOneWidget);
      expect(
        find.text(
          'Funding is locked until compliance review completes. Open wallet overview for the current restriction and next steps.',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'notifications refresh read state after opening an unread inbox item',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
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
          home: GteNotificationsScreen(controller: controller),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unread'), findsOneWidget);

      await tester.tap(
        find.text('Deposit DEP-1001 submitted. Pending review.'),
      );
      await tester.pumpAndSettle();
      expect(find.text('Transaction History'), findsOneWidget);

      await tester.pageBack();
      await tester.pumpAndSettle();

      expect(find.text('Unread'), findsNothing);
      expect(find.text('Read'), findsNWidgets(2));
    },
  );

  testWidgets('withdrawal notifications route into the withdrawal workspace', (
    WidgetTester tester,
  ) async {
    _setLargeViewport(tester);

    final GteMockApi repository = GteMockApi(latency: Duration.zero);
    await tester.runAsync(() async {
      await repository.acceptPolicyDocument('privacy_policy', 'v1.0');
      await repository.acceptPolicyDocument('withdrawal_policy', 'v1.0');
      await repository.createWithdrawalRequest(
        const GteWithdrawalCreateRequest(amountCoin: 25),
      );
    });
    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(repository),
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
        home: GteNotificationsScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    final Finder withdrawalNotification = find.textContaining(
      'Withdrawal WDR-',
    );
    expect(withdrawalNotification, findsOneWidget);

    await tester.tap(withdrawalNotification);
    await _pumpUntilText(tester, 'Request withdrawal');

    expect(find.text('Withdrawals'), findsOneWidget);
    expect(find.text('Request withdrawal'), findsOneWidget);
  });

  testWidgets(
    'withdrawal workspace disables request initiation when blockers are already known',
    (WidgetTester tester) async {
      _setLargeViewport(tester);

      final GteExchangeController controller = GteExchangeController(
        api: _fixtureClient(_BlockedWithdrawalApi()),
      );
      controller.session = _authenticatedSession(
        userId: 'user-ibadan',
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GteWithdrawalEligibilityScreen(controller: controller),
        ),
      );
      await _pumpUntilText(tester, 'Withdrawals');

      final Finder requestButton = find.widgetWithText(
        FilledButton,
        'Request withdrawal',
      );
      expect(tester.widget<FilledButton>(requestButton).onPressed, isNull);
      expect(find.text('Withdrawal request unavailable'), findsOneWidget);
      expect(
        find.text('Policy acceptance required before withdrawal is enabled.'),
        findsOneWidget,
      );
    },
  );
}

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(2400, 2200);
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
    'session_id': 'session-$userId',
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

Future<void> _pumpUntilText(
  WidgetTester tester,
  String text, {
  Duration step = const Duration(milliseconds: 50),
  int maxPumps = 120,
}) async {
  final Finder finder = find.text(text);
  for (int pump = 0; pump < maxPumps; pump += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Timed out waiting for "$text".');
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
}

class _BlockedWithdrawalApi extends GteMockApi {
  _BlockedWithdrawalApi({super.latency = Duration.zero});

  @override
  Future<GteWithdrawalEligibility> fetchWithdrawalEligibility() async {
    await Future<void>.delayed(latency);
    return const GteWithdrawalEligibility(
      availableBalance: 250,
      withdrawableNow: 0,
      remainingAllowance: 0,
      nextEligibleAt: null,
      kycStatus: GteKycStatus.fullyVerified,
      requiresKyc: false,
      requiresBankAccount: false,
      pendingWithdrawals: 0,
      countryCode: 'NG',
      countryWithdrawalsEnabled: true,
      missingRequiredPolicies: <String>['withdrawal_policy'],
      policyBlocked: true,
      policyBlockReason:
          'Policy acceptance required before withdrawal is enabled.',
    );
  }
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
