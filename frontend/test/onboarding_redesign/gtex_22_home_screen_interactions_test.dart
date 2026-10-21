import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_club_ownership_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_competitions_and_jackpot_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_living_world_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_regen_economy_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_tv_and_finance_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/gtex_22_home_screen.dart';

void main() {
  testWidgets('GTEX 22 component: stage progression simulator responds to tap', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexClubOwnershipSection(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final Finder stageElite = find.text('Elite Championship Club');
    expect(stageElite, findsOneWidget);

    // Tap Elite stage
    await tester.tap(stageElite);
    await tester.pumpAndSettle();

    // Expect Elite 60% TV cut to be displayed
    expect(find.text('60% Club TV Share'), findsWidgets);
  });

  testWidgets('GTEX 22 component: revenue breakdown simulator switches tiers', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexTvAndFinanceSection(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final Finder establishedChip = find.text('Established Club (50%)');
    expect(establishedChip, findsOneWidget);

    // Tap Established tier
    await tester.tap(establishedChip);
    await tester.pumpAndSettle();

    // Expect Established indicative turnover: 1,650,000 GTC
    expect(find.text('1,650,000 GTC'), findsWidgets);
  });

  testWidgets('GTEX 22 component: regen dossier tab switcher updates active prospect', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexRegenEconomySection(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final Finder alvarezChip = find.textContaining('Mateo Alvarez');
    expect(alvarezChip, findsOneWidget);

    // Tap Mateo Alvarez chip
    await tester.tap(alvarezChip);
    await tester.pumpAndSettle();

    // Expect Mateo Alvarez's potential ceiling rating 91
    expect(find.text('91'), findsWidgets);
  });

  testWidgets('GTEX 22 component: Grounded AI News modal opens and dismisses', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexLivingWorldSection(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final Finder inspectBtn = find.text('Inspect Grounded Story & Facts').first;
    expect(inspectBtn, findsOneWidget);

    // Tap inspect
    await tester.tap(inspectBtn);
    await tester.pumpAndSettle();

    // Verify dialog contents
    expect(find.text('ESTABLISHED PLATFORM FACTS (READ-ONLY)'), findsOneWidget);
    expect(find.text('EDITORIAL NARRATION'), findsOneWidget);

    // Dismiss dialog via close button
    await tester.tap(find.byIcon(Icons.close_rounded));
    await tester.pumpAndSettle();

    expect(find.text('ESTABLISHED PLATFORM FACTS (READ-ONLY)'), findsNothing);
  });

  testWidgets('GTEX 22 component: competitions and jackpot section renders 4 scheduled drops', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: GtexCompetitionsAndJackpotSection(),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Continental Glory & 4 Scheduled Daily Jackpots'), findsOneWidget);
    expect(find.text('4 SCHEDULED DAILY DROPS • 6-HR CYCLE'), findsOneWidget);
    expect(find.text('TIME TO NEXT SCHEDULED DROP (FAILSAFE 6-HR CAP)'), findsOneWidget);
  });

  testWidgets('GTEX 22 interactions: auth and routing callbacks invoke successfully', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    bool signupCalled = false;
    bool loginCalled = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Gtex22HomeScreen(
          onSignup: () => signupCalled = true,
          onLogin: () => loginCalled = true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Tap 'Create free account'
    final Finder signupBtn = find.text('Create free account').first;
    await tester.tap(signupBtn);
    await tester.pump();
    expect(signupCalled, isTrue);

    // Tap 'Sign in' on navbar
    final Finder loginBtn = find.text('Sign in');
    await tester.tap(loginBtn);
    await tester.pump();
    expect(loginCalled, isTrue);
  });
}
