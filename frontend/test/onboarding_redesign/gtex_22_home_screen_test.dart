import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/onboarding_redesign/gtex_22_home_screen.dart';

Future<void> _scrollToPlatformMap(WidgetTester tester) async {
  final Finder page = find.byType(Scrollable).first;
  final Finder heading = find.text('Everything football.\nOne living system.');
  for (int step = 0; step < 12 && heading.evaluate().isEmpty; step++) {
    await tester.drag(page, const Offset(0, -320));
    await tester.pump();
  }
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('GTEX 22 homepage leads with the rebuilt-football hero', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Gtex22HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('FOOTBALL,\nREBUILT.'), findsOneWidget);
    // The hero owns the first viewport by design; the retired landing's
    // "Players" label must not reappear on it.
    expect(find.text('Players'), findsNothing);
  });

  testWidgets('GTEX 22 homepage maps the platform below the hero', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Gtex22HomeScreen()));
    await tester.pumpAndSettle();
    await _scrollToPlatformMap(tester);

    expect(find.text('Everything football.\nOne living system.'), findsOneWidget);
    expect(find.text('Talent Exchange'), findsOneWidget);
    expect(find.text('Club Ownership'), findsOneWidget);
    expect(find.text('Matches & Competitions'), findsOneWidget);
    expect(find.text('Wallet & Economy'), findsOneWidget);
    expect(find.text('Social Football'), findsOneWidget);
  });

  testWidgets('GTEX 22 role CTAs remain available on narrow screens', (tester) async {
    tester.view.physicalSize = const Size(430, 932);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(const MaterialApp(home: Gtex22HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Create free account'), findsOneWidget);
    expect(find.text('Discover & develop'), findsOneWidget);
    expect(find.text('Build & manage'), findsOneWidget);
  });
}
