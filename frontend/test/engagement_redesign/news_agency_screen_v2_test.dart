import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/news_agency/gtex_news_agency_screen_v2.dart';

void main() {
  testWidgets('news agency screen renders AI newsroom title', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: GtexNewsAgencyScreenV2(allowFixtureData: true)),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('GTEX AI News Agency'), findsOneWidget);
    expect(find.textContaining('Lagos Galaxy'), findsWidgets);
  });

  testWidgets('news agency blocks fixture articles by default', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: GtexNewsAgencyScreenV2())),
    );
    await tester.pumpAndSettle();

    expect(find.text('News agency unavailable'), findsOneWidget);
    expect(
      find.textContaining('Live story feed API is required'),
      findsOneWidget,
    );
    expect(find.text('GTEX AI News Agency'), findsNothing);
    expect(find.textContaining('Lagos Galaxy'), findsNothing);
  });
}
