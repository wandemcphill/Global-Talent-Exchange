import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/jackpot/presentation/gtex_jackpot_route_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('jackpot route fails closed without live API (no demo fallback)', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexJackpotRouteScreen(
          dependencies: const GteNavigationDependencies(
            apiBaseUrl: 'http://127.0.0.1:9',
            backendMode: GteBackendMode.live,
            isAuthenticated: false,
          ),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    expect(find.text('GTEX jackpot'), findsOneWidget);
    expect(find.text('GTEX jackpot unavailable'), findsOneWidget);
  });
}
