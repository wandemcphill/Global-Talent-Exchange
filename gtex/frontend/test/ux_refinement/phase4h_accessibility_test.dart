import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// PHASE 4H - interaction that survives a phone.
void main() {
  testWidgets('the master-detail panel sheet close control has a name', (
    WidgetTester tester,
  ) async {
    // On a phone the browse and summary panels exist only as this sheet, and
    // this button is the only way back out of it. It used to be a bare glyph
    // with nothing a screen reader or a tooltip could announce.
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: Builder(
            builder: (BuildContext context) {
              return Center(
                child: TextButton(
                  onPressed:
                      () => showGtexMasterDetailPanelSheet(
                        context,
                        'Browse hub',
                        const Text('panel body'),
                      ),
                  child: const Text('open'),
                ),
              );
            },
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(find.text('panel body'), findsOneWidget);
    final IconButton close = tester.widget<IconButton>(
      find.widgetWithIcon(IconButton, Icons.close),
    );
    expect(
      close.tooltip,
      'Close Browse hub',
      reason: 'the sheet close control had no accessible name',
    );
  });
}
