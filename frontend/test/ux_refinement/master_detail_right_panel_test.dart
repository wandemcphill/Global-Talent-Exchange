import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// The right panel carries the primary actions for the selected item (for
/// example buy/shortlist in the Transfer Hub). Below the desktop breakpoint
/// it cannot be shown inline, and it used to be dropped with no affordance
/// at all between 720px and 1280px.
void main() {
  Future<void> pumpScaffold(WidgetTester tester, double width) async {
    tester.view.physicalSize = Size(width, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexMasterDetailScaffold(
            title: 'Transfer Hub',
            leftPanel: Text('LEFT-PANEL'),
            detail: Text('DETAIL-PANEL'),
            rightPanel: Text('RIGHT-PANEL'),
          ),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets('right panel is inline on desktop', (WidgetTester tester) async {
    await pumpScaffold(tester, 1400);
    expect(find.text('RIGHT-PANEL'), findsOneWidget);
  });

  for (final double width in <double>[760, 900, 1100, 1279]) {
    testWidgets('right panel is reachable at ${width}px', (
      WidgetTester tester,
    ) async {
      await pumpScaffold(tester, width);

      expect(
        find.text('RIGHT-PANEL'),
        findsNothing,
        reason: 'no room for it inline at ${width}px',
      );
      final Finder action = find.byKey(
        const Key('gtex-master-detail-summary-action'),
      );
      expect(
        action,
        findsOneWidget,
        reason: 'the summary panel must still be reachable at ${width}px',
      );

      await tester.tap(action);
      await tester.pumpAndSettle();
      expect(find.text('RIGHT-PANEL'), findsOneWidget);
    });
  }

  testWidgets('compact layout keeps its own summary affordance', (
    WidgetTester tester,
  ) async {
    await pumpScaffold(tester, 400);
    expect(find.text('Open summary'), findsOneWidget);
    await tester.tap(find.text('Open summary'));
    await tester.pumpAndSettle();
    expect(find.text('RIGHT-PANEL'), findsOneWidget);
  });

  testWidgets('no summary affordance when there is no right panel', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(900, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexMasterDetailScaffold(
            title: 'Transfer Hub',
            leftPanel: Text('LEFT-PANEL'),
            detail: Text('DETAIL-PANEL'),
          ),
        ),
      ),
    );
    await tester.pump();
    expect(
      find.byKey(const Key('gtex-master-detail-summary-action')),
      findsNothing,
    );
  });
}
