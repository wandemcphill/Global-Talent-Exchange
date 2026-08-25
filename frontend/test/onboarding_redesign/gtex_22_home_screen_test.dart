import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/onboarding_redesign/gtex_22_home_screen.dart';

void main() {
  testWidgets('GTEX 22 homepage explains the platform in the first viewport', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Gtex22HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('FOOTBALL,\nREBUILT.'), findsOneWidget);
    expect(find.text('Everything football.\nOne living system.'), findsOneWidget);
    expect(find.text('Talent Exchange'), findsOneWidget);
    expect(find.text('Club Ownership'), findsOneWidget);
    expect(find.text('Matches & Competitions'), findsOneWidget);
    expect(find.text('Wallet & Economy'), findsOneWidget);
    expect(find.text('Social Football'), findsOneWidget);
    expect(find.text('Players'), findsNothing);
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

    expect(find.text('Create your GTEX identity'), findsOneWidget);
    expect(find.text('Discover & develop'), findsOneWidget);
    expect(find.text('Build & manage'), findsOneWidget);
  });
}
