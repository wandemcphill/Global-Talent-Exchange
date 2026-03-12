import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/screens/clubs/club_finance_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club finance screen shows summary and opens budget and cashflow',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubFinanceScreen(api: ClubOpsApi.fixture()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Club finances'), findsOneWidget);
    expect(find.text('Current balance'), findsOneWidget);
    expect(find.text('Operating budget'), findsWidgets);

    await tester.ensureVisible(find.text('Budget'));
    await tester.tap(find.text('Budget'));
    await tester.pumpAndSettle();
    expect(find.text('Operating budget'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Cashflow'));
    await tester.tap(find.text('Cashflow'));
    await tester.pumpAndSettle();
    expect(find.text('Cashflow summary'), findsOneWidget);
    expect(find.text('Ledger'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Recent cashflow'),
      300,
    );
    expect(find.text('Recent cashflow'), findsOneWidget);
  });
}
