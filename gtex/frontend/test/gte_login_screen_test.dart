import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gte_login_screen.dart';

void main() {
  testWidgets('GTEX 22 sign-in surface starts empty and branded', (tester) async {
    final controller = GteExchangeController(api: GteExchangeApiClient.fixture());

    await tester.pumpWidget(MaterialApp(home: GteLoginScreen(controller: controller)));
    await tester.pumpAndSettle();

    expect(find.text('THE WORLD\nIS STILL MOVING.'), findsOneWidget);
    expect(find.text('ENTER GTEX'), findsOneWidget);
    expect(find.text('CREATE A GTEX ID'), findsOneWidget);

    final fields = tester.widgetList<TextField>(find.byType(TextField)).toList();
    expect(fields, hasLength(2));
    expect(fields[0].controller?.text, isEmpty);
    expect(fields[1].controller?.text, isEmpty);
  });

  testWidgets('GTEX 22 sign-in reports authentication failures without hiding the form', (tester) async {
    final controller = GteExchangeController(api: GteExchangeApiClient.fixture());

    await tester.pumpWidget(MaterialApp(home: GteLoginScreen(controller: controller)));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).first, 'not-a-user@example.com');
    await tester.enterText(find.byType(TextField).last, 'wrong-password');
    await tester.tap(find.text('ENTER GTEX'));
    await tester.pumpAndSettle();

    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('ENTER GTEX'), findsOneWidget);
  });
}
