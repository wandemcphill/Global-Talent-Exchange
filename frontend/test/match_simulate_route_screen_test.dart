import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match/match_simulate_route_screen.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  testWidgets('simulation route stays blocked outside explicit fixture mode', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        const GteAppConfig(
          apiBaseUrl: 'https://example.test',
          backendMode: GteBackendMode.liveThenFixture,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Simulation sandbox blocked'), findsWidgets);
    expect(
      find.textContaining('reserved for explicit fixture-mode runs'),
      findsWidgets,
    );
    expect(find.text('Launch simulation'), findsNothing);
  });

  testWidgets('simulation route opens the local screen in fixture mode', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _host(
        const GteAppConfig(
          apiBaseUrl: 'https://example.test',
          backendMode: GteBackendMode.fixture,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Simulate'), findsWidgets);
    expect(find.text('Launch simulation'), findsOneWidget);
  });
}

Widget _host(GteAppConfig config) {
  return ProviderScope(
    overrides: [appConfigProvider.overrideWithValue(config)],
    child: const MaterialApp(home: MatchSimulateRouteScreen()),
  );
}
