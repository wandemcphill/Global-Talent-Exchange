import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/world/world_screen.dart';

void main() {
  testWidgets('lazy loads world tabs and joins a federation', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: WorldScreen()),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('World'), findsOneWidget);
    expect(find.byKey(const Key('world-loading-regens')), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 450));

    expect(find.byKey(const Key('world-regens-grid')), findsOneWidget);
    expect(
      find.byKey(const Key('world-regen-card-regen-kamara')),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const Key('world-tab-competitions')));
    await tester.pump(const Duration(milliseconds: 180));

    expect(find.text('GTEX World Cup'), findsNothing);

    await tester.pump(const Duration(milliseconds: 700));

    expect(find.text('GTEX World Cup'), findsOneWidget);
    expect(find.byKey(const Key('world-competition-card-0')), findsOneWidget);

    await tester.tap(find.byKey(const Key('world-tab-federations')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 900));

    expect(find.byKey(const Key('world-federation-card-0')), findsOneWidget);

    await tester.tap(find.byKey(const Key('world-federation-join-0')));
    await tester.pump();

    expect(find.text('Joined'), findsWidgets);
  });
}
