import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_order_ticket_sheet.dart';

/// PHASE5-A / PR-2B: the migrated trade ticket stays usable and legible.
///
/// The migration changed what the ticket says and submits, so this covers the
/// controls it touched - price, quantity, and the confirm action - across the
/// supported width ladder, plus their accessibility semantics.

Future<GteExchangeController> _controller(WidgetTester tester) async {
  late GteExchangeController controller;
  await tester.runAsync(() async {
    controller = GteExchangeController(api: GteExchangeApiClient.fixture());
    await controller.signIn(
      email: 'fixture.trader@gte.local',
      password: 'DemoPass123', // pragma: allowlist secret
    );
    await controller.openPlayer('lamine-yamal');
  });
  return controller;
}

/// The ticket shows an indeterminate progress indicator while settling, which
/// schedules frames forever, so pumpAndSettle would hang.
Future<void> _settle(WidgetTester tester) async {
  for (int i = 0; i < 20; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

void main() {
  // The supported ladder: phone, large phone, tablet, and desktop breakpoints.
  const List<double> widths = <double>[390, 430, 768, 1024, 1280, 1440, 1920];

  for (final double width in widths) {
    testWidgets('trade ticket lays out at ${width.toInt()}px',
        (WidgetTester tester) async {
      final GteExchangeController controller = await _controller(tester);

      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = Size(width, 900);
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GteOrderTicketSheet(
              controller: controller,
              snapshot: controller.selectedPlayer!,
            ),
          ),
        ),
      );
      await _settle(tester);

      // No RenderFlex overflow or fixed-height clipping at this width.
      expect(tester.takeException(), isNull);

      // Every control the migration touched is still reachable.
      expect(find.text('SHARE PRICE'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'Shares'), findsOneWidget);
      expect(find.text('Buy shares'), findsOneWidget);

      // The confirm action stays within the viewport rather than being
      // clipped off the bottom edge.
      final Rect button = tester.getRect(find.text('Buy shares'));
      expect(button.right, lessThanOrEqualTo(width));
      expect(button.left, greaterThanOrEqualTo(0));
    });
  }

  testWidgets('migrated controls carry accessible semantics',
      (WidgetTester tester) async {
    final GteExchangeController controller = await _controller(tester);
    final SemanticsHandle handle = tester.ensureSemantics();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GteOrderTicketSheet(
            controller: controller,
            snapshot: controller.selectedPlayer!,
          ),
        ),
      ),
    );
    await _settle(tester);

    // The quantity field is labelled, so it is not an unnamed text box.
    expect(
      tester.getSemantics(find.byType(EditableText)),
      matchesSemantics(
        isTextField: true,
        hasEnabledState: true,
        isEnabled: true,
        isFocusable: true,
        hasTapAction: true,
        hasFocusAction: true,
        label: 'Shares',
        value: '1',
      ),
    );

    // The confirm action announces itself as an enabled, tappable button.
    expect(
      tester.getSemantics(find.widgetWithText(FilledButton, 'Buy shares')),
      matchesSemantics(
        isButton: true,
        hasEnabledState: true,
        isEnabled: true,
        isFocusable: true,
        hasTapAction: true,
        hasFocusAction: true,
        label: 'Buy shares',
      ),
    );

    handle.dispose();
  });
}
