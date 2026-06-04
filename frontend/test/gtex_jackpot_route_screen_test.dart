import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/jackpot/presentation/gtex_jackpot_route_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'guest jackpot route blocks when backend jackpot data is missing',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: GtexJackpotRouteScreen(
            dependencies: const GteNavigationDependencies(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              isAuthenticated: false,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('GTEX jackpot'), findsOneWidget);
      expect(
        find.text('GTEX jackpot unavailable', skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.text('Sign in to contribute', skipOffstage: false),
        findsNothing,
      );
    },
  );

  testWidgets('admin jackpot route does not render fixture wallet money', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtexJackpotRouteScreen(
          dependencies: const GteNavigationDependencies(
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            isAuthenticated: true,
            currentUserRole: 'admin',
            accessToken: 'fixture-token',
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(
      find.text('GTEX jackpot unavailable', skipOffstage: false),
      findsOneWidget,
    );
    expect(find.textContaining('Wallet available:'), findsNothing);
    expect(find.textContaining('1,200'), findsNothing);
  });
}
