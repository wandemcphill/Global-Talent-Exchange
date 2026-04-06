import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/jackpot/presentation/gtex_jackpot_route_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('guest jackpot route shows sign-in contribution gate', (
    WidgetTester tester,
  ) async {
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
    expect(find.text('Join the pool', skipOffstage: false), findsOneWidget);
    expect(
      find.text('Sign in to contribute', skipOffstage: false),
      findsOneWidget,
    );
  });

  testWidgets('admin jackpot route shows contribution and runtime controls', (
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
      find.text('Contribute from wallet', skipOffstage: false),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.text('Admin controls', skipOffstage: false),
      300,
      scrollable: find.byType(Scrollable),
    );
    await tester.pumpAndSettle();

    expect(find.text('Admin controls', skipOffstage: false), findsOneWidget);
    expect(find.text('Manual trigger', skipOffstage: false), findsOneWidget);
    expect(find.text('Recent rounds', skipOffstage: false), findsOneWidget);
  });
}
