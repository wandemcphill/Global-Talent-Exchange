import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('login surface hides seeded credentials on first render',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1600, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteLoginScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    final List<TextField> fields =
        tester.widgetList<TextField>(find.byType(TextField)).toList();

    expect(find.text('Use demo credentials'), findsNothing);
    expect(find.text('Use admin credentials'), findsNothing);
    expect(fields, hasLength(2));
    expect(fields[0].controller?.text, isEmpty);
    expect(fields[1].controller?.text, isEmpty);
  });

  testWidgets('login surface exposes creator access request entry',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1600, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteLoginScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Apply for creator access'), findsOneWidget);

    await tester.ensureVisible(find.text('Apply for creator access'));
    await tester.tap(find.text('Apply for creator access'));
    await tester.pumpAndSettle();

    expect(find.text('Creator access request'), findsOneWidget);
    expect(find.text('Create account to continue'), findsOneWidget);
  });

  testWidgets(
      'authenticated login surface avoids unlocked copy when capital actions stay restricted',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1600, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    controller.session = _authenticatedSession(
      userId: 'demo-user',
      userName: 'Ayo Martins',
      clubId: 'ibadan-lions',
      clubName: 'Ibadan Lions FC',
    );
    controller.complianceStatus = const GteComplianceStatus(
      countryCode: 'NG',
      countryPolicyBucket: 'regulated_market_disabled',
      depositsEnabled: true,
      marketTradingEnabled: false,
      platformRewardWithdrawalsEnabled: false,
      requiredPolicyAcceptancesMissing: 1,
      missingPolicyAcceptances: <GtePolicyRequirementSummary>[
        GtePolicyRequirementSummary(
          documentKey: 'wallet-policy',
          title: 'Wallet policy acceptance',
          versionLabel: 'v2',
          isMandatory: true,
        ),
      ],
      canDeposit: false,
      canWithdrawPlatformRewards: false,
      canTradeMarket: false,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteLoginScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Session active'), findsOneWidget);
    expect(find.text('Mission confirmed'), findsNothing);
    expect(
      find.text(
        'Active session for demo-user. GTEX access is live, but some capital actions remain restricted until compliance clears this account.',
      ),
      findsOneWidget,
    );
    expect(find.text('Compliance action required'), findsOneWidget);
    expect(find.text('Open compliance center'), findsOneWidget);
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
