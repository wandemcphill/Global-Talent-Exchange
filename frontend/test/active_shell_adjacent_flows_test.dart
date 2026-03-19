import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_portfolio_screen.dart';
import 'package:gte_frontend/screens/notifications/gte_notifications_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
      'active shell reaches notification settings, wallet lane, and creator community surfaces',
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

    await tester.ensureVisible(find.text('Community').last);
    await tester.tap(find.text('Community').last);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Notifications').last);
    await tester.tap(find.text('Notifications').last);
    await tester.pumpAndSettle();
    expect(find.text('Wallet alerts'), findsOneWidget);
    expect(find.text('Announcements'), findsOneWidget);
    final Finder marketOpenAlerts =
        find.widgetWithText(SwitchListTile, 'Market open alerts');
    expect(
      tester.widget<SwitchListTile>(marketOpenAlerts).value,
      isTrue,
    );
    await tester.tap(find.text('Market open alerts'));
    await _pumpUntilSwitchValue(tester, marketOpenAlerts, false);
    expect(
      tester.widget<SwitchListTile>(marketOpenAlerts).value,
      isFalse,
    );

    await tester.ensureVisible(find.text('Wallet').last);
    await tester.tap(find.text('Wallet').last);
    await _pumpUntilText(tester, 'Wallet actions');
    expect(find.text('Wallet actions'), findsOneWidget);
    expect(find.text('Fund wallet'), findsOneWidget);

    await tester.tap(find.byTooltip('Creator community'));
    await tester.pumpAndSettle();
    expect(find.text('Community invites'), findsOneWidget);
    expect(find.text('Creator dashboard'), findsOneWidget);
  });

  testWidgets(
      'portfolio wallet actions open overview, funding, withdrawals, and notifications',
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
          builder: (BuildContext context, Widget? child) => GtePortfolioScreen(
            controller: controller,
            onOpenPlayer: (_) {},
            onOpenLogin: () {},
          ),
        ),
      ),
    );
    controller.refreshAccount();
    await _pumpUntilText(tester, 'Wallet actions');

    final Finder walletOverviewButton =
        find.widgetWithText(FilledButton, 'Wallet overview');
    await tester.ensureVisible(walletOverviewButton);
    await tester.tap(walletOverviewButton);
    await _pumpUntilText(tester, 'Wallet hub');
    expect(find.text('Wallet hub'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
    await _pumpUntilText(tester, 'Wallet actions');

    final Finder fundWalletButton =
        find.widgetWithText(OutlinedButton, 'Fund wallet');
    await tester.ensureVisible(fundWalletButton);
    await tester.tap(fundWalletButton);
    await _pumpUntilText(tester, 'Create a deposit request');
    expect(find.text('Create a deposit request'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
    await _pumpUntilText(tester, 'Wallet actions');

    final Finder withdrawButton =
        find.widgetWithText(OutlinedButton, 'Withdraw');
    await tester.ensureVisible(withdrawButton);
    await tester.tap(withdrawButton);
    await _pumpUntilText(tester, 'Request withdrawal');
    expect(find.text('Request withdrawal'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
    await _pumpUntilText(tester, 'Wallet actions');

    final Finder notificationsButton =
        find.widgetWithText(OutlinedButton, 'Notifications');
    await tester.ensureVisible(notificationsButton);
    await tester.tap(notificationsButton);
    await _pumpUntilText(tester, 'Mark all read');
    expect(find.text('Mark all read'), findsOneWidget);
  });

  testWidgets(
      'wallet actions disable manual funding when compliance blocks deposits',
      (WidgetTester tester) async {
    _setLargeViewport(tester);

    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(
        _BlockedComplianceApi(
          latency: const Duration(milliseconds: 10),
        ),
      ),
    );
    controller.session = _authenticatedSession(
      userId: 'demo-user',
      userName: 'Ayo Martins',
      clubId: 'ibadan-lions',
      clubName: 'Ibadan Lions FC',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: AnimatedBuilder(
          animation: controller,
          builder: (BuildContext context, Widget? child) => GtePortfolioScreen(
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
    await _pumpUntilText(tester, 'Wallet actions');

    final Finder fundWalletButton =
        find.widgetWithText(OutlinedButton, 'Fund wallet');
    expect(
      tester.widget<OutlinedButton>(fundWalletButton).onPressed,
      isNull,
    );
    expect(
      find.text(
        'Funding is locked until compliance review completes. Open Wallet overview for the current restriction and next steps.',
      ),
      findsOneWidget,
    );
  });

  testWidgets(
      'notifications refresh read state after opening an unread inbox item',
      (WidgetTester tester) async {
    _setLargeViewport(tester);

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.session = _authenticatedSession(
      userId: 'demo-user',
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

    await tester.tap(find.text('Deposit DEP-1001 submitted. Pending review.'));
    await tester.pumpAndSettle();
    expect(find.text('Deposit history'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(find.text('Unread'), findsNothing);
    expect(find.text('Read'), findsNWidgets(2));
  });

  testWidgets('withdrawal notifications route into the withdrawal workspace',
      (WidgetTester tester) async {
    _setLargeViewport(tester);

    final GteMockApi repository = GteMockApi(latency: Duration.zero);
    await tester.runAsync(() async {
      await repository.acceptPolicyDocument('privacy_policy', 'v1.0');
      await repository.acceptPolicyDocument('withdrawal_policy', 'v1.0');
      await repository.createWithdrawalRequest(
        const GteWithdrawalCreateRequest(
          amountCoin: 25,
        ),
      );
    });
    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(repository),
    );
    controller.session = _authenticatedSession(
      userId: 'demo-user',
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

    final Finder withdrawalNotification =
        find.textContaining('Withdrawal WDR-');
    expect(withdrawalNotification, findsOneWidget);

    await tester.tap(withdrawalNotification);
    await _pumpUntilText(tester, 'Request withdrawal');

    expect(find.text('Withdrawals'), findsOneWidget);
    expect(find.text('Request withdrawal'), findsOneWidget);
  });
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
  return GteAuthSession.fromJson(
    <String, Object?>{
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
    },
  );
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

Future<void> _pumpUntilSwitchValue(
  WidgetTester tester,
  Finder finder,
  bool expected, {
  Duration step = const Duration(milliseconds: 50),
  int maxPumps = 120,
}) async {
  for (int pump = 0; pump < maxPumps; pump += 1) {
    await tester.pump(step);
    if (tester.widget<SwitchListTile>(finder).value == expected) {
      return;
    }
  }
  throw TestFailure('Timed out waiting for switch value $expected.');
}

class _BlockedComplianceApi extends GteMockApi {
  _BlockedComplianceApi({
    super.latency = Duration.zero,
  });

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
