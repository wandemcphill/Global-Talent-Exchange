import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_redesign.dart';

void main() {
  testWidgets('global search sheet renders live-style results', (
    WidgetTester tester,
  ) async {
    String? openedRoute;
    final GtexGlobalSearchController controller = GtexGlobalSearchController(
      api: GtexGlobalSearchApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexGlobalSearchSheet(
            controller: controller,
            onOpenRoute: (String route) => openedRoute = route,
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'Jude');
    await tester.pumpAndSettle();

    expect(find.text('Jude Bellingham'), findsOneWidget);
    expect(find.text('Player'), findsOneWidget);

    await tester.tap(find.text('Jude Bellingham'));
    await tester.pumpAndSettle();

    expect(openedRoute, '/app/market?player=player-jude');
  });

  testWidgets('global search sheet opens product-loop result routes', (
    WidgetTester tester,
  ) async {
    String? openedRoute;
    final GtexGlobalSearchController controller = GtexGlobalSearchController(
      api: GtexGlobalSearchApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexGlobalSearchSheet(
            controller: controller,
            onOpenRoute: (String route) => openedRoute = route,
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'Liquidity');
    await tester.pumpAndSettle();

    expect(find.text('Lagos Liquidity Desk'), findsOneWidget);
    expect(find.text('Coin Trader'), findsOneWidget);

    await tester.tap(find.text('Lagos Liquidity Desk'));
    await tester.pumpAndSettle();

    expect(openedRoute, '/app/coin-traders?trader=trader-lagos');
  });

  testWidgets('global search sheet opens matchday economy result routes', (
    WidgetTester tester,
  ) async {
    String? openedRoute;
    final GtexGlobalSearchController controller = GtexGlobalSearchController(
      api: GtexGlobalSearchApi.fixture(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GtexGlobalSearchSheet(
            controller: controller,
            onOpenRoute: (String route) => openedRoute = route,
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'Africa');
    await tester.pumpAndSettle();

    expect(find.text('Africa GTEX Federation'), findsOneWidget);
    expect(find.text('Federation'), findsOneWidget);

    await tester.tap(find.text('Africa GTEX Federation'));
    await tester.pumpAndSettle();

    expect(openedRoute, '/app/play?federation=federation-africa');
  });
}
