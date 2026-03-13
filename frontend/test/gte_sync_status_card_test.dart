import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';

void main() {
  testWidgets('sync status card renders refresh affordance and labels', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const Scaffold(
          body: GteSyncStatusCard(
            title: 'Capital layer',
            status: 'Balances and ledgers are protected.',
            syncedAt: null,
          ),
        ),
      ),
    );

    expect(find.text('Capital layer'), findsOneWidget);
    expect(find.text('Balances and ledgers are protected.'), findsOneWidget);
    expect(find.text('Refresh'), findsOneWidget);
  });
}
