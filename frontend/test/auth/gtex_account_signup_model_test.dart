import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/screens/auth/gtex_account_signup_screens.dart';

void main() {
  testWidgets('account selector exposes only normal GTEX account registration',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexAccountSelectorScreen()),
    );
    await tester.pumpAndSettle();

    expect(find.text('STANDARD GTEX ACCOUNT'), findsOneWidget);
    expect(find.textContaining('Register once with a normal GTEX account'), findsOneWidget);
    expect(find.text('CREATOR ACCOUNT'), findsNothing);
    expect(find.text('COIN TRADER ACCOUNT'), findsNothing);
  });
}
