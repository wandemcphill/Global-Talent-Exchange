import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/wallet/gte_funding_flow_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
      'funding screen repaints into compliance-gated state after deferred refresh',
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
        home: GteFundWalletScreen(controller: controller),
      ),
    );

    expect(find.text('Fund wallet'), findsOneWidget);
    expect(find.text('Create a deposit request'), findsOneWidget);
    expect(find.text('Compliance action required'), findsNothing);

    await _pumpUntil(
      tester,
      () =>
          controller.complianceStatus != null &&
          controller.complianceStatus!.canDeposit == false &&
          !controller.isLoadingCompliance,
    );

    expect(find.text('Compliance action required'), findsOneWidget);
    expect(find.text('Open compliance center'), findsOneWidget);
    expect(
      find.text('Complete 1 policy items to unlock deposits.'),
      findsOneWidget,
    );
  });
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
