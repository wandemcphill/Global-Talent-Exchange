import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/design_lab/gtex_competition_design_lab_screen.dart';

void main() {
  testWidgets('competition design lab explores three distinct hierarchies', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexCompetitionDesignLabScreen()),
    );

    expect(find.text('B · Competition atlas'), findsOneWidget);
    expect(find.text('The competition creates the matchday.'), findsOneWidget);
    expect(find.textContaining('FIXTURE-ONLY DESIGN LAB'), findsOneWidget);

    await tester.tap(find.text('A · Matchday board'));
    await tester.pumpAndSettle();
    expect(find.text('Next fixture first.'), findsOneWidget);

    await tester.tap(find.text('C · Participation desk'));
    await tester.pumpAndSettle();
    expect(find.text('Can this club enter?'), findsOneWidget);
  });

  testWidgets('competition design lab keeps fixture labels visible on mobile', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      const MaterialApp(home: GtexCompetitionDesignLabScreen()),
    );

    expect(find.textContaining('Local fixtures only'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('competition design lab accepts a capture direction in its route', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: GtexCompetitionDesignLabScreen(initialDirection: 'participation'),
      ),
    );
    expect(find.text('Can this club enter?'), findsOneWidget);
  });
}
