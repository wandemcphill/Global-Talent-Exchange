import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_order_ticket_sheet.dart';

Future<GteExchangeController> _controller(
  WidgetTester tester, {
  bool signedIn = true,
}) async {
  late GteExchangeController controller;
  await tester.runAsync(() async {
    controller = GteExchangeController(api: GteExchangeApiClient.fixture());
    if (signedIn) {
      await controller.signIn(
        email: 'fixture.player@gte.local',
        password: 'DemoPass123', // pragma: allowlist secret
      );
    }
    await controller.openPlayer('lamine-yamal');
  });
  return controller;
}

Future<void> _pumpAcquisition(
  WidgetTester tester,
  GteExchangeController controller,
) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: GteOrderTicketSheet(
          controller: controller,
          snapshot: controller.selectedPlayer!,
        ),
      ),
    ),
  );
  for (int i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

void main() {
  testWidgets('acquisition sheet presents one whole player unit',
      (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    await _pumpAcquisition(tester, controller);

    expect(find.text('Acquire player'), findsWidgets);
    expect(
      find.text(
        'One complete player unit. Each account can acquire this player only once.',
      ),
      findsOneWidget,
    );
    expect(find.byType(TextField), findsNothing);
    expect(find.textContaining('Shares'), findsNothing);
    expect(find.textContaining('Trading fee'), findsNothing);
    expect(find.textContaining('Sell'), findsNothing);
  });

  testWidgets('acquisition surface exposes no quantity or resale controls',
      (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    await _pumpAcquisition(tester, controller);

    expect(find.text('UNITS OWNED'), findsOneWidget);
    expect(find.text('Acquire player'), findsWidgets);
    expect(find.text('Buy shares'), findsNothing);
    expect(find.text('Sell shares'), findsNothing);
    expect(find.text('Trade shares'), findsNothing);
    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('signed-out account is asked to sign in instead of fabricating ownership',
      (WidgetTester tester) async {
    final GteExchangeController controller =
        await _controller(tester, signedIn: false);
    await _pumpAcquisition(tester, controller);

    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('0 of 1'), findsNothing);
    expect(find.text('Acquire player'), findsNothing);
    expect(find.byType(TextField), findsNothing);
  });
}
