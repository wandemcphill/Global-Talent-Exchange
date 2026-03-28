import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/main.dart';

void main() {
  testWidgets('renders the new GTEX shell and opens the transfer market', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(const ProviderScope(child: GtexApp()));
    await tester.pumpAndSettle();

    expect(find.text('GTEX'), findsOneWidget);
    expect(find.text('Command Center'), findsWidgets);
    expect(find.text('Play Match'), findsWidgets);

    await tester.tap(find.byKey(const Key('home-action-market')));
    await tester.pumpAndSettle();

    expect(find.text('Transfer Market'), findsWidgets);
    expect(find.text('Wallet Dashboard'), findsOneWidget);
    expect(find.text('Search player, club, or position'), findsOneWidget);
  });
}
