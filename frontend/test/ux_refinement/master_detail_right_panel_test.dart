import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// The right panel carries the primary actions for the selected item (for
/// example buy/shortlist in the Transfer Hub). It is shown inline only when
/// the box the scaffold was handed can afford it *and* still leave the
/// detail pane its minimum width; otherwise it drops to the shared sheet.
///
/// The admission widths below are derived, not magic: with the default
/// 310px left panel, 340px right panel, 20px screen padding, 16px gaps and
/// a 420px detail floor, all three panes need 1142px of box, and the left
/// panel plus detail need 786px.
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

  testWidgets('right panel comes inline as soon as it is affordable', (
    WidgetTester tester,
  ) async {
    // Previously gated on the window being >= 1280 regardless of the box,
    // which both hid the panel when there was room and showed it when there
    // was not.
    await pumpScaffold(tester, 1142);
    expect(find.text('RIGHT-PANEL'), findsOneWidget);
    expect(find.text('LEFT-PANEL'), findsOneWidget);
    expect(find.text('DETAIL-PANEL'), findsOneWidget);
  });

  testWidgets('browse panel stays reachable once it is dropped', (
    WidgetTester tester,
  ) async {
    // 760px cannot afford the left panel and a 420px detail pane, so the
    // browse panel moves to a sheet rather than starving the content.
    await pumpScaffold(tester, 760);
    expect(find.text('LEFT-PANEL'), findsNothing);

    final Finder action = find.byKey(
      const Key('gtex-master-detail-browse-action'),
    );
    expect(action, findsOneWidget);
    await tester.tap(action);
    await tester.pumpAndSettle();
    expect(find.text('LEFT-PANEL'), findsOneWidget);
  });

  for (final double width in <double>[760, 900, 1100, 1141]) {
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
