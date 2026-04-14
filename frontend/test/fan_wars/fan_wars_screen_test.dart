import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/fan_wars/presentation/fan_wars_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('public fan wars screen is explicitly read-only', (
    WidgetTester tester,
  ) async {
    await _pumpFanWarsScreen(tester);

    expect(
      find.textContaining('Public Fan Wars is read-only here'),
      findsOneWidget,
    );
    expect(find.text('Load Nations Cup'), findsOneWidget);
    expect(find.text('Create cup'), findsNothing);
    expect(find.text('Advance cup'), findsNothing);
  });

  testWidgets('admin fan wars screen exposes cup controls', (
    WidgetTester tester,
  ) async {
    await _pumpFanWarsScreen(tester, currentUserRole: 'admin');

    expect(find.text('Create cup'), findsOneWidget);
  });
}

Future<void> _pumpFanWarsScreen(
  WidgetTester tester, {
  String? currentUserRole,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: GteShellTheme.build(),
      home: FanWarsScreen(
        baseUrl: 'https://example.test',
        backendMode: GteBackendMode.fixture,
        currentUserRole: currentUserRole,
      ),
    ),
  );

  await tester.pumpAndSettle();
}
