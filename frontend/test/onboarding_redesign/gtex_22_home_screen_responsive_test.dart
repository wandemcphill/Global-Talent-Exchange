import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/onboarding_redesign/gtex_22_home_screen.dart';

/// The GTEX 22 homepage is the public front door, so it has to lay out cleanly
/// on phones, tablets and desktops. Any `RenderFlex` overflow surfaces as an
/// unexpected exception and fails the matching case below.
void main() {
  const List<Size> viewports = <Size>[
    Size(360, 640),
    Size(430, 932),
    Size(768, 1024),
    Size(800, 600),
    Size(1200, 900),
    Size(1440, 900),
  ];

  for (final Size viewport in viewports) {
    testWidgets(
      'GTEX 22 homepage lays out without overflow at '
      '${viewport.width.toInt()}x${viewport.height.toInt()}',
      (WidgetTester tester) async {
        tester.view.physicalSize = viewport;
        tester.view.devicePixelRatio = 1;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await tester.pumpWidget(const MaterialApp(home: Gtex22HomeScreen()));
        await tester.pumpAndSettle();

        // Walk the whole page so every section is laid out at this viewport,
        // not just the slivers that happen to start on screen.
        final Finder page = find.byType(Scrollable).first;
        for (int step = 0; step < 30; step++) {
          await tester.drag(page, const Offset(0, -400));
          await tester.pump();
        }
        await tester.pumpAndSettle();
      },
    );
  }
}
