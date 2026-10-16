import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/onboarding_redesign/gtex_onboarding_flow_screen_v2.dart';
import 'package:gte_frontend/features/onboarding_redesign/gtex_public_landing_screen_v2.dart';
import 'package:gte_frontend/screens/gte_login_screen_v2.dart';

void main() {
  testWidgets('landing screen shows GTEX positioning', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexPublicLandingScreenV2()),
    );
    expect(find.text('GTEX'), findsOneWidget);
    expect(find.text('OWN A CLUB.\nSIGN THE STARS.'), findsOneWidget);
    expect(find.text('WIN IT ALL.'), findsOneWidget);
    expect(find.text('CHOOSE YOUR PATH'), findsOneWidget);
    expect(find.text('HOW YOU PLAY'), findsOneWidget);
    expect(find.text('Create free account'), findsOneWidget);
  });

  testWidgets('login screen validates required form fields', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: GteLoginScreenV2()));
    await tester.tap(find.text('Login'));
    await tester.pump();
    expect(find.text('Email address is required'), findsOneWidget);
    expect(find.text('Password is required'), findsOneWidget);
  });

  testWidgets('onboarding flow advances through setup steps', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: GtexOnboardingFlowScreenV2(allowFixtureData: true),
      ),
    );
    expect(find.text('Choose how you want to enter GTEX'), findsOneWidget);
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    expect(find.text('Pick your football region'), findsOneWidget);
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    expect(find.text('Create or join a club'), findsOneWidget);
  });

  testWidgets('onboarding flow blocks fixture state by default', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexOnboardingFlowScreenV2()),
    );

    expect(find.text('Live onboarding unavailable'), findsOneWidget);
    expect(find.text('Choose how you want to enter GTEX'), findsNothing);
  });
}
