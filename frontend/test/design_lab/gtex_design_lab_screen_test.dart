import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/design_lab/gtex_design_lab_screen.dart';

void main() {
  testWidgets(
    'design lab exposes all three distinct command-center directions',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(const MaterialApp(home: GtexDesignLabScreen()));

      expect(find.text('A · Matchday Pulse'), findsOneWidget);
      expect(find.text('B · Club Atlas'), findsOneWidget);
      expect(find.text('C · Ownership Ledger'), findsOneWidget);
      expect(
        find.text('The next football moment is the command.'),
        findsOneWidget,
      );

      await tester.tap(find.text('B · Club Atlas'));
      await tester.pumpAndSettle();
      expect(
        find.text('Your club is the world you are building.'),
        findsOneWidget,
      );

      await tester.tap(find.text('C · Ownership Ledger'));
      await tester.pumpAndSettle();
      expect(
        find.text('Make your football ownership visible.'),
        findsOneWidget,
      );
    },
  );

  testWidgets('design lab keeps specimens readable at mobile width', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(const MaterialApp(home: GtexDesignLabScreen()));

    expect(find.textContaining('ISOLATED FIXTURE MODE'), findsOneWidget);
    expect(
      find.text('The next football moment is the command.'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('design lab can open a requested visual direction', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: GtexDesignLabScreen(initialDirection: 'ownership'),
      ),
    );

    expect(find.text('Make your football ownership visible.'), findsOneWidget);
  });
}
